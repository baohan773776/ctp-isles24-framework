"""Stage A/C (imaging): physical-unit recovery of the per-subject-normalised CTP maps, QC, and
extraction of prespecified, physiologically interpretable perfusion features.

Unit recovery. The public pre-processed release stores each map as z = (x - mu)/sigma (mu, sigma
unknown), after clipping x to [0, CLIP]. Background is x = 0, so x = b (z - z_min); when the clip
ceiling is present, b = CLIP / (z_max - z_min). Validated by the central volume theorem
(MTT = 60 * CBV / CBF) and, in ISLES 2018, by simulation (s03_isles2018_validation.py).

Geometry. Arrays are (64, 128, 128) = (left-right, anterior-posterior, superior-inferior);
axis 0 is the left-right axis (confirmed by mirror symmetry and LVO-mask laterality).
Voxel size is not recoverable, so all volumes are expressed as fractions of covered brain tissue.
"""
import sys
import numpy as np
import pandas as pd
from scipy import stats
from config import ISLES24, DATA, TAB, CLIP, CHANNELS

LR_AXIS = 0
EPS = 1e-6


def recover(perf):
    out, qc = {}, {}
    for c, nm in enumerate(CHANNELS):
        z = perf[c].astype(np.float64)
        lo, hi = z.min(), z.max()
        span = hi - lo
        tol = 1e-6 * max(1.0, span)
        qc[f"{nm}_n_at_ceiling"] = int((np.abs(z - hi) <= tol).sum())
        out[nm] = CLIP[nm] * (z - lo) / span
    return out, qc


def midline(brain):
    prof = brain.sum(axis=(1, 2))
    idx = np.nonzero(prof)[0]
    c0 = (idx.min() + idx.max()) / 2.0
    best, best_d = c0, -1
    for off in np.arange(-4, 4.5, 0.5):
        c = c0 + off
        shift = int(round(2 * c - (brain.shape[0] - 1)))
        fl = np.roll(np.flip(brain, 0), shift, axis=0)
        d = 2 * (brain & fl).sum() / (brain.sum() + fl.sum())
        if d > best_d:
            best, best_d = c, d
    return best, best_d


def dist_stats(v, prefix):
    if v.size < 50:
        return {f"{prefix}_{k}": np.nan for k in ("mean", "sd", "skew", "kurt", "p10", "p25", "p50", "p75", "p90")}
    p = np.percentile(v, [10, 25, 50, 75, 90])
    return {f"{prefix}_mean": v.mean(), f"{prefix}_sd": v.std(), f"{prefix}_skew": stats.skew(v),
            f"{prefix}_kurt": stats.kurtosis(v), f"{prefix}_p10": p[0], f"{prefix}_p25": p[1],
            f"{prefix}_p50": p[2], f"{prefix}_p75": p[3], f"{prefix}_p90": p[4]}


def extract(sid):
    perf = np.load(ISLES24 / "perfusion" / f"{sid}_perf.npy")
    m, qc = recover(perf)
    qc["degenerate_norm"] = bool(abs(perf[0].min()) < 1e-9)
    lvo = np.load(ISLES24 / "masks" / f"{sid}_lvo_mask.npy")
    f = features_from_maps(m, lvo, qc)
    f["subject_id"] = sid
    return f


