"""Documents of the targeted scientific repair (2026-11-14, second pass), written to BMC_TARGETED_REPAIR_2026-11-14/:
  SCIENTIFIC_REPAIR_REPORT.md        concise before/after report (numbers read from the result tables)
  FINAL_VALIDITY_AUDIT_REPAIRED.md   the validity audit with superseded statements corrected
  REMAINING_LIMITATIONS_REPAIRED.md  the limitations list, synchronised with the repaired manuscript
  CLAIM_TO_EVIDENCE_REPAIRED.csv     claim matrix with repair notes and an automatic check that every cited evidence
                                     file is present in the delivery package; a claim is never marked VERIFIED when a
                                     cited file is missing from the package
  VERIFICATION_FILES_README.md, MODEL_CODE_GLOSSARY.csv   for the verification/ folder of the light package
The original audit files in BMC_FEASIBILITY_VALIDITY_UPGRADE/ are left unchanged.
"""
import re

import pandas as pd
from openpyxl import load_workbook

from v_common import ROOT, VTAB
import w10_additional_file5 as W10
import w11_final_package as W11

B3 = ROOT.parent
VU = B3 / "BMC_FEASIBILITY_VALIDITY_UPGRADE"
REP = B3 / "BMC_TARGETED_REPAIR_2026-11-14"
REP.mkdir(exist_ok=True)


def nums():
    E = pd.read_csv(VTAB / "vE_bootstrap_refit_summary.csv").set_index("quantity")
    Ed = pd.read_csv(VTAB / "vE_bootstrap_refit_draws.csv")
    X = pd.read_csv(VTAB / "vX1_isles2018_core_vs_dwi.csv").set_index(["analysis", "metric"])
    Xb = pd.read_csv(VTAB / "vX1b_isles2018_core_vs_dwi_dedup.csv").set_index(["analysis", "metric"])
    Sb = pd.read_csv(VTAB / "vX1b_slab_overlap_summary.csv").iloc[0]
    A = pd.read_csv(VTAB / "vA_paired.csv")
    a = A[A.role.str.startswith("PRIMARY")].iloc[0]
    k0, k1 = "s03_harmonised: all patients", "s03_harmonised: all patients | dedup_adjacency_keepA (primary)"
    f = lambda T, k, m: T.loc[(k, m)]
    return dict(
        sd_fix=E.loc["dAUC F - P1", "fixed_pred_boot_sd"], sd_ref=E.loc["dAUC F - P1", "refit_boot_sd"],
        ratio=E.loc["dAUC F - P1", "sd_ratio_refit_over_fixed"], w_fix=E.loc["dAUC F - P1", "fixed_pred_boot_width"],
        w_ref=E.loc["dAUC F - P1", "refit_boot_width"], p1_ref=E.loc["P1 AUC", "refit_boot_mean"],
        p1_can=E.loc["P1 AUC", "canonical_estimate"], uq=(Ed.n_unique / 129).mean(), uq_lo=(Ed.n_unique / 129).min(),
        uq_hi=(Ed.n_unique / 129).max(),
        d0=f(X, k0, "dice_mean"), s0=f(X, k0, "sensitivity_mean"), v0=f(X, k0, "vol_bias_ml"), r0=f(X, k0, "spearman_core_vs_dwi"),
        d1=f(Xb, k1, "dice_mean"), s1=f(Xb, k1, "sensitivity_mean"), v1=f(Xb, k1, "vol_bias_ml"), r1=f(Xb, k1, "spearman_core_vs_dwi"),
        p1=f(Xb, k1, "precision_mean"), p0=f(X, k0, "precision_mean"),
        ndup=int(Sb.patients_with_duplicated_slices_adjacency), nstrict=int(Sb.patients_with_duplicated_slices_strict),
        ntwo=int(Sb.two_slab_patients), otd=Sb.ot_slice_dice_median_duplicated_pairs, oto=Sb.ot_slice_dice_median_other_matched_pairs,
        da=a.delta_auc, da_lo=a.ci_lo, da_hi=a.ci_hi)


def ci(r, nd=3):
    return f"{r.estimate:.{nd}f} ({r.ci_lo:.{nd}f} to {r.ci_hi:.{nd}f})"


