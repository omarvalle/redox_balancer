"""Enzyme library interface for loading from BRENDA/UniProt data."""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from pydantic import BaseModel, Field, validator, ValidationError

logger = logging.getLogger(__name__)


class EnzymeSchema(BaseModel):
    """Schema for enzyme data validation."""
    name: str = Field(..., description="Enzyme name")
    substrates: Optional[List[str]] = Field(None, description="List of substrate names")
    products: Optional[List[str]] = Field(None, description="List of product names")
    kcat: float = Field(..., gt=0, description="Catalytic rate constant (1/s)")
    km: Optional[float] = Field(None, gt=0, description="Michaelis constant (mM)")
    specificity: Optional[float] = Field(None, ge=0, le=1, description="Substrate specificity")
    cofactors: Optional[List[str]] = Field(default_factory=list, description="Required cofactors")
    reaction: Optional[str] = Field(None, description="Reaction string")
    organism: Optional[str] = Field(None, description="Source organism")
    temperature: Optional[float] = Field(None, description="Optimal temperature")
    pH: Optional[float] = Field(None, description="Optimal pH")
    
    @validator('cofactors', pre=True)
    def parse_cofactors(cls, v):
        """Parse cofactors from various formats."""
        if isinstance(v, str):
            # Handle comma-separated strings
            return [c.strip() for c in v.split(',')]
        return v or []


