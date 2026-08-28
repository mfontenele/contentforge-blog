---
title: "Agent identity: runtime governance for non-human principals"
date: 2026-08-28T06:00:00-03:00
draft: false
categories: ["AI Agent Operations"]
tags: ["agent-identity", "non-human-identity", "workload-identity", "agent-governance", "iam"]
keywords: ["agent identity", "non-human identity", "workload identity", "agent governance", "IAM for agents"]
description: "Agent identity governance is failing: MCP config files exposed 24,008 unique secrets in 2025 alone. Here's how runtime credential governance fixes it."
summary: "Stop handing agents long-lived secrets; govern credential use the moment each agent acts, not at rest."
cover:
  image: "/images/covers/2026-08-28-agent-identities-first-class-principals-nhi-governance/cover.jpg"
  alt: "Agent identity governance: molten silver orbs on obsidian, evaporating into violet steam under warm side-lighting"
  caption: "Image generated with gemini-3-pro-image (Agents' Codex AI illustration)"
  relative: false
  hidden: false
ShowToc: true
TocOpen: true
faq:
- q: "Is a password manager enough for agent credentials?"
  a: "No. A password manager protects credentials at rest, but the real problem is how an agent uses them at runtime. You need runtime credential governance, not just storage."
- q: "What is the difference between secret storage and runtime credential governance?"
  a: "Secret storage keeps a credential somewhere safe until it is needed, and that is where it stops. Runtime credential governance controls the credential at the exact moment an identity uses it, brokering each request and writing an audit record rather than assuming a pre-provisioned secret is fine [1]. Storage is necessary but insufficient; the decision that actually matters is made in the brokerage layer, when the agent asks to read a table or call an API, not at rest in the vault."
- q: "Should we adopt workload identity federation right away?"
  a: "It depends on your cloud posture. Federation removes the long-lived secret and is the cleanest fix, but it requires trust configuration between your platform and an external identity provider. We have not seen clean production guidance on how agent-to-agent delegation behaves under federation, so pilot it on one workload and measure before you roll it out broadly."
- q: "How do we find agent credentials we did not know we had?"
  a: "Start with discovery: scan for API keys and MCP config files across your repos and environments. The four-layer model puts discovery first for a reason, see the layers table above. We do not have clean production data on total sprawl, so treat any single scan as a lower bound rather than a complete inventory."
---

**TL;DR**

- MCP config files leaked 24,008 unique secrets in 2025, and AI credential leaks jumped 81.5% year over year [1].
- Runtime credential governance controls access at the moment of use, replacing standing secrets with brokered, short-lived tokens.
- Federated token exchange removes the long-lived credential entirely, so there is nothing left to leak or revoke.

In a single year, [Model Context Protocol](/posts/2026-08-14-federated-mcp-distributed-tool-access/) (MCP) configuration files exposed 24,008 unique secrets; AI-related credential leaks climbed 81.5% in that same window [1]. The pattern behind both numbers is the same: we keep handing agents long-lived credentials that outlive the workflows that needed them. Treat it as a storage problem — you will buy a better vault and still lose. It is a governance problem, and it compounds quietly. The fix is two-fold: broker credential use at runtime, and treat agents as first-class principals rather than borrowed credentials.

## Why agent credentials sprawl faster than teams can revoke them

AI infrastructure leaks secrets at five times the rate of the core LLM providers [1]. Read that number slowly; the risk is not in the model itself, it is in the plumbing that connects an agent to your databases, internal APIs, and tooling.

MCP makes that plumbing visible, and the numbers are damning. In its first year of widespread adoption, MCP configuration files alone exposed 24,008 unique secrets [1]. Teams embedded credentials straight into tool configs, committed them, and moved on to the next integration. Nobody came back to audit what they left behind.

Most teams cannot answer the simplest question: how many secrets do our agents actually hold right now?

That 24,008 figure is a floor, not the full sprawl; it counts secrets sitting in plaintext config files but not the ones a team already rotated out or tucked into a second system. The true inventory is larger. Almost nobody holds a complete view of it.

The 81.5% year-over-year jump in AI credential leaks tells the same story from a different angle [1]. The problem is not that agents need credentials; it is that every new tool integration quietly mints another standing key. That key quietly outlives its purpose. Multiply the pattern by a growing fleet, and the surface you must track outpaces any team's ability to review it.

Agents break the traditional IAM model for a concrete reason: they are non-deterministic. A static API key might be reused across unrelated workflows, then passed downstream to a sub-agent or an external tool (often one you have never heard of). Issue it once — and it becomes an invisible dependency chain you can no longer trace end to end.

