# Claude Code Context for redox_balancer

## Project Overview
This is a NAD+/NADH Redox-Balancer project adapted from succinate_sink. It uses IMPALA reinforcement learning to optimize metabolic networks for redox balance.

## Critical Warnings

### Memory Management
- **NEVER** start with 180 actors - begin with 30 and scale to 120 max
- Monitor memory usage continuously during training
- Each actor uses ~3.4GB with core model, ~10GB with Recon3D

### Technical Choices
- **DO NOT** use Ray RLlib - keep the custom IMPALA implementation
- **DO NOT** assume HiGHS solver works - default to GLPK
- **DO NOT** auto-commit - always ask before git operations

### Development Practices
- Use TodoWrite tool frequently to track tasks
- Run lint/typecheck commands after code changes
- Test locally before AWS deployment

## Key Learnings

### Building Core Models from Recon3D
1. **Medium Requirements**: Recon3D requires lipoproteins (HDL, LDL, IDL) in addition to standard nutrients. These were added to HUMAN_MINIMAL_MEDIUM.

2. **Biomass Objective**: Recon3D defaults to BIOMASS_maintenance as objective. Must explicitly set to BIOMASS_reaction for growth.

3. **Essential Reactions**: When computing essential reactions with single_reaction_deletion, must set the correct objective first.

4. **Core Model Size**: Pure flux-based pruning fails below ~1000 reactions. Need to explicitly preserve:
   - Essential reactions (from single_reaction_deletion)
   - Central carbon metabolism
   - All exchanges from HUMAN_MINIMAL_MEDIUM

5. **Use fastcc**: The only reliable way to build a feasible core model is to start from fastcc-consistent reactions.

### Central Carbon Reactions in Recon3D
Many have different IDs than expected:
- AKGDH → AKGDm (mitochondrial)
- SUCOAS → SUCOASm (mitochondrial)
- Glucose transport: Need multiple (GLCt1, GLCt4, etc.)
- Always search by reaction name/pattern, not hardcoded IDs

### AWS Deployment Issues & Solutions

**Instance Selection**:
- x8g.48xlarge (3TB RAM) not available due to vCPU limits
- Successfully used r7i.48xlarge (1.5TB RAM, 192 vCPUs) instead
- Cost: $12.08/hour vs $18.14/hour for x8g

**Environment Setup Problems**:
1. **Shell issues**: Ubuntu AMI uses dash, not bash - `source` command fails
   - Solution: Use direct Python executable paths
2. **Conda permission errors**: sudo changes user context
   - Solution: Run as target user, not via sudo
3. **Ray workers can't find modules**: PYTHONPATH not propagated
   - Solution: Export PYTHONPATH explicitly
4. **Missing dependencies**: tensorboard not in base environment
   - Solution: pip install in conda environment

**Critical Environment Variables**:
```bash
export PYTHONPATH=/home/redox/redox_balancer/src
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export RAY_memory_monitor_refresh_ms=0
```

### Current Status
- Core model: 10,386 reactions, growth = 0.011 h⁻¹
- Training on AWS r7i.48xlarge: ~80 FPS with 30 actors
- Memory usage: Only 5% of 1.5TB RAM
- 200k timestep test running successfully

## Working Commands

### Build Core Model
```bash
PYTHONPATH=src python scripts/build_redox_core.py \
    --input data/models/Recon3D_full.json \
    --output data/models/redox_core_v1.json \
    --reactions 1500  # Will get ~10k with fastcc
```

### Test Model Growth
```bash
PYTHONPATH=src python -c "
import cobra
from redox_balancer.utils.medium import HUMAN_MINIMAL_MEDIUM, set_medium
m = cobra.io.load_json_model('data/models/redox_core_v1.json')
set_medium(m, HUMAN_MINIMAL_MEDIUM)
m.objective = 'BIOMASS_reaction'
print(m.optimize().objective_value)
"
```

### AWS Training (PRODUCTION COMMAND)
```bash
# On AWS instance as redox user
cd /home/redox/redox_balancer

# Set all required environment variables
export PYTHONPATH=/home/redox/redox_balancer/src
export OMP_NUM_THREADS=8
export OPENBLAS_NUM_THREADS=8
export MKL_NUM_THREADS=8
export NUMEXPR_NUM_THREADS=8
export RAY_memory_monitor_refresh_ms=0
export RAY_object_spilling_threshold=0.8
export RAY_object_store_memory=120000000000

# Set file descriptor limits
ulimit -n 1048576
ulimit -u 65536

# Run training with resume support
/home/redox/miniconda3/envs/redox/bin/python scripts/train_impala.py \
    --timesteps 10000000 \
    --num-actors 120 \
    --model data/models/redox_core_v1.json \
    --enzymes data/enzyme_library_redox.json \
    --save-interval 60 \
    --batch-size 64 \
    --checkpoint-dir ./experiments/redox_120actors_sink_flux_20250713_020105 \
    --resume ./experiments/redox_120actors_sink_flux_20250713_020105/step_932960
```

