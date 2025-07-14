#!/bin/bash
# Download files needed to continue or restart training

set -e

BUCKET_NAME="redox-balancer"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Downloading files for training ==="

# Parse command line arguments
CHECKPOINT=""
FULL_MODEL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --checkpoint)
            CHECKPOINT="$2"
            shift 2
            ;;
        --full-model)
            FULL_MODEL=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--checkpoint STEP] [--full-model]"
            echo "  --checkpoint STEP  Download specific checkpoint (e.g., step_9000000)"
            echo "  --full-model       Download the full Recon3D model (7.5MB)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create directories
mkdir -p "${PROJECT_ROOT}/data/models"

# Download core model
echo "Downloading core model..."
aws s3 cp "s3://${BUCKET_NAME}/models/redox_core_v2.json" \
    "${PROJECT_ROOT}/data/models/redox_core_v2.json"

# Download full model if requested
if [ "$FULL_MODEL" = true ]; then
    echo "Downloading full Recon3D model..."
    aws s3 cp "s3://${BUCKET_NAME}/models/Recon3D_full.json" \
        "${PROJECT_ROOT}/data/models/Recon3D_full.json"
    aws s3 cp "s3://${BUCKET_NAME}/models/redox_core_v1.json" \
        "${PROJECT_ROOT}/data/models/redox_core_v1.json"
fi

# Download enzyme library
echo "Downloading enzyme library..."
aws s3 cp "s3://${BUCKET_NAME}/data/enzyme_library_redox.json" \
    "${PROJECT_ROOT}/data/enzyme_library_redox.json"

# Download checkpoint if specified
if [ -n "$CHECKPOINT" ]; then
    echo "Downloading checkpoint: $CHECKPOINT"
    CHECKPOINT_PATH="experiments/redox_120actors_sink_flux_20250713_020105/$CHECKPOINT"
    mkdir -p "${PROJECT_ROOT}/${CHECKPOINT_PATH}"
    aws s3 sync "s3://${BUCKET_NAME}/${CHECKPOINT_PATH}/" \
        "${PROJECT_ROOT}/${CHECKPOINT_PATH}/"
else
    # Download the final checkpoint by default
    echo "Downloading final checkpoint..."
    FINAL_CHECKPOINT="experiments/redox_120actors_sink_flux_20250713_020105/final"
    mkdir -p "${PROJECT_ROOT}/${FINAL_CHECKPOINT}"
    aws s3 sync "s3://${BUCKET_NAME}/${FINAL_CHECKPOINT}/" \
        "${PROJECT_ROOT}/${FINAL_CHECKPOINT}/"
fi

echo
echo "=== Download complete ==="
echo "Files ready for training:"
echo "  - Core model: data/models/redox_core_v2.json"
if [ "$FULL_MODEL" = true ]; then
    echo "  - Full model: data/models/Recon3D_full.json"
fi
echo "  - Enzymes: data/enzyme_library_redox.json"
echo "  - Checkpoint: Available for resume"
echo
echo "Start training with:"
echo "  python scripts/train_impala.py --model data/models/redox_core_v2.json --resume [checkpoint-path]"