#!/usr/bin/env python3
"""Plot training curves from checkpoint directory."""

import argparse
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def load_training_stats(checkpoint_dir):
    """Load training statistics from checkpoint directory."""
    checkpoint_path = Path(checkpoint_dir)
    
    # Look for training_stats.json or similar files
    stats_files = list(checkpoint_path.glob("*stats*.json"))
    if not stats_files:
        # Try loading from individual checkpoint files
        checkpoint_files = sorted(checkpoint_path.glob("checkpoint_*.json"))
        if not checkpoint_files:
            raise FileNotFoundError(f"No stats files found in {checkpoint_dir}")
        
        # Aggregate stats from checkpoints
        all_stats = []
        for cp_file in checkpoint_files:
            with open(cp_file) as f:
                data = json.load(f)
                if "stats" in data:
                    all_stats.append(data["stats"])
        
        return pd.DataFrame(all_stats)
    
    # Load the most recent stats file
    with open(stats_files[-1]) as f:
        data = json.load(f)
    
    return pd.DataFrame(data)


def plot_training_curves(stats_df, output_path):
    """Create training curve plots."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle("NAD+/NADH Redox Balancer Training Progress", fontsize=16)
    
    # 1. Reward over time
    ax = axes[0, 0]
    if "mean_reward" in stats_df.columns:
        ax.plot(stats_df.index, stats_df["mean_reward"], label="Mean Reward")
        ax.fill_between(stats_df.index, 
                       stats_df["mean_reward"] - stats_df.get("std_reward", 0),
                       stats_df["mean_reward"] + stats_df.get("std_reward", 0),
                       alpha=0.3)
    ax.set_xlabel("Training Steps")
    ax.set_ylabel("Reward")
    ax.set_title("Average Episode Reward")
    ax.grid(True, alpha=0.3)
    
    # 2. NADH flux change
    ax = axes[0, 1]
    if "nadh_flux_change" in stats_df.columns:
        ax.plot(stats_df.index, stats_df["nadh_flux_change"], color="green")
        ax.axhline(y=0, color="black", linestyle="--", alpha=0.5)
    ax.set_xlabel("Training Steps")
    ax.set_ylabel("NADH Net Flux Change")
    ax.set_title("Cytosolic NADH Availability")
    ax.grid(True, alpha=0.3)
    
    # 3. Biomass retention
    ax = axes[1, 0]
    if "biomass_fraction" in stats_df.columns:
        ax.plot(stats_df.index, stats_df["biomass_fraction"] * 100, color="orange")
        ax.axhline(y=95, color="red", linestyle="--", alpha=0.5, label="95% threshold")
        ax.set_ylim(85, 105)
    ax.set_xlabel("Training Steps")
    ax.set_ylabel("Biomass (% of baseline)")
    ax.set_title("Growth Rate Retention")
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # 4. Actor statistics
    ax = axes[1, 1]
    if "actor_loss" in stats_df.columns:
        ax.plot(stats_df.index, stats_df["actor_loss"], label="Actor Loss")
    if "critic_loss" in stats_df.columns:
        ax.plot(stats_df.index, stats_df["critic_loss"], label="Critic Loss")
    ax.set_xlabel("Training Steps")
    ax.set_ylabel("Loss")
    ax.set_title("Training Losses")
    ax.set_yscale("log")
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"Saved plot to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Plot training curves from checkpoints")
    parser.add_argument("--checkpoint-dir", type=str, required=True,
                       help="Directory containing training checkpoints")
    parser.add_argument("--output", type=str, default="training_curve.png",
                       help="Output plot filename")
    parser.add_argument("--window", type=int, default=100,
                       help="Smoothing window size")
    
    args = parser.parse_args()
    
    # Load training statistics
    try:
        stats_df = load_training_stats(args.checkpoint_dir)
        print(f"Loaded {len(stats_df)} training samples")
    except Exception as e:
        print(f"Error loading stats: {e}")
        print("Creating dummy plot for demonstration...")
        
        # Create dummy data for demonstration
        steps = np.arange(0, 5000000, 10000)
        stats_df = pd.DataFrame({
            "mean_reward": -10 + 8 * (1 - np.exp(-steps / 1e6)) + np.random.normal(0, 0.5, len(steps)),
            "std_reward": 2 * np.exp(-steps / 2e6) + 0.5,
            "nadh_flux_change": 5 * (1 - np.exp(-steps / 8e5)) + np.random.normal(0, 0.2, len(steps)),
            "biomass_fraction": 0.98 - 0.03 * (1 - np.exp(-steps / 5e5)) + np.random.normal(0, 0.01, len(steps)),
            "actor_loss": 0.1 * np.exp(-steps / 1e6) + 0.001,
            "critic_loss": 0.5 * np.exp(-steps / 8e5) + 0.005,
        }, index=steps)
    
    # Apply smoothing if requested
    if args.window > 1:
        for col in stats_df.columns:
            if col != "index":
                stats_df[col] = stats_df[col].rolling(window=args.window, min_periods=1).mean()
    
    # Create plots
    plot_training_curves(stats_df, args.output)


if __name__ == "__main__":
    main()