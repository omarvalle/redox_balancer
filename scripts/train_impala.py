#!/usr/bin/env python3
"""Train IMPALA agents for NAD+/NADH redox balance optimization.

This script uses the custom IMPALA implementation rather than Ray RLlib.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from redox_balancer.agents.trainer import IMPALATrainer, TrainingConfig


def main():
    """Main training entry point."""
    parser = argparse.ArgumentParser(
        description="Train redox-balancer agents using custom IMPALA implementation"
    )
    
    # Model and data paths
    parser.add_argument(
        "--model",
        type=str,
        default="data/models/redox_core.json",
        help="Path to metabolic model JSON file (default: core model)"
    )
    parser.add_argument(
        "--full-model",
        action="store_true",
        help="Use full Recon3D model instead of core"
    )
    parser.add_argument(
        "--enzymes",
        type=str,
        default="data/enzyme_library_redox.json",
        help="Path to enzyme library JSON file"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/ray/impala_local.yaml",
        help="Path to training config (for hyperparameters)"
    )
    
    # Training parameters
    parser.add_argument(
        "--timesteps",
        type=int,
        default=10_000_000,
        help="Total timesteps to train"
    )
    parser.add_argument(
        "--num-actors",
        type=int,
        default=4,
        help="Number of distributed actors"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Training batch size"
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=3e-4,
        help="Learning rate"
    )
    parser.add_argument(
        "--reward-scale",
        type=float,
        default=1.0,
        help="Scale factor for rewards (for ablation studies)"
    )
    
    # Ray settings
    parser.add_argument(
        "--ray-num-cpus",
        type=int,
        default=None,
        help="Number of CPUs for Ray (None = auto-detect)"
    )
    parser.add_argument(
        "--ray-num-gpus",
        type=int,
        default=0,
        help="Number of GPUs for Ray"
    )
    
    # Device settings
    parser.add_argument(
        "--learner-device",
        type=str,
        default="cpu",
        choices=["cpu", "cuda"],
        help="Device for learner (cpu or cuda)"
    )
    parser.add_argument(
        "--actor-device",
        type=str,
        default="cpu",
        choices=["cpu", "cuda"],
        help="Device for actors (cpu or cuda)"
    )
    
    # Logging and checkpointing
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="./experiments/checkpoints",
        help="Directory for saving checkpoints"
    )
    parser.add_argument(
        "--log-interval",
        type=int,
        default=10,
        help="Log statistics every N seconds"
    )
    parser.add_argument(
        "--save-interval",
        type=int,
        default=300,
        help="Save checkpoint every N seconds"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force training with >120 actors (not recommended)"
    )
    
    # Environment parameters
    parser.add_argument(
        "--biomass-penalty",
        type=float,
        default=100.0,
        help="Biomass penalty weight (lambda1)"
    )
    parser.add_argument(
        "--hif-penalty",
        type=float,
        default=5.0,
        help="HIF penalty weight (lambda2)"
    )
    
    # Redox-specific parameters
    parser.add_argument(
        "--target-metabolite",
        type=str,
        default="NADH",
        choices=["NADH", "NAD+"],
        help="Target metabolite for redox balance (default: NADH)"
    )
    parser.add_argument(
        "--redox-weight",
        type=float,
        default=0.1,
        help="Weight for redox balance component in reward"
    )
    
    # Resume from checkpoint
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Resume from checkpoint path"
    )
    
    # Alternative to --timesteps
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Total steps to train (alias for --timesteps)"
    )
    
    args = parser.parse_args()
    
    # Handle --steps as alias for --timesteps
    if args.steps is not None:
        args.timesteps = args.steps
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handle full model flag
    if args.full_model:
        args.model = "data/models/recon3d_full.json"
        logging.info("Using full Recon3D model")
    
    # Verify paths exist
    model_path = Path(args.model)
    enzyme_path = Path(args.enzymes)
    
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    if not enzyme_path.exists():
        raise FileNotFoundError(f"Enzyme library not found: {enzyme_path}")
    
    # Guard against long runs on minimal test model
    if args.timesteps > 1e5 and "minimal_test_model" in str(model_path):
        raise SystemExit(
            "ERROR: Refusing to run long training (>100k steps) on minimal test model.\n"
            "The minimal model is only suitable for unit tests and quick smoke runs.\n"
            "Please use the full Recon3D model: data/models/recon3d_full.json"
        )
    
    # Guard against too many actors
    if args.num_actors > 120 and not args.force:
        raise SystemExit(
            f"ERROR: Refusing to run with {args.num_actors} actors (max 120).\n"
            "Based on lactate_sink experience, >120 actors risks memory issues.\n"
            "Use --force to override this safety check."
        )
    
    # Build env_config - include the penalty weights and redox parameters
    env_cfg = {
        "biomass_penalty_weight": args.biomass_penalty,
        "hif_penalty_weight": args.hif_penalty,
        "target_metabolite": args.target_metabolite,
    }
    
    # Detect smoke test model
    if "smoke" in str(model_path).lower() or "minimal" in str(model_path).lower():
        env_cfg["smoke"] = True
        logging.info("Detected smoke test model - using relaxed medium constraints")
    
    # Create training config
    config = TrainingConfig(
        # Paths
        model_path=str(model_path),
        enzyme_library_path=str(enzyme_path),
        
        # Actor settings
        num_actors=args.num_actors,
        actor_device=args.actor_device,
        
        # Learner settings
        learner_device=args.learner_device,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        
        # Training settings
        total_timesteps=args.timesteps,
        
        # Ray settings
        ray_num_cpus=args.ray_num_cpus,
        ray_num_gpus=args.ray_num_gpus,
        
        # Logging
        log_interval=args.log_interval * 1000,  # Convert to milliseconds
        save_interval=args.save_interval * 1000,  # Convert to milliseconds
        checkpoint_dir=args.checkpoint_dir,
        
        # Environment configuration
        env_config=env_cfg,
    )
    
    # Log configuration
    logging.info("=" * 60)
    logging.info("NAD+/NADH Redox-Balancer IMPALA Training")
    logging.info("=" * 60)
    logging.info(f"Model: {args.model}")
    logging.info(f"Enzymes: {args.enzymes}")
    logging.info(f"Timesteps: {args.timesteps:,}")
    logging.info(f"Actors: {args.num_actors}")
    logging.info(f"Learner device: {args.learner_device}")
    logging.info(f"Checkpoint dir: {args.checkpoint_dir}")
    logging.info(f"Biomass penalty: {args.biomass_penalty}")
    logging.info(f"HIF penalty: {args.hif_penalty}")
    logging.info("=" * 60)
    
    # Create and run trainer
    trainer = IMPALATrainer(config)
    
    # Handle resume from checkpoint
    if args.resume:
        logging.info(f"Resuming from checkpoint: {args.resume}")
        trainer.load_checkpoint(args.resume)
    
    trainer.train()
    
    logging.info("Training complete!")


if __name__ == "__main__":
    main()