def report(n):
    T = f"""# Scientific repair report: BMC MIDM feasibility manuscript (2026-11-14)

This report covers the two repair passes applied to the first final version. The canonical outputs
(`analysis_v3/outputs`, 246 files) are byte-identical to the baseline snapshot; no model was retrained and no benchmark was
repeated in the final pass. The primary and fully nested OOF results and the ISLES 2018 de-duplicated patient-level
metrics were reproduced independently by the reviewer.

## Part A. Final content-only repair (no new analyses)

| # | Item | Before | After |
|---|---|---|---|
| 1 | Optimism of the locked clinical GBM | "the absolute AUC of the clinical GBM should be read as optimistic by up to about 0.04"; Discussion: "its absolute AUC is optimistic" | The 0.036 locked-vs-nested difference "does not isolate selection-induced optimism" (different tuning strategy and objective); selection on the same cohort "remains a concern, but its magnitude cannot be estimated from this comparison"; Discussion: "may be optimistic, although this comparison cannot isolate by how much"; Limitations reworded accordingly |
| 2 | Bootstrap-refit interpretation | "suggested that these intervals understate uncertainty"; "indicates the direction of the error"; "SEs … too small by an amount that cannot be quantified" | Abstract: "exploratory refitting (different design) showed greater variability without calibrating these intervals". Methods, M5, Results, Limitations, cover letter, Additional file 5 (Table S32), audit and limitations list: SD ratio {n['ratio']:.2f} reported as an observed difference under a design with about {n['uq']:.0%} unique patients per resample and one CV; it neither shows that the primary CIs are underestimated by any specific amount nor establishes the direction or size of any bias in the sample sizes |
| 3 | 350-patient target | Abstract: "A definitive study would provisionally need about 350 patients … with 24-h NIHSS and follow-up imaging" | Abstract: "A provisional target of about 350 patients (≈120 events) applies only to a constrained pre-treatment CTP comparison, not to post-treatment, highly parameterised or external-validation analyses"; same restriction in M5, Discussion and Conclusions |
| 4 | Published ISLES'24 centre count | Yellow placeholder asking the authors to confirm 100/49; source table "not re-read" | Placeholder removed; published Table 1 count 100/49 (N = 149) stated as confirmed. 99/50 storage inference and the unresolved subject-level provenance limitation retained |
| 5 | Audit and handover documents | Audit Phase 6 described the validity-revised manuscript (abstract 347 words, "0.698–0.727", S21–S35, 45 claims); first-pass change log with superseded abstract in the submission ZIP | Audit Phase 6 rewritten for the current manuscript (separate estimates 0.727 and 0.698; Additional file 5 Tables S21–S42; 54-claim matrix); first-pass change log moved to the FULL audit trail as superseded |
| 6 | Evidence missing from LIGHT | 10 claims cited files absent from LIGHT (cohort and M1 patient-level data, preprocessing configuration, native-verification data, provenance audit, data-access drafts, superseded audit) | Added to LIGHT (CC BY-NC-SA 4.0 derivatives, public pseudonymous IDs): cohort_129, cohort_flow_149, CTP feature tables (recovered and native), acquisition fingerprints, location features, release preprocessing configuration, native-verification per-subject data, provenance audit; data-access drafts added to audit/. New column `reproducibility_from_LIGHT` distinguishes recomputable claims from image-derived claims that can only be checked |
| 7 | ISLES 2018 | "one slice location appeared in both slabs" | "image similarity indicated that one slice location appeared in both slabs … physical slice positions were not available to verify this"; low Dice and sensitivity and all limitations retained; no external prognostic validation claimed |
| 8 | Synchronisation | — | Manuscript, cover letter, Additional file 5, claim matrix, limitations list, audit and this report updated together; no numerical value changed except removal of "0.04" and rephrasing "−0.036" as "0.036 lower" |

## Part B. Targeted scientific repair (earlier pass; wording as now in the manuscript)

| # | Issue | Before | After | Evidence | Status |
|---|---|---|---|---|---|
| 1 | ISLES'24 centre counts | Text cited descriptor v1 (100/50 of 150) and v2 (99/50 of 149); audit stated "no version reports 100/49" | All three sources cited: arXiv v1 100/50 of 150, arXiv v2 99/50 of 149, published article Table 1 100/49 of 149. The storage signature reproduces 99/50, the identifier-block split reproduces 100/49. The info sheet on Zenodo (12 kB) holds only the variable dictionary, so no per-case centre list was available. For the one discordant patient (sub-stroke0008), three outcome-independent case-level signatures (imputation pattern, recorded 24-h NIHSS, CT pixel spacing) match the larger cluster; on each, its value occurs in 0 of 49 concordant smaller-cluster patients. Centre identity is stated as **not verified** at subject level. Existing sensitivity results (canonical / reassigned / excluded) retained | vC2_centre_count_sources.csv, vC2_ambiguous_case_signatures.csv, vC2_signature_by_cluster.csv, patient_provenance_ledger_extended.csv; AF5 S40–S42 | arXiv counts verified from the PDFs; published Table 1 count confirmed by the authors |
| 2 | Bootstrap-refit | "SD 1.7 times … so the primary CIs understate uncertainty"; abstract: "widened the spread 1.7-fold" | Described as exploratory: B = 100, {n['uq']:.0%} unique patients per resample (range {n['uq_lo']:.0%}–{n['uq_hi']:.0%}), one 10-fold CV per resample; SD of ΔAUC {n['sd_ref']:.3f} vs {n['sd_fix']:.3f} (ratio {n['ratio']:.2f}), refit clinical AUC mean {n['p1_ref']:.3f} vs {n['p1_can']:.3f}. Greater variability under a different design; not a calibrated correction of the intervals or the sample sizes (see Part A, item 2) | vE_bootstrap_refit_summary.csv, vE_bootstrap_refit_draws.csv; AF5 S32 | numbers verified; interpretation narrowed |
| 3 | ISLES 2018 two-slab patients | TP/FP/FN and volumes summed across slabs without checking overlap | Header geometry unusable (identity affine, no slice position in NIfTI or JSON). Estimate from image similarity (not verified from physical positions): {n['ndup']} of {n['ntwo']} two-slab patients have one duplicated slice location (adjacency criterion; {n['nstrict']} by the strict criterion NCC ≥ 0.95); reference-mask slice Dice at duplicated pairs {n['otd']:.2f} vs {n['oto']:.2f} at other matched pairs (independent plausibility check). De-duplicated Dice {ci(n['d1'])}, sensitivity {ci(n['s1'])}, mean volume difference {ci(n['v1'], 1)} mL; slab-summed values Dice {ci(n['d0'])}, sensitivity {ci(n['s0'])}, {ci(n['v0'], 1)} mL. Slab-summed results are labelled as such | vX1b_slab_overlap_summary.csv, vX1b_slab_overlap_per_patient.csv, vX1b_isles2018_core_vs_dwi_dedup.csv, vX1b_isles2018_per_patient_ledger.csv; AF5 S38–S39 | verified (image-based estimate; sub-slice overlap unresolved) |
| 4 | Interpretation of ISLES 2018 agreement | "core agreed modestly with DWI"; "technical operation and core agreement" | Technical execution (no failures, finite features, side agreement 99%) separated from anatomical accuracy (limited: Dice 0.21, sensitivity 0.15, about −32 to −33 mL); "not a validation of clinical core segmentation". The median harmonisation was introduced after the as-distributed run on the same data, and ISLES 2018 was already used in the unit-recovery simulation, so the benchmark is not fully untouched | as above; s03_isles2018_validation.py | wording repaired |
| 5 | Voxel alignment and registration Dice | Audit: "voxel Dice values are lower bounds"; registration Dice reported against "the CT intracranial mask" | Approximate axis-flip alignment does not make voxel Dice a bound; values combine recovery error and residual misalignment. Registration Dice is against an automatically derived NCCT intracranial mask: a consistency check, not expert ground truth | vB_native_per_subject.csv (align_flip, align_corr_tmax median 0.84); vD_registration_quality.csv | wording repaired |
| 6 | Abstract AUC range | "0.763 (0.698–0.727 with configurations re-selected within folds)" | "two sensitivity analyses re-selecting configurations within folds gave separate estimates of 0.727 and 0.698" | performance_all_models_sens_nestedgbm.csv (0.727); vA_performance.csv (0.698) | repaired |
| 7 | CTP recommendation and sample size | "no-go for pre-treatment CTP, thresholds, volumes and location"; "a definitive study would need about 350 patients" | Recommendations conditional on study design and measurement validity; CTP "not a priority as measured here, but not excluded" given the fully nested ΔAUC +{n['da']:.3f} (95% CI {n['da_lo']:.3f} to +{n['da_hi']:.3f}); thresholds, volumes and location "deprioritised". 350 patients = provisional target for a constrained pre-treatment CTP comparison, requiring recalculation. Original results and the canonical go_nogo.csv unchanged | vA_paired.csv; design_sample_size.csv; go_nogo.csv | repaired (decisions remain judgements) |
| 8 | Methods vs post hoc voxel analysis | Methods: "no voxelwise reconstruction accuracy was computed on ISLES'24" while a post hoc voxel comparison was reported | "The prespecified analyses included no voxelwise comparison on ISLES'24; an approximate voxelwise comparison was added post hoc" | — | repaired |
| 9 | Light review package | No OOF predictions or fold records (models excluded) | LIGHT_2 now has verification/: OOF predictions (primary and post hoc), outer-fold manifests, inner-selection records, pooled probabilities, train/test AUCs, inferred centre labels and provenance ledger, ISLES 2018 per-patient and per-slab ledgers, model-code glossary. No models, checkpoints, arrays or images | LIGHT_2_results_and_audit_summary.zip | done (public pseudonymous IDs only; CC BY-NC-SA 4.0) |
| 10 | Synchronisation | — | Manuscript, cover letter, Additional file 5 (Tables S21–S42, captions for S24, S25, S29, S32–S34 revised), claim-to-evidence matrix, audit report and limitations list updated together. Claims whose cited files are absent from the package are not marked VERIFIED | CLAIM_TO_EVIDENCE_REPAIRED.csv; FINAL_VALIDITY_AUDIT_REPAIRED.md | done |

## Numbers that changed in the manuscript (both passes)

- Added: centre count 100/49 (published Table 1), case-level signature result, slab-overlap counts ({n['ndup']}/{n['ntwo']}), de-duplicated
  Dice {n['d1'].estimate:.2f} (95% CI {n['d1'].ci_lo:.2f}–{n['d1'].ci_hi:.2f}), sensitivity {n['s1'].estimate:.2f} ({n['s1'].ci_lo:.2f}–{n['s1'].ci_hi:.2f}), volume difference {n['v1'].estimate:.0f} mL ({n['v1'].ci_lo:.0f} to {n['v1'].ci_hi:.0f}),
  ratio {n['ratio']:.2f} with the refit AUC {n['p1_ref']:.3f}, the fully nested ΔAUC in the abstract and Table 3.
- Removed: "1.7-fold" (three places), "0.698–0.727" as a range, "optimistic by up to about 0.04", the centre outcome counts
  38/88 vs 6/41 from the abstract (centre outcome rates remain in the Results), the abstract sentence on equivalence (still in
  the Results).
- Unchanged: every primary estimate, CI and P value; all canonical result files.

## Still unresolved (stated in the manuscript)

- No subject-level centre list was accessible (it may exist inside the 99 GB train.7z archive, which was not downloaded);
  centre assignments remain inferred.
- Sub-slice slab overlap in ISLES 2018 cannot be resolved without physical slice positions.
- No external prognostic validation exists.
- Administrative declarations remain highlighted for the authors (AUTHOR_TODO.md).
"""
    (REP / "SCIENTIFIC_REPAIR_REPORT.md").write_text(T, encoding="utf-8")


