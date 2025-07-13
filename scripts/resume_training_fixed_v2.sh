#!/bin/bash
# Resume training with proper memory limits (Ray-compatible version)

set -e

echo "=== RESUME TRAINING WITH PROPER MEMORY LIMITS ==="
echo "Time: $(date)"
echo

# 1. Clean up completely
echo "1. Cleaning up old processes and Ray..."
pkill -9 -f python 2>/dev/null || true
pkill -9 -f ray 2>/dev/null || true
sleep 3
ray stop --force 2>/dev/null || true
rm -rf /tmp/ray/session_* 2>/dev/null || true
rm -rf /home/omar/ray_temp/session_* 2>/dev/null || true
rm -rf /home/omar/ray_spill/* 2>/dev/null || true

# 2. Set base limits (not virtual memory yet)
echo
echo "2. Setting base resource limits..."
ulimit -n 1048576  # File descriptors
ulimit -u 65536    # Max processes

# 3. Configure environment
echo
echo "3. Configuring environment..."
# Skip conda activation on local system
export PYTHONPATH=/home/omar/redox_balancer/src

# Thread control
export OMP_NUM_THREADS=8
export OPENBLAS_NUM_THREADS=8
export MKL_NUM_THREADS=8
export NUMEXPR_NUM_THREADS=8

# Ray memory settings
export RAY_memory_usage_threshold=0.80              # Kill at 80%
export RAY_memory_monitor_refresh_ms=200           # Check every 200ms
export RAY_object_spilling_threshold=0.65          # Spill earlier
export RAY_worker_register_timeout_seconds=120     # More time for workers

# CRITICAL: Set worker memory limit via env var (Ray will apply this to workers only)
export RAY_worker_rlimit_vmem=$((14*1024*1024))    # 14 GB per worker

# Limit worker restart rate
export RAY_max_dead_workers_to_report=10
export RAY_max_used_resources_per_node=100

# 4. Create directories
echo
echo "4. Creating required directories..."
mkdir -p /home/omar/ray_temp
mkdir -p /home/omar/ray_spill

# 5. Start Ray with UNLIMITED virtual memory (needed for startup)
echo
echo "5. Starting Ray (with unlimited memory for head node)..."
ulimit -v unlimited  # CRITICAL: Allow Ray head to start

ray start --head \
    --port=6379 \
    --object-store-memory=200000000000 \
    --temp-dir=/home/omar/ray_temp \
    --disable-usage-stats \
    --system-config='{"memory_usage_threshold":0.80,"automatic_object_spilling_enabled":true,"object_spilling_config":"{\"type\":\"filesystem\",\"params\":{\"directory_path\":\"/home/omar/ray_spill\"}}","max_io_workers":8}'

# Wait for Ray to fully start
sleep 10

# Verify Ray started
echo
echo "6. Verifying Ray startup..."
ray status || { echo "ERROR: Ray failed to start"; exit 1; }

# Check Ray logs for errors
echo
echo "Checking Ray logs..."
tail -5 /home/omar/ray_temp/session_latest/logs/gcs_server.out 2>/dev/null || echo "GCS log not found"
tail -5 /home/omar/ray_temp/session_latest/logs/raylet.out 2>/dev/null | grep -v "INFO" || echo "Raylet log clean"

# 7. Find latest checkpoint
LATEST_CHECKPOINT="experiments/redox_120actors_sink_flux_20250713_020105/step_2856620"
echo
echo "7. Resuming from checkpoint: $LATEST_CHECKPOINT"
echo "   Progress: 28.56% (2,856,620 / 10,000,000 steps)"

# 8. Launch training with memory-limited workers
echo
echo "8. Starting training..."
echo "   Configuration:"
echo "   - Actors: 60"
echo "   - Head node: Unlimited memory"
echo "   - Worker limit: 14GB each (via RAY_worker_rlimit_vmem)"
echo "   - Memory threshold: 80%"
echo "   - Object store: 200GB"
echo "   - Checkpoint interval: 30 seconds"
echo

python scripts/train_impala.py \
    --timesteps 10000000 \
    --num-actors 60 \
    --model data/models/redox_core_v1.json \
    --enzymes data/enzyme_library_redox.json \
    --save-interval 30 \
    --batch-size 32 \
    --checkpoint-dir ./experiments/redox_120actors_sink_flux_20250713_020105 \
    --resume $LATEST_CHECKPOINT \
    2>&1 | tee -a training_launch.log