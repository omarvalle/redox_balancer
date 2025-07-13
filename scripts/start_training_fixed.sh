#!/bin/bash
# Comprehensive AWS Redox Training Startup Script
# Includes all pre-flight checks and quality-of-life improvements

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REDOX_USER="redox"
REDOX_HOME="/home/redox"
EXPERIMENT_BASE_DIR="${REDOX_HOME}/redox_balancer/experiments"
INSTANCE_IP="44.193.26.15"
S3_BUCKET="s3://your-bucket-name/redox-experiments"  # Update this with your S3 bucket

echo -e "${BLUE}=== Redox Training Pre-Flight Checks ===${NC}"
echo "Time: $(date)"
echo "Instance IP: ${INSTANCE_IP}"
echo

# Function to log with timestamp
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check and report status
check_status() {
    local check_name="$1"
    local command="$2"
    echo -n "Checking ${check_name}... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        return 1
    fi
}

# 1. Verify we're running as redox user
log "${YELLOW}1. Verifying user context${NC}"
if [ "$USER" != "$REDOX_USER" ]; then
    echo -e "${RED}ERROR: Must run as redox user!${NC}"
    echo "Please run: sudo su - redox"
    exit 1
fi
echo -e "${GREEN}✓ Running as redox user${NC}"

# 2. Verify ulimit settings
log "${YELLOW}2. Checking ulimit settings${NC}"
CURRENT_NOFILE=$(ulimit -n)
CURRENT_NPROC=$(ulimit -u)
echo "Current ulimits:"
echo "  - Open files (nofile): $CURRENT_NOFILE"
echo "  - Max processes (nproc): $CURRENT_NPROC"

if [ "$CURRENT_NOFILE" -lt 1048576 ] || [ "$CURRENT_NPROC" -lt 524288 ]; then
    echo -e "${YELLOW}Warning: ulimits are not optimal. Attempting to set...${NC}"
    ulimit -n 1048576 2>/dev/null || echo "  Failed to set nofile limit"
    ulimit -u 524288 2>/dev/null || echo "  Failed to set nproc limit"
    echo "Updated ulimits:"
    echo "  - Open files: $(ulimit -n)"
    echo "  - Max processes: $(ulimit -u)"
fi

# 3. Clean up Ray's orphaned files
log "${YELLOW}3. Cleaning up Ray temporary files${NC}"
# Stop any existing Ray instances
ray stop --force 2>/dev/null || true
sleep 2

# Clean up Ray directories
RAY_TEMP_DIRS=(
    "/tmp/ray"
    "/tmp/ray_spill"
    "/tmp/ray_plasma"
    "/tmp/ray_tmp_*"
    "${REDOX_HOME}/.ray"
)

for dir in "${RAY_TEMP_DIRS[@]}"; do
    if [ -d "$dir" ] || ls $dir 2>/dev/null; then
        echo "  Cleaning: $dir"
        rm -rf $dir 2>/dev/null || sudo rm -rf $dir
    fi
done

# Clean up any orphaned shared memory segments
echo "  Cleaning shared memory segments..."
ipcs -m | grep "$USER" | awk '{print $2}' | while read id; do
    ipcrm -m $id 2>/dev/null || true
done

echo -e "${GREEN}✓ Ray cleanup complete${NC}"

# 4. Check /tmp space and setup Ray directories
log "${YELLOW}4. Checking disk space and setting up directories${NC}"
TMP_AVAILABLE=$(df -BG /tmp | tail -1 | awk '{print $4}' | sed 's/G//')
echo "  /tmp available space: ${TMP_AVAILABLE}GB"

if [ "$TMP_AVAILABLE" -lt 50 ]; then
    echo -e "${YELLOW}  Warning: Low /tmp space. Cleaning up...${NC}"
    # Clean old logs and temp files
    find /tmp -type f -mtime +1 -name "*.log" -delete 2>/dev/null || true
    find /tmp -type f -mtime +1 -name "core.*" -delete 2>/dev/null || true
    TMP_AVAILABLE=$(df -BG /tmp | tail -1 | awk '{print $4}' | sed 's/G//')
    echo "  /tmp available after cleanup: ${TMP_AVAILABLE}GB"
fi

