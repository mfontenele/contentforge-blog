---
title: "OWASP Top 10 for agentic apps: agent security guardrails"
date: 2026-04-03T06:00:00-03:00
draft: false
categories: ["AI Agent Operations"]
tags: ["agent-security", "owasp", "prompt-injection", "llm-security", "ai-guardrails"]
keywords: ["agent security", "OWASP agentic applications", "prompt injection", "agent guardrails", "tool misuse"]
description: "The OWASP Top 10 for Agentic Applications defines the attack surfaces autonomous AI creates. Here's how to deploy production guardrails against each risk."
summary: "Autonomous agents introduce attack surfaces traditional security never anticipated — and the new OWASP ASI framework is the first standard built to address them."
cover:
  image: "/images/covers/2026-04-03-owasp-top-10-agentic-apps-security-guardrails/cover.jpg"
  alt: "teal LED panel"
  caption: "Photo by [Adi Goldstein](https://unsplash.com/@adigold1) on [Unsplash](https://unsplash.com/photos/EUsVwEOsblE)"
  relative: false
  hidden: false
ShowToc: true
TocOpen: true
faq:
- q: "What is the OWASP Top 10 for Agentic Applications?"
  a: "It is the first peer-reviewed security framework specifically addressing autonomous AI system risks, released December 2025. It defines ten attack classes — ASI01 through ASI10 — spanning goal hijacking, tool misuse, identity abuse, supply chain vulnerabilities, memory poisoning, and more. Over 100 industry experts contributed to its development, and OWASP paired the framework with threat modeling guides, secure development guidelines, and hackathons to speed adoption. The framework is described in depth in the first section of this article. One current limitation: the ASI framework is new, and while it defines risk categories well, production tooling and open-source implementations that fully address all ten classes are still maturing as of early 2026."
- q: "How does prompt injection differ from traditional injection attacks?"
  a: "Traditional injection attacks exploit syntax vulnerabilities in code parsers. Prompt injection exploits the LLM's natural language understanding — any text the agent reads is a potential attack vector, and there is no syntax to escape."
- q: "What is memory poisoning and why is it harder to detect than prompt injection?"
  a: "Memory poisoning injects malicious instructions into an agent's persistent vector store, so the attack survives across sessions and triggers days or weeks later in unrelated queries — see the memory poisoning section for concrete defense patterns. Unlike prompt injection, it cannot be caught by per-request guardrails; it requires provenance tracking and sanitization of the retrieval layer itself. The provenance tracking approaches described in this article are still maturing — production-grade open-source implementations are sparse as of early 2026, meaning many teams will need to build custom solutions or rely on commercial offerings."
- q: "How do I choose between Lakera Guard, AWS Bedrock Guardrails, and Azure AI Prompt Shield?"
  a: "Use the PINT benchmark comparison table in the production guardrails section: Lakera Guard leads at 95.22% with 0.1–0.2% false positives; AWS and Azure score around 89% with higher false positive rates. Cloud-native options simplify deployment within their respective ecosystems. For multi-cloud or self-hosted setups, Lakera Guard's API proxy model offers more flexibility."
- q: "Does the OWASP ASI framework cover multi-agent systems?"
  a: "Yes. ASI07 covers insecure inter-agent communication, ASI08 addresses cascading failures in multi-agent pipelines, and ASI10 targets rogue agents that deviate autonomously from intended behavior. The framework recommends treating every inter-agent message as untrusted and implementing cryptographic attestation for agent-to-agent communication."
---

**TL;DR**

- OWASP released its Agentic Security Initiative (ASI01–ASI10) in December 2025 — the first peer-reviewed framework for autonomous AI risk, built by 100+ industry experts.
- 80% of organizations have encountered risky AI agent behaviors; CVE-2025-68664 (CVSS 9.3) and the IDEsaster Project show these are production-grade threats, not theoretical ones.
- Deploy guardrails in phases: identity controls first, then runtime monitoring, sandboxed execution, and memory sanitization for long-term vector stores.

