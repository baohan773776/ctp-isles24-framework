"""Shared helpers for the validity-upgrade analyses (post hoc; never overwrite canonical outputs).

All outputs go to analysis_v3/outputs_validity/{tables,oof,data,figures}. The canonical folders
analysis_v3/outputs/* are only read.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import numpy as np
import pandas as pd
from config import ROOT, DATA, TAB, OOF, SEEDS, N_BOOT, BOOT_SEED  # noqa: E402  (canonical, read-only)
from stats_utils import auc_fast, calib  # noqa: E402

import os  # noqa: E402
# Optional overrides (defaults unchanged): BRANCH3_VOUT for the post hoc output folder, NATIVE_ISLES24_DIR for the
# local cache of native-unit maps read by vB_native_verification.py.
VOUT = Path(os.environ.get("BRANCH3_VOUT", ROOT / "outputs_validity"))
if VOUT.resolve() == Path(TAB).resolve().parent:
    raise SystemExit("BRANCH3_VOUT must not point to the canonical output folder")
VTAB, VOOF, VDATA, VFIG = (VOUT / d for d in ("tables", "oof", "data", "figures"))
for d in (VTAB, VOOF, VDATA, VFIG):
    d.mkdir(parents=True, exist_ok=True)
NATIVE_DIR = Path(os.environ.get("NATIVE_ISLES24_DIR", ROOT.parent / "native_isles24"))


def boot_indices(y, n_boot=N_BOOT, seed=BOOT_SEED):
    """Same patient-level bootstrap scheme as s05 (resamples with both classes present)."""
    rng = np.random.default_rng(seed)
    n = len(y)
    out = []
    while len(out) < n_boot:
        b = rng.integers(0, n, n)
        if 0 < y[b].sum() < n:
            out.append(b)
    return out


def load_oof(path, ids=None):
    o = pd.read_csv(path)
    if ids is None:
        ids = np.sort(o.subject_id.unique())
    y = o.drop_duplicates("subject_id").set_index("subject_id").loc[ids, "y"].values
    P = {m: g.pivot(index="subject_id", columns="seed", values="p_poor").loc[ids, SEEDS].values.T
         for m, g in o.groupby("model")}
    return np.asarray(ids), y, P


def seed_auc(y, Pm, idx=None):
    if idx is None:
        return float(np.mean([auc_fast(y, p) for p in Pm]))
    return float(np.mean([auc_fast(y[idx], p[idx]) for p in Pm]))


def perf_and_pairs(y, P, pairs, boots, label="", subset=None):
    """Seed-mean AUC with patient-bootstrap CI, calibration of the pooled mean-OOF probability,
    and paired seed-mean dAUC with bootstrap CI (identical estimands to s05)."""
    if subset is not None:
        y = y[subset]
        P = {m: v[:, subset] for m, v in P.items()}
        boots = boot_indices(y)
    bt = {m: np.array([seed_auc(y, P[m], b) for b in boots]) for m in P}
    perf = []
    for m in sorted(P):
        pm = P[m].mean(0)
        c = calib(y, pm)
        perf.append({"analysis": label, "model": m, "n": len(y), "events": int(y.sum()),
                     "auc_seed_mean": seed_auc(y, P[m]), "auc_seed_sd": float(np.std([auc_fast(y, p) for p in P[m]], ddof=1)),
                     "auc_ci_lo": np.percentile(bt[m], 2.5), "auc_ci_hi": np.percentile(bt[m], 97.5),
                     "brier_seed_mean": float(np.mean([np.mean((p - y) ** 2) for p in P[m]])),
                     "cal_slope_pooled": c["slope"], "cal_citl_pooled": c["citl"], "brier_pooled": c["brier"]})
    comp = []
    for new, ref, role in pairs:
        if new not in P or ref not in P:
            continue
        db = bt[new] - bt[ref]
        comp.append({"analysis": label, "new": new, "reference": ref, "role": role, "n": len(y), "events": int(y.sum()),
                     "delta_auc": seed_auc(y, P[new]) - seed_auc(y, P[ref]),
                     "ci_lo": np.percentile(db, 2.5), "ci_hi": np.percentile(db, 97.5),
                     "p_bootstrap": min(1.0, 2 * min((db <= 0).mean(), (db >= 0).mean()))})
    return pd.DataFrame(perf), pd.DataFrame(comp)
