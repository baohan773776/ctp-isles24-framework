"""Targeted repair 3 (post hoc): overlap of the two CTP slabs in ISLES 2018 patients and patient-level metrics after
spatial de-duplication.

Problem: vX1_isles2018_benchmark.py sums TP, FP, FN and volumes over a patient's slabs. The challenge documentation
states that the two slabs of a patient may partially overlap, so summing can count the same tissue twice.
Header geometry is insufficient: every ISLES 2018 NIfTI file has an identity affine (sform_code 2, no origin or slice
position) and the SMIR JSON sidecars carry no slice position, so slab positions cannot be read from metadata.
Image-based estimate used instead: for every pair of slices (slab A slice i, slab B slice j) the normalised
cross-correlation (NCC) of the CTP reference image ('CT', clipped to [-50, 1000] HU) is computed after the best integer
in-plane shift (phase correlation, |shift| <= 12 voxels). Overlap is modelled as a contiguous block of k slices at the
end of one slab matching the start of the other (both orders, k = 1 .. min(nA, nB) - 1); the block with the highest
mean NCC is retained. A matched slice pair is called a DUPLICATED LOCATION when
  * 'adjacency' criterion (primary): its NCC exceeds the NCC of each of the two slices with its own neighbour(s) in the
    same slab, i.e. the two slices are more alike than physically distinct, 1-slice-apart slices of one acquisition;
  * 'strict' criterion (sensitivity): NCC >= 0.95.
De-duplication removes the duplicated slices of slab B (primary; 'keep A') or of slab A ('keep B') from the patient
sums. Partial (sub-slice) overlap cannot be resolved by this method, so the de-duplicated metrics remain estimates.
The OT (reference) masks are NOT used to detect overlap; their slice Dice at the matched pairs is reported as an
independent plausibility check only. The canonical vX1 outputs are not modified.
Outputs: outputs_validity/data/vX1b_slab_overlap_per_patient.csv, vX1b_isles2018_per_patient_ledger.csv;
         outputs_validity/tables/vX1b_slab_overlap_summary.csv, vX1b_isles2018_core_vs_dwi_dedup.csv
"""
import sys
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from v_common import VDATA, VTAB
from config import ISLES18, CLIP, CHANNELS
import vX1_isles2018_benchmark as X

sys.stdout.reconfigure(encoding="utf-8")
BASE = ISLES18 / "ISLES2018_Training" / "TRAINING"
STRICT = 0.95


def ncc_shift(a, b, max_shift=12):
    a = np.clip(a, -50, 1000); b = np.clip(b, -50, 1000)
    fa, fb = np.fft.fft2(a - a.mean()), np.fft.fft2(b - b.mean())
    cps = fa * np.conj(fb)
    r = np.fft.ifft2(cps / (np.abs(cps) + 1e-9)).real
    dy, dx = np.unravel_index(np.argmax(r), r.shape)
    dy = dy - a.shape[0] if dy > a.shape[0] // 2 else dy
    dx = dx - a.shape[1] if dx > a.shape[1] // 2 else dx
    if abs(dy) > max_shift or abs(dx) > max_shift:
        dy = dx = 0
    bs = np.roll(np.roll(b, dy, 0), dx, 1)
    m = (a > -40) | (bs > -40)
    x, y = a[m] - a[m].mean(), bs[m] - bs[m].mean()
    return float((x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum() + 1e-12))


def per_slice(case):
    """Per-slice TP/FP/FN/core/OT voxel counts of the unchanged vX1 pipeline, both scalings."""
    cd = str(BASE / case)
    raw = {nm: X.load(cd, f"CT_{nm}")[0] for nm in CHANNELS}
    ot, img = X.load(cd, "OT")
    ot = ot > 0.5
    ct = X.load(cd, "CT")[0]
    brain = np.zeros(ot.shape, bool)
    for nm in CHANNELS:
        brain |= raw[nm] > 0
    out = {"ct": ct, "ot": ot, "vox_ml": float(np.prod(img.header.get_zooms()[:3])) / 1000}
    for scaling in ("as_distributed", "s03_harmonised"):
        maps = {nm: np.nan_to_num(raw[nm].copy(), nan=0.0, posinf=0.0, neginf=0.0) for nm in CHANNELS}
        if scaling == "s03_harmonised":
            maps["CBF"] *= 14.3 / np.median(maps["CBF"][brain & (maps["CBF"] > 0)])
            maps["CBV"] *= 2.8 / np.median(maps["CBV"][brain & (maps["CBV"] > 0)])
        maps = {nm: np.clip(maps[nm], 0, CLIP[nm]) for nm in CHANNELS}
        f, tissue, core, hyp = X.core_masks(maps)
        out[scaling] = {"tp": (core & ot).sum((0, 1)), "fp": (core & ~ot).sum((0, 1)), "fn": (~core & ot).sum((0, 1)),
                        "core": core.sum((0, 1)), "otv": ot.sum((0, 1)), "hyp": hyp.sum((0, 1)),
                        "ot_in_hyp": (hyp & ot).sum((0, 1)), "ot_in_tissue": (tissue & ot).sum((0, 1))}
    return out


