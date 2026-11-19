# Incremental prognostic value of CT perfusion after thrombectomy (ISLES'24): analysis code

Code for the manuscript *"A reproducible framework for evaluating the incremental prognostic value of CT perfusion after
thrombectomy: feasibility study on the public ISLES'24 dataset and design parameters for a definitive study"*.

## Canonical version (2026-11-14)

| Item | File | Built by |
|---|---|---|
| Manuscript | `BMC_FINAL_SUBMISSION_STAGING/Manuscript_BMC_MIDM_FINAL.docx` (PDF preview alongside) | `validity/w09_final_manuscript.py` → `validity/w13_targeted_repair.py` |
| Cover letter | `BMC_FINAL_SUBMISSION_STAGING/Cover_letter_BMC_MIDM_FINAL.docx` | `validity/w12_cover_letter.py` |
| Additional file 5 (Tables S21–S42, Figure S8) | `BMC_FINAL_SUBMISSION_STAGING/Additional_file_5_post_hoc_analyses_and_external_benchmark.xlsx` | `validity/w10_additional_file5.py` |
| Additional files 1–4 | unchanged from the 2026-11-13 audit package | `s12_supplements.py` (historical run) |
| Evidence ledger (54 claims) and audit | `BMC_TARGETED_REPAIR_2026-11-14/` | `validity/w14_repair_documents.py` |
| Delivery ZIPs | `BMC_FINAL_DELIVERY_2026-11-14/` | `validity/w11_final_package.py` |

Canonical results (unchanged by every later pass; `outputs/` is byte-identical to the baseline snapshot):

| Quantity | Value | Source |
|---|---|---|
| Analysed cohort | N = 129, 44 poor outcomes (mRS 3–6) | `outputs/data/cohort_129.csv` |
| Primary clinical GBM AUC (seed mean) | 0.763 | `outputs/oof/oof_long.csv`, model `P1_clin_GBM` |
| Primary late fusion AUC | 0.774 | model `F_late_P1_E` |
| Primary ΔAUC (fusion − clinical) | +0.011 (95% CI −0.039 to +0.068) | `outputs/tables/paired_auc_comparisons*.csv` |
| GBM-only nested tuning, clinical AUC (sensitivity analysis) | 0.727 | `outputs/oof/oof_long_sens_nestedgbm.csv` |
| Fully nested selection (post hoc): clinical / fusion AUC | 0.698 / 0.752 | `outputs_validity/oof/oof_long_vA.csv` |
| Fully nested ΔAUC (post hoc) | +0.054 (95% CI −0.006 to +0.121) | `outputs_validity/tables/vA_paired.csv` |
| ISLES 2018 de-duplicated Dice / sensitivity (technical benchmark) | 0.206 / 0.152 | `outputs_validity/tables/vX1b_isles2018_core_vs_dwi_dedup.csv` |

Outcome coding everywhere: `y = 1` = poor outcome (mRS 3–6); `p_poor` = predicted P(mRS 3–6).

## Data and configurable paths

- ISLES'24 training set: pre-processed release (input of the primary analysis) and original release (native-unit maps,
  NCCT, follow-up DWI, masks; read per subject from the Hugging Face mirror `hugging-science/isles24-stroke` by HTTP range
  requests, `httpfile.py`). Zenodo: doi:10.5281/zenodo.17652035 (CC BY-NC-SA 4.0).
- ISLES 2018 training set (SMIR): unit-recovery simulation (s03) and the post hoc technical benchmark (vX1, vX1b).
- Source data are not redistributed; see `DATA_NOTICE.md`.
- `config.py` uses paths relative to this folder. Environment overrides: `BRANCH3_DATA_ROOT`, `ISLES24_DIR`,
  `ISLES18_DIR`, `BRANCH3_OUT` (canonical outputs). `validity/v_common.py` adds `BRANCH3_VOUT` (post hoc outputs; must not
  point to the canonical folder) and `NATIVE_ISLES24_DIR` (local cache of native-unit maps).

## Environment

Python 3.10.11; direct dependencies with the versions used are pinned in `requirements.txt` (includes `requests` for
`httpfile.py` and `joblib` for the fitted models).

## Workflow

### Stage 1: primary analysis, scripts `s01`–`s30` (canonical; writes `outputs/`)

Re-running these scripts overwrites the canonical outputs and is only needed to reproduce the primary analysis from the
images. Check integrity afterwards with `validity/qa_code_checks.py` (SHA256 comparison with the baseline snapshot).

| Step | Script(s) | Purpose |
|---|---|---|
| 1 | s01 | cohort 149 → 129, clinical variables in physical units, probable release-level imputation |
| 2 | s02 | recovery of CTP physical units, quality checks, 53 perfusion features (needs images) |
| 3 | s03 | ISLES 2018 simulation of the pre-processing (needs images) |
| 4 | s04 `primary` | nested repeated cross-validation (5 seeds × 10-fold, inner 5-fold), out-of-fold predictions |
| 5 | s05 | AUC with bootstrap CI, paired ΔAUC, DeLong, calibration, decision curves, reclassification |
| 6 | s06 `features missing tmaxcertain 5fold scalefree nestedgbm` | sensitivity analyses |
| 7 | s07, s08, s10 | interpretation, Table 1 and Riley sample size, ordinal analyses |
| 8 | s13, s15 | native-unit maps from the original release; agreement, absolute volumes (needs images) |
| 9 | s19 | centre inference from data provenance (needs native maps) |
| 10 | s14 `ref`, s14 `native`, s16, s05 `_all` | reference / recalibrated / native-unit / volume models; combined evaluation |
| 11 | s17, s18 | precision and equivalence; exploratory subgroups |
| 12 | s21 `munich_cv`, s05 `_munich`, s21, s20 | centre-aware analyses |
| 13 | s23–s27 | supplementary analysis plan (H1–H3; s23 and s25 need DWI), Holm adjustment |
| 14 | s28 | design parameters: sample size by target ΔAUC, Riley minimum n, go/no-go table |
| 15 | s09, s22, s29 | figures |