# Create Ray directories with proper permissions
mkdir -p /tmp/ray_spill
mkdir -p /tmp/ray_plasma
mkdir -p ${REDOX_HOME}/.ray
chmod 755 /tmp/ray_spill /tmp/ray_plasma

# 5. Check Python environment
log "${YELLOW}5. Verifying Python environment${NC}"
if ! command -v conda &> /dev/null; then
    echo -e "${RED}ERROR: Conda not found!${NC}"
    exit 1
fi

# Activate conda environment
source ${REDOX_HOME}/miniconda3/bin/activate redox || {
    echo -e "${RED}ERROR: Failed to activate redox conda environment!${NC}"
    exit 1
}

# Verify key packages
REQUIRED_PACKAGES=("ray" "torch" "cobra" "gymnasium" "tensorboard")
MISSING_PACKAGES=()

for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if ! python -c "import $pkg" 2>/dev/null; then
        MISSING_PACKAGES+=("$pkg")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "${RED}ERROR: Missing required packages: ${MISSING_PACKAGES[*]}${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python environment verified${NC}"

# 6. Check model and data files
log "${YELLOW}6. Verifying model and data files${NC}"
cd ${REDOX_HOME}/redox_balancer || exit 1

check_status "redox_core_v1.json" "[ -f data/models/redox_core_v1.json ]"
check_status "enzyme_library_redox.json" "[ -f data/enzyme_library_redox.json ]"
check_status "PYTHONPATH setup" "[ ! -z '$PYTHONPATH' ]"

export PYTHONPATH=${REDOX_HOME}/redox_balancer/src

# 7. Setup experiment directory
log "${YELLOW}7. Setting up experiment directory${NC}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EXPERIMENT_NAME="redox_120actors_sink_flux_${TIMESTAMP}"
EXPERIMENT_DIR="${EXPERIMENT_BASE_DIR}/${EXPERIMENT_NAME}"

mkdir -p ${EXPERIMENT_DIR}/{checkpoints,logs,tensorboard}
echo "Experiment directory: ${EXPERIMENT_DIR}"

# 8. Configure Ray environment
log "${YELLOW}8. Configuring Ray environment${NC}"
export RAY_memory_monitor_refresh_ms=0
export RAY_object_spilling_config='{"type":"filesystem","params":{"directory_path":"/tmp/ray_spill"}}'
export RAY_verbose_spill_logs=0
export RAY_TMPDIR="/tmp/ray"
export RAY_PLASMA_DIRECTORY="/tmp/ray_plasma"

# 9. Setup TensorBoard
log "${YELLOW}9. Setting up TensorBoard${NC}"
# Kill any existing TensorBoard processes
pkill -f tensorboard 2>/dev/null || true

# Start TensorBoard in background
tensorboard --logdir=${EXPERIMENT_BASE_DIR} --bind_all --port 6006 > ${EXPERIMENT_DIR}/logs/tensorboard.log 2>&1 &
TENSORBOARD_PID=$!
echo "TensorBoard started (PID: $TENSORBOARD_PID)"
echo "Access at: http://${INSTANCE_IP}:6006"

# 10. Create S3 backup script
log "${YELLOW}10. Creating S3 backup script${NC}"
cat > ${REDOX_HOME}/backup_to_s3.sh << 'EOF'
#!/bin/bash
# S3 Backup Script for Redox Experiments

EXPERIMENT_DIR="$1"
S3_BUCKET="$2"

if [ -z "$EXPERIMENT_DIR" ] || [ -z "$S3_BUCKET" ]; then
    echo "Usage: $0 <experiment_dir> <s3_bucket_path>"
    exit 1
fi

# Get experiment name from path
EXPERIMENT_NAME=$(basename $EXPERIMENT_DIR)

# Sync to S3
aws s3 sync $EXPERIMENT_DIR ${S3_BUCKET}/${EXPERIMENT_NAME}/ \
    --exclude "*.log" \
    --exclude "ray_tmp*" \
    --exclude "__pycache__/*" \
    --exclude ".ray/*"

