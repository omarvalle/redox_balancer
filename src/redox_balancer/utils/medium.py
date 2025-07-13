"""Medium definitions for metabolic models."""

DEFAULT_MEDIUM = {
    "EX_glc__D_e": -10.0,   # Glucose uptake (mmol/gDW/h)
    "EX_gln__L_e": -4.0,    # Glutamine uptake
    "EX_o2_e": -20.0,       # Oxygen uptake
    "EX_h2o_e": -1000.0,    # Water exchange
    "EX_nh4_e": -10.0,      # Ammonia exchange (limited)
    "EX_pi_e": -3.4,        # Phosphate exchange (limited)
    # Note: EX_h_e removed - protons should balance naturally
    "EX_co2_e": 1000.0,     # CO2 exchange (secretion only)
    "EX_hco3_e": 0.0,       # Block bicarbonate uptake
    "EX_so4_e": -1.0,       # Sulfate (limited)
}

# Human minimal medium based on typical cell culture media (RPMI-like)
# Supports Recon3D growth without the MIP optimization
HUMAN_MINIMAL_MEDIUM = {
    # Primary carbon/nitrogen sources
    "EX_glc__D_e": -10.0,     # Glucose
    "EX_gln__L_e": -2.0,      # Glutamine
    "EX_o2_e": -20.0,         # Oxygen
    
    # Amino acids (essential)
    "EX_arg__L_e": -0.5,      # Arginine
    "EX_cys__L_e": -0.2,      # Cysteine
    "EX_his__L_e": -0.2,      # Histidine
    "EX_ile__L_e": -0.4,      # Isoleucine
    "EX_leu__L_e": -0.4,      # Leucine
    "EX_lys__L_e": -0.4,      # Lysine
    "EX_met__L_e": -0.2,      # Methionine
    "EX_phe__L_e": -0.2,      # Phenylalanine
    "EX_thr__L_e": -0.4,      # Threonine
    "EX_trp__L_e": -0.05,     # Tryptophan
    "EX_tyr__L_e": -0.2,      # Tyrosine
    "EX_val__L_e": -0.4,      # Valine
    
    # Vitamins
    "EX_btn_e": -0.001,       # Biotin
    "EX_chol_e": -0.01,       # Choline
    "EX_fol_e": -0.001,       # Folate
    "EX_ncam_e": -0.01,       # Nicotinamide
    "EX_pnto__R_e": -0.001,   # Pantothenate
    "EX_pydam_e": -0.001,     # Pyridoxamine
    "EX_ribflv_e": -0.001,    # Riboflavin
    "EX_thm_e": -0.001,       # Thiamine
    
    # Minerals and ions
    # Note: ca2, cl, mg2, mn2, zn2 don't exist as simple ions in Recon3D
    # Using available alternatives or omitting
    "EX_aqcobal_e": -0.001,   # Cobalt (aquacobalamin)
    "EX_fe2_e": -0.01,        # Iron(II)
    "EX_fe3_e": -0.01,        # Iron(III)
    "EX_k_e": -5.0,           # Potassium
    "EX_na1_e": -140.0,       # Sodium
    "EX_nh4_e": -1.0,         # Ammonia
    "EX_pi_e": -1.0,          # Phosphate
    "EX_so4_e": -0.4,         # Sulfate
    
    # Other essentials
    "EX_h2o_e": -1000.0,      # Water
    "EX_h_e": -1000.0,        # Protons
    "EX_co2_e": 1000.0,       # CO2 (secretion only)
    
    # Additional cofactors that might be needed
    "EX_glyc_e": -0.1,        # Glycerol (for lipid synthesis)
    "EX_inost_e": -0.01,      # Inositol (for phospholipids)
    
    # Lipoproteins (essential for Recon3D biomass)
    "EX_hdl_hs_e": -0.001,    # HDL
    "EX_ldl_hs_e": -0.001,    # LDL
    "EX_idl_hs_e": -0.001,    # IDL
}

def set_medium(model, medium=None):
    """Set medium constraints on a metabolic model.
    
    Args:
        model: COBRApy model
        medium: Dict of reaction_id -> lower_bound values
                If None, uses DEFAULT_MEDIUM
    """
    if medium is None:
        medium = DEFAULT_MEDIUM
    
    # First close all exchanges (no uptake, allow secretion)
    for rxn in model.exchanges:
        rxn.lower_bound = 0.0      # close uptake
        rxn.upper_bound = 1000.0   # allow secretion
    
    # Then open specific exchanges according to medium
    for rxn_id, lb in medium.items():
        if rxn_id in model.reactions:
            rxn = model.reactions.get_by_id(rxn_id)
            if lb < 0:  # Uptake
                rxn.lower_bound = lb
            else:  # Secretion only
                rxn.lower_bound = 0
                rxn.upper_bound = lb
    
    # Block all sink & demand reactions except essential maintenance
    for rxn in model.reactions:
        if rxn.id.startswith(('DM_', 'SK_', 'sink_')):
            rxn.bounds = (0.0, 0.0)
    
    # Keep ATPM open if it exists (non-growth maintenance)
    if 'ATPM' in model.reactions:
        model.reactions.ATPM.lower_bound = 8.0  # Standard maintenance
    elif 'ATPM_' in model.reactions:
        # Some models have ATPM with suffix
        for rxn in model.reactions.query('ATPM'):
            rxn.lower_bound = 8.0
            break
    
    # Verify no unexpected exchanges are open
    allowed_exchanges = set(medium.keys()) | {'EX_h2o_e', 'EX_h_e'}
    unexpected_open = [
        rxn.id for rxn in model.exchanges
        if rxn.lower_bound < 0 and rxn.id not in allowed_exchanges
    ]
    if unexpected_open:
        raise ValueError(f"Unexpected open exchanges after set_medium: {unexpected_open}")

def minimal_medium():
    """Return a minimal medium for testing."""
    return {
        "EX_glc__D_e": -10.0,
        "EX_o2_e": -20.0,
        "EX_h2o_e": -1000.0,
        "EX_pi_e": -1000.0,
        "EX_h_e": -1000.0,
        "EX_co2_e": 1000.0,
    }