def match(A, B):
    """Best edge-anchored overlap block between slabs A and B (CT reference images)."""
    na, nb = A["ct"].shape[2], B["ct"].shape[2]
    M = np.array([[ncc_shift(A["ct"][..., i], B["ct"][..., j]) for j in range(nb)] for i in range(na)])
    adjA = [ncc_shift(A["ct"][..., i], A["ct"][..., i + 1]) for i in range(na - 1)]
    adjB = [ncc_shift(B["ct"][..., j], B["ct"][..., j + 1]) for j in range(nb - 1)]

    def nb_max(adj, k, n):
        v = ([adj[k - 1]] if k > 0 else []) + ([adj[k]] if k < n - 1 else [])
        return max(v) if v else np.nan

    best = None
    for order in ("A_end_B_start", "B_end_A_start"):
        for k in range(1, min(na, nb)):
            pairs = ([(na - k + t, t) for t in range(k)] if order == "A_end_B_start" else [(t, nb - k + t) for t in range(k)])
            mean = np.mean([M[i, j] for i, j in pairs])
            if best is None or mean > best[0]:
                best = (mean, order, pairs)
    _, order, pairs = best
    rows = []
    for i, j in pairs:
        thr = max(nb_max(adjA, i, na), nb_max(adjB, j, nb))
        oa, ob = A["ot"][..., i], B["ot"][..., j]
        s = oa.sum() + ob.sum()
        rows.append({"i": i, "j": j, "ncc": M[i, j], "adj_threshold": thr,
                     "dup_adjacency": bool(M[i, j] > thr), "dup_strict": bool(M[i, j] >= STRICT),
                     "ot_slice_dice": (2 * (oa & ob).sum() / s) if s else np.nan})
    return order, rows, float(M.max())


def one_patient(pid, cases):
    ca, cb = cases
    A, B = per_slice(ca), per_slice(cb)
    if A["ct"].shape[:2] != B["ct"].shape[:2]:
        return {"patient": pid, "note": "in-plane grids differ"}, A, B, []
    order, rows, mx = match(A, B)
    return {"patient": pid, "case_A": ca, "case_B": cb, "n_slices_A": A["ct"].shape[2], "n_slices_B": B["ct"].shape[2],
            "best_block_order": order, "block_k": len(rows), "max_ncc_any_pair": mx,
            "n_dup_adjacency": sum(r["dup_adjacency"] for r in rows), "n_dup_strict": sum(r["dup_strict"] for r in rows),
            "ncc_matched": ";".join(f"{r['ncc']:.3f}" for r in rows),
            "adj_threshold": ";".join(f"{r['adj_threshold']:.3f}" for r in rows),
            "ot_slice_dice_matched": ";".join("nan" if np.isnan(r["ot_slice_dice"]) else f"{r['ot_slice_dice']:.3f}" for r in rows),
            "note": ""}, A, B, rows


def patient_sums(slabs, drop):
    """slabs: list of per_slice dicts; drop: list of sets of slice indices to drop per slab."""
    out = {}
    for sc in ("as_distributed", "s03_harmonised"):
        acc = {k: 0.0 for k in ("tp", "fp", "fn", "core_ml", "ot_ml", "tmax6_ml", "ot_in_tmax6", "ot_vox")}
        for s, d in zip(slabs, drop):
            keep = np.array([z not in d for z in range(s["ct"].shape[2])])
            q = s[sc]
            acc["tp"] += q["tp"][keep].sum(); acc["fp"] += q["fp"][keep].sum(); acc["fn"] += q["fn"][keep].sum()
            acc["core_ml"] += q["core"][keep].sum() * s["vox_ml"]; acc["ot_ml"] += q["otv"][keep].sum() * s["vox_ml"]
            acc["tmax6_ml"] += q["hyp"][keep].sum() * s["vox_ml"]
            acc["ot_in_tmax6"] += q["ot_in_hyp"][keep].sum(); acc["ot_vox"] += q["ot_in_tissue"][keep].sum()
        out[sc] = acc
    return out


def to_frame(rows, protocol):
    P = pd.DataFrame(rows).set_index("patient")
    P["protocol"] = protocol.reindex(P.index)
    P["dice"] = 2 * P.tp / (2 * P.tp + P.fp + P.fn).replace(0, np.nan)
    P["sensitivity"] = P.tp / (P.tp + P.fn).replace(0, np.nan)
    P["precision"] = P.tp / (P.tp + P.fp).replace(0, np.nan)
    P["vol_diff_ml"] = P.core_ml - P.ot_ml
    P["dwi_core_covered_by_tmax6"] = P.ot_in_tmax6 / P.ot_vox.replace(0, np.nan)
    return P


