#!/bin/bash
# Resume training with memory safeguards

set -e

echo "=== SAFE TRAINING RESUME ==="
echo "Time: $(date)"
echo

# 1. Clean up Ray completely
echo "Cleaning up Ray..."
ray stop --force 2>/dev/null || true
sleep 3
rm -rf /tmp/ray/session_* 2>/dev/null || true

# 2. Set generous limits
echo "Setting resource limits..."
ulimit -v unlimited
ulimit -m unlimited
ulimit -d unlimited
ulimit -n 1048576

# 3. Configure environment
source /home/redox/miniconda3/bin/activate redox
export PYTHONPATH=/home/redox/redox_balancer/src

# Thread control
export OMP_NUM_THREADS=8
export OPENBLAS_NUM_THREADS=8
export MKL_NUM_THREADS=8
export NUMEXPR_NUM_THREADS=8

# Ray memory settings - MORE AGGRESSIVE
export RAY_memory_monitor_refresh_ms=5000  # Check every 5s
export RAY_object_spilling_threshold=0.7   # Spill at 70%
export RAY_object_store_memory=200000000000  # 200GB object store

# 4. Find latest checkpoint
LATEST_CHECKPOINT=$(ls -td experiments/redox_120actors_sink_flux_20250713_020105/step_* | head -1)
echo
echo "Resuming from: $LATEST_CHECKPOINT"
CHECKPOINT_STEP=$(basename $LATEST_CHECKPOINT | cut -d_ -f2)
PROGRESS=$(awk "BEGIN {printf \"%.2f\", $CHECKPOINT_STEP * 100 / 10000000}")
echo "Progress: ${PROGRESS}% ($CHECKPOINT_STEP / 10,000,000 steps)"

# 5. Launch with REDUCED actors (90 instead of 120)
echo
echo "Starting training with 90 actors (reduced from 120)..."
echo "Memory safeguards:"
echo "  - Object store: 200GB"
echo "  - Memory monitoring: Every 5 seconds"
echo "  - Spilling threshold: 70%"
echo

python scripts/train_impala.py \
    --timesteps 10000000 \
    --num-actors 90 \
    --model data/models/redox_core_v1.json \
    --enzymes data/enzyme_library_redox.json \
    --save-interval 60 \
    --batch-size 64 \
    --checkpoint-dir ./experiments/redox_120actors_sink_flux_20250713_020105 \
    --resume $LATEST_CHECKPOINT