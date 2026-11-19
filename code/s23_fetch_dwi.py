"""Fetch the skull-stripped follow-up DWI (co-registered to NCCT space) from the HF mirror, block-averaged
on the same 4x4 in-plane grid as s13, for atlas registration (H1). Output: NATIVE_DIR/<sid>_dwi.npz"""
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pyarrow.parquet as pq
from config import DATA
from httpfile import HTTPFile, shard_url
from s13_fetch_native import NATIVE_DIR, load_nii, block

sys.stdout.reconfigure(encoding="utf-8")


def fetch(i):
    f = HTTPFile(shard_url(i))
    pf = pq.ParquetFile(f)
    sid = pf.read(columns=["subject_id"]).to_pylist()[0]["subject_id"]
    cell = pf.read(columns=["dwi"]).to_pylist()[0]["dwi"]
    img, a = load_nii(cell)
    if a.ndim == 4:
        a = a[..., -1]  # highest b-value volume if a series is stored
    a = np.nan_to_num(a, nan=0.0)
    np.savez_compressed(NATIVE_DIR / f"{sid}_dwi.npz", dwi=block(a, np.mean).astype(np.float32),
                        affine=img.affine, zooms=np.array(img.header.get_zooms()[:3]), shape=np.array(a.shape))
    return {"shard": i, "subject_id": sid, "shape": list(a.shape), "MB": f.bytes_read / 1e6}


def main():
    done = {p.name.replace("_dwi.npz", "") for p in NATIVE_DIR.glob("*_dwi.npz")}
    meta = {json.loads(l)["shard"]: json.loads(l)["subject_id"] for l in (DATA / "native_meta.jsonl").read_text(encoding="utf-8").splitlines()}
    todo = [i for i, s in meta.items() if s not in done]
    print("todo", len(todo), flush=True)
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(fetch, i): i for i in todo}
        for k, fu in enumerate(as_completed(futs)):
            try:
                r = fu.result(); print(k, r, flush=True)
            except Exception as e:
                print("FAIL", futs[fu], repr(e), flush=True)


if __name__ == "__main__":
    main()
