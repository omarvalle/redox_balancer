# NAD+/NADH Redox-Balancer

A reinforcement learning framework for optimizing cellular NAD+/NADH redox balance through engineered enzyme systems.

## Overview

This project applies IMPALA (Importance Weighted Actor-Learner Architecture) to design enzyme constructs that modulate the NAD+/NADH ratio in metabolic models. By targeting cytosolic NADH availability, we aim to:

- Increase NAD+ regeneration capacity
- Optimize redox-dependent metabolic fluxes
- Maintain cellular growth above 95% of baseline

## Key Features

- **Custom IMPALA Implementation**: Distributed RL training optimized for metabolic models
- **Redox-Specific Rewards**: Novel reward function targeting NADH net flux
- **Enzyme Library**: Curated NADH oxidases and malate-aspartate shuttle components
- **Genome-Scale Models**: Compatible with Recon3D and custom core models

## Installation

```bash
# Clone the repository
git clone https://github.com/[your-org]/redox_balancer.git
cd redox_balancer

# Install dependencies
pip install -r requirements.txt

# Set PYTHONPATH
export PYTHONPATH=$PWD/src

# The repository includes:
# - Recon3D full model (10k+ reactions)
# - Core model (374 reactions) 
# - Minimal test model
```

## Quick Start

### 1. Smoke Test (50k steps, ~5 minutes)
```bash
python scripts/train_impala.py \
    --timesteps 50000 \
    --num-actors 4 \
    --model data/models/smoke_test_model.json
```

### 2. Core Model Training (5M steps, ~2 hours)
```bash
python scripts/train_impala.py \
    --timesteps 5000000 \
    --num-actors 30 \
    --model data/models/redox_core.json \
    --checkpoint-dir ./experiments/redox_core_v1
```

### 3. Full Production Training (10M steps, ~15 hours)
```bash
python scripts/train_impala.py \
    --timesteps 10000000 \
    --num-actors 120 \
    --model data/models/redox_core_v1.json \
    --enzymes data/enzyme_library_redox.json \
    --batch-size 64 \
    --save-interval 60 \
    --checkpoint-dir ./experiments/redox_production
```

## Training Parameters

- `--target-metabolite`: Choose between "NADH" or "NAD+" (default: NADH)
- `--biomass-penalty`: Weight for growth constraint (default: 100.0)
- `--redox-weight`: Weight for redox balance component (default: 0.1)
- `--num-actors`: Number of distributed actors (max 120 recommended)

## Memory Management

⚠️ **CRITICAL**: Large-scale training requires careful memory management:

1. Start with 30 actors, scale up gradually
2. Monitor memory usage with `htop` or `nvidia-smi`
3. Enable Ray object spilling if needed:
   ```bash
   export RAY_object_spilling_config='{"type":"filesystem","params":{"directory_path":"/tmp/ray/spill"}}'
   ```

## Enzyme Library

The `data/enzyme_library_redox.json` contains:

- **NADH Oxidases**: NOX_Ec (E. coli), NOX_Lb (L. brevis)
- **Shuttle Components**: mAspAT, cAspAT, MDH1, MDH2
- **Transporters**: SLC25A11, SLC25A12

## Model Building

To create a custom core model focused on redox metabolism:

```bash
python scripts/build_redox_core.py \
    --input data/models/recon3d_full.json \
    --output data/models/redox_core_v2.json \
    --reactions 400
```

## Testing

```bash
# Run all tests
pytest tests/

# Fast tests only (skip slow integration tests)
pytest tests/ -m "not slow"

# Specific test file
pytest tests/test_redox_env.py -v
```

## Visualization

Plot training curves:
```bash
python scripts/plot_training_curve.py \
    --checkpoint-dir ./experiments/redox_core_v1 \
    --output plots/training_curve.png
```

## Checkpointing

Training automatically saves checkpoints based on --save-interval. To resume:

```bash
python scripts/train_impala.py \
    --resume ./experiments/redox_core_v1/step_500000 \
    --timesteps 10000000 \
    # ... other original parameters
```

**Note**: The trainer now supports checkpoint resumption with the --resume flag.

