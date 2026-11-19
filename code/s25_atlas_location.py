"""H1 (PLAN_v4_prespecified.md): location of hypoperfusion and of the final infarct in eloquent regions.

MNI152 2-mm template (nilearn) -> subject skull-stripped follow-up DWI (NCCT space, 4x4 in-plane block grid):
affine registration with SimpleITK (Mattes MI, 3-level pyramid). Atlas labels and a hemisphere map are carried
with nearest-neighbour interpolation. QC: Dice(warped MNI brain mask, subject brain mask).

Regions (ipsilateral to the perfusion deficit unless stated):
  CST    Juelich 'WM Corticospinal tract'
  DEEP   Harvard-Oxford subcortical caudate, putamen, pallidum, thalamus
  INSOP  Harvard-Oxford insular cortex + frontal/central/parietal opercular cortex
  LANG   LEFT Harvard-Oxford IFG pars opercularis/triangularis, posterior STG, supramarginal (ant/post), angular
Features: fraction of the region involved by (a) Tmax > 6 s tissue (over region voxels inside the CTP slab) and
(b) the DWI final infarct (over all region voxels).
  python s25_atlas_location.py            all subjects (parallel), -> outputs/data/location_features.csv
  python s25_atlas_location.py qc         QC figure (FigS4)
"""
import sys
import numpy as np
import pandas as pd
import nibabel as nib
import SimpleITK as sitk
from concurrent.futures import ProcessPoolExecutor
from config import ROOT, DATA, TAB, FIG, CLIP

sys.stdout.reconfigure(encoding="utf-8")
NATIVE_DIR = ROOT.parent / "native_isles24"
ATL = ROOT.parent / "atlases"
F = 4
REG = {"CST": "CST", "DEEP": "DEEP", "INSOP": "INSOP", "LANG": "LANG"}


def mni_assets():
    from nilearn import datasets, image
    tmpl = datasets.load_mni152_template(resolution=2)
    bmask = datasets.load_mni152_brain_mask(resolution=2)
    ho = datasets.fetch_atlas_harvard_oxford("cort-maxprob-thr25-2mm", data_dir=str(ATL), verbose=0)
    hs = datasets.fetch_atlas_harvard_oxford("sub-maxprob-thr25-2mm", data_dir=str(ATL), verbose=0)
    ju = datasets.fetch_atlas_juelich("maxprob-thr25-2mm", data_dir=str(ATL), verbose=0)

    def lab(atlas, names):
        img = atlas.maps if not isinstance(atlas.maps, str) else nib.load(atlas.maps)
        img = image.resample_to_img(img, tmpl, interpolation="nearest", force_resample=True, copy_header=True)
        a = np.asarray(img.dataobj).astype(int)
        idx = [i for i, l in enumerate(atlas.labels) if str(l) in names]
        assert len(idx) == len(names), (names, idx)
        return np.isin(a, idx)

    cst = lab(ju, ["WM Corticospinal tract"])
    deep = lab(hs, [f"{s} {r}" for s in ("Left", "Right") for r in ("Caudate", "Putamen", "Pallidum", "Thalamus")])
    insop = lab(ho, ["Insular Cortex", "Frontal Opercular Cortex", "Central Opercular Cortex", "Parietal Opercular Cortex"])
    lang = lab(ho, ["Inferior Frontal Gyrus, pars opercularis", "Inferior Frontal Gyrus, pars triangularis",
                    "Superior Temporal Gyrus, posterior division", "Supramarginal Gyrus, anterior division",
                    "Supramarginal Gyrus, posterior division", "Angular Gyrus"])
    ijk = np.indices(tmpl.shape).reshape(3, -1)
    x = (tmpl.affine @ np.vstack([ijk, np.ones(ijk.shape[1])]))[0].reshape(tmpl.shape)
    hemi = np.where(x < 0, 1, 2)  # 1 = left, 2 = right (MNI x)
    # one label volume: bit-coded regions + hemisphere
    code = (cst * 1) + (deep * 2) + (insop * 4) + (lang * 8) + hemi * 16
    t = np.asarray(tmpl.dataobj, dtype=np.float32)
    return t, np.asarray(bmask.dataobj) > 0, code.astype(np.int32), tmpl.affine


