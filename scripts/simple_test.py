#!/usr/bin/env python3
"""
Simple test to verify downloaded files work.
"""

import os
import sys
import torch
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_downloads():
    """Test that all downloaded files are accessible."""
    
    print("=== Testing Downloaded Files ===")
    print()
    
    # Test 1: Model file
    model_path = "data/models/redox_core_v2.json"
    if os.path.exists(model_path):
        print("✅ Core model found")
        try:
            import cobra
            model = cobra.io.load_json_model(model_path)
            print(f"   {len(model.reactions)} reactions, {len(model.metabolites)} metabolites")
        except Exception as e:
            print(f"   ❌ Failed to load: {e}")
    else:
        print("❌ Core model missing")
        return False
    
    # Test 2: Enzyme library
    enzyme_path = "data/enzyme_library_redox.json"
    if os.path.exists(enzyme_path):
        print("✅ Enzyme library found")
        try:
            with open(enzyme_path) as f:
                enzymes = json.load(f)
            print(f"   Contains {len(enzymes)} top-level entries")
        except Exception as e:
            print(f"   ❌ Failed to load: {e}")
    else:
        print("❌ Enzyme library missing")
    
    # Test 3: Final checkpoint
    checkpoint_dir = "experiments/redox_120actors_sink_flux_20250713_020105/final"
    if os.path.exists(checkpoint_dir):
        print("✅ Final checkpoint found")
        files = os.listdir(checkpoint_dir)
        print(f"   Files: {', '.join(files)}")
        
        # Test loading one of the model files
        tumor_model = os.path.join(checkpoint_dir, "tumor_agent.pt.gz")
        if os.path.exists(tumor_model):
            try:
                checkpoint = torch.load(tumor_model, map_location='cpu')
                print(f"   Tumor agent: {len(checkpoint)} parameters")
            except Exception as e:
                print(f"   ⚠️  Tumor agent load warning: {e}")
        
        # Test training state
        state_file = os.path.join(checkpoint_dir, "training_state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file) as f:
                    state = json.load(f)
                print(f"   Training state: step {state.get('step', 'unknown')}")
            except Exception as e:
                print(f"   ⚠️  State file warning: {e}")
    else:
        print("❌ Final checkpoint missing")
    
    # Test 4: Directory structure
    print()
    print("📁 Current directory structure:")
    print(f"   Total size: {get_dir_size('.')} MB")
    
    for item in ['.', 'data/', 'experiments/', 'scripts/']:
        if os.path.exists(item):
            size = get_dir_size(item)
            print(f"   {item}: {size} MB")
    
    print()
    print("🎯 Ready for analysis!")
    print()
    print("Next steps:")
    print("   1. For training curves: ./scripts/download_for_visualization.sh")
    print("   2. For full evaluation: python scripts/eval_agents.py --checkpoint final")
    print("   3. See POST_TRAINING_ANALYSIS.md for detailed workflows")
    
    return True

def get_dir_size(path):
    """Get directory size in MB."""
    try:
        import subprocess
        result = subprocess.run(['du', '-sm', path], capture_output=True, text=True)
        return result.stdout.split()[0]
    except:
        return "?"

if __name__ == "__main__":
    test_downloads()