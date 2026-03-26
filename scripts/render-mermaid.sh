#!/usr/bin/env bash
# Pre-render mermaid diagrams from markdown files to SVG.
# Output: static/images/mermaid/<slug>-<N>.svg
# Called during CI build before Hugo.
set -uo pipefail

POSTS_DIR="${1:-content/posts}"
OUTPUT_DIR="static/images/mermaid"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PUPPETEER_CFG="$SCRIPT_DIR/puppeteer-config.json"
mkdir -p "$OUTPUT_DIR"

rendered=0

for md_file in "$POSTS_DIR"/*.md; do
  [ -f "$md_file" ] || continue

  slug=$(basename "$md_file" .md)

  # Extract mermaid blocks (both ```mermaid and {{< mermaid >}} syntaxes)
  # Uses awk to find and extract each block
  idx=0
  in_block=false
  block_content=""

  while IFS= read -r line; do
    # Start of ```mermaid block
    if [[ "$line" =~ ^\`\`\`mermaid ]]; then
      in_block=true
      block_content=""
      continue
    fi

    # Start of {{< mermaid >}} block
    if [[ "$line" =~ \{\{.*mermaid.*\}\} ]] && [[ ! "$line" =~ /mermaid ]]; then
      in_block=true
      block_content=""
      continue
    fi

    # End of ```mermaid block
    if $in_block && [[ "$line" =~ ^\`\`\` ]]; then
      in_block=false
      if [ -n "$block_content" ]; then
        svg_path="$OUTPUT_DIR/${slug}-${idx}.svg"
        tmp_file=$(mktemp /tmp/mermaid-XXXXXX.mmd)
        printf '%s\n' "$block_content" > "$tmp_file"
        if mmdc -i "$tmp_file" -o "$svg_path" -t neutral -p "$PUPPETEER_CFG" --quiet 2>/dev/null; then
          echo "  Rendered: $svg_path"
          rendered=$((rendered + 1))
        else
          echo "  WARN: Failed to render $svg_path" >&2
        fi
        rm -f "$tmp_file"
        idx=$((idx + 1))
      fi
      continue
    fi

    # End of {{< /mermaid >}} block
    if $in_block && [[ "$line" =~ \{\{.*\/mermaid.*\}\} ]]; then
      in_block=false
      if [ -n "$block_content" ]; then
        svg_path="$OUTPUT_DIR/${slug}-${idx}.svg"
        tmp_file=$(mktemp /tmp/mermaid-XXXXXX.mmd)
        printf '%s\n' "$block_content" > "$tmp_file"
        if mmdc -i "$tmp_file" -o "$svg_path" -t neutral -p "$PUPPETEER_CFG" --quiet 2>/dev/null; then
          echo "  Rendered: $svg_path"
          rendered=$((rendered + 1))
        else
          echo "  WARN: Failed to render $svg_path" >&2
        fi
        rm -f "$tmp_file"
        idx=$((idx + 1))
      fi
      continue
    fi

    # Accumulate block content
    if $in_block; then
      if [ -z "$block_content" ]; then
        block_content="$line"
      else
        block_content="$block_content
$line"
      fi
    fi
  done < "$md_file"
done

echo "Rendered $rendered mermaid diagrams to $OUTPUT_DIR/"