# Also backup important logs
aws s3 cp ${EXPERIMENT_DIR}/training.log ${S3_BUCKET}/${EXPERIMENT_NAME}/ 2>/dev/null || true
aws s3 cp ${EXPERIMENT_DIR}/summary.txt ${S3_BUCKET}/${EXPERIMENT_NAME}/ 2>/dev/null || true

echo "[$(date)] Backup completed: ${EXPERIMENT_NAME} -> ${S3_BUCKET}"
EOF

chmod +x ${REDOX_HOME}/backup_to_s3.sh

# 11. Setup hourly cron job for S3 backup
log "${YELLOW}11. Setting up hourly S3 backup${NC}"
# Remove existing cron job if any
crontab -l 2>/dev/null | grep -v "backup_to_s3.sh" | crontab - 2>/dev/null || true

# Add new cron job
if [ ! -z "$S3_BUCKET" ]; then
    (crontab -l 2>/dev/null; echo "0 * * * * ${REDOX_HOME}/backup_to_s3.sh ${EXPERIMENT_DIR} ${S3_BUCKET} >> ${REDOX_HOME}/s3_backup.log 2>&1") | crontab -
    echo -e "${GREEN}✓ Hourly S3 backup configured${NC}"
else
    echo -e "${YELLOW}  Warning: S3_BUCKET not configured. Update the script with your S3 bucket.${NC}"
fi

# 12. System monitoring setup
log "${YELLOW}12. Starting system monitoring${NC}"
cat > ${EXPERIMENT_DIR}/monitor.sh << 'EOF'
#!/bin/bash
while true; do
    echo "=== $(date) ==="
    
    # Memory usage
    echo "Memory:"
    free -h | grep -E "(Mem|Swap)"
    
    # CPU usage
    echo -e "\nCPU Load:"
    uptime
    
    # Top processes
    echo -e "\nTop processes by memory:"
    ps aux --sort=-%mem | head -5 | awk '{printf "%-10s %5s %5s %s\n", $1, $3, $4, $11}'
    
    # Ray processes
    echo -e "\nRay processes: $(ps aux | grep -E "ray::" | wc -l)"
    
    # Disk usage
    echo -e "\nDisk usage:"
    df -h / /tmp | grep -v Filesystem
    
    # GPU usage (if available)
    if command -v nvidia-smi &> /dev/null; then
        echo -e "\nGPU usage:"
        nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader
    fi
    
    echo "----------------------------------------"
    sleep 60
done
EOF

chmod +x ${EXPERIMENT_DIR}/monitor.sh
${EXPERIMENT_DIR}/monitor.sh > ${EXPERIMENT_DIR}/logs/system_monitor.log 2>&1 &
MONITOR_PID=$!

# 13. Create training configuration
log "${YELLOW}13. Creating training configuration${NC}"
cat > ${EXPERIMENT_DIR}/config.json << EOF
{
    "experiment_name": "${EXPERIMENT_NAME}",
    "instance_type": "r7i.48xlarge",
    "instance_ip": "${INSTANCE_IP}",
    "model": "redox_core_v1.json",
    "model_reactions": 10386,
    "timesteps": 5000000,
    "num_actors": 120,
    "save_interval": 50000,
    "experiment_dir": "${EXPERIMENT_DIR}",
    "start_time": "$(date -Iseconds)",
    "ray_config": {
        "memory_monitor": "disabled",
        "object_spilling": "/tmp/ray_spill",
        "plasma_directory": "/tmp/ray_plasma"
    },
    "tensorboard_url": "http://${INSTANCE_IP}:6006"
}
EOF

# 14. Create cleanup script
log "${YELLOW}14. Creating cleanup script${NC}"
cat > ${EXPERIMENT_DIR}/cleanup.sh << EOF
#!/bin/bash
echo "Cleaning up experiment ${EXPERIMENT_NAME}..."

# Stop monitoring
kill $MONITOR_PID 2>/dev/null || true

# Stop TensorBoard
kill $TENSORBOARD_PID 2>/dev/null || true

# Final S3 backup
${REDOX_HOME}/backup_to_s3.sh ${EXPERIMENT_DIR} ${S3_BUCKET}

# Stop Ray
ray stop --force

# Clean up temp files
rm -rf /tmp/ray* 2>/dev/null || true

echo "Cleanup complete"
EOF
chmod +x ${EXPERIMENT_DIR}/cleanup.sh

