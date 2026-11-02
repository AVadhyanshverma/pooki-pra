#!/usr/bin/env python3
"""
Find and screenshot AdhyanshVerma's Hugging Face profile using Camoufox & Laya.
"""
import os
import sys
import time
from pathlib import Path

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from src.browser.browser_manager import BrowserManager
from src.engine.laya_engine import LayaEngine

def main():
    print("=== Browser Agent: Finding Hugging Face Profile ===")
    
    # 1. Initialize Engine & Browser
    print("Initializing Laya Decision Engine...")
    engine = LayaEngine()
    
    print("Starting Camoufox Stealth Browser...")
    browser = BrowserManager(headless=True)
    
    pictures_dir = Path.home() / "Pictures"
    pictures_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = pictures_dir / "AdhyanshVerma_hf.png"
    
    try:
        # 2. Navigate to profile
        profile_url = "https://huggingface.co/AdhyanshVerma"
        print(f"Navigating to {profile_url}...")
        obs = browser.navigate(profile_url)
        
        print(f"Page Title: {obs.get('title')}")
        print(f"Discovered {len(obs.get('actions', []))} interactable elements.")
        print(f"Page Summary: {obs.get('text', '')[:300]}...")
        
        # 3. Use Laya to evaluate current profile state
        goal = "Confirm user profile of AdhyanshVerma"
        decision = engine.decide(obs, goal=goal)
        print(f"\nLaya Assessment:")
        print(f" - Operation: {decision['operation']}")
        print(f" - Confidence: {decision['confidence'] * 100:.1f}%")
        
        # Allow any avatar / models grid images to fully finish rendering
        time.sleep(2.0)
        
        # 4. Capture screenshot into ~/Pictures
        print(f"\nCapturing screenshot to: {screenshot_path}...")
        browser.screenshot(str(screenshot_path))
        
        size_kb = screenshot_path.stat().st_size / 1024
        print(f"Screenshot successfully saved! ({size_kb:.1f} KB)")
        
    finally:
        browser.close()
        print("Browser session closed cleanly.")

if __name__ == "__main__":
    main()
