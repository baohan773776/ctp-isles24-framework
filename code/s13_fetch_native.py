"""Fetch the native-unit ISLES'24 perfusion maps (icobrain cva output, co-registered to NCCT space)
from the Hugging Face mirror of the official release (hugging-science/isles24-stroke, one parquet
file per subject). Only the needed columns are read via HTTP range requests (~29 MB / subject).

Per subject we store, in NATIVE_DIR/<sid>.npz:
  maps CBF/CBV/MTT/Tmax block-averaged 4x4 in-plane (about 1.9 x 1.9 x 2 mm), float32
  lvo (max-pooled) and lesion (fraction) masks on the same grid
and one metadata row (voxel size, native value ranges, CTP slab coverage, lesion volume in mL).
"""
import sys
import gzip
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import nibabel as nib
import pyarrow.parquet as pq
from config import ROOT, DATA
from httpfile import HTTPFile, shard_url

sys.stdout.reconfigure(encoding="utf-8")
NATIVE_DIR = ROOT.parent / "native_isles24"
NATIVE_DIR.mkdir(exist_ok=True)
MAPS = {"cbf": "CBF", "cbv": "CBV", "mtt": "MTT", "tmax": "Tmax"}
CLIN = ["subject_id", "age", "sex", "nihss_admission", "mrs_admission", "mrs_3month"]
F = 4  # in-plane block factor


def load_nii(cell):
    b = cell["bytes"]
    if b[:2] == b"\x1f\x8b":
        b = gzip.decompress(b)
    img = nib.as_closest_canonical(nib.Nifti1Image.from_bytes(b))
    return img, np.asarray(img.dataobj, dtype=np.float32)


def block(a, fn):
    x, y, z = a.shape
    a = a[: x - x % F, : y - y % F, :]
    a = a.reshape(a.shape[0] // F, F, a.shape[1] // F, F, z)
    return fn(a, axis=(1, 3))


def fetch(i):
    f = HTTPFile(shard_url(i))
    pf = pq.ParquetFile(f)
    clin = pf.read(columns=CLIN).to_pylist()[0]
    sid = clin["subject_id"]
    out = NATIVE_DIR / f"{sid}.npz"
    meta = dict(clin, shard=i)
    arrs = {}
    for col, nm in MAPS.items():
        cell = pf.read(columns=[col]).to_pylist()[0][col]
        img, a = load_nii(cell)
        zooms = [float(v) for v in img.header.get_zooms()[:3]]
        pos = a[np.isfinite(a) & (a > 0)]
        meta.update({
            f"{nm}_min": float(np.nanmin(a)), f"{nm}_max": float(np.nanmax(a)),
            f"{nm}_p50pos": float(np.median(pos)) if pos.size else np.nan,
            f"{nm}_p99pos": float(np.percentile(pos, 99)) if pos.size else np.nan,
            f"{nm}_neg_frac": float((a < 0).mean()), f"{nm}_nan_frac": float(np.isnan(a).mean()),
        })
        if nm == "Tmax":
            meta.update({"shape": list(a.shape), "zooms": zooms,
                         "descrip": img.header["descrip"].tobytes().decode("latin1").strip("\x00"),
                         "axcodes": "".join(nib.aff2axcodes(img.affine))})
            zs = np.nonzero((a > 0).any(axis=(0, 1)))[0]
            meta["ctp_slab_mm"] = float((zs.max() - zs.min() + 1) * zooms[2]) if zs.size else 0.0
            meta["ctp_slices"] = int(zs.size)
        a = np.nan_to_num(a, nan=0.0)
        arrs[nm] = block(a, np.mean).astype(np.float32)
    for col, nm in (("lvo_mask", "lvo"), ("lesion_mask", "lesion")):
        cell = pf.read(columns=[col]).to_pylist()[0][col]
        if cell is None or cell.get("bytes") is None:
            meta[f"{nm}_available"] = False
            continue
        img, a = load_nii(cell)
        meta[f"{nm}_available"] = True
        vox_ml = float(np.prod(img.header.get_zooms()[:3])) / 1000.0
        meta[f"{nm}_ml_native"] = float((a > 0.5).sum() * vox_ml)
        if a.shape[:2] == tuple(meta["shape"][:2]) and a.shape[2] == meta["shape"][2]:
            arrs[nm] = block((a > 0.5).astype(np.float32), np.max if nm == "lvo" else np.mean).astype(np.float32)
        else:
            meta[f"{nm}_shape_mismatch"] = list(a.shape)
    meta["grid_zooms"] = [meta["zooms"][0] * F, meta["zooms"][1] * F, meta["zooms"][2]]
    meta["MB_read"] = f.bytes_read / 1e6
    np.savez_compressed(out, **arrs)
    return meta


def main():
    idx = list(range(149))
    done = {}
    mfile = DATA / "native_meta.jsonl"
    if mfile.exists():
        for line in mfile.read_text(encoding="utf-8").splitlines():
            m = json.loads(line)
            done[m["shard"]] = m
    todo = [i for i in idx if i not in done]
    print("todo", len(todo), flush=True)
    with ThreadPoolExecutor(max_workers=6) as ex, open(mfile, "a", encoding="utf-8") as fh:
        futs = {ex.submit(fetch, i): i for i in todo}
        for k, fu in enumerate(as_completed(futs)):
            i = futs[fu]
            try:
                m = fu.result()
            except Exception as e:  # keep going; rerun picks up failures
                print("FAIL", i, repr(e), flush=True)
                continue
            fh.write(json.dumps(m, default=float) + "\n")
            fh.flush()
            print(k, i, m["subject_id"], round(m["MB_read"], 1), "MB", flush=True)


if __name__ == "__main__":
    main()
