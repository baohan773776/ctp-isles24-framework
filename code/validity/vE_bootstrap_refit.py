"""Experiment E (post hoc): does the fixed-prediction patient bootstrap capture model-fitting variability?

Canonical CIs (s05) resample patients while keeping each patient's out-of-fold predictions FIXED; refitting variability
enters only through the 5 CV repeats. Here the WHOLE modelling procedure is re-run on each bootstrap resample.
Fixed computation budget (set before running): B = 100 patient-level bootstrap resamples x 1 repeat of 10-fold CV.
Within a resample, duplicated patients are kept in the same fold (StratifiedGroupKFold, groups = patient) and the
inner tuning folds are grouped the same way, so no patient is ever in both training and test data.
Models: primary pair only - P1 (locked clinical GBM), E_CTP_all (elastic net, inner 5-fold grid, neg. log-loss),
F_late_P1_E = 0.5 P1 + 0.5 E. Statistic: OOF AUC of each model and dAUC (F - P1) in each resample.
Comparison: percentile interval of the bootstrap-refit distribution vs the canonical fixed-prediction bootstrap CI and
the between-seed SD of the canonical CV repeats. The number of resamples was NOT chosen to narrow any interval.
Outputs: outputs_validity/tables/vE_bootstrap_refit_draws.csv, vE_bootstrap_refit_summary.csv
"""
import time
import warnings
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from v_common import VTAB, OOF, SEEDS, load_oof, boot_indices, seed_auc
from stats_utils import auc_fast
from config import CLINICAL_22
import features as F
from s04_models_cv import EN_GRID, en_pipe, gbm, load_data

warnings.filterwarnings("ignore")
B = 100
N_OUTER, N_INNER = 10, 5


def one(b, df, seed0=777000):
    rng = np.random.default_rng(seed0 + b)
    n = len(df)
    while True:
        idx = rng.integers(0, n, n)
        y = df.poor.values[idx].astype(int)
        if 0 < y.sum() < n:
            break
    groups = df.subject_id.values[idx]
    Xc, Xe = df[CLINICAL_22].values[idx], df[F.CTP_ALL].values[idx]
    pc, pe = np.zeros(n), np.zeros(n)
    outer = StratifiedGroupKFold(N_OUTER, shuffle=True, random_state=b)
    for tr, te in outer.split(Xc, y, groups):
        m = gbm(b).fit(Xc[tr], y[tr]); pc[te] = m.predict_proba(Xc[te])[:, 1]
        en = en_pipe(); en.set_params(lr__random_state=b)
        inner = list(StratifiedGroupKFold(N_INNER, shuffle=True, random_state=b).split(Xe[tr], y[tr], groups[tr]))
        gs = GridSearchCV(en, EN_GRID, scoring="neg_log_loss", cv=inner, n_jobs=1, refit=True).fit(Xe[tr], y[tr])
        pe[te] = gs.predict_proba(Xe[te])[:, 1]
    pf = 0.5 * pc + 0.5 * pe
    return {"b": b, "n_unique": len(np.unique(groups)), "events": int(y.sum()), "auc_P1": auc_fast(y, pc),
            "auc_E": auc_fast(y, pe), "auc_F": auc_fast(y, pf), "dauc_F_minus_P1": auc_fast(y, pf) - auc_fast(y, pc)}


def main():
    df = load_data()
    t0 = time.time()
    rows = Parallel(n_jobs=14, verbose=5)(delayed(one)(b, df) for b in range(B))
    D = pd.DataFrame(rows)
    D.to_csv(VTAB / "vE_bootstrap_refit_draws.csv", index=False)
    ids, y, P = load_oof(OOF / "oof_long.csv")
    boots = boot_indices(y)
    fixed = {m: np.array([seed_auc(y, P[m], bb) for bb in boots]) for m in ("P1_clin_GBM", "E_CTP_all", "F_late_P1_E")}
    seeds = {m: np.array([auc_fast(y, p) for p in P[m]]) for m in fixed}
    out = []
    for lab, col, m in (("P1 AUC", "auc_P1", "P1_clin_GBM"), ("E_CTP AUC", "auc_E", "E_CTP_all"),
                        ("F_late_P1_E AUC", "auc_F", "F_late_P1_E"), ("dAUC F - P1", "dauc_F_minus_P1", None)):
        fx = fixed[m] if m else fixed["F_late_P1_E"] - fixed["P1_clin_GBM"]
        sd_seed = np.std(seeds[m], ddof=1) if m else np.std(seeds["F_late_P1_E"] - seeds["P1_clin_GBM"], ddof=1)
        est = seed_auc(y, P[m]) if m else seed_auc(y, P["F_late_P1_E"]) - seed_auc(y, P["P1_clin_GBM"])
        r = D[col]
        out.append({"quantity": lab, "canonical_estimate": est,
                    "fixed_pred_boot_lo": np.percentile(fx, 2.5), "fixed_pred_boot_hi": np.percentile(fx, 97.5),
                    "fixed_pred_boot_width": np.percentile(fx, 97.5) - np.percentile(fx, 2.5), "fixed_pred_boot_sd": fx.std(ddof=1),
                    "refit_boot_B": len(r), "refit_boot_mean": r.mean(), "refit_boot_lo": np.percentile(r, 2.5),
                    "refit_boot_hi": np.percentile(r, 97.5), "refit_boot_width": np.percentile(r, 97.5) - np.percentile(r, 2.5),
                    "refit_boot_sd": r.std(ddof=1), "sd_ratio_refit_over_fixed": r.std(ddof=1) / fx.std(ddof=1),
                    "between_seed_sd_canonical": sd_seed})
    S = pd.DataFrame(out)
    S.to_csv(VTAB / "vE_bootstrap_refit_summary.csv", index=False)
    print(f"{time.time() - t0:.0f}s"); print(S.round(4).T.to_string())


if __name__ == "__main__":
    main()
