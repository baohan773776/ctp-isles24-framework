"""Experiment B (post hoc): native-unit verification of the Tmax recovery, per subject, stratified by recovery QC.

The canonical s15 analysis compared FEATURES (ICC) between native-unit and recovered maps. This script adds a
per-subject, voxel-level comparison on a common grid and a per-subject feature/volume comparison, stratified by the
canonical Tmax-recovery QC status (certain: Tmax ceiling present in >= 2 voxels and non-degenerate normalisation;
uncertain: the remaining 41 of the 129 analysed patients).
Grid: the native maps (s13: NCCT space, 4x4 in-plane block average, RAS) are clipped to [0, CLIP] (as the public
pre-processing did), resampled to the 64x128x128 release grid (linear), and aligned to the recovered map over the
8 axis-flip combinations (best Tmax correlation; the chosen flip and correlation are reported as alignment QC).
Thresholds: Tmax > 4/6/8/10 s -> Dice and fraction of brain voxels classified differently.
Feature level (no regridding): recovered vs native core (rCBF<30% in ipsilateral Tmax>6 s), Tmax>6 s and mismatch
fractions of covered tissue, converted to mL with the native voxel size (fraction x native tissue volume).
Model level: paired dAUC native vs recovered CTP on identical folds (canonical oof_long_all; no refitting), overall
and within QC strata.
Outputs: outputs_validity/data/vB_native_per_subject.csv, tables/vB_*.csv
"""
import itertools
import json
import numpy as np
import pandas as pd
from scipy import ndimage
from joblib import Parallel, delayed
from v_common import VDATA, VTAB, DATA, OOF, NATIVE_DIR, boot_indices, perf_and_pairs, load_oof, seed_auc
from config import ISLES24, CLIP, CHANNELS
from s02_ctp_features import recover

GRID = (64, 128, 128)


def per_subject(sid, vox_ml):
    perf = np.load(ISLES24 / "perfusion" / f"{sid}_perf.npy")
    rec, _ = recover(perf)
    z = np.load(NATIVE_DIR / f"{sid}.npz")
    nat = {k: np.clip(z[k], 0, CLIP[k]) for k in CHANNELS}
    natr = {k: np.clip(ndimage.zoom(v, [g / s for g, s in zip(GRID, v.shape)], order=1), 0, CLIP[k]) for k, v in nat.items()}
    best = None
    for fl in itertools.product((False, True), repeat=3):
        t = natr["Tmax"]
        for ax, f in enumerate(fl):
            if f:
                t = np.flip(t, ax)
        m = (t > 0) & (rec["Tmax"] > 0)
        if m.sum() < 1000:
            continue
        c = np.corrcoef(t[m], rec["Tmax"][m])[0, 1]
        if best is None or c > best[1]:
            best = (fl, c)
    fl, corr = best
    for k in CHANNELS:
        for ax, f in enumerate(fl):
            if f:
                natr[k] = np.flip(natr[k], ax)
    brain = (natr["Tmax"] > 0) & (rec["Tmax"] > 0) & (natr["CBF"] > 0) & (rec["CBF"] > 0)
    tn, tr = natr["Tmax"][brain], rec["Tmax"][brain]
    out = {"subject_id": sid, "align_flip": "".join("F" if f else "-" for f in fl), "align_corr_tmax": corr,
           "n_brain_vox": int(brain.sum()),
           "tmax_mae_s": float(np.mean(np.abs(tr - tn))), "tmax_median_abs_err_s": float(np.median(np.abs(tr - tn))),
           "tmax_bias_s": float(np.mean(tr - tn)),
           "tmax_scale_ratio_median": float(np.median(tr[tn > 1] / tn[tn > 1])) if (tn > 1).sum() > 100 else np.nan,
           "tmax_native_contra_like_median": float(np.median(tn))}
    for t in (4, 6, 8, 10):
        a, b = tr > t, tn > t
        out[f"dice_tmax{t}"] = 2 * (a & b).sum() / max(a.sum() + b.sum(), 1) if (a.sum() + b.sum()) > 0 else np.nan
        out[f"disagree_frac_tmax{t}"] = float((a != b).mean())
        out[f"frac_rec_tmax{t}"], out[f"frac_nat_tmax{t}"] = float(a.mean()), float(b.mean())
    return out


