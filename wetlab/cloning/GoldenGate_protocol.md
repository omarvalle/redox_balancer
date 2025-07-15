# Golden Gate Assembly Protocol for Redox-Balancing Constructs

## Overview
This protocol describes the assembly of multi-enzyme constructs using Golden Gate cloning with BsaI-HF v2 enzyme for scarless, directional assembly.

## Materials

### Reagents
- **Enzymes**:
  - BsaI-HF v2 (NEB #R3733, 20 U/μL)
  - T4 DNA Ligase (NEB #M0202, 400 U/μL)
- **Buffers**:
  - T4 DNA Ligase Buffer (10X) with ATP
  - CutSmart Buffer (for verification digests)
- **Competent Cells**:
  - NEB 5-alpha (for cloning)
  - BL21(DE3) (for expression)
- **Selection Media**:
  - LB + Kanamycin (50 μg/mL) for pET constructs
  - LB + Ampicillin (100 μg/mL) for pYES2/pDuet constructs

### DNA Components
- Destination vectors (50 ng/μL):
  - pET28a-GG (BsaI sites flanking MCS)
  - pYES2-GG (modified for Golden Gate)
  - pDuet-1-GG (for multi-enzyme cassettes)
- Insert fragments (gene blocks or PCR products, 20 ng/μL each)
- Control plasmid (pUC19-GFP for positive control)

## Protocol

### Day 1: Golden Gate Assembly

#### Assembly Reaction (20 μL total)
| Component | Volume | Final Amount |
|-----------|--------|--------------|
| Destination vector (50 ng/μL) | 2 μL | 100 ng |
| Insert 1 (20 ng/μL) | 2 μL | 40 ng |
| Insert 2 (if applicable) | 2 μL | 40 ng |
| Insert 3 (if applicable) | 2 μL | 40 ng |
| T4 DNA Ligase Buffer (10X) | 2 μL | 1X |
| BsaI-HF v2 (20 U/μL) | 0.5 μL | 10 U |
| T4 DNA Ligase (400 U/μL) | 0.5 μL | 200 U |
| Nuclease-free water | to 20 μL | - |

#### Thermocycler Program
```
Step 1: 37°C for 5 min  (digestion/ligation)
Step 2: 16°C for 5 min  (ligation)
Repeat steps 1-2 for 30 cycles
Step 3: 50°C for 5 min  (digestion of unligated vector)
Step 4: 80°C for 10 min (enzyme inactivation)
Hold: 4°C
```

#### Transformation
1. Add 2 μL of assembly reaction to 50 μL NEB 5-alpha competent cells
2. Incubate on ice for 30 min
3. Heat shock at 42°C for 30 sec
4. Return to ice for 5 min
5. Add 950 μL SOC medium
6. Incubate at 37°C, 225 rpm for 1 hour
7. Plate 100 μL on appropriate selection plates
8. Incubate overnight at 37°C

### Day 2: Colony Screening

#### Colony PCR
- Use vector-specific primers (T7 promoter/terminator for pET28a)
- Expected sizes listed in construct_manifest.xlsx
- Run 1% agarose gel

#### Overnight Cultures
- Pick 3-4 positive colonies per construct
- Grow in 5 mL LB + antibiotic
- Incubate at 37°C, 225 rpm overnight

### Day 3: Plasmid Verification

#### Miniprep and Sequencing
1. Isolate plasmid DNA using standard miniprep kit
2. Quantify by NanoDrop
3. Verify by restriction digest:
   - 500 ng plasmid
   - 1 μL NcoI + XhoI
   - 2 μL CutSmart Buffer
   - to 20 μL with water
   - Incubate 37°C for 1 hour
4. Submit for Sanger sequencing with appropriate primers

## Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| No colonies | Incompatible overhangs | Verify overhang design |
| | Inactive enzymes | Use fresh aliquot |
| | Poor competent cells | Check transformation efficiency |
| Background colonies | Incomplete digestion | Increase BsaI amount or cycles |
| | Vector religation | Ensure proper overhang design |
| Wrong insert size | Multiple insertions | Reduce insert:vector ratio |
| | Incomplete assembly | Increase cycle number |

## Expected Results
- Transformation efficiency: >100 colonies per plate
- Correct assembly rate: >80% by colony PCR
- Typical yields: 100-200 ng/μL miniprep DNA

## Safety Notes
- All work in BSL-1 laboratory
- Standard PPE required
- Dispose of bacterial waste per institutional guidelines