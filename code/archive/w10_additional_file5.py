"""Build the submission version of Additional file 5 (Tables S21-S42, Figure S8) with descriptive names instead of
internal model codes, readable column headers and values rounded to three decimals. Numbers are read unchanged from
outputs_validity/tables and the validity-upgrade CSVs; nothing is recomputed.
Output: BMC_FINAL_SUBMISSION_STAGING/Additional_file_5_post_hoc_analyses_and_external_benchmark.{xlsx,pdf}
"""
import re

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font

from v_common import VTAB, VDATA, ROOT

U = ROOT.parent / "BMC_FEASIBILITY_VALIDITY_UPGRADE"
OUTD = ROOT.parent / "BMC_FINAL_SUBMISSION_STAGING"
OUTD.mkdir(parents=True, exist_ok=True)
XLSX = OUTD / "Additional_file_5_post_hoc_analyses_and_external_benchmark.xlsx"

MODEL = {
    "A_clin": "Clinical (22 predictors), consistent nested tuning",
    "A_ctp_rec": "CTP (recovered units), consistent nested tuning",
    "A_ctp_nat": "CTP (native units), consistent nested tuning",
    "A_joint_rec": "Clinical + CTP joint model (recovered units), consistent nested tuning",
    "A_joint_nat": "Clinical + CTP joint model (native units), consistent nested tuning",
    "A_late_rec": "Clinical + CTP late fusion (recovered units), consistent nested tuning",
    "A_late_nat": "Clinical + CTP late fusion (native units), consistent nested tuning",
    "canon_E_CTP_all": "CTP, all channels (primary analysis)",
    "canon_F_late_P1_E": "Clinical GBM + CTP late fusion (primary analysis)",
    "canon_P1_locked_GBM": "Clinical GBM, locked configuration (primary analysis)",
    "canon_P1_nested_GBM": "Clinical GBM, nested-tuned configuration",
    "E_CTP_all": "CTP, all channels",
    "E_native": "CTP, all channels (native units)",
    "F_late_P1_E": "Clinical GBM + CTP late fusion",
    "F_late_P1_Enat": "Clinical GBM + CTP late fusion (native units)",
    "F_late_P1_V": "Clinical GBM + CTP absolute volumes, late fusion",
    "P1_clin_GBM": "Clinical GBM",
    "R1_clin_LR4": "Parsimonious logistic model (4 predictors)",
    "F_late_R1_E": "Parsimonious logistic model + CTP late fusion",
    "R1_plus_volumes": "Parsimonious logistic model + CTP volumes (joint)",
    "F_loc_ncct": "Clinical GBM + CTP location (admission-CT registration)",
    "F_loc_dwi": "Clinical GBM + CTP location (DWI registration, repeated)",
    "Loc_CTP_ncct": "CTP location only (admission-CT registration)",
    "Loc_CTP_dwi": "CTP location only (DWI registration, repeated)",
}
TEXT = {
    "Exp A: full cohort (n=129)": "Full cohort (n = 129)",
    "all analysed (n=129)": "Full cohort (n = 129)",
    "full cohort": "Full cohort (n = 129)",
    "NCCT registration Dice >= 0.80": "Admission-CT registration Dice ≥ 0.80",
    "Tmax recovery certain": "Tmax scale reliably recoverable",
    "Tmax recovery uncertain": "Tmax scale not reliably recoverable",
    "ceiling present, degenerate normalisation": "Tmax ceiling present, degenerate normalisation",
    "no Tmax ceiling (n=41 definition)": "No Tmax ceiling",
    "canonical (S1 storage; 99/50 release)": "Primary assignment (storage precision; 99/50)",
    "ambiguous -> ID block (100/49 release)": "Ambiguous patient reassigned by identifier block (100/49)",
    "ambiguous excluded": "Ambiguous patient excluded",
    "Munich -> Zurich": "Developed in Munich, tested in Zurich (inferred centres)",
    "ncct": "Admission non-contrast CT", "dwi": "Follow-up DWI",
    "CST": "Corticospinal tract", "DEEP": "Deep grey matter", "INSOP": "Insula/operculum", "LANG": "Left language cortex",
    "as_distributed": "As distributed", "s03_harmonised": "After label-free median rescaling",
    "P1 AUC": "AUC, clinical GBM", "E_CTP AUC": "AUC, CTP all channels",
    "F_late_P1_E AUC": "AUC, clinical GBM + CTP late fusion", "dAUC F - P1": "ΔAUC, late fusion − clinical GBM",
    "PRIMARY (Exp A): CTP added to clinical, consistent nested tuning, late fusion":
        "Main comparison: CTP added to clinical, consistent nested tuning, late fusion",
    "procedure contrast: consistent nested vs locked clinical GBM (NOT a pure selection-bias estimate)":
        "Procedure contrast: consistent nested vs locked clinical GBM (not a pure estimate of selection optimism)",
    "procedure contrast: consistent nested (EN or GBM) vs GBM-only nested":
        "Procedure contrast: consistent nested (elastic net or GBM) vs GBM-only nested",
    "procedure contrast: fused model, consistent nested vs primary": "Procedure contrast: fused model, consistent nested vs primary analysis",
    "clinical + native CTP vs clinical + recovered CTP (primary)": "Clinical + native-unit CTP vs clinical + recovered-unit CTP",
    "recovered CTP added to clinical (primary H0)": "Recovered-unit CTP added to clinical (primary comparison)",
    "H1 at admission time: NCCT-registered location added to P1": "Location (admission-CT registration) added to clinical GBM",
    "H1 as canonical: DWI-registered location added to P1 (re-run)": "Location (DWI registration, repeated) added to clinical GBM",
    "NCCT vs DWI registration, fused model": "Admission-CT vs DWI registration, fused model",
    "NCCT vs DWI registration, location only": "Admission-CT vs DWI registration, location only",
}
METRIC = {
    "align_corr_tmax": "Alignment correlation, Tmax (common grid)", "tmax_mae_s": "Tmax mean absolute error (s)",
    "tmax_median_abs_err_s": "Tmax median absolute error (s)", "tmax_bias_s": "Tmax bias (s)",
    "tmax_scale_ratio_median": "Tmax scale ratio, recovered/native", "dice_tmax4": "Dice, Tmax > 4 s mask",
    "dice_tmax6": "Dice, Tmax > 6 s mask", "dice_tmax8": "Dice, Tmax > 8 s mask", "dice_tmax10": "Dice, Tmax > 10 s mask",
    "disagree_frac_tmax4": "Disagreement fraction, Tmax > 4 s", "disagree_frac_tmax6": "Disagreement fraction, Tmax > 6 s",
    "disagree_frac_tmax8": "Disagreement fraction, Tmax > 8 s", "disagree_frac_tmax10": "Disagreement fraction, Tmax > 10 s",
    "core_ml_diff": "Core volume, recovered − native (mL)", "hypoperf_tmax6_ml_diff": "Tmax > 6 s volume, recovered − native (mL)",
    "mismatch_ml_diff": "Mismatch volume, recovered − native (mL)",
    "dice_mean": "Dice, mean", "dice_median": "Dice, median", "sensitivity_mean": "Sensitivity, mean",
    "precision_mean": "Precision, mean", "vol_bias_ml": "Volume bias, CTP − DWI (mL)",
    "vol_abs_err_ml_median": "Absolute volume error, median (mL)", "spearman_core_vs_dwi": "Spearman correlation, CTP vs DWI core volume",
    "ccc_core_vs_dwi_ml": "Concordance correlation coefficient, core volume", "dwi_core_covered_by_tmax6_median": "Fraction of DWI core inside Tmax > 6 s, median",
    "bland_altman_loa_ml": "Bland–Altman mean difference (CI columns: 95% limits of agreement, mL)",
}
for ch in ("CBF", "CBV", "MTT", "Tmax"):
    METRIC.update({f"raw_{ch}_median": f"{ch}, brain median (distributed units)", f"raw_{ch}_p99": f"{ch}, brain 99th percentile",
                   f"raw_{ch}_above_clip": f"{ch}, fraction of brain voxels above the ISLES'24 clip limit"})