AUDIT_SUBS = [
    ("# Final validity audit: BMC MIDM feasibility manuscript (ISLES'24 CTP framework)\n",
     "# Final validity audit: BMC MIDM feasibility manuscript (ISLES'24 CTP framework) — repaired version\n\n"
     "> Updated by the targeted scientific repair of 2026-11-14 (see SCIENTIFIC_REPAIR_REPORT.md). Corrected statements are "
     "marked **[repaired]**; the original file is kept unchanged in the audit trail.\n"),
    ("**ISLES'24 centre counts: correction to the task premise.**\n"
     "- Descriptor v1 (arXiv:2408.11142v1) reports **100/50 of 150** training cases.\n"
     "- Descriptor v2 reports **99/50 of 149**, which is exactly the canonical inference.\n"
     "- No version reports 100/49. That figure is the subject-ID-block split already mentioned in the manuscript.\n"
     "- The manuscript text was corrected to cite both descriptor versions.",
     "**ISLES'24 centre counts [repaired].**\n"
     "- arXiv:2408.11142 v1 reports **100/50 of 150** training cases; v2 reports **99/50 of 149** (= storage-signature inference).\n"
     "- The published article (Radiol Artif Intell 2026;8(3):e250603), Table 1, reports **100/49 of 149** (= identifier-block "
     "split; confirmed by the authors).\n"
     "- The earlier statement \"No version reports 100/49\" is withdrawn.\n"
     "- The separately downloadable info sheet (Zenodo 16813698) contains only the variable dictionary; no per-case centre "
     "list was accessible. Centre identity is therefore not verified at case level."),
    ("- **Voxel-level comparison** on a common grid: alignment correlation median 0.84. Voxel Dice values are therefore lower bounds.",
     "- **Voxel-level comparison** on an approximate common grid (axis-flip alignment; correlation median 0.84). **[repaired]** "
     "Approximate alignment does not make the voxel Dice values bounds: they combine recovery error with residual misalignment."),
    ("- **Outcome:** the mapping was not changed, so M4 was not replaced.",
     "- **Case-level signatures [repaired]:** imputation pattern (1 of 4 variables imputed), recorded 24-h NIHSS and CT pixel "
     "spacing 0.41 mm match the larger cluster; each value occurs in 0 of 49 concordant smaller-cluster patients. "
     "Consistent with the published 100/49 count, but not a verification.\n"
     "- **Outcome:** the mapping was not changed, so M4 was not replaced."),
    ("- **Registration quality:** Dice vs NCCT intracranial mask 0.92 (NCCT) vs 0.91 (DWI re-run).",
     "- **Registration quality:** Dice vs the automatically derived NCCT intracranial mask 0.92 (NCCT) vs 0.91 (DWI re-run) "
     "**[repaired]**: a consistency check, not agreement with expert manual segmentation."),
    ("- **Conclusion:** the canonical CIs understate uncertainty, and the sample-size estimates (M5) are optimistic.",
     "- **Conclusion [repaired]:** exploratory. Each resample contains about 63% unique patients and is analysed with one "
     "cross-validation, a design different from the primary analysis. The observed SD ratio 1.72 shows greater variability "
     "under that design; it does not show that the primary CIs are underestimated by any specific amount and does not "
     "establish the direction or magnitude of any bias in the M5 sample sizes."),
    ("- **CTP core vs expert DWI core:**",
     "- **CTP core vs expert DWI core (slab-summed) [repaired]:** limited anatomical agreement; not a validation of core segmentation."),
    ("- **By protocol:** similar across acquisition protocols (matrix 256; 5/10/12 mm groups).",
     "- **By protocol:** similar across acquisition protocols (matrix 256; 5/10/12 mm groups).\n"
     "- **Slab overlap [repaired]:** headers carry no slice position; image similarity indicated one duplicated slice location "
     "in 17 of 31 two-slab patients (not verified from physical positions). De-duplicated: Dice 0.21 (0.18–0.23), sensitivity 0.15 (0.13–0.17), volume difference "
     "−32 mL (−42 to −22).\n"
     "- **Independence [repaired]:** the median rescaling was introduced after the as-distributed run on the same data, and "
     "ISLES 2018 had been used for the unit-recovery simulation; the benchmark is not a fully untouched evaluation."),
    ("| Dataset version mismatch | ISLES'24 descriptor v1 vs v2 resolved (99/50 = v2). ISLES 2018 copy = SMIR 2018 training set. |",
     "| Dataset version mismatch | **[repaired]** ISLES'24 counts differ across arXiv v1 (100/50 of 150), v2 (99/50 of 149) and the "
     "published article (100/49 of 149); unresolved at case level. ISLES 2018 copy = SMIR 2018 training set. |"),
    ("| Patient/scan duplication | ISLES 2018 slabs aggregated per patient.",
     "| Patient/scan duplication | ISLES 2018 slabs aggregated per patient; **[repaired]** overlapping slab slices identified "
     "from image content and counted once (slab-summed values kept for comparison)."),
    ("| Label leakage | ISLES 2018 rescaling uses whole-slab medians, not OT.",
     "| Label leakage | ISLES 2018 rescaling uses whole-slab medians, not OT (**[repaired]** but it was chosen after the "
     "as-distributed run on the same data)."),
    ("- The bootstrap-refit shows the primary CIs are ~1.7× too narrow in SD.",
     "- **[repaired]** The exploratory bootstrap-refit showed greater variability of ΔAUC (SD ratio 1.72) under a different "
     "resampling and cross-validation design; it is not a calibrated correction of the primary CIs or of the sample sizes."),
    ("Its threshold core agrees modestly with the expert early DWI core (Dice 0.21; Spearman 0.62; −33 mL bias).",
     "**[repaired]** Technical execution is shown; anatomical agreement of its threshold core with the expert early DWI core "
     "is limited (Dice 0.21 slab-summed and de-duplicated; sensitivity 0.15; mean volume difference −33 / −32 mL; Spearman 0.62)."),
    ("- Adequately powered estimation: about 350 patients, and more once refitting variability is included.",
     "- Adequately powered estimation: about 350 patients as a provisional target for a constrained pre-treatment CTP "
     "comparison only, to be recalculated (not sufficient for post-treatment, highly parameterised or external-validation "
     "analyses)."),
    ("- **Procedure contrast vs locked P1:** −0.065 (−0.101 to −0.032). Because the procedures differ, this is *not* a pure "
     "estimate of selection bias.",
     "- **Procedure contrast vs locked P1:** −0.065 (−0.101 to −0.032). Because the procedures differ, this is *not* a pure "
     "estimate of selection bias. **[repaired]** Likewise, the 0.036 difference between the locked and GBM-only nested "
     "procedures does not isolate selection-induced optimism, and the manuscript no longer assigns it a magnitude."),
    ("  - the refit levels are biased low (~63% unique patients per resample);",
     "  - the refit AUCs are lower on average, consistent with ~63% unique patients per resample;"),
]


