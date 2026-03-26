#!/usr/bin/env python3
"""Post-process RSS feed to replace mermaid blocks with pre-rendered SVG images.

Reads public/index.xml, finds <pre class="mermaid"> and <div class="mermaid">
blocks, replaces them with <img> tags pointing to pre-rendered SVGs.

Usage:
  python3 scripts/patch-rss-mermaid.py [--rss public/index.xml] [--base-url https://agentscodex.com]
"""

import argparse
import re
import sys
from pathlib import Path


def extract_slug_from_link(item_text: str) -> str:
    """Extract article slug from <link> element in RSS item."""
    m = re.search(r"<link>(https?://[^<]+/posts/([^/<]+)/?)</link>", item_text)
    if m:
        return m.group(2).rstrip("/")
    return ""


def patch_rss(rss_path: str, base_url: str, svg_dir: str) -> int:
    """Replace mermaid blocks in RSS with img tags. Returns count of replacements."""
    rss_file = Path(rss_path)
    if not rss_file.exists():
        print(f"ERROR: {rss_path} not found", file=sys.stderr)
        return 0

    content = rss_file.read_text(encoding="utf-8")

    # Track per-slug mermaid block index
    slug_counters: dict[str, int] = {}
    replacements = 0

    def replace_mermaid(match: re.Match) -> str:
        nonlocal replacements
        tag = match.group(1)  # "pre" or "div"
        mermaid_code = match.group(2)

        # Find which slug this belongs to by searching backward for <link>
        pos = match.start()
        preceding = content[:pos]
        link_matches = list(re.finditer(r"<link>https?://[^<]+/posts/([^/<]+)/?</link>", preceding))
        if not link_matches:
            return match.group(0)  # Can't determine slug, leave as-is

        slug = link_matches[-1].group(1).rstrip("/")
        idx = slug_counters.get(slug, 0)
        slug_counters[slug] = idx + 1

        svg_path = Path(svg_dir) / f"{slug}-{idx}.svg"
        if not svg_path.exists():
            # No pre-rendered SVG, leave as-is
            return match.group(0)

        img_url = f"{base_url.rstrip('/')}/images/mermaid/{slug}-{idx}.svg"
        replacements += 1
        return f'<img src="{img_url}" alt="Diagram" style="max-width:100%;height:auto;" />'

    # Match both <pre class="mermaid">...</pre> and <div class="mermaid">...</div>
    # These appear inside CDATA sections in RSS
    pattern = r"<(pre|div) class=\"mermaid\">\s*(.*?)\s*</\1>"
    content = re.sub(pattern, replace_mermaid, content, flags=re.DOTALL)

    rss_file.write_text(content, encoding="utf-8")
    return replacements


def main():
    parser = argparse.ArgumentParser(description="Patch RSS feed: replace mermaid with SVG images")
    parser.add_argument("--rss", default="public/index.xml", help="Path to RSS file")
    parser.add_argument("--base-url", default="https://agentscodex.com", help="Site base URL")
    parser.add_argument("--svg-dir", default="static/images/mermaid", help="Directory with pre-rendered SVGs")
    args = parser.parse_args()

    count = patch_rss(args.rss, args.base_url, args.svg_dir)
    print(f"Patched {count} mermaid block(s) in {args.rss}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