COLS = {
    "analysis": "Analysis", "model": "Model", "n": "Patients", "events": "Poor outcomes", "auc_seed_mean": "AUC (mean of 5 seeds)",
    "auc_seed_sd": "Between-seed SD", "auc_ci_lo": "95% CI lower", "auc_ci_hi": "95% CI upper", "brier_seed_mean": "Brier score",
    "cal_slope_pooled": "Calibration slope", "cal_citl_pooled": "Calibration-in-the-large", "brier_pooled": "Brier score (seed-averaged probabilities)",
    "n_folds_selected_EN": "Outer folds selecting elastic net", "n_folds_selected_GBM": "Outer folds selecting GBM",
    "mean_fold_train_auc": "Mean training-fold AUC", "mean_fold_test_auc": "Mean test-fold AUC",
    "new": "Model", "reference": "Reference", "role": "Comparison", "delta_auc": "ΔAUC", "ci_lo": "95% CI lower", "ci_hi": "95% CI upper",
    "p_bootstrap": "Bootstrap P", "within_centre_auc": "Within-centre AUC", "within_lo": "95% CI lower", "within_hi": "95% CI upper",
    "metric": "Metric", "qc3": "Tmax recovery status", "mapping": "Centre assignment", "n_zurich": "Patients, Zurich", "events_zurich": "Poor outcomes, Zurich",
    "direction": "Direction", "registration": "Registration target", "dice_vs_ncct_ic_median": "Dice with CT intracranial mask, median",
    "q1": "Q1", "q3": "Q3", "n_dice_lt_0.80": "Registrations with Dice < 0.80", "region": "Atlas region", "icc31": "ICC(3,1)",
    "spearman": "Spearman correlation", "median_abs_diff": "Median absolute difference", "atlas_concordance_dice_median": "Atlas-region Dice, median",
    "quantity": "Quantity", "canonical_estimate": "Estimate (primary analysis)", "fixed_pred_boot_lo": "Fixed-prediction bootstrap, 2.5%",
    "fixed_pred_boot_hi": "Fixed-prediction bootstrap, 97.5%", "fixed_pred_boot_width": "Fixed-prediction bootstrap, 95% width",
    "fixed_pred_boot_sd": "Fixed-prediction bootstrap, SD", "refit_boot_B": "Refit resamples (B)", "refit_boot_mean": "Bootstrap-refit, mean",
    "refit_boot_lo": "Bootstrap-refit, 2.5%", "refit_boot_hi": "Bootstrap-refit, 97.5%", "refit_boot_width": "Bootstrap-refit, 95% width",
    "refit_boot_sd": "Bootstrap-refit, SD", "sd_ratio_refit_over_fixed": "SD ratio, refit/fixed", "between_seed_sd_canonical": "Between-seed SD (primary analysis)",
    "scaling": "Input scaling", "slabs": "CTP slabs", "patients": "Patients", "technical_failures_slabs": "Slabs with technical failure",
    "slabs_with_any_nonfinite_feature": "Slabs with any non-finite feature", "feature_completeness_pct": "Feature completeness (%)",
    "tmax_volume_monotonicity_pct": "Tmax-threshold volumes monotone (%)", "core_threshold_monotonicity_pct": "Core-threshold volumes monotone (%)",
    "ipsilateral_side_agrees_with_dwi_pct": "Ipsilateral side agrees with DWI lesion (%)", "mirror_dice_median": "Hemisphere mirror Dice, median",
    "n_patients": "Patients", "n_slabs": "CTP slabs", "estimate": "Estimate", "Unnamed: 0": "Quantity (per slab)", "count": "Slabs",
    "mean": "Mean", "std": "SD", "min": "Minimum", "25%": "25th percentile", "50%": "Median", "75%": "75th percentile", "max": "Maximum",
    "mw_p_certain_vs_uncertain": "Mann–Whitney P, recoverable vs not",
    # repair tables (S38-S42)
    "two_slab_patients": "Patients with two slabs", "analysable_pairs": "Slab pairs analysed",
    "header_geometry_usable": "Slice position available from headers",
    "patients_with_duplicated_slices_adjacency": "Patients with a duplicated slice location (adjacency criterion)",
    "duplicated_slices_adjacency_total": "Duplicated slice locations (adjacency criterion)",
    "patients_with_duplicated_slices_strict": "Patients with a duplicated slice location (strict criterion)",
    "duplicated_slices_strict_total": "Duplicated slice locations (strict criterion)",
    "slices_in_two_slab_patients": "Slices in two-slab patients",
    "ot_slice_dice_median_duplicated_pairs": "Reference-mask slice Dice at duplicated pairs, median",
    "ot_slice_dice_median_other_matched_pairs": "Reference-mask slice Dice at other matched pairs, median",
    "source": "Source", "training_n": "Training cases", "centre_1_munich": "Centre 1 (Munich)", "centre_2_zurich": "Centre 2 (Zurich)",
    "subject_level_list": "Subject-level centre list", "status": "Status",
    "signature": "Signature", "value_sub_stroke0008": "Value, sub-stroke0008", "munich_like_median": "Median, Munich-like cluster",
    "zurich_like_median": "Median, Zurich-like cluster", "share_munich_like_with_same_value": "Share of Munich-like cluster with the same value",
    "share_zurich_like_with_same_value": "Share of Zurich-like cluster with the same value", "closer_to": "Closer to",
    "interpretation": "Interpretation", "cluster": "Cluster", "median": "Median", "p05": "5th percentile", "p95": "95th percentile",
}
SIGNAME = {"S3_ncct_slice_mm": "NCCT slice thickness (mm)", "S4_inplane_mm": "NCCT in-plane spacing (mm)",
           "S5_ctp_slab_mm": "CTP slab coverage (mm)", "S10_ctp_slices": "CTP slices",
           "S8_n_imputed_of_4": "Release-level median imputations among leucocytes, CRP, INR, onset-to-door (0–4)",
           "S9_nihss24h_recorded": "24-h NIHSS recorded (1 = yes)",
           "S1 storage precision (primary mapping)": "Storage precision of perfusion maps (primary mapping)",
           "S2 subject-ID block": "Subject-identifier block"}
