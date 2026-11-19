"""Precision / equivalence analysis of the incremental value of CTP (reviewer point: 'absence of
evidence is not evidence of absence').

For each prespecified pair (new vs reference):
  * delta AUC (mean of per-seed AUCs) with the same 2000 patient-level bootstrap resamples as s05;
  * 90% CI and two one-sided tests (TOST) against an equivalence margin of +/-0.05 AUC
    (a commonly used threshold for a clinically relevant gain in discrimination), and against +/-0.03;
  * Bayesian bootstrap (Dirichlet(1,...,1) patient weights, weighted AUC) posterior probabilities
    P(delta > 0) and P(delta > 0.05);
  * minimal detectable difference at 80% power (2.80 x bootstrap SE) and the sample size that
    would be needed to detect delta = 0.05 with 80% power (SE scaled by 1/sqrt(n)).
"""
import numpy as np
import pandas as pd
from config import TAB, N_BOOT, BOOT_SEED
from s05_evaluate import load, seed_auc

PAIRS = [
    ("F_late_P1_E", "P1_clin_GBM", "primary"),
    ("F_late_R1_E", "R1_clin_LR4", "parsimonious clinical reference"),
    ("F_late_P1recal_E", "P1_recal", "recalibrated clinical reference"),
    ("F_late_P1_Enat", "P1_clin_GBM", "native-unit CTP features"),
    ("F_late_P1_V", "P1_clin_GBM", "absolute CTP volumes (late fusion)"),
    ("R1_plus_volumes", "R1_clin_LR4", "absolute CTP volumes (joint model)"),
]
MARGINS = (0.05, 0.03)


def w_auc(y, p, w):
    pos, neg = y == 1, y == 0
    pp, pn = p[pos][:, None], p[neg][None, :]
    k = (pp > pn) + 0.5 * (pp == pn)
    wp, wn = w[pos][:, None], w[neg][None, :]
    return (k * wp * wn).sum() / (wp.sum() * wn.sum())


def main():
    ids, y, P = load("_all")
    n = len(y)
    rng = np.random.default_rng(BOOT_SEED)
    boots = []
    while len(boots) < N_BOOT:
        b = rng.integers(0, n, n)
        if 0 < y[b].sum() < n:
            boots.append(b)
    rng2 = np.random.default_rng(BOOT_SEED + 1)
    W = rng2.dirichlet(np.ones(n), size=N_BOOT)
    rows = []
    for new, ref, role in PAIRS:
        if new not in P or ref not in P:
            continue
        d = seed_auc(y, P[new]) - seed_auc(y, P[ref])
        db = np.array([seed_auc(y, P[new], b) - seed_auc(y, P[ref], b) for b in boots])
        se = db.std(ddof=1)
        dbb = np.array([np.mean([w_auc(y, pn, w) - w_auc(y, pr, w) for pn, pr in zip(P[new], P[ref])]) for w in W])
        r = {"new": new, "reference": ref, "role": role, "delta_auc": d, "se_boot": se,
             "ci95_lo": np.percentile(db, 2.5), "ci95_hi": np.percentile(db, 97.5),
             "ci90_lo": np.percentile(db, 5), "ci90_hi": np.percentile(db, 95),
             "post_p_gt0": (dbb > 0).mean(), "post_p_gt0.03": (dbb > 0.03).mean(), "post_p_gt0.05": (dbb > 0.05).mean(),
             "mdd_80pct_power": 2.80 * se, "n_needed_delta0.05": int(np.ceil(n * (2.80 * se / 0.05) ** 2)),
             "events_needed_delta0.05": int(np.ceil(n * (2.80 * se / 0.05) ** 2 * y.mean()))}
        for m in MARGINS:
            r[f"tost_equiv_{m}"] = bool(r["ci90_lo"] > -m and r["ci90_hi"] < m)
            r[f"exclude_gain_ge_{m}"] = bool(r["ci95_hi"] < m)
        rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "precision_equivalence.csv", index=False)
    print(out.round(3).T.to_string())


if __name__ == "__main__":
    main()
