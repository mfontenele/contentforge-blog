# AGENTS.md — contentforge-blog

This repository contains the Hugo source for [agentscodex.com](https://agentscodex.com),
a technical blog about AI agent operations, LLM cost optimization, and multi-agent architecture.
Posts are authored by autonomous agents and merged by a human reviewer.

---

## Build & Preview

```bash
# Install Hugo (extended) if needed
sudo apt install hugo        # Debian/Ubuntu
brew install hugo            # macOS

# Start local dev server (live reload)
hugo server -D

# Production build (output to ./public/)
hugo --minify
```

The site is deployed automatically via GitHub Actions on every merge to `main`.
**Never run `hugo` to deploy manually** — always go through PR → merge.

---

## Repository Structure

```
contentforge-blog/
├── .github/workflows/deploy.yml   ← GitHub Actions: build + deploy to Pages
├── config.toml                    ← Hugo config (baseURL, theme, params)
├── content/
│   ├── posts/                     ← All blog articles live here
│   ├── about.md
│   └── privacy.md
├── static/
│   └── images/                    ← Post images (referenced in frontmatter)
└── themes/
    └── PaperMod/                  ← Git submodule — do not edit directly
```

---

## Adding a Post

All posts go in `content/posts/` with the naming convention:

```
YYYY-MM-DD-slug-in-lowercase-hyphen.md
```

Example: `2025-03-04-mcp-protocol-deep-dive.md`

### Required Frontmatter

Every post must include this frontmatter block:

```yaml
---
title: "Full Article Title Here"
date: YYYY-MM-DDT06:00:00-03:00
draft: false
description: "One-sentence summary for SEO meta description (120–155 chars)."
tags: ["tag-one", "tag-two", "tag-three"]
categories: ["AI Agents"]
author: "Agents Codex"
showToc: true
TocOpen: false
cover:
  image: ""
  alt: ""
  caption: ""
---
```

### Quality Floor

Every article must meet these minimums before being merged:

| Criterion | Minimum |
|---|---|
| H2 sections | ≥ 5 |
| Primary sources cited | ≥ 3 |
| Numeric data points | ≥ 5 |
| Real-world examples (companies, products, case studies) | ≥ 2 |
| Word count (body, excluding frontmatter) | 1500–2000 |

---

## Affiliate Links

- Maximum **4 affiliate links per article**
- All affiliate links must include `rel="sponsored"` and UTM parameters
- Format: `https://example.com?utm_source=agentscodex&utm_medium=affiliate&utm_campaign=slug`
- Do not hardcode affiliate URLs — the Writer agent reads `AFFILIATE-REGISTRY.md` from its workspace

---

## Git Workflow

**Never commit directly to `main`.** All posts arrive via pull request from the publisher agent.

Branch naming convention:
```
post/YYYY-MM-DD-article-slug
```

Commit convention:
```
feat(content): add post - Article Title Here
```

PRs are reviewed and merged by the human maintainer. GitHub Actions builds and deploys on merge.

---

## Conventions

- **Language:** English only. All posts, frontmatter, and commit messages in English.
- **Theme:** PaperMod — do not modify files inside `themes/PaperMod/`. Override via `layouts/` at root.
- **Images:** Place in `static/images/`. Reference in frontmatter as `/images/filename.jpg`.
- **Submodule:** If cloning fresh, run `git submodule update --init --recursive` to pull PaperMod.
- **Drafts:** `draft: true` posts are excluded from production builds. Use for WIP only.

---

## What Not to Do

- **NEVER** commit directly to `main`
- **NEVER** modify files inside `themes/PaperMod/`
- **NEVER** include API keys, tokens, or secrets in any file
- **NEVER** set `draft: false` on a post that hasn't passed the Quality Floor
- **NEVER** add more than 4 affiliate links per article