{{< figure src="/images/posts/2026-08-28-agent-identities-first-class-principals-nhi-governance/image-1.jpg" alt="Secret sprawl: a single brass key fracturing into diverging cracks, symbolizing one shared credential fanning out across multiple agent workflows with no central view" caption="One shared credential fanning out across multiple agent workflows" >}}

## From a shared service account to a first-class principal

A service account is a shared resource: an application borrows a credential, and rarely does anyone ask which part of the application actually used it. Agents make that model untenable. A single key now fans out across dozens of autonomous decision points with no single owner in charge.

The alternative is to treat each agent as a first-class principal with its own identity record. That record has four parts. Give the agent a unique service principal (distinct from every other workload); attach a human sponsor, a named person who can be reached when the agent misbehaves. Scope permissions through entitlement-managed access packages that come up for periodic review, and inherit policy through the sponsor's risk posture rather than granting the agent a blank check.

The sponsor is the part most teams skip, which is a mistake: it is the part that matters most. A unique identity tells you what acted; a named human tells you who answers for it. Skip the sponsor — and an agent that keeps running after its owner leaves becomes orphaned. Orphaned agents are exactly how standing credentials outlive the people who issued them.

## Runtime credential governance: why a better vault is not the answer

The NHI Management Group names the discipline precisely: runtime credential governance is controlling agent access at the moment of use, instead of assuming pre-provisioned secrets are sufficient [1]. That distinction matters more than it first appears.

A secret sitting in a vault is still a standing credential; storing it safely does nothing about what happens the instant an agent presents it. The shift that matters (the one most teams have not made) is from storage-centric thinking to action-centric thinking. It changes where you spend your hours.

> [!WARNING]
> A vault encrypts a credential at rest, but the moment an agent uses it, the vault is out of the picture. If you only secure storage, you are still blind to how the credential is exercised in practice.

The same group is blunt about what changes: the important architectural shift is not just storing secrets centrally, but brokering how an agent exercises that access [1]. Storage is the easy half. Brokering the actual use is where governance happens, and its absence is what lands teams in an incident.

## Federated token exchange: how to delete the long-lived credential

The cleanest way to stop credential sprawl is to stop issuing standing credentials at all; Microsoft's Workload Identity Federation points at the pattern [3]. A workload exchanges an existing token from an external identity provider for a short-lived access token; it never manages a secret of its own.

Concretely, a user-assigned managed identity or an app registration can be configured to trust tokens issued by GitHub, Google Cloud, or AWS [3]. The agent presents its external token, and the platform swaps it for a scoped, expiring token bound to the current session. The long-lived secret does not exist to begin with.

```mermaid
flowchart LR
    A[Agent] --> H[Host environment]
    H --> E[Token exchange]
    E --> P[External IdP token]
    P --> C[Short-lived access token]
    C --> T[Protected resource]
```

> [!TIP]
> Short-lived tokens reset the compromise window: a stolen key that was valid for months now expires in minutes, and it revokes itself without anyone filing a ticket or remembering to rotate it.

This is the just-in-time (JIT) model applied to identity, and it is the strongest answer to sprawl we have. With no long-lived secret left on disk or in config, there is nothing to leak, rotate, or orphan. The trade-off is real, though: you must stand up the trust relationship first, and every exchange adds a moving part to your incident path.

## The four layers that broker access instead of just storing it

Effective agent identity governance is not one tool; the NHI Management Group structures it across four layers, and the ordering is deliberate [1]. Skip a layer and the one above it quietly fails.

| Layer | Function | What it looks like in practice |
| --- | --- | --- |
| Discovery | Find every agent and its credentials across environments | Inventory of agents, keys, and MCP configs |
| Storage | Hold credentials outside [agent configurations](/posts/2026-05-22-agents-md-self-describing-repositories/) | Centralized vault or secrets manager |
| Brokerage | Mediate agent access with policy enforcement | Policy gateway that approves or blocks each use |
| Audit | Keep immutable logs of what agents did | SIEM and cloud-native audit services |

Discovery and storage are table stakes; most teams already run some version of both. Brokerage is the layer they skip, and it is the one that turns a passive vault into active governance. Audit closes the loop, but only if the logs are immutable enough to survive the incident they are meant to explain. Treat discovery as an ongoing crawl, not a one-time scan, because the agent fleet changes weekly.

{{< key-takeaway >}}
Brokering is the whole point. Discovery tells you what exists, storage keeps it safe, audit tells you what happened — but only brokerage controls what an agent is allowed to do at the exact moment it tries.
{{< /key-takeaway >}}

## What S&P Global and Natoma get right about brokered access

