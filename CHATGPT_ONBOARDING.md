# ChatGPT Onboarding Guide - Redox Balancer Project

## Quick Overview
You're looking at a NAD+/NADH Redox-Balancer project that uses reinforcement learning (IMPALA) to optimize metabolic networks. The project trains AI agents to design enzyme constructs that modulate cellular NAD+/NADH ratios.

## Current Status (July 13, 2025)

### Active Training Run
- **Location**: AWS r7i.48xlarge instance (IP: 44.193.26.15)
- **Progress**: ~15% complete (1.5M / 10M timesteps)
- **Performance**: ~443 FPS with 120 actors
- **Returns**: 3700-3870 range (healthy learning signal)
- **Estimated completion**: 13-14 hours from now

### Recent Major Fix
We just solved a critical issue where rewards were always zero:
- **Problem**: FBA enforces steady-state mass balance, so NADH net flux is always 0
- **Solution**: Changed reward to measure sink reaction flux instead
- **Result**: Rewards jumped from 0 to 3000-4000 range

## Key Files to Read (in order)

1. **README.md** - User-facing documentation with installation and usage
2. **CLAUDE.md** - Detailed implementation notes, AWS issues, and solutions
3. **src/redox_balancer/env/redox_env.py** - The environment with the fixed reward function (see line 566-577)
4. **scripts/train_impala.py** - Main training script with checkpoint resume support
5. **experiments/redox_120actors_sink_flux_20250713_020105.log** - Current training log

## Important Context

### What Works
- Core model training with 120 actors
- Checkpoint saving/resuming
- Reward signal (after fix)
- AWS deployment on r7i.48xlarge

### What We Learned
1. **File descriptors**: Must set `ulimit -n 1048576` for Ray with many actors
2. **Memory**: Each actor uses ~3.4GB (core model) or ~10GB (Recon3D)
3. **Solver**: Use GLPK, not HiGHS (compatibility issues)
4. **FBA constraint**: Internal metabolites always balance to zero net flux

### AWS Instance Details
```bash
# Connect to instance
ssh -i ~/.ssh/succinate-sink-training-key.pem ubuntu@44.193.26.15

# Switch to training user
sudo su - redox

# Check training
cd redox_balancer
tail -f training_launch.log
```

## Current Tasks & Next Steps

### Immediate (while training runs)
1. **Model trimming spec**: Draft plan to reduce model from 10k to 500-800 reactions
2. **Evaluation script**: Create script to test trained agents over 500 episodes
3. **Monitor training**: Check every few hours for stability

### Post-Training
1. Analyze if returns plateau (if so, consider batch size 96 or curriculum changes)
2. Archive final checkpoint to S3
3. Run evaluation suite
4. Start planning lighter model for cheaper instances

## Key Commands

### Check training status (run locally)
```bash
ssh -i ~/.ssh/succinate-sink-training-key.pem ubuntu@44.193.26.15 \
  "sudo -u redox bash -c 'cd /home/redox/redox_balancer && tail -1 training_launch.log'"
```

### View TensorBoard
Open browser to: http://44.193.26.15:6006

### If training crashes
The instance has scripts to handle recovery:
- `start_training_fixed.sh` - Resumes from latest checkpoint
- `check_training_health.sh` - Comprehensive health check

## Project Architecture

```
redox_balancer/
├── src/redox_balancer/
│   ├── env/          # RL environment (redox_env.py has reward logic)
│   ├── agents/       # IMPALA trainer
│   └── models/       # Metabolic model utilities
├── scripts/
│   ├── train_impala.py      # Main training script
│   ├── build_redox_core.py  # Model reduction script
│   └── monitor_training.sh  # Real-time monitoring
├── data/
│   ├── models/       # Metabolic models (Recon3D, core, test)
│   └── enzyme_library_redox.json  # NADH oxidases and shuttles
└── experiments/      # Training outputs and checkpoints
```

## Critical Code Sections

### The Reward Fix (redox_env.py, line 566-577)
```python
# OLD: Always zero due to mass balance
nadh_flux = self._get_nadh_net_flux(solution)
r_metabolite = scale * (nadh_flux - self.baseline_nadh)

# NEW: Measures actual sink activity
sink_flux = sum(solution.fluxes[rxn_id] 
                for rxn_id in solution.fluxes.index 
                if rxn_id.startswith("SINK_"))
r_metabolite = scale * sink_flux
```

### Checkpoint Resume (train_impala.py)
```python
parser.add_argument("--resume", type=str, help="Checkpoint path to resume from")
# ...
if args.resume:
    trainer.load_checkpoint(args.resume)
```

## Background Reading
- IMPALA paper: https://arxiv.org/abs/1802.01561
- COBRApy docs: https://cobrapy.readthedocs.io/
- FBA primer: Understanding steady-state assumption is crucial

## Questions You Might Have

**Q: Why is FPS showing 443 instead of expected 166?**
A: After fixing the zero-reward issue, the environment runs faster. The initial "1400 FPS" was a measurement artifact from resuming.

**Q: Why not use the full Recon3D model?**
A: It's too large (10k+ reactions). We use a 374-reaction core model that preserves essential metabolism.

**Q: What's the biological goal?**
A: Design enzyme constructs that increase NAD+ regeneration while maintaining >95% cell growth.

## Contact & Resources
- Training logs: `/home/redox/redox_balancer/experiments/`
- Monitoring: `tmux attach -t training` on the AWS instance
- S3 backups: Configured for hourly snapshots (update bucket name)

---

**Bottom Line**: The training is running smoothly after fixing a fundamental reward calculation issue. We're 15% done with a 10M-step run that should complete in ~13 hours. The main task now is planning how to create a smaller, more efficient model while the training finishes.