def main():
    meta = pd.DataFrame([json.loads(l) for l in (DATA / "native_meta.jsonl").read_text(encoding="utf-8").splitlines()])
    meta = meta.drop_duplicates("subject_id").set_index("subject_id")
    coh = pd.read_csv(DATA / "cohort_129.csv")
    rec = pd.read_csv(DATA / "ctp_features_v3_149.csv").set_index("subject_id")
    nat = pd.read_csv(DATA / "ctp_features_native_149.csv").set_index("subject_id")
    ids = sorted(coh.subject_id)
    vox = {s: float(np.prod(meta.loc[s, "grid_zooms"])) / 1000 for s in ids}
    rows = Parallel(n_jobs=12)(delayed(per_subject)(s, vox[s]) for s in ids)
    D = pd.DataFrame(rows).set_index("subject_id")
    certain = (rec.qc_Tmax_n_at_ceiling >= 2) & (~rec.qc_degenerate_norm.astype(bool))
    D["qc_stratum"] = np.where(certain.loc[D.index], "Tmax recovery certain", "Tmax recovery uncertain")
    D["qc_Tmax_n_at_ceiling"] = rec.loc[D.index, "qc_Tmax_n_at_ceiling"]
    D["qc_degenerate_norm"] = rec.loc[D.index, "qc_degenerate_norm"]
    tissue_ml = nat.loc[D.index, "tissue_ml"]
    for f, lab in (("core_rcbf30_hypo_frac", "core"), ("tmax_gt6_frac", "hypoperf_tmax6"), ("mismatch_frac", "mismatch"),
                   ("tmax_gt4_frac", "tmax4"), ("tmax_gt8_frac", "tmax8"), ("tmax_gt10_frac", "tmax10")):
        D[f"{lab}_frac_rec"] = rec.loc[D.index, f]
        D[f"{lab}_frac_nat"] = nat.loc[D.index, f"nat_{f}"]
        D[f"{lab}_ml_rec"] = D[f"{lab}_frac_rec"] * tissue_ml
        D[f"{lab}_ml_nat"] = D[f"{lab}_frac_nat"] * tissue_ml
        D[f"{lab}_ml_diff"] = D[f"{lab}_ml_rec"] - D[f"{lab}_ml_nat"]
    D["poor"] = coh.set_index("subject_id").loc[D.index, "poor"]
    D.reset_index().to_csv(VDATA / "vB_native_per_subject.csv", index=False)

    # stratified summaries (median [IQR]) and Mann-Whitney tests certain vs uncertain
    from scipy import stats
    cols = ["align_corr_tmax", "tmax_mae_s", "tmax_median_abs_err_s", "tmax_bias_s", "tmax_scale_ratio_median",
            "dice_tmax4", "dice_tmax6", "dice_tmax8", "dice_tmax10", "disagree_frac_tmax4", "disagree_frac_tmax6",
            "disagree_frac_tmax8", "disagree_frac_tmax10", "core_ml_diff", "hypoperf_tmax6_ml_diff", "mismatch_ml_diff"]
    S = []
    for c in cols:
        r = {"metric": c}
        for st, g in [("all", D)] + list(D.groupby("qc_stratum")):
            v = g[c].dropna()
            r[f"{st}__n"] = len(v)
            r[f"{st}__median"] = v.median(); r[f"{st}__q1"] = v.quantile(.25); r[f"{st}__q3"] = v.quantile(.75)
            if c.endswith("_diff"):
                r[f"{st}__mean"] = v.mean(); r[f"{st}__loa_lo"] = v.mean() - 1.96 * v.std(); r[f"{st}__loa_hi"] = v.mean() + 1.96 * v.std()
        a = D.loc[D.qc_stratum == "Tmax recovery certain", c].dropna()
        b = D.loc[D.qc_stratum == "Tmax recovery uncertain", c].dropna()
        r["mw_p_certain_vs_uncertain"] = stats.mannwhitneyu(a, b).pvalue if len(a) and len(b) else np.nan
        S.append(r)
    pd.DataFrame(S).to_csv(VTAB / "vB_native_voxel_feature_agreement_by_qc.csv", index=False)
    print(pd.DataFrame(S).round(3).to_string(index=False))

    # model level on identical folds (canonical OOF, no refitting)
    ids_o, y, P = load_oof(OOF / "oof_long_all.csv")
    keep = {k: P[k] for k in ("P1_clin_GBM", "E_CTP_all", "E_native", "F_late_P1_E", "F_late_P1_Enat", "R1_clin_LR4",
                              "F_late_R1_E", "V_volumes", "F_late_P1_V") if k in P}
    pairs = [("F_late_P1_Enat", "F_late_P1_E", "clinical + native CTP vs clinical + recovered CTP (primary)"),
             ("E_native", "E_CTP_all", "native vs recovered CTP alone"),
             ("F_late_P1_Enat", "P1_clin_GBM", "native CTP added to clinical"),
             ("F_late_P1_E", "P1_clin_GBM", "recovered CTP added to clinical (primary H0)")]
    strata = pd.Series(D.loc[ids_o, "qc_stratum"].values)
    perf_all, comp_all = [], []
    p, c = perf_and_pairs(y, keep, pairs, boot_indices(y), label="all analysed (n=129)")
    perf_all.append(p); comp_all.append(c)
    for st in ("Tmax recovery certain", "Tmax recovery uncertain"):
        sub = np.nonzero((strata == st).values)[0]
        p, c = perf_and_pairs(y, keep, pairs, None, label=st, subset=sub)
        perf_all.append(p); comp_all.append(c)
    pd.concat(perf_all).to_csv(VTAB / "vB_model_native_vs_recovered_perf.csv", index=False)
    pd.concat(comp_all).to_csv(VTAB / "vB_model_native_vs_recovered_paired.csv", index=False)
    print(pd.concat(comp_all)[["analysis", "new", "reference", "n", "events", "delta_auc", "ci_lo", "ci_hi"]].round(3).to_string(index=False))


