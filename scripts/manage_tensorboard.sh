#!/bin/bash
# TensorBoard Management Script
# Ensures TensorBoard runs continuously and recovers from crashes

set -e

# Configuration
TENSORBOARD_PORT=6006
TENSORBOARD_BASE_DIR="/home/redox/redox_balancer/experiments"
TENSORBOARD_LOG="/home/redox/tensorboard.log"
TENSORBOARD_PID_FILE="/home/redox/.tensorboard.pid"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to check if TensorBoard is running
is_tensorboard_running() {
    if [ -f "$TENSORBOARD_PID_FILE" ]; then
        local pid=$(cat "$TENSORBOARD_PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    
    # Also check by process name
    if pgrep -f "tensorboard.*--port=$TENSORBOARD_PORT" > /dev/null; then
        return 0
    fi
    
    return 1
}

# Function to stop TensorBoard
stop_tensorboard() {
    echo -e "${YELLOW}Stopping TensorBoard...${NC}"
    
    # Try PID file first
    if [ -f "$TENSORBOARD_PID_FILE" ]; then
        local pid=$(cat "$TENSORBOARD_PID_FILE")
        if kill "$pid" 2>/dev/null; then
            echo -e "${GREEN}✓ Stopped TensorBoard (PID: $pid)${NC}"
        fi
        rm -f "$TENSORBOARD_PID_FILE"
    fi
    
    # Kill any remaining TensorBoard processes
    pkill -f "tensorboard.*--port=$TENSORBOARD_PORT" 2>/dev/null || true
    
    sleep 2
}

# Function to start TensorBoard
start_tensorboard() {
    echo -e "${YELLOW}Starting TensorBoard...${NC}"
    
    # Check if already running
    if is_tensorboard_running; then
        echo -e "${YELLOW}TensorBoard is already running${NC}"
        return 0
    fi
    
    # Check if logdir exists
    if [ ! -d "$TENSORBOARD_BASE_DIR" ]; then
        echo -e "${RED}ERROR: TensorBoard base directory not found: $TENSORBOARD_BASE_DIR${NC}"
        return 1
    fi
    
    # Start TensorBoard
    nohup tensorboard \
        --logdir="$TENSORBOARD_BASE_DIR" \
        --bind_all \
        --port=$TENSORBOARD_PORT \
        --reload_interval=30 \
        --samples_per_plugin="scalars=10000,images=100" \
        > "$TENSORBOARD_LOG" 2>&1 &
    
    local pid=$!
    echo $pid > "$TENSORBOARD_PID_FILE"
    
    # Wait a moment and check if it started successfully
    sleep 3
    if ps -p "$pid" > /dev/null; then
        echo -e "${GREEN}✓ TensorBoard started successfully${NC}"
        echo "  PID: $pid"
        echo "  Port: $TENSORBOARD_PORT"
        echo "  Log: $TENSORBOARD_LOG"
        
        # Get instance IP
        local instance_ip=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "localhost")
        echo -e "  URL: ${BLUE}http://${instance_ip}:${TENSORBOARD_PORT}${NC}"
        
        return 0
    else
        echo -e "${RED}✗ Failed to start TensorBoard${NC}"
        echo "Check log: $TENSORBOARD_LOG"
        return 1
    fi
}

# Function to restart TensorBoard
restart_tensorboard() {
    stop_tensorboard
    start_tensorboard
}