Agentic AI has created an agent security threat surface traditional application security was never built to handle. Traditional security assumed deterministic code that does what you tell it. Agentic AI does what it infers you mean — and attackers have learned to exploit exactly that gap. In 2025, 80% of organizations reported risky AI agent behaviors [1]. The first autonomous AI cyberattacks moved from proof-of-concept to production exploitation, targeting everything from developer toolchains to enterprise knowledge bases. The OWASP Top 10 for Agentic Applications, released December 2025 [2], is the industry's first peer-reviewed answer: a framework that names ten attack classes autonomous agents introduce, from goal hijacking to rogue behavior. Getting ahead of these risks before your agents reach production is no longer optional — it is a deployment requirement.

## Why traditional agent security requires a new approach

Conventional application security assumes a deterministic system: a function receives input, applies logic, returns output. Agents break this model. They read arbitrary content. They plan multi-step actions, call external tools, and store context across sessions — any of which becomes an attack vector. The OWASP Agentic Security Initiative was developed by over 100 industry experts specifically to address this new threat surface [2].

The ten ASI risks span the full agent lifecycle: goal hijacking (ASI01), tool misuse (ASI02), identity abuse (ASI03), supply chain vulnerabilities (ASI04), unexpected code execution (ASI05), memory poisoning (ASI06), insecure inter-agent communication (ASI07), cascading failures (ASI08), human trust exploitation (ASI09), and rogue agents (ASI10). Each risk class has concrete mitigations. OWASP paired the framework with threat modeling guides, secure development guidelines, and hackathons to speed adoption [2].

> [!WARNING]
> Every piece of text an agent reads is a potential attack surface. Agents do not inherently distinguish between legitimate instructions and injected ones — they process both as natural language.

```mermaid
graph TD\n A[Input] --> B{Planning}\n B --> C[Tool Execution]\n C --> D[Memory]\n D --> E[Output]\n
```

## ASI01–ASI03: goal hijacking, tool misuse, and the identity crisis

Goal hijacking (ASI01) is prompt injection at its most dangerous. Attackers embed hidden instructions inside content the agent processes — a knowledge base document, a calendar invite, an email — causing it to abandon its original objective without any code modification [3]. No syntax escaping helps here. The attack exploits the agent's language understanding directly, and agents never signal when their goals have been altered. Detection depends on behavioral monitoring, not input validation.

Tool misuse (ASI02) amplifies the blast radius. Agents with legitimate access to email, databases, APIs, and filesystems can be steered to exfiltrate data, trigger unauthorized transactions, or execute harmful commands — all while staying within granted permissions. Traditional perimeter controls never trigger. Real-world examples include agent-driven phishing campaigns using deepfake audio to impersonate executives and request fund transfers [4].

Scale is the core problem in identity abuse (ASI03). Machine identities — including [AI agents](/posts/2026-03-09-mast-taxonomy-enterprise-agent-failures/) — now outnumber humans by 80:1 to 100:1, yet 68% of organizations lack any identity security controls for these systems [5]. Consider that 42% of machine identities already access sensitive data with standing elevated permissions. The critical blind spot: 88% of organizations still define privileged identities as human-only — entirely overlooking what an AI agent can do at machine speed and scale [5].

Non-human identities are projected to surpass 45 billion by 2026. Only 10% of organizations have management strategies in place [5].

{{< key-takeaway >}}
Least-privilege enforcement [for AI agents](/posts/2026-03-03-ai-agent-observability-production/) is the single most impactful control — most organizations have not implemented it at all.
{{< /key-takeaway >}}

## LangGrinch and IDEsaster: what real exploits look like

CVE-2025-68664 — nicknamed LangGrinch — is a serialization injection vulnerability in LangChain Core affecting versions below 1.2.5 and 0.3.81, with a CVSS score of 9.3 [6]. Discovered in December 2025, the flaw exists in LangChain's `dumps()` and `dumpd()` functions, which fail to properly escape user-controlled dictionaries containing the reserved `'lc'` key. Because LangChain Core has hundreds of millions of installs globally [6], the exposure was immediate and broad.

