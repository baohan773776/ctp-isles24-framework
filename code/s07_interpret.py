"""Stage F: interpretability and stability.
(1) Elastic-net coefficients (standardised) of the all-channel CTP model and the early-fusion model:
    mean |coef|, selection frequency, channel share, rank stability across the 50 outer folds.
(2) TreeSHAP on outer-test patients for the clinical GBM (P1) and the clinical+threshold GBM,
    refitted on the identical folds (deterministic), aggregated by feature and by channel.
"""
import itertools
import numpy as np
import pandas as pd
import shap
from scipy import stats
from sklearn.model_selection import StratifiedKFold
from config import OOF, TAB, SEEDS, N_OUTER, CLINICAL_22
import features as F
from s04_models_cv import load_data, gbm


def rank_stability(mat):
    """median pairwise Spearman correlation between importance vectors (rows = folds)."""
    rs = [stats.spearmanr(a, b).correlation for a, b in itertools.combinations(mat, 2)]
    return float(np.nanmedian(rs)), float(np.nanpercentile(rs, 25)), float(np.nanpercentile(rs, 75))


def coef_summary():
    c = pd.read_csv(OOF / "coefficients.csv")
    out, stab = [], []
    for m in ("E_CTP_all", "F_EN_clin_CTP", "B_CBV", "D_Tmax", "A_CBF", "C_MTT", "T_thresholds", "P2_clin_EN"):
        g = c[c.model == m].copy()
        if g.empty:
            continue
        g["abs"] = g.coef_std.abs()
        s = g.groupby("feature").agg(mean_abs_coef=("abs", "mean"), mean_coef=("coef_std", "mean"),
                                     selection_freq=("coef_std", lambda v: float((v.abs() > 1e-8).mean())))
        s["channel"] = [F.CHANNEL_OF.get(f, "other") for f in s.index]
        s["model"] = m
        out.append(s.reset_index())
        piv = g.pivot_table(index=["seed", "fold"], columns="feature", values="abs").values
        med, q1, q3 = rank_stability(piv)
        ch = s.groupby("channel").mean_abs_coef.sum()
        stab.append({"model": m, "rank_spearman_median": med, "q1": q1, "q3": q3,
                     **{f"share_{k}": v / ch.sum() for k, v in ch.items()}})
    pd.concat(out).sort_values(["model", "mean_abs_coef"], ascending=[True, False]).to_csv(TAB / "coef_importance.csv", index=False)
    pd.DataFrame(stab).to_csv(TAB / "coef_rank_stability.csv", index=False)
    print(pd.DataFrame(stab).round(3).to_string(index=False))


def tree_shap():
    df = load_data(); y = df.poor.astype(int).values
    res = {}
    for name, cols in (("P1_clin_GBM", CLINICAL_22), ("F_GBM_clin_thresh", CLINICAL_22 + F.THRESH)):
        vals, fold_imp = np.zeros((len(df), len(cols))), []
        cnt = np.zeros(len(df))
        allrows = []
        for seed in SEEDS:
            for fold, (tr, te) in enumerate(StratifiedKFold(N_OUTER, shuffle=True, random_state=seed).split(df, y)):
                m = gbm(seed).fit(df.loc[tr, cols].values, y[tr])
                Xte = m.named_steps["imp"].transform(df.loc[te, cols].values)
                sv = shap.TreeExplainer(m.named_steps["gbm"]).shap_values(Xte)
                sv = sv[1] if isinstance(sv, list) else sv
                vals[te] += sv; cnt[te] += 1
                fold_imp.append(np.abs(sv).mean(0))
                allrows.append(pd.DataFrame(sv, columns=cols).assign(subject_id=df.subject_id.values[te], seed=seed))
        mean_sv = vals / cnt[:, None]
        imp = pd.DataFrame({"feature": cols, "mean_abs_shap": np.abs(mean_sv).mean(0),
                            "corr_value_shap": [stats.spearmanr(df[c], mean_sv[:, j], nan_policy="omit").correlation for j, c in enumerate(cols)]})
        imp["channel"] = [F.CHANNEL_OF.get(f, "other") for f in imp.feature]
        imp = imp.sort_values("mean_abs_shap", ascending=False)
        med, q1, q3 = rank_stability(np.array(fold_imp))
        imp.to_csv(TAB / f"treeshap_{name}.csv", index=False)
        pd.concat(allrows).to_csv(OOF / f"treeshap_values_{name}.csv", index=False)
        res[name] = {"rank_spearman_median": med, "q1": q1, "q3": q3}
        print(name, res[name]); print(imp.head(12).round(4).to_string(index=False))
    pd.DataFrame(res).T.to_csv(TAB / "treeshap_rank_stability.csv")


if __name__ == "__main__":
    coef_summary()
    tree_shap()
