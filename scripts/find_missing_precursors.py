#!/usr/bin/env python3
"""Find missing biomass precursors in core model."""

import cobra
import sys
sys.path.insert(0, 'src')
from redox_balancer.utils.medium import HUMAN_MINIMAL_MEDIUM, set_medium

core = cobra.io.load_json_model("data/models/redox_core_v1.json")
set_medium(core, HUMAN_MINIMAL_MEDIUM)
core.objective = "BIOMASS_reaction"

# Find metabolites in biomass reaction
biomass = core.reactions.get_by_id("BIOMASS_reaction")
targets = [m.id for m in biomass.metabolites]

# For each target metabolite, test if it can be produced from the medium
missing = []
for met_id in targets:
    demand = cobra.Reaction(f"DM_{met_id}")
    demand.add_metabolites({core.metabolites.get_by_id(met_id): -1})
    core.add_reactions([demand])
    core.objective = demand
    sol = core.optimize()
    if sol.status != "optimal" or sol.fluxes[demand.id] < 1e-6:
        missing.append(met_id)
    core.reactions.remove(demand)

print("First 10 missing biomass precursors:", missing[:10])