The attack vector is prompt injection. An attacker steers an LLM to generate crafted structured outputs containing the 'lc' key in metadata fields — because LangChain uses that key internally to mark serialized objects, the serialization layer treats attacker-controlled data as trusted configuration, enabling secret leakage from environment variables, arbitrary object injection, and code execution through Jinja2 templates, all triggered from a single adversarial prompt [6]. Patch immediately: upgrade to LangChain Core ≥1.2.5 or ≥0.3.81. The fix introduces an allowed_objects allowlist, blocks Jinja2 templates by default, and removes automatic secret loading from the environment.

The IDEsaster Project, published January 2026, found 30+ vulnerabilities across AI-powered IDEs with 24 CVEs assigned — 100% of tested tools were vulnerable [7]. Scope: 1.8 million developers. Tools affected included GitHub Copilot, Cursor, Windsurf, [Claude Code](/posts/2026-03-20-garry-tan-gstack-agent-teams-claude-code/), Gemini CLI, and others. One flaw scored CVSS 10.0. The three-stage attack chain: prompt injection hijacks AI context, legitimate tools collect sensitive data, then the agent writes malicious JSON configs triggering base IDE features for exfiltration or RCE [7]. These IDEs were designed for human users. Autonomous agents weaponize the same features into attack primitives.

```mermaid
graph TD\n A[Prompt Injection] --> B{Tool Exploitation}\n B --> C[Config Weaponization]\n C --> D[RCE/Data Exfiltration]\n
```

## Memory poisoning and supply chain: the persistent threats (ASI04, ASI06)

Memory poisoning (ASI06) is more dangerous than prompt injection because it outlives individual sessions. Attackers inject malicious instructions into an agent's long-term memory — typically a vector store used for RAG — using phrases like "Remember that..." to trick the agent into persisting the payload [8]. Once embedded, poisoned data activates in unrelated queries days or weeks later, prioritizing attacker instructions over legitimate user input. The MINJA methodology demonstrated 95%+ success rates at NeurIPS 2025 — though these results are from controlled lab conditions; production vector stores with namespace isolation and active provenance tracking have not been evaluated at the same scale [8]. Microsoft's 2026 report documented 50+ unique exploitation prompts from 31 companies across 14 industries over a 60-day period [9].

If your agent uses a vector store for long-term memory, trust-aware retrieval and provenance tracking are non-negotiable. Implement namespace isolation to restrict what the agent can retrieve per session — scoping retrieval to auditable, task-specific subsets reduces the blast radius if a poisoning attack does succeed. Provenance metadata on every stored chunk lets you trace any retrieved content back to its origin and flag suspicious insertions before they activate.

Supply chain risks (ASI04) exploit a property unique to agentic architectures: runtime component loading. Traditional software ships with a fixed dependency set — agents dynamically pull MCP servers, plugins, prompt templates, and tool configurations from external sources at execution time, creating a trust boundary that effectively does not exist unless you build it explicitly [3]. Two 2025 incidents illustrate the risk: the Shai-Hulud Worm, a self-replicating npm attack that compromised hundreds of packages via stolen tokens in September 2025, and Git MCP server flaws (CVE-2025-68143 to -68145) that exposed arbitrary filesystem paths and unsanitized CLI arguments [3]. Neither required zero-days.

> [!TIP]
> Pin all agent dependencies by cryptographic hash and maintain an AI-BOM (Bill of Materials). For MCP servers, allowlist domains and verify signatures before runtime loading.

## Production agent security guardrails: benchmarks, deployment, and phased rollout

Deploying guardrails without benchmarks is guesswork. The PINT benchmark provides an objective measure — though note it is published by Lakera itself, and independent third-party validation of these scores is not yet available. With that context: Lakera Guard leads at 95.2200% balanced accuracy on prompt injection detection [10], ahead of AWS Bedrock Guardrails (89.2404%) and Azure AI Prompt Shield (89.1241%) [10]. Lakera Guard achieves false-positive rates of 0.1–0.2% via per-application tuning [12] — well below the 1–3% typical of tuned commercial systems.

| Solution | PINT Score | False Positive Rate | Deployment |
| --- | --- | --- | --- |
| Lakera Guard | 95.22% | 0.1–0.2% | API proxy |
| AWS Bedrock Guardrails | 89.24% | 1–3% | AWS-native |
| Azure AI Prompt Shield | 89.12% | 1–3% | Azure-native |
| Rebuff (open source) | Varies | Varies | Self-hosted |

