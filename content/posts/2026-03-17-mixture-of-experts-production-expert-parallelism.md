---
title: "Mixture of experts in production: expert parallelism and the new inference stack"
date: 2026-03-17T06:00:00-03:00
draft: false
categories: ["AI Agent Operations"]
tags: ["moe", "inference", "llm-serving", "distributed-systems", "transformers"]
keywords: ["mixture of experts production", "expert parallelism", "MoE inference", "Transformers v5", "sparse LLM deployment"]
description: "How MoE models like GPT-OSS reshape production LLM inference with expert parallelism, async weight loading, and grouped GEMM backends in Transformers v5."
summary: "Sparse MoE architectures have won the LLM scaling race — here is how to actually run them at production scale."
cover:
  image: "/images/covers/2026-03-17-mixture-of-experts-production-expert-parallelism/cover.jpg"
  alt: "Abstract neural network visualization representing distributed expert routing in Mixture of Experts architecture"
  caption: "Cover: Neural network abstraction — Photo by Unsplash"
  relative: false
  hidden: false
ShowToc: true
TocOpen: true
faq:
- q: "What is the difference between Expert Parallelism and Tensor Parallelism for MoE models?"
  a: "Tensor Parallelism shards individual weight matrices across GPUs and requires all-reduce communication after each matrix multiply. Expert Parallelism assigns entire expert modules to specific GPUs and routes tokens to the device holding the required expert — eliminating all-reduce overhead and fitting far more experts in available VRAM."
- q: "How does async weight loading work in Transformers v5?"
  a: "The WeightConverter abstraction maps per-expert checkpoint tensors to packed runtime tensors via a thread pool, converting tensors asynchronously as they arrive from disk. This avoids the memory spike from holding both unpacked and packed tensors simultaneously, reducing Qwen 110B load time from 66s to ~20.7s (async alone); combining with tensor parallelism achieves 10.1s."
- q: "When should I use grouped_mm vs batched_mm as the expert backend?"
  a: "Use grouped_mm for large batches or memory-constrained setups where grouped GEMM provides the best kernel utilization. Use batched_mm for consumer hardware or low-concurrency scenarios. Use eager only for debugging."
---

**TL;DR**

- GPT-OSS-20B activates only 3.6B of 21B parameters per token, hitting ~115 tok/s on Apple M3 Ultra hardware.
- Expert Parallelism distributes experts across GPUs, solving the VRAM wall that standard tensor parallelism cannot handle for large sparse models.

Running a 120-billion-parameter model on a single GPU sounds like marketing copy. For dense models, it is. For Mixture of Experts architectures, it is engineering reality — GPT-OSS-120B fits on one H100 via MXFP4 [quantization](/posts/2026-03-05-cutting-llm-agent-costs-by-50-a-production-engineers-playbook/) because it activates only 5.1 billion parameters per token [3]. The MoE wave that began with DeepSeek R1 in January 2025 has flooded the open-weights ecosystem: GPT-OSS, Kimi K2.5, Qwen 3.5, MiniMax M2, and GLM-5 all use sparse routing [1]. Every inference framework built for dense transformers struggles when experts scatter tokens across GPUs. Deploying MoE at production scale requires a different parallelism strategy, a new weight-loading pipeline, and backend-aware kernel selection. Transformers v5 delivers all three. The result is an inference stack purpose-built for sparse architectures — a genuine step change in what you can run on the hardware you already own.

## Total vs. active parameters: the math behind MoE efficiency

Dense LLMs have a single compute-to-parameter relationship: every token activates every weight. MoE models break this coupling. A routing layer selects a small subset of expert feed-forward networks for each token, leaving the rest idle. The result is a model whose capacity scales with total parameters but whose inference cost scales with active parameters — a fundamentally more efficient design for large-scale deployment [1]. This is what finally makes very large models economically viable for teams without hyperscaler-scale infrastructure.

