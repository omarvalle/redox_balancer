#!/bin/bash
# Training Monitor Script for Redox Balancer
# Usage: ./monitor_training.sh [experiment_dir]

# Configuration
INSTANCE_IP="44.193.26.15"
KEY_PATH="$HOME/.ssh/succinate-sink-training-key.pem"
REMOTE_USER="ubuntu"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default experiment directory (latest)
if [ -z "$1" ]; then
    EXPERIMENT_DIR=$(ssh -o ConnectTimeout=10 -i $KEY_PATH $REMOTE_USER@$INSTANCE_IP \
        "sudo -u redox bash -c 'ls -td /home/redox/redox_balancer/experiments/redox_120actors_* 2>/dev/null | head -1'")
else
    EXPERIMENT_DIR="$1"
fi

echo -e "${BLUE}===== REDOX BALANCER TRAINING MONITOR =====${NC}"
echo -e "Instance: ${GREEN}$INSTANCE_IP${NC}"
echo -e "Experiment: ${GREEN}$EXPERIMENT_DIR${NC}"
echo ""

# Function to check connection
check_connection() {
    if ssh -o ConnectTimeout=5 -i $KEY_PATH $REMOTE_USER@$INSTANCE_IP "echo 'Connected'" &>/dev/null; then
        return 0
    else
        echo -e "${RED}ERROR: Cannot connect to instance${NC}"
        echo "Instance may be overloaded or network issues"
        return 1
    fi
}

