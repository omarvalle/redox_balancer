#!/bin/bash
# Production IMPALA training run on AWS x8g.48xlarge
# Full safety checks and monitoring

set -e

# Configuration
TIMESTEPS=5000000  # 5M timesteps
NUM_ACTORS=120     # IMPALA sweet spot for large instances
SAVE_INTERVAL=50000
MIN_FREE_RAM_GB=500  # Minimum free RAM required

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Redox Balancer Production Run ===${NC}"
echo "Timesteps: $(printf "%'d" $TIMESTEPS)"
echo "Actors: $NUM_ACTORS"
echo "Model: redox_core_v1.json"
echo "Save interval: $(printf "%'d" $SAVE_INTERVAL)"
echo "Estimated runtime: 8-12 hours"
echo "Estimated cost: \$150-220"
echo

# Safety checks
echo -e "${YELLOW}Running safety checks...${NC}"

# Check if we're on the right instance
INSTANCE_TYPE=$(ec2-metadata --instance-type 2>/dev/null | cut -d' ' -f2 || echo "unknown")
if [ "$INSTANCE_TYPE" != "r7i.48xlarge" ]; then
    echo -e "${YELLOW}WARNING: Not running on r7i.48xlarge (detected: $INSTANCE_TYPE)${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check available memory
FREE_RAM_GB=$(free -g | grep Mem | awk '{print $7}')
if [ "$FREE_RAM_GB" -lt "$MIN_FREE_RAM_GB" ]; then
    echo -e "${RED}ERROR: Insufficient free RAM: ${FREE_RAM_GB}GB < ${MIN_FREE_RAM_GB}GB required${NC}"
    exit 1
fi
echo "Free RAM: ${FREE_RAM_GB}GB ✓"

# Check if previous experiment was successful
LATEST_EXPERIMENT=$(ls -td experiments/aws_x8g_* 2>/dev/null | head -1)
if [ -z "$LATEST_EXPERIMENT" ]; then
    echo -e "${RED}ERROR: No previous experiment found. Run initial test first!${NC}"
    exit 1
fi

echo "Checking previous experiment: $LATEST_EXPERIMENT"
if [ -f "$LATEST_EXPERIMENT/summary.txt" ]; then
    echo -e "${GREEN}Previous experiment summary:${NC}"
    grep -E "(Peak memory|Average FPS)" $LATEST_EXPERIMENT/summary.txt
else
    echo -e "${YELLOW}WARNING: No summary found from previous experiment${NC}"
fi