### Stage 2: post hoc analyses, `validity/v*.py` (write only `outputs_validity/`)

| Label in audit documents | Script | Content |
|---|---|---|
| A | `vA_nested_consistent.py`, `vA_within_centre.py` | consistent fully nested learner selection (0.698 / 0.752 / +0.054) |
| B | `vB_native_verification.py` | recovered vs native Tmax on an approximate common grid (needs native maps) |
| C | `vC_provenance.py`, `vC2_centre_reconciliation.py` | provenance table, centre-assignment sensitivity, published centre counts, case-level signatures |
| D | `vD_fetch_ncct.py`, `vD_registration.py`, `vD_models.py` | admission-CT atlas registration (needs NCCT) |
| E | `vE_bootstrap_refit.py` | exploratory bootstrap-refit (B = 100) |
| ISLES 2018 | `vX1_isles2018_benchmark.py`, `vX1b_isles2018_slab_overlap.py` | technical component benchmark; image-based slab de-duplication (needs ISLES 2018 images) |
| — | `vX3_jhu_brain_extraction.py` | prepared but not executed (data not obtainable) |

### Stage 3: submission build (current), `validity/w*.py`

Run in this order: `w01_compatibility_matrix` → `w02_collect` → `w07_figures_clean` → `w08_freeze_models` →
`w10_additional_file5` → `w09_final_manuscript` (writes `_build/…before_repair.docx`) → `w13_targeted_repair` (final
manuscript) → Word PDF export → `w12_cover_letter` → `w14_repair_documents` (ledger, audit, report) →
`w11_final_package` (ZIPs). `qa_code_checks.py` runs the code and reproducibility checks.

### Historical scripts (do not use to rebuild the submission package)

`s11_manuscript.py`, `s11_manuscript_v3_full.py`, `s12_supplements.py` (Additional files 1–4 were built by its earlier run
and are used unchanged), `s30_package.py`, `validity/w03_manuscript.py` (built the validity-revised manuscript, the frozen
input of w09), `validity/w04_claims_and_log.py` (built the base ledger, the frozen input of w14), `validity/w05_number_check.py`
and `validity/w06_package.py`. Except `s12` and `w05`, they stop unless `BRANCH3_ALLOW_HISTORICAL=1` is set. The folder
`FINAL_PACKAGE_BMC_MIDM/` is an older packaged copy of the code.

## Reproducing AUC and ΔAUC from the stored predictions

```python
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
o = pd.read_csv("outputs/oof/oof_long.csv")            # subject_id, seed, fold, y, model, p_poor
auc = lambda m: np.mean([roc_auc_score(g.y, g.p_poor) for _, g in o[o.model == m].groupby("seed")])
print(auc("P1_clin_GBM"), auc("F_late_P1_E"), auc("F_late_P1_E") - auc("P1_clin_GBM"))   # 0.763 0.774 +0.011
v = pd.read_csv("outputs_validity/oof/oof_long_vA.csv")  # fully nested: A_clin 0.698, A_late_rec 0.752
```

Bootstrap CIs use 2,000 patient-level resamples in which each patient carries all five seed predictions
(`s05_evaluate.py`, `validity/v_common.boot_indices`). `validity/qa_code_checks.py` performs these reproductions and
checks every OOF file against its fold manifest.

## What needs the original images

Unit recovery and CTP features (s02, s15), the ISLES 2018 simulation (s03) and benchmark (vX1, vX1b), atlas location
features and registration (s25, vD), native-unit voxel comparisons (vB) and the storage-precision centre signature
(s19). Everything downstream of the stored per-patient tables and out-of-fold predictions (all AUCs, paired
differences, calibration, decision curves, sample sizes) can be recomputed without images. End-to-end regeneration from
the raw images was performed when the analyses were run but was not repeated in the final quality-control pass.

## External benchmarks and validation

- Executed: ISLES 2018 technical component benchmark (63 patients, 94 slabs; CTP core vs expert DWI core; slab-summed
  and de-duplicated estimates; no outcome data).
- Not executed: UniToBrain (no Tmax map), Johns Hopkins head-CT brain masks (data not obtainable), CPAISD and AISD (no
  reference label matching a pipeline output).
- No independent external prognostic validation was possible (no accessible cohort with CTP and 90-day mRS).

## Evidence ledger statuses

In `CLAIM_TO_EVIDENCE_REPAIRED.csv`, `VERIFIED` means the claim was checked against a cited file that is present in the
delivery package; `VERIFIED_WITH_LIMITATION` means it was checked but rests on an inference, an approximation or an
estimate whose limitation is stated in the manuscript; `SOURCE_MISSING` marks author-completed declarations. The column
`reproducibility_from_LIGHT` states whether a claim can be recomputed from the light package or only checked there.

## Outputs

`outputs/` (canonical: tables, oof, data, figures), `outputs_validity/` (post hoc: tables, oof, data, figures, final
fitted models in `models/`).
