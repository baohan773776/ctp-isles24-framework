"""Experiment A (post hoc, internal validity): one consistent, fully nested clinical-vs-CTP comparison.

Every arm uses the SAME procedure, so that differences between arms are not confounded by
differently tuned procedures:
  * outer: the canonical fold manifest (5 seeds x stratified 10-fold, s04), verified row by row;
  * inner: stratified 5-fold CV on the outer-training patients only (random_state = seed);
  * candidate learners (identical for every feature set): elastic-net logistic regression
    (s04.EN_GRID, 15 configurations; median imputation + standardisation inside the pipeline) and
    gradient boosting (s04.GBM_GRID, 24 configurations; median imputation inside the pipeline);
  * tuning objective: mean inner-fold log-loss (neg_log_loss); the learner family AND its
    hyper-parameters are chosen jointly by this objective, then refitted on the whole outer-training fold;
  * frozen late-fusion rule: p = 0.5 p_clinical + 0.5 p_CTP (no trainable fusion parameters).
Arms:  A_clin (22 clinical), A_ctp_rec (53 recovered-unit CTP), A_joint_rec (75),
       A_ctp_nat (53 native-unit CTP, s15), A_joint_nat (75), late fusions A_late_rec, A_late_nat.
Outputs (outputs_validity): oof/oof_long_vA.csv, oof/fold_manifest_vA.csv, oof/inner_selection_vA.csv,
       tables/vA_performance.csv, tables/vA_paired.csv
"""
import time
import warnings
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from v_common import VOOF, VTAB, OOF, DATA, SEEDS, load_oof, boot_indices, perf_and_pairs
from config import CLINICAL_22, N_OUTER, N_INNER
import features as F
from s04_models_cv import EN_GRID, GBM_GRID, load_data

warnings.filterwarnings("ignore")
NAT = [f"nat_{c}" for c in F.CTP_ALL]
SETS = {"A_clin": CLINICAL_22, "A_ctp_rec": F.CTP_ALL, "A_joint_rec": CLINICAL_22 + F.CTP_ALL,
        "A_ctp_nat": NAT, "A_joint_nat": CLINICAL_22 + NAT}
LATE = {"A_late_rec": ("A_clin", "A_ctp_rec"), "A_late_nat": ("A_clin", "A_ctp_nat")}


def candidates(seed):
    en = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()),
                   ("lr", LogisticRegression(penalty="elasticnet", solver="saga", max_iter=20000, tol=1e-4,
                                             random_state=seed))])
    gb = Pipeline([("imp", SimpleImputer(strategy="median")),
                   ("gbm", GradientBoostingClassifier(random_state=seed))])
    return {"EN": (en, EN_GRID), "GBM": (gb, GBM_GRID)}


def fit_select(Xtr, ytr, seed):
    best = None
    for fam, (est, grid) in candidates(seed).items():
        gs = GridSearchCV(est, grid, scoring="neg_log_loss", n_jobs=1, refit=True,
                          cv=StratifiedKFold(N_INNER, shuffle=True, random_state=seed))
        gs.fit(Xtr, ytr)
        if best is None or gs.best_score_ > best[1]:
            best = (fam, gs.best_score_, gs.best_estimator_, gs.best_params_)
    return best


def one_fold(df, seed, fold, tr, te):
    y = df["poor"].astype(int).values
    ids = df["subject_id"].values
    preds, sel, oof = {}, [], []
    for name, cols in SETS.items():
        Xtr, Xte = df.loc[tr, cols].values, df.loc[te, cols].values
        fam, score, m, bp = fit_select(Xtr, y[tr], seed)
        preds[name] = m.predict_proba(Xte)[:, 1]
        sel.append({"seed": seed, "fold": fold, "model": name, "family": fam, "inner_neg_logloss": score,
                    "train_auc": roc_auc_score(y[tr], m.predict_proba(Xtr)[:, 1]),
                    "test_auc": roc_auc_score(y[te], preds[name]),
                    **{k.split("__")[1]: v for k, v in bp.items()}})
    for name, (a, b) in LATE.items():
        preds[name] = 0.5 * preds[a] + 0.5 * preds[b]
    for name, p in preds.items():
        oof += [{"subject_id": ids[i], "seed": seed, "fold": fold, "model": name, "y": y[i], "p_poor": pi}
                for i, pi in zip(te, p)]
    return oof, sel, [{"seed": seed, "fold": fold, "subject_id": ids[i]} for i in te]