def repaired_csvs():
    """Current copies of two validity-upgrade tables for the light package (originals kept in the FULL audit trail)."""
    iv = pd.read_csv(VU / "INTERNAL_VALIDITY_RESULTS.csv")
    for c in iv.columns:
        if iv[c].dtype == object:
            iv[c] = (iv[c].str.replace("level biased low (bootstrap samples contain ~63% unique patients)",
                                       "lower level, consistent with ~63% unique patients per resample; exploratory, not a "
                                       "calibrated correction", regex=False)
                          .str.replace("PRIMARY (Exp A): ", "Main post hoc comparison (fully nested): ", regex=False))
    iv.to_csv(REP / "INTERNAL_VALIDITY_RESULTS_REPAIRED.csv", index=False)
    log = pd.read_csv(VU / "EXPERIMENT_EXECUTION_LOG.csv")
    log.loc[log.step == "P6", "scope_and_runtime"] = ("content update of the validity-revised manuscript (superseded by "
                                                       "Manuscript_BMC_MIDM_FINAL.docx; see SCIENTIFIC_REPAIR_REPORT.md)")
    add = [
        ("P7", "First final version: descriptive names, placeholders, Figures 3 and 6 redrawn, Additional file 5", "EXECUTED",
         "w07_figures_clean.py; w08_freeze_models.py; w09_final_manuscript.py; w10_additional_file5.py; w12_cover_letter.py",
         "no new analysis", "formatting untouched", "2026-11-14", "no"),
        ("P8", "Targeted scientific repair: published centre counts, case-level signatures, ISLES 2018 slab de-duplication",
         "EXECUTED", "vC2_centre_reconciliation.py; vX1b_isles2018_slab_overlap.py; w13_targeted_repair.py; w14_repair_documents.py",
         "post hoc; image-based overlap estimate (ISLES 2018 images)", "Additional file 5 Tables S38-S42", "2026-11-14", "no"),
        ("P9", "Final content-only repair", "EXECUTED", "w13_targeted_repair.py; w12_cover_letter.py; w14_repair_documents.py",
         "no new analysis", "optimism not quantified; bootstrap-refit exploratory; 350 provisional", "2026-11-14", "no"),
        ("P10", "Final evidence-ledger, README and code QA", "EXECUTED", "qa_code_checks.py; w15_final_qa_report.py",
         "no new analysis; compile, imports, OOF schema, reproduction from stored predictions", "FINAL_CONTENT_AND_CODE_QA.md",
         "2026-11-14", "no"),
    ]
    log = pd.concat([log, pd.DataFrame(add, columns=log.columns)], ignore_index=True)
    log.to_csv(REP / "EXPERIMENT_EXECUTION_LOG_REPAIRED.csv", index=False)

PHASE6 = """## Phase 6: manuscript [repaired: describes the current version]

**File:** `Manuscript_BMC_MIDM_FINAL.docx`, built by `w09_final_manuscript.py` (descriptive names, placeholders) and
`w13_targeted_repair.py` (targeted and final content-only repairs). Earlier versions are kept only in the FULL audit trail.

**Formatting:** text replaced inside existing runs; Figures 3 and 6 redrawn from the same tables; no style changes.

**Abstract:** {abs_words} words without and {abs_labels} words with the four structured labels (limit 350). The clinical
AUC 0.763 is followed by two separate sensitivity-analysis estimates, attributed to their procedures: 0.727 (GBM settings
re-selected within folds) and 0.698 (post hoc fully nested learner selection); they are not a confidence interval. The
fully nested ΔAUC +0.054 (−0.006 to +0.121) is reported; the bootstrap-refit result is described as greater variability
under a different design, not as a correction; the ≈350-patient target is provisional and limited to a constrained
pre-treatment CTP comparison.

**Selection optimism of the locked clinical GBM:** described as a concern; not quantified.

**Additional file 5:** Tables S21–S42 and Figure S8 (S38–S39 ISLES 2018 slab overlap and de-duplication; S40–S42
centre-count reconciliation and case-level signatures).

**Claim matrix:** `CLAIM_TO_EVIDENCE_REPAIRED.csv`, {n_claims} claims (45 earlier, 9 added by the targeted repair), with
evidence availability in the LIGHT and FULL packages, a reproducibility-from-LIGHT column and a final-QA column.
Superseded interpretations are kept only in `CLAIM_TO_EVIDENCE_HISTORICAL_NOTES.csv` (labelled historical, FULL package).

**Final QA:** `FINAL_CONTENT_AND_CODE_QA.md` (ledger corrections, manuscript consistency checks, code and
reproducibility checks).

**Change log:** `MANUSCRIPT_REPAIR_CHANGE_LOG.md` (all edits relative to the first final version).

**Author items:** `AUTHOR_TODO.md`, {n_todo} administrative declarations, highlighted in the manuscript.

"""