VARIANT = {" | slab_summed (original)": " | slab-summed (as in Table S34)",
           " | dedup_adjacency_keepA (primary)": " | de-duplicated, adjacency criterion, slab A kept (primary)",
           " | dedup_adjacency_keepB": " | de-duplicated, adjacency criterion, slab B kept",
           " | dedup_strict_keepA": " | de-duplicated, strict criterion, slab A kept"}
for reg in ("CST", "DEEP", "INSOP", "LANG"):
    COLS[f"coverage_{reg}_median"] = f"{TEXT[reg]} coverage, median"
    COLS[f"missing_{reg}"] = f"{TEXT[reg]}: missing"


def label(v):
    if not isinstance(v, str):
        return v
    if v in TEXT:
        return TEXT[v]
    if v in MODEL:
        return MODEL[v]
    if v in METRIC:
        return METRIC[v]
    if v in SIGNAME:
        return SIGNAME[v]
    for k_old, k_new in VARIANT.items():
        if v.endswith(k_old):
            return label(v[: -len(k_old)]) + k_new
    m = re.match(r"delta (\S+) - (\S+)$", v)
    if m:
        return f"ΔAUC: {MODEL.get(m[1], m[1])} − {MODEL.get(m[2], m[2])}"
    m = re.match(r"(as_distributed|s03_harmonised): (.*)$", v)
    if m:
        rest = re.sub(r"protocol matrix(\d+)_dz([\d.]+)", lambda k: f"protocol: matrix {k[1]}, slice {float(k[2]):g} mm", m[2])
        return f"{TEXT[m[1]]}: {rest}"
    return v


