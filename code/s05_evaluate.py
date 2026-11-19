"""Stage E: discrimination, paired comparisons, calibration, DCA, reclassification, ordinal c-index.

Primary estimand: mean over the 5 seeds of the per-seed OOF AUC (each seed: 129 patients).
95% CIs: 2000 patient-level bootstrap resamples; a resampled patient carries all 5 seed predictions.
Secondary estimand (curves, calibration, DCA, NRI/IDI): per-patient mean of the 5 OOF probabilities.
"""
import sys
import numpy as np
import pandas as pd
from config import DATA, OOF, TAB, SEEDS, N_BOOT, BOOT_SEED
from stats_utils import (auc_fast, delong, calib, net_benefit, nb_all, nri_idi, classif, pr_auc, ordinal_c)

COMPARISONS = [  # (new, reference, role)
    ("F_late_P1_E", "P1_clin_GBM", "primary: added value of CTP to clinical model"),
    ("F_EN_clin_CTP", "P1_clin_GBM", "secondary multimodal"),
    ("F_GBM_clin_thresh", "P1_clin_GBM", "secondary multimodal"),
    ("F_late_P1_T", "P1_clin_GBM", "secondary multimodal"),
    ("F_late_P1_E", "E_CTP_all", "multimodal vs imaging-only"),
    ("E_CTP_all", "T_thresholds", "ML on CTP vs classical thresholds"),
    ("D_Tmax", "A_CBF", "channel"), ("D_Tmax", "B_CBV", "channel"), ("D_Tmax", "C_MTT", "channel"),
    ("B_CBV", "A_CBF", "channel"), ("B_CBV", "C_MTT", "channel"), ("A_CBF", "C_MTT", "channel"),
    ("E_CTP_all", "D_Tmax", "all channels vs Tmax"), ("E_CTP_all", "B_CBV", "all channels vs CBV"),
    ("P1_clin_GBM", "THRIVE", "clinical ML vs score"), ("P1_clin_GBM", "SPAN100", "clinical ML vs score"),
    ("F_late_P1_E", "THRIVE", "multimodal vs score"), ("F_late_P1_E", "SPAN100", "multimodal vs score"),
    ("P1_clin_GBM", "P2_clin_EN", "GBM vs linear clinical"),
    # additional analyses (oof_long_all)
    ("P1_clin_GBM", "R1_clin_LR4", "flexible vs parsimonious clinical"),
    ("F_late_R1_E", "R1_clin_LR4", "added value of CTP to parsimonious clinical model"),
    ("F_late_P1recal_E", "P1_recal", "added value of CTP to recalibrated clinical model"),
    ("P1_recal", "P1_clin_GBM", "recalibration"),
    ("F_late_P1_Enat", "P1_clin_GBM", "added value of native-unit CTP features"),
    ("F_late_P1_V", "P1_clin_GBM", "added value of absolute CTP volumes"),
    ("R1_plus_volumes", "R1_clin_LR4", "added value of absolute CTP volumes (joint model)"),
    ("F_late_R1_V", "R1_clin_LR4", "added value of absolute CTP volumes (late fusion)"),
    ("E_native", "E_CTP_all", "native vs recovered CTP features"),
    ("V_volumes", "T_thresholds", "absolute vs relative threshold volumes"),
    # sensitivity analysis 'nestedgbm' (oof_long_sens_nestedgbm): nested-tuned clinical GBM reference
    ("P1_nested_GBM", "P1_clin_GBM", "sensitivity: nested-tuned vs locked clinical GBM (selection optimism)"),
    ("F_late_P1nested_E", "P1_nested_GBM", "sensitivity: added value of CTP to nested-tuned clinical GBM"),
]
EXTRA_PAIRS = [("F_late_R1_E", "R1_clin_LR4"), ("F_late_P1recal_E", "P1_recal"), ("F_late_P1_V", "P1_clin_GBM"),
               ("R1_plus_volumes", "R1_clin_LR4"), ("F_late_P1_Enat", "P1_clin_GBM")]
DCA_T = [0.20, 0.35, 0.50]
COMP_COLS = ["new", "reference", "role", "delta_auc", "ci_lo", "ci_hi", "p_bootstrap", "delta_auc_pooled", "p_delong_pooled"]
DCT_COLS = ["new", "reference", "threshold", "nb_new", "nb_ref", "nb_treat_all", "delta_nb", "ci_lo", "ci_hi"]
RC_COLS = ["new", "reference", "nri_type", "nri", "nri_lo", "nri_hi", "nri_events", "nri_nonevents", "idi", "idi_lo", "idi_hi"]


