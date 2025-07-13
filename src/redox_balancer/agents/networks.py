"""Neural network architectures for IMPALA agents."""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple, Optional
import numpy as np


class ActorCriticNetwork(nn.Module):
    """Shared actor-critic network for both tumor and sink designer agents."""
    
    def __init__(
        self,
        obs_dim: int = 250,
        action_dim: int = 10,  # Default for tumor agent
        hidden_dim: int = 256,
        lstm_layers: int = 1,
        embedding_dim: int = 128,
    ):
        super().__init__()
        
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.hidden_dim = hidden_dim
        
        # Metabolite embedding layer
        self.metabolite_embed = nn.Sequential(
            nn.Linear(obs_dim, embedding_dim),
            nn.LayerNorm(embedding_dim),
            nn.ReLU(),
            nn.Linear(embedding_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
        )
        
        # LSTM for temporal dependencies
        self.lstm = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=lstm_layers,
            batch_first=True,
        )
        
        # Separate heads for actor and critic
        self.actor_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
        )
        
        self.critic_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
        
        # Initialize weights
        self._initialize_weights()
        
    def _initialize_weights(self):
        """Initialize network weights using Xavier initialization."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.LSTM):
                for name, param in m.named_parameters():
                    if 'weight' in name:
                        nn.init.xavier_uniform_(param)
                    elif 'bias' in name:
                        nn.init.constant_(param, 0)
                        
    def forward(
        self,
        obs: torch.Tensor,
        hidden_state: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        sequence_length: Optional[int] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass through the network.
        
        Args:
            obs: Observation tensor [batch_size, seq_len, obs_dim] or [batch_size, obs_dim]
            hidden_state: Optional LSTM hidden state (h, c)
            sequence_length: Length of sequences for LSTM
            
        Returns:
            Dictionary containing:
                - 'action_logits': Raw policy outputs
                - 'value': State value estimate
                - 'hidden_state': Updated LSTM state
        """
        # Handle both sequential and non-sequential inputs
        if obs.dim() == 2:
            obs = obs.unsqueeze(1)  # Add sequence dimension
            
        batch_size, seq_len, _ = obs.shape
        
        # Embed observations
        embedded = self.metabolite_embed(obs)
        
        # Pass through LSTM
        if hidden_state is None:
            h0 = torch.zeros(self.lstm.num_layers, batch_size, self.hidden_dim).to(obs.device)
            c0 = torch.zeros(self.lstm.num_layers, batch_size, self.hidden_dim).to(obs.device)
            hidden_state = (h0, c0)
            
        lstm_out, new_hidden = self.lstm(embedded, hidden_state)
        
        # Use last output for predictions
        if sequence_length is not None:
            # Handle variable length sequences
            last_outputs = []
            for i, length in enumerate(sequence_length):
                last_outputs.append(lstm_out[i, length - 1])
            features = torch.stack(last_outputs)
        else:
            features = lstm_out[:, -1, :]
            
        # Compute policy and value
        action_logits = self.actor_head(features)
        value = self.critic_head(features).squeeze(-1)
        
        return {
            'action_logits': action_logits,
            'value': value,
            'hidden_state': new_hidden,
        }


class SinkDesignerNetwork(ActorCriticNetwork):
    """Specialized network for sink designer agent with discrete-continuous actions."""
    
    def __init__(
        self,
        obs_dim: int = 250,
        n_enzymes: int = 100,  # Size of enzyme library
        n_compartments: int = 3,  # c, m, p
        max_enzymes_per_construct: int = 4,
        hidden_dim: int = 256,
        **kwargs
    ):
        # Action dim = enzyme selection + copy numbers + compartments
        action_dim = max_enzymes_per_construct * (1 + 1 + 1)
        super().__init__(obs_dim, action_dim, hidden_dim, **kwargs)
        
        self.n_enzymes = n_enzymes
        self.n_compartments = n_compartments
        self.max_enzymes = max_enzymes_per_construct
        
        # Separate heads for different action types
        self.enzyme_selector = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, n_enzymes * max_enzymes_per_construct),
        )
        
        self.copy_number_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, max_enzymes_per_construct),
        )
        
        self.compartment_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, n_compartments * max_enzymes_per_construct),
        )
        
    def forward(
        self,
        obs: torch.Tensor,
        hidden_state: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        sequence_length: Optional[int] = None,
    ) -> Dict[str, torch.Tensor]:
        """Forward pass with structured action outputs for sink designer."""
        # Get base features
        base_out = super().forward(obs, hidden_state, sequence_length)
        
        # Extract features for specialized heads
        if obs.dim() == 2:
            obs = obs.unsqueeze(1)
            
        batch_size = obs.shape[0]
        
        # Get LSTM features
        embedded = self.metabolite_embed(obs)
        lstm_out, _ = self.lstm(embedded, hidden_state)
        features = lstm_out[:, -1, :]
        
        # Compute specialized actions
        enzyme_logits = self.enzyme_selector(features).view(
            batch_size, self.max_enzymes, self.n_enzymes
        )
        copy_numbers = torch.sigmoid(self.copy_number_head(features)) * 8  # 0-8 copies
        compartment_logits = self.compartment_head(features).view(
            batch_size, self.max_enzymes, self.n_compartments
        )
        
        return {
            **base_out,
            'enzyme_logits': enzyme_logits,
            'copy_numbers': copy_numbers,
            'compartment_logits': compartment_logits,
        }