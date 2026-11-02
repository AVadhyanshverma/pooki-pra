#!/usr/bin/env bash
# ==============================================================================
# Pooki-Pra: Universal Setup & Installer Script
# Author: Adhyansh Verma
# ==============================================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "       ___          _    _     ___             "
echo "      / _ \___  ___| | _(_)___/ _ \_ __ __ _   "
echo "     / /_)/ _ \/ _ \ |/ / /___/ /_)/ '__/ _\` |  "
echo "    / ___/ (_) \__ \   <| |  / ___/| | | (_| |  "
echo "    \/    \___/|___/_|\_\_|  \/    |_|  \__,_|  "
echo "    High-Performance Anti-Detect Browser Agent  "
echo -e "${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DEST="$HOME/.local/bin"
mkdir -p "$BIN_DEST"

# 1. Build or Install Native Rust Binary
echo -e "${YELLOW}[1/5] Setting up native Rust binary (pooki-pra)...${NC}"
if [ -d "$SCRIPT_DIR/crates/pooki-pra" ] && command -v cargo &>/dev/null; then
    echo "Compiling pooki-pra release binary from source..."
    (cd "$SCRIPT_DIR/crates/pooki-pra" && cargo build --release)
    install -m 755 "$SCRIPT_DIR/crates/pooki-pra/target/release/pooki-pra" "$BIN_DEST/pooki-pra"
else
    echo "Checking for pre-compiled binary..."
    if [ -f "$SCRIPT_DIR/crates/pooki-pra/target/release/pooki-pra" ]; then
        install -m 755 "$SCRIPT_DIR/crates/pooki-pra/target/release/pooki-pra" "$BIN_DEST/pooki-pra"
    else
        echo "Attempting to download pre-built release binary..."
        OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
        ARCH="$(uname -m)"
        TARBALL="pooki-pra-${OS}-${ARCH}.tar.gz"
        RELEASE_URL="https://github.com/AVadhyanshverma/pooki-pra/releases/latest/download/${TARBALL}"
        curl -fsSL "$RELEASE_URL" -o "/tmp/${TARBALL}" || true
        if [ -f "/tmp/${TARBALL}" ]; then
            tar -xzf "/tmp/${TARBALL}" -C "/tmp/"
            install -m 755 "/tmp/pooki-pra" "$BIN_DEST/pooki-pra"
            rm -f "/tmp/${TARBALL}" "/tmp/pooki-pra"
        fi
    fi
fi

chmod +x "$BIN_DEST/pooki-pra"
echo -e "${GREEN}✓ Binary installed to: $BIN_DEST/pooki-pra${NC}"

# 2. Check PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo -e "${YELLOW}Note: Add ~/.local/bin to your PATH in ~/.bashrc or ~/.zshrc:${NC}"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# 3. Model Weights Verification
echo -e "\n${YELLOW}[2/5] Verifying neural decision weights...${NC}"
mkdir -p "$SCRIPT_DIR/laya"
MODEL_FILE="$SCRIPT_DIR/laya/model_edge_int8.onnx"
if [ ! -f "$MODEL_FILE" ] && [ ! -f "$SCRIPT_DIR/laya/model.onnx" ]; then
    echo "Fetching Ultra-Edge INT8 weights (310 MB) from Hugging Face..."
    curl -fL --progress-bar "https://huggingface.co/AdhyanshVerma/browser-laya-onnx/resolve/main/model_int8.onnx" \
        -o "$MODEL_FILE"
    ln -sf "model_edge_int8.onnx" "$SCRIPT_DIR/laya/model.onnx"
    echo -e "${GREEN}✓ INT8 Model weights downloaded successfully.${NC}"
else
    if [ ! -f "$SCRIPT_DIR/laya/model.onnx" ] && [ -f "$MODEL_FILE" ]; then
        ln -sf "model_edge_int8.onnx" "$SCRIPT_DIR/laya/model.onnx"
    fi
    echo -e "${GREEN}✓ Model weights verified.${NC}"
fi

# 4. Anti-Detect Engine (Camoufox)
echo -e "\n${YELLOW}[3/5] Verifying Camoufox anti-detect engine...${NC}"
CAMOU_DIR="$HOME/.cache/camoufox/browsers/official"
CAMOU_BIN=$(find "$CAMOU_DIR" -name "camoufox-bin" 2>/dev/null | head -n 1)

