"""Collect the validity-upgrade results into the handover tables and a supplementary figure.
Writes to BMC_FEASIBILITY_VALIDITY_UPGRADE/: INTERNAL_VALIDITY_RESULTS.csv, EXTERNAL_COMPONENT_BENCHMARK_RESULTS.csv,
PATIENT_LEVEL_PROVENANCE_AUDIT.csv, and supplementary/FigS8_validity_upgrade.{png,pdf}, supplementary/Supplementary_tables_validity_upgrade.xlsx
"""
import json
import numpy as np
import pandas as pd
from v_common import VTAB, VDATA, ROOT

U = ROOT.parent / "BMC_FEASIBILITY_VALIDITY_UPGRADE"
SUP = U / "supplementary"
SUP.mkdir(parents=True, exist_ok=True)


def internal():
    rows = []

    def add(exp, analysis, quantity, est, lo, hi, n, events, p=np.nan, src="", note=""):
        rows.append({"experiment": exp, "analysis": analysis, "quantity": quantity, "estimate": est, "ci_lo": lo, "ci_hi": hi,
                     "n_patients": n, "events": events, "p_bootstrap": p, "source_table": src, "interpretation_note": note})
    A = pd.read_csv(VTAB / "vA_performance.csv"); Ac = pd.read_csv(VTAB / "vA_paired.csv")
    for _, r in A.iterrows():
        add("A", "consistent fully nested tuning (EN or GBM selected by inner log-loss)", f"AUC {r.model}", r.auc_seed_mean, r.auc_ci_lo, r.auc_ci_hi,
            r.n, r.events, src="vA_performance.csv", note=f"calibration slope {r.cal_slope_pooled:.2f}; Brier {r.brier_seed_mean:.3f}")
    for _, r in Ac.iterrows():
        add("A", r.role, f"dAUC {r.new} - {r.reference}", r.delta_auc, r.ci_lo, r.ci_hi, r.n, r.events, r.p_bootstrap, "vA_paired.csv")
    Aw = pd.read_csv(VTAB / "vA_within_centre.csv")
    for _, r in Aw.iterrows():
        add("A", "within inferred centre (centre-stratified bootstrap)", f"within-centre AUC {r.model}", r.within_centre_auc, r.ci_lo, r.ci_hi,
            129, 44, r.get("p_bootstrap", np.nan), "vA_within_centre.csv")
    Bp = pd.read_csv(VTAB / "vB_model_native_vs_recovered_paired.csv")
    for _, r in Bp.iterrows():
        add("B", f"{r.analysis}: {r.role}", f"dAUC {r.new} - {r.reference}", r.delta_auc, r.ci_lo, r.ci_hi, r.n, r.events, r.p_bootstrap,
            "vB_model_native_vs_recovered_paired.csv", "canonical OOF predictions, identical folds, no refitting")
    Bc = pd.read_csv(VTAB / "vB_native_by_ceiling_definition.csv", index_col=0)
    for st, r in Bc.iterrows():
        for c in ("tmax_scale_ratio_median", "tmax_median_abs_err_s", "dice_tmax6", "hypoperf_tmax6_ml_diff", "core_ml_diff", "mismatch_ml_diff"):
            add("B", f"voxel/feature agreement, stratum: {st}", f"{c} (median [IQR])", r[f"{c}__median"], r[f"{c}__q1"], r[f"{c}__q3"], int(r.n), np.nan,
                src="vB_native_by_ceiling_definition.csv", note="CI columns hold Q1 and Q3 for this row")
    W = pd.read_csv(VTAB / "vC_site_sensitivity_within_centre.csv")
    for _, r in W.iterrows():
        add("C", f"within-centre AUC, mapping: {r.mapping}", r.model, r.within_centre_auc, r.within_lo, r.within_hi, r.n, np.nan, src="vC_site_sensitivity_within_centre.csv")
    G = pd.read_csv(VTAB / "vC_site_sensitivity_geographic_paired.csv")
    for _, r in G.iterrows():
        add("C", f"Munich -> Zurich (inferred), mapping: {r.mapping}", f"dAUC {r.new} - {r.reference}", r.delta_auc, r.ci_lo, r.ci_hi, np.nan, np.nan,
            r.p_bootstrap, "vC_site_sensitivity_geographic_paired.csv", "5-6 external events: uninformative")
    if (VTAB / "vD_h1_paired.csv").exists():
        D = pd.read_csv(VTAB / "vD_h1_paired.csv")
        for _, r in D.iterrows():
            add("D", f"{r.analysis}: {r.role}", f"dAUC {r.new} - {r.reference}", r.delta_auc, r.ci_lo, r.ci_hi, r.n, r.events, r.p_bootstrap, "vD_h1_paired.csv")
        Q = pd.read_csv(VTAB / "vD_registration_quality.csv")
        for _, r in Q.iterrows():
            add("D", f"registration target: {r.registration}", "Dice(warped MNI brain, NCCT intracranial mask), median [IQR]",
                r.dice_vs_ncct_ic_median, r.q1, r.q3, r.n, np.nan, src="vD_registration_quality.csv", note=f"Dice<0.80: {r['n_dice_lt_0.80']}")
        Ag = pd.read_csv(VTAB / "vD_location_feature_agreement.csv")
        for _, r in Ag.iterrows():
            add("D", "NCCT- vs DWI-registered location feature", f"ICC(3,1) {r.region}", r.icc31, np.nan, np.nan, r.n, np.nan,
                src="vD_location_feature_agreement.csv", note=f"Spearman {r.spearman:.2f}; atlas concordance Dice {r.atlas_concordance_dice_median:.2f}")
    E = pd.read_csv(VTAB / "vE_bootstrap_refit_summary.csv")
    for _, r in E.iterrows():
        add("E", "fixed-prediction patient bootstrap (canonical)", r.quantity, r.canonical_estimate, r.fixed_pred_boot_lo, r.fixed_pred_boot_hi, 129, 44,
            src="vE_bootstrap_refit_summary.csv", note=f"SD {r.fixed_pred_boot_sd:.4f}")
        add("E", "bootstrap-refit of the whole procedure (B=100, grouped 10-fold)", r.quantity, r.refit_boot_mean, r.refit_boot_lo, r.refit_boot_hi, 129, 44,
            src="vE_bootstrap_refit_summary.csv", note=f"SD {r.refit_boot_sd:.4f}; SD ratio refit/fixed {r.sd_ratio_refit_over_fixed:.2f}; level biased low (bootstrap samples contain ~63% unique patients)")
    out = pd.DataFrame(rows)
    out.to_csv(U / "INTERNAL_VALIDITY_RESULTS.csv", index=False)
    return out


