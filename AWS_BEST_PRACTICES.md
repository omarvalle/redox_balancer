# AWS Best Practices for Redox Balancer Training

## Security Best Practices

### 1. SSH Access Only
- **NO SSM Session Manager** - Only use SSH with key authentication
- Security group should only allow SSH (port 22) from your specific IP
- Never enable password authentication

### 2. IAM Minimal Permissions
```json
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
    }
  ]
}
```

### 3. Instance Termination Safety
- Set `--instance-initiated-shutdown-behavior terminate`
- Use `sudo shutdown -h +720` for 12-hour auto-termination
- Tag instances with AutoTerminate time

## Technical Best Practices

### 1. Use Ubuntu 22.04 LTS
- More stable than Amazon Linux for scientific computing
- Better package availability for ARM64
- Consistent Python environment

### 2. Python Environment
- Use Python 3.11 (not 3.13) for stability with Ray
- Pin all package versions in requirements
- Use conda for environment isolation

### 3. Ray Configuration for Large Memory
```yaml
# ~/.ray/ray_init.yaml
object_store_memory: 1000000000000  # 1TB for object store
redis_max_memory: 10000000000       # 10GB for Redis
num_heartbeats_timeout: 300         # 5 min timeout
```

### 4. System Optimizations
```bash
# Disable swap (plenty of RAM)
sudo swapoff -a

# Increase file descriptors
echo "* soft nofile 1048576" | sudo tee -a /etc/security/limits.conf

# Enable huge pages
echo 50000 | sudo tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages

# Optimize kernel for Ray
echo "net.core.somaxconn = 1024" | sudo tee -a /etc/sysctl.conf
```

## Cost Management

### 1. Instance Selection
- x8g.48xlarge: $18.14/hour (on-demand)
- Consider Spot instances for 70% savings
- Use smallest instance that meets needs

### 2. Auto-termination
```bash
# Always set termination timer
sudo shutdown -h +720  # 12 hours

# Monitor costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -d "yesterday" +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

### 3. Data Management
- Sync checkpoints to S3 periodically
- Use lifecycle policies for old data
- Download results before termination

## Monitoring Best Practices

### 1. Use tmux for Resilience
```bash
# Always run training in tmux
tmux new-session -d -s training
tmux send-keys -t training "python train.py" C-m
```

### 2. Comprehensive Logging
- System metrics every 5 minutes
- Training progress every minute
- Separate logs for debugging

### 3. Progress Tracking
```bash
# Track completion percentage
tail -f progress.csv | awk -F, '{print $3 "% complete"}'
```

## Common Gotchas to Avoid

### 1. Memory Issues
- Each actor uses ~5-15GB with large models
- Monitor with `free -h` and `ray memory`
- Set `RAY_memory_monitor_refresh_ms=0` to disable OOM killer

### 2. Wrong Biomass Objective
- Recon3D defaults to BIOMASS_maintenance (ATP only)
- Must set to BIOMASS_reaction for growth
- Verify with `model.objective`

### 3. Missing Dependencies
- Recon3D requires lipoproteins (HDL, LDL, IDL)
- Check all exchange reactions are present
- Use HUMAN_MINIMAL_MEDIUM not DEFAULT_MEDIUM

### 4. Reaction ID Mismatches
- Recon3D uses different IDs than textbooks
- Example: AKGDH → AKGDm (mitochondrial)
- Always search for correct IDs

### 5. Model Feasibility
- Use fastcc to ensure consistent reaction set
- Don't rely on flux-based pruning alone
- Verify growth before training

## Workflow Summary

1. **Launch**: Use provided scripts with proper AMI and user data
2. **Sync**: Transfer code via rsync over SSH
3. **Test**: Run 200k timestep experiment first
4. **Monitor**: Check memory < 40% before scaling
5. **Scale**: Increase actors based on test results
6. **Production**: Run with auto-termination and monitoring
7. **Download**: Get results before instance terminates

## Emergency Commands

```bash
# Kill runaway processes
pkill -f ray
pkill -f python

# Emergency shutdown
sudo shutdown -h now

# Check what's using memory
ps aux --sort=-%mem | head -20

# Free memory
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
```