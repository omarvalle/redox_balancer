#!/bin/bash
# System Health Check Script for Redox Training
# Performs comprehensive checks on system resources and training status

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Redox Training System Health Check ===${NC}"
echo "Time: $(date)"
echo

# Function to check and display status
check_item() {
    local name="$1"
    local value="$2"
    local status="$3"
    
    printf "%-30s: " "$name"
    
    case "$status" in
        "good")
            echo -e "${value} ${GREEN}✓${NC}"
            ;;
        "warning")
            echo -e "${value} ${YELLOW}⚠${NC}"
            ;;
        "error")
            echo -e "${value} ${RED}✗${NC}"
            ;;
        *)
            echo "$value"
            ;;
    esac
}

# 1. User and Environment
echo -e "${YELLOW}User & Environment:${NC}"
check_item "Current user" "$USER" $([ "$USER" = "redox" ] && echo "good" || echo "warning")
check_item "Home directory" "$HOME" "info"
check_item "Python path" "${PYTHONPATH:-Not set}" $([ -n "$PYTHONPATH" ] && echo "good" || echo "warning")

# Check conda environment
if command -v conda &> /dev/null; then
    CONDA_ENV=$(conda info --envs | grep '*' | awk '{print $1}')
    check_item "Conda environment" "${CONDA_ENV:-base}" $([ "$CONDA_ENV" = "redox" ] && echo "good" || echo "warning")
else
    check_item "Conda" "Not found" "error"
fi
echo

# 2. System Limits
echo -e "${YELLOW}System Limits:${NC}"
NOFILE=$(ulimit -n)
NPROC=$(ulimit -u)
check_item "Open files limit" "$NOFILE" $([ $NOFILE -ge 1048576 ] && echo "good" || echo "warning")
check_item "Process limit" "$NPROC" $([ $NPROC -ge 524288 ] && echo "good" || echo "warning")
echo

# 3. Memory Status
echo -e "${YELLOW}Memory Status:${NC}"
MEM_TOTAL=$(free -g | grep Mem | awk '{print $2}')
MEM_USED=$(free -g | grep Mem | awk '{print $3}')
MEM_AVAIL=$(free -g | grep Mem | awk '{print $7}')
MEM_PERCENT=$((MEM_USED * 100 / MEM_TOTAL))

check_item "Total memory" "${MEM_TOTAL}GB" "info"
check_item "Used memory" "${MEM_USED}GB (${MEM_PERCENT}%)" \
    $([ $MEM_PERCENT -lt 80 ] && echo "good" || [ $MEM_PERCENT -lt 90 ] && echo "warning" || echo "error")
check_item "Available memory" "${MEM_AVAIL}GB" \
    $([ $MEM_AVAIL -gt 100 ] && echo "good" || [ $MEM_AVAIL -gt 50 ] && echo "warning" || echo "error")

# Check for swap usage
SWAP_USED=$(free -g | grep Swap | awk '{print $3}')
check_item "Swap used" "${SWAP_USED}GB" $([ $SWAP_USED -eq 0 ] && echo "good" || echo "warning")
echo

# 4. Disk Space
echo -e "${YELLOW}Disk Space:${NC}"
# Root filesystem
ROOT_USED=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
ROOT_AVAIL=$(df -h / | tail -1 | awk '{print $4}')
check_item "Root filesystem" "${ROOT_AVAIL} free (${ROOT_USED}% used)" \
    $([ $ROOT_USED -lt 80 ] && echo "good" || [ $ROOT_USED -lt 90 ] && echo "warning" || echo "error")

# /tmp filesystem
TMP_USED=$(df -h /tmp | tail -1 | awk '{print $5}' | sed 's/%//')
TMP_AVAIL=$(df -h /tmp | tail -1 | awk '{print $4}')
check_item "/tmp filesystem" "${TMP_AVAIL} free (${TMP_USED}% used)" \
    $([ $TMP_USED -lt 80 ] && echo "good" || [ $TMP_USED -lt 90 ] && echo "warning" || echo "error")
echo

# 5. Ray Status
echo -e "${YELLOW}Ray Status:${NC}"
if command -v ray &> /dev/null; then
    # Check if Ray is running
    if ray status &> /dev/null; then
        check_item "Ray cluster" "Running" "good"
        
        # Count Ray processes
        RAY_PROCS=$(ps aux | grep -E "ray::" | grep -v grep | wc -l)
        check_item "Ray processes" "$RAY_PROCS" $([ $RAY_PROCS -gt 0 ] && echo "good" || echo "warning")
        
        # Check Ray temp directories
        for dir in /tmp/ray /tmp/ray_spill /tmp/ray_plasma; do
            if [ -d "$dir" ]; then
                SIZE=$(du -sh "$dir" 2>/dev/null | cut -f1 || echo "0")
                check_item "$(basename $dir) size" "$SIZE" "info"
            fi
        done
    else
        check_item "Ray cluster" "Not running" "warning"
    fi
else
    check_item "Ray" "Not installed" "error"
fi
echo

# 6. Training Status
echo -e "${YELLOW}Training Status:${NC}"
# Check for active tmux sessions
if tmux has-session -t redox_training 2>/dev/null; then
    check_item "Training session" "Active (tmux: redox_training)" "good"
else
    check_item "Training session" "Not found" "info"
fi

