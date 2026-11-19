"""Geographic (leave-one-centre-out) validation with the inferred centre labels (s19).

Each model is developed on all patients of one centre (inner CV for penalised models; GBM and inner
CV averaged over the 5 evaluation seeds) and applied unchanged to the other centre.
Munich -> Zurich is the informative direction (development 88 patients / 38 events); Zurich -> Munich
has only 6 development events and is reported for completeness.
Metrics on the external centre: AUC (2000-resample bootstrap CI), paired delta AUC versus the clinical
reference, calibration slope, calibration-in-the-large, observed/expected ratio and Brier score.
"""
import sys
import warnings
import numpy as np
import pandas as pd
import s04_models_cv as M
import s14_extra_models as X   # registers the gbm_cal kind and the R1/volume feature lists
from config import DATA, TAB, SEEDS, N_BOOT, BOOT_SEED, CLINICAL_22
from stats_utils import auc_fast, calib
import features as F

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
NAT = [f"nat_{c}" for c in F.CTP_ALL]
MODELS = {
    "P1_clin_GBM": (CLINICAL_22, "gbm"), "P2_clin_EN": (CLINICAL_22, "en"), "R1_clin_LR4": (X.R1, "lr"),
    "E_CTP_all": (F.CTP_ALL, "en"), "E_native": (NAT, "en"), "V_volumes": (X.VOL, "lr"),
    "R1_plus_volumes": (X.R1 + X.VOL, "lr"),
}
LATE = {"F_late_P1_E": ("P1_clin_GBM", "E_CTP_all"), "F_late_P1_Enat": ("P1_clin_GBM", "E_native"),
        "F_late_R1_E": ("R1_clin_LR4", "E_CTP_all"), "F_late_P1_V": ("P1_clin_GBM", "V_volumes")}
PAIRS = [("F_late_P1_E", "P1_clin_GBM"), ("F_late_P1_Enat", "P1_clin_GBM"), ("F_late_P1_V", "P1_clin_GBM"),
         ("F_late_R1_E", "R1_clin_LR4"), ("R1_plus_volumes", "R1_clin_LR4"), ("P1_clin_GBM", "R1_clin_LR4")]


def data():
    df = X.load("native").merge(pd.read_csv(DATA / "inferred_site.csv")[["subject_id", "site_inferred"]], on="subject_id")
    df["site"] = np.where(df.site_inferred.str.startswith("Zurich"), "Zurich", "Munich")
    return df


def predict(dev, ext):
    y = dev.poor.astype(int).values
    P = {}
    for name, (cols, kind) in MODELS.items():
        ps = []
        for s in SEEDS:
            m, _ = M.fit_model(kind, dev[cols].values, y, s)
            ps.append(m.predict_proba(ext[cols].values)[:, 1])
            if kind == "lr":   # deterministic: one fit is enough
                break
        P[name] = np.mean(ps, axis=0)
    for name, (a, b) in LATE.items():
        P[name] = 0.5 * P[a] + 0.5 * P[b]
    return P


def evaluate(y, P, direction, rng):
    n = len(y)
    boots = []
    while len(boots) < N_BOOT:
        b = rng.integers(0, n, n)
        if 0 < y[b].sum() < n:
            boots.append(b)
    rows = []
    for m, p in P.items():
        c = calib(y, p)
        bt = np.array([auc_fast(y[b], p[b]) for b in boots])
        rows.append({"direction": direction, "model": m, "n": n, "events": int(y.sum()), "auc": auc_fast(y, p),
                     "auc_lo": np.percentile(bt, 2.5), "auc_hi": np.percentile(bt, 97.5), "cal_slope": c["slope"],
                     "citl": c["citl"], "o_e": y.mean() / p.mean(), "brier": c["brier"]})
    comp = []
    for new, ref in PAIRS:
        d = auc_fast(y, P[new]) - auc_fast(y, P[ref])
        db = np.array([auc_fast(y[b], P[new][b]) - auc_fast(y[b], P[ref][b]) for b in boots])
        comp.append({"direction": direction, "new": new, "reference": ref, "delta_auc": d,
                     "ci_lo": np.percentile(db, 2.5), "ci_hi": np.percentile(db, 97.5),
                     "p_bootstrap": min(1.0, 2 * min((db <= 0).mean(), (db >= 0).mean()))})
    return rows, comp


def main():
    df = data()
    rng = np.random.default_rng(BOOT_SEED)
    print(df.groupby("site").poor.agg(["size", "sum"]))
    rows, comps = [], []
    for dev_site, ext_site in (("Munich", "Zurich"), ("Zurich", "Munich")):
        dev, ext = df[df.site == dev_site].reset_index(drop=True), df[df.site == ext_site].reset_index(drop=True)
        P = predict(dev, ext)
        r, c = evaluate(ext.poor.astype(int).values, P, f"{dev_site} -> {ext_site}", rng)
        rows += r; comps += c
    perf = pd.DataFrame(rows); comp = pd.DataFrame(comps)
    perf.to_csv(TAB / "geographic_validation_performance.csv", index=False)
    comp.to_csv(TAB / "geographic_validation_paired.csv", index=False)
    print(perf.round(3).to_string(index=False))
    print(comp.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
