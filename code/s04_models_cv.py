"""Stage D: nested repeated cross-validation of all prespecified models with one shared fold manifest.

Outer: 5 repeats (seeds 42, 100, 2024, 777, 999) x stratified 10-fold (same protocol as Branch 2).
Inner: stratified 5-fold grid search (neg. log-loss) for penalised models; all preprocessing
(median imputation, standardisation) is fitted inside training folds only.
Outcome: poor = mRS 3-6 (event = 1); every probability is P(poor).
"""
import json
import sys
import time
import warnings
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from config import DATA, OOF, SEEDS, N_OUTER, N_INNER, CLINICAL_22
import features as F

warnings.filterwarnings("ignore")
EN_GRID = {"lr__C": [0.01, 0.03, 0.1, 0.3, 1.0], "lr__l1_ratio": [0.2, 0.5, 0.8]}
# grid for the nested-tuning sensitivity analysis of the clinical GBM (s06 'nestedgbm'); contains the locked configuration
GBM_GRID = {"gbm__n_estimators": [50, 80, 150, 300], "gbm__max_depth": [2, 3, 4], "gbm__learning_rate": [0.03, 0.1],
            "gbm__subsample": [0.7]}


def en_pipe():
    return Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()),
                     ("lr", LogisticRegression(penalty="elasticnet", solver="saga", max_iter=20000, tol=1e-4))])


def lr_fixed(C=1.0):
    return Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()),
                     ("lr", LogisticRegression(C=C, max_iter=5000))])


def gbm(seed):
    # Branch 2 locked configuration (not re-tuned here)
    return Pipeline([("imp", SimpleImputer(strategy="median")),
                     ("gbm", GradientBoostingClassifier(n_estimators=80, max_depth=3, learning_rate=0.1,
                                                        subsample=0.7, random_state=seed))])


# name -> (feature list, builder kind)
MODELS = {
    "P1_clin_GBM": (CLINICAL_22, "gbm"),
    "P2_clin_EN": (CLINICAL_22, "en"),
    "NIHSS_only": (["NIHSS at admission"], "lr"),
    "A_CBF": (F.CBF, "en"),
    "B_CBV": (F.CBV, "en"),
    "C_MTT": (F.MTT, "en"),
    "D_Tmax": (F.TMAX, "en"),
    "E_CTP_all": (F.CTP_ALL, "en"),
    "T_thresholds": (F.THRESH, "lr"),
    "F_EN_clin_CTP": (CLINICAL_22 + F.CTP_ALL, "en"),
    "F_GBM_clin_thresh": (CLINICAL_22 + F.THRESH, "gbm"),
    "THRIVE": (["THRIVE"], "lr"),
    "SPAN100": (["SPAN100_raw"], "lr"),
}
# late-fusion models (equal-weight probability average; no trainable fusion parameters)
LATE = {"F_late_P1_E": ("P1_clin_GBM", "E_CTP_all"), "F_late_P1_T": ("P1_clin_GBM", "T_thresholds")}


def fit_model(kind, Xtr, ytr, seed):
    if kind == "gbm":
        m = gbm(seed).fit(Xtr, ytr); return m, {}
    if kind == "gbm_tuned":   # sensitivity analysis: GBM configuration selected inside each training fold
        gs = GridSearchCV(gbm(seed), GBM_GRID, scoring="neg_log_loss",
                          cv=StratifiedKFold(N_INNER, shuffle=True, random_state=seed), n_jobs=-1, refit=True)
        gs.fit(Xtr, ytr)
        return gs.best_estimator_, {k.replace("gbm__", ""): v for k, v in gs.best_params_.items()}
    if kind == "lr":
        m = lr_fixed().fit(Xtr, ytr); return m, {}
    if kind == "pca":
        from sklearn.decomposition import PCA
        m = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()),
                      ("pca", PCA(n_components=5, random_state=seed)), ("lr", LogisticRegression(C=1.0, max_iter=5000))])
        return m.fit(Xtr, ytr), {}
    gs = GridSearchCV(en_pipe(), EN_GRID, scoring="neg_log_loss",
                      cv=StratifiedKFold(N_INNER, shuffle=True, random_state=seed), n_jobs=-1, refit=True)
    gs.fit(Xtr, ytr)
    return gs.best_estimator_, {k.replace("lr__", ""): v for k, v in gs.best_params_.items()}


def load_data():
    df = pd.read_csv(DATA / "cohort_129.csv").merge(pd.read_csv(DATA / "ctp_features_v3_149.csv"), on="subject_id")
    return df.sort_values("subject_id").reset_index(drop=True)


def main(protocol="primary"):
    n_outer = N_OUTER if protocol == "primary" else 5
    tag = "" if protocol == "primary" else f"_{protocol}"
    run_cv(load_data(), MODELS, LATE, n_outer, tag)


def run_cv(df, MODELS, LATE, n_outer, tag, verbose=True):
    y = df["poor"].astype(int).values
    ids = df["subject_id"].values
    oof, manifest, params, coefs, gaps = [], [], [], [], []
    t0 = time.time()
    for seed in SEEDS:
        skf = StratifiedKFold(n_outer, shuffle=True, random_state=seed)
        for fold, (tr, te) in enumerate(skf.split(df, y)):
            manifest += [{"seed": seed, "fold": fold, "subject_id": ids[i]} for i in te]
            preds = {}
            for name, (cols, kind) in MODELS.items():
                Xtr, Xte = df.loc[tr, cols].values, df.loc[te, cols].values
                m, bp = fit_model(kind, Xtr, y[tr], seed)
                p = m.predict_proba(Xte)[:, 1]
                preds[name] = p
                gaps.append({"seed": seed, "fold": fold, "model": name,
                             "train_auc": roc_auc_score(y[tr], m.predict_proba(Xtr)[:, 1]),
                             "test_auc": roc_auc_score(y[te], p)})
                if bp:
                    params.append({"seed": seed, "fold": fold, "model": name, **bp})
                if kind in ("en", "lr") and "lr" in m.named_steps and m.named_steps["lr"].coef_.shape[1] == len(cols):
                    coefs += [{"seed": seed, "fold": fold, "model": name, "feature": c, "coef_std": w}
                              for c, w in zip(cols, m.named_steps["lr"].coef_[0])]
            for name, (a, b) in LATE.items():
                preds[name] = 0.5 * preds[a] + 0.5 * preds[b]
            for name, p in preds.items():
                oof += [{"subject_id": ids[i], "seed": seed, "fold": fold, "model": name, "y": y[i], "p_poor": pi}
                        for i, pi in zip(te, p)]
            if verbose:
                print(f"seed {seed} fold {fold} done ({time.time()-t0:.0f}s)", flush=True)
    pd.DataFrame(oof).to_csv(OOF / f"oof_long{tag}.csv", index=False)
    pd.DataFrame(manifest).to_csv(OOF / f"fold_manifest{tag}.csv", index=False)
    # header is written even when no model was tuned in this run (runs with fixed models only)
    (pd.DataFrame(params) if params else pd.DataFrame(columns=["seed", "fold", "model"])).to_csv(
        OOF / f"inner_best_params{tag}.csv", index=False)
    pd.DataFrame(coefs).to_csv(OOF / f"coefficients{tag}.csv", index=False)
    pd.DataFrame(gaps).to_csv(OOF / f"train_test_auc{tag}.csv", index=False)
    o = pd.DataFrame(oof)
    s = o.groupby(["model", "seed"]).apply(lambda g: roc_auc_score(g.y, g.p_poor)).groupby("model").agg(["mean", "std"])
    print(s.sort_values("mean", ascending=False).round(4).to_string())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "primary")
