#!/usr/bin/env python3
"""
Download BGE Reranker v2-m3 from HuggingFace Hub
This script ensures all required files are downloaded for vLLM compatibility
"""

import os
import sys
from pathlib import Path
from huggingface_hub import snapshot_download

# Model configuration
MODEL_REPO = "BAAI/bge-reranker-v2-m3"
OUTPUT_DIR = "/models"

# Ensure output directory exists
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

print("=" * 70)
print(f"📥 DOWNLOADING: {MODEL_REPO}")
print(f"📍 DESTINATION: {OUTPUT_DIR}")
print("=" * 70)

try:
    # Download ALL files (not just specific patterns)
    # vLLM needs complete model directory
    snapshot_download(
        repo_id=MODEL_REPO,
        local_dir=OUTPUT_DIR,
        repo_type="model",
        resume_download=True,
        force_download=False,
    )
    
    print("\n✅ Download completed successfully!")
    
    # Verify critical files exist
    required_files = [
        "config.json",
        "model.safetensors",
        "tokenizer.json",
    ]
    
    print("\n📋 VERIFICATION:")
    all_exist = True
    for file in required_files:
        file_path = Path(OUTPUT_DIR) / file
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"   ✓ {file} ({size_mb:.1f} MB)")
        else:
            print(f"   ✗ {file} - MISSING!")
            all_exist = False
    
    if not all_exist:
        print("\n❌ ERROR: Required files missing!")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("✅ All files verified. Ready for vLLM!")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ ERROR downloading model: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
