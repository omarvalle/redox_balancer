#!/bin/bash
# AWS x8g.48xlarge setup script for redox_balancer
# Following best practices: SSH only, proper IAM, AWS CLI v2

set -e

echo "=== AWS r7i.48xlarge Setup Script ==="
echo "Instance type: r7i.48xlarge (1.5TB RAM, 192 vCPUs, x86_64)"
echo "Estimated cost: ~$12.08/hour"
echo

# Configuration
INSTANCE_TYPE="r7i.48xlarge"
# Ubuntu 22.04 LTS x86_64 - more stable than Amazon Linux for our use case
AMI_ID="ami-09ac0b140f63d3458"  # Ubuntu 22.04 x86_64 in us-east-1
KEY_NAME="your-key-name"  # REPLACE with your SSH key name
SECURITY_GROUP="your-sg-id"  # REPLACE with your security group ID
SUBNET_ID="your-subnet-id"  # REPLACE with your subnet ID (optional)

# Create minimal IAM role (only for CloudWatch logs, no SSM)
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

cat > role-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:CreateBucket"
      ],
      "Resource": [
        "arn:aws:s3:::redox-balancer-*",
        "arn:aws:s3:::redox-balancer-*/*"
      ]
    }
  ]
}
EOF

# User data script with proper conda setup and optimizations
cat > user_data.sh << 'EOF'
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

# Install AWS CLI v2 for x86_64
cd /tmp
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
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

# Install Miniconda for x86_64
wget https://repo.anaconda.com/miniconda/Miniconda3-py311_24.1.2-0-Linux-x86_64.sh
bash Miniconda3-py311_24.1.2-0-Linux-x86_64.sh -b -p /home/redox/miniconda3
rm Miniconda3-py311_24.1.2-0-Linux-x86_64.sh

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

# Install HiGHS (should work on x86_64)
pip install highspy==1.5.3 || echo "HiGHS installation failed, will use GLPK"

# Configure Ray for large memory system
mkdir -p ~/.ray
cat > ~/.ray/ray_init.yaml << 'RAYEOF'
# Optimized for 1.5TB RAM system
object_store_memory: 500000000000   # 500GB for object store
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
EOF

echo "=== AWS CLI Commands ==="
echo
echo "1. Create IAM role (if not exists):"
echo "aws iam create-role --role-name RedoxEC2Role --assume-role-policy-document file://trust-policy.json"
echo "aws iam put-role-policy --role-name RedoxEC2Role --policy-name RedoxEC2Policy --policy-document file://role-policy.json"
echo "aws iam create-instance-profile --instance-profile-name RedoxEC2Profile"
echo "aws iam add-role-to-instance-profile --instance-profile-name RedoxEC2Profile --role-name RedoxEC2Role"
echo
echo "2. Launch instance:"
echo "aws ec2 run-instances \\"
echo "  --instance-type $INSTANCE_TYPE \\"
echo "  --image-id $AMI_ID \\"
echo "  --key-name $KEY_NAME \\"
echo "  --security-group-ids $SECURITY_GROUP \\"
echo "  --subnet-id $SUBNET_ID \\"
echo "  --iam-instance-profile Name=RedoxEC2Profile \\"
echo "  --user-data file://user_data.sh \\"
echo "  --block-device-mappings '[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":200,\"VolumeType\":\"gp3\",\"Iops\":10000}}]' \\"
echo "  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=redox-x8g-experiment},{Key=Project,Value=redox-balancer},{Key=AutoTerminate,Value=12h}]' \\"
echo "  --instance-initiated-shutdown-behavior terminate \\"
echo "  --count 1"
echo
echo "3. IMPORTANT Security Reminders:"
echo "   - Use SSH key authentication only (no passwords)"
echo "   - Security group should only allow SSH from your IP"
echo "   - Do NOT enable SSM Session Manager"
echo "   - Set instance to terminate on shutdown"
echo
echo "4. Cost Control:"
echo "   - Instance auto-terminates on shutdown"
echo "   - Set 'sudo shutdown -h +720' for 12-hour limit"
echo "   - Monitor with: aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-01-02 --granularity DAILY --metrics UsageQuantity --group-by Type=DIMENSION,Key=SERVICE"