#!/usr/bin/env python3
"""
Uploads ONLY the INT8 Quantized Laya ONNX model to AdhyanshVerma/browser-laya-onnx
"""
import os
import sys
import shutil
import tempfile
from pathlib import Path
from huggingface_hub import HfApi, create_repo

BASE_DIR = Path(__file__).resolve().parent.parent
LAYA_DIR = BASE_DIR / "laya"

def upload():
    api = HfApi()
    user = api.whoami()
    username = user["name"]
    repo_id = f"{username}/browser-laya-onnx"

    print(f"=== Uploading INT8 Model to Hugging Face ===")
    print(f"Target Repository: https://huggingface.co/{repo_id}")

    # 1. Create Repository if not existing
    create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)
    print("✓ Repository confirmed.")

    # 2. Stage only INT8 files in a clean temporary directory
    with tempfile.TemporaryDirectory() as stage_dir:
        stage = Path(stage_dir)
        print(f"Staging INT8 files into {stage}...")

        # Copy INT8 model
        int8_src = LAYA_DIR / "model_edge_int8.onnx"
        if not int8_src.exists():
            raise FileNotFoundError(f"Missing {int8_src}")

        # In the HF repo, provide it as model_int8.onnx and model.onnx for easy loading
        shutil.copy2(int8_src, stage / "model_int8.onnx")
        shutil.copy2(int8_src, stage / "model.onnx")

        # Copy configs
        for cfg in ["config.json", "rl_agent_config.json"]:
            src = LAYA_DIR / cfg
            if src.exists():
                shutil.copy2(src, stage / cfg)

        # Copy tokenizer
        tok_src = LAYA_DIR / "tokenizer"
        if tok_src.exists():
            shutil.copytree(tok_src, stage / "tokenizer", dirs_exist_ok=True)

        # Generate Model Card
        readme_content = f"""---
language:
- en
license: mit
tags:
- onnx
- int8
- quantization
- browser-agent
- laya
- pooki-pra
- modernbert
- web-navigation
- edge-ai
pipeline_tag: text-classification
---

# Laya Browser Decision Head (Ultra-Edge INT8 ONNX)

This repository provides the official **Ultra-Edge INT8 Quantized ONNX version** of the **Laya System-1 Decision Head** for browser agents, created for the **[Pooki-Pra](https://github.com/AVadhyanshverma/pooki-pra)** anti-detect browser engine.

## Model Highlights

* **Model Architecture**: ModernBERT unpadded sequence classification fine-tuned for DOM action spaces (`CLICK`, `TYPE_TEXT`, `SELECT`, `SCROLL_DOWN`, `SCROLL_UP`, `WAIT`, `DONE`).
* **Quantization**: Dynamic INT8 symmetric quantization (`onnxruntime.quantization.QuantType.QInt8`).
* **Ultra-Lightweight**: **310.1 MB** (over 4x size reduction from the 1.28 GB FP32 model).
* **Zero GPU Required**: Sub-45ms inference on standard x86_64 CPUs, laptops, and ARM edge devices.

## Files in this Repository

| File | Size | Description |
| :--- | :--- | :--- |
| `model.onnx` / `model_int8.onnx` | 310 MB | Self-contained INT8 quantized ONNX decision model |
| `config.json` | 1.8 KB | ModernBERT base configuration |
| `rl_agent_config.json` | 68 B | Reinforcement learning action head mapping |
| `tokenizer/` | Directory | Tokenizer JSON vocabulary (256,000 tokens) |

## Quick Inference Example

```python
import onnxruntime as ort
import numpy as np

# Load the 310 MB INT8 model
session = ort.InferenceSession("model.onnx", providers=["CPUExecutionProvider"])

# Forward pass with dynamic sequence length and action markers
outputs = session.run(None, {{
    "input_ids": input_ids,
    "attention_mask": attention_mask,
    "marker_pos": marker_pos,
    "marker_mask": marker_mask,
    "qtype": qtype
}})
action_logits = outputs[0]
```

## Part of Pooki-Pra
* Developed by [Adhyansh Verma](https://huggingface.co/AdhyanshVerma).
* Designed for [Pooki-Pra](https://github.com/AVadhyanshverma/pooki-pra) & [Camoufox](https://github.com/daijro/camoufox).
"""
        (stage / "README.md").write_text(readme_content, encoding="utf-8")

        print("Uploading staged INT8 files to Hugging Face...")
        api.upload_folder(
            folder_path=str(stage),
            repo_id=repo_id,
            repo_type="model"
        )

    print(f"\n🎉 Successfully uploaded ONLY INT8 model to: https://huggingface.co/{repo_id}")

if __name__ == "__main__":
    upload()