# 15. Pre-flight summary
log "${BLUE}=== Pre-Flight Check Summary ===${NC}"
echo -e "✓ User context: ${GREEN}redox${NC}"
echo -e "✓ Ulimits: nofile=$(ulimit -n), nproc=$(ulimit -u)"
echo -e "✓ Ray temp cleaned: ${GREEN}OK${NC}"
echo -e "✓ Disk space: /tmp has ${TMP_AVAILABLE}GB available"
echo -e "✓ Python environment: ${GREEN}redox conda activated${NC}"
echo -e "✓ Model files: ${GREEN}verified${NC}"
echo -e "✓ Experiment directory: ${EXPERIMENT_DIR}"
echo -e "✓ TensorBoard: ${GREEN}http://${INSTANCE_IP}:6006${NC}"
echo -e "✓ S3 backup: ${YELLOW}configured (update S3_BUCKET)${NC}"
echo -e "✓ System monitoring: ${GREEN}active${NC}"

# 16. Create tmux session for training
log "${YELLOW}16. Setting up tmux session${NC}"
tmux kill-session -t redox_training 2>/dev/null || true
tmux new-session -d -s redox_training

# 17. Generate training command
TRAINING_CMD="cd ${REDOX_HOME}/redox_balancer && \
export PYTHONPATH=${REDOX_HOME}/redox_balancer/src && \
export RAY_memory_monitor_refresh_ms=0 && \
export RAY_object_spilling_config='{\"type\":\"filesystem\",\"params\":{\"directory_path\":\"/tmp/ray_spill\"}}' && \
export RAY_TMPDIR=/tmp/ray && \
export RAY_PLASMA_DIRECTORY=/tmp/ray_plasma && \
python scripts/train_impala.py \
    --timesteps 5000000 \
    --num-actors 120 \
    --model data/models/redox_core_v1.json \
    --enzymes data/enzyme_library_redox.json \
    --save-interval 50000 \
    --checkpoint-dir ${EXPERIMENT_DIR}/checkpoints \
    --tensorboard-dir ${EXPERIMENT_DIR}/tensorboard \
    2>&1 | tee ${EXPERIMENT_DIR}/training.log"

# Save command for reference
echo "$TRAINING_CMD" > ${EXPERIMENT_DIR}/training_command.sh
chmod +x ${EXPERIMENT_DIR}/training_command.sh

echo
echo -e "${GREEN}=== Pre-flight checks complete! ===${NC}"
echo
echo "Experiment: ${EXPERIMENT_NAME}"
echo "Directory: ${EXPERIMENT_DIR}"
echo
echo -e "${YELLOW}To start training:${NC}"
echo "1. tmux attach -t redox_training"
echo "2. Paste or run: ${EXPERIMENT_DIR}/training_command.sh"
echo
echo -e "${YELLOW}To monitor:${NC}"
echo "- Training log: tail -f ${EXPERIMENT_DIR}/training.log"
echo "- System stats: tail -f ${EXPERIMENT_DIR}/logs/system_monitor.log"
echo "- TensorBoard: http://${INSTANCE_IP}:6006"
echo
echo -e "${YELLOW}To cleanup when done:${NC}"
echo "- Run: ${EXPERIMENT_DIR}/cleanup.sh"
echo
echo -e "${BLUE}Ready to start training!${NC}"

# Create a convenience script to tail all logs
cat > ${EXPERIMENT_DIR}/watch_logs.sh << 'EOF'
#!/bin/bash
# Watch all logs in split panes
tmux new-session -d -s logs
tmux send-keys -t logs "tail -f ${EXPERIMENT_DIR}/training.log" C-m
tmux split-window -t logs -h
tmux send-keys -t logs "tail -f ${EXPERIMENT_DIR}/logs/system_monitor.log" C-m
tmux attach -t logs
EOF
chmod +x ${EXPERIMENT_DIR}/watch_logs.sh

# Export experiment directory for easy access
export CURRENT_EXPERIMENT_DIR=${EXPERIMENT_DIR}
echo "export CURRENT_EXPERIMENT_DIR=${EXPERIMENT_DIR}" >> ${REDOX_HOME}/.bashrc