LIM_SUBS = [
    ("# Remaining limitations after the validity upgrade (2026-11-14)",
     "# Remaining limitations after the validity upgrade and the targeted repair (2026-11-14)"),
    ("2. **Tuning dependence.**", "2. **Tuning dependence.** The 0.036 difference between the locked and nested clinical GBM "
     "procedures does not isolate selection-induced optimism (different tuning strategy and objective); selection bias of "
     "the locked configuration remains an unquantified concern."),
    ("3. **Underestimated uncertainty.** Model-refitting variability inflates the SD of ΔAUC by about 1.7×. The published CIs "
     "and the M5 sample sizes (≈306–350 patients) are therefore optimistic, and a definitive study needs a larger sample or a "
     "refit-aware power calculation.",
     "3. **Refitting variability.** The published CIs omit model-refitting variability. An exploratory bootstrap-refit "
     "analysis (B = 100, about 63% unique patients per resample, one CV each) showed greater variability of ΔAUC (SD ratio "
     "1.72), but because its design differs from the primary analysis it does not show that the CIs are underestimated by "
     "any specific amount, nor the direction or size of any bias in the M5 sample sizes (≈306–350 patients, a provisional "
     "target for a constrained pre-treatment comparison). A definitive study needs its own refit-aware power calculation."),
    ("    - optional confirmation of the centre labels by the ISLES organisers (the descriptor v2 says an info sheet with "
     "per-case centres exists; we did not find it in the public files);",
     "    - optional confirmation of subject-level centre labels by the ISLES organisers (the separately downloadable info "
     "sheet contains only the variable dictionary);"),
    ("4. **Inferred centres.** Centres were inferred, not labelled; exact identity is not established.",
     "4. **Inferred centres.** Centres were inferred, not labelled; published counts differ between descriptor versions "
     "(99/50 vs 100/49) and no per-case centre list was accessible, so exact identity is not established."),
    ("7. **Approximate voxel comparison.** The voxel-level native-vs-recovered comparison uses an approximate common grid "
     "(alignment r ≈ 0.84), so its voxel Dice values are lower bounds.",
     "7. **Approximate voxel comparison.** The voxel-level native-vs-recovered comparison uses an approximate common grid "
     "(axis-flip alignment, r ≈ 0.84); its voxel measures combine recovery error with residual misalignment and are not "
     "bounds. Registration Dice values are against an automatically derived intracranial mask, not expert segmentation."),
    ("so the frozen absolute limits are not unit-transportable.",
     "so the frozen absolute limits are not unit-transportable. The rescaling was introduced after the as-distributed run "
     "on the same data, so the benchmark is not fully untouched. Core agreement was limited (Dice 0.21, sensitivity 0.15). "
     "Slab overlap was estimated from image content because slice positions are missing; sub-slice overlap is unresolved."),
]


def apply(text, subs, name):
    for old, new in subs:
        assert text.count(old) == 1, (name, old[:70])
        text = text.replace(old, new)
    return text


def glossary():
    wb = load_workbook(B3 / "BMC_MIDM_FEASIBILITY_FINAL_AUDIT_PACKAGE" / "06_SUPPLEMENTARY" / "Additional_file_2_supplementary_tables.xlsx",
                       read_only=True)
    rows = list(wb["Glossary_models"].iter_rows(values_only=True))[1:]
    G = pd.DataFrame(rows, columns=["model_code", "description"]).dropna(subset=["model_code"])
    G["source"] = "Additional file 2, Glossary_models"
    extra = {k: v for k, v in W10.MODEL.items() if not k.startswith("canon_")}
    extra.update({"P1_nested_GBM": "Clinical GBM with configuration re-selected inside each training fold (nested tuning)",
                  "F_late_P1nested_E": "Nested-tuned clinical GBM + CTP all channels, late fusion"})
    add = pd.DataFrame([{"model_code": k, "description": v, "source": "post hoc analyses (Additional file 5)"}
                        for k, v in extra.items() if k not in set(G.model_code)])
    G = pd.concat([G, add], ignore_index=True)
    G.to_csv(REP / "MODEL_CODE_GLOSSARY.csv", index=False)
    import glob
    used = set()
    for f in glob.glob(str(ROOT / "outputs" / "oof" / "oof_long*.csv")) + glob.glob(str(ROOT / "outputs_validity" / "oof" / "oof_long*.csv")):
        used |= set(pd.read_csv(f, usecols=["model"]).model.unique())
    missing = sorted(used - set(G.model_code))
    return missing


VREADME = """# Verification files (light review package)

De-identified files that allow the main numbers to be recomputed without models or images. Subject identifiers are the
public pseudonymous IDs of ISLES'24 (sub-strokeNNNN) and ISLES 2018 (patient numbers); no other identifiers are present.
Derived from CC BY-NC-SA 4.0 data: non-commercial use, attribution and share-alike apply.

## Reproducing the headline numbers

```python
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
def auc(path, m):
    o = pd.read_csv(path)
    return np.mean([roc_auc_score(g.y, g.p_poor) for _, g in o[o.model == m].groupby("seed")])
p = "primary_analysis/oof/oof_long.csv"
print(auc(p, "P1_clin_GBM"), auc(p, "F_late_P1_E"))           # 0.763, 0.774; ΔAUC +0.011
v = "post_hoc_analyses/oof/oof_long_vA.csv"
print(auc(v, "A_clin"), auc(v, "A_late_rec"))                  # 0.698, 0.752; ΔAUC +0.054
L = pd.read_csv("isles2018_benchmark/vX1b_isles2018_per_patient_ledger.csv")
L = L[(L.scaling == "s03_harmonised") & (L.variant == "dedup_adjacency_keepA (primary)")]
print(L.dice.mean(), L.sensitivity.mean())                     # 0.206, 0.152
```
Confidence intervals: 2,000 patient-level bootstrap resamples, each patient carrying all five seed predictions.

## primary_analysis/oof and post_hoc_analyses/oof
- `oof_long*.csv`: one row per patient × seed × model: `subject_id, seed, fold, y (1 = mRS 3–6), model, p_poor`
  (`p_poor` = predicted P(mRS 3–6)). Primary estimand = mean over the five seeds (42, 100, 2024, 777, 999) of the AUC of
  `p_poor` against `y`. Every file was checked against its fold manifest (`validity/qa_code_checks.py`).
- `fold_manifest*.csv`: outer-fold assignment per seed (`seed, fold, subject_id`); the same manifest is shared by all models of a run.
- `inner_best_params*.csv`, `inner_selection_vA.csv`: hyperparameters (and, for the consistent nested run, learner family,
  inner log-loss, train and test AUC) chosen in each outer training fold.
- `pooled_probabilities*.csv`: seed-averaged probabilities (calibration and decision-curve inputs).
- `train_test_auc*.csv`: training- and test-fold AUC per fold (overfitting gap).
- Suffixes: none = primary run; `_all` = all models of the primary run in one file; `_munich` = within-Munich run;
  `_sens_*` = sensitivity analyses; `_ext_*`, `_lvo`, `_loc_dice80` = supplementary-plan models; `_vA` = consistent fully
  nested comparison; `_vD_*` = admission-CT registration.
- Model codes: `MODEL_CODE_GLOSSARY.csv`.

## centres
- `inferred_site.csv`: inferred centre per subject (storage-precision signature; 99/50).
- `patient_provenance_ledger_extended.csv`: all provenance signatures (S1–S10) and the alternative identifier-block vote (100/49).
- `PATIENT_LEVEL_PROVENANCE_AUDIT.csv`: the seven-signature provenance table of Additional file 5, Table S37.

## m1_data (cohort and data-readiness files)
- `cohort_129.csv`, `cohort_flow_149.csv`: analysed cohort (clinical predictors back-transformed to physical units, outcome)
  and the 149 → 129 flow with exclusion reasons.
- `ctp_features_v3_149.csv`, `ctp_features_native_149.csv`: the 53 CTP features from recovered-unit and native-unit maps,
  with the per-channel ceiling QC columns.
- `native_acquisition_fingerprints.csv`: voxel sizes, slab coverage and storage signatures of the native maps.
- `location_features.csv`: atlas-region coverage features (H1).
- `vB_native_per_subject.csv`: per-subject recovered-vs-native Tmax comparison on the approximate common grid.
- `config_snapshot.json`: pre-processing configuration distributed with the ISLES'24 release (clip limits used for unit recovery).

These are derivatives of the public ISLES'24 release (CC BY-NC-SA 4.0), which permits redistribution of adapted material
for non-commercial use with attribution under the same licence. ISLES 2018 files contain derived numbers only (no images).

## What LIGHT alone can and cannot reproduce
Statistical claims (AUCs, paired differences, bootstrap CIs, calibration, sample sizes) can be recomputed from these files.
Image-derived quantities (unit recovery, CTP features, voxel comparisons, registration, slab-overlap detection, storage
signatures) can be checked at patient level but not recomputed without the original images, which are not redistributed
here (99 GB release; ISLES 2018 images under their own terms). See the column `reproducibility_from_LIGHT` in
`audit/CLAIM_TO_EVIDENCE_REPAIRED.csv`.

## Evidence-ledger statuses
`VERIFIED`: checked against a cited file that is present in the package. `VERIFIED_WITH_LIMITATION`: checked, but the
claim rests on an inference, approximation or estimate whose limitation is stated in the manuscript. `SOURCE_MISSING`:
author-completed declarations (not a scientific failure).

## isles2018_benchmark
- `vX1_isles2018_per_slab.csv`: per-slab technical and agreement results of the unchanged pipeline (both input scalings).
- `vX1_isles2018_per_patient.csv`: slab-summed per-patient counts (as in Additional file 5, Table S34).
- `vX1b_slab_overlap_per_patient.csv`: image-based slab-overlap detection per two-slab patient (NCC of matched slices, adjacency thresholds, reference-mask slice Dice).
- `vX1b_isles2018_per_patient_ledger.csv`: per-patient TP/FP/FN, volumes and metrics for every variant (slab-summed; de-duplicated
  with the adjacency criterion keeping slab A (primary) or slab B; strict criterion) and both scalings. Patient-level
  bootstrap of these rows reproduces Additional file 5, Tables S34 and S39.
"""


