"""CLAIM_TO_EVIDENCE_FINAL_UPDATED.csv (33 existing claims kept, with update notes; new claims for the validity upgrade)
and EXPERIMENT_EXECUTION_LOG.csv.

HISTORICAL (2026-11-14): its output is the frozen base of the current ledger, which w14_repair_documents.py writes as
BMC_TARGETED_REPAIR_2026-11-14/CLAIM_TO_EVIDENCE_REPAIRED.csv (see README.md)."""
import os as _os
import sys as _sys
if _os.environ.get("BRANCH3_ALLOW_HISTORICAL") != "1":
    _sys.exit("Historical script (base claim ledger, input of w14); set BRANCH3_ALLOW_HISTORICAL=1 to run it anyway.")
import pandas as pd
from v_common import ROOT

U = ROOT.parent / "BMC_FEASIBILITY_VALIDITY_UPGRADE"
OLD = ROOT.parent / "BMC_MIDM_FEASIBILITY_FINAL_AUDIT_PACKAGE" / "02_NUMERICAL_EVIDENCE" / "CLAIM_TO_EVIDENCE_FINAL.csv"
T = "results/tables/"

UPDATES = {
    "CL-03": "Supplemented by voxel-level verification (Exp B): Tmax scale ratio 1.000 (certain) vs 1.048 (no ceiling); see CL-36.",
    "CL-05": "Descriptor v1 reports 100/50 of 150; descriptor v2 (arXiv:2408.11142v2) reports 99/50 of 149 = identical to the inference. "
             "No descriptor version reports 100/49 (that figure is the identifier-block split). Manuscript text corrected. See CL-38.",
    "CL-11": "Native-unit fused model vs recovered fused model directly: +0.003 (-0.011 to +0.018) (Exp B).",
    "CL-18": "Admission-time alternative executed (Exp D): NCCT-registered H1 dAUC -0.001 (-0.037 to +0.038). See CL-39.",
    "CL-19": "Robust to the ambiguous centre assignment (Exp C): +0.005 (reassigned), +0.009 (excluded).",
    "CL-29": "A consistent fully nested procedure (Exp A) gives clinical AUC 0.698; procedure contrast vs locked P1 -0.065 (not a pure selection-bias estimate). See CL-34.",
    "CL-30": "Bootstrap-refit (Exp E) shows SD of dAUC 1.7x the fixed-prediction bootstrap. See CL-40.",
}
NEW = [
    ("CL-34", "Results (post hoc)", "Consistent fully nested comparison: clinical 0.698 (0.607-0.783), CTP 0.681 (0.596-0.763), late fusion 0.752 (0.666-0.828); dAUC +0.054 (-0.006 to +0.121), P = 0.08",
     "refitted nested CV on the canonical fold manifest (verified identical)", T + "vA_performance.csv; vA_paired.csv; oof/oof_long_vA.csv", "VERIFIED", "yes", "post hoc sensitivity; CTP branch selected GBM in 48/50 folds"),
    ("CL-35", "Results (post hoc)", "Exp A increment within inferred centres +0.052 (-0.017 to +0.119); native-unit CTP increment +0.023 (-0.033 to +0.086)",
     "centre-stratified bootstrap", T + "vA_within_centre.csv; vA_paired.csv", "VERIFIED", "yes", ""),
    ("CL-36", "Results (post hoc)", "No-ceiling patients (41): Tmax ratio 1.048 (IQR 1.017-1.147); Tmax>6 s volume +6.2 mL (IQR 2.9-27.9) vs -0.1 mL (-1.7 to 1.8) in 85 certain; core 0.0 mL",
     "voxel-level native vs recovered on common grid + feature-level volumes", T + "vB_native_by_ceiling_definition.csv; data/vB_native_per_subject.csv", "VERIFIED_WITH_LIMITATION", "yes",
     "common-grid resampling approximates the release pre-processing (alignment correlation median 0.84); voxel Dice is a lower bound"),
    ("CL-37", "Results (post hoc)", "Native vs recovered features in the fused model: +0.003 (-0.011 to +0.018); in the 44 without certain recovery +0.006 (-0.029 to +0.045)",
     "canonical OOF predictions, identical folds", T + "vB_model_native_vs_recovered_paired.csv", "VERIFIED", "yes", ""),
    ("CL-38", "Methods/Results", "One ambiguous centre assignment (sub-stroke0008); reassignment -> 100/49, within-centre increment +0.005; exclusion +0.009; Munich->Zurich uninformative",
     "patient-level provenance ledger (7 signatures) + M4 re-run", "PATIENT_LEVEL_PROVENANCE_AUDIT.csv; " + T + "vC_site_sensitivity_*.csv", "VERIFIED_WITH_LIMITATION", "yes",
     "exact centre identity not established; inferred-centre terminology kept"),
    ("CL-39", "Results (post hoc)", "Admission-NCCT registration Dice 0.92 vs DWI 0.91 (5 vs 21 < 0.80); location ICC 0.92-0.99; H1 dAUC -0.001 (-0.037 to +0.038); Dice>=0.80 -0.013 (-0.044 to +0.019)",
     "re-registration (SimpleITK) + refitted CV", T + "vD_registration_quality.csv; vD_location_feature_agreement.csv; vD_h1_paired.csv", "VERIFIED", "yes",
     "DWI re-run differs from canonical features by <= 0.036 (registration sampling nondeterminism)"),
    ("CL-40", "Results (post hoc)", "Bootstrap-refit SD of dAUC 0.047 vs fixed-prediction 0.027 (ratio 1.7); 95% width 0.173 vs 0.107",
     "B = 100 grouped bootstrap-refit, budget fixed in advance", T + "vE_bootstrap_refit_summary.csv; vE_bootstrap_refit_draws.csv", "VERIFIED_WITH_LIMITATION", "yes",
     "B = 100 gives imprecise percentile endpoints; refit levels biased low (about 63% unique patients per resample)"),
    ("CL-41", "Results (external technical)", "ISLES 2018 = 94 slabs from 63 patients (31 with 2 slabs); patient used as unit",
     "SMIR object descriptions Train_<patient>_<slab> in the local copy", "data/vX1_isles2018_per_slab.csv", "VERIFIED", "yes", ""),
    ("CL-42", "Results (external technical)", "As distributed, ISLES 2018 CBF/CBV scale differs (medians ~210/~30; 86%/91% above clip); feature completeness 95.4%; side agreement 86%",
     "frozen extractor on unmodified maps", T + "vX1_isles2018_technical.csv; vX1_isles2018_raw_map_ranges.csv", "VERIFIED", "yes", "units of the ISLES 2018 maps UNVERIFIED"),
    ("CL-43", "Results (external technical)", "After label-free rescaling: 0 failures, 100% finite features, side agreement 99%; CTP core vs DWI core Dice 0.21 (0.18-0.24), sens 0.15, precision 0.46, bias -33 mL (LoA -116 to +49), Spearman 0.62",
     "frozen extractor; patient-level bootstrap (63 patients)", T + "vX1_isles2018_core_vs_dwi.csv; data/vX1_isles2018_per_patient.csv", "VERIFIED_WITH_LIMITATION", "yes",
     "early DWI core is not a 90-day outcome; technical component evidence only"),
    ("CL-44", "Methods", "UniToBrain, JHU, CPAISD, AISD not analysed; no independent cohort with CTP and 90-day mRS accessible",
     "dataset audit (primary sources, local CPAISD label audit)", "EXTERNAL_DATASET_COMPATIBILITY_MATRIX.csv; DATA_ACCESS_REQUESTS.md", "VERIFIED", "yes",
     "legacy 'CPAISD brain-mask Dice 0.962' and 'ISLES2024 Zurich AUC 0.9557' results from the older Model F work are invalid and not used"),
    ("CL-45", "Discussion", "The size of the CTP increment depends on how both arms are tuned; no positive conclusion; none of the post hoc analyses is an external prognostic validation",
     "interpretation of CL-34..CL-43", "FINAL_VALIDITY_AUDIT.md", "VERIFIED", "yes", ""),
]