GPT-OSS-20B makes the math concrete: 21B total parameters, only 3.6B active per token — a ~6x sparsity ratio [3]. That ratio allows the model to run at approximately 115 tokens per second on Apple M3 Ultra hardware. A dense 20B-class model on the same hardware would be memory-bandwidth-throttled to a fraction of that throughput. The 120B variant (117B total, 5.1B active per token) fits within a single 80GB H100 via MXFP4 post-training quantization of its MoE weight tensors, enabling single-GPU deployment at full model scale [1][3].

| Model | Total Parameters | Active per Token | Sparsity Ratio | Single-GPU Fit |
| --- | --- | --- | --- | --- |
| GPT-OSS-20B | 21B | 3.6B | ~6x | Yes (consumer hardware) |
| GPT-OSS-120B | 117B | 5.1B | ~23x | Yes (H100 80GB, MXFP4) |
| Dense 20B baseline | 20B | 20B | 1x | No (requires multiple GPUs) |

> [!NOTE]
> Sparsity ratio = total parameters / active parameters per token. Higher ratios deliver better inference efficiency but increase memory bandwidth demands from scattered expert lookups.

The tradeoff is not free. MoE inference is inherently **memory-bandwidth bound**. Each token routes to a small set of experts, meaning the GPU must load many small weight tensors on demand rather than streaming one large matrix. This is why standard tensor parallelism strategies perform poorly with MoE — they shard individual weight matrices, not the expert dimension.

## Expert parallelism: beyond tensor and pipeline sharding

Tensor Parallelism (TP) splits a single weight matrix across GPUs column- or row-wise, requiring an all-reduce communication pass after each matrix multiply. Pipeline Parallelism (PP) assigns consecutive transformer layers to different devices, introducing bubble latency. Both strategies assume weights are monolithic — a poor fit for MoE, where hundreds of independent expert weight matrices must live separately [1].

Expert Parallelism (EP) distributes entire experts across the cluster. Each GPU holds `num_experts / num_devices` experts. The router dispatches each token to the GPU holding the required expert, eliminating the all-reduce that TP requires and the pipeline bubble that PP introduces. EP scales predictably: adding more GPUs reduces expert load per device linearly. For large MoE models, EP is the only strategy that keeps VRAM requirements tractable without aggressive quantization [1]. TP and PP do not have this property — communication overhead and bubble latency both grow with device count.

{{< mermaid >}}
graph TB
    subgraph "Tensor Parallelism (TP)"
        T1[Token] -->|broadcast| G0[GPU0<br/>W cols 0-25%]
        T1 -->|broadcast| G1[GPU1<br/>W cols 25-50%]
        T1 -->|broadcast| G2[GPU2<br/>W cols 50-75%]
        T1 -->|broadcast| G3[GPU3<br/>W cols 75-100%]
        G0 --> AR[All-Reduce Sync]
        G1 --> AR
        G2 --> AR
        G3 --> AR
    end
    
    subgraph "Expert Parallelism (EP)"
        T2[Token] --> R[Router]
        R -->|route| E0[GPU0<br/>Experts E0-E1]
        R -->|route| E1[GPU1<br/>Experts E2-E3]
        R -->|route| E2[GPU2<br/>Experts E4-E5]
        R -->|route| E3[GPU3<br/>Experts E6-E7]
    end
    
    style AR fill:#ffcccc
    style R fill:#ccffcc
{{< /mermaid >}}

```text
Tensor Parallelism (TP)          Expert Parallelism (EP)
─────────────────────────        ─────────────────────────
  Single weight matrix W           Experts E0–E7 distributed

  GPU0 | W[cols  0–25%]            GPU0 | E0, E1
  GPU1 | W[cols 25–50%]            GPU1 | E2, E3
  GPU2 | W[cols 50–75%]            GPU2 | E4, E5
  GPU3 | W[cols 75–100%]           GPU3 | E6, E7

  Token → broadcast to ALL GPUs   Token → routed to ONE GPU
  Result → all-reduce (sync)       Result → no all-reduce needed

  ✗ All-reduce cost grows with N   ✓ Communication stays local
  ✗ Experts share sharded VRAM     ✓ Each GPU owns full experts
```