Natoma and 1Password partnered to ship a working version of this model [2], and the pattern is direct. Organizations connect their 1Password vault to Natoma; credentials stay in the vault rather than in code. When an agent needs access, Natoma retrieves the secret reference at runtime and brokers the interaction with the target system.

The policy controls are what turn this from a convenience into governance: read-only database access, write-operation blocking, query rate limiting, and scope-by-user-group permissions [2]. An agent gets exactly the access the policy allows, and nothing more.

Ravi Chinni, Global Head of IAM at S&P Global, frames the endgame clearly: as [AI agents](/posts/2026-07-24-rotunda-agent-native-browser/) become more embedded in enterprise operations, organizations will need interoperable approaches that bring together credential protection, policy governance, and auditability across platforms [2]. It is a coordination problem more than a tooling problem.

{{< figure src="/images/posts/2026-08-28-agent-identities-first-class-principals-nhi-governance/image-2.jpg" alt="Secret sprawl flow: a single brass key radiates copper wires to seven tarnished nodes, symbolizing one shared API key fanning out across agent workflows with no central view." caption="One key, seven paths: how a single credential leaks across agent workflows." >}}

The lesson here is not the specific vendor pair; it is that brokered access, enforced at the point of use, is a pattern teams can adopt today with the secrets tooling they already run. Waiting for a full platform migration is how these programs stall. The smaller win is available now.

## Practical Takeaways

1. Inventory your agent credentials first: find every API key and MCP config embedded in code before you change anything.
2. Move credentials out of agent configs into a centralized store, but treat storage as the starting point, not the finish line.
3. Attach a named human sponsor to every agent identity so there is always someone accountable when access needs review or revocation.
4. Add a brokerage layer that enforces policy at the moment of use, so read-only or rate-limited access is a configured rule rather than a hope.
5. Adopt federated token exchange where your cloud provider supports it, so agents exchange short-lived tokens instead of carrying standing secrets.
6. Turn on immutable audit logging for agent actions before you scale, so every access can be traced back to a specific agent and sponsor.

## Conclusion

The teams that pull ahead here are not the ones with the most elaborate secret stores; they are the ones who learned to retire the standing secret entirely. What the current tooling still will not show you is whether a delegated request can carry authorization that nobody downstream actually granted. Until that chain of custody is settled, a quiet gap stays open. Begin now: put a policy gate in front of one system, and measure how many old keys you retire this quarter.

## Frequently Asked Questions

### Is a password manager enough for agent credentials?

No. A password manager protects credentials at rest, but the real problem is how an agent uses them at runtime. You need runtime credential governance, not just storage.

### What is the difference between secret storage and runtime credential governance?

Secret storage keeps a credential somewhere safe until it is needed, and that is where it stops. Runtime credential governance controls the credential at the exact moment an identity uses it, brokering each request and writing an audit record rather than assuming a pre-provisioned secret is fine [1]. Storage is necessary but insufficient; the decision that [actually matters](/posts/2026-03-06-benchmarking-ai-agents-production/) is made in the brokerage layer, when the agent asks to read a table or call an API, not at rest in the vault.

### Should we adopt workload identity federation right away?

It depends on your cloud posture. Federation removes the long-lived secret and is the cleanest fix, but it requires trust configuration between your platform and an external identity provider. We have not seen clean production guidance on how agent-to-agent delegation behaves under federation, so pilot it on one workload and measure before you roll it out broadly.

### How do we find agent credentials we did not know we had?

Start with discovery: scan for API keys and MCP config files across your repos and environments. The four-layer model puts discovery first for a reason, see the layers table above. We do not have clean production data on total sprawl, so treat any single scan as a lower bound rather than a complete inventory.

---

## Sources

| # | Publisher | Title | URL | Date | Type |
| --- | --- | --- | --- | --- | --- |
| 1 | NHI Management Group | "AI Agent Credentials Need Runtime Governance, Not Embedded Secrets" | https://nhimg.org/articles/ai-agent-credentials-need-runtime-governance-not-embedded-secrets/ | 2026-04-02 | Blog |
| 2 | 1Password | "Natoma + 1Password: Scale Enterprise AI" | https://1password.com/blog/natoma-1password-scale-enterprise-ai | 2026-04-02 | Blog |
| 3 | Microsoft | "Workload Identity Federation - Microsoft Learn" | https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation | undated | Documentation |

## Image Credits

- **Cover photo**: Image generated with gemini-3-pro-image (Agents' Codex AI illustration)
- **Figure 1**: Image generated with gemini-3-pro-image (Agents' Codex AI illustration)
- **Figure 2**: Image generated with gemini-3-pro-image (Agents' Codex AI illustration)
