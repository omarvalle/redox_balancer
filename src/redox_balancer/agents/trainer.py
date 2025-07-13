"""IMPALA distributed trainer using Ray."""

import ray
import torch
import numpy as np
from typing import Dict, List, Optional, Tuple
import time
import logging
from collections import deque
from dataclasses import dataclass, field
import json
import os
import shutil
from pathlib import Path

from ..env.redox_env import RedoxBalancerEnv
from ..cache.delta_cache import DeltaCache
from .impala_agent import IMPALAAgent, Trajectory
from .networks import ActorCriticNetwork, SinkDesignerNetwork
from ..utils import TensorBoardLogger

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configuration for IMPALA training."""
    # Environment settings
    model_path: str
    enzyme_library_path: str
    
    # Actor settings
    num_actors: int = 100
    actor_device: str = "cpu"
    
    # Learner settings
    learner_device: str = "cuda"
    batch_size: int = 32
    trajectory_length: int = 80
    
    # Training settings
    total_timesteps: int = 10_000_000
    learning_rate: float = 3e-4
    discount: float = 0.99
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 40.0
    
    # Environment config
    env_config: dict = field(default_factory=dict)
    
    # Self-play settings
    opponent_update_interval: int = 50000
    save_interval: int = 100000
    
    # Ray settings
    ray_num_cpus: Optional[int] = None
    ray_num_gpus: Optional[int] = None
    
    # Logging
    log_interval: int = 1000
    checkpoint_dir: str = "./checkpoints"
    

@ray.remote
class ActorWorker:
    """Ray actor that runs environment rollouts."""
    
    def __init__(
        self,
        worker_id: int,
        config: TrainingConfig,
        agent_role: str,
    ):
        self.worker_id = worker_id
        self.config = config
        self.agent_role = agent_role
        
        # Create environment
        # Load model and enzyme library
        import cobra
        import json
        
        base_model = cobra.io.load_json_model(config.model_path)
        
        # Load enzyme library directly from JSON
        with open(config.enzyme_library_path) as f:
            enzyme_data = json.load(f)
        enzyme_db = enzyme_data.get('enzymes', {})
            
        self.env = RedoxBalancerEnv(
            base_model=base_model,
            agent_role=agent_role,
            enzyme_db=enzyme_db,
            use_warm_start=True,
            env_config=config.env_config,
        )
        
        # Create local agent copy
        obs_dim = self.env.observation_space.shape[0]
        action_dim = self.env.action_space.shape[0]
        
        self.agent = IMPALAAgent(
            agent_role=agent_role,
            obs_dim=obs_dim,
            action_dim=action_dim,
            device=config.actor_device,
        )
        
        # Opponent agent for self-play
        opponent_role = "tumor" if agent_role == "sink_designer" else "sink_designer"
        self.opponent = IMPALAAgent(
            agent_role=opponent_role,
            obs_dim=obs_dim,
            action_dim=action_dim,
            device=config.actor_device,
        )
        
        self.num_episodes = 0
        self.num_timesteps = 0
        
    def get_num_episodes(self) -> int:
        """Return current episode count."""
        return self.num_episodes
        
    def run_episode(self, learner_weights: Dict[str, bytes]) -> Dict:
        """Run a single episode and return trajectory."""
        # Update network weights from learner
        self._update_weights(learner_weights)
        
        # Reset environment and agents
        obs, _ = self.env.reset()  # Unpack tuple
        self.agent.reset_hidden_state()
        self.opponent.reset_hidden_state()
        
        # Storage for trajectory
        observations = []
        actions = []
        rewards = []
        values = []
        action_log_probs = []
        dones = []
        infos = []
        
        done = False
        episode_return = 0
        episode_length = 0
        
        while not done and episode_length < self.config.trajectory_length:
            # Agent action - environment is always for our agent role
            action, info = self.agent.act(obs, deterministic=False)
            active_agent = self.agent
                
            # Step environment
            next_obs, reward, terminated, truncated, env_info = self.env.step(action)
            done = terminated or truncated
            
            # Store trajectory data
            observations.append(obs)
            actions.append(action)
            rewards.append(reward)
            values.append(info['value'])
            action_log_probs.append(info['log_prob'])
            dones.append(done)
            infos.append(env_info)
                
            episode_return += reward
            episode_length += 1
            obs = next_obs
            
        self.num_episodes += 1
        self.num_timesteps += episode_length
        
        # Memory cleanup - avoid returning large objects
        import gc
        del self.env.model  # Will be recreated on next reset
        gc.collect()
        
        # Convert to tensors with batch dimension
        trajectory = Trajectory(
            observations=torch.FloatTensor(np.array(observations)).unsqueeze(0),  # Add batch dim
            actions=torch.FloatTensor(np.array(actions)).unsqueeze(0),
            rewards=torch.FloatTensor(np.array(rewards)).unsqueeze(0),
            values=torch.FloatTensor(np.array(values)).unsqueeze(0),
            action_log_probs=torch.FloatTensor(np.array(action_log_probs)).unsqueeze(0),
            hidden_states=None,  # TODO: Add LSTM states
            dones=torch.FloatTensor(np.array(dones)).unsqueeze(0),
            infos=infos,
        )
        
        return {
            'trajectory': trajectory,
            'episode_return': episode_return,
            'episode_length': episode_length,
            'worker_id': self.worker_id,
            'num_episodes': self.num_episodes,
            'num_timesteps': self.num_timesteps,
        }
        
    def _update_weights(self, weights: Dict[str, bytes]):
        """Update agent weights from learner."""
        import io
        
        # Update main agent
        if self.agent_role in weights:
            buffer = io.BytesIO(weights[self.agent_role])
            state_dict = torch.load(buffer, map_location=self.config.actor_device)
            self.agent.network.load_state_dict(state_dict)
            
        # Update opponent
        opponent_role = "tumor" if self.agent_role == "sink_designer" else "sink_designer"
        if opponent_role in weights:
            buffer = io.BytesIO(weights[opponent_role])
            state_dict = torch.load(buffer, map_location=self.config.actor_device)
            # Only load if architectures match (same action dim)
            try:
                self.opponent.network.load_state_dict(state_dict)
            except RuntimeError as e:
                if "size mismatch" in str(e):
                    logger.debug(f"Skipping opponent weight update due to architecture mismatch: {e}")
                else:
                    raise


class IMPALATrainer:
    """Coordinates distributed IMPALA training."""
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        
        # Initialize Ray with memory safety settings
        if not ray.is_initialized():
            import json
            ray.init(
                num_cpus=config.ray_num_cpus,
                num_gpus=config.ray_num_gpus,
                _system_config={
                    "object_spilling_config": json.dumps({
                        "type": "filesystem",
                        "params": {"directory_path": str(Path.home() / "ray_spill")}
                    }),
                    "max_io_workers": 4,
                }
            )
            
        # Create learner agents
        # Load model and enzyme library
        import cobra
        import json
        base_model = cobra.io.load_json_model(config.model_path)
        with open(config.enzyme_library_path) as f:
            enzyme_db = json.load(f)
            
        env = RedoxBalancerEnv(
            base_model=base_model,
            agent_role="tumor",  # Just to get dimensions
            enzyme_db=enzyme_db,
            env_config=config.env_config,
        )
        obs_dim = env.observation_space.shape[0]
        action_dim = env.action_space.shape[0]
        env.close()
        
        self.tumor_agent = IMPALAAgent(
            agent_role="tumor",
            obs_dim=obs_dim,
            action_dim=action_dim,
            learning_rate=config.learning_rate,
            device=config.learner_device,
            entropy_coef_decay=0.997,     # slower decay
            min_entropy_coef=0.005,       # higher floor
        )
        
        self.sink_agent = IMPALAAgent(
            agent_role="sink_designer",
            obs_dim=obs_dim,
            action_dim=action_dim,
            learning_rate=config.learning_rate,
            device=config.learner_device,
        )
        
        # Create actor workers
        self.actors = []
        for i in range(config.num_actors):
            # Alternate between tumor and sink designer actors
            agent_role = "tumor" if i % 2 == 0 else "sink_designer"
            actor = ActorWorker.remote(i, config, agent_role)
            self.actors.append(actor)
            
        # Training statistics
        self.global_timesteps = 0
        self.episode_returns = deque(maxlen=100)
        self.episode_lengths = deque(maxlen=100)
        self.start_time = time.time()
        
        # Create checkpoint directory
        self.checkpoint_dir = Path(config.checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize TensorBoard logger
        self.tb_logger = TensorBoardLogger(str(self.checkpoint_dir / "tensorboard"))
        
    def train(self):
        """Main training loop."""
        logger.info(f"Starting IMPALA training with {self.config.num_actors} actors")
        
        # Start initial rollouts
        rollout_futures = []
        for actor in self.actors:
            weights = self._get_current_weights()
            future = actor.run_episode.remote(weights)
            rollout_futures.append(future)
            
        start_time = time.time()
        last_log_time = start_time
        last_save_time = start_time
        
        while self.global_timesteps < self.config.total_timesteps:
            # Wait for any rollout to complete
            ready_futures, rollout_futures = ray.wait(rollout_futures, num_returns=1)
            
            # Process completed rollout
            for future in ready_futures:
                result = ray.get(future)
                trajectory = result['trajectory']
                
                # Determine which agent to update
                worker_id = result['worker_id']
                agent_role = "tumor" if worker_id % 2 == 0 else "sink_designer"
                agent = self.tumor_agent if agent_role == "tumor" else self.sink_agent
                
                # Compute behavior policy log probs (from trajectory)
                behavior_logprobs = trajectory.action_log_probs  # Already has batch dim
                
                # Update agent with entropy annealing
                losses = agent.update(
                    trajectory, 
                    behavior_logprobs,
                    current_step=self.global_timesteps,
                    total_steps=self.config.total_timesteps
                )
                
                # Log training metrics
                self.tb_logger.log_training_metrics(losses, agent_role)
                
                # Update statistics
                self.global_timesteps += result['episode_length']
                self.episode_returns.append(result['episode_return'])
                self.episode_lengths.append(result['episode_length'])
                
                # Log episode metrics
                episode_metrics = {
                    'episode_return': result['episode_return'],
                    'episode_length': result['episode_length'],
                }
                if 'd2hg_level' in result:
                    episode_metrics['d2hg_level'] = result['d2hg_level']
                if 'growth_rate' in result:
                    episode_metrics['growth_rate'] = result['growth_rate']
                self.tb_logger.log_episode_metrics(episode_metrics)
                self.tb_logger.increment_step()
                
                # Start new rollout for this actor
                actor = self.actors[worker_id]
                weights = self._get_current_weights()
                new_future = actor.run_episode.remote(weights)
                rollout_futures.append(new_future)
                
            # Logging
            if time.time() - last_log_time > self.config.log_interval / 1000:
                self._log_statistics()
                last_log_time = time.time()
                
            # Save checkpoint
            if time.time() - last_save_time > self.config.save_interval / 1000:
                self._save_checkpoint()
                last_save_time = time.time()
                
        logger.info("Training completed!")
        self._save_checkpoint(final=True)
        
        # Return final statistics
        final_stats = {
            'mean_reward': np.mean(self.episode_returns) if self.episode_returns else 0,
            'min_reward': np.min(self.episode_returns) if self.episode_returns else 0,
            'max_reward': np.max(self.episode_returns) if self.episode_returns else 0,
            'episode_returns': list(self.episode_returns),
            'timesteps': self.global_timesteps,
        }
        return final_stats
        
    def _get_current_weights(self) -> Dict[str, bytes]:
        """Get current network weights as bytes."""
        import io
        
        weights = {}
        
        # Tumor agent weights
        buffer = io.BytesIO()
        torch.save(self.tumor_agent.network.state_dict(), buffer)
        weights['tumor'] = buffer.getvalue()
        
        # Sink designer weights
        buffer = io.BytesIO()
        torch.save(self.sink_agent.network.state_dict(), buffer)
        weights['sink_designer'] = buffer.getvalue()
        
        return weights
        
    def _log_statistics(self):
        """Log training statistics."""
        if len(self.episode_returns) == 0:
            return
            
        mean_return = np.mean(self.episode_returns)
        mean_length = np.mean(self.episode_lengths)
        
        elapsed_time = time.time() - self.start_time
        fps = self.global_timesteps / elapsed_time
        eps = len(self.episode_returns) / elapsed_time
        
        # Log to console
        logger.info(
            f"Timesteps: {self.global_timesteps:,} | "
            f"Episodes: {len(self.episode_returns)} | "
            f"Return: {mean_return:.6f} | "
            f"Length: {mean_length:.1f} | "
            f"FPS: {fps:.0f}"
        )
        
        # Log to TensorBoard
        self.tb_logger.log_performance_metrics({
            'steps_per_second': fps,
            'episodes_per_second': eps,
        })
        
    def _save_checkpoint(self, final: bool = False, lightweight: bool = False):
        """Save training checkpoint with compression.
        
        Args:
            final: If True, save as 'final' checkpoint
            lightweight: If True, save only policy weights (not optimizer state)
        """
        import gzip
        import io
        
        checkpoint_name = "final" if final else f"step_{self.global_timesteps}"
        if lightweight:
            checkpoint_name += "_light"
        checkpoint_path = self.checkpoint_dir / checkpoint_name
        checkpoint_path.mkdir(exist_ok=True)
        
        # Save compressed agent checkpoints
        for agent_name, agent in [("tumor", self.tumor_agent), ("sink_designer", self.sink_agent)]:
            # Get state dict
            state_dict = agent.network.state_dict()
            
            # Compress state dict
            buffer = io.BytesIO()
            torch.save(state_dict, buffer)
            compressed = gzip.compress(buffer.getvalue())
            
            # Save compressed file
            with open(checkpoint_path / f"{agent_name}_agent.pt.gz", 'wb') as f:
                f.write(compressed)
        
        # Save training state
        state = {
            'global_timesteps': self.global_timesteps,
            'config': self.config.__dict__,
            'checkpoint_format': 'compressed',
        }
        
        with open(checkpoint_path / "training_state.json", 'w') as f:
            json.dump(state, f, indent=2)
        
        # Save requirements for reproducibility
        import subprocess
        try:
            requirements = subprocess.check_output(['pip', 'freeze'], text=True)
            with open(checkpoint_path / "requirements.txt", 'w') as f:
                f.write(requirements)
        except:
            pass  # Non-critical if it fails
            
        logger.info(f"Saved compressed checkpoint to {checkpoint_path}")
        
        # Prune old checkpoints (keep only last 5 non-final checkpoints)
        # Only prune if this is a regular checkpoint, not final
        if not final:
            self._prune_old_checkpoints(keep_last=5)
    
    def load_checkpoint(self, checkpoint_path: str):
        """Load a checkpoint and resume training.
        
        Args:
            checkpoint_path: Path to checkpoint directory
        """
        import gzip
        import io
        
        checkpoint_path = Path(checkpoint_path)
        if not checkpoint_path.exists():
            raise ValueError(f"Checkpoint path does not exist: {checkpoint_path}")
            
        # Load training state
        with open(checkpoint_path / "training_state.json", 'r') as f:
            state = json.load(f)
            
        # Restore global timesteps
        self.global_timesteps = state['global_timesteps']
        logger.info(f"Resuming from checkpoint at step {self.global_timesteps:,}")
        
        # Load compressed agent states
        for agent_name, agent in [("tumor", self.tumor_agent), ("sink_designer", self.sink_agent)]:
            compressed_path = checkpoint_path / f"{agent_name}_agent.pt.gz"
            if compressed_path.exists():
                # Load and decompress
                with open(compressed_path, 'rb') as f:
                    compressed = f.read()
                decompressed = gzip.decompress(compressed)
                
                # Load state dict
                buffer = io.BytesIO(decompressed)
                state_dict = torch.load(buffer, map_location=self.config.learner_device)
                agent.network.load_state_dict(state_dict)
                logger.info(f"Loaded {agent_name} agent weights")
            else:
                logger.warning(f"No checkpoint found for {agent_name} agent")
                
        # Note: We're not saving/loading optimizer states or replay buffers
        # This is a limitation but keeps checkpoints smaller
        logger.info(f"Successfully resumed from {checkpoint_path}")
        logger.info(f"Continuing training from step {self.global_timesteps:,} to {self.config.total_timesteps:,}")
    
    def _prune_old_checkpoints(self, keep_last: int = 5):
        """Remove old checkpoints to save disk space."""
        # Get all step checkpoints (not 'final')
        step_checkpoints = []
        for path in self.checkpoint_dir.iterdir():
            if path.is_dir() and path.name.startswith("step_"):
                try:
                    timestep = int(path.name.split("_")[1])
                    step_checkpoints.append((timestep, path))
                except (IndexError, ValueError):
                    continue
        
        # Sort by timestep
        step_checkpoints.sort(key=lambda x: x[0])
        
        # Remove old checkpoints
        if len(step_checkpoints) > keep_last:
            for _, path in step_checkpoints[:-keep_last]:
                logger.info(f"Removing old checkpoint: {path}")
                shutil.rmtree(path)


def main():
    """Example training script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Train IMPALA agents")
    parser.add_argument("--model", required=True, help="Path to metabolic model")
    parser.add_argument("--enzymes", required=True, help="Path to enzyme library")
    parser.add_argument("--actors", type=int, default=100, help="Number of actors")
    parser.add_argument("--timesteps", type=int, default=10_000_000, help="Total timesteps")
    parser.add_argument("--checkpoint-dir", default="./checkpoints", help="Checkpoint directory")
    
    args = parser.parse_args()
    
    config = TrainingConfig(
        model_path=args.model,
        enzyme_library_path=args.enzymes,
        num_actors=args.actors,
        total_timesteps=args.timesteps,
        checkpoint_dir=args.checkpoint_dir,
    )
    
    trainer = IMPALATrainer(config)
    trainer.train()


if __name__ == "__main__":
    main()