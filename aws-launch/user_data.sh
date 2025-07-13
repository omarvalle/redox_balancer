#!/bin/bash
set -e

# Log all output
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "=== Starting instance setup at $(date) ==="

# Update system
apt-get update
apt-get install -y \
    build-essential \
    git \
    htop \
    tmux \
    wget \
    curl \
    vim \
    python3-dev \
    libgfortran5 \
    libblas-dev \
    liblapack-dev \
    gfortran

# Install AWS CLI v2 for ARM64
cd /tmp
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Create user for experiments (avoid running as root)
useradd -m -s /bin/bash redox
usermod -aG sudo redox
echo "redox ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to redox user for remaining setup
su - redox << 'USEREOF'
cd /home/redox

# Install Miniconda for ARM64
wget https://repo.anaconda.com/miniconda/Miniconda3-py311_24.1.2-0-Linux-aarch64.sh
bash Miniconda3-py311_24.1.2-0-Linux-aarch64.sh -b -p /home/redox/miniconda3
rm Miniconda3-py311_24.1.2-0-Linux-aarch64.sh

# Add conda to PATH
echo 'export PATH="/home/redox/miniconda3/bin:$PATH"' >> ~/.bashrc
export PATH="/home/redox/miniconda3/bin:$PATH"

# Create conda environment with Python 3.11 (more stable than 3.13)
conda create -n redox python=3.11 -y
source activate redox

# Install core dependencies with specific versions
pip install --upgrade pip setuptools wheel
pip install numpy==1.24.3 scipy==1.10.1 pandas==2.0.3
pip install matplotlib==3.7.2 seaborn==0.12.2
pip install torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu

# Install Ray with specific version for stability
pip install "ray[default]==2.9.0"

# Install COBRApy and dependencies
pip install cobra==0.26.3 optlang==1.7.0
pip install gymnasium==0.29.1

# Try to install HiGHS (may fail on ARM64, that's OK)
pip install highspy || echo "HiGHS installation failed, will use GLPK"

# Configure Ray for large memory system
mkdir -p ~/.ray
cat > ~/.ray/ray_init.yaml << 'RAYEOF'
# Optimized for 3TB RAM system
object_store_memory: 1000000000000  # 1TB for object store
redis_max_memory: 10000000000       # 10GB for Redis
num_heartbeats_timeout: 300         # 5 min timeout for large models
RAYEOF

# Set up working directory
mkdir -p /home/redox/redox_balancer
cd /home/redox/redox_balancer

# Create system optimization script
cat > optimize_system.sh << 'OPTEOF'
#!/bin/bash
# System optimizations for large memory workloads

# Disable swap (we have plenty of RAM)
sudo swapoff -a

# Increase file descriptors
echo "* soft nofile 1048576" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 1048576" | sudo tee -a /etc/security/limits.conf

# Set up huge pages for better memory performance
echo 50000 | sudo tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages

# Optimize kernel parameters for Ray
echo "net.core.somaxconn = 1024" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 1024" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.ip_local_port_range = 10000 65000" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

echo "System optimizations applied"
OPTEOF
chmod +x optimize_system.sh

# Create monitoring script
cat > monitor.sh << 'MONEOF'
#!/bin/bash
# Real-time monitoring for training runs

while true; do
    clear
    echo "=== System Monitor - $(date) ==="
    echo
    echo "=== Memory Usage ==="
    free -h
    echo
    echo "=== Top Processes by Memory ==="
    ps aux --sort=-%mem | head -10
    echo
    echo "=== Ray Status ==="
    ray status 2>/dev/null || echo "Ray not running"
    echo
    echo "=== GPU Status ==="
    echo "No GPU (CPU instance)"
    echo
    sleep 10
done
MONEOF
chmod +x monitor.sh

echo "Setup complete for user redox"
USEREOF

# Final message
echo "=== Instance setup completed at $(date) ==="
echo "SSH as: ssh -i your-key.pem ubuntu@<instance-ip>"
echo "Then: sudo su - redox"