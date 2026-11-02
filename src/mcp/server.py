import os
import sys
import json
from typing import Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BASE_DIR)

from src.browser.browser_manager import BrowserManager
from src.browser.profile_manager import ProfileManager
from src.storage.db import DatabaseManager
from src.engine.laya_engine import LayaEngine
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("agent-browser")

_browser: Optional[BrowserManager] = None
_engine: Optional[LayaEngine] = None
_db = DatabaseManager()
_profile_mgr = ProfileManager(db=_db)
_history = []

def get_browser(profile_name: Optional[str] = None, is_temp: bool = False) -> BrowserManager:
    global _browser
    if _browser is None or (_browser.profile_name != profile_name and profile_name is not None) or (_browser.is_temp != is_temp and is_temp):
        if _browser is not None:
            _browser.close()
        _browser = BrowserManager(headless=True, profile_name=profile_name, is_temp=is_temp)
    return _browser

def get_engine() -> LayaEngine:
    global _engine
    if _engine is None:
        _engine = LayaEngine()
    return _engine

# --- Browser & Navigation Tools ---

@mcp.tool()
def browser_navigate(url: str, profile_name: str = "", is_temp: bool = False) -> str:
    """
    Navigates Camoufox stealth browser to a URL using a persistent or temporary profile.
    Returns page summary, title, and interactable elements.
    """
    global _history
    _history = []
    p_name = profile_name if profile_name else None
    b = get_browser(profile_name=p_name, is_temp=is_temp)
    obs = b.navigate(url)
    return json.dumps({
        "url": obs.get("url"),
        "title": obs.get("title"),
        "profile": b.profile_name,
        "is_temp": b.is_temp,
        "text_summary": obs.get("text", "")[:400],
        "interactable_elements_count": len(obs.get("actions", [])),
        "sample_actions": obs.get("actions", [])[:15]
    }, indent=2)

@mcp.tool()
def browser_step(goal: str, fill_text: str = "") -> str:
    """
    Prompts Laya System 1 decision engine on the current page to perform the next action towards the goal.
    """
    global _history
    b = get_browser()
    e = get_engine()
    
    obs = b.get_observation()
    decision = e.decide(obs, goal=goal, history=_history)
    
    op = decision["operation"]
    act = decision.get("action")
    
    text_val = fill_text if fill_text else (act.get("value") if act else "")
    success = b.execute_action(op, act, fill_text=text_val)
    
    history_entry = {
        "action": act.get("label", op) if act else op,
        "kind": act.get("kind", op.lower()) if act else op.lower(),
        "text": text_val,
        "page_changed": True
    }
    _history.append(history_entry)
    
    new_obs = b.get_observation()
    
    return json.dumps({
        "operation": op,
        "target_element": act.get("label") if act else None,
        "target_id": act.get("id") if act else None,
        "confidence": round(decision["confidence"] * 100, 1),
        "executed": success,
        "latency_ms": decision["latency_ms"],
        "new_url": new_obs.get("url"),
        "new_title": new_obs.get("title"),
        "recent_action_history": _history[-5:]
    }, indent=2)

@mcp.tool()
def browser_scrape(url: str = "", mode: str = "readability", output_path: str = "") -> str:
    """
    Converts a web page into clean, readable Markdown (.md), saves to disk,
    and logs metadata in SQLite. If url is provided, navigates first; otherwise scrapes current page.
    """
    b = get_browser()
    if url:
        b.navigate(url)
    res = b.scrape(mode=mode, output_path=output_path)
    return json.dumps(res, indent=2)

@mcp.tool()
def browser_screenshot(filename: str = "browser_snapshot.png") -> str:
    """
    Captures a screenshot of the current page and returns the absolute file path.
    """
    b = get_browser()
    dest_path = os.path.join(BASE_DIR, filename) if not os.path.isabs(filename) else filename
    b.screenshot(dest_path)
    return f"Screenshot saved to: {dest_path}"

@mcp.tool()
def browser_close() -> str:
    """
    Closes the active Camoufox browser session and cleans up temporary profiles.
    """
    global _browser
    if _browser is not None:
        _browser.close()
        _browser = None
    return "Browser session closed successfully."

# --- Profile Management Tools ---

@mcp.tool()
def profile_list() -> str:
    """
    Lists all browser profiles stored in SQLite with disk size, temp status, and last used timestamp.
    """
    profiles = _profile_mgr.list_profiles()
    return json.dumps({"profiles": profiles}, indent=2)

@mcp.tool()
def profile_create(name: str, copy_from: str = "", notes: str = "") -> str:
    """
    Creates a new persistent profile. Optional copy_from clones existing profile data.
    """
    from_name = copy_from if copy_from else None
    prof = _profile_mgr.create_profile(name, copy_from=from_name, notes=notes)
    return json.dumps({"status": "created", "profile": prof}, indent=2)

@mcp.tool()
def profile_delete(name: str, force: bool = False) -> str:
    """
    Deletes a profile from disk and SQLite.
    """
    deleted = _profile_mgr.delete_profile(name, force=force)
    return json.dumps({"name": name, "deleted": deleted}, indent=2)

@mcp.tool()
def profile_switch(name: str) -> str:
    """
    Switches the active profile in SQLite for subsequent browser sessions.
    """
    global _browser
    if _browser is not None:
        _browser.close()
        _browser = None
    prof = _profile_mgr.switch_profile(name)
    return json.dumps({"status": "switched", "active_profile": prof}, indent=2)

@mcp.tool()
def session_history(limit: int = 15) -> str:
    """
    Queries SQLite for recent browser navigation, actions, and scraping logs.
    """
    actions = _db.get_recent_actions(limit=limit)
    scrapes = _db.list_scrapes(limit=limit)
    return json.dumps({
        "recent_actions": actions,
        "recent_scrapes": scrapes
    }, indent=2)

if __name__ == "__main__":
    mcp.run(transport="stdio")
