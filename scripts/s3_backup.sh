#!/bin/bash
# Comprehensive S3 Backup Script for Redox Training
# Handles checkpoints, logs, and experiment data with retry logic

set -e

# Configuration
S3_BUCKET="${S3_BUCKET:-s3://your-bucket-name/redox-experiments}"
MAX_RETRIES=3
RETRY_DELAY=30

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to perform S3 sync with retry
sync_with_retry() {
    local source="$1"
    local dest="$2"
    local attempt=1
    
    while [ $attempt -le $MAX_RETRIES ]; do
        log "Sync attempt $attempt/$MAX_RETRIES: $source -> $dest"
        
        if aws s3 sync "$source" "$dest" \
            --exclude "*.pyc" \
            --exclude "__pycache__/*" \
            --exclude ".ray/*" \
            --exclude "ray_tmp*" \
            --exclude "core.*" \
            --exclude "*.swp" \
            --exclude ".DS_Store" \
            --storage-class INTELLIGENT_TIERING; then
            log "✓ Sync successful"
            return 0
        else
            log "✗ Sync failed"
            if [ $attempt -lt $MAX_RETRIES ]; then
                log "Retrying in ${RETRY_DELAY} seconds..."
                sleep $RETRY_DELAY
            fi
            ((attempt++))
        fi
    done
    
    return 1
}

# Function to backup a single experiment
backup_experiment() {
    local experiment_dir="$1"
    local s3_base="$2"
    
    if [ ! -d "$experiment_dir" ]; then
        log "ERROR: Directory not found: $experiment_dir"
        return 1
    }
    
    local experiment_name=$(basename "$experiment_dir")
    local s3_path="${s3_base}/${experiment_name}"
    
    log "Starting backup: $experiment_name"
    
    # Create metadata file
    local metadata_file="${experiment_dir}/backup_metadata.json"
    cat > "$metadata_file" << EOF
{
    "backup_time": "$(date -Iseconds)",
    "experiment_name": "${experiment_name}",
    "experiment_dir": "${experiment_dir}",
    "hostname": "$(hostname)",
    "instance_ip": "$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo 'unknown')",
    "disk_usage": "$(du -sh ${experiment_dir} 2>/dev/null | cut -f1)",
    "checkpoint_count": $(ls ${experiment_dir}/checkpoints 2>/dev/null | wc -l),
    "last_checkpoint": "$(ls -t ${experiment_dir}/checkpoints 2>/dev/null | head -1 || echo 'none')"
}
EOF
    
    # Backup checkpoints (highest priority)
    if [ -d "${experiment_dir}/checkpoints" ]; then
        log "Backing up checkpoints..."
        if sync_with_retry "${experiment_dir}/checkpoints" "${s3_path}/checkpoints"; then
            log "✓ Checkpoints backed up"
        else
            log "✗ Failed to backup checkpoints"
        fi
    fi
    
    # Backup tensorboard data
    if [ -d "${experiment_dir}/tensorboard" ]; then
        log "Backing up TensorBoard data..."
        sync_with_retry "${experiment_dir}/tensorboard" "${s3_path}/tensorboard" || true
    fi
    
    # Backup logs and config files
    log "Backing up logs and configs..."
    for file in training.log summary.txt config.json system_info.txt backup_metadata.json; do
        if [ -f "${experiment_dir}/${file}" ]; then
            aws s3 cp "${experiment_dir}/${file}" "${s3_path}/" || true
        fi
    done
    
    # Backup compressed system monitor log (if large)
    if [ -f "${experiment_dir}/logs/system_monitor.log" ]; then
        local log_size=$(stat -f%z "${experiment_dir}/logs/system_monitor.log" 2>/dev/null || stat -c%s "${experiment_dir}/logs/system_monitor.log" 2>/dev/null || echo 0)
        if [ "$log_size" -gt 10485760 ]; then  # 10MB
            log "Compressing large system monitor log..."
            gzip -c "${experiment_dir}/logs/system_monitor.log" > "${experiment_dir}/logs/system_monitor.log.gz"
            aws s3 cp "${experiment_dir}/logs/system_monitor.log.gz" "${s3_path}/logs/" || true
            rm -f "${experiment_dir}/logs/system_monitor.log.gz"
        else
            aws s3 cp "${experiment_dir}/logs/system_monitor.log" "${s3_path}/logs/" || true
        fi
    fi
    
    # Create backup completion marker
    echo "$(date -Iseconds)" | aws s3 cp - "${s3_path}/.backup_complete" || true
    
    log "Backup completed: $experiment_name"
}

# Function to backup all experiments
backup_all_experiments() {
    local base_dir="${1:-/home/redox/redox_balancer/experiments}"
    local s3_base="${2:-$S3_BUCKET}"
    
    log "Starting backup of all experiments in $base_dir"
    
    # Find all experiment directories
    for exp_dir in $(find "$base_dir" -maxdepth 1 -type d -name "redox_*" 2>/dev/null | sort); do
        backup_experiment "$exp_dir" "$s3_base"
        echo
    done
}

# Function to backup current active experiment
backup_current() {
    if [ -n "$CURRENT_EXPERIMENT_DIR" ] && [ -d "$CURRENT_EXPERIMENT_DIR" ]; then
        backup_experiment "$CURRENT_EXPERIMENT_DIR" "$S3_BUCKET"
    else
        log "No current experiment directory set"
        return 1
    fi
}

# Main logic
main() {
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}ERROR: AWS CLI not installed${NC}"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}ERROR: AWS credentials not configured${NC}"
        exit 1
    fi
    
    # Parse arguments
    case "${1:-current}" in
        "all")
            backup_all_experiments "${2:-/home/redox/redox_balancer/experiments}" "${3:-$S3_BUCKET}"
            ;;
        "current")
            backup_current
            ;;
        *)
            if [ -d "$1" ]; then
                backup_experiment "$1" "${2:-$S3_BUCKET}"
            else
                echo "Usage: $0 [all|current|<experiment_dir>] [s3_bucket]"
                echo "  all     - Backup all experiments"
                echo "  current - Backup current experiment (from CURRENT_EXPERIMENT_DIR)"
                echo "  <dir>   - Backup specific experiment directory"
                exit 1
            fi
            ;;
    esac
}

# Run main function
main "$@"