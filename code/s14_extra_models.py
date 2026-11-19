"""Additional prespecified models, run on the SAME fold manifest as s04 (same seeds, same row order),
so their OOF predictions can be paired with the primary ones.

group "ref"    (reviewer-driven reference models)
  R1_clin_LR4   parsimonious logistic model: age, NIHSS, premorbid mRS, glucose (4 df; within the
                Riley budget) - an established-predictor benchmark that is not overfitted by design
  P1_recal      the locked clinical GBM with Platt (sigmoid) recalibration fitted by 5-fold CV inside
                each outer training fold
group "native" (native-unit maps from the original release, s13/s15)
  E_native          elastic net on the 53 features recomputed from native-unit maps
  V_volumes         logistic model on absolute volumes (log mL): core, Tmax>6 s, mismatch
  R1_plus_volumes   R1 + the three log volumes (7 df)
Late fusions are formed afterwards in s16_combine.py.
"""
import sys
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold
import s04_models_cv as M
from config import DATA, N_OUTER, N_INNER
import features as F

R1 = ["Age", "NIHSS at admission", "mRS premorbid", "Glucose"]
VOL = ["log_core_ml", "log_tmax6_ml", "log_mismatch_ml"]

GROUPS = {
    "ref": {"R1_clin_LR4": (R1, "lr"), "P1_recal": (M.CLINICAL_22, "gbm_cal")},
    "native": {"E_native": ([f"nat_{c}" for c in F.CTP_ALL], "en"), "V_volumes": (VOL, "lr"),
               "R1_plus_volumes": (R1 + VOL, "lr")},
}

_orig_fit = M.fit_model


def fit_model(kind, Xtr, ytr, seed):
    if kind == "gbm_cal":
        # ensemble=False: the calibrator is fitted on inner-CV predictions and the GBM itself is refitted
        # on the whole outer training fold, so the ranking (AUC) of P1 is preserved
        cal = CalibratedClassifierCV(M.gbm(seed), method="sigmoid", ensemble=False,
                                     cv=StratifiedKFold(N_INNER, shuffle=True, random_state=seed))
        return cal.fit(Xtr, ytr), {}
    return _orig_fit(kind, Xtr, ytr, seed)


M.fit_model = fit_model


def load(group):
    df = M.load_data()
    if group == "native":
        nat = pd.read_csv(DATA / "ctp_features_native_149.csv")
        keep = ["subject_id"] + [c for c in nat.columns if c.startswith("nat_") or c in VOL]
        df = df.merge(nat[keep], on="subject_id", how="left")
    return df.sort_values("subject_id").reset_index(drop=True)


def main(group):
    df = load(group)
    missing = [c for _, (cols, _) in GROUPS[group].items() for c in cols if c not in df.columns]
    assert not missing, missing
    M.run_cv(df, GROUPS[group], {}, N_OUTER, f"_ext_{group}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ref")