def to_sitk(arr, affine):
    """nibabel (x,y,z RAS) array + affine -> SimpleITK image (LPS)."""
    img = sitk.GetImageFromArray(np.ascontiguousarray(np.transpose(arr, (2, 1, 0))))
    sp = np.sqrt((affine[:3, :3] ** 2).sum(0))
    R = affine[:3, :3] / sp
    flip = np.diag([-1, -1, 1])
    img.SetSpacing(sp.tolist()); img.SetOrigin((flip @ affine[:3, 3]).tolist())
    img.SetDirection((flip @ R).flatten().tolist())
    return img


def from_sitk(img):
    return np.transpose(sitk.GetArrayFromImage(img), (2, 1, 0))


def block_affine(aff):
    A = aff.copy()
    A[:3, :3] = aff[:3, :3] @ np.diag([F, F, 1])
    A[:3, 3] = aff[:3, 3] + aff[:3, :3] @ np.array([(F - 1) / 2, (F - 1) / 2, 0])
    return A


def register(fixed_arr, fixed_aff, mov_arr, mov_aff):
    fx = to_sitk(fixed_arr.astype(np.float32), fixed_aff)
    mv = to_sitk(mov_arr.astype(np.float32), mov_aff)
    init = sitk.CenteredTransformInitializer(fx, mv, sitk.AffineTransform(3),
                                             sitk.CenteredTransformInitializerFilter.MOMENTS)
    R = sitk.ImageRegistrationMethod()
    R.SetMetricAsMattesMutualInformation(32)
    R.SetMetricSamplingStrategy(R.RANDOM); R.SetMetricSamplingPercentage(0.25, 1234)
    R.SetInterpolator(sitk.sitkLinear)
    R.SetOptimizerAsRegularStepGradientDescent(1.0, 1e-4, 300, relaxationFactor=0.6)
    R.SetOptimizerScalesFromPhysicalShift()
    R.SetShrinkFactorsPerLevel([4, 2, 1]); R.SetSmoothingSigmasPerLevel([2, 1, 0])
    R.SetInitialTransform(init, inPlace=False)
    tx = R.Execute(fx, mv)
    return fx, tx, R.GetMetricValue()


def warp(arr, aff, fx, tx, nearest=True):
    mv = to_sitk(arr, aff)
    out = sitk.Resample(mv, fx, tx, sitk.sitkNearestNeighbor if nearest else sitk.sitkLinear, 0)
    return from_sitk(out)


