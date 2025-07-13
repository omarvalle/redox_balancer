#!/bin/bash
# Run IMPALA training experiment on AWS x8g.48xlarge
# Incorporates all lessons learned from previous runs

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Redox Balancer AWS Experiment ===${NC}"
echo "Instance type: r7i.48xlarge (1.5TB RAM)"
echo "Model: redox_core_v1.json (10,386 reactions)"
echo

# Ensure we're in the right directory
cd /home/redox/redox_balancer || exit 1

# Check environment
if [ ! -f "data/models/redox_core_v1.json" ]; then
    echo -e "${RED}ERROR: Model file not found!${NC}"
    exit 1
fi

# Verify conda environment
if ! command -v python &> /dev/null; then
    echo -e "${YELLOW}Activating conda environment...${NC}"
    source /home/redox/miniconda3/bin/activate redox
fi

# Set Python path
export PYTHONPATH=/home/redox/redox_balancer/src

# Configure Ray for optimal performance
export RAY_memory_monitor_refresh_ms=0  # Disable OOM killer (we have plenty of RAM)
export RAY_object_spilling_config='{"type":"filesystem","params":{"directory_path":"/tmp/ray_spill"}}'
export RAY_verbose_spill_logs=0

# Create experiment directory with timestamp
EXPERIMENT_DIR="experiments/aws_x8g_$(date +%Y%m%d_%H%M%S)"
mkdir -p $EXPERIMENT_DIR
mkdir -p $EXPERIMENT_DIR/checkpoints
mkdir -p /tmp/ray_spill

echo -e "${YELLOW}Experiment directory: $EXPERIMENT_DIR${NC}"

# Log system info
echo -e "${YELLOW}Logging system information...${NC}"
{
    echo "=== System Information ==="
    echo "Date: $(date)"
    echo "Hostname: $(hostname)"
    echo "CPU: $(lscpu | grep 'Model name' | cut -d: -f2 | xargs)"
    echo "Cores: $(nproc)"
    echo "Memory: $(free -h | grep Mem | awk '{print $2}')"
    echo
    echo "=== Python Environment ==="
    which python
    python --version
    pip list | grep -E "(ray|torch|cobra|gymnasium)"
    echo
} > $EXPERIMENT_DIR/system_info.txt

# Start system monitoring in background
echo -e "${YELLOW}Starting system monitoring...${NC}"
{
    while true; do 
        echo "=== $(date) ===" 
        echo "Memory:"
        free -h | grep -E "(Mem|Swap)"
        echo
        echo "Top processes by memory:"
        ps aux --sort=-%mem | head -5 | awk '{print $2, $3, $4, $11}'
        echo
        echo "Ray processes:"
        ps aux | grep -E "ray::" | wc -l
        echo
        echo "Disk usage:"
        df -h / /tmp
        echo "----------------------------------------"
        sleep 60
    done
} > $EXPERIMENT_DIR/system_monitor.log 2>&1 &
MONITOR_PID=$!
echo "Monitor PID: $MONITOR_PID"