def evidence_files(s):
    if not isinstance(s, str):
        return []
    toks = re.split(r"[;,\s]+", s)
    out = []
    for t in toks:
        t = t.strip().rstrip(")").lstrip("(")
        m = re.search(r"([A-Za-z0-9_.*\-]+\.(?:csv|json|py|md|jsonl|xlsx|docx|txt))", t)
        if m:
            out.append(m.group(1).split(":")[0])
    return out


def package_names():
    light = (W11.submission_items(False) + W11.results_items(False) + W11.audit_summary_items() + W11.verification_items()
             + W11.code_items(False))
    full = (W11.submission_items(True) + W11.results_items(True) + W11.code_items(True) + W11.model_items()
            + W11.full_audit_items())
    nm = lambda items: {a.split("/")[-1] for _, a in items} | {s.name for s, _ in items}
    return nm(light), nm(full)


REPAIR_NOTES = {
    "CL-29": ("Final repair: the 0.036 locked-vs-nested difference does not isolate selection-induced optimism (different "
              "tuning strategy and objective); the manuscript no longer assigns a magnitude to it."),
    "CL-03": "Voxel-level supplement uses an approximate common grid; voxel measures are not bounds.",
    "CL-05": ("Claim revised: storage signature 99/50 matches arXiv v2; identifier-block split 100/49 matches Table 1 of the "
              "published article (confirmed by the authors); arXiv v1 100/50 of 150. Centre identity not verified at case level."),
    "CL-22": ("Provisional planning figures based on fixed-prediction SEs that omit refitting variability; the exploratory "
              "bootstrap-refit does not establish the direction or size of any bias."),
    "CL-24": ("Claim revised: provisional target for a constrained pre-treatment CTP comparison only; not sufficient for "
              "post-treatment, highly parameterised or external-validation analyses."),
    "CL-25": ("Claim revised: decisions conditional on study design and measurement validity; pre-treatment CTP not a priority "
              "as measured but not excluded (fully nested ΔAUC +0.054, −0.006 to +0.121). Canonical go_nogo.csv unchanged; "
              "wording updated in manuscript Table 3."),
    "CL-30": "Bootstrap-refit is exploratory and uses a different design; it is not a calibrated correction (see CL-40).",
    "CL-36": "Approximate common grid (axis-flip alignment).",
    "CL-38": "Case-level signatures added (CL-48); identity still not verified.",
    "CL-39": "Registration Dice is against an automatically derived NCCT mask, not expert segmentation.",
    "CL-40": ("Claim revised: exploratory (B = 100, ~63% unique patients per resample, one CV each). The SD ratio 1.72 is an "
              "observed difference under a different design; it does not show that the primary CIs are underestimated by any "
              "specific amount nor the direction or size of bias in the sample sizes."),
    "CL-43": ("Claim revised: slab-summed estimates; limited core agreement (not a validation of core segmentation); "
              "harmonisation chosen after the as-distributed run on the same data. De-duplicated values: CL-51."),
    "CL-45": "Revised: supports neither a positive conclusion nor a firm no-go decision for CTP.",
}
CLAIM_TEXT = {
    "CL-05": "Centres inferred from map quantisation: 99/50 in the release (matches arXiv v2), 88/41 analysed (38 vs 6 poor); "
             "identifier-block split 100/49 (matches the published Table 1 count); arXiv v1 reports 100/50 of 150",
    "CL-24": "A provisional target of about 350 patients (about 120 events) applies only to a constrained pre-treatment CTP "
             "comparison under the present assumptions; it must be recalculated and is not sufficient for post-treatment, "
             "highly parameterised or external-validation analyses",
    "CL-45": "The size of the CTP increment depends on how both arms are tuned; supports neither a positive conclusion nor a "
             "firm no-go; none of the post hoc analyses is an external prognostic validation",
    "CL-25": "Proposed decisions per research direction, conditional on study design and measurement validity (Table 3)",
    "CL-40": "Exploratory bootstrap-refit (B = 100, ~63% unique per resample, one CV each): SD of dAUC 0.047 vs 0.027 "
             "(ratio 1.72); 95% width 0.173 vs 0.107; refit clinical AUC mean 0.691",
    "CL-43": "ISLES 2018 after label-free rescaling: 0 failures, 100% finite features, side agreement 99% (technical "
             "execution); slab-summed CTP core vs DWI core Dice 0.21 (0.18-0.24), sensitivity 0.15, precision 0.46, "
             "bias -33 mL: limited agreement",
}
NEW_CLAIMS = [
    ("CL-46", "Methods M1", "ISLES'24 training-set centre counts: arXiv v1 100/50 of 150; arXiv v2 99/50 of 149; published "
     "article Table 1 100/49 of 149", "source documents", "vC2_centre_count_sources.csv",
     "VERIFIED", "arXiv counts read from the PDFs; published Table 1 count confirmed by the authors. Subject-level centre "
     "provenance remains unresolved"),
    ("CL-47", "Methods M1", "The separately downloadable ISLES'24 info sheet holds only the variable dictionary; no per-case "
     "centre list was accessible", "downloaded file (12 kB) inspected", "vC2_centre_count_sources.csv", "VERIFIED", ""),
    ("CL-48", "Results (post hoc)", "Ambiguous patient sub-stroke0008: imputation pattern, recorded 24-h NIHSS and CT pixel "
     "spacing match the larger cluster; each value occurs in 0/49 concordant smaller-cluster patients",
     "case-level signatures", "vC2_ambiguous_case_signatures.csv; vC2_signature_by_cluster.csv; patient_provenance_ledger_extended.csv",
     "VERIFIED_WITH_LIMITATION", "consistency only; centre identity not verified"),
    ("CL-49", "Methods (external technical)", "ISLES 2018 NIfTI headers have identity affines and the JSON sidecars no slice "
     "position, so slab positions cannot be read from metadata", "header inspection", "vX1b_slab_overlap_summary.csv; vX1b_isles2018_slab_overlap.py",
     "VERIFIED", ""),
    ("CL-50", "Results (external technical)", "Image similarity indicates one duplicated slice location in 17 of 31 "
     "two-slab ISLES 2018 patients (adjacency criterion; 7 strict), not verified from physical positions; reference-mask "
     "slice Dice 0.70 at duplicated vs 0.00 at other matched pairs",
     "image-based estimate", "vX1b_slab_overlap_summary.csv; vX1b_slab_overlap_per_patient.csv", "VERIFIED_WITH_LIMITATION",
     "sub-slice overlap unresolved"),
    ("CL-51", "Results (external technical)", "De-duplicated ISLES 2018 agreement: Dice 0.206 (0.179-0.234), sensitivity 0.152 "
     "(0.130-0.175), mean volume difference -31.6 mL (-41.8 to -22.0)", "patient-level bootstrap",
     "vX1b_isles2018_core_vs_dwi_dedup.csv; vX1b_isles2018_per_patient_ledger.csv", "VERIFIED_WITH_LIMITATION",
     "estimate; depends on the overlap rule (alternatives in the same table)"),
    ("CL-52", "Abstract", "0.727 (GBM-only nested tuning) and 0.698 (consistent fully nested selection) are separate "
     "sensitivity-analysis AUCs, not CI bounds", "result tables", "performance_all_models_sens_nestedgbm.csv; vA_performance.csv",
     "VERIFIED", ""),
    ("CL-53", "Methods M1", "No voxelwise comparison was prespecified on ISLES'24; an approximate voxelwise comparison was "
     "added post hoc", "code and outputs", "vB_native_verification.py; vB_native_per_subject.csv", "VERIFIED", ""),
    ("CL-54", "Methods (external technical)", "The ISLES 2018 median harmonisation was introduced after the as-distributed run "
     "on the same data, and ISLES 2018 was used for the unit-recovery simulation", "code history",
     "s03_isles2018_validation.py; vX1_isles2018_benchmark.py", "VERIFIED", ""),
]


