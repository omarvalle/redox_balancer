"""Delta-based caching system for metabolic flux computations.

Instead of caching all combinations, we cache single-enzyme effects
and compose them efficiently.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Set, FrozenSet
import pickle
import hashlib
from dataclasses import dataclass
import logging
from pathlib import Path
import cobra
from concurrent.futures import ProcessPoolExecutor, as_completed
import json

logger = logging.getLogger(__name__)


@dataclass
class FluxDelta:
    """Represents flux changes from adding a single enzyme."""
    enzyme_ec: str
    compartment: str
    copy_number: int
    d2hg_delta: float
    growth_delta: float
    nadph_delta: float
    key_flux_deltas: Dict[str, float]  # Top affected reactions
    
    def scale(self, factor: float) -> 'FluxDelta':
        """Scale deltas by copy number factor."""
        return FluxDelta(
            enzyme_ec=self.enzyme_ec,
            compartment=self.compartment,
            copy_number=int(self.copy_number * factor),
            d2hg_delta=self.d2hg_delta * factor,
            growth_delta=self.growth_delta * factor,
            nadph_delta=self.nadph_delta * factor,
            key_flux_deltas={k: v * factor for k, v in self.key_flux_deltas.items()}
        )


class DeltaCache:
    """Efficient caching using flux deltas instead of full combinations."""
    
    def __init__(
        self,
        cache_dir: str = "cache/delta_cache",
        model: Optional[cobra.Model] = None,
        enzyme_db: Optional[Dict] = None
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.model = model
        self.enzyme_db = enzyme_db or {}
        
        # In-memory caches
        self.single_enzyme_cache: Dict[str, FluxDelta] = {}
        self.pairwise_interactions: Dict[FrozenSet[str], float] = {}
        
        # Load existing cache
        self._load_cache()
        
    def _load_cache(self):
        """Load cached deltas from disk."""
        single_cache_path = self.cache_dir / "single_enzyme_deltas.pkl"
        pair_cache_path = self.cache_dir / "pairwise_interactions.pkl"
        
        if single_cache_path.exists():
            try:
                with open(single_cache_path, "rb") as f:
                    self.single_enzyme_cache = pickle.load(f)
                logger.info(f"Loaded {len(self.single_enzyme_cache)} single enzyme deltas")
            except Exception as e:
                logger.warning(f"Failed to load single enzyme cache: {e}")
                
        if pair_cache_path.exists():
            try:
                with open(pair_cache_path, "rb") as f:
                    self.pairwise_interactions = pickle.load(f)
                logger.info(f"Loaded {len(self.pairwise_interactions)} pairwise interactions")
            except Exception as e:
                logger.warning(f"Failed to load pairwise cache: {e}")
                
    def save_cache(self):
        """Persist caches to disk."""
        with open(self.cache_dir / "single_enzyme_deltas.pkl", "wb") as f:
            pickle.dump(self.single_enzyme_cache, f)
            
        with open(self.cache_dir / "pairwise_interactions.pkl", "wb") as f:
            pickle.dump(self.pairwise_interactions, f)
            
        # Also save human-readable summary
        summary = {
            "single_enzymes": len(self.single_enzyme_cache),
            "pairwise_interactions": len(self.pairwise_interactions),
            "enzymes": list(set(d.enzyme_ec for d in self.single_enzyme_cache.values()))
        }
        with open(self.cache_dir / "cache_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
            
    def get_construct_prediction(
        self,
        enzymes: List[str],
        compartments: List[str],
        copy_numbers: List[int]
    ) -> Dict[str, float]:
        """Predict flux changes for enzyme construct using cached deltas."""
        
        # Start with baseline
        result = {
            "d2hg_level": 0.0,
            "growth_rate": 1.0,
            "nadph_ratio": 1.0,
            "confidence": 1.0
        }
        
        # Apply single enzyme effects
        single_effects = []
        missing_enzymes = []
        
        for enzyme_ec, comp, copies in zip(enzymes, compartments, copy_numbers):
            cache_key = f"{enzyme_ec}_{comp}_1"  # Base copy number
            
            if cache_key in self.single_enzyme_cache:
                delta = self.single_enzyme_cache[cache_key]
                # Scale by actual copy number
                scaled_delta = delta.scale(copies)
                single_effects.append(scaled_delta)
            else:
                missing_enzymes.append((enzyme_ec, comp))
                result["confidence"] *= 0.8  # Reduce confidence
                
        # If too many missing, return low confidence estimate
        if len(missing_enzymes) > len(enzymes) // 2:
            result["confidence"] = 0.1
            return result
            
        # Compose single effects (additive approximation)
        for delta in single_effects:
            result["d2hg_level"] += delta.d2hg_delta
            result["growth_rate"] *= (1 + delta.growth_delta)  # Multiplicative for growth
            result["nadph_ratio"] *= (1 + delta.nadph_delta)
            
        # Apply pairwise interaction corrections if available
        if len(enzymes) >= 2:
            for i in range(len(enzymes)):
                for j in range(i + 1, len(enzymes)):
                    pair_key = frozenset([enzymes[i], enzymes[j]])
                    if pair_key in self.pairwise_interactions:
                        interaction = self.pairwise_interactions[pair_key]
                        result["d2hg_level"] *= (1 + interaction)
                        
        # Clamp to reasonable ranges
        # Note: d2hg_level can be negative (reduction from baseline)
        result["d2hg_level"] = np.clip(result["d2hg_level"], -10, 10)
        result["growth_rate"] = np.clip(result["growth_rate"], 0, 1.5)
        result["nadph_ratio"] = np.clip(result["nadph_ratio"], 0.1, 10)
        
        return result
    
    def compute_missing_deltas(self, n_workers: int = 4):
        """Pre-compute deltas for all enzymes in enzyme_db."""
        if not self.model or not self.enzyme_db:
            raise ValueError("Model and enzyme_db required for pre-computation")
            
        missing_enzymes = []
        
        # Find missing single enzyme deltas
        for enzyme_ec in self.enzyme_db:
            for compartment in ["c", "m", "p"]:
                cache_key = f"{enzyme_ec}_{compartment}_1"
                if cache_key not in self.single_enzyme_cache:
                    missing_enzymes.append((enzyme_ec, compartment))
                    
        if not missing_enzymes:
            logger.info("All single enzyme deltas already cached")
            return
            
        logger.info(f"Computing {len(missing_enzymes)} missing enzyme deltas...")
        
        # Parallel computation
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            futures = {}
            
            for enzyme_ec, compartment in missing_enzymes:
                future = executor.submit(
                    self._compute_single_enzyme_delta,
                    self.model,
                    enzyme_ec,
                    compartment,
                    self.enzyme_db[enzyme_ec]
                )
                futures[future] = (enzyme_ec, compartment)
                
            # Collect results
            completed = 0
            for future in as_completed(futures):
                enzyme_ec, compartment = futures[future]
                try:
                    delta = future.result()
                    cache_key = f"{enzyme_ec}_{compartment}_1"
                    self.single_enzyme_cache[cache_key] = delta
                    completed += 1
                    
                    if completed % 10 == 0:
                        logger.info(f"Computed {completed}/{len(missing_enzymes)} deltas")
                        
                except Exception as e:
                    logger.error(f"Failed to compute delta for {enzyme_ec} in {compartment}: {e}")
                    
        # Save updated cache
        self.save_cache()
        logger.info(f"Computed and cached {completed} enzyme deltas")
        
    @staticmethod
    def _compute_single_enzyme_delta(
        model: cobra.Model,
        enzyme_ec: str,
        compartment: str,
        enzyme_data: Dict
    ) -> FluxDelta:
        """Compute flux changes from adding single enzyme (worker function)."""
        # Work on model copy
        try:
            model_copy = model.copy()
        except (TypeError, Exception) as e:
            # Workaround for cobra/Python 3.13 compatibility
            import tempfile
            import os
            
            # Serialize and deserialize to create a deep copy
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                cobra.io.save_json_model(model, f.name)
                temp_path = f.name
            
            model_copy = cobra.io.load_json_model(temp_path)
            os.unlink(temp_path)
        
        # Get baseline
        baseline_sol = model_copy.optimize()
        if baseline_sol.status != "optimal":
            raise ValueError("Baseline model infeasible")
            
        baseline_d2hg = abs(baseline_sol.fluxes.get("EX_2hg_e", 0))
        baseline_growth = baseline_sol.objective_value
        baseline_nadph = _calculate_nadph_ratio(baseline_sol, model_copy)
        
        # Add enzyme reaction
        rxn = cobra.Reaction(f"SINK_{enzyme_ec}_{compartment}")
        
        # Standard D-2HG consumption reaction
        # D-2HG + NAD+ -> α-KG + NADH + H+
        metabolites = {
            f"2hg_{compartment}": -1,
            f"nad_{compartment}": -1,
            f"akg_{compartment}": 1,
            f"nadh_{compartment}": 1,
            f"h_{compartment}": 1,
        }
        
        # Add metabolites if they exist
        rxn_metabolites = {}
        for met_id, coeff in metabolites.items():
            # Try with and without compartment suffix
            if met_id in model_copy.metabolites:
                rxn_metabolites[model_copy.metabolites.get_by_id(met_id)] = coeff
            else:
                # Try alternative IDs for 2-HG
                if "2hg" in met_id:
                    alt_ids = [f"h2g_{compartment}", f"D_2hg_{compartment}", 
                              f"L_2hg_{compartment}", f"2hydroxyglutarate_{compartment}"]
                    for alt_id in alt_ids:
                        if alt_id in model_copy.metabolites:
                            rxn_metabolites[model_copy.metabolites.get_by_id(alt_id)] = coeff
                            break
                
        if not rxn_metabolites:
            logger.warning(f"Required metabolites not found for {enzyme_ec} in {compartment}, skipping")
            return FluxDelta(
                enzyme_ec=enzyme_ec,
                compartment=compartment,
                copy_number=1,
                d2hg_delta=0,
                growth_delta=0,
                nadph_delta=0,
                key_flux_deltas={}
            )
            
        rxn.add_metabolites(rxn_metabolites)
        
        # Set flux bounds based on kinetics
        kcat = enzyme_data.get("kcat", 10)  # 1/s
        km = enzyme_data.get("km", 0.1)  # mM
        
        # Approximate Vmax for 1 copy
        vmax = kcat * 1e-3  # mmol/gDW/h
        rxn.lower_bound = 0
        rxn.upper_bound = vmax
        
        model_copy.add_reactions([rxn])
        
        # Solve with enzyme
        enzyme_sol = model_copy.optimize()
        if enzyme_sol.status != "optimal":
            # Return zero deltas if infeasible
            return FluxDelta(
                enzyme_ec=enzyme_ec,
                compartment=compartment,
                copy_number=1,
                d2hg_delta=0,
                growth_delta=0,
                nadph_delta=0,
                key_flux_deltas={}
            )
            
        # Calculate deltas
        new_d2hg = abs(enzyme_sol.fluxes.get("EX_2hg_e", 0))
        new_growth = enzyme_sol.objective_value
        new_nadph = _calculate_nadph_ratio(enzyme_sol, model_copy)
        
        # Find top changed fluxes
        flux_changes = {}
        for rxn_id in baseline_sol.fluxes.index:
            if rxn_id in enzyme_sol.fluxes:
                delta = enzyme_sol.fluxes[rxn_id] - baseline_sol.fluxes[rxn_id]
                if abs(delta) > 1e-6:
                    flux_changes[rxn_id] = delta
                    
        # Keep top 10 flux changes
        top_changes = dict(sorted(
            flux_changes.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:10])
        
        return FluxDelta(
            enzyme_ec=enzyme_ec,
            compartment=compartment,
            copy_number=1,
            d2hg_delta=new_d2hg - baseline_d2hg,
            growth_delta=(new_growth - baseline_growth) / (baseline_growth + 1e-6),
            nadph_delta=(new_nadph - baseline_nadph) / (baseline_nadph + 1e-6),
            key_flux_deltas=top_changes
        )
        
    def compute_pairwise_interactions(
        self,
        enzyme_pairs: Optional[List[Tuple[str, str]]] = None,
        n_workers: int = 4
    ):
        """Compute non-additive interactions between enzyme pairs."""
        if not enzyme_pairs:
            # Generate all pairs from cached single enzymes
            enzymes = list(set(d.enzyme_ec for d in self.single_enzyme_cache.values()))
            enzyme_pairs = [(e1, e2) for i, e1 in enumerate(enzymes) 
                           for e2 in enzymes[i+1:]]
                           
        logger.info(f"Computing {len(enzyme_pairs)} pairwise interactions...")
        
        # Filter to missing pairs
        missing_pairs = []
        for e1, e2 in enzyme_pairs:
            pair_key = frozenset([e1, e2])
            if pair_key not in self.pairwise_interactions:
                missing_pairs.append((e1, e2))
                
        if not missing_pairs:
            logger.info("All pairwise interactions already cached")
            return
            
        # Compute in parallel (similar to single enzyme computation)
        # ... implementation similar to compute_missing_deltas ...
        
        self.save_cache()


def _calculate_nadph_ratio(solution: cobra.Solution, model: cobra.Model) -> float:
    """Helper to calculate NADPH/NADP+ ratio from solution."""
    nadph_produced = 0
    nadph_consumed = 0
    
    for rxn_id, flux in solution.fluxes.items():
        if rxn_id in model.reactions:
            rxn = model.reactions.get_by_id(rxn_id)
            
            # Check metabolites by ID
            for metabolite, coeff in rxn.metabolites.items():
                if "nadph" in metabolite.id.lower():
                    if flux > 0 and coeff > 0:  # Product
                        nadph_produced += flux * coeff
                    elif flux > 0 and coeff < 0:  # Reactant
                        nadph_consumed += flux * abs(coeff)
                    elif flux < 0 and coeff < 0:  # Product in reverse
                        nadph_produced += abs(flux) * abs(coeff)
                    elif flux < 0 and coeff > 0:  # Reactant in reverse
                        nadph_consumed += abs(flux) * coeff
                
    return nadph_produced / (nadph_consumed + 1e-6)