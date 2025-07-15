# Path to Licensing – Redox-Balancing Enzyme-Sink Platform

*Last updated: 2025-07-13*

---

## 0. Executive Snapshot

| Phase | Goal | Typical Duration | Estimated Cost (USD) |
|-------|------|------------------|----------------------|
| 1. Hardening in-silico package | Reproducible code, CI, public dataset | 1–2 mo | $15 k–$30 k |
| 2. Wet-lab PoC (in vitro) | Demonstrate NAD⁺/NADH shift in cell-free lysate | 2–3 mo | $60 k–$90 k |
| 3. Cellular validation | Show redox correction & growth impact in HEK293 / tumor lines | 4 mo | $120 k–$200 k |
| 4. IP consolidation | Convert provisional → non-prov.; freedom-to-operate | parallel | $35 k–$55 k |
| 5. Data Room & Diligence | GLP repeat, QA, formal reports | 2 mo | $40 k–$70 k |
| **TOTAL (18 mo)** | Ready-to-license asset | **~$270 k–$445 k** |

> Costs assume US CRO rates; EU/Asia can be ~20 % lower.

---

## 1. Code Hardening & Reproducibility  (Month 0–2)

1. **Repository cleanup & documentation**  
   * Action: Convert current training repo into a cookie-cut project with Conda env, Dockerfile, pytest.  
   * Cost: 1 FTE software eng (contract) × 6 weeks ≈ **$18 k**.
2. **Continuous Integration / GPU farm replication**  
   * GitHub Actions + AWS Spot tests; produce fixed SHA artifacts.  
   * Cost: infra $500 + labour included above.
3. **Public benchmark dataset**  
   * Strip proprietary Recon3D bits; host sanitized core model on Zenodo.  
   * Legal review $2 k.

Deliverable → *v1.0 open-science package* referenced in all future studies.

---

## 2. Wet-Lab Proof-of-Concept (In Vitro)  (Month 2–5)

1. **Gene synthesis & cloning**  
   * 6 constructs × 3 compartments × 4 copies = 72 variants  
   * GeneArt @ ~$0.18/bp ⇒ ≈ $12 k.
2. **Protein expression + purification**  
   * E. coli BL21 shake-flasks, Ni-NTA.  
   * CRO quote: $500/construct ⇒ ~$36 k.
3. **Enzymatic activity & redox assay**  
   * NADH oxidase kit, plate-reader time.  
   * Reagents $4k; CRO labour $8k.

Milestone: ≥30 % NAD⁺ regeneration vs. control in lysate.

---

## 3. Cellular Validation (Mammalian)  (Month 5–9)

1. **Lentiviral vectors & transduction** — $25 k.
2. **Stable cell-line generation (HEK293, A549)** — $30 k.
3. **Redox/ROS assays (LC-MS, Seahorse XF)** — $45 k.
4. **Proliferation & hypoxia marker panel** — $20 k.

Success Criteria:  
* >25 % decrease in NADH/NAD⁺ ratio.  
* Maintained growth rate ±10 %.  
* Down-regulation of HIF1α (p < 0.05).

---

## 4. IP Consolidation & FTO  (parallel)

* **Non-provisional filing** (US + PCT) – $22 k fees + $8 k attorney.  
* **Freedom-to-Operate search** – $5–10 k.  
* Optionally file **method-of-use** continuations before licensing.

---

## 5. GLP Repeat & Data-Room Prep  (Month 10–12)

* Repeat key cell assays in GLP lab – $25 k.  
* Compile *Investigator’s Brochure*-style PDF inc. memray data – $5 k.  
* Quality audit + raw-data package – $10 k.  
* Finance/market model slide-deck – $5 k.

---

## 6. Outreach & Deal Timeline  (Month 12–18)

| Step | Duration | Notes |
|------|----------|-------|
| Soft-circle 8–10 BD contacts | 1 mo | Use existing VC/pharma network. |
| Confidential pitch + CDA | 1 mo | Provide code repo + wet-lab binder. |
| Option-to-license term-sheet | 1 mo | Target up-front $250–500 k. |
| Technical diligence | 2 mo | They replicate assays (we support). |
| Closing | 1 month | License or asset-purchase. |

---

## Risk & Mitigation

* **Assay fails to translate** → run backup with yeast or in-vivo mouse xenograft (adds $90 k, 4 mo).  
* **Memory patch regresses** → maintain CI; freeze docker image.  
* **Competing patents** → file continuation with narrower enzyme list.

---

## Key Contacts

* **Project lead / PI**  – Omar Valle  
* **Wet-lab CRO shortlist**  – Genscript (US), Twist Bioscience (US), Genewiz (CN/EU).  
* **Patent counsel**  – Wilson Sonsini (Boston)

---

> With ~18 months and ≲$450 k cash burn, the project becomes a “data-room-ready” asset that can be licensed to mid-cap biotech or partnered for Series-A financing. 