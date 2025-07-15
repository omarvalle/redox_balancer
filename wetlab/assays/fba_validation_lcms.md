# FBA Validation by LC-MS Metabolomics

## Overview
Validate flux balance analysis predictions by measuring key metabolite concentrations via targeted LC-MS/MS.

## Target Metabolites

### Primary Targets (Redox-Related)
1. **NAD+** (m/z 664.1 → 524.0)
2. **NADH** (m/z 666.1 → 649.1)
3. **Malate** (m/z 133.0 → 115.0)
4. **Aspartate** (m/z 132.0 → 88.0)
5. **Oxaloacetate** (m/z 131.0 → 87.0)
6. **α-Ketoglutarate** (m/z 145.0 → 101.0)

### Secondary Targets (Central Carbon)
7. **Glucose-6-phosphate** (m/z 259.0 → 97.0)
8. **Pyruvate** (m/z 87.0 → 43.0)
9. **Lactate** (m/z 89.0 → 43.0)
10. **Citrate** (m/z 191.0 → 111.0)

## Sample Preparation

### Quenching Protocol (Critical for NAD+/NADH)
1. **E. coli/Yeast**:
   - Add 5 volumes cold (-40°C) 60% methanol
   - Vortex immediately, incubate -40°C for 30 min
   - Centrifuge 4,000g, 10 min, -10°C

2. **HEK293T**:
   - Aspirate media, add cold (-40°C) 80% methanol
   - Scrape on dry ice, transfer to tubes
   - Incubate -80°C for 15 min

### Extraction
1. Add 500 μL extraction solvent (40:40:20 MeOH:ACN:H2O + 0.1% formic acid)
2. Vortex 30 sec, sonicate ice bath 10 min
3. Centrifuge 16,000g, 10 min, 4°C
4. Transfer 400 μL supernatant
5. Dry under nitrogen or SpeedVac
6. Reconstitute in 100 μL 95:5 H2O:ACN + 0.1% formic acid

## LC-MS Method

### Chromatography
- **Column**: Waters BEH Amide, 2.1 × 100 mm, 1.7 μm
- **Mobile Phase A**: 95:5 H2O:ACN + 10 mM NH4OAc + 0.1% FA
- **Mobile Phase B**: 95:5 ACN:H2O + 10 mM NH4OAc + 0.1% FA
- **Flow Rate**: 0.3 mL/min
- **Column Temp**: 40°C
- **Injection**: 5 μL

### Gradient Program

| Time (min) | %A | %B | Curve |
|------------|----|----|-------|
| 0.0 | 5 | 95 | Initial |
| 1.0 | 5 | 95 | Hold |
| 8.0 | 35 | 65 | Linear |
| 9.0 | 60 | 40 | Linear |
| 10.0 | 80 | 20 | Linear |
| 10.1 | 5 | 95 | Step |
| 13.0 | 5 | 95 | Re-equilibrate |

### MS Parameters (Waters TQ-S or equivalent)

**Source Settings**:
- Ionization: ESI negative mode
- Capillary: 2.5 kV
- Cone: 30 V
- Source Temp: 150°C
- Desolvation: 600°C
- Gas Flow: 1000 L/hr

**MRM Transitions**:

| Metabolite | Precursor | Product | Cone (V) | Collision (eV) | RT (min) |
|------------|-----------|---------|----------|----------------|----------|
| NAD+ | 664.1 | 524.0 | 45 | 20 | 7.2 |
| NADH | 666.1 | 649.1 | 45 | 15 | 7.5 |
| Malate | 133.0 | 115.0 | 20 | 10 | 6.8 |
| Aspartate | 132.0 | 88.0 | 20 | 12 | 7.1 |
| OAA | 131.0 | 87.0 | 20 | 10 | 6.5 |
| αKG | 145.0 | 101.0 | 20 | 10 | 6.2 |
| G6P | 259.0 | 97.0 | 25 | 15 | 8.1 |
| Pyruvate | 87.0 | 43.0 | 15 | 8 | 5.2 |
| Lactate | 89.0 | 43.0 | 15 | 8 | 5.5 |
| Citrate | 191.0 | 111.0 | 20 | 12 | 7.8 |

## Calibration Standards

### Standard Mix Preparation
Prepare in extraction solvent at 1 mM each:

1. **Level 1**: 1 μM (1:1000 dilution)
2. **Level 2**: 5 μM
3. **Level 3**: 10 μM
4. **Level 4**: 50 μM
5. **Level 5**: 100 μM
6. **Level 6**: 500 μM

### Internal Standards
- d3-Malate (5 μM final)
- ¹³C₅-Glutamate (5 μM final)
- d4-Citrate (5 μM final)

## Data Analysis

### Quantification
1. Integrate peaks using vendor software
2. Calculate response ratio (analyte/IS)
3. Generate calibration curves (weighted 1/x²)
4. Ensure R² > 0.99 for all metabolites

### Normalization Options
- Per mg protein
- Per cell number
- Per sample dry weight
- To internal metabolite (e.g., total adenylates)

### FBA Comparison
```python
# Example comparison structure
measured_fluxes = {
    'malate_to_oaa': calculate_from_ratio(malate, oaa),
    'asp_production': calculate_from_concentration(asp),
    'nadh_regeneration': calculate_from_nad_ratio(nad, nadh)
}

fba_predictions = model.optimize().fluxes
correlation = pearson_correlation(measured_fluxes, fba_predictions)
```

## Expected Results

### Control vs Treated Ratios

| Metabolite Ratio | Control | +NOX Enzyme | +MAS Upregulation |
|------------------|---------|-------------|-------------------|
| NAD+/NADH | 3-5 | 8-12 | 6-8 |
| Malate/OAA | 50-100 | 30-50 | 20-30 |
| Lactate/Pyruvate | 10-20 | 5-10 | 8-15 |
| αKG/Glutamate | 0.1-0.2 | 0.15-0.25 | 0.12-0.22 |

## Quality Control

1. **Blank Injection**: Between every 10 samples
2. **QC Pool**: Mix all samples, inject every 10 runs
3. **Recovery Standard**: Spike known amounts pre-extraction
4. **CV Acceptance**: <15% for QC replicates
5. **Retention Time**: ±0.1 min window

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| NAD+ degradation | pH/temperature | Keep pH>7, samples on dry ice |
| Poor peak shape | Column degradation | Replace column, check pH |
| Low sensitivity | Ion suppression | Dilute samples, clean source |
| RT drift | Temperature fluctuation | Thermostat column compartment |
| No OAA signal | Rapid degradation | Add malonate to inhibit SDH |

## Data Reporting Template

Report should include:
1. Heatmap of metabolite changes
2. NAD+/NADH ratio bar graph
3. PCA plot of metabolite profiles
4. Table of measured vs predicted fluxes
5. Statistical analysis (p-values, fold changes)