def save(rows, cols, path):
    """Write a table; a run without any matching pair still gets a valid CSV with a header."""
    (pd.DataFrame(rows) if rows else pd.DataFrame(columns=cols)).to_csv(path, index=False)


def load(tag=""):
    o = pd.read_csv(OOF / f"oof_long{tag}.csv")
    ids = np.sort(o.subject_id.unique())
    y = o.drop_duplicates("subject_id").set_index("subject_id").loc[ids, "y"].values
    P = {}
    for m, g in o.groupby("model"):
        w = g.pivot(index="subject_id", columns="seed", values="p_poor").loc[ids, SEEDS]
        P[m] = w.values.T   # (5, n)
    return ids, y, P


def seed_auc(y, Pm, idx=None):
    if idx is None:
        return np.mean([auc_fast(y, p) for p in Pm])
    return np.mean([auc_fast(y[idx], p[idx]) for p in Pm])


def main(tag=""):
    ids, y, P = load(tag)
    coh = pd.read_csv(DATA / "cohort_129.csv").set_index("subject_id").loc[ids]
    rng = np.random.default_rng(BOOT_SEED)
    n = len(y)
    boots = []
    while len(boots) < N_BOOT:
        b = rng.integers(0, n, n)
        if 0 < y[b].sum() < n:
            boots.append(b)
    models = sorted(P)
    bt = {m: np.array([seed_auc(y, P[m], b) for b in boots]) for m in models}

    rows = []
    for m in models:
        per = [auc_fast(y, p) for p in P[m]]
        pm = P[m].mean(0)
        a, se = delong(y, pm)
        c = calib(y, pm)
        cs = [calib(y, p)["slope"] for p in P[m]]
        rows.append({"model": m, "auc_seed_mean": np.mean(per), "auc_seed_sd": np.std(per, ddof=1),
                     "auc_ci_lo": np.percentile(bt[m], 2.5), "auc_ci_hi": np.percentile(bt[m], 97.5),
                     "auc_pooled": a, "auc_pooled_lo": a - 1.96 * se, "auc_pooled_hi": a + 1.96 * se,
                     "auprc_pooled": pr_auc(y, pm), "brier_seed_mean": np.mean([np.mean((p - y) ** 2) for p in P[m]]),
                     "cal_slope_seed_mean": np.mean(cs), **{f"pooled_{k}": v for k, v in c.items()},
                     **{f"thr50_{k}": v for k, v in classif(y, pm, 0.5).items()},
                     "ordinal_c_mrs": ordinal_c(coh["mrs90"].values, pm)})
    perf = pd.DataFrame(rows).sort_values("auc_seed_mean", ascending=False)
    perf.to_csv(TAB / f"performance_all_models{tag}.csv", index=False)

    comp = []
    for new, ref, role in COMPARISONS:
        if new not in P or ref not in P:
            continue
        d = seed_auc(y, P[new]) - seed_auc(y, P[ref])
        db = bt[new] - bt[ref]
        p_boot = min(1.0, 2 * min((db <= 0).mean(), (db >= 0).mean()))
        dd, dse, pdl = delong(y, P[new].mean(0), P[ref].mean(0))
        comp.append({"new": new, "reference": ref, "role": role, "delta_auc": d, "ci_lo": np.percentile(db, 2.5),
                     "ci_hi": np.percentile(db, 97.5), "p_bootstrap": p_boot, "delta_auc_pooled": dd, "p_delong_pooled": pdl})
    save(comp, COMP_COLS, TAB / f"paired_auc_comparisons{tag}.csv")
    for ref in ("P1_clin_GBM", "T_thresholds", "E_CTP_all", "R1_clin_LR4"):
        if ref not in P:
            continue
        rows_r = []
        for m in models:
            if m == ref:
                continue
            db = bt[m] - bt[ref]
            rows_r.append({"model": m, "reference": ref, "delta_auc": seed_auc(y, P[m]) - seed_auc(y, P[ref]),
                           "ci_lo": np.percentile(db, 2.5), "ci_hi": np.percentile(db, 97.5),
                           "p_bootstrap": min(1.0, 2 * min((db <= 0).mean(), (db >= 0).mean()))})
        pd.DataFrame(rows_r).to_csv(TAB / f"paired_vs_{ref}{tag}.csv", index=False)

    # ---- decision curves ----
    ts = np.round(np.arange(0.05, 0.61, 0.01), 2)
    dca = [{"threshold": t, "model": m, "net_benefit": net_benefit(y, P[m].mean(0), t)} for m in models for t in ts]
    dca += [{"threshold": t, "model": "treat_all", "net_benefit": nb_all(y, t)} for t in ts]
    dca += [{"threshold": t, "model": "treat_none", "net_benefit": 0.0} for t in ts]
    pd.DataFrame(dca).to_csv(TAB / f"dca_curves{tag}.csv", index=False)
    dct = []
    for new, ref in [("F_late_P1_E", "P1_clin_GBM"), ("F_EN_clin_CTP", "P1_clin_GBM"), ("P1_clin_GBM", "THRIVE"),
                     ("P1_clin_GBM", "SPAN100"), ("E_CTP_all", "T_thresholds"), ("F_late_P1_E", "THRIVE")] + EXTRA_PAIRS:
        if new not in P or ref not in P:
            continue
        pn, po = P[new].mean(0), P[ref].mean(0)
        for t in DCA_T:
            d = net_benefit(y, pn, t) - net_benefit(y, po, t)
            db = np.array([net_benefit(y[b], pn[b], t) - net_benefit(y[b], po[b], t) for b in boots])
            dct.append({"new": new, "reference": ref, "threshold": t, "nb_new": net_benefit(y, pn, t),
                        "nb_ref": net_benefit(y, po, t), "nb_treat_all": nb_all(y, t), "delta_nb": d,
                        "ci_lo": np.percentile(db, 2.5), "ci_hi": np.percentile(db, 97.5)})
    save(dct, DCT_COLS, TAB / f"dca_delta_nb{tag}.csv")

    # ---- reclassification ----
    rc = []
    for new, ref in [("F_late_P1_E", "P1_clin_GBM"), ("F_EN_clin_CTP", "P1_clin_GBM"), ("P1_clin_GBM", "THRIVE"),
                     ("P1_clin_GBM", "SPAN100"), ("E_CTP_all", "T_thresholds")] + EXTRA_PAIRS:
        if new not in P or ref not in P:
            continue
        pn, po = P[new].mean(0), P[ref].mean(0)
        for lab, cuts in [("category-free", None), ("categorical <0.20/0.20-0.50/>0.50", [0.2, 0.5])]:
            est = nri_idi(y, pn, po, cuts)
            bb = np.array([nri_idi(y[b], pn[b], po[b], cuts) for b in boots])
            rc.append({"new": new, "reference": ref, "nri_type": lab, "nri": est[0], "nri_lo": np.percentile(bb[:, 0], 2.5),
                       "nri_hi": np.percentile(bb[:, 0], 97.5), "nri_events": est[1], "nri_nonevents": est[2],
                       "idi": est[3], "idi_lo": np.percentile(bb[:, 3], 2.5), "idi_hi": np.percentile(bb[:, 3], 97.5)})
    save(rc, RC_COLS, TAB / f"reclassification{tag}.csv")

    # ---- overfitting gap ----
    try:
        g = pd.read_csv(OOF / f"train_test_auc{tag}.csv")
        g["gap"] = g.train_auc - g.test_auc
        g.groupby("model")[["train_auc", "test_auc", "gap"]].mean().round(4).to_csv(TAB / f"overfit_gap{tag}.csv")
    except FileNotFoundError:
        pass

    # ---- pooled probabilities for figures ----
    pd.DataFrame({"subject_id": ids, "y": y, "mrs90": coh["mrs90"].values,
                  **{m: P[m].mean(0) for m in models}}).to_csv(OOF / f"pooled_probabilities{tag}.csv", index=False)

    cols = ["model", "auc_seed_mean", "auc_seed_sd", "auc_ci_lo", "auc_ci_hi", "auc_pooled", "brier_seed_mean",
            "pooled_slope", "pooled_citl", "pooled_ici", "ordinal_c_mrs"]
    print(perf[cols].round(3).to_string(index=False))
    for frame, cols in ((comp, ["new", "reference", "delta_auc", "ci_lo", "ci_hi", "p_bootstrap", "p_delong_pooled"]), (dct, None), (rc, None)):
        if frame:   # runs with no prespecified pair (e.g. _sens_scalefree) write empty tables and print nothing here
            fr = pd.DataFrame(frame)
            print((fr[cols] if cols else fr).round(3).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")

