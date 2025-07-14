#!/bin/bash
# Download files needed for model evaluation

set -e

BUCKET_NAME="redox-balancer"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Downloading files for evaluation ==="

# Create directories if needed
mkdir -p "${PROJECT_ROOT}/data/models"
mkdir -p "${PROJECT_ROOT}/checkpoints"

# Download the core model for evaluation
echo "Downloading redox_core_v2.json..."
aws s3 cp "s3://${BUCKET_NAME}/models/redox_core_v2.json" \
    "${PROJECT_ROOT}/data/models/redox_core_v2.json"

# Download the final checkpoint from AWS training
echo "Downloading final checkpoint..."
FINAL_CHECKPOINT="experiments/redox_120actors_sink_flux_20250713_020105/final"
mkdir -p "${PROJECT_ROOT}/${FINAL_CHECKPOINT}"
aws s3 sync "s3://${BUCKET_NAME}/${FINAL_CHECKPOINT}/" \
    "${PROJECT_ROOT}/${FINAL_CHECKPOINT}/" \
    --exclude "*.log"

# Download enzyme library
echo "Downloading enzyme library..."
aws s3 cp "s3://${BUCKET_NAME}/data/enzyme_library_redox.json" \
    "${PROJECT_ROOT}/data/enzyme_library_redox.json"

# Download test models for comparison
echo "Downloading test models..."
aws s3 cp "s3://${BUCKET_NAME}/models/smoke_test_model.json" \
    "${PROJECT_ROOT}/data/models/smoke_test_model.json"

echo
echo "=== Download complete ==="
echo "Files ready for evaluation in:"
echo "  - Model: data/models/redox_core_v2.json"
echo "  - Checkpoint: ${FINAL_CHECKPOINT}/"
echo "  - Enzymes: data/enzyme_library_redox.json"
echo
echo "Run evaluation with:"
echo "  python scripts/eval_agents.py --checkpoint ${FINAL_CHECKPOINT}"