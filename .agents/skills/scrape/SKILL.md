---
name: scrape
description: Converts any web page or article into clean GitHub Flavored Markdown (.md) using the Camoufox browser agent, handles interactive file path saving, and records metadata in SQLite.
---

# Web Page Scraper to Markdown (`/scrape`)

Use this skill when the user triggers `/scrape` or asks to convert a web page, article, documentation, or blog post into Markdown (`.md`).

## Command Syntax
```text
/scrape <url> [output_path] [--full] [--profile=<name>]
```

## Workflow Instructions

1. **URL & Parameters**:
   - Extract the target `url` from the user's message.
   - If an `output_path` is specified (e.g. `./docs/page.md`), use it.
   - If no `output_path` is specified:
     - Suggest the default path: `./scrapes/<slugified_title>.md`.
     - You can ask or immediately save to `./scrapes/<slugified_title>.md` and provide a clickable file link.
   - Determine `mode`: `"readability"` by default (strips ads, navbars, footers, cookie banners); `"full"` if the user asked for full page content.

2. **Call `browser_scrape`**:
   - Invoke `browser_scrape(url=..., mode=..., output_path=...)`.
   - The tool executes inside Camoufox, converts tables to GFM pipe format, formats codeblocks, extracts YAML frontmatter, saves the file to disk, and indexes the scrape in SQLite.

3. **Report to User**:
   - Provide a clickable markdown link to the saved file: `[<filename>](file:///absolute/path/to/file.md)`.
   - Report statistics: Word count, estimated reading time, and an excerpt of the extracted content.
