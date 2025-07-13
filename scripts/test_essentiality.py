#!/usr/bin/env python3
"""Test essentiality analysis."""

import cobra
from cobra.flux_analysis import single_reaction_deletion
import sys
sys.path.insert(0, 'src')
from redox_balancer.utils.medium import HUMAN_MINIMAL_MEDIUM, set_medium

# Create a simple test model
model = cobra.io.load_json_model("data/models/test_full_model.json")
print(f"Test model: {len(model.reactions)} reactions")

# Apply medium
set_medium(model, HUMAN_MINIMAL_MEDIUM)

# Check baseline growth
sol = model.optimize()
print(f"Baseline growth: {sol.objective_value:.6f}")

# Test single reaction deletion
print("\nTesting single reaction deletion...")
ess = single_reaction_deletion(model, processes=1)
print(f"Result shape: {ess.shape}")
print(f"Columns: {list(ess.columns)}")

# Show first few rows
print("\nFirst 5 results:")
print(ess.head())

# Count essential
essential_count = len(ess[ess["growth"] < 1e-6])
print(f"\nEssential reactions: {essential_count}/{len(model.reactions)}")