### Monitoring Scripts Created
- `start_training_fixed.sh`: Robust launcher with all checks
- `monitor_training_local.sh`: Real-time training monitor
- `check_training_health.sh`: Comprehensive health check
- `backup_to_s3.sh`: Hourly S3 backup (via cron)

## Zero Reward Issue (CRITICAL)

### The Problem
The fundamental issue with FBA and NADH mass balance:
- FBA enforces steady-state: Σ(S·v) = 0 for all internal metabolites
- NADH is an internal metabolite → production MUST equal consumption
- Net flux is ALWAYS zero → reward signal was always zero

### The Solution
Changed reward from NADH net flux to sink reaction flux:
```python
# OLD (always zero due to mass balance)
r_metabolite = scale * (nadh_flux - self.baseline_nadh)

# NEW (measures actual sink activity)
sink_flux = sum(solution.fluxes[rxn_id] for rxn_id in solution.fluxes.index 
                if rxn_id.startswith("SINK_"))
r_metabolite = scale * sink_flux
```

Also changed sink reaction objective coefficients from -1e-3 to +1e-3 (COBRA maximizes).

## AWS Deployment - Complete Workflow

### Instance Setup
1. **Instance choice**: r7i.48xlarge (1.5TB RAM, 192 vCPUs, $12.08/hour)
   - x8g family unavailable due to vCPU limits
   - r7i provides best RAM/cost ratio

2. **File descriptor limits** (CRITICAL for Ray):
   ```bash
   # Add to /etc/security/limits.conf
   * soft nofile 1048576
   * hard nofile 1048576
   redox soft nofile 1048576
   redox hard nofile 1048576
   ```

3. **Ray object store limits**:
   ```bash
   export RAY_object_store_memory=120000000000  # 120GB cap
   ```

### Training Memory Leak Crisis & Resolution (July 13, 2025)

#### Initial Crash: File Descriptor Exhaustion
- Default ulimit was 1024 (too low for 120 actors)
- Led to gRPC failures → Ray GCS crash at step 932,960
- Fixed by setting ulimit to 1M and resuming

#### Major Memory Leak Discovery
Training crashed again after 2 hours at step 2,859,040 (28.59%) due to severe memory leak:
- **Symptom**: Ray actors grew from expected 3-4GB to 18GB each
- **Total memory**: 1,413GB used (95% of 1.5TB) → OOM crash
- **Performance degradation**: FPS dropped from 600 to 415

#### Memory Profiling with memray
Used memray to identify leak sources:
```bash
# Set kernel parameters for profiling
sudo sysctl -w kernel.yama.ptrace_scope=0
sudo sysctl -w kernel.perf_event_paranoid=1

# Attach memray to Ray actor
memray attach -o actor_heap.bin -f PID
memray flamegraph actor_heap.bin
```

**Top memory consumers identified**:
1. Model.copy() - 45GB (32.3%)
2. glp_read_prob - 32GB (23.1%)  
3. Solution objects - 19GB (13.5%)

#### Memory Fixes Implemented

1. **Model Reuse** (prevents deep copying):
```python
# In reset() method
if not hasattr(self, "_working_model"):
    self._working_model = self.base_model.copy()
self.model = self._working_model
```

2. **FBA Cache Size Limit**:
```python
# Limit cache to 5000 entries, remove oldest 1000 when exceeded
if len(self.fba_cache) > 5000:
    keys_to_remove = list(self.fba_cache.keys())[:1000]
    for k in keys_to_remove:
        del self.fba_cache[k]
```

3. **Garbage Collection**:
```python
# Force GC at end of reset()
if hasattr(self, "fba_cache"):
    self.fba_cache.clear()
gc.collect()
```

#### Results After Fixes
- **Memory per actor**: Stable at 1.07GB (was growing to 18GB)
- **Total memory**: 46GB used (was 1,413GB)
- **Performance**: FPS stable at ~1,000
- **Progress**: Currently 75.22% complete (7.5M steps)
- **ETA**: Tuesday afternoon (July 15th)

## Lessons Learned
1. Always use fastcc for core model extraction
2. Test with small actor counts before scaling up
3. Use absolute Python paths on AWS to avoid shell issues
4. Set thread control env vars for Ray on large instances
5. Monitor memory usage - each actor needs ~3.4GB with core model (without fixes)
6. **Set file descriptor limits to 1M for distributed training**
7. **Create AMI backups before any risky operations**
8. **FPS after resume shows inflated values due to timestep counting**
9. **Always check reward signals are non-zero before large runs**
10. **Memory leaks in RL training compound over millions of steps**
11. **Profile with memray when actors grow beyond expected memory**
12. **COBRApy Solution objects contain large pandas DataFrames - cache carefully**
13. **Model.copy() is expensive - reuse working models when possible**
14. **Always implement cache size limits for long-running training**