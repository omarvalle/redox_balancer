# Expression Induction Schedule

## E. coli BL21(DE3) - Shake Flask Protocol

### Pre-induction Growth Phase

| Time | Temperature | OD600 | Action |
|------|-------------|-------|--------|
| 0 hr | 37°C | 0.05 | Inoculate 50 mL LB+antibiotic with overnight culture |
| 2 hr | 37°C | 0.3-0.4 | Check growth rate |
| 3 hr | 37°C | 0.6-0.8 | **Pre-induction sample** (1 mL) |
| 3.25 hr | 18°C | 0.6-0.8 | Shift to expression temperature |

### Induction Phase

| Time | IPTG (mM) | Temperature | Expected OD600 | Sample |
|------|-----------|-------------|----------------|---------|
| 0 hr | 0.5 | 18°C | 0.6-0.8 | T0 (pre-induction) |
| 1 hr | 0.5 | 18°C | 0.8-1.0 | T1 |
| 3 hr | 0.5 | 18°C | 1.2-1.5 | T3 |
| 6 hr | 0.5 | 18°C | 1.8-2.2 | T6 |
| 16 hr | 0.5 | 18°C | 2.5-3.0 | T16 (harvest) |

### Optimization Variables

**IPTG Concentration Screen**:
- Low: 0.1 mM
- Medium: 0.5 mM (standard)
- High: 1.0 mM

**Temperature Screen**:
- 18°C (soluble expression)
- 25°C (balanced)
- 30°C (high yield, risk of inclusion bodies)

## S. cerevisiae BY4741 - Galactose Induction

### Growth Phase (Raffinose)

| Time | Medium | OD600 | Action |
|------|--------|-------|--------|
| 0 hr | SC-Ura + 2% Raffinose | 0.1 | Inoculate from overnight |
| 6 hr | SC-Ura + 2% Raffinose | 0.4-0.6 | Check growth |
| 10 hr | SC-Ura + 2% Raffinose | 0.8-1.0 | **Ready for induction** |

### Induction Phase (Galactose)

| Time | Galactose | OD600 | Sample | Notes |
|------|-----------|-------|---------|-------|
| 0 hr | 2% | 1.0 | T0 | Pellet cells, resuspend in galactose medium |
| 2 hr | 2% | 1.2 | T2 | Early induction check |
| 4 hr | 2% | 1.5 | T4 | Mid-log expression |
| 8 hr | 2% | 2.0 | T8 | Peak expression expected |
| 24 hr | 2% | 2.5-3.0 | T24 | Extended expression |

## HEK293T - Transient Transfection

### Transfection Timeline

| Day | Confluency | Action |
|-----|------------|--------|
| -1 | N/A | Seed 2×10⁶ cells in 6-well plate |
| 0 | 70% | Transfect with 2.5 μg DNA + Lipofectamine |
| 1 | 80% | Change to fresh medium |
| 2 | 90% | Harvest for analysis |
| 3 | 95% | Extended expression (optional) |

## Expected Protein Yields

### E. coli BL21(DE3)
- NOX enzymes: 20-50 mg/L culture
- AspAT: 30-60 mg/L culture
- Multi-enzyme cassette: 10-20 mg/L each

### S. cerevisiae BY4741
- MDH1/MDH2: 5-15 mg/L culture
- Lower yield but proper folding

### HEK293T
- All constructs: 0.5-2 mg/L culture
- Focus on activity, not yield

## Sample Collection Protocol

1. **Pre-induction**: 1 mL culture for negative control
2. **Time points**: 1 mL culture each
3. **Processing**:
   - Centrifuge 13,000 rpm, 1 min
   - Resuspend pellet in 100 μL lysis buffer
   - Freeze at -80°C until analysis
4. **Analysis**: SDS-PAGE, Western blot, enzyme activity

## Quality Control Checkpoints

| Parameter | E. coli | Yeast | HEK293T |
|-----------|---------|-------|---------|
| Growth rate | Doubling <45 min | Doubling ~90 min | Doubling ~24 hr |
| Final OD600 | 2.5-3.0 | 2.0-3.0 | N/A |
| Viability | >90% (plate count) | >85% (methylene blue) | >95% (trypan blue) |
| Expression | SDS-PAGE band | Western blot | Activity assay |

## Troubleshooting Quick Reference

- **Low OD600**: Check antibiotic concentration, fresh media
- **No induction**: Verify IPTG/galactose stock, check promoter
- **Inclusion bodies**: Lower temperature, reduce IPTG
- **Low yield**: Optimize induction time, check plasmid stability