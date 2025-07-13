#!/usr/bin/env python3
"""Check model consistency."""

import cobra
import sys
sys.path.insert(0, 'src')
from redox_balancer.utils.medium import HUMAN_MINIMAL_MEDIUM, set_medium
from cobra.flux_analysis import fastcc

core = cobra.io.load_json_model("data/models/redox_core_v1.json")
set_medium(core, HUMAN_MINIMAL_MEDIUM)

# fastcc returns a consistent model
try:
    consistent_model = fastcc(core, zero_cutoff=1e-6)
    consistent_rxns = set(r.id for r in consistent_model.reactions)
    all_rxns = set(r.id for r in core.reactions)
    inconsistent = all_rxns - consistent_rxns
    
    print("Reactions that make the model infeasible (first 20):")
    print(list(inconsistent)[:20])
    print("Total inconsistent reactions:", len(inconsistent))
except Exception as e:
    print(f"FastCC error: {e}")
    
    # Alternative - check ATPM constraint
    print("\nChecking if ATPM constraint causes infeasibility...")
    if "ATPM" in core.reactions:
        core.reactions.ATPM.lower_bound = 0
        sol = core.optimize()
        print(f"With ATPM=0: status={sol.status}")
        
    # Check biomass components
    print("\nChecking biomass precursors that cannot be produced...")
    biomass = core.reactions.BIOMASS_reaction
    missing = []
    for met in biomass.metabolites:
        if met.id.endswith('_c'):  # Cytosolic metabolites
            # Check if any reaction produces this metabolite
            producing = [r for r in met.reactions if r.metabolites[met] > 0]
            if len(producing) == 0:
                missing.append(met.id)
                
    print(f"Biomass components with no producing reactions: {missing[:10]}")