class EnzymeLibrary:
    """Interface for managing enzyme data from various sources."""
    
    def __init__(self, library_path: Optional[str] = None):
        """Initialize enzyme library.
        
        Args:
            library_path: Path to enzyme data file (JSON, CSV, or TSV)
        """
        self.enzymes = {}
        if library_path:
            self.load_library(library_path)
            
    def load_library(self, path: str, validate: bool = True):
        """Load enzyme library from file.
        
        Supports:
        - JSON format (current test format)
        - CSV/TSV from BRENDA exports
        - Custom formats
        
        Args:
            path: Path to enzyme data file
            validate: Whether to validate enzyme data against schema
        """
        path = Path(path)
        
        if path.suffix == '.json':
            with open(path) as f:
                raw_data = json.load(f)
                
            # --- hot-fix: accept old list format ---------------------------------
            # Older JSONs store the library as a list of records; convert on the fly
            if isinstance(raw_data, list):
                # each element must expose either 'id' or 'enzyme_id'; fallback to index
                raw_data = {d.get("id") or d.get("enzyme_id") or str(i): d
                           for i, d in enumerate(raw_data)}
            # ----------------------------------------------------------------------
                
            if validate:
                self.enzymes = self._validate_enzymes(raw_data)
            else:
                self.enzymes = raw_data
                
            logger.info(f"Loaded {len(self.enzymes)} enzymes from JSON")
                
        elif path.suffix in ['.csv', '.tsv']:
            sep = '\t' if path.suffix == '.tsv' else ','
            df = pd.read_csv(path, sep=sep)
            self._parse_dataframe(df, validate=validate)
            logger.info(f"Loaded {len(self.enzymes)} enzymes from {path.suffix}")
            
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
    
    def _validate_enzymes(self, raw_data: Dict[str, Dict]) -> Dict[str, Dict]:
        """Validate enzyme data against schema."""
        validated = {}
        errors = []
        
        for ec_number, enzyme_data in raw_data.items():
            try:
                # Validate with schema
                validated_enzyme = EnzymeSchema(**enzyme_data)
                validated[ec_number] = validated_enzyme.dict()
            except ValidationError as e:
                errors.append(f"EC {ec_number}: {e}")
                logger.warning(f"Validation error for enzyme {ec_number}: {e}")
        
        if errors and len(errors) == len(raw_data):
            raise ValueError(f"All enzymes failed validation:\n" + "\n".join(errors))
        
        logger.info(f"Validated {len(validated)}/{len(raw_data)} enzymes")
        return validated
            
    def _parse_dataframe(self, df: pd.DataFrame, validate: bool = True):
        """Parse enzyme data from DataFrame.
        
        Expected columns:
        - EC_number: EC classification
        - name: Enzyme name
        - kcat: Turnover number (1/s)
        - km: Michaelis constant (mM)
        - cofactor: Required cofactor
        - reaction: Reaction string
        - organism: Source organism (optional)
        - temperature: Optimal temperature (optional)
        - pH: Optimal pH (optional)
        """
        required_cols = ['EC_number', 'name', 'kcat', 'km', 'cofactor', 'reaction']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
            
        raw_enzymes = {}
        for _, row in df.iterrows():
            ec_number = row['EC_number']
            enzyme_data = {
                'name': row['name'],
                'kcat': float(row['kcat']),
                'km': float(row['km']) if pd.notna(row.get('km')) else None,
                'cofactors': row.get('cofactor', row.get('cofactors', [])),
                'reaction': row.get('reaction', ''),
            }
            
            # Add optional fields if present
            for field in ['organism', 'temperature', 'pH', 'substrates', 'products']:
                if field in row and pd.notna(row[field]):
                    enzyme_data[field] = row[field]
                    
            raw_enzymes[ec_number] = enzyme_data
        
        if validate:
            self.enzymes = self._validate_enzymes(raw_enzymes)
        else:
            self.enzymes = raw_enzymes
                    
    def filter_by_substrate(self, substrate: str) -> Dict[str, Dict]:
        """Filter enzymes that act on a specific substrate.
        
        Args:
            substrate: Substrate name (e.g., "D-2-hydroxyglutarate", "D-2HG")
            
        Returns:
            Filtered enzyme dictionary
        """
        filtered = {}
        substrate_lower = substrate.lower()
        substrate_variants = [
            substrate_lower,
            substrate_lower.replace('-', ''),
            substrate_lower.replace('d-', ''),
            'd2hg' if '2hg' in substrate_lower else substrate_lower,
        ]
        
        for ec, data in self.enzymes.items():
            reaction = data.get('reaction', '').lower()
            if any(variant in reaction for variant in substrate_variants):
                filtered[ec] = data
                
        logger.info(f"Found {len(filtered)} enzymes for substrate {substrate}")
        return filtered
        
    def filter_by_compartment_compatibility(
        self, 
        compartments: List[str] = ['c', 'm', 'p']
    ) -> Dict[str, Dict]:
        """Filter enzymes compatible with specified compartments.
        
        Args:
            compartments: List of compartment IDs
            
        Returns:
            Filtered enzyme dictionary
        """
        # For now, return all enzymes
        # In future, could filter based on targeting sequences, pH compatibility, etc.
        return self.enzymes
        
    def get_enzyme_stats(self) -> Dict[str, float]:
        """Get statistics about the enzyme library."""
        if not self.enzymes:
            return {}
            
        kcats = [e['kcat'] for e in self.enzymes.values()]
        kms = [e['km'] for e in self.enzymes.values()]
        
        return {
            'count': len(self.enzymes),
            'mean_kcat': sum(kcats) / len(kcats),
            'min_kcat': min(kcats),
            'max_kcat': max(kcats),
            'mean_km': sum(kms) / len(kms),
            'min_km': min(kms),
            'max_km': max(kms),
        }
        
    def to_action_space(self) -> Tuple[List[str], Dict[str, int]]:
        """Convert enzyme library to RL action space format.
        
        Returns:
            enzyme_list: Ordered list of EC numbers
            enzyme_to_idx: Mapping from EC number to action index
        """
        enzyme_list = sorted(self.enzymes.keys())
        enzyme_to_idx = {ec: idx for idx, ec in enumerate(enzyme_list)}
        return enzyme_list, enzyme_to_idx
        
    def save_as_json(self, path: str):
        """Save enzyme library as JSON."""
        with open(path, 'w') as f:
            json.dump(self.enzymes, f, indent=2)
            
    def __len__(self):
        return len(self.enzymes)
        
    def __getitem__(self, ec_number: str):
        return self.enzymes[ec_number]
        
    def __contains__(self, ec_number: str):
        return ec_number in self.enzymes