# Final fitted models (research use only)

Fitted on all 129 analysed ISLES'24 patients by `w08_freeze_models.py`; the specifications are those of the cross-validated models in the manuscript. All performance figures in the paper come from nested cross-validation, not from these fits.

| File | Model |
|---|---|
| clinical_gbm_5seed.joblib | gradient boosting on 22 clinical predictors, locked configuration; five fits (seeds 42, 100, 2024, 777, 999), prediction = mean |
| ctp_elastic_net.joblib | elastic-net logistic regression on 53 CTP features (recovered units); C and l1_ratio tuned by 5-fold CV |
| parsimonious_logistic.joblib | logistic regression on age, admission NIHSS, premorbid mRS, glucose |
| model_card.json | training data, inputs, fusion rule, cross-validated performance, warnings, software versions, SHA256 |

Fusion rule: p = 0.5 × p(clinical GBM) + 0.5 × p(CTP elastic net).

Apply to a new cohort: `python apply_frozen_models.py . new_cohort.csv scored.csv` (column lists in features_*.txt).

Warnings: the clinical GBM is overconfident (cross-validated calibration slope 0.58) and reaches an apparent AUC of 1.00 on its training data; recalibrate before any use. CTP inputs must be in physical units with the same clip limits; on ISLES 2018 the maps had to be rescaled first. Use the scikit-learn version recorded in model_card.json. Trained on CC BY-NC-SA 4.0 data: non-commercial use.
