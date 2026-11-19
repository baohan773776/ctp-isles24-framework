"""Stage A/B: cohort definition, raw-unit recovery of clinical variables, missingness audit,
THRIVE / SPAN-100 recomputation, included-vs-excluded comparison.

Scaler/imputer parameters were read from processed/tabular/clinical_preprocessor.pkl with a
restricted unpickler that executes no code (see tools/safe_pkl.py); the values are copied below.
"""
import json
import numpy as np
import pandas as pd
from config import ISLES24, DATA, TAB, CLINICAL_22, INTRA_PROCEDURAL

CONT = ["Age", "Glucose", "Leucocytes", "CRP", "INR"]
CONT_MEAN = [70.45637513182692, 111.90442065043415, 8.89565584444129, 0.7804052629031214, 1.0013139944743326]
CONT_SCALE = [15.028548687815395, 41.31863208108027, 2.2242492804406173, 1.721993095475696, 0.12239155144386016]
CONT_MEDIAN = [74.0, 108.61963752228351, 8.750170987622571, 0.20917762377817, 1.006273786856195]
DUR = ["Onset to door_min", "Alert to door_min", "Door to imaging_min", "Door to groin_min",
       "Door to first series_min", "Door to recanalization_min", "Time of intervention_min"]
DUR_MEAN = [152.3100961538462, 29.18923076923077, 24.619038461538462, 78.25807692307693,
            84.7439423076923, 134.01826923076925, 46.37596153846154]
DUR_SCALE = [184.3301928109487, 10.577133508396207, 43.651539877658706, 44.50380502481098,
             32.53990359242577, 52.01965296963602, 35.94605428676397]
DUR_MEDIAN = [111.65, 28.35, 18.54, 69.65, 79.79, 124.46, 37.065]


def thrive(age, nihss, htn, dm, af):
    a = np.where(age >= 80, 2, np.where(age >= 60, 1, 0))
    n = np.where(nihss >= 21, 4, np.where(nihss >= 11, 2, 0))
    return a + n + htn.astype(int) + dm.astype(int) + af.astype(int)


def smd(a, b, binary=False):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if binary:
        p1, p2 = a.mean(), b.mean()
        s = np.sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / 2)
    else:
        s = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return (a.mean() - b.mean()) / s if s > 0 else 0.0


def main():
    clin = pd.read_csv(ISLES24 / "tabular" / "clinical_features.csv")
    lab = pd.read_csv(ISLES24 / "labels" / "outcome_labels.csv")
    df = clin.merge(lab[["subject_id", "mRS_3_months_raw", "mRS_3_months_bin", "TICI postinterventional"]],
                    on="subject_id", how="left")
    assert len(df) == 149 and df.subject_id.is_unique

    # ---- inverse-transform to physical units; flag probable imputed entries ----
    imputed = {}
    for cols, mu, sc, med in ((CONT, CONT_MEAN, CONT_SCALE, CONT_MEDIAN), (DUR, DUR_MEAN, DUR_SCALE, DUR_MEDIAN)):
        for c, m, s, md in zip(cols, mu, sc, med):
            raw = df[c] * s + m
            imputed[c] = np.isclose(raw, md, atol=1e-3)
            df[c] = raw
    df["Age"] = df["Age"].round(0)

    # ---- outcome: poor = mRS 3-6 (event = 1) ----
    df["mrs90"] = df["mRS_3_months_raw"]
    df["included"] = df["mrs90"].notna()
    df["poor"] = np.where(df["included"], (df["mrs90"] >= 3).astype(float), np.nan)
    assert ((df["mRS_3_months_bin"] == 1) == (df["mrs90"] <= 2))[df.included].all()

    # ---- clinical scores ----
    df["THRIVE"] = thrive(df["Age"], df["NIHSS at admission"], df["Hypertension"], df["Diabetes"], df["Atrial fibrillation"])
    df["SPAN100_raw"] = df["Age"] + df["NIHSS at admission"]
    df["SPAN100_pos"] = (df["SPAN100_raw"] >= 100).astype(int)

    # cross-check with legacy benchmark file (THRIVE coding audit)
    try:
        from config import BENCH_CSV
        old = pd.read_csv(BENCH_CSV)[["subject_id", "THRIVE_score", "Age_raw"]]
        chk = df.merge(old, on="subject_id")
        audit = {"n_compared": int(len(chk)),
                 "age_max_abs_diff": float((chk["Age"] - chk["Age_raw"].round(0)).abs().max()),
                 "thrive_mismatches": int((chk["THRIVE"] != chk["THRIVE_score"]).sum()),
                 "mismatch_examples": chk.loc[chk["THRIVE"] != chk["THRIVE_score"],
                                              ["subject_id", "Age", "NIHSS at admission", "THRIVE", "THRIVE_score"]].head(10).to_dict("records")}
        json.dump(audit, open(TAB / "audit_thrive_legacy.json", "w"), indent=2, default=str)
        print("THRIVE legacy audit:", {k: v for k, v in audit.items() if k != "mismatch_examples"})
    except FileNotFoundError:
        pass

    inc = df[df.included].copy()
    exc = df[~df.included].copy()
    print(f"N total={len(df)} included={len(inc)} excluded={len(exc)}; poor={int(inc.poor.sum())} good={int((1-inc.poor).sum())}")

    # ---- missingness audit (probable imputed entries) on the analysed cohort ----
    miss = pd.DataFrame({"variable": list(imputed),
                         "n_probable_imputed": [int(imputed[c][df.included].sum()) for c in imputed]})
    miss["pct"] = (100 * miss.n_probable_imputed / len(inc)).round(1)
    miss.to_csv(TAB / "missingness_probable_imputed.csv", index=False)
    inc["any_probable_imputed"] = np.any(np.column_stack([imputed[c][df.included] for c in CONT + DUR[:3]]), axis=1)

    # ---- included vs excluded ----
    rows = []
    for v, binary in [("Age", False), ("Sex", True), ("NIHSS at admission", False), ("mRS premorbid", False),
                      ("mRS at admission", False), ("Referral", True), ("Wake-up", True), ("Atrial fibrillation", True),
                      ("Hypertension", True), ("Diabetes", True), ("Onset to door_min", False)]:
        rows.append({"variable": v, "included_mean": inc[v].mean(), "excluded_mean": exc[v].mean(),
                     "included_median": inc[v].median(), "excluded_median": exc[v].median(),
                     "SMD": smd(inc[v], exc[v], binary)})
    pd.DataFrame(rows).round(3).to_csv(TAB / "included_vs_excluded.csv", index=False)

    keep = ["subject_id", "poor", "mrs90", "TICI postinterventional", "THRIVE", "SPAN100_raw", "SPAN100_pos",
            "any_probable_imputed"] + CLINICAL_22 + INTRA_PROCEDURAL
    inc[keep].to_csv(DATA / "cohort_129.csv", index=False)
    df[["subject_id", "included", "mrs90"]].to_csv(DATA / "cohort_flow_149.csv", index=False)
    print(miss.to_string(index=False))


if __name__ == "__main__":
    main()
