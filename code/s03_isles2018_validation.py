"""Technical validation on ISLES 2018 (94 training cases; CTP maps in physical units + DWI core mask).

(1) Unit-recovery simulation: reproduce the ISLES'24 public pre-processing (clip -> resample to
    64x128x128 -> per-subject z-normalisation), then apply our recovery x = b (z - z_min) and
    compare recovered maps / features with the ground-truth maps.
(2) Physiological validity of the feature extractor: correlation of CTP-derived core / hypoperfusion
    fractions with the DWI-defined infarct-core fraction (ISLES 2018 ground truth, OT).
No outcome data exist in ISLES 2018; it is used only for technical validation.
"""
import glob
import os
import numpy as np
import pandas as pd
import nibabel as nib
from scipy import ndimage, stats
from config import ISLES18, TAB, DATA, CLIP, CHANNELS
from s02_ctp_features import features_from_maps

GRID = (64, 128, 128)
rng = np.random.default_rng(7)


def load(case_dir, key):
    f = [p for p in glob.glob(os.path.join(case_dir, "*", "*.nii")) if f".{key}." in os.path.basename(p)]
    return np.asanyarray(nib.load(f[0]).dataobj).astype(np.float64)


def resample(a, order=1):
    return ndimage.zoom(a, [g / s for g, s in zip(GRID, a.shape)], order=order)


def icc_a1(x, y):
    """ICC(A,1), two-way, absolute agreement."""
    d = np.column_stack([x, y]); n, k = d.shape
    gm = d.mean(); msr = k * ((d.mean(1) - gm) ** 2).sum() / (n - 1)
    msc = n * ((d.mean(0) - gm) ** 2).sum() / (k - 1)
    sse = ((d - d.mean(1, keepdims=True) - d.mean(0, keepdims=True) + gm) ** 2).sum()
    mse = sse / ((n - 1) * (k - 1))
    return (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n)


def main():
    cases = sorted(glob.glob(str(ISLES18 / "ISLES2018_Training" / "TRAINING" / "case_*")),
                   key=lambda p: int(p.split("_")[-1]))
    rows, frows = [], []
    for cd in cases:
        cid = os.path.basename(cd)
        raw = {nm: load(cd, f"CT_{nm}") for nm in CHANNELS}
        ot = load(cd, "OT")
        brain = np.zeros(ot.shape, bool)
        for nm in CHANNELS:
            brain |= raw[nm] > 0
        # bring CBF/CBV to ISLES'24-like magnitude (relative features are scale-invariant)
        raw["CBF"] *= 14.3 / np.median(raw["CBF"][brain & (raw["CBF"] > 0)])
        raw["CBV"] *= 2.8 / np.median(raw["CBV"][brain & (raw["CBV"] > 0)])
        truth, recov = {}, {}
        r = {"case": cid, "n_slices": ot.shape[2]}
        for nm in CHANNELS:
            x = np.clip(raw[nm], 0, CLIP[nm])
            xr = np.clip(resample(x), 0, CLIP[nm])
            truth[nm] = xr
            fg = xr > 0
            mu, sd = xr[fg].mean(), xr[fg].std()
            z = ((xr - mu) / sd).astype(np.float32).astype(np.float64)
            rec = CLIP[nm] * (z - z.min()) / (z.max() - z.min())
            recov[nm] = rec
            r[f"{nm}_true_max"] = xr.max()
            r[f"{nm}_scale_ratio"] = (CLIP[nm] / (z.max() - z.min())) / sd    # 1 = exact recovery
            m = fg
            r[f"{nm}_voxel_mape"] = float(np.mean(np.abs(rec[m] - xr[m]) / np.maximum(xr[m], 1e-3)))
        rows.append(r)
        ft = features_from_maps(truth)
        fr = features_from_maps(recov)
        otr = resample(ot, order=0) > 0.5
        tissue_n = ft["qc_tissue_vox"]
        frows.append({"case": cid, "gt_core_frac": otr.sum() / max(tissue_n, 1),
                      **{f"true__{k}": v for k, v in ft.items() if not k.startswith("qc_")},
                      **{f"rec__{k}": v for k, v in fr.items() if not k.startswith("qc_")}})
    sim = pd.DataFrame(rows)
    fe = pd.DataFrame(frows)
    sim.to_csv(TAB / "isles2018_unit_recovery_sim.csv", index=False)
    fe.to_csv(DATA / "isles2018_features_true_vs_recovered.csv", index=False)

    summ = []
    for nm in CHANNELS:
        s = sim[f"{nm}_scale_ratio"]
        summ.append({"channel": nm, "n": len(s), "pct_ceiling_reached": 100 * float((sim[f"{nm}_true_max"] >= CLIP[nm] - 1e-6).mean()),
                     "scale_ratio_median": s.median(), "scale_ratio_p5": s.quantile(.05), "scale_ratio_p95": s.quantile(.95),
                     "pct_within_5pct": 100 * float((s.sub(1).abs() <= .05).mean()), "voxel_mape_median": sim[f"{nm}_voxel_mape"].median()})
    pd.DataFrame(summ).round(4).to_csv(TAB / "isles2018_unit_recovery_summary.csv", index=False)
    print(pd.DataFrame(summ).round(4).to_string(index=False))

    feats = [c[6:] for c in fe.columns if c.startswith("true__")]
    agree = []
    for k in feats:
        x, y = fe[f"true__{k}"].values, fe[f"rec__{k}"].values
        ok = np.isfinite(x) & np.isfinite(y)
        rho_gt = stats.spearmanr(fe.loc[ok, "gt_core_frac"], x[ok]).correlation
        agree.append({"feature": k, "ICC_true_vs_recovered": icc_a1(x[ok], y[ok]), "spearman_true_vs_rec": stats.spearmanr(x[ok], y[ok]).correlation,
                      "spearman_with_DWI_core": rho_gt})
    ag = pd.DataFrame(agree)
    ag.round(4).to_csv(TAB / "isles2018_feature_agreement.csv", index=False)
    print(ag.round(3).sort_values("ICC_true_vs_recovered").to_string(index=False))


if __name__ == "__main__":
    main()
