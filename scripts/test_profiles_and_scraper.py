#!/usr/bin/env python3
"""
End-to-end verification of SQLite storage, Profile Management (persistent & temp),
and Semantic Markdown Scraping.
"""
import os
import sys
import shutil
from pathlib import Path

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from src.storage.db import DatabaseManager
from src.browser.profile_manager import ProfileManager
from src.browser.browser_manager import BrowserManager

def test_all():
    print("=== Testing SQLite, Profiles & Markdown Scraper ===")

    # 1. Test Database
    print("\n[1] Initializing SQLite database...")
    db = DatabaseManager()
    print(f"Database initialized at: {db.db_path}")

    # 2. Test Persistent Profiles
    print("\n[2] Testing ProfileManager (create persistent profile)...")
    pm = ProfileManager(db=db)
    prof = pm.create_profile("test_user_profile", notes="Test profile for verification")
    print(f"Created profile: {prof['name']} at {prof['path']}")
    assert Path(prof['path']).exists(), "Profile path does not exist on disk!"

    profiles = pm.list_profiles()
    print(f"Listed {len(profiles)} profile(s): {[p['name'] for p in profiles]}")

    # 3. Test Ephemeral / Temp Profile
    print("\n[3] Testing Ephemeral (--temp) Profile...")
    temp_prof = pm.create_temp_profile()
    temp_path = Path(temp_prof['path'])
    print(f"Created temp profile: {temp_prof['name']} at {temp_path}")
    assert temp_path.exists(), "Temp profile path does not exist!"
    pm.cleanup_temp_profiles()
    assert not temp_path.exists(), "Temp profile was not cleaned up!"
    print("Temp profile cleaned up cleanly.")

    # 4. Test In-Browser Markdown Scraping
    print("\n[4] Testing In-Browser Markdown Scraper on live page...")
    target_url = "https://huggingface.co/AdhyanshVerma"
    b = BrowserManager(headless=True, profile_name="test_user_profile")
    try:
        print(f"Navigating to {target_url}...")
        b.navigate(target_url)
        print("Scraping page to markdown...")
        scrape_result = b.scrape(mode="readability")
        print(f"Scraped Title: {scrape_result['title']}")
        print(f"Saved to: {scrape_result['file_path']}")
        print(f"Word Count: {scrape_result['word_count']}")
        print(f"Markdown Excerpt:\n{scrape_result['markdown_snippet'][:300]}")
        
        saved_file = Path(scrape_result['file_path'])
        assert saved_file.exists(), "Scraped markdown file does not exist on disk!"
        content = saved_file.read_text(encoding="utf-8")
        assert "---" in content and "word_count" in content, "Missing frontmatter in markdown!"
        print("Markdown file validation PASSED!")
    finally:
        b.close()

    # 5. Verify SQLite Records
    print("\n[5] Verifying SQLite session and scrape records...")
    scrapes = db.list_scrapes(limit=5)
    print(f"Total recorded scrapes: {len(scrapes)}")
    assert len(scrapes) > 0, "No scrapes recorded in SQLite!"
    print(f"Latest scrape record: {scrapes[0]['url']} -> {scrapes[0]['file_path']}")

    actions = db.get_recent_actions(limit=5)
    print(f"Recorded recent actions: {len(actions)}")
    assert len(actions) > 0, "No actions recorded in SQLite!"

    # 6. Cleanup test profile
    print("\n[6] Cleaning up test profile...")
    pm.delete_profile("test_user_profile", force=True)
    print("Test profile deleted.")

    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_all()