# Check for current experiment
if [ -n "$CURRENT_EXPERIMENT_DIR" ] && [ -d "$CURRENT_EXPERIMENT_DIR" ]; then
    check_item "Current experiment" "$(basename $CURRENT_EXPERIMENT_DIR)" "good"
    
    # Check training log
    if [ -f "$CURRENT_EXPERIMENT_DIR/training.log" ]; then
        LOG_SIZE=$(ls -lh "$CURRENT_EXPERIMENT_DIR/training.log" | awk '{print $5}')
        LAST_UPDATE=$(stat -c %y "$CURRENT_EXPERIMENT_DIR/training.log" 2>/dev/null | cut -d. -f1 || stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$CURRENT_EXPERIMENT_DIR/training.log" 2>/dev/null || echo "Unknown")
        check_item "Training log" "${LOG_SIZE}, last update: ${LAST_UPDATE}" "info"
        
        # Check for recent activity
        if [ -f "$CURRENT_EXPERIMENT_DIR/training.log" ]; then
            MINS_AGO=$((($(date +%s) - $(stat -c %Y "$CURRENT_EXPERIMENT_DIR/training.log" 2>/dev/null || stat -f %m "$CURRENT_EXPERIMENT_DIR/training.log" 2>/dev/null || echo 0)) / 60))
            if [ $MINS_AGO -lt 5 ]; then
                check_item "Training activity" "Active (updated ${MINS_AGO}m ago)" "good"
            elif [ $MINS_AGO -lt 30 ]; then
                check_item "Training activity" "Inactive (${MINS_AGO}m since update)" "warning"
            else
                check_item "Training activity" "Stale (${MINS_AGO}m since update)" "error"
            fi
        fi
    fi
    
    # Check checkpoints
    if [ -d "$CURRENT_EXPERIMENT_DIR/checkpoints" ]; then
        CKPT_COUNT=$(ls "$CURRENT_EXPERIMENT_DIR/checkpoints" 2>/dev/null | wc -l)
        LATEST_CKPT=$(ls -t "$CURRENT_EXPERIMENT_DIR/checkpoints" 2>/dev/null | head -1)
        check_item "Checkpoints" "${CKPT_COUNT} saved, latest: ${LATEST_CKPT:-none}" "info"
    fi
else
    check_item "Current experiment" "Not set" "info"
fi
echo

# 7. Network Services
echo -e "${YELLOW}Network Services:${NC}"
# Check TensorBoard
TB_PID=$(pgrep -f tensorboard | head -1)
if [ -n "$TB_PID" ]; then
    TB_PORT=$(netstat -tlpn 2>/dev/null | grep "$TB_PID" | grep -oE ':[0-9]+' | head -1 | sed 's/://')
    check_item "TensorBoard" "Running on port ${TB_PORT:-6006} (PID: $TB_PID)" "good"
else
    check_item "TensorBoard" "Not running" "info"
fi

# Check SSH
if systemctl is-active sshd &>/dev/null || service ssh status &>/dev/null; then
    check_item "SSH service" "Active" "good"
else
    check_item "SSH service" "Inactive" "warning"
fi
echo

# 8. Ray Cleanup Status
echo -e "${YELLOW}Ray Cleanup Check:${NC}"
# Check for orphaned Ray files
ORPHANED_COUNT=0
for pattern in "/tmp/ray_tmp*" "/tmp/core.*ray*" "/dev/shm/*ray*"; do
    COUNT=$(ls $pattern 2>/dev/null | wc -l)
    ORPHANED_COUNT=$((ORPHANED_COUNT + COUNT))
done

if [ $ORPHANED_COUNT -eq 0 ]; then
    check_item "Orphaned Ray files" "None found" "good"
else
    check_item "Orphaned Ray files" "$ORPHANED_COUNT files need cleanup" "warning"
fi

# Check shared memory
SHM_COUNT=$(ipcs -m 2>/dev/null | grep "$USER" | wc -l)
check_item "Shared memory segments" "$SHM_COUNT" $([ $SHM_COUNT -lt 10 ] && echo "good" || echo "warning")
echo

# 9. Summary and Recommendations
echo -e "${BLUE}=== Summary & Recommendations ===${NC}"

# Generate recommendations based on checks
RECOMMENDATIONS=()

if [ "$USER" != "redox" ]; then
    RECOMMENDATIONS+=("Switch to redox user: sudo su - redox")
fi

if [ $NOFILE -lt 1048576 ] || [ $NPROC -lt 524288 ]; then
    RECOMMENDATIONS+=("Update ulimits in /etc/security/limits.conf")
fi

if [ $MEM_PERCENT -gt 90 ]; then
    RECOMMENDATIONS+=("High memory usage - consider reducing num-actors or restarting")
fi

if [ $TMP_USED -gt 80 ]; then
    RECOMMENDATIONS+=("Clean up /tmp directory: sudo rm -rf /tmp/ray_tmp* /tmp/core.*")
fi

if [ $ORPHANED_COUNT -gt 0 ]; then
    RECOMMENDATIONS+=("Clean orphaned Ray files: ray stop --force && rm -rf /tmp/ray*")
fi

if [ ${#RECOMMENDATIONS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ System is healthy and ready for training${NC}"
else
    echo -e "${YELLOW}Recommendations:${NC}"
    for rec in "${RECOMMENDATIONS[@]}"; do
        echo "  • $rec"
    done
fi

echo
echo "Run this check periodically to ensure system health."