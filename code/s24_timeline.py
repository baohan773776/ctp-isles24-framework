"""H3 (PLAN_v4_prespecified.md): prognostic information across the care pathway.

  python s24_timeline.py setA      full cohort: R1_DWI, DWI_only on the primary fold manifest -> oof_long_ext_timeline.csv
  python s24_timeline.py setB      Munich only: R1 -> +NIHSS 24 h -> +DWI, each +/- pre-treatment CTP (E)
  python s24_timeline.py setBcc    same, complete cases for NIHSS 24 h
  python s24_timeline.py eval      paired comparisons (same bootstrap scheme as s05) -> tables/timeline_*.csv
"""
import sys
import numpy as np
import pandas as pd
import s04_models_cv as M
import s14_extra_models as X
from s05_evaluate import load, seed_auc
from s21_site_effects import site_of, within_auc
from config import DATA, TAB, ISLES24, N_OUTER, N_BOOT, BOOT_SEED, CLINICAL_22
from stats_utils import calib
import features as F

sys.stdout.reconfigure(encoding="utf-8")
DWI = ["log_dwi_ml"]
N24 = ["NIHSS_24h"]


def data():
    df = X.load("native")
    nat = pd.read_csv(DATA / "ctp_features_native_149.csv")[["subject_id", "dwi_final_ml"]]
    lab = pd.read_csv(ISLES24 / "labels" / "outcome_labels.csv")[["subject_id", "NIHSS 24h"]].rename(columns={"NIHSS 24h": "NIHSS_24h"})
    df = df.merge(nat, on="subject_id").merge(lab, on="subject_id", how="left")
    df["log_dwi_ml"] = np.log1p(df["dwi_final_ml"])
    return df.sort_values("subject_id").reset_index(drop=True)


SET_A = {"DWI_only": (DWI, "lr"), "R1_DWI": (X.R1 + DWI, "lr")}
SET_B = {"R1_clin_LR4": (X.R1, "lr"), "R1_N24": (X.R1 + N24, "lr"), "R1_N24_DWI": (X.R1 + N24 + DWI, "lr"),
         "P1_clin_GBM": (CLINICAL_22, "gbm"), "E_CTP_all": (F.CTP_ALL, "en")}
LATE_B = {"R1_plus_E": ("R1_clin_LR4", "E_CTP_all"), "R1_N24_plus_E": ("R1_N24", "E_CTP_all"),
          "R1_N24_DWI_plus_E": ("R1_N24_DWI", "E_CTP_all")}


def setA():
    M.run_cv(data(), SET_A, {}, N_OUTER, "_ext_timeline")


def setB(cc=False):
    df = data()
    df = df[site_of(df.subject_id) == "Munich"]
    if cc:
        df = df[df.NIHSS_24h.notna()]
    df = df.reset_index(drop=True)
    print("n", len(df), "events", int(df.poor.sum()), "NIHSS24h missing", int(df.NIHSS_24h.isna().sum()))
    M.run_cv(df, SET_B, LATE_B, N_OUTER, "_munich_timeline" + ("_cc" if cc else ""))


def paired(tag, pairs, label):
    ids, y, P = load(tag)
    n = len(y)
    rng = np.random.default_rng(BOOT_SEED)
    boots = []
    while len(boots) < N_BOOT:
        b = rng.integers(0, n, n)
        if 0 < y[b].sum() < n:
            boots.append(b)
    site = site_of(ids)
    perf = []
    for m in sorted(P):
        bt = np.array([seed_auc(y, P[m], b) for b in boots])
        c = calib(y, P[m].mean(0))
        perf.append({"set": label, "model": m, "n": n, "events": int(y.sum()), "auc": seed_auc(y, P[m]),
                     "auc_lo": np.percentile(bt, 2.5), "auc_hi": np.percentile(bt, 97.5),
                     "within_centre_auc": np.mean([within_auc(y, p, site) for p in P[m]]),
                     "cal_slope": c["slope"], "brier": np.mean([np.mean((p - y) ** 2) for p in P[m]])})
    comp = []
    for new, ref, role in pairs:
        if new not in P or ref not in P:
            continue
        db = np.array([seed_auc(y, P[new], b) - seed_auc(y, P[ref], b) for b in boots])
        comp.append({"set": label, "new": new, "reference": ref, "role": role,
                     "delta_auc": seed_auc(y, P[new]) - seed_auc(y, P[ref]),
                     "ci_lo": np.percentile(db, 2.5), "ci_hi": np.percentile(db, 97.5),
                     "p_bootstrap": min(1.0, 2 * min((db <= 0).mean(), (db >= 0).mean()))})
    return pd.DataFrame(perf), pd.DataFrame(comp)


def evaluate():
    pa, ca = paired("_all", [
        ("R1_DWI", "R1_clin_LR4", "PRIMARY H3: follow-up infarct volume added to admission model"),
        ("R1_DWI_plus_E", "R1_DWI", "pre-treatment CTP once final infarct known"),
        ("P1_plus_DWI", "P1_clin_GBM", "infarct volume added to clinical GBM"),
        ("DWI_only", "E_CTP_all", "final infarct volume vs pre-treatment CTP"),
        ("R1_DWI", "F_late_P1_E", "post-treatment simple model vs best pre-treatment model")], "A: full cohort")
    out_p, out_c = [pa], [ca]
    for tag, lab in (("_munich_timeline", "B: Munich"), ("_munich_timeline_cc", "B: Munich, complete NIHSS 24 h")):
        pb, cb = paired(tag, [
            ("R1_N24", "R1_clin_LR4", "24-h NIHSS added"),
            ("R1_N24_DWI", "R1_N24", "follow-up infarct volume added at T2"),
            ("R1_N24_DWI", "R1_clin_LR4", "T2 vs T0"),
            ("R1_plus_E", "R1_clin_LR4", "CTP at T0"),
            ("R1_N24_plus_E", "R1_N24", "CTP at T1"),
            ("R1_N24_DWI_plus_E", "R1_N24_DWI", "CTP at T2")], lab)
        out_p.append(pb); out_c.append(cb)
    P = pd.concat(out_p); C = pd.concat(out_c)
    P.to_csv(TAB / "timeline_performance.csv", index=False); C.to_csv(TAB / "timeline_paired.csv", index=False)
    print(P.round(3).to_string(index=False)); print(C.round(3).to_string(index=False))


if __name__ == "__main__":
    {"setA": setA, "setB": setB, "setBcc": lambda: setB(True), "eval": evaluate}[sys.argv[1]]()
