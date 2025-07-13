#!/usr/bin/env python3
"""Debug script to verify reward calculation issues."""

import json
import cobra
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from redox_balancer.env.redox_env import RedoxBalancerEnv

# Load model and enzyme database
model = cobra.io.load_json_model("data/models/redox_core_v1.json")
enzyme_db = json.load(open("data/enzyme_library_redox.json"))["enzymes"]

# Create environment
env = RedoxBalancerEnv(model, agent_role="sink_designer", enzyme_db=enzyme_db)
obs, _ = env.reset()

print("=== REWARD DEBUGGING ===")
print(f"Model: {len(model.reactions)} reactions, {len(model.metabolites)} metabolites")
print(f"Enzymes available: {len(enzyme_db)}")
print()

# Check baseline
print("Baseline reward should be 0:", env._calculate_reward(env._solve_fba()))

# Try random sink actions
print("\nTesting random sink actions:")
action = np.random.uniform(low=0, high=100, size=env.action_space.shape)
for i in range(5):
    obs, r, done, truncated, info = env.step(action)
    print(f"Step {i+1} - Reward: {r:.6f}")
    if 'reward_components' in info:
        print(f"  Components: {info['reward_components']}")

# Check if any sink reactions were added
print(f"\nSink reactions added: {len([r for r in env.model.reactions if 'SINK_' in r.id])}")

# Check NADH flux
solution = env._solve_fba()
if solution.status == 'optimal':
    nadh_producing = sum(r.flux * r.metabolites.get(env.model.metabolites.get_by_id('nadh_c'), 0) 
                        for r in env.model.reactions if r.flux > 0)
    nadh_consuming = sum(-r.flux * r.metabolites.get(env.model.metabolites.get_by_id('nadh_c'), 0) 
                        for r in env.model.reactions if r.flux < 0)
    print(f"\nNADH flux analysis:")
    print(f"  Production: {nadh_producing:.3f}")
    print(f"  Consumption: {nadh_consuming:.3f}")
    print(f"  Net flux: {nadh_producing - nadh_consuming:.3f}")
    
    # Check sink reactions specifically
    print("\nSink reaction analysis:")
    for rxn in env.model.reactions:
        if 'SINK_' in rxn.id:
            print(f"  {rxn.id}: flux={rxn.flux:.6f}, bounds=[{rxn.lower_bound}, {rxn.upper_bound}], obj_coef={rxn.objective_coefficient}")
            # Show reaction stoichiometry
            print(f"    Reaction: {rxn.reaction}")
            
    # Debug reward components
    print("\nReward components:")
    print(f"  Baseline NADH flux: {env.baseline_nadh:.6f}")
    print(f"  Current NADH flux: {env._get_nadh_net_flux(solution):.6f}")
    
    # Calculate sink flux
    sink_flux = sum(
        solution.fluxes[rxn_id]
        for rxn_id in solution.fluxes.index
        if rxn_id.startswith("SINK_")
    )
    print(f"  Total sink flux: {sink_flux:.6f}")
    print(f"  Reward scale: 10.0 (normal mode)")
    print(f"  Expected r_metabolite: {10.0 * sink_flux:.6f}")
    
    # Check NADH flux by compartment
    print("\nNADH flux by compartment:")
    for comp in ['c', 'm', 'p']:
        prod = 0
        cons = 0
        for rxn_id, flux in solution.fluxes.items():
            if rxn_id in env.model.reactions:
                rxn = env.model.reactions.get_by_id(rxn_id)
                for metabolite, coeff in rxn.metabolites.items():
                    if f"nadh_{comp}" == metabolite.id.lower():
                        if flux > 0 and coeff > 0:  # Product
                            prod += flux * coeff
                        elif flux > 0 and coeff < 0:  # Reactant
                            cons += flux * abs(coeff)
        if prod > 0 or cons > 0:
            print(f"  {comp}: production={prod:.3f}, consumption={cons:.3f}, net={prod-cons:.3f}")