def external():
    rows = []
    T = pd.read_csv(VTAB / "vX1_isles2018_technical.csv")
    for _, r in T.iterrows():
        for k in ("technical_failures_slabs", "slabs_with_any_nonfinite_feature", "feature_completeness_pct", "tmax_volume_monotonicity_pct",
                  "core_threshold_monotonicity_pct", "ipsilateral_side_agrees_with_dwi_pct", "mirror_dice_median"):
            rows.append({"benchmark": "B1 ISLES 2018", "status": "EXECUTED", "input_scaling": r.scaling, "stratum": "all", "metric": k, "estimate": r[k],
                         "ci_lo": np.nan, "ci_hi": np.nan, "n_patients": r.patients, "n_slabs": r.slabs, "reference_semantics": "technical (no reference label)",
                         "note": "monotonicity is a sanity check, not evidence of accuracy" if "monoton" in k else ""})
    R = pd.read_csv(VTAB / "vX1_isles2018_core_vs_dwi.csv")
    for _, r in R.iterrows():
        sc, st = r.analysis.split(": ", 1)
        rows.append({"benchmark": "B1 ISLES 2018", "status": "EXECUTED", "input_scaling": sc, "stratum": st, "metric": r.metric, "estimate": r.estimate,
                     "ci_lo": r.ci_lo, "ci_hi": r.ci_hi, "n_patients": r.n_patients, "n_slabs": r.n_slabs,
                     "reference_semantics": "expert manual DWI infarct core, DWI within 3 h of CTP (early core, not 90-day outcome)",
                     "note": "Bland-Altman row: estimate = mean difference, CI columns = 95% limits of agreement" if "loa" in r.metric else
                     "patient-level bootstrap (63 patients); voxels never treated as independent"})
    for b, st, why in (("B2 UniToBrain", "NOT_EXECUTED_BLOCKED", "50.8 GB single archive; no Tmax map; relative maps from different software"),
                       ("B3 JHU head CT masks", "NOT_EXECUTED_BLOCKED", "target compatible (intracranial incl. CSF) but repository refuses scripted download (HTTP 403); script vX3 prepared"),
                       ("B4a CPAISD", "SKIPPED_NOT_APPLICABLE", "no pipeline output matching NCCT core/penumbra; no brain-mask reference exists in CPAISD"),
                       ("B4b AISD", "SKIPPED_NOT_APPLICABLE", "no pipeline output matching NCCT lesion segmentation")):
        rows.append({"benchmark": b, "status": st, "metric": "none", "note": why})
    out = pd.DataFrame(rows)
    out.to_csv(U / "EXTERNAL_COMPONENT_BENCHMARK_RESULTS.csv", index=False)
    return out


def provenance():
    L = pd.read_csv(VDATA / "patient_provenance_ledger.csv")
    L.to_csv(U / "PATIENT_LEVEL_PROVENANCE_AUDIT.csv", index=False)
    return L


def figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 2, figsize=(10, 8))
    # (a) Exp A paired dAUC
    Ac = pd.read_csv(VTAB / "vA_paired.csv").iloc[:7][::-1]
    a = ax[0, 0]
    a.errorbar(Ac.delta_auc, range(len(Ac)), xerr=[Ac.delta_auc - Ac.ci_lo, Ac.ci_hi - Ac.delta_auc], fmt="o", color="#2a78d6", capsize=3)
    a.set_yticks(range(len(Ac))); a.set_yticklabels([f"{n} vs {r}" for n, r in zip(Ac.new, Ac.reference)], fontsize=7)
    a.axvline(0, color="grey", lw=0.8); a.set_xlabel("ΔAUC (95% CI)"); a.set_title("(a) Exp A: consistent fully nested tuning", loc="left", fontsize=9)
    # (b) Exp B Tmax scale ratio by stratum
    B = pd.read_csv(VDATA / "vB_native_per_subject.csv")
    grp = np.select([B.qc_Tmax_n_at_ceiling < 2, B.qc_degenerate_norm.astype(bool)], ["no ceiling (41)", "degenerate (3)"], "certain (85)")
    b = ax[0, 1]
    labs = ["certain (85)", "degenerate (3)", "no ceiling (41)"]
    b.boxplot([B.hypoperf_tmax6_ml_diff[grp == g] for g in labs], tick_labels=labs, showfliers=True)
    b.axhline(0, color="grey", lw=0.8); b.set_ylabel("Tmax>6 s volume, recovered − native (mL)")
    b.set_title("(b) Exp B: native-unit verification by recovery QC", loc="left", fontsize=9)
    # (c) ISLES 2018 Bland-Altman (harmonised)
    P = pd.read_csv(VDATA / "vX1_isles2018_per_patient.csv"); P = P[P.scaling == "s03_harmonised"]
    c = ax[1, 0]
    m, d = (P.core_ml + P.ot_ml) / 2, P.core_ml - P.ot_ml
    c.scatter(m, d, s=12, color="#1baf7a")
    for v, ls in ((d.mean(), "-"), (d.mean() - 1.96 * d.std(), "--"), (d.mean() + 1.96 * d.std(), "--")):
        c.axhline(v, color="grey", ls=ls, lw=0.8)
    c.set_xlabel("mean of CTP core and DWI core (mL)"); c.set_ylabel("CTP core − DWI core (mL)")
    c.set_title("(c) ISLES 2018: frozen CTP core vs DWI core (63 patients)", loc="left", fontsize=9)
    # (d) Exp E
    E = pd.read_csv(VTAB / "vE_bootstrap_refit_draws.csv")
    e = ax[1, 1]
    e.hist(E.dauc_F_minus_P1, bins=20, color="#eda100", alpha=0.8, label="bootstrap-refit (B=100)")
    S = pd.read_csv(VTAB / "vE_bootstrap_refit_summary.csv").set_index("quantity").loc["dAUC F - P1"]
    e.axvspan(S.fixed_pred_boot_lo, S.fixed_pred_boot_hi, color="#2a78d6", alpha=0.15, label="fixed-prediction 95% CI")
    e.axvline(S.canonical_estimate, color="#2a78d6"); e.set_xlabel("ΔAUC (CTP fusion − clinical GBM)"); e.legend(fontsize=7)
    e.set_title("(d) Exp E: refit vs fixed-prediction bootstrap", loc="left", fontsize=9)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(SUP / f"FigS8_validity_upgrade.{ext}", dpi=300, bbox_inches="tight")


def xlsx():
    files = ["vA_performance", "vA_paired", "vA_within_centre","vB_native_voxel_feature_agreement_by_qc", "vB_native_by_ceiling_definition",
             "vB_model_native_vs_recovered_paired", "vC_site_sensitivity_within_centre", "vC_site_sensitivity_geographic_paired",
             "vD_registration_quality", "vD_location_feature_agreement", "vD_h1_paired", "vE_bootstrap_refit_summary",
             "vX1_isles2018_technical", "vX1_isles2018_core_vs_dwi", "vX1_isles2018_raw_map_ranges"]
    with pd.ExcelWriter(SUP / "Supplementary_tables_validity_upgrade.xlsx") as xw:
        idx = []
        for i, f in enumerate(files, 1):
            p = VTAB / f"{f}.csv"
            if not p.exists():
                continue
            sheet = f"S{20 + i}"
            pd.read_csv(p).to_excel(xw, sheet_name=sheet, index=False)
            idx.append({"sheet": sheet, "source": f + ".csv"})
        pd.DataFrame(idx).to_excel(xw, sheet_name="contents", index=False)


if __name__ == "__main__":
    internal(); external(); provenance(); figure(); xlsx()
    print("collected")