def features_from_maps(m, lvo=None, qc=None):
    qc = {} if qc is None else qc
    cbf, cbv, mtt, tmax = m["CBF"], m["CBV"], m["MTT"], m["Tmax"]
    brain = (cbf > 0) | (cbv > 0) | (mtt > 0) | (tmax > 0)
    tissue = brain & (cbf > 0) & (cbv > 0) & (cbv < 8.0) & (cbf < 99.0)

    # central volume theorem check
    cv = tissue & (cbf > 5) & (cbv > 0.2) & (mtt > 0) & (mtt < 29.9)
    qc["cvt_ratio_median"] = float(np.median(mtt[cv] / (60 * cbv[cv] / cbf[cv]))) if cv.sum() > 500 else np.nan
    qc["cvt_corr"] = float(np.corrcoef(mtt[cv], 60 * cbv[cv] / cbf[cv])[0, 1]) if cv.sum() > 500 else np.nan

    mid, sym = midline(brain)
    ii = np.arange(brain.shape[0])[:, None, None]
    A = tissue & (ii < mid - 1)
    B = tissue & (ii > mid + 1)
    fa, fb = (tmax[A] > 6).mean() if A.any() else 0, (tmax[B] > 6).mean() if B.any() else 0
    ipsi, contra = (A, B) if fa >= fb else (B, A)
    side = "low" if fa >= fb else "high"   # hemisphere along axis 0 (low/high index)
    lvo_side = None
    if lvo is not None and lvo.sum() > 0:
        lvo_side = "low" if np.argwhere(lvo > 0)[:, 0].mean() < mid else "high"
    qc.update({"midline": mid, "mirror_dice": sym, "ipsi_side": side, "lvo_side": lvo_side,
               "tissue_vox": int(tissue.sum()), "ipsi_vox": int(ipsi.sum()), "contra_vox": int(contra.sum())})

    n_t = tissue.sum()
    ref = {nm: np.median(m[nm][contra]) for nm in ("CBF", "CBV", "MTT")}
    r = {nm: m[nm] / max(ref[nm], EPS) for nm in ("CBF", "CBV", "MTT")}
    qc.update({f"contra_median_{k}": v for k, v in ref.items()})
    qc["contra_median_Tmax"] = float(np.median(tmax[contra]))

    f = {}
    # ---- Tmax (absolute seconds) ----
    for t in (4, 6, 8, 10):
        f[f"tmax_gt{t}_frac"] = (tissue & (tmax > t)).sum() / n_t
    hyp6 = ipsi & (tmax > 6)
    f["hir"] = (tissue & (tmax > 10)).sum() / max((tissue & (tmax > 6)).sum(), 1)
    f["tmax_ipsi_minus_contra"] = np.median(tmax[ipsi]) - np.median(tmax[contra])
    f.update(dist_stats(tmax[ipsi], "tmax_ipsi"))
    # ---- CBF (relative to contralateral median) ----
    for t in (20, 30, 38):
        f[f"core_rcbf{t}_frac"] = (ipsi & (r["CBF"] < t / 100)).sum() / n_t
        # primary core definition: rCBF below threshold inside ipsilateral Tmax>6 s tissue
        f[f"core_rcbf{t}_hypo_frac"] = (hyp6 & (r["CBF"] < t / 100)).sum() / n_t
    f["rcbf_ipsi_ratio"] = np.median(cbf[ipsi]) / max(ref["CBF"], EPS)
    f["rcbf_in_hypo"] = r["CBF"][hyp6].mean() if hyp6.sum() > 20 else 1.0
    f.update(dist_stats(r["CBF"][ipsi], "rcbf_ipsi"))
    # ---- CBV ----
    f["rcbv_ipsi_ratio"] = np.median(cbv[ipsi]) / max(ref["CBV"], EPS)
    f["lowcbv_rcbv60_frac"] = (ipsi & (r["CBV"] < 0.6)).sum() / n_t
    f["cbv_index_hypo"] = r["CBV"][hyp6].mean() if hyp6.sum() > 20 else 1.0
    f.update(dist_stats(r["CBV"][ipsi], "rcbv_ipsi"))
    # ---- MTT ----
    f["rmtt_ipsi_ratio"] = np.median(mtt[ipsi]) / max(ref["MTT"], EPS)
    f["mtt145_frac"] = (ipsi & (r["MTT"] > 1.45)).sum() / n_t
    f["rmtt_in_hypo"] = r["MTT"][hyp6].mean() if hyp6.sum() > 20 else 1.0
    f.update(dist_stats(r["MTT"][ipsi], "rmtt_ipsi"))
    # ---- mismatch ----
    core_v = (hyp6 & (r["CBF"] < 0.30)).sum()
    hyp_v = (tissue & (tmax > 6)).sum()
    f["mismatch_ratio_log"] = np.log((hyp_v + 1) / (core_v + 1))
    f["mismatch_frac"] = max(hyp_v - core_v, 0) / n_t
    for k, v in qc.items():
        f[f"qc_{k}"] = v
    return f


def main():
    cohort = pd.read_csv(DATA / "cohort_flow_149.csv")
    rows = []
    for i, sid in enumerate(cohort.subject_id):
        rows.append(extract(sid))
        if i % 25 == 0:
            print(i, sid, flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "ctp_features_v3_149.csv", index=False)
    inc = df[df.subject_id.isin(cohort.subject_id[cohort.included])]
    q = {
        "n": len(inc),
        "cvt_ratio_median_of_medians": inc.qc_cvt_ratio_median.median(),
        "cvt_ratio_IQR": [inc.qc_cvt_ratio_median.quantile(.25), inc.qc_cvt_ratio_median.quantile(.75)],
        "cvt_ratio_within_5pct": float((inc.qc_cvt_ratio_median.sub(1).abs() <= 0.05).mean()),
        "cvt_corr_median": inc.qc_cvt_corr.median(),
        "degenerate_norm_n": int(inc.qc_degenerate_norm.sum()),
        "tmax_ceiling_ge2_n": int((inc.qc_Tmax_n_at_ceiling >= 2).sum()),
        "lvo_mask_available": int(inc.qc_lvo_side.notna().sum()),
        "ipsi_agrees_with_lvo": float((inc.qc_lvo_side == inc.qc_ipsi_side)[inc.qc_lvo_side.notna()].mean()),
        "contra_tmax_median": inc.qc_contra_median_Tmax.median(),
        "contra_cbf_median": inc.qc_contra_median_CBF.median(),
        "contra_cbv_median": inc.qc_contra_median_CBV.median(),
        "contra_mtt_median": inc.qc_contra_median_MTT.median(),
        "mirror_dice_median": inc.qc_mirror_dice.median(),
    }
    pd.Series(q).to_json(TAB / "ctp_qc_summary.json", indent=2)
    print(pd.Series(q).to_string())
    feat = [c for c in df.columns if not c.startswith("qc_") and c != "subject_id"]
    print(inc[feat].describe().T[["mean", "50%", "min", "max"]].round(3).to_string())


if __name__ == "__main__":
    main()
