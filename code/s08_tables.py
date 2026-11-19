"""Descriptive tables and sample-size reasoning.
Table 1: cohort characteristics by 90-day outcome (physical units).
Sample size: Riley et al. (BMJ 2020) criteria for binary outcomes -> number of predictor parameters
supportable with n = 129, given outcome prevalence and an anticipated C-statistic.
"""
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from config import DATA, TAB, CLINICAL_22

BIN = ["Sex", "Wake-up", "In-House", "Referral", "Atrial fibrillation", "Hypertension", "Diabetes", "Hyperlipidemia",
       "Anticoagulation", "Lipid lowering drugs", "PAIs"]
CONT = ["Age", "NIHSS at admission", "mRS premorbid", "mRS at admission", "Glucose", "Leucocytes", "CRP", "INR",
        "Onset to door_min", "Alert to door_min", "Door to imaging_min", "THRIVE", "SPAN100_raw"]
CTP = ["core_rcbf30_hypo_frac", "tmax_gt6_frac", "tmax_gt10_frac", "hir", "mismatch_ratio_log", "rcbv_ipsi_ratio",
       "cbv_index_hypo", "rcbf_ipsi_ratio", "rmtt_ipsi_ratio"]


def fmt_med(v):
    v = v.dropna(); q = v.quantile([.25, .5, .75])
    d = 2 if abs(q[.5]) < 10 else 0
    return f"{q[.5]:.{d}f} [{q[.25]:.{d}f}–{q[.75]:.{d}f}]"


def table1():
    d = pd.read_csv(DATA / "cohort_129.csv").merge(pd.read_csv(DATA / "ctp_features_v3_149.csv"), on="subject_id")
    for c in ("core_rcbf30_hypo_frac", "tmax_gt6_frac", "tmax_gt10_frac"):
        d[c] = 100 * d[c]   # % of covered tissue
    g, p = d[d.poor == 0], d[d.poor == 1]
    rows = [{"variable": "N", "all": len(d), "good (mRS 0-2)": len(g), "poor (mRS 3-6)": len(p), "p": ""}]
    for c in BIN:
        t = stats.fisher_exact(pd.crosstab(d.poor, d[c]).values)[1]
        rows.append({"variable": f"{c}, n (%)", "all": f"{int(d[c].sum())} ({100*d[c].mean():.1f})",
                     "good (mRS 0-2)": f"{int(g[c].sum())} ({100*g[c].mean():.1f})",
                     "poor (mRS 3-6)": f"{int(p[c].sum())} ({100*p[c].mean():.1f})", "p": f"{t:.3f}"})
    for c in CONT + CTP:
        t = stats.mannwhitneyu(g[c].dropna(), p[c].dropna()).pvalue
        rows.append({"variable": f"{c}, median [IQR]", "all": fmt_med(d[c]), "good (mRS 0-2)": fmt_med(g[c]),
                     "poor (mRS 3-6)": fmt_med(p[c]), "p": f"{t:.3f}"})
    mrs = d.mrs90.value_counts().sort_index()
    rows.append({"variable": "90-day mRS 0/1/2/3/4/5/6, n", "all": "/".join(str(int(mrs.get(k, 0))) for k in range(7)),
                 "good (mRS 0-2)": "", "poor (mRS 3-6)": "", "p": ""})
    tici = d["TICI postinterventional"].astype(str).str.replace(".0", "", regex=False).value_counts()
    rows.append({"variable": "Post-interventional mTICI, n", "all": "; ".join(f"{k}: {v}" for k, v in tici.items()),
                 "good (mRS 0-2)": "", "poor (mRS 3-6)": "", "p": ""})
    pd.DataFrame(rows).to_csv(TAB / "table1_by_outcome.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False))


def riley(n=129, phi=44 / 129, auc=0.75, S=0.9, seed=1):
    """Max predictor parameters (criterion 1: global shrinkage >= S) and criterion-3 intercept precision."""
    rng = np.random.default_rng(seed)
    N = 400_000
    sig = np.sqrt(2) * stats.norm.ppf(auc)           # binormal equal-variance LP spread
    # find mean so that prevalence = phi
    lo, hi = -10, 10
    z = rng.standard_normal(N)
    for _ in range(60):
        mu = (lo + hi) / 2
        pr = 1 / (1 + np.exp(-(mu + sig * z)))
        lo, hi = (mu, hi) if pr.mean() < phi else (lo, mu)
    yy = rng.random(N) < pr
    lp = mu + sig * z
    ll1 = np.sum(yy * np.log(pr) + (1 - yy) * np.log(1 - pr))
    ll0 = N * (phi * np.log(phi) + (1 - phi) * np.log(1 - phi))
    r2cs = 1 - np.exp(2 * (ll0 - ll1) / N)
    p_max = n * (S - 1) * np.log(1 - r2cs / S)   # Riley criterion (i) solved for p
    n_int = (1.96 / 0.05) ** 2 * phi * (1 - phi)
    out = {"n": n, "events": round(n * phi), "prevalence": phi, "anticipated_auc": auc, "anticipated_R2cs": r2cs,
           "max_R2cs": 1 - np.exp(2 * ll0 / N), "max_params_for_shrinkage_0.9": p_max,
           "n_required_intercept_precision": n_int, "EPV_22_clinical": n * phi / 22,
           "EPV_22_plus_53_ctp": n * phi / 75}
    return out


if __name__ == "__main__":
    table1()
    rr = pd.DataFrame([riley(auc=a) for a in (0.70, 0.75, 0.80)])
    rr.to_csv(TAB / "sample_size_riley.csv", index=False)
    print(rr.round(3).T.to_string())
