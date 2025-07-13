"""IMPALA agent implementation for self-play metabolic design."""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical, Normal
import numpy as np
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
import logging

from .networks import ActorCriticNetwork, SinkDesignerNetwork

logger = logging.getLogger(__name__)


@dataclass
class Trajectory:
    """Container for agent trajectories."""
    observations: torch.Tensor
    actions: torch.Tensor
    rewards: torch.Tensor
    values: torch.Tensor
    action_log_probs: torch.Tensor
    hidden_states: Optional[Tuple[torch.Tensor, torch.Tensor]]
    dones: torch.Tensor
    infos: List[Dict]


class IMPALAAgent:
    """IMPALA agent for metabolic self-play."""
    
    def __init__(
        self,
        agent_role: str,
        obs_dim: int = 250,
        action_dim: int = 10,
        learning_rate: float = 3e-4,
        discount: float = 0.99,
        entropy_coef: float = 0.01,
        entropy_coef_decay: float = 0.99,  # Multiplicative decay per update
        min_entropy_coef: float = 0.001,  # Minimum entropy coefficient
        value_coef: float = 0.5,
        max_grad_norm: float = 40.0,
        rho_bar: float = 1.0,
        c_bar: float = 1.0,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        **network_kwargs
    ):
        self.agent_role = agent_role
        self.device = torch.device(device)
        self.discount = discount
        self.entropy_coef = entropy_coef
        self.entropy_coef_decay = entropy_coef_decay
        self.min_entropy_coef = min_entropy_coef
        self.value_coef = value_coef
        self.max_grad_norm = max_grad_norm
        self.rho_bar = rho_bar
        self.c_bar = c_bar
        self.update_count = 0
        
        # Create network based on agent role
        if agent_role == "sink_designer":
            self.network = SinkDesignerNetwork(
                obs_dim=obs_dim,
                **network_kwargs
            ).to(self.device)
        else:
            self.network = ActorCriticNetwork(
                obs_dim=obs_dim,
                action_dim=action_dim,
                **network_kwargs
            ).to(self.device)
            
        self.optimizer = torch.optim.Adam(
            self.network.parameters(),
            lr=learning_rate
        )
        
        # Hidden state for recurrent network
        self.hidden_state = None
        
    def act(
        self,
        observation: np.ndarray,
        deterministic: bool = False
    ) -> Tuple[np.ndarray, Dict]:
        """Select action given observation."""
        # Handle gymnasium tuple format
        if isinstance(observation, tuple):
            observation = observation[0]
            
        with torch.no_grad():
            obs_tensor = torch.FloatTensor(observation).unsqueeze(0).to(self.device)
            
            output = self.network(obs_tensor, self.hidden_state)
            self.hidden_state = output['hidden_state']
            
            if self.agent_role == "sink_designer":
                # Handle structured actions for sink designer
                action, log_prob = self._sample_sink_action(output, deterministic)
            else:
                # Simple continuous actions for tumor agent
                action_logits = output['action_logits']
                
                if deterministic:
                    action = torch.tanh(action_logits).cpu().numpy()[0]
                    log_prob = 0.0
                else:
                    # Add noise for exploration
                    dist = Normal(torch.tanh(action_logits), 0.1)
                    action_sample = dist.sample()
                    action = action_sample.cpu().numpy()[0]
                    log_prob = dist.log_prob(action_sample).sum(dim=-1).item()
                    
            info = {
                'value': output['value'].item(),
                'log_prob': log_prob,
            }
            
        return action, info
        
    def _sample_sink_action(
        self,
        output: Dict[str, torch.Tensor],
        deterministic: bool
    ) -> Tuple[np.ndarray, float]:
        """Sample structured action for sink designer."""
        enzyme_logits = output['enzyme_logits'][0]  # [max_enzymes, n_enzymes]
        copy_numbers = output['copy_numbers'][0]    # [max_enzymes]
        compartment_logits = output['compartment_logits'][0]  # [max_enzymes, n_compartments]
        
        actions = []
        log_probs = []
        
        for i in range(enzyme_logits.shape[0]):
            # Sample enzyme
            if deterministic:
                enzyme_idx = enzyme_logits[i].argmax().item()
            else:
                enzyme_dist = Categorical(logits=enzyme_logits[i])
                enzyme_idx = enzyme_dist.sample().item()
                log_probs.append(enzyme_dist.log_prob(torch.tensor(enzyme_idx).to(enzyme_logits.device)))
                
            # Copy number (continuous, clipped to [1, 8])
            copy_num = copy_numbers[i].item()
            copy_num = max(1, min(8, int(copy_num + 0.5)))
            
            # Sample compartment
            if deterministic:
                comp_idx = compartment_logits[i].argmax().item()
            else:
                comp_dist = Categorical(logits=compartment_logits[i])
                comp_idx = comp_dist.sample().item()
                log_probs.append(comp_dist.log_prob(torch.tensor(comp_idx).to(compartment_logits.device)))
                
            actions.extend([enzyme_idx, copy_num, comp_idx])
            
        action = np.array(actions, dtype=np.float32)
        total_log_prob = sum(log_probs).item() if log_probs else 0.0
        
        return action, total_log_prob
        
    def compute_vtrace_loss(
        self,
        trajectory: Trajectory,
        behavior_policy_logprobs: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        """Compute V-trace loss for off-policy correction."""
        # Move everything to the correct device
        observations = trajectory.observations.to(self.device)
        actions = trajectory.actions.to(self.device)
        rewards = trajectory.rewards.to(self.device)
        values = trajectory.values.to(self.device)
        dones = trajectory.dones.to(self.device)
        behavior_policy_logprobs = behavior_policy_logprobs.to(self.device)
        
        # Assert all tensors are on the same device
        tensors = [observations, actions, rewards, values, dones, behavior_policy_logprobs]
        devices = [t.device for t in tensors]
        assert all(d == devices[0] for d in devices), f"Device mismatch: {devices}"
        
        batch_size, time_steps = rewards.shape
        
        # Forward pass through network - reshape for batch processing
        obs_flat = observations.view(-1, observations.shape[-1])
        output = self.network(obs_flat)
        
        policy_logits = output['action_logits'].view(batch_size, time_steps, -1)
        values_pred = output['value'].view(batch_size, time_steps)
        
        # Compute current policy log probabilities
        if self.agent_role == "sink_designer":
            # For sink designer, treat as continuous actions for simplicity
            # TODO: Implement structured action log probs
            action_dist = Normal(torch.tanh(policy_logits), 0.1)
            policy_logprobs = action_dist.log_prob(actions).sum(dim=-1)
        else:
            # Continuous actions with tanh squashing
            action_dist = Normal(torch.tanh(policy_logits), 0.1)
            policy_logprobs = action_dist.log_prob(actions).sum(dim=-1)
            
        # Compute importance sampling weights
        with torch.no_grad():
            # Ensure policy_logprobs has same shape as behavior_policy_logprobs
            if policy_logprobs.shape != behavior_policy_logprobs.shape:
                # Reshape if needed (e.g., from [batch*time, 1] to [batch, time])
                policy_logprobs = policy_logprobs.view(batch_size, time_steps)
                
            log_rhos = policy_logprobs - behavior_policy_logprobs
            rhos = torch.exp(log_rhos)
            clipped_rhos = torch.minimum(rhos, torch.tensor(self.rho_bar))
            cs = torch.minimum(rhos, torch.tensor(self.c_bar))
            
        # Compute V-trace targets (excluding last timestep for deltas)
        deltas = clipped_rhos[:, :-1] * (rewards[:, :-1] + self.discount * values[:, 1:] * (1 - dones[:, 1:]) - values[:, :-1])
        
        # Compute V-trace target recursively
        vtrace_targets = torch.zeros_like(values)
        # Bootstrap from the final value with the final TD error
        if time_steps > 1:
            # Use the predicted value for the last timestep plus any remaining advantage
            vtrace_targets[:, -1] = values_pred[:, -1]
        
        for t in reversed(range(time_steps - 1)):
            vtrace_targets[:, t] = values[:, t] + deltas[:, t] + \
                self.discount * cs[:, t] * (vtrace_targets[:, t + 1] - values[:, t + 1]) * (1 - dones[:, t + 1])
                
        # Compute losses (exclude last timestep)
        value_loss = 0.5 * F.mse_loss(values_pred[:, :-1], vtrace_targets[:, :-1].detach())
        
        # Policy gradient loss with V-trace advantages
        advantages = (vtrace_targets[:, :-1] - values_pred[:, :-1]).detach()
        policy_loss = -(policy_logprobs[:, :-1] * advantages).mean()
        
        # Entropy bonus
        if self.agent_role == "sink_designer":
            entropy = self._compute_sink_entropy(output)
        else:
            # For continuous actions, compute entropy from the distribution
            entropy = action_dist.entropy()[:, :-1].mean()
            
        # Total loss
        total_loss = policy_loss + self.value_coef * value_loss - self.entropy_coef * entropy
        
        return {
            'total_loss': total_loss,
            'policy_loss': policy_loss,
            'value_loss': value_loss,
            'entropy': entropy,
            'mean_rho': rhos.mean(),
        }
        
    def _compute_sink_logprobs(
        self,
        output: Dict[str, torch.Tensor],
        actions: torch.Tensor
    ) -> torch.Tensor:
        """Compute log probabilities for structured sink designer actions."""
        batch_size, time_steps, action_dim = actions.shape
        enzyme_logits = output['enzyme_logits']
        compartment_logits = output['compartment_logits']
        
        log_probs = []
        
        for t in range(time_steps):
            step_log_probs = []
            action_t = actions[:, t, :].view(batch_size, -1, 3)  # [batch, max_enzymes, 3]
            
            for i in range(action_t.shape[1]):
                enzyme_idx = action_t[:, i, 0].long()
                comp_idx = action_t[:, i, 2].long()
                
                # Enzyme log prob
                enzyme_dist = Categorical(logits=enzyme_logits[:, i, :])
                step_log_probs.append(enzyme_dist.log_prob(enzyme_idx))
                
                # Compartment log prob
                comp_dist = Categorical(logits=compartment_logits[:, i, :])
                step_log_probs.append(comp_dist.log_prob(comp_idx))
                
            log_probs.append(torch.stack(step_log_probs, dim=1).sum(dim=1))
            
        return torch.stack(log_probs, dim=1)
        
    def _compute_sink_entropy(self, output: Dict[str, torch.Tensor]) -> torch.Tensor:
        """Compute entropy for structured sink designer actions."""
        enzyme_dist = Categorical(logits=output['enzyme_logits'])
        comp_dist = Categorical(logits=output['compartment_logits'])
        
        return enzyme_dist.entropy().mean() + comp_dist.entropy().mean()
        
    def update(self, trajectory: Trajectory, behavior_policy_logprobs: torch.Tensor, 
               current_step: int = None, total_steps: int = None):
        """Update agent using V-trace with optional entropy annealing."""
        losses = self.compute_vtrace_loss(trajectory, behavior_policy_logprobs)
        
        self.optimizer.zero_grad()
        losses['total_loss'].backward()
        
        # Gradient clipping
        nn.utils.clip_grad_norm_(self.network.parameters(), self.max_grad_norm)
        
        self.optimizer.step()
        
        # Entropy annealing
        if current_step is not None and total_steps is not None:
            # Linear annealing that decays to 10% of original value
            frac = min(1.0, current_step / total_steps)
            annealed_entropy_coef = self.entropy_coef * (1 - 0.9 * frac)
            self.entropy_coef = max(self.min_entropy_coef, annealed_entropy_coef)
        else:
            # Fall back to multiplicative decay if step info not provided
            self.update_count += 1
            self.entropy_coef = max(
                self.min_entropy_coef,
                self.entropy_coef * self.entropy_coef_decay
            )
        
        # Add current entropy coefficient to losses for logging
        loss_dict = {k: v.item() for k, v in losses.items()}
        loss_dict['entropy_coef'] = self.entropy_coef
        
        return loss_dict
        
    def save(self, path: str):
        """Save agent state."""
        torch.save({
            'network_state_dict': self.network.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'agent_role': self.agent_role,
        }, path)
        
    def load(self, path: str):
        """Load agent state (supports compressed files)."""
        import gzip
        
        if path.endswith('.gz'):
            # Load compressed checkpoint
            with gzip.open(path, 'rb') as f:
                state_dict = torch.load(f, map_location=self.device)
            self.network.load_state_dict(state_dict)
        else:
            # Load regular checkpoint
            checkpoint = torch.load(path, map_location=self.device)
            if 'network_state_dict' in checkpoint:
                self.network.load_state_dict(checkpoint['network_state_dict'])
                self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            else:
                # Just state dict
                self.network.load_state_dict(checkpoint)
        
    def reset_hidden_state(self):
        """Reset LSTM hidden state."""
        self.hidden_state = None