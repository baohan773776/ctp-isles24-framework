"""Combine primary and additional OOF predictions (identical fold manifest) and form the additional
equal-weight late fusions. Output: outputs/oof/oof_long_all.csv (evaluate with `python s05_evaluate.py _all`)."""
import pandas as pd
from config import OOF

LATE_EXTRA = {
    "F_late_R1_E": ("R1_clin_LR4", "E_CTP_all"),
    "F_late_P1recal_E": ("P1_recal", "E_CTP_all"),
    "F_late_P1_Enat": ("P1_clin_GBM", "E_native"),
    "F_late_P1_V": ("P1_clin_GBM", "V_volumes"),
    "F_late_R1_V": ("R1_clin_LR4", "V_volumes"),
    # round 4 (PLAN_v4_prespecified.md)
    "R1_DWI_plus_E": ("R1_DWI", "E_CTP_all"),
    "P1_plus_DWI": ("P1_clin_GBM", "DWI_only"),
    "F_loc": ("P1_clin_GBM", "Loc_CTP"),
}


def main():
    parts = [pd.read_csv(OOF / "oof_long.csv")]
    for tag in ("_ext_ref", "_ext_native", "_ext_timeline", "_ext_location"):
        f = OOF / f"oof_long{tag}.csv"
        if f.exists():
            parts.append(pd.read_csv(f))
    o = pd.concat(parts, ignore_index=True)
    # every model must share the primary fold manifest
    man = o.drop_duplicates(["model", "seed", "subject_id"]).pivot_table(index=["seed", "subject_id"], columns="model",
                                                                         values="fold", aggfunc="first")
    assert (man.nunique(axis=1) == 1).all(), "fold manifests differ"
    w = o.pivot_table(index=["subject_id", "seed", "fold", "y"], columns="model", values="p_poor").reset_index()
    for name, (a, b) in LATE_EXTRA.items():
        if a in w and b in w:
            w[name] = 0.5 * w[a] + 0.5 * w[b]
    long = w.melt(id_vars=["subject_id", "seed", "fold", "y"], var_name="model", value_name="p_poor").dropna()
    long.to_csv(OOF / "oof_long_all.csv", index=False)
    print(sorted(long.model.unique()))


if __name__ == "__main__":
    main()
