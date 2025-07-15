# Wet Lab Implementation Guide for Redox-Balancing Enzyme Constructs

## Project Overview
This directory contains all necessary documentation for transitioning AI-designed redox-balancing enzyme constructs from computational predictions to experimental validation.

**Goal**: Express and validate NADH oxidase and malate-aspartate shuttle enzyme constructs that improve cellular NAD+/NADH ratios by 15-25% while maintaining >95% growth viability.

**Principal Contact**: Dr. Omar Farooq  
**Email**: [To be provided]  
**Computational Design Date**: July 14, 2025

## Directory Structure

### 📋 `construct_manifest.xlsx`
Master spreadsheet listing all enzyme constructs selected by the RL model, including expression parameters and expected properties.

### 🧬 `gene_sequences.fasta`
Codon-optimized DNA sequences for all enzymes with appropriate targeting sequences for compartment-specific expression.

### 🔬 `cloning/`
- **GoldenGate_protocol.md**: Detailed cloning protocol for multi-enzyme assembly
- **primer_list.csv**: All primers needed for construct generation
- **vector_maps/**: Annotated plasmid maps for expression systems

### 🧫 `expression/`
- **host_selection.md**: Rationale for expression system selection
- **induction_schedule.md**: Optimized expression protocols
- **troubleshooting.md**: Common issues and solutions

### 📊 `assays/`
- **nadh_balance_colorimetric.md**: NAD+/NADH quantification protocol
- **fba_validation_lcms.md**: Metabolomics validation by LC-MS
- **plate_reader_template.xlsx**: Data collection templates

### ⚠️ `safety_compliance/`
- **gmo_risk_assessment.docx**: Biosafety documentation
- **material_safety_data_links.txt**: MSDS references for all materials

### 💰 `budget_timeline.md`
Project timeline and cost estimates for complete experimental validation.

## Quick Start
1. Review `construct_manifest.xlsx` for enzyme selection
2. Order primers from `cloning/primer_list.csv`
3. Follow `cloning/GoldenGate_protocol.md` for construct assembly
4. Use protocols in `expression/` for protein production
5. Validate with assays in `assays/` directory

## Expected Outcomes
- 4-6 week timeline from construct ordering to validation data
- Functional expression of 3-4 lead enzyme constructs
- Quantitative NAD+/NADH ratio improvements matching computational predictions