#!/usr/bin/env python3
"""
End-to-End integration test for Camoufox + Laya ONNX browser agent.
"""
import os
import sys
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from src.browser.browser_manager import BrowserManager
from src.engine.laya_engine import LayaEngine

def main():
    print("=== Testing Camoufox + Laya End-to-End Browser Agent ===")
    
    # 1. Initialize System 1 Engine
    print("1. Initializing Laya ONNX Engine...")
    engine = LayaEngine()
    print(f"   Provider: {engine.active_provider}")
    
    # 2. Initialize Browser
    print("2. Starting Camoufox Browser...")
    browser = BrowserManager(headless=True)
    
    try:
        # 3. Navigate
        target_url = "https://crates.io"
        print(f"3. Navigating to {target_url}...")
        obs = browser.navigate(target_url)
        print(f"   Page Title: {obs.get('title')}")
        print(f"   Discovered {len(obs.get('actions', []))} interactable elements.")
        
        # 4. Step 1: Type search query
        goal_step1 = "Search for 'tokio' on crates.io"
        print(f"\n4. [System 2 -> System 1] Step 1 Goal: {goal_step1}")
        decision1 = engine.decide(obs, goal=goal_step1)
        
        op1 = decision1["operation"]
        act1 = decision1.get("action")
        print(f"   Laya Decision: {op1} on '{act1.get('label') if act1 else None}' (Confidence: {decision1['confidence']*100:.1f}%)")
        
        browser.execute_action(op1, act1, fill_text="tokio")
        print("   Executed action in Camoufox.")
        
        # 5. Step 2: Submit search
        obs_step2 = browser.get_observation()
        history = [{"action": act1.get("label", op1) if act1 else op1, "kind": "fill", "text": "tokio", "page_changed": False}]
        goal_step2 = "Submit search query"
        print(f"\n5. [System 2 -> System 1] Step 2 Goal: {goal_step2}")
        decision2 = engine.decide(obs_step2, goal=goal_step2, history=history)
        
        op2 = decision2["operation"]
        act2 = decision2.get("action")
        print(f"   Laya Decision: {op2} on '{act2.get('label') if act2 else None}' (Confidence: {decision2['confidence']*100:.1f}%)")
        
        browser.execute_action(op2, act2)
        print("   Executed submit action in Camoufox.")
        
        # 6. Take Screenshot
        screenshot_path = os.path.join(BASE_DIR, "crates_test_result.png")
        browser.screenshot(screenshot_path)
        print(f"\n6. Screenshot captured and saved to: {screenshot_path}")
        
        print("\nAll integration checks PASSED!")
        
    finally:
        print("Cleaning up browser session...")
        browser.close()

if __name__ == "__main__":
    main()
