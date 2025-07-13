# TODO: Future Enhancements for Redox Balancer

## High Priority

### 1. Genome-Scale Fine-Tuning
- [ ] Implement curriculum learning: core model → full Recon3D
- [ ] Add progressive model complexity scaling
- [ ] Create model pruning utilities for different tissue types

### 2. Advanced Shuttle Systems
- [ ] Implement glycerol-3-phosphate shuttle
- [ ] Add citrate-malate shuttle
- [ ] Create shuttle efficiency metrics
- [ ] Model tissue-specific shuttle preferences

### 3. Multi-Objective Optimization
- [ ] Add ATP/ADP ratio as secondary objective
- [ ] Implement Pareto frontier exploration
- [ ] Create visualization for trade-offs
- [ ] Add ROS (reactive oxygen species) minimization

## Medium Priority

### 4. Checkpoint Resume Enhancement
- [ ] Add training state serialization (optimizer, scheduler)
- [ ] Implement checkpoint averaging for ensemble
- [ ] Create checkpoint pruning (keep best N)
- [ ] Add automatic checkpoint validation

### 5. Wet-Lab Integration
- [ ] Create `wetlab/` folder structure:
  ```
  wetlab/
  ├── plasmid_designs/
  ├── protocols/
  ├── validation_assays/
  └── data_analysis/
  ```
- [ ] Generate GenBank files for top constructs
- [ ] Create enzyme expression protocols
- [ ] Design NADH/NAD+ ratio measurement assays

### 6. Enhanced Metrics
- [ ] Add redox potential calculation
- [ ] Implement metabolic flux analysis (MFA) integration
- [ ] Create pathway usage heatmaps
- [ ] Add thermodynamic feasibility checks

## Low Priority

### 7. Algorithm Improvements
- [ ] Experiment with PPO as alternative to IMPALA
- [ ] Add curiosity-driven exploration
- [ ] Implement hierarchical RL for pathway selection
- [ ] Test meta-learning for rapid adaptation

### 8. Analysis Tools
- [ ] Create interactive dashboard (Streamlit/Dash)
- [ ] Add construct clustering visualization
- [ ] Implement pathway enrichment analysis
- [ ] Generate automated reports

### 9. Extended Enzyme Library
- [ ] Add more NOX variants from different organisms
- [ ] Include alternative oxidases (AOX)
- [ ] Add NADH kinases for NADPH production
- [ ] Curate tissue-specific expression data

### 10. Deployment & Scaling
- [ ] Create Docker container with all dependencies
- [ ] Add Kubernetes configs for cloud deployment
- [ ] Implement distributed training across multiple GPUs
- [ ] Create REST API for model inference

## Research Directions

### Biological Validation
- Compare predicted constructs with literature
- Validate in cell-free systems first
- Test in mammalian cell lines (HEK293, HeLa)
- Measure metabolomic changes

### Computational Studies
- Sensitivity analysis of reward function weights
- Ablation studies on enzyme library size
- Compare with traditional optimization methods
- Benchmark against existing tools

### Applications
- Cancer metabolism modulation
- Aging and NAD+ decline
- Metabolic disease interventions
- Bioproduction optimization

## Technical Debt
- [ ] Add comprehensive type hints
- [ ] Improve test coverage to >90%
- [ ] Profile and optimize bottlenecks
- [ ] Add pre-commit hooks
- [ ] Create contribution guidelines

## Documentation
- [ ] Add detailed API documentation
- [ ] Create video tutorials
- [ ] Write best practices guide
- [ ] Add troubleshooting section
- [ ] Create architecture diagrams