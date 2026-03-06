---
title: "SKILLs vs MCP: Why Declarative Agent Configuration is Winning Over Protocol-Based Integration"
date: 2026-03-05T06:00:00-03:00
categories: ["AI Engineering", "Agent Architecture"]
tags: ["SKILL.md", "agent skills", "MCP alternative", "agent configuration", "OpenClaw", "declarative AI"]
keywords: ["SKILL.md", "agent skills", "MCP alternative", "agent configuration", "OpenClaw", "declarative AI"]
description: "MCP's USB-C analogy sounds perfect—but the reality involves JSON-RPC servers, stateful sessions, and infrastructure overhead. Here's why a simple markdown file often beats a protocol-based approach."
cover:
  image: "/images/skills-vs-mcp-cover.jpg"
  alt: "Declarative vs Protocol-Based Agent Configuration"
  caption: "Declarative configuration trades protocol overhead for simplicity"
  relative: false
---

The USB-C analogy for MCP is brilliant marketing. One universal port that connects everything—databases, IDEs, browsers, SaaS tools—to any AI agent that speaks the protocol. Anthropic's Model Context Protocol promises to eliminate the N×M integration nightmare, replacing it with elegant N+M connectivity where N agents plug into M servers through a single standard.

But here's what the marketing doesn't emphasize: USB-C cables don't require you to run a local server, negotiate stateful sessions, or debug JSON-RPC error codes at 2 AM. MCP does.

For many real-world use cases, a YAML file with markdown instructions beats a protocol-based client-server architecture. The emerging SKILL.md pattern proves it. While MCP adoption accelerates with OpenAI and Google DeepMind integrations in 2025, teams are discovering that declarative agent configuration offers a faster path to value—especially when your "integration" is primarily about encoding procedural knowledge rather than connecting to external systems.

This article examines both approaches honestly. MCP solves real problems for real scenarios. But so does SKILL.md, and understanding when each fits will save you from architectural overkill that slows down teams rather than empowering them.

## The Two Paths: Declarative vs Protocol-Based Configuration

Agent configuration today splits into two fundamentally different philosophies. Understanding this distinction clears up most confusion about when to use which approach.

**SKILL.md takes a declarative approach.** You write a YAML frontmatter block describing the skill's metadata—name, description, parameters—followed by markdown instructions telling the agent exactly how to behave. The file lives on the filesystem. The agent reads it when needed. No servers spin up. No sockets open. No protocols negotiate capabilities.

**MCP takes a protocol-based approach.** You build a server implementing the MCP specification. It speaks JSON-RPC 2.0 over stdio or HTTP. Clients maintain stateful 1:1 connections to servers. Capability negotiation happens at connection time. Every tool invocation traverses this protocol stack.

The difference isn't cosmetic—it changes who owns the complexity. With SKILL.md, complexity lives in the agent's implementation. With MCP, complexity lives in your infrastructure.

Here's what a simple SKILL.md file looks like:

```yaml
---
skill:
  name: code_review
  description: Review code changes for quality, security, and maintainability
  params:
    files:
      type: array
      description: List of file paths to review
      required: true
    focus:
      type: string
      description: Specific area to focus on (security, performance, readability)
      default: general
---

## Instructions

When reviewing code:
1. Check for obvious security issues (SQL injection, XSS, hardcoded secrets)
2. Verify error handling exists and is appropriate
3. Look for test coverage of critical paths
4. Flag overly complex functions (>50 lines)
5. Suggest specific improvements, not vague criticisms

## Examples

**Good feedback:** "The `userInput` parameter isn't sanitized before being passed to `exec()`. Use parameterized queries instead."

**Bad feedback:** "This seems insecure."
```

The entire skill is self-contained in a single human-readable file. Git tracks every change. Rollbacks require nothing more than `git checkout`. No deployment pipeline. No health checks. No authentication configuration.

