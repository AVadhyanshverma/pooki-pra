import re
from pathlib import Path
from typing import Dict, Any, List

class MarkdownFormatter:
    """Formats structured DOM blocks into clean GitHub Flavored Markdown."""

    @staticmethod
    def format(data: Dict[str, Any]) -> str:
        title = data.get("title", "Untitled").strip()
        url = data.get("url", "")
        scraped_at = data.get("scraped_at", "")
        blocks = data.get("blocks", [])

        # Count total words
        text_corpus = " ".join(b.get("text", "") for b in blocks if "text" in b)
        word_count = len(text_corpus.split())
        reading_time = max(1, round(word_count / 200))

        # Build YAML Frontmatter
        lines = [
            "---",
            f"title: \"{title.replace('\"', '\\\"')}\"",
            f"url: \"{url}\"",
            f"scraped_at: \"{scraped_at}\"",
            f"word_count: {word_count}",
            f"reading_time_min: {reading_time}",
            "---",
            "",
            f"# {title}",
            "",
            f"> Source: [{url}]({url}) | Scraped: {scraped_at[:10]}",
            ""
        ]

        for b in blocks:
            b_type = b.get("type")
            if b_type == "heading":
                prefix = "#" * min(6, max(1, b.get("level", 2)))
                lines.append(f"{prefix} {b.get('text', '')}\n")
            elif b_type == "paragraph":
                lines.append(f"{b.get('text', '')}\n")
            elif b_type == "code":
                lang = b.get("language", "")
                code = b.get("text", "")
                lines.append(f"```{lang}\n{code}\n```\n")
            elif b_type == "quote":
                lines.append(f"> {b.get('text', '')}\n")
            elif b_type == "list":
                ordered = b.get("ordered", False)
                items = b.get("items", [])
                for idx, itm in enumerate(items):
                    pfx = f"{idx + 1}." if ordered else "*"
                    lines.append(f"{pfx} {itm}")
                lines.append("")
            elif b_type == "table":
                rows: List[List[str]] = b.get("rows", [])
                if rows:
                    # Format as GFM pipe table
                    col_count = max(len(r) for r in rows)
                    # Normalize row widths
                    norm_rows = [r + [""] * (col_count - len(r)) for r in rows]
                    # Header
                    header = norm_rows[0]
                    lines.append("| " + " | ".join(header) + " |")
                    lines.append("| " + " | ".join(["---"] * col_count) + " |")
                    for r in norm_rows[1:]:
                        lines.append("| " + " | ".join(r) + " |")
                    lines.append("")

        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def save(markdown_text: str, title: str, dest_dir: Path, requested_path: str = "") -> Path:
        """Saves markdown to disk, handling slugification and collision avoidance."""
        dest_dir.mkdir(parents=True, exist_ok=True)

        if requested_path:
            target = Path(requested_path).expanduser().resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(markdown_text, encoding="utf-8")
            return target

        # Generate slugified filename from title
        clean_slug = re.sub(r"[^\w\s-]", "", title).strip().lower()
        slug = re.sub(r"[-\s]+", "-", clean_slug)[:60].strip("-") or "page"

        target = dest_dir / f"{slug}.md"
        counter = 1
        while target.exists():
            target = dest_dir / f"{slug}-{counter}.md"
            counter += 1

        target.write_text(markdown_text, encoding="utf-8")
        return target