def colname(c):
    if c in COLS:
        return COLS[c]
    for k_old, k_new in (("Tmax recovery certain__", "Tmax recoverable: "), ("Tmax recovery uncertain__", "Tmax not recoverable: "), ("all__", "All: ")):
        if c.startswith(k_old):
            stat = c[len(k_old):]
            return k_new + {"n": "n", "median": "median", "q1": "Q1", "q3": "Q3", "mean": "mean", "loa_lo": "lower 95% LoA", "loa_hi": "upper 95% LoA"}[stat]
    m = re.match(r"(.+)__(median|q1|q3)$", c)
    if m:
        return f"{METRIC.get(m[1], m[1])}: {'median' if m[2] == 'median' else m[2].upper()}"
    return c


def clean(df):
    df = df.copy()
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].map(label)
        elif np.issubdtype(df[c].dtype, np.floating):
            df[c] = df[c].round(3)
    return df.rename(columns={c: colname(c) for c in df.columns})


def compat():
    a = pd.read_csv(U / "EXTERNAL_DATASET_COMPATIBILITY_MATRIX.csv")
    keep = {"dataset": "Dataset", "official_source": "Source", "independent_patients": "Independent patients", "scans_or_slabs": "Scans or slabs",
            "modalities": "Modalities", "ctp_maps_and_units": "CTP maps and units", "mrs_90d_available": "90-day mRS",
            "imaging_ground_truth_type": "Reference standard", "anatomical_target_definition": "Target definition", "license": "Licence",
            "access_class": "Access", "compatible_component": "Compatible pipeline component", "scientific_status": "Status", "status_reason": "Reason"}
    a = a[list(keep)].rename(columns=keep)
    a["Status"] = a["Status"].str.replace("_", " ").str.capitalize()
    a = a.replace({r"frozen ": "", r"\(frozen\)": "(unchanged)", r"\bR1 clinical model": "Parsimonious clinical model",
                   r"\bR1 clinical": "Parsimonious clinical"}, regex=True)
    return a