# Final QA (2026-11-14): current interpretation fields that replace outdated wording. The superseded wording is written
# only to CLAIM_TO_EVIDENCE_HISTORICAL_NOTES.csv, which is labelled as a historical record.
CURRENT = {
    "CL-05": {"validity_upgrade_update": "Descriptor counts: arXiv v1 100/50 of 150; arXiv v2 99/50 of 149 (= storage-signature "
                                         "inference); published article Table 1 100/49 of 149 (= identifier-block split). See "
                                         "CL-38 and CL-46."},
    "CL-09": {"notes": "Performance estimates of the locked P1 configuration may be affected by model-selection optimism because "
                       "the configuration was selected using the same cohort. The magnitude of this bias is not identified by the "
                       "current sensitivity analyses."},
    "CL-20": {"notes": "Values match performance_all_models_munich.csv and paired_auc_comparisons_munich.csv"},
    "CL-21": {"notes": "Wording: statistically inconclusive; evidence neither of transportability failure nor of success"},
    "CL-26": {"notes": "Core and Tmax > 6 s extents are labelled as percentages of covered tissue"},
    "CL-27": {"notes": "Brier column pooled (seed-averaged) for consistency with the slope; the two location rows are labelled "
                       "'admission CTP; atlas registered to follow-up DWI' because the primary location features use a "
                       "post-treatment registration target"},
    "CL-28": {"evidence_files": "s09_figures.py; s22_new_figures.py; s29_framework_figure.py; w07_figures_clean.py",
              "notes": "N labels in Fig. 1 hard-coded but verified; Figures 3 and 6 redrawn with descriptive labels from the same "
                       "tables by w07_figures_clean.py"},
    "CL-29": {"notes": "The locked and nested-selected GBM procedures differ by approximately 0.036 AUC, but they use different "
                       "model-selection strategies and objectives. This comparison does not isolate or quantify "
                       "selection-induced optimism. The observed CTP increment remains statistically uncertain."},
    "CL-30": {"validity_upgrade_update": "Exploratory bootstrap-refit (B = 100) showed a larger SD of ΔAUC (0.047 vs 0.027; "
                                         "ratio 1.72) under a different resampling and cross-validation design; it is not a "
                                         "calibrated correction. See CL-40."},
    "CL-31": {"notes": "Verification output: reference_verification_crossref.json (primary result tables). Reference 14 was later "
                       "extended with its preprint versions (arXiv:2408.11142 v1 and v2); reference 20 awaits the authors' update"},
    "CL-35": {"claim": "Fully nested comparison: increment within inferred centres +0.052 (-0.017 to +0.119); native-unit CTP "
                       "increment +0.023 (-0.033 to +0.086)"},
    "CL-36": {"notes": "Voxel-level comparisons use an approximate common grid and correlation-based axis-flip alignment. The "
                       "reported Dice values combine recovery error and residual spatial misalignment. They are neither proven "
                       "lower nor upper bounds on true voxel agreement."},
    "CL-40": {"notes": "B = 100 gives imprecise percentile endpoints; refit AUCs are lower on average, consistent with about 63% "
                       "unique patients per resample"},
    "CL-52": {"notes": "Abstract wording: 're-selecting GBM settings within folds gave 0.727 and post hoc fully nested learner "
                       "selection 0.698'"},
}
FINAL_QA = {
    "CL-05": "Outdated statement that no descriptor reports 100/49 removed from current fields.",
    "CL-09": "Note replaced: optimism of the locked configuration is a concern, not an established or quantified bias.",
    "CL-29": "Note replaced: the 0.036 difference does not isolate or quantify selection-induced optimism.",
    "CL-30": "Validity-upgrade note reworded: no fold-change interpretation.",
    "CL-36": "Note replaced: approximate-grid Dice is neither a lower nor an upper bound.",
    "CL-40": "Note reworded: refit AUC levels described as lower on average, not as a quantified bias.",
    "CL-27": "Table 2 location rows relabelled (registration to follow-up DWI).",
    "CL-52": "Abstract now attributes 0.727 and 0.698 to their tuning procedures.",
}
FORBIDDEN_CURRENT = ("lower bound", "is real", "about 0.04", "1.7x", "1.7-fold", "No descriptor version reports",
                     "not re-read", "biased low", "optimistic (CL-29)")


