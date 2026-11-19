"""Native-unit analyses (original ISLES'24 release, fetched by s13):
1. recompute the 53 prespecified features on native-unit maps (clipped to the same [0, CLIP] range
   that the public pre-processing applied) -> direct test of the unit-recovery method;
2. absolute volumes in mL (core rCBF<30% within Tmax>6 s, Tmax>6 s, mismatch) from voxel size;
3. construct validity against the follow-up DWI final infarct volume;
4. acquisition-protocol fingerprints (voxel size, matrix, CTP slab coverage) for site clustering;
5. sex-coding check against the text labels of the original release.
"""
import json
import sys
import numpy as np
import pandas as pd
from scipy import stats
from config import ROOT, DATA, TAB, CLIP
from s02_ctp_features import features_from_maps
import features as F

sys.stdout.reconfigure(encoding="utf-8")
NATIVE_DIR = ROOT.parent / "native_isles24"


def icc31(a, b):
    x = np.c_[a, b]
    x = x[np.isfinite(x).all(1)]
    n, k = x.shape
    gm = x.mean()
    ssr = k * ((x.mean(1) - gm) ** 2).sum()
    ssc = n * ((x.mean(0) - gm) ** 2).sum()
    sse = ((x - gm) ** 2).sum() - ssr - ssc
    msr, mse = ssr / (n - 1), sse / ((n - 1) * (k - 1))
    return (msr - mse) / (msr + (k - 1) * mse)