def provenance():
    b = pd.read_csv(U / "PATIENT_LEVEL_PROVENANCE_AUDIT.csv").drop(columns=["hf_shard", "S1_vote", "S2_vote", "S3_vote"])
    ren = {"subject_id": "Subject", "idnum": "Identifier number", "S1_quantised_share": "Share of map values quantised to 1/64",
           "S1_cluster": "Storage cluster", "S2_id_block": "Identifier block", "S3_ncct_slice_mm": "NCCT slice thickness (mm)",
           "S4_inplane_mm": "NCCT in-plane spacing (mm)", "S5_ctp_slab_mm": "CTP slab coverage (mm)", "S6_descrip": "NIfTI description field",
           "S7_tmax_min": "Minimum stored Tmax", "n_slices": "CTP slices", "canonical_site_inferred": "Inferred centre",
           "S1_S2_agree": "Storage and identifier block agree", "n_votes_zurich": "Signatures indicating Zurich", "certainty": "Assignment",
           "in_analysed_cohort_129": "In analysed cohort", "exclusion_reason": "Exclusion reason", "poor_outcome": "Poor outcome (mRS 3–6)",
           "exact_centre_identity": "Exact centre identity"}
    return b.rename(columns=ren)


SHEETS = [
    ("vA_performance", "Consistent fully nested comparison: discrimination and calibration"),
    ("vA_paired", "Consistent fully nested comparison: paired differences in AUC"),
    ("vA_within_centre", "Consistent fully nested comparison: within-centre AUC (centre-stratified bootstrap)"),
    ("vB_native_voxel_feature_agreement_by_qc", "Recovered versus native Tmax: voxel- and volume-level agreement by Tmax recovery status (median, IQR; mean and 95% limits of agreement). "
     "Voxel measures use an approximate common grid (native maps resampled to the release grid and oriented by the axis-flip combination with the highest "
     "Tmax correlation; median alignment correlation 0.84); they combine recovery error with residual misalignment and are not bounds on either"),
    ("vB_native_by_ceiling_definition", "Recovered versus native Tmax: summary by Tmax-ceiling status (median, Q1, Q3; approximate common grid as in Table S24)"),
    ("vB_model_native_vs_recovered_paired", "Native-unit versus recovered-unit CTP features: paired differences in AUC (same out-of-fold folds, no refitting)"),
    ("vC_site_sensitivity_within_centre", "Centre-assignment sensitivity: within-centre AUC"),
    ("vC_site_sensitivity_geographic_paired", "Centre-assignment sensitivity: models developed in Munich and tested in Zurich (inferred centres; 5–6 events, uninformative)"),
    ("vD_registration_quality", "Atlas registration to the admission CT versus the follow-up DWI: registration quality and region coverage. Dice is computed "
     "against an automatically derived CT intracranial mask (−20 to 100 HU enclosed by the skull); it is a consistency check, not agreement with expert manual segmentation"),
    ("vD_location_feature_agreement", "Agreement of regional location features between registration targets"),
    ("vD_h1_paired", "Location hypothesis with admission-time registration: paired differences in AUC"),
    ("vE_bootstrap_refit_summary", "Exploratory bootstrap-refit versus fixed-prediction bootstrap of the primary comparison. B = 100 resamples, "
     "each with about 63% unique patients (range 57–69%) and one 10-fold cross-validation. Refit AUCs are lower on average, consistent with smaller "
     "effective training sets. Because this design differs from the primary analysis, the larger refit SD describes variability under that design; it "
     "does not calibrate the fixed-prediction intervals or establish the direction or size of any bias in the sample-size estimates"),
    ("vX1_isles2018_technical", "ISLES 2018 (94 slabs, 63 patients): technical execution of the unchanged CTP feature extractor (not anatomical accuracy)"),
    ("vX1_isles2018_core_vs_dwi", "ISLES 2018: CTP core versus expert DWI core, slab-summed estimates (voxel counts summed over a patient's slabs "
     "without removing overlapping slices; patient-level bootstrap; patient = unit of analysis). De-duplicated estimates: Table S39"),
    ("vX1_isles2018_raw_map_ranges", "ISLES 2018: distribution of perfusion map values as distributed"),
    ("COMPAT", "External datasets considered for technical benchmarking or validation"),
    ("PROV", "Patient-level provenance signatures and inferred centre (149 released cases)"),
    ("vX1b_slab_overlap_summary", "ISLES 2018: overlap of the two CTP slabs in the 31 patients with two slabs. NIfTI headers (identity affine) and JSON "
     "sidecars carry no slice position, so overlap was estimated from image similarity and could not be verified from physical slice positions: a "
     "slice pair counts as a duplicated location when its normalised "
     "cross-correlation, after in-plane alignment, exceeds that of each slice with its neighbours in its own slab (adjacency criterion) or is ≥ 0.95 "
     "(strict criterion). Reference masks were not used for detection; their slice Dice is shown as a plausibility check"),
    ("vX1b_isles2018_core_vs_dwi_dedup", "ISLES 2018: CTP core versus expert DWI core with overlapping slab slices counted once (primary: adjacency "
     "criterion, duplicated slices removed from slab B), with the slab-summed estimates and two alternative de-duplication rules for comparison. "
     "Sub-slice overlap cannot be resolved, so all values are estimates"),
    ("vC2_centre_count_sources", "ISLES'24 training-set centre counts by source. No source provides a subject-level centre list"),
    ("vC2_ambiguous_case_signatures", "The one patient with discordant storage and identifier signatures (sub-stroke0008): additional outcome-independent "
     "case-level signatures relative to the 148 patients whose two signatures agree (consistency only; centre identity not verified)"),
    ("vC2_signature_by_cluster", "Distribution of the case-level provenance signatures in the two concordant clusters"),
]


