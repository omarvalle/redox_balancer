#!/usr/bin/env python3
"""Debug sink reactions to understand why they have no flux."""

import json
import cobra
import numpy as np
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from redox_balancer.env.redox_env import RedoxBalancerEnv

# Load model and enzyme database
model = cobra.io.load_json_model("data/models/redox_core_v1.json")
enzyme_db = json.load(open("data/enzyme_library_redox.json"))["enzymes"]

# Check biomass reaction
print("=== BIOMASS REACTION ===")
biomass_rxns = [r for r in model.reactions if 'biomass' in r.id.lower()]
for rxn in biomass_rxns:
    print(f"{rxn.id}: obj_coef={rxn.objective_coefficient}")

# Create environment and add sinks
env = RedoxBalancerEnv(model, agent_role="sink_designer", enzyme_db=enzyme_db)
env.reset()

# Add maximum sink reactions
action = np.ones(env.action_space.shape) * 100  # Max expression
env.step(action)

print("\n=== SINK REACTIONS ===")
for rxn in env.model.reactions:
    if 'SINK_' in rxn.id:
        print(f"\n{rxn.id}:")
        print(f"  Bounds: [{rxn.lower_bound}, {rxn.upper_bound}]")
        print(f"  Objective coefficient: {rxn.objective_coefficient}")
        print(f"  Metabolites: {rxn.reaction}")
        
        # Check if NADH is involved
        has_nadh = any('nadh' in m.id.lower() for m in rxn.metabolites)
        print(f"  Involves NADH: {has_nadh}")

# Try to force flux through a sink
print("\n=== FORCING SINK FLUX ===")
# Find a NADH sink
nadh_sinks = [r for r in env.model.reactions if 'SINK_' in r.id and 
              any('nadh' in m.id.lower() for m in r.metabolites)]

if nadh_sinks:
    sink = nadh_sinks[0]
    print(f"Testing {sink.id}")
    
    # Save original biomass coefficient
    biomass_rxn = biomass_rxns[0]
    orig_bio_coef = biomass_rxn.objective_coefficient
    
    # Temporarily make sink the main objective
    biomass_rxn.objective_coefficient = 0
    sink.objective_coefficient = 1
    
    solution = env.model.optimize()
    print(f"  With sink as objective: flux={sink.flux:.6f}, biomass={biomass_rxn.flux:.6f}")
    
    # Restore original
    biomass_rxn.objective_coefficient = orig_bio_coef
    sink.objective_coefficient = -1e-3
    
    solution = env.model.optimize()
    print(f"  With original objective: flux={sink.flux:.6f}, biomass={biomass_rxn.flux:.6f}")