def main():
    S = pd.read_csv(VDATA / "vX1_isles2018_per_slab.csv")
    protocol = S.groupby("patient").protocol.first()
    groups = {pid: g.sort_values("slab").case.tolist() for pid, g in S.groupby("patient")}
    res = Parallel(n_jobs=8)(delayed(lambda p, c: (p, c, *((one_patient(p, c)) if len(c) == 2 else
                                                          (None, per_slice(c[0]), None, []))))(p, c) for p, c in groups.items())
    meta, variants = [], {"slab_summed (original)": [], "dedup_adjacency_keepA (primary)": [],
                          "dedup_adjacency_keepB": [], "dedup_strict_keepA": []}
    check = []
    for pid, cases, info, A, B, rows in res:
        slabs = [A] if B is None else [A, B]
        # consistency with the canonical per-slab totals
        for case, s in zip(cases, slabs):
            r = S.set_index("case").loc[case]
            check.append(int(s["s03_harmonised"]["tp"].sum()) == int(r["s03_harmonised__tp"]) and
                         int(s["s03_harmonised"]["fn"].sum()) == int(r["s03_harmonised__fn"]))
        if info is not None:
            meta.append(info)
        dupA = {r["j"] for r in rows if r["dup_adjacency"]}
        dupB = {r["i"] for r in rows if r["dup_adjacency"]}
        dupS = {r["j"] for r in rows if r["dup_strict"]}
        drops = {"slab_summed (original)": [set(), set()][:len(slabs)],
                 "dedup_adjacency_keepA (primary)": [set(), dupA][:len(slabs)],
                 "dedup_adjacency_keepB": [dupB, set()][:len(slabs)],
                 "dedup_strict_keepA": [set(), dupS][:len(slabs)]}
        for v, d in drops.items():
            sums = patient_sums(slabs, d)
            for sc, acc in sums.items():
                variants[v].append(dict(acc, patient=pid, scaling=sc, n_slabs=len(slabs)))
    assert all(check), "per-slice counts do not reproduce the canonical per-slab totals"
    Mt = pd.DataFrame(meta)
    Mt.to_csv(VDATA / "vX1b_slab_overlap_per_patient.csv", index=False)
    two = Mt[Mt.note == ""]
    summ = pd.DataFrame([{
        "two_slab_patients": len(Mt), "analysable_pairs": len(two),
        "header_geometry_usable": "no (identity affine; no slice position in NIfTI or JSON)",
        "patients_with_duplicated_slices_adjacency": int((two.n_dup_adjacency > 0).sum()),
        "duplicated_slices_adjacency_total": int(two.n_dup_adjacency.sum()),
        "patients_with_duplicated_slices_strict": int((two.n_dup_strict > 0).sum()),
        "duplicated_slices_strict_total": int(two.n_dup_strict.sum()),
        "slices_in_two_slab_patients": int(two.n_slices_A.sum() + two.n_slices_B.sum()),
    }])
    # OT plausibility check: slice Dice of the reference masks at duplicated vs non-duplicated matched pairs
    od = []
    for _, r in two.iterrows():
        nccs = [float(x) for x in r.ncc_matched.split(";")]
        thr = [float(x) for x in r.adj_threshold.split(";")]
        dz = [float(x) for x in r.ot_slice_dice_matched.split(";")]
        od += [{"dup": n > t, "ot_dice": d} for n, t, d in zip(nccs, thr, dz) if np.isfinite(d)]
    od = pd.DataFrame(od)
    summ["ot_slice_dice_median_duplicated_pairs"] = od.loc[od.dup, "ot_dice"].median() if len(od) else np.nan
    summ["ot_slice_dice_median_other_matched_pairs"] = od.loc[~od.dup, "ot_dice"].median() if len(od) else np.nan
    summ.to_csv(VTAB / "vX1b_slab_overlap_summary.csv", index=False)
    print(summ.T.to_string())
    out, ledgers = [], []
    for v, rows in variants.items():
        D = pd.DataFrame(rows)
        for sc, g in D.groupby("scaling"):
            P = to_frame(g.drop(columns="scaling").to_dict("records"), protocol)
            out += X.summarise(P, f"{sc}: all patients | {v}")
            if sc == "s03_harmonised" and v.startswith("dedup_adjacency_keepA"):
                for prot, gp in P.groupby("protocol"):
                    if len(gp) >= 8:
                        out += X.summarise(gp, f"{sc}: protocol {prot} | {v}")
            L = P.reset_index().assign(scaling=sc, variant=v)
            ledgers.append(L)
    R = pd.DataFrame(out)
    R.to_csv(VTAB / "vX1b_isles2018_core_vs_dwi_dedup.csv", index=False)
    led = pd.concat(ledgers)
    led = led.merge(Mt[["patient", "n_dup_adjacency", "n_dup_strict", "best_block_order"]], on="patient", how="left")
    led.to_csv(VDATA / "vX1b_isles2018_per_patient_ledger.csv", index=False)
    key = R[R.analysis.str.contains("all patients") & R.metric.isin(
        ["dice_mean", "sensitivity_mean", "precision_mean", "vol_bias_ml", "spearman_core_vs_dwi", "bland_altman_loa_ml"])]
    print(key.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