In Transformers v5, EP is enabled via `DistributedConfig(enable_expert_parallel=True)`. Two primitives power the implementation: `GroupedGemmParallel` shards expert weights along the expert dimension, enabling single-kernel dispatch to multiple experts. `RouterParallel` remaps global expert indices to local device indices so routing decisions on one GPU correctly resolve to weights on another [1].

```python
from transformers import AutoModelForCausalLM, DistributedConfig

# Enable Expert Parallelism across the current process group
dist_config = DistributedConfig(enable_expert_parallel=True)

model = AutoModelForCausalLM.from_pretrained(
    "openai/gpt-oss-120b",
    distributed_config=dist_config,
    torch_dtype="auto",
    device_map="auto",
)
```

{{< key-takeaway >}}
Use Expert Parallelism instead of tensor parallelism whenever deploying MoE models with more than ~16 experts. EP is the only strategy that scales naturally with expert count and avoids the all-reduce bottleneck.
{{< /key-takeaway >}}

## WeightConverter and async loading: from 66 seconds to 10

MoE checkpoints store individual per-expert weight tensors — natural for training, expensive at inference. Efficient grouped GEMM kernels require a single packed tensor containing all expert weights. Bridging this mismatch naively means scanning the checkpoint twice, allocating full-model memory during conversion, and blocking the GPU until the process completes [1].

Transformers v5 introduces the `WeightConverter` abstraction to solve this. A converter defines source key patterns and target packing operations such as `MergeModulelist` or `Concatenate`. The loader schedules conversion via a thread pool, enabling lazy materialization that converts expert tensors into packed format as they arrive from disk. The result: Qwen 110B load time drops from ~20.7 seconds (async alone, `device_map="auto"`) to 10.1 seconds when async loading is combined with tensor parallelism [1][2].

> [!TIP]
> Set `use_async_weight_loading=True` when loading large MoE checkpoints. The improvement is most dramatic on models with 64+ experts where the packing overhead dominates cold-start latency.

Async loading also reduces peak memory during initialization. Eager loading allocates memory for both unpacked checkpoint tensors and packed target tensors simultaneously — a transient spike that can exceed available VRAM even when the steady-state model fits. The lazy materialization pipeline reuses memory regions as conversion completes, eliminating this spike [1].

The cold-start improvement matters for auto-scaling. When a new serving replica spins up to handle a traffic spike, a 66-second load time means over a minute of cold requests hitting remaining replicas. Cutting that to 10 seconds lets you scale out more aggressively without degrading tail latency during the ramp-up period [1].

**KV cache and memory budgeting.** A critical MoE memory planning trap: KV cache growth is not gated by the router. Every token in the context window generates key-value pairs for every attention head in every layer, regardless of which experts were activated. KV state therefore scales with total context length, not active parameter count, and can dominate GPU memory under realistic concurrency. In auto-scaling deployments, each replica must reserve KV cache headroom proportional to max context length times concurrent sequences — entirely independent of the model's sparsity ratio. Profile this before setting memory budgets: a model that fits at batch size 1 can OOM at batch size 8 without explicit KV cache allocation.

## Expert backends: choosing eager, batched_mm, or grouped_mm

Transformers v5 ships a pluggable Expert Backend system that exposes three execution strategies via the `@use_experts_implementation` decorator. Each backend makes different trade-offs between simplicity, GPU utilization, and memory footprint [1].

| Backend | Mechanism | Best For | Caveat |
| --- | --- | --- | --- |
| eager | Loops over selected experts sequentially | Debugging and reference implementations | Slowest — not suitable for production throughput |
| batched_mm | Batched GEMM via torch.bmm | Small-batch GPU workloads, consumer hardware | Suboptimal for large batch sizes |
| grouped_mm | Grouped GEMM via torch._grouped_mm | Large batches or memory-constrained setups | Requires compatible grouped GEMM kernel support on the target hardware |

For production serving with vLLM, TensorRT-LLM, or SGLang on server-class hardware, `grouped_mm` is the recommended backend [1]. Grouped GEMM dispatches multiple expert operations in a single kernel call, reducing kernel launch overhead. For consumer hardware such as M3 Ultra running GPT-OSS-20B at ~115 tok/s, `batched_mm` performs better — batch sizes at the edge are smaller and per-request latency matters more than throughput [1][3]. Switching backends requires no model reload; the decorator applies at the module level, so you can benchmark all three against your production request distribution before committing.

