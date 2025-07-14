#!/bin/bash
# Sync trained models and results from AWS to S3

set -e

BUCKET_NAME="redox-balancer"
AWS_HOST="ubuntu@44.193.26.15"
SSH_KEY="~/.ssh/succinate-sink-training-key.pem"

echo "=== Syncing AWS training results to S3 ==="

# First, upload from AWS to S3
echo "Uploading final checkpoint from AWS..."
ssh -i ${SSH_KEY} ${AWS_HOST} "sudo su - redox -c 'cd /home/redox/redox_balancer && aws s3 sync experiments/redox_120actors_sink_flux_20250713_020105/final/ s3://${BUCKET_NAME}/experiments/redox_120actors_sink_flux_20250713_020105/final/ --exclude \"*.log\"'"

echo "Uploading training logs..."
ssh -i ${SSH_KEY} ${AWS_HOST} "sudo su - redox -c 'cd /home/redox && aws s3 cp training_memfix_v2.log s3://${BUCKET_NAME}/logs/training_memfix_v2.log'"

echo "Uploading sample intermediate checkpoints..."
ssh -i ${SSH_KEY} ${AWS_HOST} "sudo su - redox -c 'cd /home/redox/redox_balancer && aws s3 sync experiments/redox_120actors_sink_flux_20250713_020105/ s3://${BUCKET_NAME}/experiments/redox_120actors_sink_flux_20250713_020105/ --exclude \"*.pt.gz\" --include \"step_1000000/*\" --include \"step_5000000/*\" --include \"step_9000000/*\"'"

echo "Uploading models to S3..."
ssh -i ${SSH_KEY} ${AWS_HOST} "sudo su - redox -c 'cd /home/redox/redox_balancer && aws s3 cp data/models/redox_core_v1.json s3://${BUCKET_NAME}/models/redox_core_v1.json'"
ssh -i ${SSH_KEY} ${AWS_HOST} "sudo su - redox -c 'cd /home/redox/redox_balancer && aws s3 cp data/models/Recon3D_full.json s3://${BUCKET_NAME}/models/Recon3D_full.json 2>/dev/null || echo \"Recon3D_full.json not found on AWS\"'"

echo
echo "=== Sync complete ==="
echo "Training results are now available in S3 bucket: ${BUCKET_NAME}"
echo
echo "Download locally with:"
echo "  ./scripts/download_for_evaluation.sh    # For model evaluation"
echo "  ./scripts/download_for_visualization.sh # For plotting training curves"
echo "  ./scripts/download_for_training.sh      # For continued training"