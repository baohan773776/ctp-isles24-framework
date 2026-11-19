"""Stage G: sensitivity analyses (each reruns the identical nested-CV protocol on the same folds).

  features   : compact physiological CTP set, PCA, scale-free features, alternative Tmax/core
               thresholds, leave-one-channel-out, alternative late-fusion partners
  missing    : missing-indicator and drop-Alert-to-door variants of the clinical GBM
  tmaxcertain: restricted to patients whose Tmax scale is certain (ceiling present, no degenerate norm.)
  5fold      : 5 repeats x 5-fold protocol (runs s04 with protocol '5fold')
  scalefree  : corrected scale-free feature list (features.SCALE_FREE, 30 features; rcbf_in_hypo removed 2026-11-13);
               only P1, E_scalefree and their fusion are refitted (tag _sens_scalefree). The E_scalefree /
               F_late_P1_Esf rows of the earlier 'features' run used the superseded 31-feature list.
  nestedgbm  : clinical GBM re-tuned inside each training fold (inner 5-fold grid search, s04.GBM_GRID) instead of
               the configuration locked by the companion study; quantifies the selection optimism of P1 and repeats
               the primary CTP comparison against the nested-tuned reference (tag _sens_nestedgbm).
"""
import sys
import numpy as np
import pandas as pd
import features as F
from config import CLINICAL_22, N_OUTER
from s04_models_cv import load_data, run_cv, MODELS, LATE
import s05_evaluate

PHYS = ["core_rcbf30_hypo_frac", "rcbf_ipsi_ratio", "rcbf_in_hypo", "rcbv_ipsi_ratio", "lowcbv_rcbv60_frac",
        "cbv_index_hypo", "rmtt_ipsi_ratio", "mtt145_frac", "rmtt_in_hypo", "tmax_gt6_frac", "tmax_gt10_frac",
        "hir", "tmax_ipsi_minus_contra", "mismatch_ratio_log", "mismatch_frac"]


def variant(name):
    df = load_data()
    base = {"P1_clin_GBM": MODELS["P1_clin_GBM"]}
    if name == "features":
        chans = {"CBF": F.CBF, "CBV": F.CBV, "MTT": F.MTT, "Tmax": F.TMAX}
        models = {**base, "E_CTP_all": MODELS["E_CTP_all"], "T_thresholds": MODELS["T_thresholds"],
                  "E_phys15": (PHYS, "en"), "E_PCA5": (F.CTP_ALL, "pca"), "E_scalefree": (F.SCALE_FREE, "en"),
                  "B_CBV": MODELS["B_CBV"],
                  "T_tmax4": (["core_rcbf30_hypo_frac", "tmax_gt4_frac", "mismatch_ratio_log", "hir"], "lr"),
                  "T_tmax8": (["core_rcbf30_hypo_frac", "tmax_gt8_frac", "mismatch_ratio_log", "hir"], "lr"),
                  "T_core20": (["core_rcbf20_hypo_frac", "tmax_gt6_frac", "mismatch_ratio_log", "hir"], "lr"),
                  "T_core38": (["core_rcbf38_hypo_frac", "tmax_gt6_frac", "mismatch_ratio_log", "hir"], "lr"),
                  "T_core_ipsi30": (["core_rcbf30_frac", "tmax_gt6_frac", "mismatch_ratio_log", "hir"], "lr")}
        for ch, cols in chans.items():
            models[f"E_minus_{ch}"] = ([c for c in F.CTP_ALL if c not in cols], "en")
        late = {"F_late_P1_E": ("P1_clin_GBM", "E_CTP_all"), "F_late_P1_Ephys": ("P1_clin_GBM", "E_phys15"),
                "F_late_P1_EPCA": ("P1_clin_GBM", "E_PCA5"), "F_late_P1_CBV": ("P1_clin_GBM", "B_CBV"),
                "F_late_P1_Esf": ("P1_clin_GBM", "E_scalefree"), "F_late_P1_T": ("P1_clin_GBM", "T_thresholds")}
    elif name == "missing":
        ind = {"CRP": 0.20917762377817, "INR": 1.006273786856195, "Leucocytes": 8.750170987622571,
               "Onset to door_min": 111.65, "Glucose": 108.61963752228351}
        for c, med in ind.items():
            df[f"miss_{c}"] = np.isclose(df[c], med, atol=1e-3).astype(int)
        miss = [f"miss_{c}" for c in ind]
        models = {**base, "P1_missind": (CLINICAL_22 + miss, "gbm"),
                  "P1_no_alert2door": ([c for c in CLINICAL_22 if c != "Alert to door_min"], "gbm"),
                  "P1_missonly": (miss, "lr"), "E_CTP_all": MODELS["E_CTP_all"]}
        late = {"F_late_P1_E": ("P1_clin_GBM", "E_CTP_all"), "F_late_P1miss_E": ("P1_missind", "E_CTP_all")}
    elif name == "tmaxcertain":
        q = pd.read_csv(__import__("config").DATA / "ctp_features_v3_149.csv")
        ok = q.loc[(q.qc_Tmax_n_at_ceiling >= 2) & (~q.qc_degenerate_norm.astype(bool)), "subject_id"]
        df = df[df.subject_id.isin(ok)].reset_index(drop=True)
        print("tmax-certain subset n =", len(df), "events =", int(df.poor.sum()))
        models = {k: MODELS[k] for k in ("P1_clin_GBM", "D_Tmax", "B_CBV", "E_CTP_all", "T_thresholds")}
        late = {"F_late_P1_E": ("P1_clin_GBM", "E_CTP_all")}
    elif name == "scalefree":
        assert "rcbf_in_hypo" not in F.SCALE_FREE
        models = {**base, "E_scalefree": (F.SCALE_FREE, "en")}
        late = {"F_late_P1_Esf": ("P1_clin_GBM", "E_scalefree")}
    elif name == "nestedgbm":
        models = {**base, "P1_nested_GBM": (CLINICAL_22, "gbm_tuned"), "E_CTP_all": MODELS["E_CTP_all"]}
        late = {"F_late_P1_E": ("P1_clin_GBM", "E_CTP_all"), "F_late_P1nested_E": ("P1_nested_GBM", "E_CTP_all")}
    else:
        raise ValueError(name)
    tag = f"_sens_{name}"
    run_cv(df, models, late, N_OUTER, tag, verbose=False)
    s05_evaluate.main(tag)


if __name__ == "__main__":
    for nm in sys.argv[1:]:
        if nm == "5fold":
            import s04_models_cv
            s04_models_cv.main("5fold"); s05_evaluate.main("_5fold")
        else:
            variant(nm)