```mermaid
graph TD\n    A[Pre-deployment] --> B[ASI assessment, policy definition, compliance mapping]\n    B --> C[Implementation]\n    C --> D[Zero-trust credentials, audit logging, prompt shield proxy]\n    D --> E[Ongoing]\n    E --> F[Monthly log reviews, quarterly red-team, MITRE ATLAS exercises]
```

Beyond prompt injection detection, production hardening follows three phases [11]. Pre-deployment is mostly assessment work: run an OWASP ASI risk assessment, define acceptable use policies for each agent, and map compliance requirements (GDPR, HIPAA, SOC 2) before a line of agentic code ships. Then harden at implementation. Configure zero-trust access with short-lived credentials, enable comprehensive audit logging with tamper-proof records, and deploy your prompt shield as an API proxy. Ongoing: monthly log reviews, quarterly vulnerability assessments, and periodic red-team exercises using MITRE ATLAS (AML.T0080) [11].

Code-executing agents (ASI05) need a hard boundary between generation and execution. Use sandboxed ephemeral environments — Firecracker micro-VMs or WebAssembly runtimes — drop privileges before running generated code, and enforce strict allowlists on syscalls and network egress. For multi-agent pipelines, treat every inter-agent message as untrusted. Implement cryptographic attestation for agent-to-agent communication and define explicit trust boundaries before a compromised agent can cascade failures across the system [3].

## Practical Takeaways

1. Patch LangChain Core now — upgrade to ≥1.2.5 / ≥0.3.81 to close CVE-2025-68664 (CVSS 9.3, the LangGrinch serialization injection flaw that enables environment variable leakage, object injection, and RCE via a single adversarial prompt).
2. Assign unique short-lived credentials to every agent. 68% of organizations currently have zero identity controls for AI systems.
3. Deploy a prompt injection guardrail as an API proxy layer before your LLM — evaluate using the PINT benchmark, where Lakera Guard leads at 95.22% accuracy; its 0.1–0.2% false-positive rate comes from per-application tuning documented in Lakera's Fall 2025 report, versus 89% accuracy and 1–3% false positives for cloud-native alternatives.
4. Sanitize your vector store. Memory poisoning (ASI06) persists across sessions and achieves 95%+ success rates in lab conditions — implement trust-aware retrieval, provenance tracking, and namespace isolation.
5. Pin dependencies by cryptographic hash, maintain an AI-BOM, and allowlist MCP server domains before runtime loading.
6. Schedule quarterly red-team exercises using MITRE ATLAS (AML.T0080) to surface ASI-class vulnerabilities before attackers do.

## Conclusion

The OWASP ASI framework marks a turning point: for the first time, agentic attack classes have a peer-reviewed taxonomy that CVE scoring bodies, compliance auditors, and regulators can reference. The next wave of standardization is already underway — expect ASI-class risks to appear in CVSS scoring guidance and cloud provider compliance checklists within 12–18 months, reshaping how organizations get audited for AI deployments. Teams that build against the ASI framework now will find themselves ahead of mandatory requirements, not scrambling to retrofit controls under deadline. The window to harden proactively, before enforcement catches up, is open — but it is not permanent.

## Frequently Asked Questions

### What is the OWASP Top 10 for Agentic Applications?

It is the first peer-reviewed security framework specifically addressing autonomous AI system risks, released December 2025. It defines ten attack classes — ASI01 through ASI10 — spanning goal hijacking, tool misuse, identity abuse, supply chain vulnerabilities, memory poisoning, and more. Over 100 industry experts contributed to its development, and OWASP paired the framework with threat modeling guides, secure development guidelines, and hackathons to speed adoption. The framework is described in depth in the first section of this article. One current limitation: the ASI framework is new, and while it defines risk categories well, production tooling and open-source implementations that fully address all ten classes are still maturing as of early 2026.

### How does prompt injection differ from traditional injection attacks?

Traditional injection attacks exploit syntax vulnerabilities in code parsers. Prompt injection exploits the LLM's natural language understanding — any text the agent reads is a potential attack vector, and there is no syntax to escape.