if [ -n "$CAMOU_BIN" ] && [ -x "$CAMOU_BIN" ]; then
    echo -e "${GREEN}✓ Camoufox stealth browser detected at: $CAMOU_BIN${NC}"
else
    echo "Camoufox stealth browser not found. Auto-fetching official release..."
    OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
    ARCH="$(uname -m)"
    
    case "$OS" in
        linux*)   CAMOU_OS="lin" ;;
        darwin*)  CAMOU_OS="mac" ;;
        msys*|mingw*|cygwin*) CAMOU_OS="win" ;;
        *)        CAMOU_OS="lin" ;;
    esac
    
    case "$ARCH" in
        x86_64|amd64) CAMOU_ARCH="x86_64" ;;
        aarch64|arm64) CAMOU_ARCH="arm64" ;;
        *)             CAMOU_ARCH="x86_64" ;;
    esac

    VERSION="158.0.1-beta.41"
    ZIP_NAME="camoufox-${VERSION}-${CAMOU_OS}.${CAMOU_ARCH}.zip"
    DOWNLOAD_URL="https://github.com/daijro/camoufox/releases/download/v${VERSION}/${ZIP_NAME}"
    TARGET_DIR="$CAMOU_DIR/${VERSION}"

    mkdir -p "$TARGET_DIR"
    echo "Downloading ${ZIP_NAME} from GitHub..."
    TMP_ZIP="/tmp/${ZIP_NAME}"
    curl -fL --progress-bar "$DOWNLOAD_URL" -o "$TMP_ZIP"
    
    echo "Extracting into $TARGET_DIR..."
    if command -v unzip &>/dev/null; then
        unzip -q -o "$TMP_ZIP" -d "$TARGET_DIR"
    else
        python3 -m zipfile -e "$TMP_ZIP" "$TARGET_DIR"
    fi
    rm -f "$TMP_ZIP"
    
    chmod +x "$TARGET_DIR/camoufox" "$TARGET_DIR/camoufox-bin" 2>/dev/null || true
    echo -e "${GREEN}✓ Camoufox anti-detect engine installed successfully.${NC}"
fi

# 5. Global SQLite Database Setup
echo -e "\n${YELLOW}[4/5] Initializing SQLite central store...${NC}"
mkdir -p "$HOME/.local/share/pooki-pra"
"$BIN_DEST/pooki-pra" --help > /dev/null 2>&1 || true
echo -e "${GREEN}✓ SQLite database configured at: $HOME/.local/share/pooki-pra/pooki_pra.db${NC}"

# 6. Global MCP Server Registration
echo -e "\n${YELLOW}[5/5] Registering MCP Server with Antigravity / Claude Code...${NC}"
GLOBAL_CONFIG="$HOME/.gemini/config/mcp_config.json"
mkdir -p "$(dirname "$GLOBAL_CONFIG")"

# Update mcp_config.json
python3 -c "
import json, os
path = os.path.expanduser('$GLOBAL_CONFIG')
data = {'mcpServers': {}}
if os.path.exists(path) and os.path.getsize(path) > 0:
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        pass
data.setdefault('mcpServers', {})['pooki-pra'] = {
    'command': '$BIN_DEST/pooki-pra',
    'args': ['mcp']
}
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
"

# Copy global plugin skills
PLUGIN_DIR="$HOME/.gemini/config/plugins/pooki-pra"
mkdir -p "$PLUGIN_DIR/skills/scrape" "$PLUGIN_DIR/rules"
cp "$SCRIPT_DIR/.agents/skills/scrape/SKILL.md" "$PLUGIN_DIR/skills/scrape/SKILL.md" 2>/dev/null || true
cp "$SCRIPT_DIR/.agents/rules/AGENTS.md" "$PLUGIN_DIR/rules/AGENTS.md" 2>/dev/null || true

echo -e "${GREEN}✓ Registered globally in $GLOBAL_CONFIG${NC}"

echo -e "\n${CYAN}================================================================${NC}"
echo -e "${GREEN}🎉 Pooki-Pra installation is complete and ready to rock!${NC}"
echo -e "${CYAN}================================================================${NC}"
echo -e "Try it right now:"
echo -e "    ${YELLOW}pooki-pra navigate https://crates.io/crates/tokio${NC}"
echo -e "    ${YELLOW}pooki-pra scrape https://crates.io/crates/tokio${NC}"
echo -e "Or in Antigravity / Claude Code:"
echo -e "    ${YELLOW}/scrape https://crates.io/crates/tokio${NC}\n"
