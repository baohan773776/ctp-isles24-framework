"""Experiment D, step 3: H1 with admission-time (NCCT-registered) vs canonical (DWI-registered) CTP location features.

Both feature versions are refitted in ONE run on the canonical fold manifest (5 seeds x 10-fold; s04.run_cv, with its
outputs redirected to outputs_validity), with the identical model definitions of s26:
  Loc_CTP_* = elastic net on the 4 regional Tmax > 6 s fractions; F_loc_* = 0.5 P1 + 0.5 Loc_CTP_*.
Primary contrast of the experiment: F_loc_ncct - P1 (H1 at admission time); also F_loc_ncct - F_loc_dwi.
Sensitivity: excluding poor NCCT registrations (Dice vs NCCT intracranial mask < 0.80).
Agreement of features: ICC(3,1) and Spearman per region between the two registrations.
"""
import numpy as np
import pandas as pd
from scipy import stats
from v_common import VOOF, VTAB, VDATA, OOF, boot_indices, perf_and_pairs, load_oof
import s04_models_cv as M
from config import CLINICAL_22, N_OUTER

M.OOF = VOOF   # never write into the canonical oof folder
REG = ("CST", "DEEP", "INSOP", "LANG")
NC = [f"ncct__loc_ctp_{r}" for r in REG]
DW = [f"dwi__loc_ctp_{r}" for r in REG]
MODELS = {"P1_clin_GBM": (CLINICAL_22, "gbm"), "Loc_CTP_ncct": (NC, "en"), "Loc_CTP_dwi": (DW, "en")}
LATE = {"F_loc_ncct": ("P1_clin_GBM", "Loc_CTP_ncct"), "F_loc_dwi": ("P1_clin_GBM", "Loc_CTP_dwi")}
PAIRS = [("F_loc_ncct", "P1_clin_GBM", "H1 at admission time: NCCT-registered location added to P1"),
         ("F_loc_dwi", "P1_clin_GBM", "H1 as canonical: DWI-registered location added to P1 (re-run)"),
         ("F_loc_ncct", "F_loc_dwi", "NCCT vs DWI registration, fused model"),
         ("Loc_CTP_ncct", "Loc_CTP_dwi", "NCCT vs DWI registration, location only")]


def icc31(a, b):
    x = np.c_[a, b]; x = x[np.isfinite(x).all(1)]; n, k = x.shape; gm = x.mean()
    ssr = k * ((x.mean(1) - gm) ** 2).sum(); ssc = n * ((x.mean(0) - gm) ** 2).sum()
    sse = ((x - gm) ** 2).sum() - ssr - ssc
    msr, mse = ssr / (n - 1), sse / ((n - 1) * (k - 1))
    return (msr - mse) / (msr + (k - 1) * mse)


def main():
    L = pd.read_csv(VDATA / "vD_location_features_ncct.csv")
    df = M.load_data().merge(L, on="subject_id", how="left")
    assert df[NC + DW].notna().mean().min() > 0.5
    # registration quality / coverage / agreement
    q = []
    inc = df
    for tag in ("ncct", "dwi"):
        d = inc[f"{tag}_reg_dice_vs_ncct_ic"]
        q.append({"registration": tag, "n": int(d.notna().sum()), "dice_vs_ncct_ic_median": d.median(),
                  "q1": d.quantile(.25), "q3": d.quantile(.75), "n_dice_lt_0.80": int((d < 0.80).sum()),
                  **{f"coverage_{r}_median": inc[f"{tag}__ctp_{r}_coverage"].median() for r in REG},
                  **{f"missing_{r}": int(inc[f"{tag}__loc_ctp_{r}"].isna().sum()) for r in REG}})
    pd.DataFrame(q).to_csv(VTAB / "vD_registration_quality.csv", index=False)
    ag = []
    for r in REG:
        a, b = inc[f"ncct__loc_ctp_{r}"].values, inc[f"dwi__loc_ctp_{r}"].values
        ok = np.isfinite(a) & np.isfinite(b)
        ag.append({"region": r, "n": int(ok.sum()), "icc31": icc31(a[ok], b[ok]), "spearman": stats.spearmanr(a[ok], b[ok])[0],
                   "median_abs_diff": np.median(np.abs(a[ok] - b[ok])), "atlas_concordance_dice_median": inc[f"concordance_dice_{r}"].median()})
    pd.DataFrame(ag).to_csv(VTAB / "vD_location_feature_agreement.csv", index=False)
    print(pd.DataFrame(q).round(3).T.to_string()); print(pd.DataFrame(ag).round(3).to_string(index=False))
    # canonical feature check: re-run DWI features equal the canonical location_features.csv?
    canon = pd.read_csv(M.DATA / "location_features.csv").set_index("subject_id")
    x = inc.set_index("subject_id")
    print("max |rerun DWI - canonical| per region:",
          {r: float(np.nanmax(np.abs(x[f"dwi__loc_ctp_{r}"] - canon.loc[x.index, f"loc_ctp_{r}"]))) for r in REG})

    M.run_cv(df, MODELS, LATE, N_OUTER, "_vD_location", verbose=False)
    good = df[df.ncct_reg_dice_vs_ncct_ic >= 0.80].reset_index(drop=True)
    print("NCCT Dice >= 0.80:", len(good), "events", int(good.poor.sum()))
    M.run_cv(good, MODELS, LATE, N_OUTER, "_vD_location_dice80", verbose=False)
    perf, comp = [], []
    for tag, lab in (("_vD_location", "full cohort"), ("_vD_location_dice80", "NCCT registration Dice >= 0.80")):
        ids, y, P = load_oof(VOOF / f"oof_long{tag}.csv")
        p, c = perf_and_pairs(y, P, PAIRS, boot_indices(y), label=lab)
        perf.append(p); comp.append(c)
    pd.concat(perf).to_csv(VTAB / "vD_h1_performance.csv", index=False)
    pd.concat(comp).to_csv(VTAB / "vD_h1_paired.csv", index=False)
    print(pd.concat(comp)[["analysis", "new", "reference", "n", "delta_auc", "ci_lo", "ci_hi", "p_bootstrap"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
