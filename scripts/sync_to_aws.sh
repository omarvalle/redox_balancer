#!/bin/bash
# Sync redox_balancer project to AWS instance
# Best practices: SSH only, proper error handling, progress tracking

set -e

# Configuration - REPLACE these values
INSTANCE_IP="44.193.26.15"
KEY_PATH="~/.ssh/succinate-sink-training-key.pem"
REMOTE_USER="ubuntu"  # Initial SSH as ubuntu, then switch to redox user

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Error handler
error_exit() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit 1
}

# Validate inputs
if [ "$INSTANCE_IP" = "YOUR_INSTANCE_IP" ]; then
    error_exit "Please set INSTANCE_IP in this script"
fi

if [ ! -f "${KEY_PATH/#\~/$HOME}" ]; then
    error_exit "SSH key not found at $KEY_PATH"
fi

echo -e "${GREEN}=== Syncing redox_balancer to AWS ===${NC}"
echo "Target: $REMOTE_USER@$INSTANCE_IP"
echo "Key: $KEY_PATH"

# Test SSH connection
echo -e "${YELLOW}Testing SSH connection...${NC}"
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i $KEY_PATH $REMOTE_USER@$INSTANCE_IP "echo 'SSH connection successful'" || error_exit "Cannot connect to instance"

# Check if redox user exists
echo -e "${YELLOW}Checking redox user setup...${NC}"
ssh -i $KEY_PATH $REMOTE_USER@$INSTANCE_IP "id redox" || error_exit "Redox user not found. Instance may still be initializing."

# Create remote directory structure
echo -e "${YELLOW}Creating remote directories...${NC}"
ssh -i $KEY_PATH $REMOTE_USER@$INSTANCE_IP "sudo -u redox mkdir -p /home/redox/redox_balancer/{src,data,scripts,experiments}"

# Prepare file list (exclude large/unnecessary files)
echo -e "${YELLOW}Preparing file list...${NC}"
cat > /tmp/rsync_exclude.txt << EOF
*.pyc
__pycache__/
.git/
.gitignore
experiments/
*.log
nohup.out
wandb/
.pytest_cache/
.mypy_cache/
.coverage
.env
.venv/
venv/
*.egg-info/
.DS_Store
.idea/
.vscode/
*.swp
*.swo
*~
redox_training.log
EOF

# Calculate total size
TOTAL_SIZE=$(du -sh . --exclude-from=/tmp/rsync_exclude.txt 2>/dev/null | cut -f1)
echo "Total size to sync: $TOTAL_SIZE"

# Sync code and data with progress
echo -e "${YELLOW}Syncing project files...${NC}"
rsync -avzP \
  --exclude-from=/tmp/rsync_exclude.txt \
  --chmod=D755,F644 \
  -e "ssh -i $KEY_PATH" \
  /home/omar/redox_balancer/ \
  $REMOTE_USER@$INSTANCE_IP:/tmp/redox_sync/

# Move files to redox user directory
echo -e "${YELLOW}Moving files to redox user...${NC}"
ssh -i $KEY_PATH $REMOTE_USER@$INSTANCE_IP << 'EOF'
sudo cp -r /tmp/redox_sync/* /home/redox/redox_balancer/
sudo chown -R redox:redox /home/redox/redox_balancer/
sudo chmod +x /home/redox/redox_balancer/scripts/*.sh
sudo rm -rf /tmp/redox_sync
EOF

# Verify sync
echo -e "${YELLOW}Verifying sync...${NC}"
ssh -i $KEY_PATH $REMOTE_USER@$INSTANCE_IP "sudo -u redox ls -la /home/redox/redox_balancer/"

# Create convenience script on remote
echo -e "${YELLOW}Creating convenience scripts...${NC}"
ssh -i $KEY_PATH $REMOTE_USER@$INSTANCE_IP << 'EOF'
# Create quick-start script for redox user
sudo -u redox bash -c 'cat > /home/redox/start_training.sh << "SCRIPT"
#!/bin/bash
# Quick start script for training

cd /home/redox/redox_balancer

# Activate conda
source /home/redox/miniconda3/bin/activate redox

# Set Python path
export PYTHONPATH=/home/redox/redox_balancer/src

# Check environment
echo "Python: $(which python)"
echo "Ray: $(ray --version 2>/dev/null || echo "Not installed")"
echo "Working dir: $(pwd)"
echo

# Run system optimizations
if [ -f optimize_system.sh ]; then
    echo "Running system optimizations..."
    ./optimize_system.sh
fi

echo "Ready to train! Example command:"
echo "python scripts/train_impala.py --timesteps 200000 --num-actors 30 --model data/models/redox_core_v1.json --enzymes data/enzyme_library_redox.json --save-interval 10000 --checkpoint-dir experiments/test_$(date +%Y%m%d_%H%M%S)"
SCRIPT
chmod +x /home/redox/start_training.sh'

# Create SSH helper
sudo bash -c 'cat > /home/ubuntu/connect_redox.sh << "SCRIPT"
#!/bin/bash
sudo su - redox
SCRIPT
chmod +x /home/ubuntu/connect_redox.sh'
EOF

# Clean up
rm -f /tmp/rsync_exclude.txt

echo -e "${GREEN}=== Sync complete! ===${NC}"
echo
echo "Next steps:"
echo "1. SSH to instance: ssh -i $KEY_PATH $REMOTE_USER@$INSTANCE_IP"
echo "2. Switch to redox user: ./connect_redox.sh"
echo "3. Start training: ./start_training.sh"
echo
echo "Monitoring:"
echo "- System monitor: ./monitor.sh"
echo "- Training logs: tail -f redox_balancer/experiments/*/training.log"
echo "- Memory usage: free -h"
echo
echo -e "${YELLOW}Remember to set auto-shutdown:${NC}"
echo "sudo shutdown -h +720  # 12 hours"