"""External technical component benchmark 1 (post hoc): frozen CTP feature/core extraction on ISLES 2018.

Unit of analysis: PATIENT. The 94 labelled training cases are 94 CTP slabs from 63 patients (31 patients
contribute two slabs); the mapping is read from the SMIR object description ("Train_<patient>_<slab>").
Frozen pipeline: s02.features_from_maps with no parameter changed and nothing learned from the reference labels.
Two input scalings are reported (both label-free): (i) maps as distributed, clipped to [0, CLIP];
(ii) the s03 harmonisation (CBF and CBV rescaled so that their whole-slab median equals the ISLES'24 contralateral
medians, 14.3 and 2.8), which only affects the absolute tissue-mask limits (relative features are scale-free).
Reference: the ISLES 2018 'OT' mask = infarct core delineated on DWI acquired after the CTP (challenge ground truth).
Compatible binary comparison: CTP core of the frozen pipeline (ipsilateral Tmax > 6 s AND rCBF < 30% of the
contralateral median) vs the DWI core. Tmax > 6 s hypoperfusion is NOT the same target as the DWI core, so it is only
summarised as coverage of the DWI core (sanity check), not as Dice.
Metrics per patient (voxel counts pooled over that patient's slabs): Dice, sensitivity, precision, volumes (mL),
volume difference (Bland-Altman); 95% CIs by patient-level bootstrap (2000 resamples). Voxels are never treated as
independent observations. Stratification by acquisition-protocol group (in-plane matrix and slice thickness;
centres are not labelled in ISLES 2018). No outcome is available, so no prognostic metric is computed.
Outputs: outputs_validity/data/vX1_isles2018_per_slab.csv, _per_patient.csv; tables/vX1_*.csv
"""
import glob
import json
import os
import re
import numpy as np
import pandas as pd
import nibabel as nib
from scipy import stats
from joblib import Parallel, delayed
from v_common import VDATA, VTAB
from config import ISLES18, CLIP, CHANNELS
from s02_ctp_features import features_from_maps
import features as F

EPS = 1e-6


def load(case_dir, key):
    f = [p for p in glob.glob(os.path.join(case_dir, "*", "*.nii")) if f".{key}." in os.path.basename(p)]
    img = nib.load(f[0])
    return np.asanyarray(img.dataobj).astype(np.float64), img


def describe(case_dir):
    j = [p for p in glob.glob(os.path.join(case_dir, "*", "*.json")) if ".CT_CBF." in p][0]
    d = json.load(open(j))["description"]
    m = re.search(r"Train_(\d+)_([A-Z])", d)
    return int(m.group(1)), m.group(2)


def core_masks(maps):
    """Re-derive the binary masks exactly as features_from_maps defines them (same helper logic)."""
    f = features_from_maps(maps)
    cbf, cbv, mtt, tmax = maps["CBF"], maps["CBV"], maps["MTT"], maps["Tmax"]
    brain = (cbf > 0) | (cbv > 0) | (mtt > 0) | (tmax > 0)
    tissue = brain & (cbf > 0) & (cbv > 0) & (cbv < 8.0) & (cbf < 99.0)
    mid = f["qc_midline"]
    ii = np.arange(brain.shape[0])[:, None, None]
    A, B = tissue & (ii < mid - 1), tissue & (ii > mid + 1)
    ipsi, contra = (A, B) if f["qc_ipsi_side"] == "low" else (B, A)
    rcbf = cbf / max(np.median(cbf[contra]) if contra.any() else np.nan, EPS)
    hyp6 = ipsi & (tmax > 6)
    core = hyp6 & (rcbf < 0.30)
    # consistency with the feature value (frozen definition)
    assert abs(core.sum() / max(tissue.sum(), 1) - f["core_rcbf30_hypo_frac"]) < 1e-9
    return f, tissue, core, tissue & (tmax > 6)


