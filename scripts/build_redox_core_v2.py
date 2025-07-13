#!/usr/bin/env python3
"""Build a core metabolic model focused on redox metabolism - Version 2.

This version ensures essential exchange reactions are preserved.
"""

import argparse
import json
import logging
from pathlib import Path
import cobra
from cobra.io import save_json_model


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_redox_core(model, target_reactions=400):
    """Extract core reactions focused on NAD(P)H metabolism."""
    
    # Essential exchange reactions to ALWAYS keep
    essential_exchanges = [
        "EX_glc__D_e", "EX_glc_e", "EX_glucose_e",  # Glucose
        "EX_o2_e", "EX_O2_e",  # Oxygen
        "EX_co2_e", "EX_CO2_e",  # CO2
        "EX_h2o_e", "EX_H2O_e",  # Water
        "EX_nh4_e", "EX_NH4_e", "EX_nh3_e",  # Nitrogen
        "EX_pi_e", "EX_PI_e",  # Phosphate
        "EX_so4_e", "EX_SO4_e",  # Sulfate
        "EX_h_e", "EX_H_e",  # Protons
        # Amino acids (at least some)
        "EX_glu__L_e", "EX_gln__L_e", "EX_asp__L_e", "EX_asn__L_e",
        "EX_ala__L_e", "EX_gly_e", "EX_ser__L_e", "EX_leu__L_e",
        "EX_ile__L_e", "EX_val__L_e", "EX_lys__L_e", "EX_arg__L_e",
        "EX_his__L_e", "EX_phe__L_e", "EX_tyr__L_e", "EX_trp__L_e",
        "EX_met__L_e", "EX_cys__L_e", "EX_thr__L_e", "EX_pro__L_e"
    ]
    
    # Key pathways to include
    key_pathways = [
        # Central carbon metabolism
        "Glycolysis", "Pentose phosphate", "TCA cycle", "Citric acid cycle",
        # Redox-related
        "NADH", "NADPH", "Oxidative phosphorylation", "Electron transport",
        # Amino acid metabolism (redox-dependent)
        "Glutamate", "Aspartate", "Malate",
        # Energy
        "ATP", "ADP"
    ]
    
    # Key metabolites to ensure connectivity
    key_metabolites = [
        "nad_c", "nadh_c", "nadp_c", "nadph_c",
        "nad_m", "nadh_m", "nadp_m", "nadph_m",
        "glc__D_c", "pyr_c", "accoa_c", "akg_c",
        "mal__L_c", "oaa_c", "glu__L_c", "asp__L_c",
        "atp_c", "adp_c", "o2_c", "co2_c", "h2o_c",
        "nh4_c", "pi_c", "h_c"
    ]
    
    # Start with essential reactions
    core_reactions = set()
    
    # 1. Add essential exchange reactions FIRST
    for ex_id in essential_exchanges:
        if ex_id in model.reactions:
            core_reactions.add(ex_id)
            logger.debug(f"Added essential exchange: {ex_id}")
    
    # 2. Add biomass reaction(s)
    if model.objective:
        for rxn in model.reactions:
            if rxn.objective_coefficient != 0:
                core_reactions.add(rxn.id)
                logger.info(f"Added biomass reaction: {rxn.id}")
    
    # 3. Add demand/sink reactions
    for rxn in model.reactions:
        if rxn.id.startswith(("DM_", "SK_", "sink_")):
            core_reactions.add(rxn.id)
    
    # 4. Add reactions containing NAD(P)H
    for rxn in model.reactions:
        metabolite_ids = [m.id for m in rxn.metabolites]
        if any("nad" in m_id.lower() for m_id in metabolite_ids):
            core_reactions.add(rxn.id)
    
    # 5. Add reactions from key pathways
    for rxn in model.reactions:
        if rxn.subsystem and any(pathway.lower() in rxn.subsystem.lower() 
                                for pathway in key_pathways):
            core_reactions.add(rxn.id)
    
    # 6. Add reactions containing key metabolites
    for met_id in key_metabolites:
        if met_id in model.metabolites:
            met = model.metabolites.get_by_id(met_id)
            for rxn in met.reactions:
                core_reactions.add(rxn.id)
    
    # 7. Add ATP maintenance
    for rxn in model.reactions:
        if "ATPM" in rxn.id or "atp maintenance" in rxn.name.lower():
            core_reactions.add(rxn.id)
            logger.info(f"Added ATP maintenance: {rxn.id}")
    
    current_count = len(core_reactions)
    logger.info(f"Core reactions before pruning: {current_count}")
    
    # If we have too many reactions, prioritize by flux in FBA
    # BUT never remove essential exchanges or biomass
    if len(core_reactions) > target_reactions:
        logger.info("Pruning reactions based on flux magnitude...")
        
        # Identify reactions that can be pruned (not essential)
        essential_rxns = set()
        for ex_id in essential_exchanges:
            if ex_id in model.reactions:
                essential_rxns.add(ex_id)
        
        # Add biomass
        for rxn in model.reactions:
            if rxn.objective_coefficient != 0:
                essential_rxns.add(rxn.id)
        
        # Create temporary model with core reactions
        temp_model = model.copy()
        rxns_to_remove = [r for r in temp_model.reactions if r.id not in core_reactions]
        temp_model.remove_reactions(rxns_to_remove)
        
        # Set medium if needed
        try:
            from redox_balancer.utils.medium import set_medium, HUMAN_MINIMAL_MEDIUM
            set_medium(temp_model, HUMAN_MINIMAL_MEDIUM)
        except:
            # If no medium module, just ensure glucose and O2 are open
            if "EX_glc__D_e" in temp_model.reactions:
                temp_model.reactions.get_by_id("EX_glc__D_e").lower_bound = -10
            if "EX_o2_e" in temp_model.reactions:
                temp_model.reactions.get_by_id("EX_o2_e").lower_bound = -20
        
        # Run FBA
        solution = temp_model.optimize()
        if solution.status == "optimal":
            # Sort reactions by absolute flux, excluding essential ones
            flux_ranking = []
            for rxn_id in core_reactions:
                if rxn_id not in essential_rxns and rxn_id in solution.fluxes:
                    flux_ranking.append((rxn_id, abs(solution.fluxes[rxn_id])))
            
            flux_ranking.sort(key=lambda x: x[1], reverse=True)
            
            # Calculate how many non-essential reactions we can keep
            num_essential = len(essential_rxns)
            num_to_keep = target_reactions - num_essential
            
            # Keep essential + top non-essential by flux
            pruned_reactions = essential_rxns.copy()
            for rxn_id, _ in flux_ranking[:num_to_keep]:
                pruned_reactions.add(rxn_id)
            
            core_reactions = pruned_reactions
            logger.info(f"Pruned to {len(core_reactions)} reactions ({num_essential} essential)")
    
    # Create the core model
    core_model = cobra.Model(f"{model.id}_redox_core")
    core_model.name = f"{model.name} - Redox Core"
    
    # Add reactions
    reactions_to_add = []
    for rxn_id in core_reactions:
        if rxn_id in model.reactions:
            reactions_to_add.append(model.reactions.get_by_id(rxn_id))
    
    core_model.add_reactions([rxn.copy() for rxn in reactions_to_add])
    
    # Set the same objective
    if model.objective:
        for rxn in model.reactions:
            if rxn.objective_coefficient != 0 and rxn.id in core_reactions:
                core_model.reactions.get_by_id(rxn.id).objective_coefficient = rxn.objective_coefficient
    
    # Remove orphan metabolites
    metabolites_to_remove = []
    for met in core_model.metabolites:
        if len(met.reactions) == 0:
            metabolites_to_remove.append(met)
    core_model.remove_metabolites(metabolites_to_remove)
    
    logger.info(f"Core model: {len(core_model.reactions)} reactions, "
                f"{len(core_model.metabolites)} metabolites, "
                f"{len(core_model.exchanges)} exchanges")
    
    # Set reasonable bounds for key exchanges
    if "EX_glc__D_e" in core_model.reactions:
        core_model.reactions.get_by_id("EX_glc__D_e").lower_bound = -10
        core_model.reactions.get_by_id("EX_glc__D_e").upper_bound = 0
    if "EX_o2_e" in core_model.reactions:
        core_model.reactions.get_by_id("EX_o2_e").lower_bound = -20
        core_model.reactions.get_by_id("EX_o2_e").upper_bound = 0
    
    # Verify the model can grow
    solution = core_model.optimize()
    logger.info(f"Optimization status: {solution.status}")
    if solution.status == "optimal":
        logger.info(f"Core model growth rate: {solution.objective_value:.6f}")
        if solution.objective_value < 0.01:
            logger.warning("Core model has very low growth! May need gap-filling.")
    else:
        logger.error("Core model cannot be optimized! Needs debugging.")
    
    return core_model


