#!/bin/bash
# S3 setup and upload script for redox_balancer project

set -e

# Configuration
BUCKET_NAME="redox-balancer"
REGION="us-east-1"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== S3 Setup for Redox Balancer ==="
echo "Bucket: s3://${BUCKET_NAME}"
echo "Region: ${REGION}"
echo

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "ERROR: AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "ERROR: AWS credentials not configured. Run 'aws configure' first."
    exit 1
fi

# Create bucket if it doesn't exist
if aws s3 ls "s3://${BUCKET_NAME}" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "Creating bucket: ${BUCKET_NAME}"
    aws s3 mb "s3://${BUCKET_NAME}" --region "${REGION}"
    
    # Enable versioning for safety
    aws s3api put-bucket-versioning \
        --bucket "${BUCKET_NAME}" \
        --versioning-configuration Status=Enabled
else
    echo "Bucket already exists: ${BUCKET_NAME}"
fi

# Function to upload with progress
upload_to_s3() {
    local source="$1"
    local dest="$2"
    echo "Uploading: $source -> s3://${BUCKET_NAME}/${dest}"
    aws s3 cp "$source" "s3://${BUCKET_NAME}/${dest}" --no-progress
}

# Upload large model files
echo
echo "Uploading model files..."
cd "${PROJECT_ROOT}"

# Upload models (if they exist locally)
if [ -f "data/models/Recon3D_full.json" ]; then
    upload_to_s3 "data/models/Recon3D_full.json" "models/Recon3D_full.json"
fi

if [ -f "data/models/redox_core_v1.json" ]; then
    upload_to_s3 "data/models/redox_core_v1.json" "models/redox_core_v1.json"
fi

# Upload smaller models too for completeness
upload_to_s3 "data/models/redox_core_v2.json" "models/redox_core_v2.json"
upload_to_s3 "data/models/smoke_test_model.json" "models/smoke_test_model.json"
upload_to_s3 "data/models/test_full_model.json" "models/test_full_model.json"

# Upload metadata files
for meta in data/models/*.metadata.json; do
    if [ -f "$meta" ]; then
        filename=$(basename "$meta")
        upload_to_s3 "$meta" "models/$filename"
    fi
done

# Upload enzyme library
upload_to_s3 "data/enzyme_library_redox.json" "data/enzyme_library_redox.json"

# Upload experiment results (if any exist)
if [ -d "experiments" ]; then
    echo
    echo "Uploading experiment results..."
    # Use sync for directories to handle nested structure
    aws s3 sync experiments/ "s3://${BUCKET_NAME}/experiments/" \
        --exclude "*.log" \
        --exclude "*.pyc" \
        --exclude "__pycache__/*"
fi

# Upload any training logs
if ls training_*.log 1> /dev/null 2>&1; then
    echo
    echo "Uploading training logs..."
    for log in training_*.log; do
        upload_to_s3 "$log" "logs/$(basename $log)"
    done
fi

# Create a manifest of what's uploaded
echo
echo "Creating manifest..."
aws s3 ls --recursive "s3://${BUCKET_NAME}/" > s3_manifest.txt

echo
echo "=== Upload Complete ==="
echo "Total size in S3:"
aws s3 ls --recursive "s3://${BUCKET_NAME}/" --summarize | grep "Total Size"
echo
echo "Manifest saved to: s3_manifest.txt"
echo
echo "To download files later, use the analysis-specific scripts:"
echo "  - scripts/download_for_evaluation.sh"
echo "  - scripts/download_for_visualization.sh"
echo "  - scripts/download_for_training.sh"