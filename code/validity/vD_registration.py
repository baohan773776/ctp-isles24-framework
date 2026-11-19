"""Experiment D (post hoc): admission-time (pre-treatment) atlas registration for the CTP location features (H1).

Canonical s25 registered the MNI152 template to the FOLLOW-UP DWI (post-treatment image) to place the atlas regions,
then computed admission-CTP location features. Here the identical registration (SimpleITK affine, Mattes MI,
3-level pyramid; s25.register) uses ONLY the ADMISSION NCCT, which is the reference space of the release (perfusion
maps and DWI are already warped to it, so no other transform is needed at admission).
Admission-time NCCT pre-processing (frozen before any outcome analysis; no learning):
  intracranial mask = voxels with -20 < HU < 100 enclosed by the skull (HU >= 100, closed, filled slice-wise),
  largest connected component, morphological opening; target = intracranial cavity INCLUDING CSF.
  fixed image = clip(HU, 0, 80) inside the intracranial mask, scaled to [0, 1].
Moving image: MNI152 2-mm template (s25.mni_assets). Region definitions, Tmax > 6 s definition and denominators are
identical to s25.
QC: Dice(warped MNI brain mask, NCCT intracranial mask); for comparison the canonical DWI-based registration is re-run
here and scored against the same NCCT mask; region-wise Dice between the two warped atlases (registration concordance).
Outputs: outputs_validity/data/vD_location_features_ncct.csv, tables/vD_*.csv
"""
import sys
import numpy as np
import pandas as pd
from scipy import ndimage
from concurrent.futures import ProcessPoolExecutor
from v_common import VDATA, VTAB, NATIVE_DIR, DATA
from config import CLIP
import s25_atlas_location as A

REGIONS = ((1, "CST"), (2, "DEEP"), (4, "INSOP"), (8, "LANG"))


def intracranial_mask(hu):
    """Frozen admission-NCCT intracranial-cavity mask (includes CSF). Works on any 3-D HU array."""
    bone = hu >= 100
    skull = ndimage.binary_closing(bone, structure=np.ones((3, 3, 1)), iterations=2)
    inside = np.zeros_like(skull)
    for k in range(hu.shape[2]):
        inside[:, :, k] = ndimage.binary_fill_holes(skull[:, :, k])
    ic = inside & ~skull & (hu > -20) & (hu < 100)
    ic = ndimage.binary_opening(ic, structure=np.ones((3, 3, 1)))
    lab, n = ndimage.label(ic)
    if n == 0:
        return ic
    sizes = ndimage.sum(ic, lab, range(1, n + 1))
    ic = lab == (1 + int(np.argmax(sizes)))
    for k in range(hu.shape[2]):
        ic[:, :, k] = ndimage.binary_fill_holes(ic[:, :, k])
    return ic


def location(wcode, m, ipsi_h):
    tissue = (m["CBF"] > 0) & (m["CBV"] > 0) & (m["CBV"] < 8) & (m["CBF"] < 99)
    hypo = tissue & (m["Tmax"] > 6)
    hemi = wcode // 16
    out = {}
    for bit, name in REGIONS:
        reg = (wcode & bit) > 0
        r = reg & (hemi == (1 if name == "LANG" else ipsi_h))
        dm = r & tissue
        out[f"ctp_{name}_vox"] = int(dm.sum())
        out[f"loc_ctp_{name}"] = (hypo & dm).sum() / dm.sum() if dm.sum() >= 20 else np.nan
        out[f"ctp_{name}_coverage"] = (r & tissue).sum() / max(r.sum(), 1)
    return out


def subject(args):
    sid, ipsi_side, assets = args
    t, bmask, code, taff = assets
    c = np.load(NATIVE_DIR / f"{sid}_ncct.npz")
    hu, aff = c["ncct"], A.block_affine(c["affine"])
    z = np.load(NATIVE_DIR / f"{sid}.npz")
    if hu.shape != z["Tmax"].shape:
        return {"subject_id": sid, "error": f"shape {hu.shape} vs {z['Tmax'].shape}"}
    ic = intracranial_mask(hu)
    out = {"subject_id": sid, "ic_ml": float(ic.sum() * np.prod(c["zooms"]) * 16 / 1000)}
    if ic.sum() < 1000:
        out["error"] = "intracranial mask failed"
        return out
    fixed = np.where(ic, np.clip(hu, 0, 80) / 80.0, 0).astype(np.float32)
    m = {k: np.clip(z[k], 0, CLIP[k]) for k in ("CBF", "CBV", "MTT", "Tmax")}
    ipsi_h = 1 if ipsi_side == "low" else 2
    warped = {}
    for tag, fx_arr in (("ncct", fixed), ("dwi", None)):
        if tag == "dwi":
            d = np.load(NATIVE_DIR / f"{sid}_dwi.npz")
            dwi = d["dwi"]
            smask = dwi > np.percentile(dwi[dwi > 0], 2) if (dwi > 0).any() else dwi > 0
            fx_arr = np.where(smask, dwi / np.percentile(dwi[smask], 99), 0)
        fx, tx, metric = A.register(fx_arr, aff, t / t.max(), taff)
        wcode = A.warp(code, taff, fx, tx)
        wmask = A.warp(bmask.astype(np.uint8), taff, fx, tx) > 0
        warped[tag] = wcode
        out[f"{tag}_reg_metric"] = metric
        out[f"{tag}_reg_dice_vs_ncct_ic"] = 2 * (wmask & ic).sum() / (wmask.sum() + ic.sum())
        out[f"{tag}_warped_brain_ml"] = float(wmask.sum() * np.prod(c["zooms"]) * 16 / 1000)
        out.update({f"{tag}__{k}": v for k, v in location(wcode, m, ipsi_h).items()})
    for bit, name in REGIONS:
        a, b = (warped["ncct"] & bit) > 0, (warped["dwi"] & bit) > 0
        out[f"concordance_dice_{name}"] = 2 * (a & b).sum() / max(a.sum() + b.sum(), 1)
    return out


def main():
    nat = pd.read_csv(DATA / "ctp_features_native_149.csv").set_index("subject_id")
    sids = [s for s in nat.index if (NATIVE_DIR / f"{s}_ncct.npz").exists() and (NATIVE_DIR / f"{s}_dwi.npz").exists()]
    assets = A.mni_assets()
    rows = []
    with ProcessPoolExecutor(max_workers=8) as ex:
        for k, r in enumerate(ex.map(subject, [(s, nat.loc[s, "nat_qc_ipsi_side"], assets) for s in sids])):
            rows.append(r)
            if k % 20 == 0:
                print(k, r.get("subject_id"), round(r.get("ncct_reg_dice_vs_ncct_ic", np.nan), 3), flush=True)
    D = pd.DataFrame(rows)
    D.to_csv(VDATA / "vD_location_features_ncct.csv", index=False)
    print(D.describe().T.round(3).to_string())


if __name__ == "__main__":
    main()
