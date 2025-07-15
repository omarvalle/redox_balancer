# Expression Troubleshooting Guide

## FAQ Quick Reference

### Q1: No protein band on SDS-PAGE after induction?

**A**: Check these in order:
1. Verify IPTG is fresh (<6 months) and correct concentration
2. Confirm BL21(DE3) strain (not regular BL21)
3. Sequence plasmid to ensure insert is in-frame
4. Try higher IPTG (1 mM) or longer induction (overnight)

### Q2: Protein is in pellet (inclusion bodies)?

**A**: For soluble expression:
- Drop temperature to 16-18°C before induction
- Use only 0.1 mM IPTG
- Harvest at 4-6 hours (not overnight)
- Co-express with GroEL/ES chaperones

### Q3: Multiple bands or degradation?

**A**: Prevent proteolysis:
- Add protease inhibitor cocktail immediately
- Work on ice, process quickly
- Use BL21(DE3)pLysS for tighter control
- Include 1 mM PMSF in lysis buffer

### Q4: Cells stop growing after induction?

**A**: Reduce metabolic burden:
- Lower IPTG to 0.05 mM
- Induce at higher OD (1.0-1.2)
- Use richer media (TB instead of LB)
- Check for plasmid loss (plate on antibiotic)

### Q5: Low yield in yeast?

**A**: Optimize galactose induction:
- Ensure complete raffinose depletion first
- Use 2% galactose (not glucose contaminated)
- Extend induction to 24-48 hours
- Check for proteases (add PMSF)

### Q6: No activity but protein expressed?

**A**: Check cofactors and folding:
- Add 1 mM FAD to culture (for oxidases)
- Include trace metals (Fe, Zn)
- Verify correct compartment targeting
- Test different lysis methods (French press vs sonication)

## Decision Trees

### Low Expression Troubleshooting
```
No band on gel?
├─ Yes → Check basics
│  ├─ Wrong antibiotic? → Use fresh plates
│  ├─ No T7 polymerase? → Use BL21(DE3)
│  └─ Frame shift? → Sequence insert
└─ Faint band → Optimize
   ├─ Increase IPTG (up to 1 mM)
   ├─ Extend time (overnight)
   └─ Richer media (2xYT, TB)
```

### Solubility Optimization
```
Inclusion bodies?
├─ Severe → Change strategy
│  ├─ Switch to yeast
│  ├─ Try SUMO fusion
│  └─ Refolding protocol
└─ Partial → Fine tune
   ├─ 16°C expression
   ├─ 0.05 mM IPTG
   └─ Harvest early (4h)
```

## Emergency Fixes

**Contamination**: Add 0.1% glucose to suppress basal expression

**Foaming**: Add 0.01% antifoam, reduce shaking to 200 rpm

**Phage infection**: Use phage-resistant strain or add citrate

**Plasmid loss**: Increase antibiotic, fresh transform weekly

## Contact for Advanced Issues

If problems persist after trying these solutions:
- Review construct design (rare codons, GC content)
- Consider synthetic gene optimization
- Try alternative expression systems
- Consult protein expression core facility