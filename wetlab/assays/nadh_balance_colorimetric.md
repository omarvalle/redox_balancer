# NAD+/NADH Colorimetric Assay Protocol

## Overview
Quantitative measurement of NAD+ and NADH levels using commercial kit (e.g., Promega NAD/NADH-Glo™ or similar WST-based assay).

## Principle
- NAD+ and NADH measured separately via selective extraction
- Enzymatic cycling reaction amplifies signal
- Colorimetric readout at 450 nm (WST formazan)

## Materials

### Reagents
- NAD/NADH Extraction Buffer Kit
- NAD Cycling Buffer
- NAD Cycling Enzyme Mix
- NADH Developer Solution
- NADH Standard (100 μM stock)

### Equipment
- 96-well clear microplate (flat bottom)
- Plate reader with 450 nm filter
- 60°C water bath or heat block
- Multichannel pipette

## Sample Preparation

### Cell Lysates (E. coli/Yeast)
1. Harvest 5×10⁷ cells by centrifugation
2. Wash 2× with cold PBS
3. Resuspend in 200 μL extraction buffer
4. Freeze-thaw 2 cycles (-80°C/37°C)
5. Centrifuge 13,000 rpm, 5 min, 4°C
6. Transfer supernatant immediately to ice

### Adherent Cells (HEK293T)
1. Wash cells 2× with cold PBS
2. Add 200 μL extraction buffer per well (6-well plate)
3. Scrape and transfer to tubes
4. Freeze-thaw 2 cycles
5. Centrifuge and collect supernatant

## Assay Protocol

### Step 1: Sample Split for NAD+/NADH
- **Total NAD**: Use sample directly
- **NADH only**: Heat 50 μL sample at 60°C for 30 min (destroys NAD+)
- **NAD+ calculation**: Total NAD - NADH = NAD+

### Step 2: Standard Curve Preparation

| Well | NADH Standard (μL) | Extraction Buffer (μL) | Final [NADH] (μM) |
|------|-------------------|----------------------|-------------------|
| Blank | 0 | 50 | 0 |
| S1 | 5 | 45 | 10 |
| S2 | 10 | 40 | 20 |
| S3 | 20 | 30 | 40 |
| S4 | 30 | 20 | 60 |
| S5 | 40 | 10 | 80 |
| S6 | 50 | 0 | 100 |

### Step 3: Plate Layout (96-well)
```
   1   2   3   4   5   6   7   8   9   10  11  12
A [B] [B] [B] [S1][S1][S1][T1][T1][T1][N1][N1][N1]
B [S2][S2][S2][S3][S3][S3][T2][T2][T2][N2][N2][N2]
C [S4][S4][S4][S5][S5][S5][T3][T3][T3][N3][N3][N3]
D [S6][S6][S6][C1][C1][C1][T4][T4][T4][N4][N4][N4]
E [C2][C2][C2][C3][C3][C3][T5][T5][T5][N5][N5][N5]
F [C4][C4][C4][C5][C5][C5][T6][T6][T6][N6][N6][N6]
G [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ]
H [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ]

B=Blank, S=Standard, C=Control, T=Total NAD, N=NADH only
```

### Step 4: Detection Reaction

1. Add 50 μL sample/standard to wells
2. Add 50 μL NAD Cycling Buffer to all wells
3. Add 2 μL NAD Cycling Enzyme Mix
4. Mix plate, incubate 30 min at RT
5. Add 10 μL Developer Solution
6. Incubate 1-2 hours at RT (monitor color)
7. Read absorbance at 450 nm

## Calculations

### Standard Curve
- Plot Absorbance (y) vs [NADH] μM (x)
- Linear regression: y = mx + b
- R² should be >0.98

### Sample Concentrations
```
[NADH] = (Abs_sample - b) / m × dilution factor
[Total NAD] = (Abs_total - b) / m × dilution factor
[NAD+] = [Total NAD] - [NADH]
NAD+/NADH ratio = [NAD+] / [NADH]
```

### Normalization
- Per mg protein (Bradford assay)
- Per 10⁶ cells
- Per OD600 unit (bacteria)

## Expected Results

| Cell Type | NAD+ (nmol/mg) | NADH (nmol/mg) | NAD+/NADH Ratio |
|-----------|----------------|-----------------|------------------|
| E. coli (WT) | 2.5-3.5 | 0.8-1.2 | 2.5-3.5 |
| E. coli + NOX | 3.5-4.5 | 0.4-0.6 | 6-8 |
| HEK293T (WT) | 0.8-1.2 | 0.15-0.25 | 4-6 |
| HEK293T + Constructs | 1.2-1.6 | 0.1-0.15 | 10-15 |

## Quality Controls

1. **Positive Control**: Add 1 mM pyruvate (consumes NADH)
2. **Negative Control**: Untransfected/empty vector cells
3. **Spike Recovery**: Add known NADH to lysate (90-110% recovery)
4. **Biological Replicates**: n≥3 independent cultures
5. **Technical Replicates**: Triplicate wells per sample

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| High background | Incomplete washing | Wash cells 3× with cold PBS |
| Low signal | Old reagents | Use fresh NADH standard |
| Poor linearity | Pipetting error | Use multichannel, mix well |
| Variable results | Temperature fluctuation | Keep samples on ice |
| No NAD+ signal | Over-heating | Exactly 60°C for 30 min |

## Data Analysis Template
- Calculate mean ± SD for replicates
- One-way ANOVA for multiple groups
- Student's t-test for pairwise comparison
- Graph as bar chart with individual points
- Report fold-change vs control