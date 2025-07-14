#!/bin/bash
# Test the S3 workflow by downloading files for evaluation

set -e

echo "=== Testing S3 Workflow ==="
echo

# Test download for evaluation
echo "1. Testing download for evaluation..."
./scripts/download_for_evaluation.sh

echo
echo "2. Verifying downloaded files..."

# Check if key files exist
if [ -f "data/models/redox_core_v2.json" ]; then
    echo "✅ Core model downloaded"
else
    echo "❌ Core model missing"
fi

if [ -d "experiments/redox_120actors_sink_flux_20250713_020105/final" ]; then
    echo "✅ Final checkpoint downloaded"
    echo "   Files: $(ls experiments/redox_120actors_sink_flux_20250713_020105/final/)"
else
    echo "❌ Final checkpoint missing"
fi

if [ -f "data/enzyme_library_redox.json" ]; then
    echo "✅ Enzyme library downloaded"
else
    echo "❌ Enzyme library missing"
fi

echo
echo "3. File sizes:"
echo "   Core model: $(ls -lh data/models/redox_core_v2.json | awk '{print $5}')"
echo "   Final checkpoint: $(du -sh experiments/redox_120actors_sink_flux_20250713_020105/final/ | awk '{print $1}')"
echo "   Total local size: $(du -sh . | awk '{print $1}')"

echo
echo "=== S3 Workflow Test Complete ==="
echo "Ready to run model evaluation!"