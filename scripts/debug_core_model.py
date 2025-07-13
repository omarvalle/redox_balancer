#!/usr/bin/env python3
"""Debug core model feasibility issues."""

import cobra
import sys
sys.path.insert(0, 'src')
from redox_balancer.utils.medium import HUMAN_MINIMAL_MEDIUM, set_medium

# Load model
model = cobra.io.load_json_model("data/models/redox_core_v1.json")
print(f"Model: {len(model.reactions)} reactions, {len(model.metabolites)} metabolites")

# Apply medium
set_medium(model, HUMAN_MINIMAL_MEDIUM)

# Try to identify bottleneck by relaxing biomass
print("\nChecking feasibility by gradually relaxing biomass...")
biomass_rxn = model.reactions.BIOMASS_maintenance

# Store original
orig_lb = biomass_rxn.lower_bound

# Try different biomass levels
for factor in [0.0, 0.001, 0.01, 0.1, 0.5, 1.0]:
    biomass_rxn.lower_bound = 0
    biomass_rxn.upper_bound = factor
    sol = model.optimize()
    print(f"  Max biomass {factor}: status={sol.status}, growth={sol.objective_value:.6f}")

# Check if we can produce ATP
print("\nChecking ATP production...")
model.objective = "ATPM"
sol = model.optimize()
print(f"  Max ATP maintenance: {sol.objective_value:.6f}")

# Check key metabolites
print("\nChecking key metabolite production...")
for met_id in ["atp_c", "nadh_c", "nad_c", "g6p_c"]:
    if met_id in model.metabolites:
        # Create demand reaction
        met = model.metabolites.get_by_id(met_id)
        demand = cobra.Reaction(f"DM_{met_id}_test")
        demand.add_metabolites({met: -1})
        demand.bounds = (0, 1000)
        model.add_reactions([demand])
        
        model.objective = demand
        sol = model.optimize()
        print(f"  {met_id}: max production = {sol.objective_value:.6f}")
        
        model.remove_reactions([demand])

# Look for missing transporters
print("\nChecking for amino acid availability...")
biomass_rxn = model.reactions.BIOMASS_maintenance
for met, coeff in biomass_rxn.metabolites.items():
    if coeff < 0 and met.compartment == "c":  # Cytosolic reactants
        # Check if there's an exchange for this metabolite
        ex_id = f"EX_{met.id[:-2]}_e"  # Remove _c, add _e
        if ex_id in model.reactions:
            ex_rxn = model.reactions.get_by_id(ex_id)
            print(f"  {met.id}: exchange exists ({ex_id}), bounds={ex_rxn.bounds}")
        else:
            # Check for any reaction that produces this metabolite
            producing_rxns = [r for r in met.reactions if r.metabolites[met] > 0]
            print(f"  {met.id}: NO exchange, {len(producing_rxns)} producing reactions")