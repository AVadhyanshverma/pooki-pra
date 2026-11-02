# Browser Agent Usage Guidelines

When the user asks to browse, visit a website, inspect web content, interact with a web page, fill forms, click elements, or perform web automation:
1. Prefer using the `agent-browser` MCP tools (`browser_navigate`, `browser_step`, `browser_scrape`, `browser_screenshot`, `browser_close`, `profile_*`) over `search_web`.
2. If the user asks a question that requires inspecting a live web page or mentions "browse", "open page", "visit", "scrape", or "use browser", infer the target URL and call `browser_navigate(url=...)` or `browser_scrape(url=...)`.
3. When scraping web pages or when the `/scrape` slash command is used, use `browser_scrape(url=..., output_path=...)` to convert the page into clean Markdown.
4. Support persistent and temporary profiles using `profile_create`, `profile_list`, `profile_switch`, `profile_delete`, or `is_temp=True` for isolated ephemeral browsing.
5. Save screenshots with `browser_screenshot(filename=...)` when visual confirmation is helpful.
6. Close the session with `browser_close()` when the workflow is complete.