def main():
    parser = argparse.ArgumentParser(description="Build redox-focused core metabolic model")
    parser.add_argument("--input", type=str, required=True, help="Input model path (JSON)")
    parser.add_argument("--output", type=str, required=True, help="Output model path (JSON)")
    parser.add_argument("--reactions", type=int, default=400, help="Target number of reactions")
    
    args = parser.parse_args()
    
    # Load the full model
    logger.info(f"Loading model from {args.input}")
    model = cobra.io.load_json_model(args.input)
    logger.info(f"Loaded model: {len(model.reactions)} reactions, "
                f"{len(model.metabolites)} metabolites")
    
    # Extract core
    core_model = extract_redox_core(model, args.reactions)
    
    # Save the core model
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Saving core model to {output_path}")
    save_json_model(core_model, str(output_path))
    
    # Save metadata
    metadata = {
        "source_model": args.input,
        "source_reactions": len(model.reactions),
        "source_metabolites": len(model.metabolites),
        "core_reactions": len(core_model.reactions),
        "core_metabolites": len(core_model.metabolites),
        "core_exchanges": len(core_model.exchanges),
        "target_reactions": args.reactions,
        "growth_rate": core_model.optimize().objective_value if core_model.optimize().status == "optimal" else 0
    }
    
    metadata_path = output_path.with_suffix(".metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    logger.info("Done!")


if __name__ == "__main__":
    main()