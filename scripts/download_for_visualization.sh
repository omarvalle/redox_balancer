#!/bin/bash
# Download files needed for training visualization and analysis

set -e

BUCKET_NAME="redox-balancer"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Downloading files for visualization ==="

# Create directories
mkdir -p "${PROJECT_ROOT}/data/analysis"
mkdir -p "${PROJECT_ROOT}/logs"

# Download training logs
echo "Downloading training logs..."
aws s3 sync "s3://${BUCKET_NAME}/logs/" "${PROJECT_ROOT}/logs/" \
    --include "*.log" \
    --exclude "*temp*"

# Download experiment metadata and smaller checkpoints for analysis
echo "Downloading experiment metadata..."
EXPERIMENT_DIR="experiments/redox_120actors_sink_flux_20250713_020105"
mkdir -p "${PROJECT_ROOT}/${EXPERIMENT_DIR}"

# Download training state files (small JSON files)
aws s3 sync "s3://${BUCKET_NAME}/${EXPERIMENT_DIR}/" \
    "${PROJECT_ROOT}/${EXPERIMENT_DIR}/" \
    --include "*/training_state.json" \
    --include "*/requirements.txt" \
    --exclude "*.pt.gz"  # Exclude large model files

# Download a few intermediate checkpoints for progress analysis
echo "Downloading sample checkpoints for analysis..."
aws s3 sync "s3://${BUCKET_NAME}/${EXPERIMENT_DIR}/" \
    "${PROJECT_ROOT}/${EXPERIMENT_DIR}/" \
    --include "step_1000000/*" \
    --include "step_5000000/*" \
    --include "step_9000000/*" \
    --include "final/*" \
    --exclude "*.pt.gz"  # Skip the large model weights

echo
echo "=== Download complete ==="
echo "Files ready for visualization:"
echo "  - Training logs: logs/"
echo "  - Experiment data: ${EXPERIMENT_DIR}/"
echo
echo "Generate plots with:"
echo "  python scripts/plot_training_curve.py --experiment-dir ${EXPERIMENT_DIR}"