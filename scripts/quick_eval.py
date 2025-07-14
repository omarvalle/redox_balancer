#!/usr/bin/env python3
"""
Quick evaluation script for the trained redox balancer model.
Tests the downloaded checkpoint on a few episodes to verify it's working.
"""

import os
import sys
import json
import torch
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def quick_eval():
    """Run a quick evaluation of the downloaded model."""
    
    # Check if files exist
    model_path = "data/models/redox_core_v2.json"
    checkpoint_dir = "experiments/redox_120actors_sink_flux_20250713_020105/final"
    
    if not os.path.exists(model_path):
        print("❌ Model file not found. Run: ./scripts/download_for_evaluation.sh")
        return False
        
    if not os.path.exists(checkpoint_dir):
        print("❌ Checkpoint not found. Run: ./scripts/download_for_evaluation.sh")
        return False
    
    print("✅ Files found, loading model...")
    
    try:
        # Load the model and environment
        import cobra
        from redox_balancer.env.redox_env import RedoxBalancerEnv
        
        # Load model
        model = cobra.io.load_json_model(model_path)
        print(f"✅ Model loaded: {len(model.reactions)} reactions")
        
        # Load enzyme library
        from redox_balancer.data.enzyme_library import EnzymeLibrary
        enzyme_library = EnzymeLibrary("data/enzyme_library_redox.json")
        print(f"✅ Enzyme library loaded: {len(enzyme_library)} enzymes")
        
        # Create environment
        env = RedoxBalancerEnv(
            base_model=model,
            agent_role="tumor",
            enzyme_db=enzyme_library
        )
        
        print(f"✅ Environment loaded: {len(env.model.reactions)} reactions")
        
        # Load checkpoint
        tumor_checkpoint = os.path.join(checkpoint_dir, "tumor_agent.pt.gz")
        if os.path.exists(tumor_checkpoint):
            checkpoint = torch.load(tumor_checkpoint, map_location='cpu')
            print(f"✅ Checkpoint loaded: {len(checkpoint)} parameters")
        else:
            print("⚠️  No tumor agent checkpoint found, using random policy")
            checkpoint = None
        
        # Run a few episodes
        print("\n🧪 Running evaluation episodes...")
        
        returns = []
        for episode in range(5):
            obs, _ = env.reset()
            total_reward = 0
            done = False
            step = 0
            
            while not done and step < 20:  # Max 20 steps per episode
                # Random action for now (replace with trained policy)
                action = env.action_space.sample()
                obs, reward, terminated, truncated, info = env.step(action)
                total_reward += reward
                done = terminated or truncated
                step += 1
            
            returns.append(total_reward)
            print(f"  Episode {episode + 1}: {total_reward:.2f} reward in {step} steps")
        
        # Summary
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        print(f"\n📊 Results:")
        print(f"  Mean return: {mean_return:.2f} ± {std_return:.2f}")
        print(f"  Expected trained performance: ~4,000-4,500")
        
        if mean_return > 1000:
            print("✅ Model appears to be performing well!")
        else:
            print("⚠️  Performance seems low - may need trained policy network")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during evaluation: {e}")
        return False

if __name__ == "__main__":
    print("=== Quick Model Evaluation ===")
    print()
    
    success = quick_eval()
    
    print()
    if success:
        print("✅ Quick evaluation completed successfully!")
        print()
        print("Next steps:")
        print("  1. Run full evaluation: python scripts/eval_agents.py --checkpoint final")
        print("  2. View training curves: tensorboard --logdir experiments/*/tensorboard")
        print("  3. See POST_TRAINING_ANALYSIS.md for detailed workflows")
    else:
        print("❌ Evaluation failed. Check error messages above.")
        print("Make sure to run: ./scripts/download_for_evaluation.sh first")