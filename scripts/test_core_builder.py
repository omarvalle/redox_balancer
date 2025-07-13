#!/usr/bin/env python3
"""Test the core builder with a simple model."""

import cobra
from cobra import Model, Reaction, Metabolite
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Create a simple test model with biomass
model = Model("test_model")

# Add metabolites
glc_e = Metabolite("glc__D_e", compartment="e")
glc_c = Metabolite("glc__D_c", compartment="c") 
o2_e = Metabolite("o2_e", compartment="e")
o2_c = Metabolite("o2_c", compartment="c")
co2_e = Metabolite("co2_e", compartment="e")
co2_c = Metabolite("co2_c", compartment="c")
h2o_e = Metabolite("h2o_e", compartment="e")
h2o_c = Metabolite("h2o_c", compartment="c")
nadh_c = Metabolite("nadh_c", compartment="c")
nad_c = Metabolite("nad_c", compartment="c")
atp_c = Metabolite("atp_c", compartment="c")
adp_c = Metabolite("adp_c", compartment="c")
pyr_c = Metabolite("pyr_c", compartment="c")
nh4_e = Metabolite("nh4_e", compartment="e")
pi_e = Metabolite("pi_e", compartment="e")
h_e = Metabolite("h_e", compartment="e")
biomass = Metabolite("biomass", compartment="c")

model.add_metabolites([glc_e, glc_c, o2_e, o2_c, co2_e, co2_c, h2o_e, h2o_c,
                      nadh_c, nad_c, atp_c, adp_c, pyr_c, nh4_e, pi_e, h_e, biomass])

# Exchange reactions
ex_glc = Reaction("EX_glc__D_e")
ex_glc.add_metabolites({glc_e: -1})
ex_glc.bounds = (-10, 0)

ex_o2 = Reaction("EX_o2_e")
ex_o2.add_metabolites({o2_e: -1})
ex_o2.bounds = (-20, 0)

ex_co2 = Reaction("EX_co2_e")
ex_co2.add_metabolites({co2_e: 1})
ex_co2.bounds = (0, 1000)

ex_h2o = Reaction("EX_h2o_e")
ex_h2o.add_metabolites({h2o_e: -1})
ex_h2o.bounds = (-1000, 1000)

ex_nh4 = Reaction("EX_nh4_e")
ex_nh4.add_metabolites({nh4_e: -1})
ex_nh4.bounds = (-5, 0)

ex_pi = Reaction("EX_pi_e")
ex_pi.add_metabolites({pi_e: -1})
ex_pi.bounds = (-3, 0)

ex_h = Reaction("EX_h_e")
ex_h.add_metabolites({h_e: -1})
ex_h.bounds = (-1000, 1000)

# Transport reactions
glct = Reaction("GLCt")
glct.add_metabolites({glc_e: -1, glc_c: 1})
glct.bounds = (-10, 10)

o2t = Reaction("O2t")
o2t.add_metabolites({o2_e: -1, o2_c: 1})
o2t.bounds = (-20, 20)

# Simplified glycolysis with NAD/NADH
glyc = Reaction("GLYC")
glyc.add_metabolites({glc_c: -1, nad_c: -2, pyr_c: 2, nadh_c: 2, atp_c: 2, adp_c: -2})
glyc.bounds = (0, 100)
glyc.subsystem = "Glycolysis"

# ATP maintenance
atpm = Reaction("ATPM")
atpm.add_metabolites({atp_c: -1, adp_c: 1})
atpm.bounds = (0, 10)  # Allow 0 for feasibility

# Simplified respiration  
resp = Reaction("RESP")
resp.add_metabolites({nadh_c: -1, o2_c: -0.5, nad_c: 1, h2o_c: 1, atp_c: 2.5, adp_c: -2.5})
resp.bounds = (0, 100)
resp.subsystem = "Oxidative phosphorylation"

# Biomass reaction
biomass_rxn = Reaction("biomass_reaction")
biomass_rxn.add_metabolites({
    glc_c: -0.1,
    atp_c: -10,
    adp_c: 10,
    biomass: 1
})
biomass_rxn.bounds = (0, 10)

# Add all reactions
model.add_reactions([ex_glc, ex_o2, ex_co2, ex_h2o, ex_nh4, ex_pi, ex_h,
                    glct, o2t, glyc, atpm, resp, biomass_rxn])

# Set objective after adding to model
model.objective = "biomass_reaction"

# Save test model
cobra.io.save_json_model(model, "data/models/test_full_model.json")

# Test that it can grow
sol = model.optimize()
print(f"Test model status: {sol.status}")
print(f"Test model growth: {sol.objective_value:.6f}")

# Now test the core builder
from build_redox_core import extract_redox_core

core = extract_redox_core(model, target_reactions=10)
print(f"\nCore model: {len(core.reactions)} reactions")
print("Core reactions:", [r.id for r in core.reactions])

# Test core growth
sol = core.optimize()
print(f"\nCore model status: {sol.status}")  
print(f"Core model growth: {sol.objective_value:.6f}")

# Check key reactions are present
for rxn_id in ["EX_glc__D_e", "EX_o2_e", "biomass_reaction", "ATPM"]:
    if rxn_id in core.reactions:
        rxn = core.reactions.get_by_id(rxn_id)
        print(f"{rxn_id}: bounds={rxn.bounds}, objective={rxn.objective_coefficient}")
    else:
        print(f"{rxn_id}: MISSING!")