def subject(args):
    sid, ipsi_side, assets = args
    t, bmask, code, taff = assets
    d = np.load(NATIVE_DIR / f"{sid}_dwi.npz")
    dwi, aff = d["dwi"], block_affine(d["affine"])
    z = np.load(NATIVE_DIR / f"{sid}.npz")
    if dwi.shape != z["Tmax"].shape:
        return {"subject_id": sid, "error": f"shape {dwi.shape} vs {z['Tmax'].shape}"}
    smask = dwi > np.percentile(dwi[dwi > 0], 2) if (dwi > 0).any() else dwi > 0
    fixed = np.where(smask, dwi / np.percentile(dwi[smask], 99), 0)
    fx, tx, metric = register(fixed, aff, t / t.max(), taff)
    wcode = warp(code, taff, fx, tx)
    wmask = warp(bmask.astype(np.uint8), taff, fx, tx) > 0
    dice = 2 * (wmask & smask).sum() / (wmask.sum() + smask.sum())
    m = {k: np.clip(z[k], 0, CLIP[k]) for k in ("CBF", "CBV", "MTT", "Tmax")}
    tissue = (m["CBF"] > 0) & (m["CBV"] > 0) & (m["CBV"] < 8) & (m["CBF"] < 99)
    hemi = (wcode // 16)
    ipsi_h = 1 if ipsi_side == "low" else 2   # axis-0 low index = left in RAS
    hypo = tissue & (m["Tmax"] > 6)
    les = z["lesion"] > 0.25 if "lesion" in z.files else np.zeros_like(tissue)
    # DWI lesion side: hemisphere holding most lesion voxels
    les_h = 1 if (les & (hemi == 1)).sum() >= (les & (hemi == 2)).sum() else 2
    out = {"subject_id": sid, "reg_dice": dice, "reg_metric": metric, "ipsi_hemi": ipsi_h, "dwi_hemi": les_h}
    for bit, name in ((1, "CST"), (2, "DEEP"), (4, "INSOP"), (8, "LANG")):
        reg = (wcode & bit) > 0
        for tag, lesion, side, denom_mask in (("ctp", hypo, ipsi_h, tissue), ("dwi", les, les_h, None)):
            r = reg & (hemi == (1 if name == "LANG" else side))
            dm = r & denom_mask if denom_mask is not None else r
            out[f"{tag}_{name}_vox"] = int(dm.sum())
            out[f"loc_{tag}_{name}"] = (lesion & dm).sum() / dm.sum() if dm.sum() >= 20 else np.nan
        out[f"ctp_{name}_coverage"] = ((reg & (hemi == (1 if name == 'LANG' else ipsi_h)) & tissue).sum()
                                       / max((reg & (hemi == (1 if name == 'LANG' else ipsi_h))).sum(), 1))
    return out


def main():
    nat = pd.read_csv(DATA / "ctp_features_native_149.csv").set_index("subject_id")
    sids = [s for s in nat.index if (NATIVE_DIR / f"{s}_dwi.npz").exists()]
    assets = mni_assets()
    args = [(s, nat.loc[s, "nat_qc_ipsi_side"], assets) for s in sids]
    rows = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for k, r in enumerate(ex.map(subject, args)):
            rows.append(r)
            if k % 20 == 0:
                print(k, r.get("subject_id"), round(r.get("reg_dice", np.nan), 3), flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "location_features.csv", index=False)
    print(df.describe().T.round(3).to_string())


def qc():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    loc = pd.read_csv(DATA / "location_features.csv").sort_values("reg_dice")
    pick = [loc.subject_id.iloc[0], loc.subject_id.iloc[len(loc) // 2], loc.subject_id.iloc[-1]]
    t, bmask, code, taff = mni_assets()
    fig, axs = plt.subplots(len(pick), 3, figsize=(7.2, 2.5 * len(pick)))
    for row, sid in zip(axs, pick):
        d = np.load(NATIVE_DIR / f"{sid}_dwi.npz"); dwi, aff = d["dwi"], block_affine(d["affine"])
        smask = dwi > np.percentile(dwi[dwi > 0], 2)
        fixed = np.where(smask, dwi / np.percentile(dwi[smask], 99), 0)
        fx, tx, _ = register(fixed, aff, t / t.max(), taff)
        wcode = warp(code, taff, fx, tx)
        z = np.load(NATIVE_DIR / f"{sid}.npz")
        nz = dwi.shape[2]
        for ax, k in zip(row, (int(nz * 0.40), int(nz * 0.55), int(nz * 0.70))):
            ax.imshow(np.rot90(dwi[:, :, k]), cmap="gray", vmax=np.percentile(dwi, 99.5))
            for bit, col in ((1, "#eb6834"), (2, "#1baf7a"), (4, "#eda100"), (8, "#e87ba4")):
                ax.contour(np.rot90(((wcode[:, :, k] & bit) > 0).astype(float)), [0.5], colors=col, linewidths=0.7)
            if "lesion" in z.files:
                ax.contour(np.rot90((z["lesion"][:, :, k] > 0.25).astype(float)), [0.5], colors="#2a78d6", linewidths=0.9)
            ax.axis("off")
        row[0].set_title(f"{sid}  Dice {loc.set_index('subject_id').loc[sid, 'reg_dice']:.2f}", loc="left", fontsize=8)
    fig.text(0.01, 0.005, "orange CST · green deep grey · yellow insula/operculum · pink left language cortex · blue DWI infarct",
             fontsize=7.5)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"FigS4_atlas_registration_qc.{ext}", dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    qc() if len(sys.argv) > 1 and sys.argv[1] == "qc" else main()
