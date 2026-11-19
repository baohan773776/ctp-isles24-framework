"""External technical component benchmark 3 (PREPARED, NOT EXECUTED in this revision): admission-NCCT intracranial
mask (vD_registration.intracranial_mask, frozen) vs the Johns Hopkins manual head-CT masks
(doi:10.7281/T1/CZDPSX; CC BY-NC 4.0; 35 subjects, NCCT; masks = "brain areas including CSF", i.e. the same
intracranial-cavity target as our mask). The repository blocks automated download (HTTP 403 / browser challenge);
download it manually (~430 MB) and set JHU_DIR to the folder holding the extracted NIfTI files.

Target harmonisation: our mask is computed on the 4x4 in-plane block-averaged grid used by the pipeline; the manual
mask is block-averaged on the same grid and binarised at 0.5. No parameter is tuned on the JHU masks.
Unit of analysis: subject (subjects with 2 scans/kernels contribute one value = mean over their scans; CIs by
subject-level bootstrap). Metrics: Dice, IoU, sensitivity, specificity (within the head), volume error (mL), failure rate.
Population caveat: JHU scans are intracerebral/intraventricular haemorrhage patients (MISTIE/CLEAR), not ischaemic stroke.
Usage: set JHU_DIR, then python vX3_jhu_brain_extraction.py
"""
import glob
import os
import re
import numpy as np
import pandas as pd
import nibabel as nib
from v_common import VTAB, VDATA
from vD_registration import intracranial_mask
from s13_fetch_native import block

JHU_DIR = os.environ.get("JHU_DIR", "")


def pairs():
    imgs = [p for p in glob.glob(os.path.join(JHU_DIR, "**", "*.nii*"), recursive=True) if "mask" not in os.path.basename(p).lower()]
    for im in sorted(imgs):
        stem = os.path.basename(im).split(".nii")[0]
        cand = [p for p in glob.glob(os.path.join(os.path.dirname(im), f"{stem}*mask*.nii*"))]
        if cand:
            yield im, sorted(cand)[0]


def main():
    assert JHU_DIR and os.path.isdir(JHU_DIR), "set JHU_DIR to the manually downloaded JHU dataset"
    rows = []
    for im, mk in pairs():
        img = nib.as_closest_canonical(nib.load(im))
        hu = np.asarray(img.dataobj, dtype=np.float32)
        ref = np.asarray(nib.as_closest_canonical(nib.load(mk)).dataobj) > 0
        hb = block(hu, np.mean); rb = block(ref.astype(np.float32), np.mean) > 0.5
        vml = float(np.prod(img.header.get_zooms()[:3])) * 16 / 1000
        try:
            pr = intracranial_mask(hb); fail = pr.sum() < 1000
        except Exception:
            pr, fail = np.zeros_like(rb), True
        head = hb > -500
        tp, fp, fn = (pr & rb).sum(), (pr & ~rb).sum(), (~pr & rb).sum(); tn = (~pr & ~rb & head).sum()
        sid = re.sub(r"[^0-9A-Za-z]", "", os.path.basename(im))[:12]
        rows.append({"scan": os.path.basename(im), "subject": sid, "failure": fail, "dice": 2 * tp / (2 * tp + fp + fn),
                     "iou": tp / (tp + fp + fn), "sensitivity": tp / (tp + fn), "specificity": tn / (tn + fp),
                     "vol_pred_ml": pr.sum() * vml, "vol_ref_ml": rb.sum() * vml})
    D = pd.DataFrame(rows); D["vol_err_ml"] = D.vol_pred_ml - D.vol_ref_ml
    D.to_csv(VDATA / "vX3_jhu_per_scan.csv", index=False)
    S = D.groupby("subject")[["dice", "iou", "sensitivity", "specificity", "vol_err_ml"]].mean()
    rng = np.random.default_rng(20261114)
    out = []
    for c in S.columns:
        bt = [S[c].iloc[rng.integers(0, len(S), len(S))].mean() for _ in range(2000)]
        out.append({"metric": c, "n_subjects": len(S), "n_scans": len(D), "estimate": S[c].mean(),
                    "ci_lo": np.percentile(bt, 2.5), "ci_hi": np.percentile(bt, 97.5), "failures": int(D.failure.sum())})
    pd.DataFrame(out).to_csv(VTAB / "vX3_jhu_brain_extraction.csv", index=False)
    print(pd.DataFrame(out).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
