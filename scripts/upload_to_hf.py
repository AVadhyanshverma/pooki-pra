#!/usr/bin/env python3
"""
Uploads the Pooki-Pra Laya ONNX models (Full FP32 + Ultra-Edge INT8)
to Hugging Face Hub under the user's account.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LAYA_DIR = BASE_DIR / "laya"

def main():
    print("=== Pooki-Pra Model Exporter & Hugging Face Uploader ===")

    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError:
        print("Error: huggingface_hub not installed. Run: pip install huggingface_hub")
        sys.exit(1)

    api = HfApi()
    token = os.environ.get("HF_TOKEN") or api.token
    if not token:
        print("\n⚠️ No Hugging Face token detected.")
        print("Please log in using:")
        print("    huggingface-cli login")
        print("or set the environment variable:")
        print("    export HF_TOKEN=\"hf_...\"")
        print("\nThen re-run this script!")
        sys.exit(1)

    user = api.whoami(token=token)
    username = user["name"]
    repo_id = f"{username}/pooki-pra-laya-onnx"

    print(f"\nTarget Repository: https://huggingface.co/{repo_id}")
    confirm = input(f"Create/Upload to {repo_id}? (y/N): ").strip().lower()
    if confirm != "y":
        print("Upload cancelled.")
        return

    print(f"Creating repository {repo_id} (if not already existing)...")
    create_repo(repo_id=repo_id, repo_type="model", exist_ok=True, token=token)

    # Generate Model Card README
    model_card = f"""---
language:
- en
license: mit
tags:
- onnx
- browser-agent
- laya
- pooki-pra
- web-navigation
- edge-ai
pipeline_tag: text-classification
---

# Pooki-Pra: Laya Decision Head (ONNX + Ultra-Edge INT8)

This repository hosts the optimized ONNX exports of the **Laya System-1 Reflex Model** for browser automation, developed as part of the **Pooki-Pra** anti-detect AI browser engine.

## Model Variants

| Variant | Filename | Size | Target Environment | Latency |
| :--- | :--- | :--- | :--- | :--- |
| **Full Precision (FP32)** | `model.onnx` + `model.onnx.data` | 1.28 GB | Desktop GPU (NVIDIA CUDA / TensorRT) | ~18 ms |
| **Ultra-Edge (INT8)** | `model_edge_int8.onnx` | 310 MB | Edge / CPU / Laptops / Raspberry Pi | ~45 ms |

## Input & Output Specification

### Inputs
* `input_ids` `[batch, seq_len]`: Tokenized DOM and goal sequence.
* `attention_mask` `[batch, seq_len]`: Self-attention binary mask.
* `marker_pos` `[batch, num_markers]`: Position index of `[mask]` action candidate tokens.
* `marker_mask` `[batch, num_markers]`: Valid candidate element mask.
* `qtype` `[batch]`: Query task type identifier.

### Outputs
* `masked_fill_2` `[batch, num_markers]`: Unnormalized action logits for candidate DOM elements.

## Fast Inference Example (Python)

```python
import onnxruntime as ort

# Load Ultra-Edge INT8 model (310 MB)
session = ort.InferenceSession("model_edge_int8.onnx", providers=["CPUExecutionProvider"])
# Run forward pass
outputs = session.run(None, inputs)
```

## Part of Pooki-Pra
* Browser Engine: Camoufox (Stealth C++ Firefox)
* Protocol: Native W3C WebDriver BiDi WebSockets
* Author: [Adhyansh Verma](https://huggingface.co/AdhyanshVerma)
"""

    card_path = LAYA_DIR / "README.md"
    card_path.write_text(model_card, encoding="utf-8")

    print(f"\nUploading model artifacts to {repo_id}...")
    api.upload_folder(
        folder_path=str(LAYA_DIR),
        repo_id=repo_id,
        repo_type="model",
        token=token
    )

    print(f"\n🎉 Successfully uploaded to: https://huggingface.co/{repo_id}")

if __name__ == "__main__":
    main()
