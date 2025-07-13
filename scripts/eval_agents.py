#!/usr/bin/env python3
"""
Evaluation script for trained redox balancer agents.
Loads checkpoint and runs deterministic evaluation episodes.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import cobra
import numpy as np
import pandas as pd
import torch
from tqdm import tqdm

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from redox_balancer.agents.net import AgentNet
from redox_balancer.env.redox_env import RedoxBalancerEnv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def load_checkpoint(checkpoint_path: Path) -> Tuple[Dict, Dict, int]:
    """Load agent networks and training state from checkpoint."""
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
    
    # Load training state
    state_path = checkpoint_path / "training_state.json"
    with open(state_path, "r") as f:
        training_state = json.load(f)
    
    # Load agent networks
    agents = {}
    for role in ["tumor", "sink_designer"]:
        agent_path = checkpoint_path / f"{role}_agent.pt.gz"
        if agent_path.exists():
            agent_state = torch.load(agent_path, map_location="cpu")
            agents[role] = agent_state
            logger.info(f"Loaded {role} agent from {agent_path}")
    
    timesteps = training_state.get("global_timesteps", 0)
    return agents, training_state, timesteps


def evaluate_agents(
    env: RedoxBalancerEnv,
    agents: Dict,
    num_episodes: int = 500,
    deterministic: bool = True,
    seed: int = 42,
) -> pd.DataFrame:
    """Run evaluation episodes and collect metrics."""
    results = []
    
    # Set seeds for reproducibility
    np.random.seed(seed)
    torch.manual_seed(seed)
    
    # Create agent networks
    nets = {}
    for role, state in agents.items():
        net = AgentNet(
            observation_space=env.observation_space,
            action_space=env.action_space,
            hidden_dim=state.get("hidden_dim", 512),
            num_layers=state.get("num_layers", 3),
        )
        net.load_state_dict(state["state_dict"])
        net.eval()
        nets[role] = net
    
    # Run evaluation episodes
    for episode in tqdm(range(num_episodes), desc="Evaluating"):
        obs, _ = env.reset(seed=seed + episode)
        done = False
        episode_return = 0
        episode_length = 0
        
        # Track episode metrics
        growth_rates = []
        sink_fluxes = []
        nadh_levels = []
        
        while not done:
            # Get action from appropriate agent
            obs_tensor = torch.FloatTensor(obs).unsqueeze(0)
            
            with torch.no_grad():
                if env.agent_role in nets:
                    policy, _ = nets[env.agent_role](obs_tensor)
                    
                    if deterministic:
                        # Take mode of distribution
                        action = policy.mode.squeeze(0).cpu().numpy()
                    else:
                        # Sample from distribution
                        action = policy.sample().squeeze(0).cpu().numpy()
                else:
                    # Random action if agent not found
                    action = env.action_space.sample()
            
            # Step environment
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            
            episode_return += reward
            episode_length += 1
            
            # Collect metrics
            growth_rates.append(info.get("growth_rate", 0))
            
            # Get sink flux from info if available
            if "sink_flux" in info:
                sink_fluxes.append(info["sink_flux"])
            
        # Record episode results
        result = {
            "episode": episode,
            "return": episode_return,
            "length": episode_length,
            "final_growth": growth_rates[-1] if growth_rates else 0,
            "mean_growth": np.mean(growth_rates) if growth_rates else 0,
            "max_sink_flux": max(sink_fluxes) if sink_fluxes else 0,
            "mean_sink_flux": np.mean(sink_fluxes) if sink_fluxes else 0,
        }
        results.append(result)
    
    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained redox balancer agents")
    parser.add_argument(
        "--checkpoint",
        type=str,
        help="Path to checkpoint directory (defaults to latest)",
    )
    parser.add_argument(
        "--experiment-dir",
        type=str,
        default="experiments",
        help="Base experiments directory",
    )
    parser.add_argument(
        "--num-episodes",
        type=int,
        default=500,
        help="Number of evaluation episodes",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="data/models/redox_core_v1.json",
        help="Path to metabolic model",
    )
    parser.add_argument(
        "--enzymes",
        type=str,
        default="data/enzyme_library_redox.json",
        help="Path to enzyme library",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output CSV path (defaults to checkpoint_dir/evaluation.csv)",
    )
    parser.add_argument(
        "--deterministic",
        action="store_true",
        default=True,
        help="Use deterministic policy (mode instead of sampling)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    
    args = parser.parse_args()
    
    # Find checkpoint
    if args.checkpoint:
        checkpoint_path = Path(args.checkpoint)
    else:
        # Find latest checkpoint
        exp_dir = Path(args.experiment_dir)
        latest_exp = sorted(exp_dir.glob("redox_*"))[-1]
        checkpoints = sorted(latest_exp.glob("step_*"))
        if not checkpoints:
            raise FileNotFoundError(f"No checkpoints found in {latest_exp}")
        checkpoint_path = checkpoints[-1]
    
    logger.info(f"Evaluating checkpoint: {checkpoint_path}")
    
    # Load checkpoint
    agents, training_state, timesteps = load_checkpoint(checkpoint_path)
    logger.info(f"Checkpoint at {timesteps:,} timesteps")
    
    # Load model and enzyme database
    model = cobra.io.load_json_model(args.model)
    with open(args.enzymes, "r") as f:
        enzyme_data = json.load(f)
    enzyme_db = enzyme_data.get("enzymes", {})
    
    # Create environment
    env = RedoxBalancerEnv(
        base_model=model,
        agent_role="sink_designer",  # Evaluate sink designer
        enzyme_db=enzyme_db,
        use_cache=False,  # Disable for evaluation
    )
    
    # Run evaluation
    logger.info(f"Running {args.num_episodes} evaluation episodes...")
    results_df = evaluate_agents(
        env,
        agents,
        num_episodes=args.num_episodes,
        deterministic=args.deterministic,
        seed=args.seed,
    )
    
    # Calculate summary statistics
    mean_return = results_df["return"].mean()
    std_return = results_df["return"].std()
    success_rate = (results_df["final_growth"] > 0.9 * 0.67).mean() * 100
    
    logger.info(f"\n=== EVALUATION RESULTS ===")
    logger.info(f"Mean return: {mean_return:.2f} ± {std_return:.2f}")
    logger.info(f"Success rate (>90% growth): {success_rate:.1f}%")
    logger.info(f"Mean final growth: {results_df['final_growth'].mean():.3f}")
    logger.info(f"Mean sink flux: {results_df['mean_sink_flux'].mean():.3f}")
    
    # Save results
    output_path = args.output or checkpoint_path / "evaluation.csv"
    results_df.to_csv(output_path, index=False)
    logger.info(f"Results saved to: {output_path}")
    
    # Save summary
    summary = {
        "checkpoint": str(checkpoint_path),
        "timesteps": timesteps,
        "num_episodes": args.num_episodes,
        "mean_return": mean_return,
        "std_return": std_return,
        "success_rate": success_rate,
        "mean_growth": results_df["final_growth"].mean(),
        "evaluation_date": datetime.now().isoformat(),
    }
    
    summary_path = output_path.parent / "evaluation_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()