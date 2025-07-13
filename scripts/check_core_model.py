#!/usr/bin/env python3
"""Check the core model for exchange reactions and growth."""

import cobra
import sys

model_path = sys.argv[1] if len(sys.argv) > 1 else "data/models/redox_core_v1.json"
model = cobra.io.load_json_model(model_path)

print(f"Model: {len(model.reactions)} reactions, {len(model.metabolites)} metabolites")
print(f"Exchanges: {len(model.exchanges)}")

if model.exchanges:
    print("\nExchange reactions:")
    for ex in list(model.exchanges)[:10]:  # First 10
        print(f"  {ex.id}: {ex.lower_bound} to {ex.upper_bound}")
else:
    print("\nNO EXCHANGE REACTIONS FOUND!")

print("\nBiomass reaction:")
for rxn in model.reactions:
    if rxn.objective_coefficient != 0:
        print(f"  {rxn.id}: coefficient={rxn.objective_coefficient}")

# Test growth
solution = model.optimize()
print(f"\nOptimization status: {solution.status}")
print(f"Growth rate: {solution.objective_value:.6f}")

# Check for key exchanges
key_exchanges = ["EX_glc__D_e", "EX_o2_e", "EX_h2o_e", "EX_co2_e", "EX_nh4_e", "EX_pi_e"]
print("\nKey exchange reactions:")
for ex_id in key_exchanges:
    if ex_id in model.reactions:
        rxn = model.reactions.get_by_id(ex_id)
        print(f"  {ex_id}: {rxn.lower_bound} to {rxn.upper_bound}")
    else:
        print(f"  {ex_id}: MISSING")