# Function to check TensorBoard status
status_tensorboard() {
    echo -e "${BLUE}=== TensorBoard Status ===${NC}"
    
    if is_tensorboard_running; then
        echo -e "Status: ${GREEN}Running${NC}"
        
        # Get PID
        local pid=""
        if [ -f "$TENSORBOARD_PID_FILE" ]; then
            pid=$(cat "$TENSORBOARD_PID_FILE")
        else
            pid=$(pgrep -f "tensorboard.*--port=$TENSORBOARD_PORT" | head -1)
        fi
        
        if [ -n "$pid" ]; then
            echo "PID: $pid"
            
            # Get memory usage
            local mem_usage=$(ps -p "$pid" -o %mem,rss | tail -1)
            echo "Memory: $mem_usage"
            
            # Get uptime
            local uptime=$(ps -p "$pid" -o etime | tail -1 | xargs)
            echo "Uptime: $uptime"
        fi
        
        # Check if port is listening
        if netstat -tlpn 2>/dev/null | grep -q ":$TENSORBOARD_PORT"; then
            echo -e "Port $TENSORBOARD_PORT: ${GREEN}Listening${NC}"
        else
            echo -e "Port $TENSORBOARD_PORT: ${RED}Not listening${NC}"
        fi
        
        # Show recent log entries
        if [ -f "$TENSORBOARD_LOG" ]; then
            echo
            echo "Recent log entries:"
            tail -5 "$TENSORBOARD_LOG" | sed 's/^/  /'
        fi
    else
        echo -e "Status: ${RED}Not running${NC}"
    fi
    
    # Show experiment directories
    echo
    echo "Experiment directories:"
    if [ -d "$TENSORBOARD_BASE_DIR" ]; then
        local exp_count=$(find "$TENSORBOARD_BASE_DIR" -maxdepth 1 -type d -name "redox_*" | wc -l)
        echo "  Total experiments: $exp_count"
        echo "  Recent experiments:"
        find "$TENSORBOARD_BASE_DIR" -maxdepth 1 -type d -name "redox_*" -printf "%T+ %f\n" 2>/dev/null | sort -r | head -5 | sed 's/^/    /'
    else
        echo "  Base directory not found: $TENSORBOARD_BASE_DIR"
    fi
}

# Function to setup auto-restart via cron
setup_auto_restart() {
    echo -e "${YELLOW}Setting up auto-restart...${NC}"
    
    # Create watchdog script
    cat > /home/redox/tensorboard_watchdog.sh << 'EOF'
#!/bin/bash
# TensorBoard watchdog - ensures TensorBoard stays running

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
${SCRIPT_DIR}/redox_balancer/scripts/manage_tensorboard.sh check-restart >> /home/redox/tensorboard_watchdog.log 2>&1
EOF
    
    chmod +x /home/redox/tensorboard_watchdog.sh
    
    # Add to crontab
    (crontab -l 2>/dev/null | grep -v "tensorboard_watchdog"; echo "*/5 * * * * /home/redox/tensorboard_watchdog.sh") | crontab -
    
    echo -e "${GREEN}✓ Auto-restart configured (checks every 5 minutes)${NC}"
}

# Function to check and restart if needed
check_restart() {
    if ! is_tensorboard_running; then
        echo "[$(date)] TensorBoard not running, restarting..."
        start_tensorboard
    fi
}

# Main logic
case "${1:-status}" in
    start)
        start_tensorboard
        ;;
    stop)
        stop_tensorboard
        ;;
    restart)
        restart_tensorboard
        ;;
    status)
        status_tensorboard
        ;;
    setup-auto-restart)
        setup_auto_restart
        ;;
    check-restart)
        check_restart
        ;;
    logs)
        if [ -f "$TENSORBOARD_LOG" ]; then
            tail -f "$TENSORBOARD_LOG"
        else
            echo "Log file not found: $TENSORBOARD_LOG"
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|setup-auto-restart|check-restart|logs}"
        echo
        echo "Commands:"
        echo "  start              - Start TensorBoard"
        echo "  stop               - Stop TensorBoard"
        echo "  restart            - Restart TensorBoard"
        echo "  status             - Show TensorBoard status"
        echo "  setup-auto-restart - Configure automatic restart via cron"
        echo "  check-restart      - Check and restart if not running (for cron)"
        echo "  logs               - Tail TensorBoard logs"
        exit 1
        ;;
esac