"""QC: every key number of the new manuscript text must appear (3-decimal or stated rounding) in the result tables."""
import pandas as pd
import docx
from v_common import VTAB, ROOT

t = " ".join(p.text for p in docx.Document(ROOT.parent / "BMC_FEASIBILITY_VALIDITY_UPGRADE" / "Manuscript_BMC_MIDM_VALIDITY_REVISED.docx").paragraphs)


def f(x, k=3):
    s = f"{abs(x):.{k}f}"
    return ("−" + s) if x < 0 and float(s) != 0 else s


A = pd.read_csv(VTAB / "vA_performance.csv").set_index("model")
Ap = pd.read_csv(VTAB / "vA_paired.csv").set_index(["new", "reference"])
Aw = pd.read_csv(VTAB / "vA_within_centre.csv").set_index("model")
B = pd.read_csv(VTAB / "vB_model_native_vs_recovered_paired.csv")
Bc = pd.read_csv(VTAB / "vB_native_by_ceiling_definition.csv", index_col=0).loc["no Tmax ceiling (n=41 definition)"]
D = pd.read_csv(VTAB / "vD_h1_paired.csv")
Q = pd.read_csv(VTAB / "vD_registration_quality.csv").set_index("registration")
E = pd.read_csv(VTAB / "vE_bootstrap_refit_summary.csv").set_index("quantity").loc["dAUC F - P1"]
X = pd.read_csv(VTAB / "vX1_isles2018_core_vs_dwi.csv")
X = X[X.analysis == "s03_harmonised: all patients"].set_index("metric")
W = pd.read_csv(VTAB / "vC_site_sensitivity_within_centre.csv")
checks = {
    "A AUCs": [f(A.loc[m, c]) for m in ("A_clin", "A_ctp_rec", "A_late_rec") for c in ("auc_seed_mean", "auc_ci_lo", "auc_ci_hi")],
    "A dAUC": [f(v) for v in Ap.loc[("A_late_rec", "A_clin"), ["delta_auc", "ci_lo", "ci_hi"]]],
    "A native": [f(v) for v in Ap.loc[("A_late_nat", "A_clin"), ["delta_auc", "ci_lo", "ci_hi"]]],
    "A procedure": [f(abs(Ap.loc[("A_clin", "canon_P1_locked_GBM"), "delta_auc"]))] + [f(v) for v in Ap.loc[("A_clin", "canon_P1_locked_GBM"), ["ci_lo", "ci_hi"]]],
    "A within": [f(v) for v in Aw.loc["delta A_late_rec - A_clin", ["within_centre_auc", "ci_lo", "ci_hi"]]],
    "B fused": [f(v) for v in B.iloc[0][["delta_auc", "ci_lo", "ci_hi"]]],
    "B uncertain": [f(v) for v in B[(B.analysis == "Tmax recovery uncertain") & (B.reference == "F_late_P1_E")].iloc[0][["delta_auc", "ci_lo", "ci_hi"]]],
    "B ratio": [f(Bc[c]) for c in ("tmax_scale_ratio_median__median", "tmax_scale_ratio_median__q1", "tmax_scale_ratio_median__q3")],
    "B ml": [f(Bc[c], 1) for c in ("hypoperf_tmax6_ml_diff__median", "hypoperf_tmax6_ml_diff__q1", "hypoperf_tmax6_ml_diff__q3")],
    "C within": [f(W[(W.mapping.str.startswith(m)) & (W.model == "delta F_late_P1_E - P1_clin_GBM")].within_centre_auc.iloc[0]) for m in ("ambiguous ->", "ambiguous excluded")],
    "D full": [f(v) for v in D.iloc[0][["delta_auc", "ci_lo", "ci_hi"]]],
    "D dice80": [f(v) for v in D.iloc[4][["delta_auc", "ci_lo", "ci_hi"]]],
    "D reg": [f(Q.loc["ncct", "dice_vs_ncct_ic_median"], 2), f(Q.loc["dwi", "dice_vs_ncct_ic_median"], 2)],
    "E": [f(E[c]) for c in ("refit_boot_sd", "fixed_pred_boot_sd", "refit_boot_width", "fixed_pred_boot_width")] + [f(E.sd_ratio_refit_over_fixed, 1)],
    "X dice": [f(X.loc["dice_mean", c], 2) for c in ("estimate", "ci_lo", "ci_hi")],
    "X sens/prec": [f(X.loc[m, c], 2) for m in ("sensitivity_mean", "precision_mean") for c in ("estimate", "ci_lo", "ci_hi")],
    "X spearman": [f(X.loc["spearman_core_vs_dwi", c], 2) for c in ("estimate", "ci_lo", "ci_hi")],
    "X BA": [f(X.loc["bland_altman_loa_ml", c], 0) for c in ("estimate", "ci_lo", "ci_hi")],
}
bad = {k: [s for s in v if s not in t] for k, v in checks.items()}
bad = {k: v for k, v in bad.items() if v}
print("checked", sum(len(v) for v in checks.values()), "numbers;", "ALL FOUND" if not bad else f"MISSING: {bad}")
