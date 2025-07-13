#!/bin/bash
# Resume training with memory leak fixes and strict limits

set -e

echo "=== RESUME TRAINING WITH MEMORY FIXES ==="
echo "Time: $(date)"
echo

# 1. Clean up completely
echo "1. Cleaning up old processes and Ray..."
pkill -9 -f python 2>/dev/null || true
pkill -9 -f ray 2>/dev/null || true
sleep 3
ray stop --force 2>/dev/null || true
rm -rf /tmp/ray/session_* 2>/dev/null || true
rm -rf /home/redox/ray_spill/* 2>/dev/null || true

# 2. Set strict memory limits
echo
echo "2. Setting memory limits..."
# Per-process virtual memory limit (14GB per worker)
ulimit -v $((14*1024*1024))
ulimit -m unlimited
ulimit -d unlimited
ulimit -n 1048576

# 3. Configure environment with memory safeguards
echo
echo "3. Configuring environment..."
source /home/redox/miniconda3/bin/activate redox
export PYTHONPATH=/home/redox/redox_balancer/src

# Thread control
export OMP_NUM_THREADS=8
export OPENBLAS_NUM_THREADS=8
export MKL_NUM_THREADS=8
export NUMEXPR_NUM_THREADS=8

# Ray memory settings - STRICT
export RAY_memory_usage_threshold=0.80              # Kill at 80% instead of 95%
export RAY_memory_monitor_refresh_ms=200           # Check every 200ms
export RAY_object_spilling_threshold=0.65          # Spill earlier
export RAY_object_store_memory=150000000000        # 150GB object store
export RAY_worker_register_timeout_seconds=120     # More time for workers

# 4. Create spill directory
mkdir -p /home/redox/ray_spill

# 5. Find latest checkpoint
LATEST_CHECKPOINT=$(ls -td experiments/redox_120actors_sink_flux_20250713_020105/step_* | head -1)
echo
echo "4. Resuming from checkpoint: $LATEST_CHECKPOINT"
CHECKPOINT_STEP=$(basename $LATEST_CHECKPOINT | cut -d_ -f2)
PROGRESS=$(awk "BEGIN {printf \"%.2f\", $CHECKPOINT_STEP * 100 / 10000000}")
echo "   Progress: ${PROGRESS}% ($CHECKPOINT_STEP / 10,000,000 steps)"

# 6. Launch with REDUCED actors and frequent checkpoints
echo
echo "5. Starting training with memory safeguards:"
echo "   - Actors: 60 (reduced from 90)"
echo "   - Memory threshold: 80%"
echo "   - Object store: 150GB"
echo "   - Per-process limit: 14GB"
echo "   - Checkpoint interval: 30 seconds"
echo

# Start Ray with explicit configuration
ray start --head \
    --object-store-memory=150000000000 \
    --memory=1200000000000 \
    --num-cpus=180 \
    --temp-dir=/home/redox/ray_temp \
    --system-config='{"automatic_object_spilling_enabled":true,"object_spilling_config":"{\"type\":\"filesystem\",\"params\":{\"directory_path\":\"/home/redox/ray_spill\"}}","max_io_workers":8}'

sleep 5
ray status

echo
echo "6. Launching training..."

python scripts/train_impala.py \
    --timesteps 10000000 \
    --num-actors 60 \
    --model data/models/redox_core_v1.json \
    --enzymes data/enzyme_library_redox.json \
    --save-interval 30 \
    --batch-size 32 \
    --checkpoint-dir ./experiments/redox_120actors_sink_flux_20250713_020105 \
    --resume $LATEST_CHECKPOINT