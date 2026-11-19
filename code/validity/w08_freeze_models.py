"""Fit and save the final (frozen) models on the full analysed cohort (n = 129) for hand-over and future external
validation. Nothing here changes any reported estimate: all performance figures in the manuscript come from nested
cross-validation. The apparent (in-sample) AUCs written below are a sanity check only and are optimistic by design.

Models (same specifications as the cross-validated models in the manuscript):
  clinical_gbm            gradient boosting on the 22 clinical predictors, fixed configuration (80 trees, depth 3,
                          learning rate 0.1, subsample 0.7); one fit per evaluation seed (42, 100, 2024, 777, 999),
                          prediction = mean of the five fits
  ctp_elastic_net         elastic-net logistic regression on the 53 CTP features (recovered units), C and l1_ratio
                          chosen by stratified 5-fold CV (neg. log-loss) on the full cohort
  parsimonious_logistic   logistic regression (C = 1) on age, admission NIHSS, premorbid mRS, glucose
  fusion rule             p = 0.5 * p_clinical_gbm + 0.5 * p_ctp_elastic_net (no trainable parameters)
Outputs: analysis_v3/outputs_validity/models/ (joblib files, model_card.json, feature lists).
"""
import hashlib
import json
import platform
from datetime import date

import joblib
import numpy as np
import sklearn
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold

from v_common import VOUT, SEEDS  # noqa: F401  (sets sys.path to the canonical modules)
from config import CLINICAL_22, N_INNER
import features as F
import s04_models_cv as M

MD = VOUT / "models"
MD.mkdir(parents=True, exist_ok=True)
R1 = ["Age", "NIHSS at admission", "mRS premorbid", "Glucose"]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    df = M.load_data()
    y = df["poor"].astype(int).values
    Xc, Xe, Xr = df[CLINICAL_22].values, df[F.CTP_ALL].values, df[R1].values
    assert len(F.CTP_ALL) == 53 and len(CLINICAL_22) == 22

    gbms = [M.gbm(s).fit(Xc, y) for s in SEEDS]
    gs = GridSearchCV(M.en_pipe(), M.EN_GRID, scoring="neg_log_loss",
                      cv=StratifiedKFold(N_INNER, shuffle=True, random_state=SEEDS[0]), n_jobs=-1, refit=True).fit(Xe, y)
    en = gs.best_estimator_
    r1 = M.lr_fixed().fit(Xr, y)

    files = {"clinical_gbm_5seed.joblib": {"seeds": SEEDS, "models": gbms, "features": CLINICAL_22},
             "ctp_elastic_net.joblib": {"model": en, "features": F.CTP_ALL,
                                        "best_params": {k.replace("lr__", ""): v for k, v in gs.best_params_.items()}},
             "parsimonious_logistic.joblib": {"model": r1, "features": R1}}
    for fn, obj in files.items():
        joblib.dump(obj, MD / fn, compress=3)

    p_clin = np.mean([m.predict_proba(Xc)[:, 1] for m in gbms], axis=0)
    p_ctp = en.predict_proba(Xe)[:, 1]
    p_fus = 0.5 * p_clin + 0.5 * p_ctp
    p_r1 = r1.predict_proba(Xr)[:, 1]
    apparent = {k: round(float(roc_auc_score(y, v)), 3) for k, v in
                {"clinical_gbm": p_clin, "ctp_elastic_net": p_ctp, "fusion": p_fus, "parsimonious_logistic": p_r1}.items()}

    for name, cols in {"features_clinical_22.txt": CLINICAL_22, "features_ctp_53.txt": F.CTP_ALL,
                       "features_parsimonious_4.txt": R1}.items():
        (MD / name).write_text("\n".join(cols) + "\n", encoding="utf-8")

    card = {
        "created": str(date.today()),
        "training_data": "ISLES'24 training set, patients with 90-day mRS (n = 129, 44 with mRS 3-6); CC BY-NC-SA 4.0",
        "outcome": "P(mRS 3-6 at 90 days)",
        "intended_use": "research only: external validation of the feasibility estimates on an independent cohort; "
                        "not for clinical decision-making",
        "input_requirements": {
            "clinical": "22 pre-procedural variables in physical units, column names as in features_clinical_22.txt "
                        "(missing values allowed; median imputation fitted on the training cohort is inside each pipeline)",
            "ctp": "53 CTP features computed with s02_ctp_features.features_from_maps on CBF/CBV/MTT/Tmax maps in "
                   "physical units, clipped to CBF 100, CBV 10, MTT 30, Tmax 30 (same grid handling as the paper)",
        },
        "fusion_rule": "p = 0.5 * p_clinical_gbm + 0.5 * p_ctp_elastic_net",
        "ctp_elastic_net_params": files["ctp_elastic_net.joblib"]["best_params"],
        "cross_validated_performance_reported_in_paper": {
            "clinical_gbm_auc": "0.763 (95% CI 0.673-0.841); calibration slope 0.58 (overconfident)",
            "fusion_auc": "0.774 (95% CI 0.690-0.850); delta vs clinical +0.011 (-0.039 to +0.068)",
            "parsimonious_logistic_auc": "0.681 (95% CI 0.572-0.778)",
        },
        "apparent_auc_in_sample_NOT_a_performance_estimate": apparent,
        "warnings": [
            "The clinical GBM is overconfident (cross-validated calibration slope 0.58); recalibrate before any use.",
            "Absolute CTP thresholds are not unit-transportable: on ISLES 2018 the maps had to be rescaled first.",
            "Trained on 129 patients from two inferred centres; transportability is untested.",
        ],
        "software": {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
                     "numpy": np.__version__, "joblib": joblib.__version__},
        "sha256": {fn: sha(MD / fn) for fn in files},
    }
    (MD / "model_card.json").write_text(json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"apparent": apparent, "en_params": card["ctp_elastic_net_params"],
                      "sizes_kb": {fn: round((MD / fn).stat().st_size / 1024) for fn in files}}, indent=1))


if __name__ == "__main__":
    main()