def by_ceiling():
    """Re-summarise with the 41-patient definition (no Tmax ceiling in >= 2 voxels), separating the 3 patients whose
    only QC flag is a degenerate normalisation."""
    D = pd.read_csv(VDATA / "vB_native_per_subject.csv")
    D["qc3"] = np.select([D.qc_Tmax_n_at_ceiling < 2, D.qc_degenerate_norm.astype(bool)],
                         ["no Tmax ceiling (n=41 definition)", "ceiling present, degenerate normalisation"],
                         "Tmax recovery certain")
    cols = ["tmax_median_abs_err_s", "tmax_bias_s", "tmax_scale_ratio_median", "dice_tmax4", "dice_tmax6", "dice_tmax8",
            "dice_tmax10", "disagree_frac_tmax6", "core_ml_diff", "hypoperf_tmax6_ml_diff", "mismatch_ml_diff"]
    g = D.groupby("qc3")
    out = pd.concat({"n": g.size(), **{f"{c}__median": g[c].median() for c in cols},
                     **{f"{c}__q1": g[c].quantile(.25) for c in cols}, **{f"{c}__q3": g[c].quantile(.75) for c in cols}}, axis=1)
    out.to_csv(VTAB / "vB_native_by_ceiling_definition.csv")
    print(out.T.round(3).to_string())


if __name__ == "__main__":
    import sys
    by_ceiling() if len(sys.argv) > 1 and sys.argv[1] == "ceiling" else (main(), by_ceiling())
