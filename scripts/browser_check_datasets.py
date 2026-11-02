#!/usr/bin/env python3
"""
Executes the dataset search and README check using Camoufox + Laya Browser Agent.
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
    print("=== Browser Agent Live Session ===")
    
    engine = LayaEngine()
    browser = BrowserManager(headless=True)
    history = []
    
    try:
        # Step 1: Navigate to Profile
        profile_url = "https://huggingface.co/AdhyanshVerma"
        print(f"\n[Turn 1] Navigating to {profile_url}...")
        obs = browser.navigate(profile_url)
        print(f"Page Title: {obs.get('title')}")
        print(f"Discovered {len(obs.get('actions', []))} interactable elements.")
        
        # Step 2: Ask Laya to click on Datasets tab / section
        goal1 = "Click on the Datasets tab or view all datasets"
        print(f"\n[Turn 2] System 2 Goal: {goal1}")
        decision1 = engine.decide(obs, goal=goal1, history=history)
        
        op1 = decision1["operation"]
        act1 = decision1.get("action")
        print(f"Laya Decision: {op1} on '{act1.get('label') if act1 else None}' (Confidence: {decision1['confidence']*100:.1f}%)")
        
        # Execute click on Datasets tab
        browser.execute_action(op1, act1)
        history.append({"action": act1.get("label", op1) if act1 else op1, "kind": "click", "page_changed": True})
        time.sleep(2.0)
        
        # Step 3: Get updated observation on Datasets page
        obs_datasets = browser.get_observation()
        print(f"\n[Turn 3] Current URL: {obs_datasets.get('url')}")
        print(f"Discovered {len(obs_datasets.get('actions', []))} elements on datasets page.")
        
        # Search page text for dataset names & download counts visible on screen
        page_text = obs_datasets.get("text", "")
        print(f"Visible page text snippet: {page_text[:400]}...")
        
        # Step 4: Ask Laya to click on the top dataset (YT)
        goal2 = "Click on the dataset 'AdhyanshVerma/YT' with most downloads"
        print(f"\n[Turn 4] System 2 Goal: {goal2}")
        decision2 = engine.decide(obs_datasets, goal=goal2, history=history)
        
        op2 = decision2["operation"]
        act2 = decision2.get("action")
        print(f"Laya Decision: {op2} on '{act2.get('label') if act2 else None}' (Confidence: {decision2['confidence']*100:.1f}%)")
        
        browser.execute_action(op2, act2)
        history.append({"action": act2.get("label", op2) if act2 else op2, "kind": "click", "page_changed": True})
        time.sleep(2.0)
        
        # Step 5: On the dataset page, check for README
        obs_yt = browser.get_observation()
        print(f"\n[Turn 5] Landed on: {obs_yt.get('url')}")
        print(f"Page Title: {obs_yt.get('title')}")
        
        # Inspect page text for README / card content
        yt_text = obs_yt.get("text", "")
        has_readme = "Dataset card" in yt_text or "README" in yt_text
        print("\n--- Browser Evaluation of Dataset Page ---")
        print(f"Full visible text excerpt:\n{yt_text[:600]}")
        
        # Step 6: Capture proof screenshot
        pics_dir = Path.home() / "Pictures"
        pics_dir.mkdir(parents=True, exist_ok=True)
        proof_path = pics_dir / "AdhyanshVerma_YT_dataset_browser.png"
        browser.screenshot(str(proof_path))
        print(f"\nCaptured browser proof screenshot to: {proof_path}")
        
    finally:
        browser.close()
        print("Browser session closed cleanly.")

if __name__ == "__main__":
    main()
