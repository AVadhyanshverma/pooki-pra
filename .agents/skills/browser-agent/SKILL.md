---
name: browser-agent
description: High-performance, anti-detect browser automation using Camoufox and Laya System-1 decision head.
---

# Browser Agent Skill

This skill allows Antigravity to command a stealth browser driven by Camoufox and the Laya decision model.

## Architecture

- **Strategic Planning (System 2)**: Antigravity handles high-level intent, decomposition into navigation milestones, content interpretation, and error recovery.
- **Fast Reflex Action Decision (System 1)**: The local Laya ONNX decision model scores and chooses candidate DOM elements and operations (`CLICK`, `TYPE_TEXT`, `SELECT`, `SCROLL`, `DONE`) in ~15–35ms.
- **Stealth Engine**: Camoufox wipes automation fingerprints (`navigator.webdriver = false` at C++ level) to bypass Cloudflare, DataDome, and anti-bot systems.

---

## How Instructions Work (System 2 to System 1)

Laya is a non-autoregressive decision model. It does not generate creative text; it **ranks and scores offered options** against a specific goal.

### 1. Atomic Sub-Goals
Never give Laya open-ended essays. Break the user's overall goal into concise, atomic navigation milestones:
* **Good**: `"Search for 'tokio' on crates.io"`
* **Good**: `"Click on the repository link"`
* **Good**: `"Select 'Documentation' from the navigation bar"`
* **Bad**: `"Browse the internet and tell me the history of Rust"`

### 2. Dual-Brain Interaction Loop
```
User Prompt: "Find the latest version of axum on crates.io"
  │
  ├── 1. Antigravity: Calls `browser_navigate("https://crates.io")`
  │      └── Returns page elements & title
  │
  ├── 2. Antigravity: Calls `browser_step(goal="Search for 'axum'", fill_text="axum")`
  │      └── Laya decides: TYPE_TEXT on #search_input
  │      └── Camoufox fills "axum" into input field
  │
  ├── 3. Antigravity: Calls `browser_step(goal="Submit search")`
  │      └── Laya decides: CLICK on submit button
  │      └── Camoufox clicks button, page navigates
  │
  ├── 4. Antigravity: Calls `browser_step(goal="Open package axum")`
  │      └── Laya decides: CLICK on first result link
  │
  └── 5. Antigravity: Reads page text from observation, extracts version, returns answer to User.
```

---

## Available MCP Tools

- `browser_navigate(url)`: Opens a URL in Camoufox and returns page interactable elements.
- `browser_step(goal, fill_text)`: Evaluates the page with Laya to choose and execute the next micro-action.
- `browser_screenshot(filename)`: Captures a PNG screenshot for multimodal inspection.
- `browser_close()`: Closes the browser session and frees resources.
