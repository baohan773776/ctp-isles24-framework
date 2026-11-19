"""Centre effects (inferred centres, s19).

1. Case mix and data completeness by centre (outcome rate, probable release-level median imputation,
   premorbid mRS, CTP slab coverage).
2. AUC of the centre indicator alone, and WITHIN-CENTRE AUC of every pooled-CV model: concordance
   computed only over (poor, good) pairs from the same centre, which removes discrimination that
   comes from between-centre differences in outcome rate (centre-stratified bootstrap CIs).
3. `python s21_site_effects.py munich_cv` runs the nested CV inside Munich only (88 patients,
   38 events), then evaluate with `python s05_evaluate.py _munich`.
"""
import sys
import numpy as np
import pandas as pd
from scipy import stats
import s04_models_cv as M
import s14_extra_models as X
from s01_build_cohort import CONT, DUR, CONT_MEDIAN, DUR_MEDIAN
from s05_evaluate import load
from config import DATA, TAB, SEEDS, N_BOOT, BOOT_SEED, CLINICAL_22, N_OUTER
from stats_utils import auc_fast
import features as F

sys.stdout.reconfigure(encoding="utf-8")


def site_of(ids):
    s = pd.read_csv(DATA / "inferred_site.csv").set_index("subject_id").reindex(ids)
    return np.where(s.site_inferred.str.startswith("Zurich"), "Zurich", "Munich")


def within_auc(y, p, site):
    num = den = 0.0
    for s in np.unique(site):
        k = site == s
        n1, n0 = y[k].sum(), (1 - y[k]).sum()
        if n1 == 0 or n0 == 0:
            continue
        num += auc_fast(y[k], p[k]) * n1 * n0
        den += n1 * n0
    return num / den


def describe():
    coh = pd.read_csv(DATA / "cohort_129.csv")
    coh["site"] = site_of(coh.subject_id)
    rows = []
    for c, md in list(zip(CONT, CONT_MEDIAN)) + list(zip(DUR, DUR_MEDIAN)):
        imp = np.isclose(coh[c], md, atol=1e-3)
        r = {"variable": c}
        for s in ("Munich", "Zurich"):
            r[f"pct_imputed_{s}"] = 100 * imp[coh.site == s].mean()
        t = pd.crosstab(coh.site, imp)
        r["fisher_p"] = stats.fisher_exact(t.values)[1] if t.shape == (2, 2) else np.nan
        rows.append(r)
    imp = pd.DataFrame(rows)
    imp.to_csv(TAB / "site_imputation.csv", index=False)
    g = coh.groupby("site")
    cm = pd.DataFrame({"n": g.size(), "poor": g.poor.sum(), "poor_pct": 100 * g.poor.mean(),
                       "age_median": g.Age.median(), "nihss_median": g["NIHSS at admission"].median(),
                       "premorbid_mrs_gt0_pct": 100 * g["mRS premorbid"].apply(lambda v: (v > 0).mean()),
                       "mrs90_0_pct": 100 * g.mrs90.apply(lambda v: (v == 0).mean())})
    cm["fisher_p_poor"] = stats.fisher_exact(pd.crosstab(coh.site, coh.poor).values)[1]
    cm.to_csv(TAB / "site_case_mix.csv")
    print(imp.round(1).to_string(index=False)); print(cm.round(2).to_string())


def within():
    ids, y, P = load("_all")
    site = site_of(ids)
    rng = np.random.default_rng(BOOT_SEED)
    idx_s = {s: np.nonzero(site == s)[0] for s in np.unique(site)}
    boots = [np.concatenate([rng.choice(ix, len(ix)) for ix in idx_s.values()]) for _ in range(N_BOOT)]
    zur = (site == "Zurich").astype(float)
    res = [{"model": "Centre indicator alone", "auc_pooled_seedmean": auc_fast(y, 1 - zur), "within_centre_auc": 0.5}]
    wb = {}
    for m, Pm in sorted(P.items()):
        w = np.mean([within_auc(y, p, site) for p in Pm])
        wb[m] = np.array([np.mean([within_auc(y[b], p[b], site[b]) for p in Pm]) for b in boots])
        res.append({"model": m, "auc_pooled_seedmean": np.mean([auc_fast(y, p) for p in Pm]), "within_centre_auc": w,
                    "within_lo": np.percentile(wb[m], 2.5), "within_hi": np.percentile(wb[m], 97.5),
                    "auc_munich": np.mean([auc_fast(y[site == 'Munich'], p[site == 'Munich']) for p in Pm]),
                    "auc_zurich": np.mean([auc_fast(y[site == 'Zurich'], p[site == 'Zurich']) for p in Pm])})
    out = pd.DataFrame(res)
    out.to_csv(TAB / "within_centre_auc.csv", index=False)
    comp = []
    for new, ref in [("F_late_P1_E", "P1_clin_GBM"), ("F_late_P1_Enat", "P1_clin_GBM"), ("F_late_P1_V", "P1_clin_GBM"),
                     ("F_late_R1_E", "R1_clin_LR4"), ("R1_plus_volumes", "R1_clin_LR4"), ("P1_clin_GBM", "R1_clin_LR4"),
                     ("P1_clin_GBM", "THRIVE")]:
        if new in P and ref in P:
            d = out.set_index("model").loc[new, "within_centre_auc"] - out.set_index("model").loc[ref, "within_centre_auc"]
            db = wb[new] - wb[ref]
            comp.append({"new": new, "reference": ref, "delta_within": d, "ci_lo": np.percentile(db, 2.5),
                         "ci_hi": np.percentile(db, 97.5), "p_bootstrap": min(1, 2 * min((db <= 0).mean(), (db >= 0).mean()))})
    pd.DataFrame(comp).to_csv(TAB / "within_centre_paired.csv", index=False)
    print(out.round(3).to_string(index=False)); print(pd.DataFrame(comp).round(3).to_string(index=False))


MUNICH_MODELS = {
    "P1_clin_GBM": (CLINICAL_22, "gbm"), "P2_clin_EN": (CLINICAL_22, "en"), "R1_clin_LR4": (X.R1, "lr"),
    "NIHSS_only": (["NIHSS at admission"], "lr"), "THRIVE": (["THRIVE"], "lr"),
    "E_CTP_all": (F.CTP_ALL, "en"), "E_native": ([f"nat_{c}" for c in F.CTP_ALL], "en"),
    "B_CBV": (F.CBV, "en"), "D_Tmax": (F.TMAX, "en"), "T_thresholds": (F.THRESH, "lr"),
    "V_volumes": (X.VOL, "lr"), "R1_plus_volumes": (X.R1 + X.VOL, "lr"),
}
MUNICH_LATE = {"F_late_P1_E": ("P1_clin_GBM", "E_CTP_all"), "F_late_P1_Enat": ("P1_clin_GBM", "E_native"),
               "F_late_R1_E": ("R1_clin_LR4", "E_CTP_all"), "F_late_P1_V": ("P1_clin_GBM", "V_volumes")}


def munich_cv():
    df = X.load("native")
    df = df[site_of(df.subject_id) == "Munich"].sort_values("subject_id").reset_index(drop=True)
    print("Munich n", len(df), "events", int(df.poor.sum()))
    M.run_cv(df, MUNICH_MODELS, MUNICH_LATE, N_OUTER, "_munich")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "munich_cv":
        munich_cv()
    else:
        describe(); within()
