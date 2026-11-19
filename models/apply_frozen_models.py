"""Apply the frozen models to a new cohort (research use only).

Usage:
    python apply_frozen_models.py <models_dir> <input.csv> <output.csv>

input.csv must contain one row per patient with a 'subject_id' column, the 22 clinical columns listed in
features_clinical_22.txt and the 53 CTP feature columns listed in features_ctp_53.txt (computed with
s02_ctp_features.features_from_maps on maps in physical units). Missing values are imputed with the training medians
stored inside each pipeline. If an outcome column 'poor' (1 = mRS 3-6) is present, the AUC of each model is printed.
The scikit-learn version should match model_card.json.
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


def main(models_dir, inp, out):
    md = Path(models_dir)
    card = json.loads((md / "model_card.json").read_text(encoding="utf-8"))
    gbm = joblib.load(md / "clinical_gbm_5seed.joblib")
    en = joblib.load(md / "ctp_elastic_net.joblib")
    r1 = joblib.load(md / "parsimonious_logistic.joblib")
    df = pd.read_csv(inp)
    need = set(gbm["features"]) | set(en["features"]) | set(r1["features"])
    miss = sorted(need - set(df.columns))
    if miss:
        sys.exit(f"missing columns ({len(miss)}): {miss}")
    p_clin = np.mean([m.predict_proba(df[gbm["features"]].values)[:, 1] for m in gbm["models"]], axis=0)
    p_ctp = en["model"].predict_proba(df[en["features"]].values)[:, 1]
    res = pd.DataFrame({"subject_id": df["subject_id"],
                        "p_clinical_gbm": p_clin, "p_ctp_elastic_net": p_ctp,
                        "p_fusion": 0.5 * p_clin + 0.5 * p_ctp,
                        "p_parsimonious_logistic": r1["model"].predict_proba(df[r1["features"]].values)[:, 1]})
    res.to_csv(out, index=False)
    print(f"{len(res)} patients scored -> {out}  (trained with scikit-learn {card['software']['scikit-learn']})")
    if "poor" in df.columns:
        from sklearn.metrics import roc_auc_score
        y = df["poor"].astype(int).values
        for c in res.columns[1:]:
            print(f"{c}: AUC {roc_auc_score(y, res[c]):.3f}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
