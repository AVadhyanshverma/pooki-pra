#!/usr/bin/env python3
"""
Exports cklxx/laya-browser to ONNX with dynamic shapes using PyTorch Dynamo exporter.
Verifies numerical parity with onnxruntime and copies required assets.
"""
import os
import sys
import shutil
import json
import torch
import numpy as np
import onnxruntime as ort
from safetensors.torch import load_file

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_DIR = os.path.join(BASE_DIR, "laya-model")
ONNX_DIR = os.path.join(BASE_DIR, "laya")
sys.path.insert(0, MODEL_DIR)

from modeling_laya_browser import LayaBrowserConfig, LayaBrowserModel

def main():
    print("=== Laya Browser ONNX Exporter ===")
    os.makedirs(ONNX_DIR, exist_ok=True)
    
    config_path = os.path.join(MODEL_DIR, "config.json")
    weights_path = os.path.join(MODEL_DIR, "model.safetensors")
    onnx_output_path = os.path.join(ONNX_DIR, "model.onnx")
    
    # Clean previous onnx files in laya/
    for f in os.listdir(ONNX_DIR):
        if f.startswith("model"):
            try:
                os.remove(os.path.join(ONNX_DIR, f))
            except Exception:
                pass
                
    with open(config_path, "r") as f:
        cfg_dict = json.load(f)
    config = LayaBrowserConfig(**cfg_dict)
    
    print("Instantiating LayaBrowserModel...")
    model = LayaBrowserModel(config)
    
    print(f"Loading weights from {weights_path}...")
    state_dict = load_file(weights_path)
    model.load_state_dict(state_dict, strict=False)
    model.eval()
    
    # Configure dynamic dims
    batch = torch.export.Dim("batch", min=1, max=16)
    seq_len = torch.export.Dim("seq_len", min=8, max=1024)
    num_markers = torch.export.Dim("num_markers", min=1, max=120)

    dynamic_shapes = {
        "input_ids": {0: batch, 1: seq_len},
        "attention_mask": {0: batch, 1: seq_len},
        "marker_pos": {0: batch, 1: num_markers},
        "marker_mask": {0: batch, 1: num_markers},
        "qtype": {0: batch}
    }

    dummy_input_ids = torch.randint(10, 1000, (2, 64), dtype=torch.long)
    dummy_attention_mask = torch.ones((2, 64), dtype=torch.long)
    dummy_marker_pos = torch.tensor([[10, 25, 40], [15, 30, 45]], dtype=torch.long)
    dummy_marker_mask = torch.ones((2, 3), dtype=torch.bool)
    dummy_qtype = torch.tensor([0, 1], dtype=torch.long)
    
    print("\nVerifying PyTorch forward pass...")
    with torch.no_grad():
        pt_out = model(
            dummy_input_ids,
            dummy_attention_mask,
            dummy_marker_pos,
            dummy_marker_mask,
            dummy_qtype
        )
    print(f"PyTorch output shape: {pt_out.shape}, sample values: {pt_out[0, :3].tolist()}")
    
    print(f"\nExporting to ONNX at {onnx_output_path}...")
    torch.onnx.export(
        model,
        (dummy_input_ids, dummy_attention_mask, dummy_marker_pos, dummy_marker_mask, dummy_qtype),
        onnx_output_path,
        dynamic_shapes=dynamic_shapes,
        opset_version=18,
        dynamo=True
    )
    
    print("Export complete. Validating with ONNX Runtime...")
    sess = ort.InferenceSession(onnx_output_path, providers=["CPUExecutionProvider"])
    ort_in = {
        "input_ids": dummy_input_ids.numpy(),
        "attention_mask": dummy_attention_mask.numpy(),
        "marker_pos": dummy_marker_pos.numpy(),
        "marker_mask": dummy_marker_mask.numpy(),
        "qtype": dummy_qtype.numpy()
    }
    ort_out = sess.run(None, ort_in)[0]
    
    max_diff = np.max(np.abs(pt_out.numpy() - ort_out))
    print(f"Max absolute difference PyTorch vs ONNX: {max_diff:.6e}")
    if max_diff < 1e-3:
        print("PARITY CHECK PASSED!")
    else:
        print(f"WARNING: Max difference {max_diff}")
        
    # Copy configs and tokenizer
    print("\nCopying tokenizer and configs to laya/...")
    shutil.copy2(config_path, os.path.join(ONNX_DIR, "config.json"))
    if os.path.exists(os.path.join(MODEL_DIR, "rl_agent_config.json")):
        shutil.copy2(os.path.join(MODEL_DIR, "rl_agent_config.json"), os.path.join(ONNX_DIR, "rl_agent_config.json"))
        
    tok_src = os.path.join(MODEL_DIR, "tokenizer")
    tok_dst = os.path.join(ONNX_DIR, "tokenizer")
    if os.path.exists(tok_src):
        if os.path.exists(tok_dst):
            shutil.rmtree(tok_dst)
        shutil.copytree(tok_src, tok_dst)
        
    print("All artifacts prepared in laya/.")

if __name__ == "__main__":
    main()