def one_case(cd):
    pid, slab = describe(cd)
    raw = {nm: load(cd, f"CT_{nm}")[0] for nm in CHANNELS}
    ot, img = load(cd, "OT")
    ot = ot > 0.5
    zooms = img.header.get_zooms()[:3]
    vox_ml = float(np.prod(zooms)) / 1000
    brain = np.zeros(ot.shape, bool)
    for nm in CHANNELS:
        brain |= raw[nm] > 0
    row = {"case": os.path.basename(cd), "patient": pid, "slab": slab, "nx": ot.shape[0], "ny": ot.shape[1],
           "nz": ot.shape[2], "dx": round(float(zooms[0]), 3), "dz": round(float(zooms[2]), 2), "vox_ml": vox_ml,
           "ot_ml": ot.sum() * vox_ml, "brain_ml": brain.sum() * vox_ml}
    for nm in CHANNELS:
        v = raw[nm][brain & (raw[nm] > 0)]
        row[f"raw_{nm}_median"] = float(np.median(v)) if v.size else np.nan
        row[f"raw_{nm}_p99"] = float(np.percentile(v, 99)) if v.size else np.nan
        row[f"raw_{nm}_nonfinite"] = int((~np.isfinite(raw[nm])).sum())
        row[f"raw_{nm}_neg"] = int((raw[nm] < 0).sum())
        row[f"raw_{nm}_above_clip"] = float((raw[nm][brain] > CLIP[nm]).mean())
    for scaling in ("as_distributed", "s03_harmonised"):
        maps = {nm: np.nan_to_num(raw[nm].copy(), nan=0.0, posinf=0.0, neginf=0.0) for nm in CHANNELS}
        if scaling == "s03_harmonised":
            maps["CBF"] *= 14.3 / np.median(maps["CBF"][brain & (maps["CBF"] > 0)])
            maps["CBV"] *= 2.8 / np.median(maps["CBV"][brain & (maps["CBV"] > 0)])
        maps = {nm: np.clip(maps[nm], 0, CLIP[nm]) for nm in CHANNELS}
        p = f"{scaling}__"
        try:
            f, tissue, core, hyp = core_masks(maps)
        except Exception as e:   # technical failure is an outcome, not dropped
            row[p + "failure"] = repr(e)[:120]
            continue
        row[p + "failure"] = ""
        feats = [f.get(c, np.nan) for c in F.CTP_ALL]
        row[p + "n_features_nonfinite"] = int(np.sum(~np.isfinite(np.asarray(feats, float))))
        row[p + "mirror_dice"] = f["qc_mirror_dice"]
        row[p + "tissue_ml"] = tissue.sum() * vox_ml
        row[p + "tp"] = int((core & ot).sum()); row[p + "fp"] = int((core & ~ot).sum()); row[p + "fn"] = int((~core & ot).sum())
        row[p + "core_ml"] = core.sum() * vox_ml
        row[p + "tmax6_ml"] = hyp.sum() * vox_ml
        row[p + "ot_in_tmax6"] = int((hyp & ot).sum())
        row[p + "ot_in_tissue"] = int((tissue & ot).sum())
        ot_side = np.argwhere(ot)[:, 0].mean() < f["qc_midline"] if ot.any() else None
        row[p + "side_agrees_with_dwi"] = (None if ot_side is None else bool((f["qc_ipsi_side"] == "low") == ot_side))
        row[p + "vol_monotone_tmax"] = bool(f["tmax_gt10_frac"] <= f["tmax_gt8_frac"] <= f["tmax_gt6_frac"] <= f["tmax_gt4_frac"])
        row[p + "vol_monotone_core"] = bool(f["core_rcbf20_hypo_frac"] <= f["core_rcbf30_hypo_frac"] <= f["core_rcbf38_hypo_frac"])
        for c in F.CTP_ALL:
            row[p + "feat_" + c] = f.get(c, np.nan)
    return row


def patient_level(S, scaling):
    p = f"{scaling}__"
    g = S[S[p + "failure"] == ""].groupby("patient")
    P = pd.DataFrame({"n_slabs": g.size(), "tp": g[p + "tp"].sum(), "fp": g[p + "fp"].sum(), "fn": g[p + "fn"].sum(),
                      "core_ml": g[p + "core_ml"].sum(), "ot_ml": g.ot_ml.sum(), "tmax6_ml": g[p + "tmax6_ml"].sum(),
                      "ot_in_tmax6": g[p + "ot_in_tmax6"].sum(), "ot_vox": g[p + "ot_in_tissue"].sum(),
                      "protocol": g.protocol.first()})
    P["dice"] = 2 * P.tp / (2 * P.tp + P.fp + P.fn).replace(0, np.nan)
    P["sensitivity"] = P.tp / (P.tp + P.fn).replace(0, np.nan)
    P["precision"] = P.tp / (P.tp + P.fp).replace(0, np.nan)
    P["vol_diff_ml"] = P.core_ml - P.ot_ml
    P["dwi_core_covered_by_tmax6"] = P.ot_in_tmax6 / P.ot_vox.replace(0, np.nan)
    P["scaling"] = scaling
    return P


def ccc(x, y):
    mx, my = x.mean(), y.mean()
    return 2 * np.cov(x, y, ddof=0)[0, 1] / (x.var() + y.var() + (mx - my) ** 2)


