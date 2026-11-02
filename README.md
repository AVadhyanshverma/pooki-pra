# Pooki-Pra (ぷきプラ)
### High-Performance Anti-Detect Browser Agent System
**Powered by Camoufox C++ Engine, W3C WebDriver BiDi WebSockets, and Laya Neural Decision Heads**

[![Rust](https://img.shields.io/badge/rust-1.80%2B-orange.svg)](https://www.rust-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Camoufox](https://img.shields.io/badge/Engine-Camoufox%20158.0-red.svg)](https://github.com/daijro/camoufox)
[![ONNX](https://img.shields.io/badge/Decision%20Head-Laya%20ONNX-blueviolet.svg)](https://huggingface.co/cklxx/laya-browser)
[![Author](https://img.shields.io/badge/Author-Adhyansh%20Verma-brightgreen.svg)](https://huggingface.co/AdhyanshVerma)

---

```
       ___          _    _     ___             
      / _ \___  ___| | _(_)___/ _ \_ __ __ _   
     / /_)/ _ \/ _ \ |/ / /___/ /_)/ '__/ _` |  
    / ___/ (_) \__ \   <| |  / ___/| | | (_| |  
    \/    \___/|___/_|\_\_|  \/    |_|  \__,_|  
    High-Performance Anti-Detect Browser Agent
```

**Pooki-Pra** is an open-source, anti-detect browser automation framework purpose-built for autonomous AI agents. Unlike standard Selenium or Playwright setups, Pooki-Pra integrates engine-level C++ stealth patches, native W3C WebSocket BiDi protocols, sub-second Rust executions, and local neural reflex decision models.

---

## 🌟 Key Features

* **Anti-Detect Stealth**: Powered by Camoufox (C++ engine-level patched Firefox). `navigator.webdriver = false`, genuine desktop font catalogs (2.1 GB cross-platform masking), WebRTC IP suppression, and WebGL noise.
* **Direct WebSocket BiDi**: Connects directly to Firefox's asynchronous W3C WebDriver BiDi protocol (`ws://127.0.0.1:<port>/session`). Zero `geckodriver` and zero Node.js bridges.
* **Dual-System Architecture**:
  * **System 2 (Executive Planner)**: Antigravity / Claude / GPT models decompose tasks.
  * **System 1 (Neural Reflex)**: Fine-tuned ModernBERT decision model running locally in ONNX (~18 ms CUDA / ~45 ms CPU).
* **Ultra-Edge Quantization**: Includes a **310 MB INT8 model** (`model_edge_int8.onnx`) running fast on any CPU or edge device.
* **In-Browser Markdown Scraper (`/scrape`)**: Extracts live computed DOM content, strips ads/banners, and formats clean GitHub Flavored Markdown with YAML frontmatter.
* **Centralized SQLite Engine**: Manages persistent profiles, ephemeral `--temp` sandboxes, and audit logs in `~/.local/share/pooki-pra/pooki_pra.db`.
* **Universal Cross-Agent Compatibility**: First-class Model Context Protocol (MCP) server for Antigravity, Claude Code, Cursor, and Windsurf.

---

## ⚡ Quickstart

### 1. One-Click Universal Install
```bash
git clone https://github.com/AVadhyanshverma/pooki-pra.git
cd pooki-pra
./install.sh
```

### 2. Standalone CLI Usage
```bash
# Navigate to any website
pooki-pra navigate https://crates.io/crates/tokio

# Convert any webpage/SPA to clean Markdown
pooki-pra scrape https://crates.io/crates/tokio --output ./tokio.md

# Capture viewport screenshot
pooki-pra screenshot https://crates.io/crates/tokio ./shot.png
```

### 3. Antigravity Slash Command
In the Antigravity CLI (`agy`), simply type:
```text
/scrape https://crates.io/crates/tokio
```

---

## 📖 Architecture & Documentation

For a comprehensive guide covering browser fingerprinting internals, WebSocket BiDi protocol packets, tensor dimensions, and agent integration, read the official handbook:

👉 **[The Pooki-Pra Architecture & Operator's Handbook](docs/BOOK.md)**

---

## 🤖 Interoperability with Other Agents

### Claude Code
```bash
claude mcp add pooki-pra -- ~/.local/bin/pooki-pra mcp
```

### Cursor & Windsurf (`mcp.json`)
```json
{
  "mcpServers": {
    "pooki-pra": {
      "command": "pooki-pra",
      "args": ["mcp"]
    }
  }
}
```

---

## 📜 License
Licensed under the [MIT License](LICENSE). Copyright (c) 2026 [Adhyansh Verma](https://huggingface.co/AdhyanshVerma).
