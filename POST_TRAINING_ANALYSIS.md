# Post-Training Analysis Guide

## 🎯 Quick Start: What Do You Want to Do?

### A. **Evaluate Model Performance**
```bash
./scripts/download_for_evaluation.sh
python scripts/eval_agents.py --checkpoint experiments/redox_120actors_sink_flux_20250713_020105/final
```

### B. **Visualize Training Progress**  
```bash
./scripts/download_for_visualization.sh
tensorboard --logdir experiments/redox_120actors_sink_flux_20250713_020105/tensorboard
# Open http://localhost:6006
```

### C. **Continue Training**
```bash
./scripts/download_for_training.sh --checkpoint step_9000000
python scripts/train_impala.py --resume experiments/redox_120actors_sink_flux_20250713_020105/step_9000000 --timesteps 15000000
```

---

## 📊 Detailed Analysis Workflows

### 1. Training Curve Analysis

**Download logs and metadata:**
```bash
./scripts/download_for_visualization.sh
```

**View in TensorBoard:**
```bash
tensorboard --logdir experiments/redox_120actors_sink_flux_20250713_020105/tensorboard
open http://localhost:6006
```

**Generate static plots:**
```bash
python scripts/plot_training_curve.py \
    --experiment-dir experiments/redox_120actors_sink_flux_20250713_020105 \
    --output plots/training_progress.png
```

### 2. Model Evaluation & Testing

**Download final checkpoint:**
```bash
./scripts/download_for_evaluation.sh
```

**Run comprehensive evaluation:**
```bash
# Test on multiple scenarios
python scripts/eval_agents.py \
    --checkpoint experiments/redox_120actors_sink_flux_20250713_020105/final \
    --model data/models/redox_core_v2.json \
    --num-episodes 100 \
    --save-results evaluation_results.json

# Quick smoke test
python scripts/eval_agents.py \
    --checkpoint experiments/redox_120actors_sink_flux_20250713_020105/final \
    --model data/models/smoke_test_model.json \
    --num-episodes 10
```

**Compare against baselines:**
```bash
# Evaluate untrained baseline
python scripts/eval_agents.py \
    --model data/models/redox_core_v2.json \
    --num-episodes 100 \
    --save-results baseline_results.json

# Compare results
python scripts/compare_evaluations.py \
    --trained evaluation_results.json \
    --baseline baseline_results.json
```

### 3. Memory Leak Analysis (Retrospective)

**Download complete training logs:**
```bash
aws s3 cp s3://redox-balancer/logs/training_memfix_v2.log ./
```

**Analyze memory patterns:**
```bash
# Extract memory usage over time
grep "Memory:" training_memfix_v2.log > memory_analysis.txt

# Plot memory usage
python scripts/plot_memory_usage.py \
    --log training_memfix_v2.log \
    --output plots/memory_usage.png
```

### 4. Checkpoint Comparison

**Download multiple checkpoints:**
```bash
./scripts/download_for_training.sh --checkpoint step_1000000
./scripts/download_for_training.sh --checkpoint step_5000000
./scripts/download_for_training.sh --checkpoint step_9000000
```

**Compare performance across training:**
```bash
python scripts/compare_checkpoints.py \
    --checkpoints experiments/redox_120actors_sink_flux_20250713_020105/step_*/  \
    --model data/models/redox_core_v2.json \
    --output checkpoint_comparison.json
```

---

## 🔬 Advanced Analysis

### 5. Model Interpretation

**Analyze learned enzyme strategies:**
```bash
python scripts/analyze_enzyme_usage.py \
    --checkpoint experiments/redox_120actors_sink_flux_20250713_020105/final \
    --output enzyme_analysis.json
```

**Visualize metabolic flux patterns:**
```bash
python scripts/visualize_flux_patterns.py \
    --checkpoint experiments/redox_120actors_sink_flux_20250713_020105/final \
    --model data/models/redox_core_v2.json \
    --output flux_visualization.html
```

### 6. Reward Signal Analysis

**Extract reward progression:**
```bash
# From TensorBoard logs
python scripts/extract_rewards.py \
    --tensorboard-dir experiments/redox_120actors_sink_flux_20250713_020105/tensorboard \
    --output rewards_timeseries.csv

# Plot reward components
python scripts/plot_reward_breakdown.py \
    --data rewards_timeseries.csv \
    --output plots/reward_analysis.png
```

### 7. Robustness Testing

**Test on perturbed models:**
```bash
# Download full model for perturbation testing
./scripts/download_for_training.sh --full-model

# Test robustness
python scripts/test_robustness.py \
    --checkpoint experiments/redox_120actors_sink_flux_20250713_020105/final \
    --base-model data/models/Recon3D_full.json \
    --perturbations knockout,flux_bounds,objective \
    --output robustness_results.json
```

---

## 📈 Key Metrics to Track

Based on our training results, focus on these metrics:

### Training Progress Metrics
- **Returns**: Should be 4,000-4,500 (achieved ✅)
- **FPS**: Should be >400 after memory fixes (achieved: ~500 ✅)
- **Memory per actor**: Should be <2GB (achieved: 1.08GB ✅)

### Model Performance Metrics
- **NADH sink flux**: Target >0.1 mmol/gDW/h
- **Growth rate**: Should maintain >95% of baseline
- **Redox balance**: NAD+/NADH ratio improvement

### Memory Efficiency Metrics
- **Model copy reduction**: From 45GB to minimal
- **Cache hit rate**: Should be >80% after warmup
- **GC frequency**: Monitor garbage collection overhead

---

## 🎯 Success Criteria Checklist

- [ ] Training completed 10M steps without crashes
- [ ] Final returns >4,000 (target achieved: 4,500)
- [ ] Memory usage stable throughout training
- [ ] Model generalizes to unseen metabolic conditions
- [ ] Enzyme strategies are biologically plausible
- [ ] Performance superior to random/heuristic baselines

---

## 🔧 Troubleshooting

### Common Issues
1. **Download fails**: Check AWS credentials with `aws sts get-caller-identity`
2. **Missing files**: Verify S3 bucket contents with `aws s3 ls s3://redox-balancer/`
3. **Evaluation crashes**: Ensure model compatibility with checkpoint
4. **TensorBoard empty**: Check tensorboard directory path

### Quick Fixes
```bash
# Re-sync AWS credentials
aws configure

# Verify S3 contents
aws s3 ls --recursive s3://redox-balancer/ | grep final

# Test model loading
python -c "import torch; print(torch.load('experiments/*/final/tumor_agent.pt.gz'))"
```

---

## 📚 Next Steps

1. **Immediate**: Run evaluation to verify model performance
2. **Short-term**: Generate publication-quality plots and analysis
3. **Medium-term**: Test on different metabolic models (iJO1366, iML1515)
4. **Long-term**: Wet-lab validation of predicted enzyme strategies

Use this guide to systematically analyze your trained model and extract maximum value from the 10M step training run!