## AWS Deployment

### Quick Start

For large-scale training on AWS, we recommend using r7i.48xlarge instances (1.5TB RAM, 192 vCPUs):

```bash
# Launch instance with proper setup
./scripts/aws_setup.sh

# Sync code to instance
./scripts/sync_to_aws.sh

# SSH and start training
ssh -i ~/.ssh/your-key.pem ubuntu@<instance-ip>
cd /home/redox/redox_balancer
./scripts/run_aws_experiment.sh
```

### Instance Recommendations

- **Core model (10k reactions)**: r7i.48xlarge with 60 actors (1.07GB each after fixes)
- **Recon3D (10k+ reactions)**: r7i.48xlarge with 60-90 actors (memory-limited)
- **Budget option**: c6a.48xlarge for CPU-only training

### Critical Memory Leak Fixes

During production training, we discovered severe memory leaks causing actors to grow from 3GB to 18GB each. After profiling with memray, we implemented three critical fixes:

1. **Model Reuse**: Prevent expensive Model.copy() operations
2. **FBA Cache Limiting**: Cap cache at 5000 entries to prevent unbounded growth
3. **Garbage Collection**: Force GC after each episode reset

These fixes reduced memory usage by 95% and enabled stable long-running training.

### Common AWS Issues

1. **Shell/Conda Issues**: Use direct Python paths instead of conda activate
2. **PYTHONPATH Problems**: Export explicitly before running
3. **Thread Contention**: Set OMP_NUM_THREADS=8 for Ray on large instances
4. **Memory Leaks**: Monitor with `ps aux | grep "ray::ActorWorker"` - actors should stay under 2GB
5. **File Descriptors**: Set `ulimit -n 1048576` for distributed training

For detailed AWS troubleshooting and memory leak analysis, see [CLAUDE.md](CLAUDE.md#training-memory-leak-crisis--resolution-july-13-2025).

## Current Training Status

As of July 13, 2025:
- **Active Training**: 60-actor run on AWS r7i.48xlarge (reduced from 120 for memory stability)
- **Progress**: 75.22% complete (7.5M / 10M steps)
- **Performance**: ~1,000 FPS with memory fixes, returns 3700-4500
- **Memory**: Stable at 1.07GB per actor (was 18GB before fixes)
- **ETA**: Tuesday afternoon (July 15th)
- **Key Fixes Applied**: 
  - Changed reward from NADH net flux (always 0) to sink flux measurement
  - Implemented memory leak fixes reducing usage by 95%

## Critical Implementation Notes

### Reward Function Fix
The original reward function used NADH net flux, which is always zero in FBA due to steady-state mass balance constraints. Fixed by measuring sink reaction flux instead:

```python
# Reward is now based on actual sink activity
sink_flux = sum(solution.fluxes[rxn_id] 
                for rxn_id in solution.fluxes.index 
                if rxn_id.startswith("SINK_"))
r_metabolite = scale * sink_flux
```

## Known Issues & Solutions

1. **Zero Rewards**: Fixed by measuring sink flux instead of NADH net flux
2. **File Descriptor Limits**: Set `ulimit -n 1048576` for Ray with many actors
3. **Memory Leaks**: Fixed with model reuse, cache limits, and GC (see AWS section)
4. **FPS Display After Resume**: Shows inflated values initially due to timestep counting
5. **COBRApy Memory**: Solution objects contain large pandas DataFrames - cache carefully

## Future Work

- [ ] Model trimming to 500-800 reactions for faster training
- [ ] Implement complex shuttle systems (glycerol-3-phosphate shuttle)
- [ ] Add tissue-specific metabolic constraints
- [ ] Integrate with wet-lab validation pipeline
- [ ] Explore multi-objective optimization (NADH + ATP)
- [ ] Create evaluation script for checkpoint performance

## Citation

If you use this code in your research, please cite:

```bibtex
@software{redox_balancer,
  title={NAD+/NADH Redox-Balancer: RL for Metabolic Engineering},
  author={[Your Name]},
  year={2025},
  url={https://github.com/[your-org]/redox_balancer}
}
```

## License

MIT License - see LICENSE file for details.