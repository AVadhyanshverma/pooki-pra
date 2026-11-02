#!/usr/bin/env python3
"""
Test script for Laya ONNX inference on realistic web page observations.
Tests end-to-end tokenizer -> ONNX Runtime -> Action decoding & latency benchmark.
"""
import os
import sys
import json
import time
import math
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ONNX_DIR = os.path.join(BASE_DIR, "laya")
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from laya_helpers import build_request, compact, NEXT_ACTION, TARGET, LABELS, QTYPES

class LayaONNXRunner:
    def __init__(self, model_dir=ONNX_DIR):
        self.model_dir = model_dir
        self.onnx_path = os.path.join(model_dir, "model.onnx")
        self.config_path = os.path.join(model_dir, "config.json")
        
        with open(self.config_path, "r") as f:
            self.config = json.load(f)
            
        self.tokenizer = AutoTokenizer.from_pretrained(os.path.join(model_dir, "tokenizer"))
        
        # Initialize ONNX Runtime session
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if "CUDAExecutionProvider" in ort.get_available_providers() else ["CPUExecutionProvider"]
        print(f"Initializing ONNX Runtime session with providers: {providers}")
        self.session = ort.InferenceSession(self.onnx_path, providers=providers)
        print(f"Active provider: {self.session.get_providers()[0]}")
        
        self.temperatures = self.config.get("temperature", [4.55, 1.0, 1.0])
        self.max_len = self.config.get("max_len", 1024)
        self.head_max_len = self.config.get("head_max_len", 768)
        self.page_text_chars = self.config.get("page_text_chars", 1200)

    def _sequence(self, state, q):
        tok = self.tokenizer
        mask_tok = tok.mask_token
        crit = q["criteria"]
        opts = [k if v is None or v == "" else "%s: %s" % (k, v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, separators=(", ", ": ")))
                for k, v in crit.items()]
        ins = q["instructions"] if isinstance(q["instructions"], str) else json.dumps(q["instructions"])
        head_ids = tok("%s question: %s" % (q["type"], ins.replace(mask_tok, " ")), add_special_tokens=False)["input_ids"]
        opt_ids = [[tok.mask_token_id] + tok(" " + o.replace(mask_tok, " "), add_special_tokens=False, truncation=True, max_length=48)["input_ids"]
                   for o in opts]
        
        hm = self.head_max_len
        budget = hm - sum(len(o) for o in opt_ids)
        if budget < 16:
            per = max(4, (hm - 16) // max(1, len(opt_ids)))
            opt_ids = [o[:per] for o in opt_ids]
            budget = hm - sum(len(o) for o in opt_ids)
            
        ids = [tok.cls_token_id] + head_ids[: max(8, budget)] + [tok.sep_token_id]
        markers = []
        for o in opt_ids:
            markers.append(len(ids))
            ids.extend(o)
        ids.append(tok.sep_token_id)
        
        room = max(0, self.max_len - len(ids) - 1)
        st = tok(json.dumps(state, ensure_ascii=False).replace(mask_tok, " "), add_special_tokens=False)["input_ids"]
        ids = (ids + st[:room] + [tok.sep_token_id])[: self.max_len]
        return ids, [m for m in markers if m < self.max_len]

    def predict(self, state, questions):
        qids = list(questions)
        seqs = [self._sequence(state, questions[q]) for q in qids]
        n = len(seqs)
        L = max(len(s) for s, _ in seqs)
        K = max(len(m) for _, m in seqs)
        
        input_ids = np.full((n, L), self.tokenizer.pad_token_id, dtype=np.int64)
        attention_mask = np.zeros((n, L), dtype=np.int64)
        marker_pos = np.zeros((n, K), dtype=np.int64)
        marker_mask = np.zeros((n, K), dtype=bool)
        
        for i, (s, m) in enumerate(seqs):
            input_ids[i, :len(s)] = s
            attention_mask[i, :len(s)] = 1
            marker_pos[i, :len(m)] = m
            marker_mask[i, :len(m)] = True
            
        qtype = np.array([QTYPES[questions[q]["type"]] for q in qids], dtype=np.int64)
        
        ort_inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "marker_pos": marker_pos,
            "marker_mask": marker_mask,
            "qtype": qtype
        }
        
        t0 = time.perf_counter()
        logits = self.session.run(None, ort_inputs)[0]
        inference_ms = (time.perf_counter() - t0) * 1000
        
        out = {}
        for r, q in enumerate(qids):
            keys = list(questions[q]["criteria"])
            k = len(seqs[r][1])
            temp = max(1e-3, float(self.temperatures[QTYPES[questions[q]["type"]]]))
            z = logits[r, :k] / temp
            exp_z = np.exp(z - np.max(z))
            p = exp_z / np.sum(exp_z)
            
            ent = -np.sum(p * np.log(np.clip(p, 1e-12, None)))
            conf = 1.0 if k < 2 else max(0.0, min(1.0, 1.0 - ent / math.log(k)))
            best_idx = int(np.argmax(p))
            out[q] = {
                "type": "choice",
                "choice": keys[best_idx],
                "probabilities": {kk: float(v) for kk, v in zip(keys, p)},
                "confidence": round(float(conf), 4),
                "inference_ms": round(inference_ms, 2)
            }
        return out

    def decide(self, page, goal, history=()):
        t_start = time.perf_counter()
        state, questions, targets, controls = build_request(page, goal, history, self.page_text_chars)
        ans = self.predict(state, questions)
        op = ans["operation"]["choice"]
        action = targets[op][ans[op.lower() + "_target"]["choice"]] if op in targets else controls.get(op)
        total_ms = (time.perf_counter() - t_start) * 1000
        
        return {
            "operation": op,
            "action": action,
            "confidence": ans["operation"]["confidence"],
            "probabilities": ans["operation"]["probabilities"],
            "latency_ms": round(total_ms, 2)
        }

def run_test():
    print("=== Testing Laya ONNX Decision Runner ===")
    runner = LayaONNXRunner()
    
    # Mock realistic web page observation
    sample_page = {
        "url": "https://crates.io",
        "title": "crates.io: Rust Package Registry",
        "text": "crates.io - The official package registry for the Rust programming language. Search thousands of crates.",
        "actions": [
            {"id": "e1", "kind": "fill", "node": "search_input", "label": "Search crates, categories, and more", "role": "searchbox", "value": ""},
            {"id": "e2", "kind": "click", "node": "search_btn", "label": "Submit search", "role": "button"},
            {"id": "e3", "kind": "click", "node": "login_link", "label": "Log in with GitHub", "role": "link"},
            {"id": "e4", "kind": "click", "node": "browse_all", "label": "Browse All Crates", "role": "link"},
            {"id": "scroll_down", "kind": "scroll", "label": "Scroll down"}
        ]
    }
    
    goal = "Search for 'tokio' on crates.io"
    print(f"\nGoal: {goal}")
    print("Page elements: 1 searchbox, 3 clickable links/buttons, 1 scroll control")
    
    decision = runner.decide(sample_page, goal=goal)
    print("\nDecision Result:")
    print(f" - Operation selected: {decision['operation']}")
    print(f" - Target action: {json.dumps(decision['action'], indent=4)}")
    print(f" - Confidence: {decision['confidence'] * 100:.1f}%")
    print(f" - End-to-end Latency: {decision['latency_ms']} ms")
    print("\nOperation Probabilities:")
    for op, prob in sorted(decision['probabilities'].items(), key=lambda x: x[1], reverse=True):
        print(f"   * {op}: {prob * 100:.2f}%")

if __name__ == "__main__":
    run_test()
