# Host Selection Rationale for Redox Enzyme Expression

## Overview
Selection of appropriate expression hosts for redox-balancing enzyme constructs based on compartmentalization requirements and post-translational modifications.

## Expression Systems

### 1. E. coli BL21(DE3) - Primary Host

**Selected for**: RB001, RB002, RB005, RB006, RB007

**Advantages**:
- High-level expression of bacterial enzymes (NOX from E. coli, L. brevis)
- T7 RNA polymerase system for tight control
- Rapid growth (3-4 hour doubling time)
- Cost-effective for initial screening
- No codon optimization required for E. coli enzymes

**Disadvantages**:
- Cannot perform eukaryotic post-translational modifications
- May not properly fold mitochondrial targeting sequences
- Limited for compartmentalized expression studies

**Induction**: IPTG (0.1-1.0 mM)

### 2. S. cerevisiae BY4741 - Secondary Host

**Selected for**: RB003, RB004 (native yeast MDH isoforms)

**Advantages**:
- Native host for MDH1/MDH2 - ensures proper folding
- Functional mitochondrial import machinery
- GAL1 promoter allows tight regulation
- Can validate compartment-specific targeting
- Established metabolic engineering chassis

**Disadvantages**:
- Slower growth (90 min doubling time)
- Lower expression yields than E. coli
- More expensive media requirements

**Induction**: Galactose (2% w/v)

### 3. HEK293T - Validation Host

**Selected for**: Final validation of lead constructs

**Advantages**:
- Human cell line - most relevant for therapeutic applications
- Proper mitochondrial/peroxisomal import
- Native human cofactor concentrations
- Allows NAD+/NADH ratio measurements in mammalian context

**Disadvantages**:
- Expensive culture requirements
- Slow growth (24 hour doubling time)
- Requires transfection optimization
- BSL-2 containment needed

**Transfection**: Lipofectamine 3000 or PEI

## Decision Matrix

| Construct | Primary Host | Rationale | Alternative |
|-----------|-------------|-----------|-------------|
| RB001 (NOX_Ec cytosol) | E. coli | Native enzyme, high expression | Yeast for compartment validation |
| RB002 (NOX_Lb mito) | E. coli | Bacterial enzyme, then validate targeting | HEK293T for mito import |
| RB003 (MDH1 cytosol) | S. cerevisiae | Native host, proper folding | E. coli for high yield |
| RB004 (MDH2 mito) | S. cerevisiae | Native host, mito targeting | HEK293T validation |
| RB005 (AspAT cytosol) | E. coli | High expression needed | Yeast for activity |
| RB006 (Multi-enzyme) | E. coli | Co-expression optimization | Sequential hosts |
| RB007 (NOX peroxisome) | E. coli | Initial expression | HEK293T for PTS1 validation |

## Media and Growth Conditions

### E. coli BL21(DE3)
- **Medium**: LB or TB (Terrific Broth for high density)
- **Temperature**: 37°C (growth), 18°C (expression)
- **Antibiotics**: Kanamycin 50 μg/mL or Ampicillin 100 μg/mL
- **Induction**: 0.5 mM IPTG at OD600 = 0.6-0.8

### S. cerevisiae BY4741
- **Medium**: SC-Ura with 2% raffinose (growth), 2% galactose (induction)
- **Temperature**: 30°C
- **Selection**: Uracil dropout
- **Induction**: Media switch at OD600 = 0.8-1.0

### HEK293T
- **Medium**: DMEM + 10% FBS + 1% Pen/Strep
- **Temperature**: 37°C, 5% CO2
- **Transfection**: 70% confluency
- **Selection**: Puromycin 2 μg/mL or G418 500 μg/mL

## Recommended Workflow

1. **Week 1-2**: Express all constructs in E. coli for rapid screening
2. **Week 3**: Express MDH constructs in yeast for native validation
3. **Week 4**: Test mitochondrial/peroxisomal targeting in appropriate hosts
4. **Week 5-6**: Validate lead constructs in HEK293T for therapeutic relevance

## Safety Considerations

- All strains are Risk Group 1 organisms
- Standard BSL-1 containment for E. coli and yeast
- BSL-2 for HEK293T work
- No pathogenic sequences or toxin production
- Waste autoclave per institutional guidelines