def summarise(P, label, rng_seed=20261114, B=2000):
    rng = np.random.default_rng(rng_seed)
    n = len(P)
    stat = {"dice_mean": lambda d: d.dice.mean(), "dice_median": lambda d: d.dice.median(),
            "sensitivity_mean": lambda d: d.sensitivity.mean(), "precision_mean": lambda d: d.precision.mean(),
            "vol_bias_ml": lambda d: d.vol_diff_ml.mean(), "vol_abs_err_ml_median": lambda d: d.vol_diff_ml.abs().median(),
            "spearman_core_vs_dwi": lambda d: stats.spearmanr(d.core_ml, d.ot_ml).correlation,
            "ccc_core_vs_dwi_ml": lambda d: ccc(d.core_ml.values, d.ot_ml.values),
            "dwi_core_covered_by_tmax6_median": lambda d: d.dwi_core_covered_by_tmax6.median()}
    rows = []
    boots = [rng.integers(0, n, n) for _ in range(B)]
    for k, fn in stat.items():
        est = fn(P)
        bt = np.array([fn(P.iloc[b]) for b in boots])
        rows.append({"analysis": label, "metric": k, "n_patients": n, "n_slabs": int(P.n_slabs.sum()),
                     "estimate": est, "ci_lo": np.nanpercentile(bt, 2.5), "ci_hi": np.nanpercentile(bt, 97.5)})
    d = P.vol_diff_ml
    rows.append({"analysis": label, "metric": "bland_altman_loa_ml", "n_patients": n, "n_slabs": int(P.n_slabs.sum()),
                 "estimate": d.mean(), "ci_lo": d.mean() - 1.96 * d.std(ddof=1), "ci_hi": d.mean() + 1.96 * d.std(ddof=1)})
    return rows


def main():
    cases = sorted(glob.glob(str(ISLES18 / "ISLES2018_Training" / "TRAINING" / "case_*")), key=lambda p: int(p.split("_")[-1]))
    S = pd.DataFrame(Parallel(n_jobs=8)(delayed(one_case)(cd) for cd in cases))
    S["protocol"] = "matrix" + S.nx.astype(str) + "_dz" + S.dz.round(1).astype(str)
    S.to_csv(VDATA / "vX1_isles2018_per_slab.csv", index=False)
    print("slabs", len(S), "patients", S.patient.nunique(), "slab counts", S.groupby("patient").size().value_counts().to_dict())
    print(S.groupby("protocol").agg(slabs=("case", "size"), patients=("patient", "nunique")).to_string())
    tech = []
    rows, Ps = [], []
    for sc in ("as_distributed", "s03_harmonised"):
        p = f"{sc}__"
        ok = S[p + "failure"] == ""
        tech.append({"scaling": sc, "slabs": len(S), "patients": S.patient.nunique(),
                     "technical_failures_slabs": int((~ok).sum()),
                     "slabs_with_any_nonfinite_feature": int((S.loc[ok, p + "n_features_nonfinite"] > 0).sum()),
                     "feature_completeness_pct": 100 * (1 - S.loc[ok, p + "n_features_nonfinite"].sum() / (ok.sum() * len(F.CTP_ALL))),
                     "tmax_volume_monotonicity_pct": 100 * S.loc[ok, p + "vol_monotone_tmax"].mean(),
                     "core_threshold_monotonicity_pct": 100 * S.loc[ok, p + "vol_monotone_core"].mean(),
                     "ipsilateral_side_agrees_with_dwi_pct": 100 * S.loc[ok, p + "side_agrees_with_dwi"].dropna().astype(bool).mean(),
                     "mirror_dice_median": S.loc[ok, p + "mirror_dice"].median()})
        P = patient_level(S, sc)
        Ps.append(P.reset_index())
        rows += summarise(P, f"{sc}: all patients")
        for prot, g in P.groupby("protocol"):
            if len(g) >= 8:
                rows += summarise(g, f"{sc}: protocol {prot}")
    raw = S[[c for c in S.columns if c.startswith("raw_") and ("median" in c or "p99" in c or "above" in c)]].describe().T
    raw.to_csv(VTAB / "vX1_isles2018_raw_map_ranges.csv")
    pd.DataFrame(tech).to_csv(VTAB / "vX1_isles2018_technical.csv", index=False)
    pd.concat(Ps).to_csv(VDATA / "vX1_isles2018_per_patient.csv", index=False)
    R = pd.DataFrame(rows)
    R.to_csv(VTAB / "vX1_isles2018_core_vs_dwi.csv", index=False)
    print(pd.DataFrame(tech).round(3).to_string(index=False))
    print(raw.round(3).to_string())
    print(R.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
