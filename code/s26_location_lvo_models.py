"""H1 and H2 models (PLAN_v4_prespecified.md).

  python s26_location_lvo_models.py loc       full cohort, primary fold manifest -> oof_long_ext_location.csv
  python s26_location_lvo_models.py loc80     sensitivity: registration Dice >= 0.80 only
  python s26_location_lvo_models.py lvo       H2: nested CV within patients with a non-empty native LVO mask
  python s26_location_lvo_models.py eval      paired comparisons -> tables/location_*.csv, tables/lvo_*.csv
"""
import sys
import numpy as np
import pandas as pd
import s04_models_cv as M
import s14_extra_models as X
from s24_timeline import data as tdata, paired
from config import DATA, TAB, N_OUTER, CLINICAL_22
import features as F

sys.stdout.reconfigure(encoding="utf-8")
LOC_CTP = [f"loc_ctp_{r}" for r in ("CST", "DEEP", "INSOP", "LANG")]
LOC_DWI = [f"loc_dwi_{r}" for r in ("CST", "DEEP", "INSOP", "LANG")]


def data():
    df = tdata()
    loc = pd.read_csv(DATA / "location_features.csv")
    df = df.merge(loc[["subject_id", "reg_dice"] + LOC_CTP + LOC_DWI], on="subject_id", how="left")
    return df.sort_values("subject_id").reset_index(drop=True)


LOC_MODELS = {"Loc_CTP": (LOC_CTP, "en"), "R1_Loc_CTP": (X.R1 + LOC_CTP, "en"),
              "R1_DWI_Loc": (X.R1 + ["log_dwi_ml"] + LOC_DWI, "en")}
SENS_MODELS = {"P1_clin_GBM": (CLINICAL_22, "gbm"), "R1_clin_LR4": (X.R1, "lr"), "R1_DWI": (X.R1 + ["log_dwi_ml"], "lr"),
               **LOC_MODELS}
SENS_LATE = {"F_loc": ("P1_clin_GBM", "Loc_CTP")}
LVO_MODELS = {"P1_clin_GBM": (CLINICAL_22, "gbm"), "R1_clin_LR4": (X.R1, "lr"), "E_CTP_all": (F.CTP_ALL, "en"),
              "Loc_CTP": (LOC_CTP, "en")}
LVO_LATE = {"F_late_P1_E": ("P1_clin_GBM", "E_CTP_all"), "F_late_R1_E": ("R1_clin_LR4", "E_CTP_all"),
            "F_loc": ("P1_clin_GBM", "Loc_CTP")}


def lvo_population(df):
    nat = pd.read_csv(DATA / "ctp_features_native_149.csv").set_index("subject_id")
    return nat.loc[df.subject_id, "nat_qc_lvo_side"].notna().values


def run(which):
    df = data()
    if which == "loc":
        M.run_cv(df, LOC_MODELS, {}, N_OUTER, "_ext_location")
    elif which == "loc80":
        d = df[df.reg_dice >= 0.80].reset_index(drop=True)
        print("Dice>=0.80:", len(d), "events", int(d.poor.sum()))
        M.run_cv(d, SENS_MODELS, SENS_LATE, N_OUTER, "_loc_dice80")
    elif which == "lvo":
        d = df[lvo_population(df)].reset_index(drop=True)
        print("LVO population:", len(d), "events", int(d.poor.sum()))
        M.run_cv(d, LVO_MODELS, LVO_LATE, N_OUTER, "_lvo")


def evaluate():
    out_p, out_c = [], []
    p, c = paired("_all", [
        ("F_loc", "P1_clin_GBM", "PRIMARY H1: CTP location features added to clinical GBM"),
        ("R1_Loc_CTP", "R1_clin_LR4", "CTP location features in a joint model"),
        ("Loc_CTP", "E_CTP_all", "location vs volumetric/relative CTP features"),
        ("Loc_CTP", "V_volumes", "location vs absolute volumes"),
        ("R1_DWI_Loc", "R1_DWI", "final-infarct location added to infarct volume")], "H1: full cohort")
    out_p.append(p); out_c.append(c)
    p, c = paired("_loc_dice80", [
        ("F_loc", "P1_clin_GBM", "H1 sensitivity: Dice >= 0.80"),
        ("R1_DWI_Loc", "R1_DWI", "H1b sensitivity: Dice >= 0.80")], "H1: registration Dice >= 0.80")
    out_p.append(p); out_c.append(c)
    p, c = paired("_lvo", [
        ("F_late_P1_E", "P1_clin_GBM", "PRIMARY H2 (hypothesis-generating): CTP within LVO population"),
        ("F_late_R1_E", "R1_clin_LR4", "CTP within LVO population, parsimonious reference"),
        ("F_loc", "P1_clin_GBM", "CTP location within LVO population")], "H2: LVO population")
    out_p.append(p); out_c.append(c)
    P = pd.concat(out_p); C = pd.concat(out_c)
    P.to_csv(TAB / "location_lvo_performance.csv", index=False); C.to_csv(TAB / "location_lvo_paired.csv", index=False)
    print(P.round(3).to_string(index=False)); print(C.round(3).to_string(index=False))


if __name__ == "__main__":
    evaluate() if sys.argv[1] == "eval" else run(sys.argv[1])
