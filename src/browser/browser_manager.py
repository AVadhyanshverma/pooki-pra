import os
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from src.storage.db import DatabaseManager
from src.browser.profile_manager import ProfileManager
from src.browser.markdown_formatter import MarkdownFormatter

class BrowserManager:
    """
    Manages Camoufox stealth browser sessions with SQLite session audit logging,
    persistent and temporary profile isolation, and in-browser markdown scraping.
    """
    def __init__(self, headless: bool = True, profile_name: Optional[str] = None, is_temp: bool = False):
        self.headless = headless
        self.profile_name = profile_name
        self.is_temp = is_temp
        
        self.db = DatabaseManager()
        self.profile_mgr = ProfileManager(db=self.db)
        
        self.session_uuid = str(uuid.uuid4())
        self.step_counter = 0
        
        self._camoufox_ctx = None
        self._browser = None
        self._page = None
        self._active_profile_path = None
        
        # Load DOM extractor JS
        dom_script_path = os.path.join(os.path.dirname(__file__), "dom_extractor.js")
        with open(dom_script_path, "r", encoding="utf-8") as f:
            self._dom_extractor_script = f.read()

        # Load Scraper JS
        scraper_script_path = os.path.join(os.path.dirname(__file__), "scraper_extractor.js")
        with open(scraper_script_path, "r", encoding="utf-8") as f:
            self._scraper_script = f.read()

    def start(self):
        """Starts the Camoufox browser session with persistent or temporary profile."""
        if self._page is not None:
            return
            
        from camoufox.sync_api import Camoufox
        
        # Determine profile path
        if self.is_temp:
            temp_meta = self.profile_mgr.create_temp_profile()
            self.profile_name = temp_meta["name"]
            self._active_profile_path = Path(temp_meta["path"])
        elif self.profile_name:
            p = self.profile_mgr.get_profile_path(self.profile_name)
            if not p:
                meta = self.profile_mgr.create_profile(self.profile_name)
                p = Path(meta["path"])
            self._active_profile_path = p
        else:
            # Check if an active profile is set in SQLite
            active = self.db.get_active_profile()
            if active and not active.get("is_temp"):
                self.profile_name = active["name"]
                self._active_profile_path = Path(active["path"])
                
        # Launch Camoufox
        if self._active_profile_path:
            self._active_profile_path.mkdir(parents=True, exist_ok=True)
            self._camoufox_ctx = Camoufox(
                headless=self.headless,
                persistent_context=True,
                user_data_dir=str(self._active_profile_path),
                os="linux"
            )
            # persistent_context returns a BrowserContext directly
            context = self._camoufox_ctx.__enter__()
            self._browser = context
            if len(context.pages) > 0:
                self._page = context.pages[0]
            else:
                self._page = context.new_page()
        else:
            self._camoufox_ctx = Camoufox(headless=self.headless, os="linux")
            self._browser = self._camoufox_ctx.__enter__()
            self._page = self._browser.new_page()
            
        self._page.set_viewport_size({"width": 1280, "height": 800})
        self.db.start_session(self.session_uuid, self.profile_name or "default", initial_url="")

    def navigate(self, url: str) -> Dict[str, Any]:
        """Navigates to URL and returns the parsed DOM observation."""
        self.start()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
            
        try:
            self._page.goto(url, wait_until="networkidle", timeout=15000)
        except Exception:
            try:
                self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
            except Exception:
                pass
                
        time.sleep(1.0) # Settle dynamic SPA scripts
        obs = self.get_observation()
        
        # Log to SQLite
        self.step_counter += 1
        self.db.record_action(
            session_uuid=self.session_uuid,
            step_idx=self.step_counter,
            url=obs.get("url", url),
            title=obs.get("title", ""),
            operation="NAVIGATE",
            target_element=url,
            confidence=1.0,
            latency_ms=0.0
        )
        return obs

    def get_observation(self) -> Dict[str, Any]:
        """Runs the DOM extractor on the active page."""
        self.start()
        obs = self._page.evaluate(self._dom_extractor_script)
        return obs

    def execute_action(self, operation: str, action: Optional[Dict[str, Any]], fill_text: Optional[str] = None) -> bool:
        """Executes the System 1 decision on the page and logs to SQLite."""
        self.start()
        success = False
        target_label = action.get("label") if action else None
        
        if operation == "SCROLL_DOWN":
            self._page.evaluate("window.scrollBy({top: 600, behavior: 'smooth'})")
            time.sleep(0.5)
            success = True
            
        elif operation == "SCROLL_UP":
            self._page.evaluate("window.scrollBy({top: -600, behavior: 'smooth'})")
            time.sleep(0.5)
            success = True
            
        elif operation in ("DONE", "BLOCKED", "WAIT"):
            if operation == "WAIT":
                time.sleep(2.0)
            success = True

        elif action and "id" in action:
            agent_id = action["id"]
            selector = f"[data-agent-id='{agent_id}']"
            locator = self._page.locator(selector).first

            if operation == "CLICK":
                locator.scroll_into_view_if_needed(timeout=5000)
                locator.click(timeout=5000)
                time.sleep(1.0)
                success = True

            elif operation == "TYPE_TEXT":
                locator.scroll_into_view_if_needed(timeout=5000)
                locator.click(timeout=5000)
                if fill_text is not None:
                    locator.fill(fill_text, timeout=5000)
                time.sleep(0.5)
                success = True

            elif operation == "SELECT":
                val = action.get("value", "")
                locator.select_option(val)
                time.sleep(0.5)
                success = True

        # Log action to SQLite
        self.step_counter += 1
        curr_url = self._page.url if self._page else ""
        curr_title = self._page.title() if self._page else ""
        self.db.record_action(
            session_uuid=self.session_uuid,
            step_idx=self.step_counter,
            url=curr_url,
            title=curr_title,
            operation=operation,
            target_element=target_label,
            confidence=1.0,
            latency_ms=0.0
        )
        return success

    def scrape(self, mode: str = "readability", output_path: str = "", dest_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Extracts content from active page, converts to Markdown, saves to disk,
        and logs to SQLite.
        """
        self.start()
        # Set window.__scrape_mode
        self._page.evaluate(f"window.__scrape_mode = '{mode}';")
        extracted_val = self._page.evaluate(self._scraper_script)
        if isinstance(extracted_val, str):
            import json
            extracted = json.loads(extracted_val)
        else:
            extracted = extracted_val
        
        md_text = MarkdownFormatter.format(extracted)
        target_dir = dest_dir or (Path.cwd() / "scrapes")
        saved_file = MarkdownFormatter.save(
            markdown_text=md_text,
            title=extracted.get("title", "page"),
            dest_dir=target_dir,
            requested_path=output_path
        )
        
        word_count = len(md_text.split())
        self.db.record_scrape(
            url=extracted.get("url", self._page.url),
            title=extracted.get("title", ""),
            file_path=str(saved_file),
            word_count=word_count,
            profile_name=self.profile_name or "default"
        )
        
        return {
            "title": extracted.get("title"),
            "url": extracted.get("url"),
            "file_path": str(saved_file),
            "word_count": word_count,
            "markdown_snippet": md_text[:500] + ("..." if len(md_text) > 500 else "")
        }

    def screenshot(self, output_path: str) -> str:
        """Saves a screenshot of the current page."""
        self.start()
        self._page.screenshot(path=output_path)
        return output_path

    def close(self):
        """Closes browser context and cleans up ephemeral profiles."""
        try:
            if self._page:
                self._page.close()
            if self._camoufox_ctx:
                self._camoufox_ctx.__exit__(None, None, None)
            self.db.end_session(self.session_uuid, status="completed")
        finally:
            self._page = None
            self._browser = None
            self._camoufox_ctx = None
            if self.is_temp:
                self.profile_mgr.cleanup_temp_profiles()