# Final confirmation
echo
echo -e "${YELLOW}This production run will:${NC}"
echo "- Run for 8-12 hours"
echo "- Cost approximately \$150-220"
echo "- Use $NUM_ACTORS parallel actors"
echo "- Save checkpoints every $(printf "%'d" $SAVE_INTERVAL) steps"
echo
read -p "Proceed with production run? (yes/no) " -r
if [ "$REPLY" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

# Set up auto-termination as safety measure
echo -e "${YELLOW}Setting auto-termination in 14 hours...${NC}"
sudo shutdown -h +840 2>/dev/null || echo "Could not set auto-shutdown (not critical)"

# Create experiment directory
EXPERIMENT_DIR="experiments/production_$(date +%Y%m%d_%H%M%S)"
mkdir -p $EXPERIMENT_DIR/checkpoints
mkdir -p $EXPERIMENT_DIR/tensorboard

# Activate environment
cd /home/redox/redox_balancer
source /home/redox/miniconda3/bin/activate redox
export PYTHONPATH=/home/redox/redox_balancer/src

# Configure Ray for production
export RAY_memory_monitor_refresh_ms=0
export RAY_object_spilling_config='{"type":"filesystem","params":{"directory_path":"/tmp/ray_spill"}}'
export RAY_verbose_spill_logs=0
export OMP_NUM_THREADS=1  # Prevent thread explosion

# Log configuration
cat > $EXPERIMENT_DIR/config.json << EOF
{
    "run_type": "production",
    "instance_type": "$INSTANCE_TYPE",
    "model": "redox_core_v1.json",
    "model_reactions": 10386,
    "timesteps": $TIMESTEPS,
    "num_actors": $NUM_ACTORS,
    "save_interval": $SAVE_INTERVAL,
    "experiment_dir": "$EXPERIMENT_DIR",
    "start_time": "$(date -Iseconds)",
    "auto_terminate_hours": 14
}
EOF

# Start comprehensive monitoring
echo -e "${YELLOW}Starting monitoring services...${NC}"

# System monitor
{
    while true; do
        {
            echo "=== $(date -Iseconds) ==="
            echo "MEMORY:"
            free -h
            echo
            echo "CPU:"
            mpstat 1 1 | tail -2
            echo
            echo "TOP_PROCESSES:"
            ps aux --sort=-%mem | head -10 | awk '{printf "%-10s %5s %5s %s\n", $2, $3, $4, $11}'
            echo
            echo "RAY_WORKERS:"
            ps aux | grep -c "ray::" || echo 0
            echo
            echo "DISK:"
            df -h / /tmp | tail -2
            echo
            echo "NETWORK:"
            ss -s | grep -E "(TCP|UDP)" | head -4
            echo "========================================"
        } >> $EXPERIMENT_DIR/system_monitor.log
        sleep 300  # Log every 5 minutes
    done
} &
MONITOR_PID=$!

# Progress tracker
{
    while true; do
        if [ -f "$EXPERIMENT_DIR/training.log" ]; then
            LATEST=$(tail -1 $EXPERIMENT_DIR/training.log | grep -oE "Timesteps: [0-9,]+" | grep -oE "[0-9,]+")
            if [ ! -z "$LATEST" ]; then
                PROGRESS=$(echo "scale=2; ${LATEST//,/} * 100 / $TIMESTEPS" | bc)
                echo "$(date -Iseconds),${LATEST//,/},$PROGRESS" >> $EXPERIMENT_DIR/progress.csv
            fi
        fi
        sleep 60
    done
} &
PROGRESS_PID=$!

# Cleanup function
cleanup() {
    echo -e "${YELLOW}Cleaning up...${NC}"
    kill $MONITOR_PID $PROGRESS_PID 2>/dev/null || true
    ray stop --force 2>/dev/null || true
    
    # Generate final report
    if [ -f "$EXPERIMENT_DIR/training.log" ]; then
        echo -e "${YELLOW}Generating final report...${NC}"
        python scripts/analyze_training.py $EXPERIMENT_DIR > $EXPERIMENT_DIR/final_report.txt 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Create resilient tmux session
tmux new-session -d -s production_run

# Build training command
TRAINING_CMD="cd /home/redox/redox_balancer && \
source /home/redox/miniconda3/bin/activate redox && \
export PYTHONPATH=/home/redox/redox_balancer/src && \
export RAY_memory_monitor_refresh_ms=0 && \
export OMP_NUM_THREADS=1 && \
python scripts/train_impala.py \
    --timesteps $TIMESTEPS \
    --num-actors $NUM_ACTORS \
    --model data/models/redox_core_v1.json \
    --enzymes data/enzyme_library_redox.json \
    --save-interval $SAVE_INTERVAL \
    --checkpoint-dir $EXPERIMENT_DIR/checkpoints \
    --tensorboard-dir $EXPERIMENT_DIR/tensorboard \
    2>&1 | tee $EXPERIMENT_DIR/training.log"

# Start training
echo -e "${GREEN}Starting production training...${NC}"
tmux send-keys -t production_run "$TRAINING_CMD" C-m

echo
echo -e "${GREEN}Production training started!${NC}"
echo
echo "=== Monitoring Commands ==="
echo "Attach to training: tmux attach -t production_run"
echo "Watch progress: tail -f $EXPERIMENT_DIR/training.log"
echo "System monitor: tail -f $EXPERIMENT_DIR/system_monitor.log"
echo "Live metrics: watch -n 10 'tail -20 $EXPERIMENT_DIR/training.log | grep Timesteps'"
echo
echo "=== Progress Tracking ==="
echo "Progress CSV: $EXPERIMENT_DIR/progress.csv"
echo "Config: $EXPERIMENT_DIR/config.json"
echo
echo "=== Important Reminders ==="
echo "- Instance will auto-terminate in 14 hours"
echo "- Check progress regularly: grep Timesteps $EXPERIMENT_DIR/training.log | tail"
echo "- Download checkpoints periodically to avoid data loss"
echo
echo -e "${YELLOW}To stop training safely:${NC}"
echo "1. tmux attach -t production_run"
echo "2. Ctrl+C to stop training"
echo "3. Wait for cleanup"
echo
echo -e "${GREEN}Good luck with your production run!${NC}"