LOGROWS = [
    ("P0", "Baseline snapshot + SHA256", "EXECUTED", "00_BASELINE_SNAPSHOT/SHA256SUMS_BASELINE.txt", "291 files, read-only", "-"),
    ("P1", "Dataset suitability research (primary sources)", "EXECUTED", "EXTERNAL_DATASET_COMPATIBILITY_MATRIX.csv", "9 datasets classified", "-"),
    ("A", "Consistent fully nested clinical vs CTP comparison", "EXECUTED", "vA_nested_consistent.py; vA_within_centre.py", "50 outer folds x 5 feature sets x 39 candidate configs; 7.2 min", "new post hoc"),
    ("B", "Native-unit verification, voxel + feature + model level", "EXECUTED", "vB_native_verification.py", "129 patients; no refitting for model level", "new post hoc"),
    ("C", "Centre provenance ledger + M4 sensitivity", "EXECUTED", "vC_provenance.py", "149 patients, 3 mappings; M4 canonical mapping unchanged", "new post hoc"),
    ("D1", "Fetch admission NCCT (HF mirror of the release, ncct column only)", "EXECUTED", "vD_fetch_ncct.py", "149 subjects, ~14 MB each, 0 failures", "public release already in use"),
    ("D2", "Admission-NCCT atlas registration + DWI re-run", "EXECUTED", "vD_registration.py", "149 subjects, 0 failures", "new post hoc"),
    ("D3", "H1 models with NCCT vs DWI registration", "EXECUTED", "vD_models.py", "full cohort + Dice>=0.80 (n=124)", "new post hoc"),
    ("E", "Bootstrap-refit of the primary comparison", "EXECUTED", "vE_bootstrap_refit.py", "B=100 fixed in advance; 1.8 min", "new post hoc"),
    ("B1", "ISLES 2018 frozen CTP feature/core benchmark", "EXECUTED", "vX1_isles2018_benchmark.py", "94 slabs / 63 patients, two input scalings", "external technical"),
    ("B2", "UniToBrain perfusion transportability", "NOT_EXECUTED_BLOCKED", "-", "50.8 GB single archive; no Tmax map; relative maps", "documented"),
    ("B3", "JHU brain extraction", "NOT_EXECUTED_BLOCKED", "vX3_jhu_brain_extraction.py (prepared)", "HTTP 403 to scripted access; target compatible", "manual download needed"),
    ("B4", "CPAISD / AISD", "SKIPPED_NOT_APPLICABLE", "-", "no matching pipeline output", "-"),
    ("P5", "Full/partial external prognostic validation", "NOT_EXECUTED_NO_DATA", "DATA_ACCESS_REQUESTS.md", "no accessible cohort with CTP + 90-day mRS", "requests drafted, not sent"),
    ("P6", "Manuscript content update", "EXECUTED", "w03_manuscript.py", "22 content changes; abstract 347 words", "formatting untouched"),
]


def main():
    c = pd.read_csv(OLD)
    c["validity_upgrade_update"] = c.claim_id.map(UPDATES).fillna("")
    n = pd.DataFrame(NEW, columns=["claim_id", "section", "claim", "evidence_type", "evidence_files", "status", "in_manuscript_text", "notes"])
    n["ledger_ids"] = "validity-upgrade"; n["validity_upgrade_update"] = "NEW (post hoc, 2026-11-14)"
    out = pd.concat([c, n[c.columns]], ignore_index=True)
    out.to_csv(U / "CLAIM_TO_EVIDENCE_FINAL_UPDATED.csv", index=False)
    pd.DataFrame(LOGROWS, columns=["step", "experiment", "status", "script_or_file", "scope_and_runtime", "note"]) \
        .assign(date="2026-11-14", canonical_outputs_modified="no").to_csv(U / "EXPERIMENT_EXECUTION_LOG.csv", index=False)
    print(len(out), "claims;", out.status.value_counts().to_dict())


if __name__ == "__main__":
    main()
