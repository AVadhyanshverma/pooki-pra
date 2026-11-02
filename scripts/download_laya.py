#!/usr/bin/env python3
import os
import sys
from huggingface_hub import hf_hub_download

REPO_ID = "cklxx/laya-browser"
LOCAL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laya-model"))

NEEDED_FILES = [
    "config.json",
    "encoder/config.json",
    "model.safetensors",
    "modeling_laya_browser.py",
    "laya_browser.py",
    "rl_agent_config.json",
    "tokenizer/tokenizer.json",
    "tokenizer/tokenizer_config.json"
]

def main():
    os.makedirs(LOCAL_DIR, exist_ok=True)
    print(f"Target directory: {LOCAL_DIR}")
    print(f"Downloading {len(NEEDED_FILES)} required files from {REPO_ID}...\n")
    
    for filename in NEEDED_FILES:
        print(f"Fetching: {filename} ...", end=" ", flush=True)
        try:
            dest = hf_hub_download(
                repo_id=REPO_ID,
                filename=filename,
                local_dir=LOCAL_DIR,
                local_dir_use_symlinks=False
            )
            size_mb = os.path.getsize(dest) / (1024 * 1024)
            print(f"DONE ({size_mb:.2f} MB)")
        except Exception as e:
            print(f"FAILED: {e}")
            sys.exit(1)
            
    print("\nAll necessary model files downloaded successfully into laya-model/")

if __name__ == "__main__":
    main()
