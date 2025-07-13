#!/bin/bash
# Ray Cleanup Script
# Safely removes orphaned Ray files and processes

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}=== Ray Cleanup Utility ===${NC}"
echo "This script will safely clean up Ray's temporary files and processes"
echo

# Function to get size of directory/files
get_size() {
    local path="$1"
    if [ -e "$path" ]; then
        du -sh "$path" 2>/dev/null | cut -f1 || echo "0"
    else
        echo "0"
    fi
}

# 1. Stop Ray gracefully
echo -e "${YELLOW}1. Stopping Ray cluster...${NC}"
if command -v ray &> /dev/null; then
    if ray status &> /dev/null; then
        ray stop --force
        echo -e "${GREEN}✓ Ray cluster stopped${NC}"
    else
        echo "  Ray cluster not running"
    fi
else
    echo "  Ray not installed"
fi

# Wait for processes to terminate
sleep 3

# 2. Kill any remaining Ray processes
echo -e "${YELLOW}2. Cleaning up Ray processes...${NC}"
RAY_PIDS=$(pgrep -f "ray::" || true)
if [ -n "$RAY_PIDS" ]; then
    echo "  Found $(echo $RAY_PIDS | wc -w) Ray processes"
    for pid in $RAY_PIDS; do
        kill -9 $pid 2>/dev/null || true
    done
    echo -e "${GREEN}✓ Ray processes terminated${NC}"
else
    echo "  No Ray processes found"
fi

# 3. Clean up Ray directories
echo -e "${YELLOW}3. Cleaning up Ray directories...${NC}"

RAY_DIRS=(
    "/tmp/ray"
    "/tmp/ray_spill"
    "/tmp/ray_plasma"
    "/tmp/ray_tmp_*"
    "$HOME/.ray"
    "/dev/shm/ray_*"
    "/dev/shm/plasma_*"
)

TOTAL_FREED=0
for dir_pattern in "${RAY_DIRS[@]}"; do
    for dir in $dir_pattern; do
        if [ -e "$dir" ]; then
            SIZE=$(get_size "$dir")
            echo -n "  Removing $dir ($SIZE)... "
            if rm -rf "$dir" 2>/dev/null; then
                echo -e "${GREEN}✓${NC}"
            else
                # Try with sudo if regular removal fails
                if sudo rm -rf "$dir" 2>/dev/null; then
                    echo -e "${GREEN}✓ (sudo)${NC}"
                else
                    echo -e "${RED}✗ Failed${NC}"
                fi
            fi
        fi
    done
done

# 4. Clean up core dumps
echo -e "${YELLOW}4. Cleaning up core dumps...${NC}"
CORE_COUNT=$(find /tmp -name "core.*" -o -name "*.core" 2>/dev/null | wc -l || echo 0)
if [ $CORE_COUNT -gt 0 ]; then
    echo "  Found $CORE_COUNT core dump files"
    find /tmp -name "core.*" -o -name "*.core" -exec rm -f {} \; 2>/dev/null
    echo -e "${GREEN}✓ Core dumps removed${NC}"
else
    echo "  No core dumps found"
fi

# 5. Clean up shared memory segments
echo -e "${YELLOW}5. Cleaning up shared memory...${NC}"
SHM_COUNT=0
while read -r shmid; do
    if [ -n "$shmid" ]; then
        ipcrm -m "$shmid" 2>/dev/null && ((SHM_COUNT++)) || true
    fi
done < <(ipcs -m 2>/dev/null | grep "$USER" | awk '{print $2}')

if [ $SHM_COUNT -gt 0 ]; then
    echo -e "${GREEN}✓ Removed $SHM_COUNT shared memory segments${NC}"
else
    echo "  No shared memory segments to clean"
fi

# 6. Clean up old log files
echo -e "${YELLOW}6. Cleaning up old logs...${NC}"
OLD_LOGS=$(find /tmp -name "*.log" -mtime +1 -size +100M 2>/dev/null | wc -l || echo 0)
if [ $OLD_LOGS -gt 0 ]; then
    echo "  Found $OLD_LOGS large old log files"
    find /tmp -name "*.log" -mtime +1 -size +100M -exec rm -f {} \; 2>/dev/null
    echo -e "${GREEN}✓ Old logs removed${NC}"
else
    echo "  No old logs to clean"
fi

# 7. Create fresh Ray directories
echo -e "${YELLOW}7. Creating fresh Ray directories...${NC}"
mkdir -p /tmp/ray_spill
mkdir -p /tmp/ray_plasma
chmod 755 /tmp/ray_spill /tmp/ray_plasma
echo -e "${GREEN}✓ Directories created${NC}"

# 8. Summary
echo
echo -e "${BLUE}=== Cleanup Summary ===${NC}"
echo "Disk space in /tmp:"
df -h /tmp | tail -1 | awk '{printf "  Total: %s, Used: %s, Available: %s (%s used)\n", $2, $3, $4, $5}'
echo
echo "Memory status:"
free -h | grep Mem | awk '{printf "  Total: %s, Used: %s, Available: %s\n", $2, $3, $7}'
echo
echo -e "${GREEN}✓ Ray cleanup complete!${NC}"
echo
echo "You can now start a fresh Ray cluster."