Compare this with MCP's architecture. To expose that same code review capability via MCP, you'd need:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "code_review",
    "arguments": {
      "files": ["src/auth.js", "src/api.js"],
      "focus": "security"
    }
  }
}
```

But that JSON-RPC message only works after:

1. Building and running an MCP server process
2. Establishing a stateful client-server connection
3. Completing capability negotiation
4. Implementing proper error handling for transport failures
5. Managing session lifecycle and reconnection logic

Both approaches accomplish similar goals—but one adds layers of infrastructure between your intent and the result. The declarative path asks: "What do you want the agent to do?" The protocol path asks: "How will you connect the agent to do it?" That framing difference shapes everything that follows.

The declarative approach treats skills as data. The protocol approach treats capabilities as services. Data is easier to version, inspect, and reason about. Services require operational expertise and ongoing maintenance. Neither is inherently superior, but they serve different needs and impose different costs.

## MCP's Hidden Complexity Tax

The N+M promise of MCP is genuine. When you have twenty different agents needing database access, MCP eliminates twenty separate database integrations. Each agent connects to one MCP server; the server manages database connectivity. The math works.

What the math hides is the operational cost of that abstraction.

**Session lifecycle management** becomes your problem. MCP connections are stateful. Each client maintains an active session with its server. When connections drop—and they will—you handle reconnection logic, state reconciliation, and error propagation. In production, this means health checks, circuit breakers, and graceful degradation strategies that didn't exist in your architecture before MCP.

**JSON-RPC overhead** manifests in multiple ways. Every tool call serializes to JSON, transmits over the wire, deserializes on the server, executes, then reverses the journey. For local stdio transport this overhead is minimal. For HTTP transports—necessary when servers run remotely—it accumulates. Error handling becomes verbose: JSON-RPC errors layer on top of transport errors layer on top of application errors. Debugging requires understanding which layer failed and why.

**Authentication complexity** blocked enterprise adoption through mid-2025. The June 2025 specification formalized MCP servers as OAuth Resource Servers with RFC 8707 Resource Indicators for protection against token mis-redemption. The November 2025 additions included async Tasks, SEP-1024 for consent dialogs on local server installation (preventing silent command execution), and SEP-835 for default OAuth scopes—expanding beyond the baseline OAuth support established earlier in the year.

**Capability negotiation** adds startup latency. Every MCP connection begins with a handshake where client and server exchange supported features. For long-running sessions this cost amortizes away. For short-lived connections—common in serverless environments or batch processing—this negotiation tax hits every single invocation. Teams optimizing for latency find themselves maintaining persistent connection pools, adding yet another operational concern.

**Server sprawl** emerges as adoption grows. Each new capability requires a server process. A typical production deployment might have separate MCP servers for databases, APIs, file systems, and custom business logic. Each needs monitoring, logging, updates, and security patches. The N+M math simplifies integration logic but multiplies operational footprint.

Replit Connectors launched in September-October 2025 with 20+ pre-built integrations (Stripe, Figma, Salesforce, etc.), powered by MCP internally but not exposed as 'MCP integrations' to users. Replit later added custom MCP server support in December 2025, allowing users to connect their own remote MCP servers. The connector platform succeeded because Replit absorbed that complexity. Teams without Replit's engineering resources face it directly.

None of this makes MCP bad. It makes MCP a deliberate architectural choice with understood trade-offs. The complexity exists for reasons: stateful sessions enable sophisticated capability negotiation; JSON-RPC provides transport flexibility; authentication standardization protects enterprise deployments. But those benefits come with costs that marketing materials rarely emphasize.

## The Simplicity of Declarative Skills

If MCP represents the protocol-based extreme, SKILL.md sits at the declarative end of the spectrum. The pattern trades away runtime flexibility for development simplicity, and for many use cases, that's exactly the right trade.

**Progressive disclosure** keeps context windows lean. A SKILL.md file loads only metadata initially—approximately 100 tokens describing the skill's name, description, and parameters. The full instructions, which can run to thousands of tokens depending on complexity, load only when the agent actually needs them. This matters because context window constraints remain the primary bottleneck in agent systems. Loading 100 skills via MCP means maintaining 100 active connections and their associated state. Loading 100 SKILL.md files means keeping ~10,000 tokens of metadata in memory—trivial for modern context windows.

**Git-native versioning** transforms how teams collaborate. Skills live in the repository alongside code. Pull requests review skill changes just like any other file. Rollbacks happen through `git revert`. Branching lets teams experiment with different approaches without affecting production. The entire skill lifecycle aligns with existing development workflows—no separate deployment pipelines, no version drift between code and capabilities.

**Zero infrastructure requirements** remove operational barriers. A SKILL.md file requires no running processes, no ports, no health checks, no connection pooling. It sits on disk waiting to be read. This makes skills infinitely portable: copy a directory of SKILL.md files to any machine with an agent that understands the pattern, and all capabilities transfer instantly. No environment variables to configure. No network policies to manage. No dependencies to install.

**Human readability** enables broader contribution. The YAML frontmatter + Markdown body format is immediately comprehensible to anyone who's worked with Jekyll, Hugo, or modern documentation systems. Junior developers write skills without learning a protocol. Product managers review skill instructions for accuracy. Security teams audit capabilities without parsing JSON-RPC schemas. The barrier to contribution drops to "can you write a markdown file?"

**Composability through the filesystem** offers elegant organization. Skills live in a directory structure that mirrors their purpose. A `skills/code-review/` directory contains review-related capabilities. `skills/security/` holds security-focused checks. Subdirectories organize by team, by domain, by maturity level. The filesystem becomes a natural taxonomy without requiring registry services or discovery protocols.

Claude Code's implementation demonstrates this pattern at scale. The system supports hundreds of skills through progressive disclosure, loading only what's needed when it's needed. Teams report that adding a new skill takes minutes: create the file, commit, push. No server deployments. No connection configuration. No operational review. The simplicity enables experimentation—teams try ideas that would be too expensive to prototype with full MCP infrastructure.

## Production Readiness: The 2025 Turning Point

Both approaches matured significantly throughout 2025, but their trajectories reveal different philosophies about production readiness.

**MCP's enterprise journey** highlights the challenges of protocol standardization. Through mid-2025, enterprise adoption faced significant headwinds. The June 2025 specification formalized MCP servers as OAuth Resource Servers with RFC 8707 Resource Indicators for protection against token mis-redemption. The November 2025 additions included async Tasks, SEP-1024 for consent dialogs on local server installation (preventing silent command execution), and SEP-835 for default OAuth scopes—expanding beyond the baseline OAuth support established earlier in the year.

**Major platform adoption** validated the protocol's trajectory. OpenAI officially adopted MCP in March 2025, integrating it into their agent platform. Google DeepMind announced MCP support for Gemini in April 2025, confirmed by Demis Hassabis. These aren't experimental commitments—they're strategic bets by major players that MCP will dominate external tool integration.

**SKILL.md's production story** is quieter but no less significant. The pattern's maturity comes from simplicity rather than specification evolution. Claude Code's support demonstrates production viability at scale—thousands of developers use SKILL.md daily without incident. The pattern doesn't need OAuth updates because it relies on filesystem permissions. It doesn't need async task infrastructure because the agent controls execution timing. Production readiness emerges from minimal surface area rather than comprehensive specification.

**Security models differ fundamentally.** MCP's protocol-based approach enables sophisticated access control: scoped tokens, per-server permissions, audit logs of every tool invocation. This matters for regulated environments where every database query must be traceable. SKILL.md's filesystem-based approach inherits operating system permissions: if the agent can read the file, it can execute the skill. This simplicity works when teams trust their agent environment; it breaks down when skills need to authenticate to external services or when audit trails are mandatory.

The 2025 turning point isn't that one approach became definitively better. It's that both approaches clarified their production boundaries. MCP addressed enterprise blockers and gained major platform support. SKILL.md proved its simplicity scales without breaking. Teams can now choose based on their actual requirements rather than experimental uncertainty.

## When to Choose Which Approach

The decision between declarative skills and protocol-based MCP isn't about which is better—it's about which fits your constraints.

**Choose MCP when:**

- You're integrating external systems that require real-time data (databases, APIs, SaaS platforms)
- Multiple teams need shared access to the same capabilities with different permission levels
- Audit trails and access logging are non-negotiable requirements
- You have operations expertise to manage server infrastructure
- The N+M integration math genuinely matters for your architecture
- You need capabilities that only exist as MCP servers (increasingly common as the ecosystem grows)

**Choose SKILL.md when:**

- You're encoding procedural knowledge (code review guidelines, deployment procedures, team conventions)
- Rapid iteration matters more than protocol compliance
- You lack operations resources for server management
- Version control integration and rollback simplicity are priorities
- Context window efficiency matters for your agent architecture
- You need capabilities that travel with the codebase (portability between environments)

**Hybrid approaches** are emerging as the practical reality. Many teams use MCP for external tool connectivity while using SKILL.md for usage conventions and context-specific behaviors. An agent might connect to an MCP database server for queries while following SKILL.md instructions for how to structure responses or handle edge cases. This layering plays to each approach's strengths: MCP handles the messy reality of external integration, SKILL.md provides the contextual guidance that makes agents useful rather than merely connected.

The framework for choosing is simpler than it appears. Ask: "Does this capability need to connect to something external, or does it need to guide how the agent thinks?" Connection problems favor MCP. Guidance problems favor SKILL.md. Most real-world agents need both.

## Conclusion

MCP's USB-C analogy captured imaginations for good reason. The N+M integration promise solves a genuine pain point, and the protocol's rapid adoption by OpenAI, Google DeepMind, and platforms like Replit validates its approach. For teams building agents that connect to databases, APIs, and enterprise systems, MCP has become the standard path forward.

But the analogy breaks down in important ways. USB-C cables don't require you to run a server process. They don't need authentication configuration or session management. They don't introduce latency through protocol negotiation. MCP does all of these things, and those costs matter—especially for teams building agent capabilities that don't require external connectivity.

The SKILL.md pattern offers a compelling alternative for these cases. Its declarative approach trades protocol flexibility for development simplicity. Progressive disclosure keeps context windows manageable. Git-native versioning aligns with existing workflows. Zero infrastructure requirements enable rapid experimentation. These advantages make SKILL.md particularly valuable for encoding the procedural knowledge that turns connected agents into useful teammates.

The smartest teams aren't choosing sides—they're choosing both. MCP for external connectivity. SKILL.md for internal guidance. The approaches complement rather than compete. Understanding when each fits separates teams that ship useful agents from those stuck in architectural debates.

The future likely holds convergence. MCP may adopt declarative configuration layers for simpler use cases. SKILL.md implementations may add optional protocol bridges for external connectivity. But today, the practical path is clear: use MCP where its complexity buys you necessary capabilities, use SKILL.md where simplicity accelerates your team, and don't let architectural purity override shipping value.

## Sources

| # | Publisher | Title | Date | Type |
|---|-----------|-------|------|------|
| 1 | Replit | Replit Platform Updates 2025 | 2025-12 | Vendor Documentation |
| 2 | MCP Specification | November 2025 Spec Release Notes | 2025-11-25 | Technical Specification |
| 5 | Claude Code Documentation | SKILL.md Pattern Documentation | 2025 | Vendor Documentation |
| 9 | MCP Blog | First Anniversary Post | 2025-11-25 | Blog Post |
