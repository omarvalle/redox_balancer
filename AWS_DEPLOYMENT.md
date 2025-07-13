# AWS x8g.48xlarge Deployment Guide

## Quick Start

### 1. Launch Instance

Edit `scripts/aws_setup.sh` with your AWS credentials, then:

```bash
# Set your AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1

# Launch instance (replace placeholders in aws_setup.sh first)
cd scripts
./aws_setup.sh
```

### 2. Get Instance Details

```bash
# Get instance ID from launch output, then:
aws ec2 describe-instances --instance-ids i-xxxxx | grep PublicIpAddress
```

### 3. Sync Project

```bash
# Edit sync_to_aws.sh with instance IP
vim scripts/sync_to_aws.sh  # Set INSTANCE_IP and KEY_PATH

# Run sync
./scripts/sync_to_aws.sh
```

### 4. SSH and Run Experiment

```bash
# SSH to instance
ssh -i ~/.ssh/your-key.pem ec2-user@<INSTANCE_IP>

# Navigate to project
cd redox_balancer

# Make scripts executable
chmod +x scripts/*.sh

# Run initial experiment (30 actors, 200k timesteps)
./scripts/run_aws_experiment.sh
```

## Cost Management

- **x8g.48xlarge**: $18.14/hour
- **Initial test** (200k steps): ~1 hour = $18
- **Production run** (5M steps): ~10 hours = $180

### Cost-Saving Tips

1. **Use Spot Instances** (70% cheaper):
   ```bash
   aws ec2 request-spot-instances \
     --instance-count 1 \
     --type "one-time" \
     --launch-specification file://spot-spec.json
   ```

2. **Set up auto-termination**:
   ```bash
   # On the instance, set auto-shutdown after 12 hours
   sudo shutdown -h +720
   ```

3. **Monitor usage**:
   ```bash
   # Check running instances
   aws ec2 describe-instances --filters "Name=instance-type,Values=x8g.48xlarge" "Name=instance-state-name,Values=running"
   ```

## Monitoring During Run

```bash
# Memory usage
watch -n 60 free -h

# Ray memory
ray memory

# Training progress
tail -f experiments/*/training.log

# System stats
htop
```

## Scaling Guide

Based on memory usage after initial test:

- **< 30% RAM used**: Scale to 60 actors
- **< 50% RAM used**: Scale to 90 actors
- **< 70% RAM used**: Scale to 120 actors (optimal)
- **> 80% RAM used**: Keep current actor count

## Production Checklist

- [ ] Initial test successful (200k steps)
- [ ] Memory usage < 70% with target actors
- [ ] FPS > 100 (indicates good performance)
- [ ] Checkpoints saving correctly
- [ ] Budget approved for full run
- [ ] Auto-termination configured

## Cleanup

```bash
# Download results
scp -i ~/.ssh/your-key.pem -r ec2-user@<IP>:/home/ec2-user/redox_balancer/experiments ./aws_results/

# Terminate instance
aws ec2 terminate-instances --instance-ids i-xxxxx

# Verify termination
aws ec2 describe-instances --instance-ids i-xxxxx | grep State
```

## Troubleshooting

### OOM Issues
- Reduce `--num-actors`
- Check for memory leaks: `ps aux | sort -k 6 -r | head -20`

### Slow Performance
- Ensure instance type is correct: `ec2-metadata --instance-type`
- Check CPU throttling: `top` (should see near 100% CPU usage)

### Network Issues
- Use `tmux` or `screen` for resilient sessions
- Set up regular checkpoint syncing to S3

## Alternative: Smaller Core Model

If AWS costs are prohibitive, create a 2k-reaction core:

```bash
# On local machine
python scripts/build_redox_core.py \
  --input data/models/Recon3D_full.json \
  --output data/models/redox_core_2k.json \
  --reactions 2000
```

This smaller model should work on your 31GB local system with 4-6 actors.