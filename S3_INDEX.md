# S3 Storage Index for Redox Balancer

This project uses S3 bucket `s3://redox-balancer` to store large files.

## Directory Structure

```
s3://redox-balancer/
├── models/                          # Model files
│   ├── Recon3D_full.json          # 7.5MB - Full human metabolic model
│   ├── redox_core_v1.json          # 6.9MB - Core model v1 (10k reactions)
│   ├── redox_core_v2.json          # 530KB - Core model v2 (optimized)
│   ├── smoke_test_model.json       # 4KB - Small test model
│   ├── test_full_model.json        # 3KB - Unit test model
│   └── *.metadata.json             # Model metadata files
├── experiments/                     # Training experiments
│   └── redox_120actors_sink_flux_20250713_020105/
│       ├── final/                  # Final trained model (6MB)
│       │   ├── tumor_agent.pt.gz   # Tumor agent weights
│       │   ├── sink_designer_agent.pt.gz # Sink designer weights
│       │   └── training_state.json # Training metadata
│       ├── step_1000000/           # Intermediate checkpoints
│       ├── step_5000000/
│       └── step_9000000/
├── data/                           # Supporting data
│   └── enzyme_library_redox.json   # Enzyme library for RL actions
└── logs/                           # Training logs
    └── training_memfix_v2.log      # Complete training log (10M steps)
```

## Download Scripts

Use these scripts to download only what you need:

### For Model Evaluation
```bash
./scripts/download_for_evaluation.sh
```
Downloads:
- Final checkpoint (~6MB)
- Core model v2 (530KB)
- Enzyme library

### For Training Visualization
```bash
./scripts/download_for_visualization.sh
```
Downloads:
- Training logs
- Checkpoint metadata (no weights)
- Sample checkpoints for progress analysis

### For Continued Training
```bash
./scripts/download_for_training.sh [--checkpoint step_X] [--full-model]
```
Downloads:
- Models needed for training
- Specific checkpoint (optional)
- Full Recon3D model (optional, 7.5MB)

## Setup

1. **First time setup**: Run `./scripts/s3_setup.sh` to create bucket and upload files
2. **Sync from AWS**: Run `./scripts/sync_from_aws.sh` to upload AWS training results
3. **Download for analysis**: Use the appropriate download script

## Cost Optimization

- S3 Standard storage: ~$0.023/GB/month
- Total project size: ~20MB for core files, ~50MB with all checkpoints
- Monthly cost: ~$1-2 for complete project storage

## Benefits

- **Local storage**: Keep only essential files (<5MB)
- **Collaboration**: Easy sharing via S3 URLs
- **Version control**: Git repo stays lightweight
- **Flexibility**: Download different file sets for different tasks