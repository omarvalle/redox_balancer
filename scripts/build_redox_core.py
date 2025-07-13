#!/usr/bin/env python3
"""Build a core metabolic model focused on redox metabolism.

This script extracts key redox-related pathways from a full genome-scale model.
"""

import argparse
import json
import logging
from pathlib import Path
import cobra
from cobra.io import save_json_model
from cobra.flux_analysis import single_reaction_deletion, fastcc
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from redox_balancer.utils.medium import HUMAN_MINIMAL_MEDIUM, set_medium

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Include all exchanges from HUMAN_MINIMAL_MEDIUM automatically
ESSENTIAL_RXNS = set(HUMAN_MINIMAL_MEDIUM.keys()) | {
    # biomass & maintenance
    "BIOMASS", "biomass_reaction", "BIOMASS_reaction",
    "BIOMASS_maintenance", "BIOMASS_maintenance_noTrTr",
    "ATPM",
    # transporters
    "GLCt", "O2t",
    # redox tracking
    "EX_nadh_c", "EX_nad_c"
}

# Central carbon metabolism reactions to always keep
CENTRAL_CARBON_RXNS = {
    # Glucose transport and glycolysis
    "GLCt1","GLCt4","HEX1","PGI","PFK","FBA","TPI","GAPD","PGK",
    "PGM","ENO","PYK",
    # TCA cycle
    "CSm","ACONTm","ACONT","ICDHyr","AKGDm","SUCOASm","SUCOAS1m",
    "SUCD1m","FUM","MDHm",
    # Pentose phosphate pathway
    "G6PDH2r","PGL","GND",
    # Oxidative phosphorylation
    "ATPS4mi",  # ATP synthase
    # Pyruvate metabolism
    "PDHm",  # Pyruvate dehydrogenase
    # Nucleotide metabolism
    "ADK1",  # Adenylate kinase (ATP + AMP <-> 2 ADP)
    "ADK1m",  # Adenylate kinase mitochondrial
}