# Function to get training stats
get_training_stats() {
    ssh -o ConnectTimeout=10 -i $KEY_PATH $REMOTE_USER@$INSTANCE_IP "sudo -u redox bash -c '
        # Get latest stats
        LOG_FILE=\"${EXPERIMENT_DIR}.log\"
        if [ -f \"\$LOG_FILE\" ]; then
            LATEST_STATS=\$(tail -100 \"\$LOG_FILE\" | grep \"Timesteps:\" | tail -1)
            if [ -n \"\$LATEST_STATS\" ]; then
                echo \"LATEST_STATS:\$LATEST_STATS\"
                
                # Extract values
                TIMESTEPS=\$(echo \"\$LATEST_STATS\" | grep -oP \"Timesteps: \K[0-9,]+\" | tr -d \",\")
                FPS=\$(echo \"\$LATEST_STATS\" | grep -oP \"FPS: \K[0-9]+\")
                RETURN=\$(echo \"\$LATEST_STATS\" | grep -oP \"Return: \K[0-9.-]+\")
                
                # Calculate progress
                TARGET=10000000
                PROGRESS=\$(awk \"BEGIN {printf \\\"%.2f\\\", \$TIMESTEPS * 100 / \$TARGET}\")
                
                echo \"TIMESTEPS:\$TIMESTEPS\"
                echo \"FPS:\$FPS\"
                echo \"RETURN:\$RETURN\"
                echo \"PROGRESS:\$PROGRESS\"
                
                # Estimate time remaining
                if [ \"\$FPS\" -gt 0 ]; then
                    REMAINING=\$(( (\$TARGET - \$TIMESTEPS) / \$FPS ))
                    HOURS=\$(( \$REMAINING / 3600 ))
                    MINUTES=\$(( (\$REMAINING % 3600) / 60 ))
                    echo \"TIME_REMAINING:\${HOURS}h \${MINUTES}m\"
                fi
            fi
        fi
    '"
}

# Function to get system stats
get_system_stats() {
    ssh -o ConnectTimeout=10 -i $KEY_PATH $REMOTE_USER@$INSTANCE_IP "
        # CPU usage
        CPU=\$(top -bn1 | grep 'Cpu(s)' | awk '{print \$2}' | cut -d'%' -f1)
        echo \"CPU_USAGE:\$CPU\"
        
        # Memory usage
        MEM_INFO=\$(free -h | grep Mem)
        MEM_USED=\$(echo \$MEM_INFO | awk '{print \$3}')
        MEM_TOTAL=\$(echo \$MEM_INFO | awk '{print \$2}')
        echo \"MEMORY:\$MEM_USED / \$MEM_TOTAL\"
        
        # Process check
        TRAINING_PID=\$(ps aux | grep 'train_impala.py' | grep -v grep | awk '{print \$2}' | head -1)
        if [ -n \"\$TRAINING_PID\" ]; then
            echo \"PROCESS:Running (PID: \$TRAINING_PID)\"
        else
            echo \"PROCESS:Not Running\"
        fi
        
        # Disk usage
        DISK_USAGE=\$(df -h / | tail -1 | awk '{print \$5}')
        echo \"DISK_USAGE:\$DISK_USAGE\"
    "
}

# Function to get checkpoint info
get_checkpoint_info() {
    ssh -o ConnectTimeout=10 -i $KEY_PATH $REMOTE_USER@$INSTANCE_IP "sudo -u redox bash -c '
        if [ -d \"$EXPERIMENT_DIR\" ]; then
            # Count checkpoints
            NUM_CHECKPOINTS=\$(ls -d $EXPERIMENT_DIR/step_* 2>/dev/null | wc -l)
            echo \"CHECKPOINTS:\$NUM_CHECKPOINTS\"
            
            # Latest checkpoint
            LATEST_CHECKPOINT=\$(ls -td $EXPERIMENT_DIR/step_* 2>/dev/null | head -1 | xargs basename)
            if [ -n \"\$LATEST_CHECKPOINT\" ]; then
                echo \"LATEST_CHECKPOINT:\$LATEST_CHECKPOINT\"
            fi
            
            # Total size
            TOTAL_SIZE=\$(du -sh $EXPERIMENT_DIR 2>/dev/null | cut -f1)
            echo \"EXPERIMENT_SIZE:\$TOTAL_SIZE\"
        fi
    '"
}

# Main monitoring loop
while true; do
    clear
    echo -e "${BLUE}===== REDOX BALANCER TRAINING MONITOR =====${NC}"
    echo -e "Time: $(date)"
    echo -e "Instance: ${GREEN}$INSTANCE_IP${NC}"
    echo ""
    
    if check_connection; then
        # Get all stats
        TRAINING_STATS=$(get_training_stats)
        SYSTEM_STATS=$(get_system_stats)
        CHECKPOINT_INFO=$(get_checkpoint_info)
        
        # Parse and display training stats
        echo -e "${YELLOW}=== Training Progress ===${NC}"
        TIMESTEPS=$(echo "$TRAINING_STATS" | grep "TIMESTEPS:" | cut -d: -f2)
        FPS=$(echo "$TRAINING_STATS" | grep "FPS:" | cut -d: -f2)
        RETURN=$(echo "$TRAINING_STATS" | grep "RETURN:" | cut -d: -f2)
        PROGRESS=$(echo "$TRAINING_STATS" | grep "PROGRESS:" | cut -d: -f2)
        TIME_REMAINING=$(echo "$TRAINING_STATS" | grep "TIME_REMAINING:" | cut -d: -f2-)
        
        if [ -n "$TIMESTEPS" ]; then
            printf "Timesteps:      %'d / 10,000,000 (%.2f%%)\n" $TIMESTEPS $PROGRESS
            echo "FPS:            $FPS"
            echo "Latest Return:  $RETURN"
            echo "Time Remaining: $TIME_REMAINING"
        else
            echo -e "${RED}No training data found${NC}"
        fi
        
        # Display system stats
        echo -e "\n${YELLOW}=== System Resources ===${NC}"
        CPU=$(echo "$SYSTEM_STATS" | grep "CPU_USAGE:" | cut -d: -f2)
        MEMORY=$(echo "$SYSTEM_STATS" | grep "MEMORY:" | cut -d: -f2-)
        PROCESS=$(echo "$SYSTEM_STATS" | grep "PROCESS:" | cut -d: -f2-)
        DISK=$(echo "$SYSTEM_STATS" | grep "DISK_USAGE:" | cut -d: -f2)
        
        echo "CPU Usage:      ${CPU}%"
        echo "Memory:         $MEMORY"
        echo "Process:        $PROCESS"
        echo "Disk Usage:     $DISK"
        
        # Display checkpoint info
        echo -e "\n${YELLOW}=== Checkpoint Status ===${NC}"
        NUM_CHECKPOINTS=$(echo "$CHECKPOINT_INFO" | grep "CHECKPOINTS:" | cut -d: -f2)
        LATEST_CHECKPOINT=$(echo "$CHECKPOINT_INFO" | grep "LATEST_CHECKPOINT:" | cut -d: -f2)
        EXPERIMENT_SIZE=$(echo "$CHECKPOINT_INFO" | grep "EXPERIMENT_SIZE:" | cut -d: -f2)
        
        echo "Checkpoints:    $NUM_CHECKPOINTS saved"
        echo "Latest:         $LATEST_CHECKPOINT"
        echo "Total Size:     $EXPERIMENT_SIZE"
        
        # Show latest log line
        echo -e "\n${YELLOW}=== Latest Log Entry ===${NC}"
        LATEST_LOG=$(echo "$TRAINING_STATS" | grep "LATEST_STATS:" | cut -d: -f2-)
        if [ -n "$LATEST_LOG" ]; then
            echo "$LATEST_LOG"
        fi
    fi
    
    echo -e "\n${BLUE}Refreshing in 30 seconds... (Press Ctrl+C to exit)${NC}"
    sleep 30
done