def main():
    meta = [json.loads(l) for l in (DATA / "native_meta.jsonl").read_text(encoding="utf-8").splitlines()]
    meta = pd.DataFrame(meta).drop_duplicates("subject_id").set_index("subject_id").sort_index()
    print("subjects fetched:", len(meta))
    rows = []
    for sid, m in meta.iterrows():
        z = np.load(NATIVE_DIR / f"{sid}.npz")
        maps = {nm: np.clip(z[nm], 0, CLIP[nm]) for nm in ("CBF", "CBV", "MTT", "Tmax")}
        lvo = z["lvo"] if "lvo" in z.files else None
        f = features_from_maps(maps, lvo)
        vox_ml = float(np.prod(m["grid_zooms"])) / 1000.0
        n_t = f["qc_tissue_vox"]
        core = f["core_rcbf30_hypo_frac"] * n_t * vox_ml
        t6 = f["tmax_gt6_frac"] * n_t * vox_ml
        mis = f["mismatch_frac"] * n_t * vox_ml
        out = {"subject_id": sid, "core_ml": core, "tmax6_ml": t6, "mismatch_ml": mis,
               "tissue_ml": n_t * vox_ml, "log_core_ml": np.log1p(core), "log_tmax6_ml": np.log1p(t6),
               "log_mismatch_ml": np.log1p(mis), "dwi_final_ml": m.get("lesion_ml_native", np.nan)}
        out.update({f"nat_{k}": v for k, v in f.items()})
        rows.append(out)
    nat = pd.DataFrame(rows)
    nat.to_csv(DATA / "ctp_features_native_149.csv", index=False)

    coh = pd.read_csv(DATA / "cohort_129.csv")
    inc = nat[nat.subject_id.isin(coh.subject_id)].merge(coh[["subject_id", "poor", "mrs90", "Sex", "Age"]], on="subject_id")
    rec = pd.read_csv(DATA / "ctp_features_v3_149.csv").set_index("subject_id")

    # 1. agreement native vs recovered
    ag = []
    for c in F.CTP_ALL:
        a = inc.set_index("subject_id")[f"nat_{c}"]
        b = rec.loc[a.index, c]
        ok = np.isfinite(a.values) & np.isfinite(b.values)
        ag.append({"feature": c, "channel": F.CHANNEL_OF.get(c, "Mismatch"), "n": int(ok.sum()),
                   "icc31": icc31(a.values[ok], b.values[ok]), "spearman": stats.spearmanr(a[ok], b[ok])[0],
                   "median_native": np.median(a[ok]), "median_recovered": np.median(b[ok])})
    ag = pd.DataFrame(ag)
    ag.to_csv(TAB / "native_vs_recovered_agreement.csv", index=False)
    print(ag.round(3).to_string(index=False))
    print("ICC median", ag.icc31.median().round(3), "IQR", ag.icc31.quantile([.25, .75]).round(3).tolist(),
          "min", ag.icc31.min().round(3), "n>=0.9", int((ag.icc31 >= 0.9).sum()), "/", len(ag))

    # 2/3. volumes and construct validity
    q = inc[["core_ml", "tmax6_ml", "mismatch_ml", "tissue_ml", "dwi_final_ml"]].describe(percentiles=[.25, .5, .75]).T
    q.to_csv(TAB / "native_volumes_summary.csv")
    print(q.round(1).to_string())
    val = {}
    for c in ("core_ml", "tmax6_ml", "mismatch_ml"):
        r, p = stats.spearmanr(inc[c], inc.dwi_final_ml, nan_policy="omit")
        val[f"rho_{c}_vs_dwi"] = r; val[f"p_{c}_vs_dwi"] = p
        r2, p2 = stats.spearmanr(inc[c], inc.mrs90)
        val[f"rho_{c}_vs_mrs90"] = r2; val[f"p_{c}_vs_mrs90"] = p2
    val["rho_dwi_vs_mrs90"], val["p_dwi_vs_mrs90"] = stats.spearmanr(inc.dwi_final_ml, inc.mrs90, nan_policy="omit")
    val["median_core_ml_poor"] = inc.loc[inc.poor == 1, "core_ml"].median()
    val["median_core_ml_good"] = inc.loc[inc.poor == 0, "core_ml"].median()
    val["mw_p_core"] = stats.mannwhitneyu(inc.loc[inc.poor == 1, "core_ml"], inc.loc[inc.poor == 0, "core_ml"]).pvalue
    val["median_tmax6_ml_poor"] = inc.loc[inc.poor == 1, "tmax6_ml"].median()
    val["median_tmax6_ml_good"] = inc.loc[inc.poor == 0, "tmax6_ml"].median()
    val["mw_p_tmax6"] = stats.mannwhitneyu(inc.loc[inc.poor == 1, "tmax6_ml"], inc.loc[inc.poor == 0, "tmax6_ml"]).pvalue
    val["target_mismatch_n"] = int(((inc.core_ml < 70) & (inc.tmax6_ml / inc.core_ml.clip(lower=0.1) >= 1.8)
                                    & (inc.mismatch_ml >= 15)).sum())
    val["ipsi_agrees_lvo"] = float((inc.nat_qc_ipsi_side == inc.nat_qc_lvo_side)[inc.nat_qc_lvo_side.notna()].mean())
    val["lvo_n"] = int(inc.nat_qc_lvo_side.notna().sum())
    val["cvt_ratio_median"] = inc.nat_qc_cvt_ratio_median.median()
    pd.Series(val).to_json(TAB / "native_validity.json", indent=2)
    print(pd.Series(val).round(4).to_string())

    # 4. acquisition fingerprints
    fp = meta.copy()
    fp["inplane_mm"] = fp.zooms.apply(lambda z: round(z[0], 3))
    fp["slice_mm"] = fp.zooms.apply(lambda z: round(z[2], 2))
    fp["nx"] = fp["shape"].apply(lambda s: s[0]); fp["ny"] = fp["shape"].apply(lambda s: s[1])
    fp["nz"] = fp["shape"].apply(lambda s: s[2])
    keep = ["inplane_mm", "slice_mm", "nx", "ny", "nz", "ctp_slab_mm", "ctp_slices", "Tmax_min", "Tmax_max",
            "CBF_max", "CBV_max", "MTT_max", "Tmax_neg_frac", "descrip", "axcodes", "sex", "mrs_3month", "shard"]
    fp[keep].to_csv(DATA / "native_acquisition_fingerprints.csv")
    for c in ["slice_mm", "nz", "ctp_slices", "Tmax_min", "descrip", "axcodes"]:
        print(c, fp[c].value_counts().head(8).to_dict())
    print("slab mm", fp.ctp_slab_mm.describe().round(1).to_dict())

    # 5. sex coding
    s = coh.set_index("subject_id")["Sex"]
    s = s[s.index.isin(meta.index)]
    x = pd.crosstab(meta.loc[s.index, "sex"], s.round(3))
    print("sex crosstab (release label x pre-processed code):\n", x)
    x.to_csv(TAB / "sex_coding_check.csv")


if __name__ == "__main__":
    main()