# Function to cleanup on exit
cleanup() {
    echo -e "${YELLOW}Cleaning up...${NC}"
    kill $MONITOR_PID 2>/dev/null || true
    # Stop Ray gracefully
    ray stop --force 2>/dev/null || true
    # Clean up spill directory
    rm -rf /tmp/ray_spill/*
}
trap cleanup EXIT

# Start tmux session for resilience
if ! tmux has-session -t redox_training 2>/dev/null; then
    tmux new-session -d -s redox_training
fi

# Log training configuration
cat > $EXPERIMENT_DIR/config.json << EOF
{
    "instance_type": "x8g.48xlarge",
    "model": "redox_core_v1.json",
    "model_reactions": 10386,
    "timesteps": 200000,
    "num_actors": 30,
    "save_interval": 10000,
    "experiment_dir": "$EXPERIMENT_DIR",
    "start_time": "$(date -Iseconds)"
}
EOF

# Run training in tmux
echo -e "${GREEN}Starting training with 30 actors for 200k timesteps${NC}"
echo "Estimated runtime: ~30-45 minutes"
echo

TRAINING_CMD="cd /home/redox/redox_balancer && \
export PYTHONPATH=/home/redox/redox_balancer/src && \
export RAY_memory_monitor_refresh_ms=0 && \
python scripts/train_impala.py \
    --timesteps 200000 \
    --num-actors 30 \
    --model data/models/redox_core_v1.json \
    --enzymes data/enzyme_library_redox.json \
    --save-interval 10000 \
    --checkpoint-dir $EXPERIMENT_DIR/checkpoints \
    2>&1 | tee $EXPERIMENT_DIR/training.log"

# Send command to tmux
tmux send-keys -t redox_training "$TRAINING_CMD" C-m

echo -e "${YELLOW}Training started in tmux session 'redox_training'${NC}"
echo "Attach with: tmux attach -t redox_training"
echo "Detach with: Ctrl-B then D"
echo

# Monitor progress
echo -e "${YELLOW}Monitoring training progress...${NC}"
sleep 10  # Give training time to start

# Wait for training to complete or user interrupt
TRAINING_COMPLETE=false
while [ "$TRAINING_COMPLETE" = false ]; do
    if [ -f "$EXPERIMENT_DIR/training.log" ]; then
        # Show latest progress
        echo -ne "\r$(tail -1 $EXPERIMENT_DIR/training.log | grep -oE 'Timesteps: [0-9,]+.*FPS: [0-9]+' || echo 'Starting...')"
        
        # Check if training completed
        if grep -q "Training complete" $EXPERIMENT_DIR/training.log 2>/dev/null || \
           grep -q "Timesteps: 200,000" $EXPERIMENT_DIR/training.log 2>/dev/null; then
            TRAINING_COMPLETE=true
        fi
        
        # Check for errors
        if grep -q -E "(ERROR|OutOfMemory|Killed)" $EXPERIMENT_DIR/training.log 2>/dev/null; then
            echo -e "\n${RED}Training error detected!${NC}"
            tail -20 $EXPERIMENT_DIR/training.log
            exit 1
        fi
    fi
    sleep 5
done

echo -e "\n${GREEN}Training complete!${NC}"
echo

# Generate summary report
echo -e "${YELLOW}Generating summary report...${NC}"
{
    echo "=== Training Summary ==="
    echo "Experiment: $EXPERIMENT_DIR"
    echo "Start time: $(grep start_time $EXPERIMENT_DIR/config.json | cut -d'"' -f4)"
    echo "End time: $(date -Iseconds)"
    echo
    echo "=== Final Metrics ==="
    tail -100 $EXPERIMENT_DIR/training.log | grep -E "(Timesteps:|FPS:|Return:)" | tail -10
    echo
    echo "=== Memory Usage ==="
    tail -5 $EXPERIMENT_DIR/system_monitor.log | grep -A2 "Memory:"
    echo
    echo "=== Checkpoints ==="
    ls -lh $EXPERIMENT_DIR/checkpoints/
    echo
    echo "=== Recommendations ==="
    
    # Analyze memory usage
    MAX_MEM=$(grep "Mem:" $EXPERIMENT_DIR/system_monitor.log | awk '{print $3}' | sed 's/G//' | sort -n | tail -1)
    echo "Peak memory usage: ${MAX_MEM}G / 3000G"
    
    if (( $(echo "$MAX_MEM < 900" | bc -l) )); then
        echo "- Memory usage is low (<30%), can safely increase to 60-90 actors"
    elif (( $(echo "$MAX_MEM < 1500" | bc -l) )); then
        echo "- Memory usage is moderate (<50%), can increase to 45-60 actors"
    else
        echo "- Memory usage is high (>50%), current actor count is appropriate"
    fi
    
    # Check FPS
    AVG_FPS=$(tail -100 $EXPERIMENT_DIR/training.log | grep -oE "FPS: [0-9]+" | awk -F: '{sum+=$2; count++} END {print int(sum/count)}')
    echo "Average FPS: $AVG_FPS"
    
    if [ "$AVG_FPS" -gt 100 ]; then
        echo "- Excellent performance, ready for production run"
    elif [ "$AVG_FPS" -gt 50 ]; then
        echo "- Good performance, consider optimizations"
    else
        echo "- Performance is suboptimal, check for bottlenecks"
    fi
} > $EXPERIMENT_DIR/summary.txt

cat $EXPERIMENT_DIR/summary.txt

echo
echo -e "${GREEN}Experiment complete! All results saved to: $EXPERIMENT_DIR${NC}"
echo
echo "Next steps:"
echo "1. Review summary: cat $EXPERIMENT_DIR/summary.txt"
echo "2. If successful, run production with: ./scripts/production_run.sh"
echo "3. Download results: scp -r user@host:$EXPERIMENT_DIR ./local_results/"
echo
echo -e "${YELLOW}Don't forget to terminate the instance when done!${NC}"