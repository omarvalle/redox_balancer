# AWS Redox Training Deployment Checklist

## Pre-Launch Verification Checklist

### 1. System Setup
- [ ] SSH to instance as `redox` user: `ssh redox@44.193.26.15`
- [ ] Verify ulimits are set correctly:
  ```bash
  ulimit -n  # Should be 1048576
  ulimit -u  # Should be 524288
  ```
- [ ] If not, update `/etc/security/limits.conf` and re-login

### 2. Environment Setup
- [ ] Activate conda environment: `conda activate redox`
- [ ] Set PYTHONPATH: `export PYTHONPATH=/home/redox/redox_balancer/src`
- [ ] Verify all packages installed: `python -c "import ray, torch, cobra, gymnasium"`

### 3. Cleanup Previous Runs
- [ ] Run Ray cleanup: `./scripts/cleanup_ray.sh`
- [ ] Check disk space: `df -h /tmp`
- [ ] Verify no orphaned processes: `ps aux | grep ray`

### 4. Pre-Flight Check
- [ ] Run system check: `./scripts/check_system.sh`
- [ ] Address any warnings or errors shown

### 5. Configure S3 Backup
- [ ] Update S3 bucket in `scripts/start_training_fixed.sh`
- [ ] Configure AWS credentials: `aws configure`
- [ ] Test S3 access: `aws s3 ls`

## Launch Procedure

### 1. Start Training
```bash
cd /home/redox/redox_balancer
./scripts/start_training_fixed.sh
```

### 2. Verify Everything Started
- [ ] Check tmux session: `tmux ls`
- [ ] Verify TensorBoard: `curl http://localhost:6006`
- [ ] Check system monitoring is running
- [ ] Verify S3 backup cron job: `crontab -l`

### 3. Start Training in tmux
```bash
tmux attach -t redox_training
# Run the training command shown or:
./experiments/redox_*/training_command.sh
```

### 4. Monitor Progress
- [ ] Watch training log: `tail -f $CURRENT_EXPERIMENT_DIR/training.log`
- [ ] Monitor system: `./experiments/redox_*/watch_logs.sh`
- [ ] Check TensorBoard: http://44.193.26.15:6006

## During Training

### Regular Checks (Every Hour)
- [ ] Run system check: `./scripts/check_system.sh`
- [ ] Verify S3 backups: `ls -la ~/s3_backup.log`
- [ ] Check memory usage isn't growing unexpectedly
- [ ] Ensure checkpoints are being saved

### If Issues Arise
1. **High Memory Usage**:
   ```bash
   ./scripts/cleanup_ray.sh
   # Then restart training with fewer actors
   ```

2. **Training Stalled**:
   - Check training log for errors
   - Run `ray status` to check cluster health
   - Consider restarting from last checkpoint

3. **TensorBoard Down**:
   ```bash
   ./scripts/manage_tensorboard.sh restart
   ```

## Post-Training

### 1. Final Backup
```bash
./scripts/s3_backup.sh current
```

### 2. Generate Summary
```bash
cd $CURRENT_EXPERIMENT_DIR
tail -1000 training.log | grep -E "(Timesteps:|Return:|FPS:)" > final_metrics.txt
```

### 3. Download Results
From local machine:
```bash
scp -r redox@44.193.26.15:~/redox_balancer/experiments/redox_* ./local_results/
# Or sync from S3
aws s3 sync s3://your-bucket/redox-experiments/redox_* ./local_results/
```

### 4. Cleanup
```bash
cd $CURRENT_EXPERIMENT_DIR
./cleanup.sh
```

### 5. Terminate Instance
- [ ] Ensure all data is backed up
- [ ] Stop the instance or terminate if no longer needed

## Troubleshooting Commands

### Check Ray Status
```bash
ray status
ray memory
```

### Force Stop Everything
```bash
ray stop --force
pkill -f tensorboard
tmux kill-server
```

### Emergency Cleanup
```bash
sudo rm -rf /tmp/ray* /dev/shm/*ray*
sudo ipcs -m | grep $USER | awk '{print $2}' | xargs -I {} sudo ipcrm -m {}
```

### Check What's Using Memory
```bash
ps aux --sort=-%mem | head -20
```

## Important Files and Locations

- **Startup Script**: `/home/redox/redox_balancer/scripts/start_training_fixed.sh`
- **System Check**: `/home/redox/redox_balancer/scripts/check_system.sh`
- **Ray Cleanup**: `/home/redox/redox_balancer/scripts/cleanup_ray.sh`
- **S3 Backup**: `/home/redox/redox_balancer/scripts/s3_backup.sh`
- **TensorBoard Manager**: `/home/redox/redox_balancer/scripts/manage_tensorboard.sh`
- **Experiment Directory**: Set in `$CURRENT_EXPERIMENT_DIR` after running startup script
- **S3 Backup Logs**: `/home/redox/s3_backup.log`

## Best Practices

1. **Always run as `redox` user** - Never run training as root or ubuntu
2. **Use tmux** - Protects against SSH disconnections
3. **Monitor actively** - Check system health every hour during long runs
4. **Backup frequently** - S3 backups run hourly, but manual backup before major changes
5. **Clean between runs** - Always run cleanup scripts before starting new experiments
6. **Document issues** - Keep notes on any problems and solutions for future reference