### What is memory poisoning and why is it harder to detect than prompt injection?

Memory poisoning injects malicious instructions into an agent's persistent vector store, so the attack survives across sessions and triggers days or weeks later in unrelated queries — see the memory poisoning section for concrete defense patterns. Unlike prompt injection, it cannot be caught by per-request guardrails; it requires provenance tracking and sanitization of the retrieval layer itself. The provenance tracking approaches described in this article are still maturing — production-grade open-source implementations are sparse as of early 2026, meaning many teams will need to build custom solutions or rely on commercial offerings.

### How do I choose between Lakera Guard, AWS Bedrock Guardrails, and Azure AI Prompt Shield?

Use the PINT benchmark comparison table in the production guardrails section: Lakera Guard leads at 95.22% with 0.1–0.2% false positives; AWS and Azure score around 89% with higher false positive rates. Cloud-native options simplify deployment within their respective ecosystems. For multi-cloud or self-hosted setups, Lakera Guard's API proxy model offers more flexibility.

### Does the OWASP ASI framework cover multi-agent systems?

Yes. ASI07 covers insecure inter-agent communication, ASI08 addresses cascading failures in multi-agent pipelines, and ASI10 targets rogue agents that deviate autonomously from intended behavior. The framework recommends treating every inter-agent message as untrusted and implementing cryptographic attestation for agent-to-agent communication.

---

## Sources

| # | Publisher | Title | URL | Date | Type |
| --- | --- | --- | --- | --- | --- |
| 1 | Acuvity AI | "2025: The Year AI Security Became Non-Negotiable" | https://acuvity.ai/2025-the-year-ai-security-became-non-negotiable/ | 2025 | Blog |
| 2 | OWASP GenAI Security Project | "OWASP Top 10 for Agentic Applications — The Benchmark for Agentic Security" | https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/ | 2025-12-09 | Documentation |
| 3 | Lares Labs | "OWASP Agentic Top 10 Deep Dive" | https://labs.lares.com/owasp-agentic-top-10/ | 2025 | Blog |
| 4 | InfoQ | "OWASP Agentic AI Security" | https://www.infoq.com/news/2025/09/owasp-agentic-ai-security/ | 2025-09 | News |
| 5 | CyberArk | "Securing AI Agents: Privileged Machine Identities at Unprecedented Scale" | https://www.cyberark.com/resources/blog/securing-ai-agents-privileged-machine-identities-at-unprecedented-scale | 2025 | Blog |
| 6 | Security Affairs | "LangChain Core Vulnerability CVE-2025-68664 (LangGrinch)" | https://securityaffairs.com/186185/hacking/langchain-core-vulnerability-allows-prompt-injection-and-data-exposure.html | 2025-12 | News |
| 7 | MaccariTA Research | "IDEsaster: 30+ Vulnerabilities in AI-Powered IDEs" | https://maccarita.com/posts/idesaster/ | 2026-01 | Blog |
| 8 | Palo Alto Networks Unit 42 | "Indirect Prompt Injection Poisons AI Long-Term Memory" | https://unit42.paloaltonetworks.com/indirect-prompt-injection-poisons-ai-longterm-memory/ | 2025 | Blog |
| 9 | Microsoft Security Blog | "AI Recommendation Poisoning" | https://www.microsoft.com/en-us/security/blog/2026/02/10/ai-recommendation-poisoning/ | 2026-02-10 | Blog |
| 10 | Lakera | "PINT Benchmark — Prompt Injection Test" | https://github.com/lakeraai/pint-benchmark | 2025-05-02 | Technical |
| 11 | Glean | "Best Practices for AI Agent Security in 2025" | https://www.glean.com/perspectives/best-practices-for-ai-agent-security-in-2025 | 2025 | Blog |
| 12 | Lakera | "Lakera Guard Fall 2025: Adaptive at Scale" | https://www.lakera.ai/blog/lakera-guard-fall-25-adaptive-at-scale | 2025 | Blog |

## Image Credits

- **Cover photo**: [Adi Goldstein](https://unsplash.com/@adigold1) on [Unsplash](https://unsplash.com/photos/EUsVwEOsblE)