def write_xlsx():
    contents = []
    with pd.ExcelWriter(XLSX, engine="openpyxl") as xw:
        pd.DataFrame().to_excel(xw, sheet_name="Contents")
        for i, (src, title) in enumerate(SHEETS, 21):
            df = compat() if src == "COMPAT" else provenance() if src == "PROV" else clean(pd.read_csv(VTAB / f"{src}.csv"))
            sh = f"Table S{i}"
            df.to_excel(xw, sheet_name=sh, index=False, startrow=2)
            contents.append((sh, title))
    wb = load_workbook(XLSX)
    for sh, title in contents:
        ws = wb[sh]
        ws["A1"] = f"{sh}. {title}"
        ws["A1"].font = Font(bold=True)
        for c in ws[3]:
            c.font = Font(bold=True)
            c.alignment = Alignment(wrap_text=True, vertical="top")
        for col in ws.columns:
            w = max(len(str(c.value)) if c.value is not None and c.row > 2 else 0 for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max(10, w * 0.9), 60)
    ws = wb["Contents"]
    ws.delete_rows(1, ws.max_row)
    ws["A1"] = "Additional file 5. Post hoc sensitivity analyses and external technical component benchmarking"
    ws["A1"].font = Font(bold=True)
    ws["A2"] = ("All analyses in this file were performed after the primary results were known and are post hoc. "
                "AUC: mean of five seed-specific out-of-fold AUCs; 95% CIs from 2,000 patient-level bootstrap resamples unless stated otherwise. "
                "Late fusion: equal-weight average of the clinical and CTP probabilities. Outcome: mRS 3–6 at 90 days.")
    ws["A2"].alignment = Alignment(wrap_text=True)
    ws.merge_cells("A2:B2")
    ws.row_dimensions[2].height = 60
    ws["A4"], ws["B4"] = "Sheet", "Content"
    ws["A4"].font = ws["B4"].font = Font(bold=True)
    for r, (sh, title) in enumerate(contents, 5):
        ws.cell(r, 1, sh)
        ws.cell(r, 2, title)
    r += 1
    ws.cell(r + 1, 1, "Figure S8").font = Font(bold=True)
    ws.cell(r + 1, 2, "Post hoc analyses and ISLES 2018 benchmark (separate PDF/PNG file).")
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 14, 120
    wb.move_sheet("Contents", offset=-len(wb.sheetnames))
    wb.save(XLSX)
    return contents


def figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 2, figsize=(10, 8))
    Ac = pd.read_csv(VTAB / "vA_paired.csv").iloc[:7][::-1]
    short = {"A_late_rec": "Fusion (rec.)", "A_joint_rec": "Joint (rec.)", "A_ctp_rec": "CTP (rec.)", "A_late_nat": "Fusion (nat.)",
             "A_joint_nat": "Joint (nat.)", "A_ctp_nat": "CTP (nat.)", "A_clin": "Clinical"}
    a = ax[0, 0]
    a.errorbar(Ac.delta_auc, range(len(Ac)), xerr=[Ac.delta_auc - Ac.ci_lo, Ac.ci_hi - Ac.delta_auc], fmt="o", color="#2a78d6", capsize=3)
    a.set_yticks(range(len(Ac)))
    a.set_yticklabels([f"{short.get(n, n)} vs {short.get(r, r)}" for n, r in zip(Ac.new, Ac.reference)], fontsize=7)
    a.axvline(0, color="grey", lw=0.8); a.set_xlabel("ΔAUC (95% CI)")
    a.set_title("(a) Consistent fully nested comparison", loc="left", fontsize=9)
    B = pd.read_csv(VDATA / "vB_native_per_subject.csv")
    grp = np.select([B.qc_Tmax_n_at_ceiling < 2, B.qc_degenerate_norm.astype(bool)], ["no ceiling (41)", "degenerate (3)"], "recoverable (85)")
    b = ax[0, 1]
    labs = ["recoverable (85)", "degenerate (3)", "no ceiling (41)"]
    b.boxplot([B.hypoperf_tmax6_ml_diff[grp == g] for g in labs], tick_labels=labs, showfliers=True)
    b.axhline(0, color="grey", lw=0.8); b.set_ylabel("Tmax > 6 s volume, recovered − native (mL)")
    b.set_title("(b) Recovered vs native Tmax by recovery status", loc="left", fontsize=9)
    P = pd.read_csv(VDATA / "vX1_isles2018_per_patient.csv"); P = P[P.scaling == "s03_harmonised"]
    c = ax[1, 0]
    m, d = (P.core_ml + P.ot_ml) / 2, P.core_ml - P.ot_ml
    c.scatter(m, d, s=12, color="#1baf7a")
    for v, ls in ((d.mean(), "-"), (d.mean() - 1.96 * d.std(), "--"), (d.mean() + 1.96 * d.std(), "--")):
        c.axhline(v, color="grey", ls=ls, lw=0.8)
    c.set_xlabel("Mean of CTP core and DWI core (mL)"); c.set_ylabel("CTP core − DWI core (mL)")
    c.set_title("(c) ISLES 2018: CTP core vs DWI core (63 patients, slab-summed)", loc="left", fontsize=9)
    E = pd.read_csv(VTAB / "vE_bootstrap_refit_draws.csv")
    e = ax[1, 1]
    e.hist(E.dauc_F_minus_P1, bins=20, color="#eda100", alpha=0.8, label="bootstrap-refit (B = 100)")
    S = pd.read_csv(VTAB / "vE_bootstrap_refit_summary.csv").set_index("quantity").loc["dAUC F - P1"]
    e.axvspan(S.fixed_pred_boot_lo, S.fixed_pred_boot_hi, color="#2a78d6", alpha=0.15, label="fixed-prediction 95% CI")
    e.axvline(S.canonical_estimate, color="#2a78d6"); e.set_xlabel("ΔAUC (CTP late fusion − clinical GBM)"); e.legend(fontsize=7)
    e.set_title("(d) Exploratory bootstrap-refit vs fixed-prediction bootstrap", loc="left", fontsize=9)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUTD / f"Additional_file_5_Figure_S8.{ext}", dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    cs = write_xlsx(); figure()
    # leftover internal codes check
    wb = load_workbook(XLSX)
    bad = re.compile(r"\b(P1|R1|Exp [A-E]|canon\w*|frozen|A_clin|A_late|F_late|E_CTP)\b")
    hits = [(ws.title, c.coordinate, c.value) for ws in wb for row in ws.iter_rows() for c in row
            if isinstance(c.value, str) and bad.search(c.value)]
    print(len(cs), "tables; leftover code hits:", hits[:20])
