"""Feature-set definitions (fixed before model fitting)."""
from config import CLINICAL_22

DIST = ["mean", "sd", "skew", "kurt", "p10", "p25", "p75", "p90"]

CBF = ["core_rcbf20_hypo_frac", "core_rcbf30_hypo_frac", "core_rcbf38_hypo_frac", "core_rcbf30_frac",
       "rcbf_ipsi_ratio", "rcbf_in_hypo"] + [f"rcbf_ipsi_{s}" for s in DIST]
CBV = ["rcbv_ipsi_ratio", "lowcbv_rcbv60_frac", "cbv_index_hypo"] + [f"rcbv_ipsi_{s}" for s in DIST]
MTT = ["rmtt_ipsi_ratio", "mtt145_frac", "rmtt_in_hypo"] + [f"rmtt_ipsi_{s}" for s in DIST]
TMAX = ["tmax_gt4_frac", "tmax_gt6_frac", "tmax_gt8_frac", "tmax_gt10_frac", "hir", "tmax_ipsi_minus_contra"] + \
       [f"tmax_ipsi_{s}" for s in DIST + ["p50"]]
MISMATCH = ["mismatch_ratio_log", "mismatch_frac"]
CTP_ALL = CBF + CBV + MTT + TMAX + MISMATCH
# classical perfusion-threshold benchmark (RAPID-like definitions)
THRESH = ["core_rcbf30_hypo_frac", "tmax_gt6_frac", "mismatch_ratio_log", "hir"]
# Features whose value does not depend on the absolute Tmax scale (sensitivity analysis): ratios to the contralateral
# median and fractions defined without a Tmax threshold (30 features). Excluded: every Tmax feature and every feature
# computed inside the Tmax > 6 s mask (core_rcbf*_hypo_frac, rcbf_in_hypo, cbv_index_hypo, rmtt_in_hypo, mismatch_*).
# Residual dependence: the ipsilateral hemisphere is the one with the larger Tmax > 6 s fraction (a between-hemisphere
# comparison, robust to a common scale factor). Corrected 2026-11-13: rcbf_in_hypo (mean rCBF inside the Tmax > 6 s
# mask) had been listed here; the sensitivity analysis with the corrected list is s06 'scalefree' (tag _sens_scalefree).
# The earlier run (tag _sens_features, 31 features including rcbf_in_hypo) is retained unchanged for provenance.
SCALE_FREE = ["core_rcbf30_frac", "rcbf_ipsi_ratio"] + [f"rcbf_ipsi_{s}" for s in DIST] + \
             ["rcbv_ipsi_ratio", "lowcbv_rcbv60_frac"] + [f"rcbv_ipsi_{s}" for s in DIST] + \
             ["rmtt_ipsi_ratio", "mtt145_frac"] + [f"rmtt_ipsi_{s}" for s in DIST]
SCALE_FREE = list(dict.fromkeys(SCALE_FREE))
assert "rcbf_in_hypo" not in SCALE_FREE and not any(f in SCALE_FREE for f in TMAX + MISMATCH) and len(SCALE_FREE) == 30

CHANNEL_OF = {**{f: "CBF" for f in CBF}, **{f: "CBV" for f in CBV}, **{f: "MTT" for f in MTT},
              **{f: "Tmax" for f in TMAX}, **{f: "Mismatch" for f in MISMATCH},
              **{f: "Clinical" for f in CLINICAL_22}}
