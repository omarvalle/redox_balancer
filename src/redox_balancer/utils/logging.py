"""Logging utilities for training monitoring."""

import torch
from torch.utils.tensorboard import SummaryWriter
from typing import Dict, Optional
import numpy as np
from pathlib import Path


class TensorBoardLogger:
    """TensorBoard logger for IMPALA training metrics."""
    
    def __init__(self, log_dir: str):
        """Initialize TensorBoard writer."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.writer = SummaryWriter(str(self.log_dir))
        self.global_step = 0
        
    def log_scalar(self, tag: str, value: float, step: Optional[int] = None):
        """Log a scalar value."""
        if step is None:
            step = self.global_step
        self.writer.add_scalar(tag, value, step)
        
    def log_scalars(self, tag: str, values: Dict[str, float], step: Optional[int] = None):
        """Log multiple scalars under the same tag."""
        if step is None:
            step = self.global_step
        self.writer.add_scalars(tag, values, step)
        
    def log_histogram(self, tag: str, values: np.ndarray, step: Optional[int] = None):
        """Log a histogram of values."""
        if step is None:
            step = self.global_step
        self.writer.add_histogram(tag, values, step)
        
    def log_training_metrics(self, metrics: Dict[str, float], agent_role: str):
        """Log standard training metrics."""
        # Loss components
        self.log_scalar(f"{agent_role}/loss/total", metrics.get('total_loss', 0))
        self.log_scalar(f"{agent_role}/loss/policy", metrics.get('policy_loss', 0))
        self.log_scalar(f"{agent_role}/loss/value", metrics.get('value_loss', 0))
        self.log_scalar(f"{agent_role}/loss/entropy", metrics.get('entropy', 0))
        
        # Learning metrics
        self.log_scalar(f"{agent_role}/learning/mean_rho", metrics.get('mean_rho', 1.0))
        self.log_scalar(f"{agent_role}/learning/entropy_coef", metrics.get('entropy_coef', 0.01))
        
    def log_episode_metrics(self, metrics: Dict[str, float]):
        """Log episode-level metrics."""
        self.log_scalar("episode/return", metrics.get('episode_return', 0))
        self.log_scalar("episode/length", metrics.get('episode_length', 0))
        self.log_scalar("episode/d2hg_level", metrics.get('d2hg_level', 0))
        self.log_scalar("episode/growth_rate", metrics.get('growth_rate', 0))
        
    def log_performance_metrics(self, metrics: Dict[str, float]):
        """Log performance metrics."""
        self.log_scalar("performance/steps_per_second", metrics.get('steps_per_second', 0))
        self.log_scalar("performance/episodes_per_second", metrics.get('episodes_per_second', 0))
        self.log_scalar("performance/cache_hit_rate", metrics.get('cache_hit_rate', 0))
        
    def increment_step(self):
        """Increment global step counter."""
        self.global_step += 1
        
    def close(self):
        """Close TensorBoard writer."""
        self.writer.close()