def claims():
    C = pd.read_csv(VU / "CLAIM_TO_EVIDENCE_FINAL_UPDATED.csv")
    H = C[["claim_id", "status", "notes", "validity_upgrade_update"]].rename(columns={
        "status": "status_as_of_2026-11-13", "notes": "note_as_of_2026-11-13",
        "validity_upgrade_update": "validity_upgrade_note_as_of_2026-11-14_first_pass"})
    for k, v in CLAIM_TEXT.items():
        C.loc[C.claim_id == k, "claim"] = v
    C["repair_2026_11_14"] = C.claim_id.map(REPAIR_NOTES).fillna("")
    new = pd.DataFrame([{"claim_id": a, "section": b, "claim": c, "evidence_type": d, "evidence_files": e, "status": f,
                         "in_manuscript_text": "yes", "notes": g, "repair_2026_11_14": "NEW (targeted repair)"}
                        for a, b, c, d, e, f, g in NEW_CLAIMS])
    C = pd.concat([C, new], ignore_index=True)
    for cid, fields in CURRENT.items():
        for k, v in fields.items():
            C.loc[C.claim_id == cid, k] = v
    C["final_qa_2026_11_14"] = C.claim_id.map(FINAL_QA).fillna("reviewed against the final manuscript; no change needed")
    C.loc[C.claim_id == "CL-45", "evidence_files"] = "FINAL_VALIDITY_AUDIT_REPAIRED.md; vA_paired.csv"
    C.loc[C.claim_id == "CL-24", "evidence_files"] = "design_sample_size.csv; design_riley.csv (s11 DEF_N)"
    light, full = package_names()
    gaps_l, gaps_f, st = [], [], []
    for _, r in C.iterrows():
        fs = evidence_files(r.evidence_files)
        mf = [f for f in fs if not any(re.fullmatch(f.replace(".", r"\.").replace("*", ".*"), n) for n in full)]
        ml = [f for f in fs if not any(re.fullmatch(f.replace(".", r"\.").replace("*", ".*"), n) for n in light)]
        gaps_f.append("; ".join(mf)); gaps_l.append("; ".join(ml))
        s = r.status
        if isinstance(s, str) and s.startswith("VERIFIED") and mf:
            s = "SUPPORTED_BY_FILES_OUTSIDE_PACKAGE"
        if isinstance(s, str) and s.startswith("VERIFIED") and not fs:
            s = s + " (no file cited)"
        st.append(s)
    C["status_after_repair"] = st
    C["evidence_files_missing_from_FULL"] = gaps_f
    C["evidence_files_missing_from_LIGHT"] = gaps_l
    rep = []
    for (_, r), ml in zip(C.iterrows(), gaps_l):
        cid = r.claim_id
        if cid in DOCUMENT:
            rep.append(DOCUMENT[cid])
        elif ml:
            rep.append(f"NOT reproducible from LIGHT alone: {ml} not included")
        elif cid in IMAGING:
            rep.append("checkable from LIGHT patient-level outputs; recomputation needs the original images (not redistributed)")
        elif cid == "CL-51":
            rep.append("metrics recomputable from the LIGHT per-patient ledger; overlap detection needs the original images")
        else:
            rep.append("recomputable from LIGHT files (OOF predictions, result tables or patient-level data)")
    C["reproducibility_from_LIGHT"] = rep
    cur = ["claim", "notes", "validity_upgrade_update", "repair_2026_11_14", "status_after_repair", "reproducibility_from_LIGHT"]
    bad = [(r.claim_id, k, s) for _, r in C.iterrows() for k in cur for s in FORBIDDEN_CURRENT
           if isinstance(r[k], str) and s.lower() in r[k].lower()]
    assert not bad, bad
    C.to_csv(REP / "CLAIM_TO_EVIDENCE_REPAIRED.csv", index=False)
    H.insert(0, "record_type", "HISTORICAL (superseded wherever it differs from CLAIM_TO_EVIDENCE_REPAIRED.csv)")
    H.to_csv(REP / "CLAIM_TO_EVIDENCE_HISTORICAL_NOTES.csv", index=False)
    return C


IMAGING = {"CL-02", "CL-03", "CL-04", "CL-05", "CL-18", "CL-36", "CL-38", "CL-39", "CL-41", "CL-42", "CL-43", "CL-48",
           "CL-49", "CL-50", "CL-53"}
DOCUMENT = {"CL-31": "source check (references verified against bibliographic databases; JSON in results tables)",
            "CL-32": "author declarations; not a reproducible result",
            "CL-44": "document claim (compatibility matrix and data-access drafts in LIGHT audit/)",
            "CL-45": "interpretive claim based on recomputable results (vA_paired.csv) and the repaired audit",
            "CL-46": "source documents (arXiv PDFs; published article); counts tabulated in vC2_centre_count_sources.csv",
            "CL-47": "source document inspected (Zenodo info sheet, not redistributed); outcome recorded in vC2_centre_count_sources.csv",
            "CL-54": "code history (scripts in LIGHT_3)"}


def main():
    n = nums()
    report(n)
    repaired_csvs()
    (REP / "VERIFICATION_FILES_README.md").write_text(VREADME, encoding="utf-8")
    print("glossary: codes used in OOF files but not described:", glossary())
    C = claims()
    # audit: replace the Phase 6 section (it described the validity-revised manuscript) by the current version
    from docx import Document
    d = Document(W11.STG / "Manuscript_BMC_MIDM_FINAL.docx")
    abs_words = sum(len("".join(r.text for r in p.runs[1:]).split()) for p in d.paragraphs[6:10])
    todo = (W11.STG / "AUTHOR_TODO.md").read_text(encoding="utf-8")
    n_todo = len(re.findall(r"^\d+\. \[AUTHORS", todo, flags=re.M))
    a = apply((VU / "FINAL_VALIDITY_AUDIT.md").read_text(encoding="utf-8"), AUDIT_SUBS, "audit")
    a, k = re.subn(r"## Phase 6: manuscript\n.*?(?=## Phase 7)", PHASE6.format(abs_words=abs_words, abs_labels=abs_words + 4, n_claims=len(C), n_todo=n_todo),
                   a, flags=re.S)
    assert k == 1
    a = a.replace("| Manuscript–code contradictions | Number check passed. Descriptor wording corrected.",
                  "| Manuscript–code contradictions | Number check passed. **[repaired]** Centre counts from all three descriptor "
                  "versions cited; Methods statement on voxelwise analysis reconciled.")
    stale = [s for s in ("347 words", "0.698–0.727", "S21–S35", "45 claims", "62/63", "lower bound", "1.7×") if s in a]
    assert not stale, stale
    (REP / "FINAL_VALIDITY_AUDIT_REPAIRED.md").write_text(a, encoding="utf-8")
    (REP / "REMAINING_LIMITATIONS_REPAIRED.md").write_text(
        apply((VU / "REMAINING_LIMITATIONS.md").read_text(encoding="utf-8"), LIM_SUBS, "limitations"), encoding="utf-8")
    print("claims:", len(C), "abstract words:", abs_words, "author items:", n_todo)
    print(C.status_after_repair.value_counts().to_string())
    print(C.reproducibility_from_LIGHT.str[:60].value_counts().to_string())
    print(C.loc[(C.evidence_files_missing_from_FULL != "") | (C.evidence_files_missing_from_LIGHT != ""),
                ["claim_id", "status_after_repair", "evidence_files_missing_from_FULL", "evidence_files_missing_from_LIGHT"]].to_string())


if __name__ == "__main__":
    main()