## Training efficiency: the Hugging Face + Unsloth 12x speedup

Fine-tuning MoE models feeds directly into the serving stack — teams checkpoint-tune before deploying, making training efficiency a direct input to inference latency and replica cost. The Transformers v5 and Unsloth collaboration directly addresses this gap [1]. Before Transformers v5, fine-tuning a 20B MoE model required hardware most teams did not have. The v5 + Unsloth stack changes that calculus.

The collaboration delivers three headline numbers compared to Transformers v4: up to ~12x faster MoE training, over 35% VRAM reduction, and up to ~6x longer context support [1]. VRAM savings come from fused expert kernels that avoid materializing intermediate activations for idle experts. The collaboration also enables up to ~6x longer context support [1]. The Transformers repository [2] tracks ongoing kernel improvements and expert-aware gradient checkpointing that further reduce memory pressure during long-context fine-tuning runs.

## Practical Takeaways

1. Enable Expert Parallelism via DistributedConfig(enable_expert_parallel=True) in Transformers v5 for any multi-GPU MoE deployment — standard tensor parallelism is the wrong primitive for sparse models.
2. Set use_async_weight_loading=True when loading large MoE checkpoints; WeightConverter in Transformers v5 reduces cold-start latency up to 6x (e.g., 66s → 10s for Qwen 110B).
3. Select the expert backend by workload: grouped_mm for large batches or memory-constrained setups, batched_mm for consumer hardware or low-concurrency deployments, eager only for debugging.
4. Profile KV cache growth under realistic concurrency before setting memory budgets — KV state scales with total context length, independent of active parameter count.

## Conclusion

Mixture of Experts architectures have structurally changed what is possible in production LLM deployment. A 117-billion-parameter model on one GPU was implausible twelve months ago; today it is a configuration choice. That progress depends on Expert Parallelism distributing workloads correctly, async weight loading cutting cold-start latency, and grouped GEMM backends matching kernel execution to hardware. Transformers v5 packages all three into a coherent framework designed for sparse models. Teams still running dense-model stacks should treat MoE as an infrastructure upgrade: lower hardware cost, higher throughput, and a growing ecosystem of permissively licensed models. Benchmark GPT-OSS-20B against your production workload before committing.

## Frequently Asked Questions

### What is the difference between Expert Parallelism and Tensor Parallelism for MoE models?

Tensor Parallelism shards individual weight matrices across GPUs and requires all-reduce communication after each matrix multiply. Expert Parallelism assigns entire expert modules to specific GPUs and routes tokens to the device holding the required expert — eliminating all-reduce overhead and fitting far more experts in available VRAM.

### How does async weight loading work in Transformers v5?

The WeightConverter abstraction maps per-expert checkpoint tensors to packed runtime tensors via a thread pool, converting tensors asynchronously as they arrive from disk. This avoids the memory spike from holding both unpacked and packed tensors simultaneously, reducing Qwen 110B load time from 66s to ~20.7s (async alone); combining with tensor parallelism achieves 10.1s.

### When should I use grouped_mm vs batched_mm as the expert backend?

Use grouped_mm for large batches or memory-constrained setups where grouped GEMM provides the best kernel utilization. Use batched_mm for consumer hardware or low-concurrency scenarios. Use eager only for debugging.

---

## Sources

| # | Publisher | Title | URL | Date | Type |
| --- | --- | --- | --- | --- | --- |
| 1 | Hugging Face | "MoE in Transformers" | https://huggingface.co/blog/moe-transformers | 2026-03 | Blog |
| 2 | Hugging Face | "Transformers: MoE Expert Backend Implementation (moe.py)" | https://github.com/huggingface/transformers/blob/main/src/transformers/integrations/moe.py | 2026-03 | Documentation |
| 3 | OpenAI / Hugging Face | "GPT-OSS-20B Model Card" | https://huggingface.co/openai/gpt-oss-20b | 2026-03 | Documentation |