def run():
    df = load_data()
    nat = pd.read_csv(DATA / "ctp_features_native_149.csv")[["subject_id"] + NAT]
    df = df.merge(nat, on="subject_id", how="left").sort_values("subject_id").reset_index(drop=True)
    assert len(df) == 129 and df[NAT].notna().all().all()
    y = df["poor"].astype(int).values
    jobs = []
    for seed in SEEDS:
        for fold, (tr, te) in enumerate(StratifiedKFold(N_OUTER, shuffle=True, random_state=seed).split(df, y)):
            jobs.append((seed, fold, tr, te))
    t0 = time.time()
    res = Parallel(n_jobs=14, verbose=5)(delayed(one_fold)(df, s, f, tr, te) for s, f, tr, te in jobs)
    oof = [r for x in res for r in x[0]]
    sel = [r for x in res for r in x[1]]
    man = pd.DataFrame([r for x in res for r in x[2]])
    # identical outer folds to the canonical analysis
    canon = pd.read_csv(OOF / "fold_manifest.csv")
    key = ["seed", "fold", "subject_id"]
    assert man.sort_values(key).reset_index(drop=True).equals(canon.sort_values(key).reset_index(drop=True)), \
        "fold manifest differs from canonical"
    pd.DataFrame(oof).to_csv(VOOF / "oof_long_vA.csv", index=False)
    man.to_csv(VOOF / "fold_manifest_vA.csv", index=False)
    pd.DataFrame(sel).to_csv(VOOF / "inner_selection_vA.csv", index=False)
    print(f"done in {time.time() - t0:.0f}s; fold manifest identical to canonical")


def evaluate():
    ids, y, P = load_oof(VOOF / "oof_long_vA.csv")
    # canonical locked/nested references on the same patients and folds (read-only)
    _, y0, P0 = load_oof(OOF / "oof_long.csv", ids)
    _, y1, P1n = load_oof(OOF / "oof_long_sens_nestedgbm.csv", ids)
    assert (y0 == y).all() and (y1 == y).all()
    P.update({"canon_P1_locked_GBM": P0["P1_clin_GBM"], "canon_F_late_P1_E": P0["F_late_P1_E"],
              "canon_E_CTP_all": P0["E_CTP_all"], "canon_P1_nested_GBM": P1n["P1_nested_GBM"]})
    pairs = [("A_late_rec", "A_clin", "PRIMARY (Exp A): CTP added to clinical, consistent nested tuning, late fusion"),
             ("A_joint_rec", "A_clin", "CTP added to clinical, consistent nested tuning, joint model"),
             ("A_ctp_rec", "A_clin", "CTP-only vs clinical-only"),
             ("A_late_nat", "A_clin", "native-unit CTP added to clinical (late fusion)"),
             ("A_joint_nat", "A_clin", "native-unit CTP added to clinical (joint model)"),
             ("A_late_nat", "A_late_rec", "native vs recovered CTP in the fused model"),
             ("A_ctp_nat", "A_ctp_rec", "native vs recovered CTP alone"),
             ("A_clin", "canon_P1_locked_GBM", "procedure contrast: consistent nested vs locked clinical GBM (NOT a pure selection-bias estimate)"),
             ("A_clin", "canon_P1_nested_GBM", "procedure contrast: consistent nested (EN or GBM) vs GBM-only nested"),
             ("A_late_rec", "canon_F_late_P1_E", "procedure contrast: fused model, consistent nested vs primary")]
    perf, comp = perf_and_pairs(y, P, pairs, boot_indices(y), label="Exp A: full cohort (n=129)")
    sel = pd.read_csv(VOOF / "inner_selection_vA.csv")
    fam = sel.groupby("model").family.value_counts().unstack(fill_value=0)
    gap = sel.groupby("model")[["train_auc", "test_auc"]].mean()
    perf = perf.merge(fam.add_prefix("n_folds_selected_").reset_index(), on="model", how="left") \
               .merge(gap.add_prefix("mean_fold_").reset_index(), on="model", how="left")
    perf.to_csv(VTAB / "vA_performance.csv", index=False)
    comp.to_csv(VTAB / "vA_paired.csv", index=False)
    print(perf[["model", "auc_seed_mean", "auc_ci_lo", "auc_ci_hi", "cal_slope_pooled", "brier_seed_mean"]].round(3).to_string(index=False))
    print(comp[["new", "reference", "delta_auc", "ci_lo", "ci_hi", "p_bootstrap"]].round(3).to_string(index=False))
    print(fam)


if __name__ == "__main__":
    import sys
    {"run": run, "eval": evaluate}[sys.argv[1] if len(sys.argv) > 1 else "run"]()
