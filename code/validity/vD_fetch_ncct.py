"""Experiment D, step 1: fetch the ADMISSION non-contrast CT (NCCT) of each ISLES'24 subject from the Hugging Face
mirror of the official release (same source and HTTP range-request reader as s13/s23; only the 'ncct' column,
~14 MB per subject), block-averaged on the same 4x4 in-plane grid as the native perfusion maps (s13).
NCCT is the reference space of the release (perfusion maps and follow-up DWI are warped to it), so admission-time
features can be generated in this space without any post-treatment image.
Output: native_isles24/<sid>_ncct.npz (ncct HU block mean, affine, zooms, shape) + outputs_validity/data/ncct_meta.csv
"""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from v_common import NATIVE_DIR, DATA, VDATA
from httpfile import HTTPFile, shard_url
from s13_fetch_native import load_nii, block


def fetch(i):
    f = HTTPFile(shard_url(i))
    pf = pq.ParquetFile(f)
    sid = pf.read(columns=["subject_id"]).to_pylist()[0]["subject_id"]
    out = NATIVE_DIR / f"{sid}_ncct.npz"
    cell = pf.read(columns=["ncct"]).to_pylist()[0]["ncct"]
    img, a = load_nii(cell)
    if a.ndim == 4:
        a = a[..., 0]
    a = np.nan_to_num(a, nan=-1024.0)
    np.savez_compressed(out, ncct=block(a, np.mean).astype(np.float32), affine=img.affine,
                        zooms=np.array(img.header.get_zooms()[:3]), shape=np.array(a.shape))
    return {"shard": i, "subject_id": sid, "shape": list(a.shape), "zooms": [float(z) for z in img.header.get_zooms()[:3]],
            "hu_p1": float(np.percentile(a, 1)), "hu_p99": float(np.percentile(a, 99)), "MB": f.bytes_read / 1e6}


def main():
    meta = {json.loads(l)["shard"]: json.loads(l)["subject_id"] for l in (DATA / "native_meta.jsonl").read_text(encoding="utf-8").splitlines()}
    done = {p.name.replace("_ncct.npz", "") for p in NATIVE_DIR.glob("*_ncct.npz")}
    todo = [i for i, s in meta.items() if s not in done]
    print("todo", len(todo), flush=True)
    rows = []
    mfile = VDATA / "ncct_meta.jsonl"
    with ThreadPoolExecutor(max_workers=6) as ex, open(mfile, "a", encoding="utf-8") as fh:
        futs = {ex.submit(fetch, i): i for i in todo}
        for k, fu in enumerate(as_completed(futs)):
            try:
                r = fu.result()
                fh.write(json.dumps(r) + "\n"); fh.flush()
                print(k, r["subject_id"], r["shape"], round(r["MB"], 1), flush=True)
            except Exception as e:
                print("FAIL", futs[fu], repr(e), flush=True)


if __name__ == "__main__":
    main()