def extract_redox_core(model, target_reactions=400):
    """Extract core reactions focused on NAD(P)H metabolism."""
    
    # First, determine essential reactions under minimal medium
    logger.info("Determining essential reactions under HUMAN_MINIMAL_MEDIUM...")
    temp_model = model.copy()
    set_medium(temp_model, HUMAN_MINIMAL_MEDIUM)
    
    # NEW LINE - protect biomass, not maintenance
    if "BIOMASS_reaction" in temp_model.reactions:
        temp_model.objective = "BIOMASS_reaction"
    
    ess = single_reaction_deletion(temp_model, processes=4)
    # Get reactions where deletion causes no growth
    essential_df = ess[ess["growth"] < 1e-6]
    essential_rxns = set()
    for idx, row in essential_df.iterrows():
        # The 'ids' column contains sets of deleted reactions
        if isinstance(row["ids"], set):
            essential_rxns.update(row["ids"])
        else:
            essential_rxns.add(row["ids"])
    logger.info(f"Found {len(essential_rxns)} essential reactions")
    
    # Key pathways to include
    key_pathways = [
        # Central carbon metabolism
        "Glycolysis", "Pentose phosphate", "TCA cycle",
        # Redox-related
        "NADH", "NADPH", "Oxidative phosphorylation",
        # Amino acid metabolism (redox-dependent)
        "Glutamate", "Aspartate", "Malate",
        # Transport
        "Transport", "Exchange"
    ]
    
    # Key metabolites to ensure connectivity
    key_metabolites = [
        "nad_c", "nadh_c", "nadp_c", "nadph_c",
        "nad_m", "nadh_m", "nadp_m", "nadph_m",
        "glc_D_c", "pyr_c", "acoa_c", "akg_c",
        "mal_L_c", "oaa_c", "glu_L_c", "asp_L_c",
        "atp_c", "adp_c", "o2_c", "co2_c", "h2o_c"
    ]
    
    # Start with essential reactions
    core_reactions = set()
    
    # 1. Add all exchange reactions
    for rxn in model.exchanges:
        core_reactions.add(rxn.id)
    
    # 2. Add biomass reaction
    if model.objective:
        for rxn in model.reactions:
            if rxn.objective_coefficient != 0:
                core_reactions.add(rxn.id)
    
    # 3. Add reactions containing NAD(P)H
    for rxn in model.reactions:
        metabolite_ids = [m.id for m in rxn.metabolites]
        if any("nad" in m_id.lower() for m_id in metabolite_ids):
            core_reactions.add(rxn.id)
    
    # 4. Add reactions from key pathways
    for rxn in model.reactions:
        if rxn.subsystem and any(pathway.lower() in rxn.subsystem.lower() 
                                for pathway in key_pathways):
            core_reactions.add(rxn.id)
    
    # 5. Add reactions containing key metabolites
    for met_id in key_metabolites:
        if met_id in model.metabolites:
            met = model.metabolites.get_by_id(met_id)
            for rxn in met.reactions:
                core_reactions.add(rxn.id)
    
    # 6. Ensure connectivity - add gap-filling reactions
    current_count = len(core_reactions)
    logger.info(f"Initial core: {current_count} reactions")
    
    # If we have too many reactions, prioritize by flux in FBA
    if len(core_reactions) > target_reactions:
        logger.info("Pruning reactions based on flux magnitude...")
        
        # Create temporary model with core reactions
        temp_model = model.copy()
        rxns_to_remove = [r for r in temp_model.reactions if r.id not in core_reactions]
        temp_model.remove_reactions(rxns_to_remove)
        
        # Run FBA (no need to set medium here, using full model flux distribution)
        solution = temp_model.optimize()
        if solution.status == "optimal":
            # Sort reactions by absolute flux
            flux_ranking = sorted(
                [(rxn_id, abs(solution.fluxes[rxn_id])) for rxn_id in core_reactions],
                key=lambda x: x[1],
                reverse=True
            )
            
            # Keep top reactions by flux
            core_reactions = set([rxn_id for rxn_id, _ in flux_ranking[:target_reactions]])
            core_reactions |= ESSENTIAL_RXNS  # ensure biomass & key exchanges stay
            core_reactions |= essential_rxns  # ensure growth-essential reactions stay
            core_reactions |= CENTRAL_CARBON_RXNS  # ensure central carbon metabolism stays
    
    # Replace top-flux selection with fastcc-consistent base
    logger.info("Running fastcc to find consistent reaction set...")
    consistent_model = fastcc(model, zero_cutoff=1e-6)
    consistent_rxns = set(r.id for r in consistent_model.reactions)
    base_set = consistent_rxns | ESSENTIAL_RXNS | CENTRAL_CARBON_RXNS | essential_rxns
    logger.info(f"fastcc consistent reactions: {len(consistent_rxns)}  |  union set: {len(base_set)}")
    
    # Use the consistent set as core reactions
    core_reactions = base_set
    
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
    
    # Restore biomass objective explicitly
    if "BIOMASS_maintenance" in core_model.reactions:
        core_model.objective = "BIOMASS_maintenance"
    elif "BIOMASS_reaction" in core_model.reactions:
        core_model.objective = "BIOMASS_reaction"
    elif "biomass_reaction" in core_model.reactions:
        core_model.objective = "biomass_reaction"
    elif "BIOMASS" in core_model.reactions:
        core_model.objective = "BIOMASS"
    
    # Remove orphan metabolites
    metabolites_to_remove = []
    for met in core_model.metabolites:
        if len(met.reactions) == 0:
            metabolites_to_remove.append(met)
    core_model.remove_metabolites(metabolites_to_remove)
    
    logger.info(f"Core model: {len(core_model.reactions)} reactions, "
                f"{len(core_model.metabolites)} metabolites")
    
    # Guarantee exchange bounds from HUMAN_MINIMAL_MEDIUM
    for rxn_id, lb in HUMAN_MINIMAL_MEDIUM.items():
        if rxn_id in core_model.reactions:
            rxn = core_model.reactions.get_by_id(rxn_id)
            rxn.lower_bound = lb
            rxn.upper_bound = 1000
    
    # Verify the model can grow
    solution = core_model.optimize()
    if solution.status == "optimal" and solution.objective_value > 0.01:
        logger.info(f"Core model grows with rate: {solution.objective_value:.4f}")
    else:
        logger.warning("Core model cannot grow! May need gap-filling.")
    
    return core_model


def create_smoke_test_model():
    """Create a minimal ~50 reaction model for smoke tests."""
    model = cobra.Model("smoke_test_redox")
    
    # This would be a very simplified model
    # For now, return None and use the minimal model from tests
    return None


def main():
    parser = argparse.ArgumentParser(description="Build redox-focused core metabolic model")
    parser.add_argument("--input", type=str, required=True, help="Input model path (JSON)")
    parser.add_argument("--output", type=str, required=True, help="Output model path (JSON)")
    parser.add_argument("--reactions", type=int, default=400, help="Target number of reactions")
    parser.add_argument("--smoke-test", action="store_true", help="Create minimal smoke test model")
    
    args = parser.parse_args()
    
    if args.smoke_test:
        logger.info("Creating smoke test model...")
        # TODO: Implement minimal model creation
        raise NotImplementedError("Smoke test model creation not yet implemented")
    
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
        "target_reactions": args.reactions
    }
    
    metadata_path = output_path.with_suffix(".metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    logger.info("Done!")


if __name__ == "__main__":
    main()