"""Experiment A, centre check: within-centre (inferred, canonical mapping) AUC of the consistent-nested models with a
centre-stratified patient bootstrap (same scheme as s21). Motivation: Tmax-recovery failure (no ceiling) is concentrated
in the inferred Zurich centre (32/41), whose outcome rate is low, so recovered-unit CTP features could carry centre signal.
"""
import numpy as np
import pandas as pd
from v_common import VOOF, VTAB, VDATA, N_BOOT, BOOT_SEED, load_oof
from vC_provenance import within_auc

ids, y, P = load_oof(VOOF / "oof_long_vA.csv")
L = pd.read_csv(VDATA / "patient_provenance_ledger.csv").set_index("subject_id")
site = np.where(L.loc[ids, "canonical_site_inferred"].str.startswith("Zurich"), "Zurich", "Munich")
rng = np.random.default_rng(BOOT_SEED)
idx = {s: np.nonzero(site == s)[0] for s in np.unique(site)}
boots = [np.concatenate([rng.choice(ix, len(ix)) for ix in idx.values()]) for _ in range(N_BOOT)]
wb = {m: np.array([np.mean([within_auc(y[b], p[b], site[b]) for p in P[m]]) for b in boots]) for m in P}
rows = [{"model": m, "within_centre_auc": np.mean([within_auc(y, p, site) for p in P[m]]),
         "ci_lo": np.percentile(wb[m], 2.5), "ci_hi": np.percentile(wb[m], 97.5)} for m in sorted(P)]
for new, ref in (("A_late_rec", "A_clin"), ("A_late_nat", "A_clin"), ("A_ctp_nat", "A_ctp_rec"), ("A_late_nat", "A_late_rec")):
    d = wb[new] - wb[ref]
    rows.append({"model": f"delta {new} - {ref}", "within_centre_auc": rows[[r["model"] for r in rows].index(new)]["within_centre_auc"]
                 - rows[[r["model"] for r in rows].index(ref)]["within_centre_auc"],
                 "ci_lo": np.percentile(d, 2.5), "ci_hi": np.percentile(d, 97.5),
                 "p_bootstrap": min(1, 2 * min((d <= 0).mean(), (d >= 0).mean()))})
out = pd.DataFrame(rows)
out.to_csv(VTAB / "vA_within_centre.csv", index=False)
print(out.round(3).to_string(index=False))
