"""Targeted repair 1 (post hoc): reconcile the ISLES'24 training-set centre counts reported by different sources
and add outcome-independent case-level signatures for the one patient whose provenance signatures disagree.

Sources (as read on 2026-11-14):
  * arXiv:2408.11142 v1 (20 Aug 2024): training n = 150, Center 1 (Munich) 100, Center 2 (Zurich) 50 (Data structure).
  * arXiv:2408.11142 v2 (6 Jul 2025): training n = 149, Center 1 99, Center 2 50 (Data structure section).
  * Radiology: Artificial Intelligence 2026;8(3):e250603 (doi:10.1148/ryai.250603), Table 1: 100 / 49 for the
    149 training cases (confirmed by the authors; the publisher page blocked automated access from this pipeline).
  * arXiv v2 states that an info sheet lists every case with its centre. The separately downloadable info sheet
    (clinical_data-description.xlsx, Zenodo 16813698, 12 kB) was inspected: it holds only the variable dictionary.
No accessible source gives a subject-level centre list, so no mapping can be verified at case level. This script does not
change any canonical output or the existing sensitivity analyses (vC_provenance.py). It (1) writes the source table,
(2) adds three further outcome-independent signatures for every patient (release-level median-imputation pattern,
24-h NIHSS availability, CTP slab coverage) and (3) reports where the ambiguous patient falls on each signature
relative to the 148 patients whose storage and ID-block signatures agree. Outcomes are never used.
Outputs: outputs_validity/tables/vC2_centre_count_sources.csv, vC2_ambiguous_case_signatures.csv,
         vC2_signature_by_cluster.csv, outputs_validity/data/patient_provenance_ledger_extended.csv
"""
import sys
import numpy as np
import pandas as pd
from v_common import VDATA, VTAB, DATA
from config import ISLES24
from s01_build_cohort import CONT, DUR, CONT_MEDIAN, DUR_MEDIAN

sys.stdout.reconfigure(encoding="utf-8")
AMB = "sub-stroke0008"
IMP_VARS = ["Leucocytes", "CRP", "INR", "Onset to door_min"]


def sources():
    S = pd.DataFrame([
        {"source": "Riedel et al., arXiv:2408.11142 v1 (20 Aug 2024), section 'Data structure'",
         "training_n": 150, "centre_1_munich": 100, "centre_2_zurich": 50, "subject_level_list": "no",
         "status": "read from the PDF in this study"},
        {"source": "Riedel et al., arXiv:2408.11142 v2 (6 Jul 2025), section 'Data structure'",
         "training_n": 149, "centre_1_munich": 99, "centre_2_zurich": 50, "subject_level_list": "no",
         "status": "read from the PDF in this study"},
        {"source": "Riedel et al., Radiol Artif Intell 2026;8(3):e250603, Table 1",
         "training_n": 149, "centre_1_munich": 100, "centre_2_zurich": 49, "subject_level_list": "no",
         "status": "published Table 1 count (confirmed by the authors); no subject-level list"},
        {"source": "Info sheet clinical_data-description.xlsx, Zenodo record 16813698 (Aug 2025; 12,149 bytes; MD5 "
                   "c8d806a021614c6bb9f732756f9701d4), downloaded 2026-11-14",
         "training_n": np.nan, "centre_1_munich": np.nan, "centre_2_zurich": np.nan, "subject_level_list": "no",
         "status": "contains only the clinical variable dictionary (Supplementary Table 1); the per-case centre list described "
                   "in arXiv v2 is not in this file and may exist only inside the 99 GB train.7z archive (not downloaded)"},
        {"source": "This study, storage-precision signature (primary mapping)",
         "training_n": 149, "centre_1_munich": 99, "centre_2_zurich": 50, "subject_level_list": "inferred",
         "status": "inferred; matches arXiv v2"},
        {"source": "This study, contiguous subject-ID blocks",
         "training_n": 149, "centre_1_munich": 100, "centre_2_zurich": 49, "subject_level_list": "inferred",
         "status": "inferred; matches the journal Table 1 count"},
    ])
    S.to_csv(VTAB / "vC2_centre_count_sources.csv", index=False)
    return S


def extended_ledger():
    L = pd.read_csv(VDATA / "patient_provenance_ledger.csv").set_index("subject_id")
    coh = pd.read_csv(DATA / "cohort_129.csv").set_index("subject_id")
    fp = pd.read_csv(DATA / "native_acquisition_fingerprints.csv").set_index("subject_id")
    lab = pd.read_csv(ISLES24 / "labels" / "outcome_labels.csv").set_index("subject_id")
    med = dict(zip(CONT + DUR, CONT_MEDIAN + DUR_MEDIAN))
    imp = pd.DataFrame({v: np.isclose(coh[v], med[v], atol=1e-3) for v in IMP_VARS}, index=coh.index)
    L["S8_n_imputed_of_4"] = imp.sum(axis=1).reindex(L.index)          # only defined in the analysed 129
    L["S9_nihss24h_recorded"] = lab["NIHSS 24h"].notna().reindex(L.index)
    L["S10_ctp_slices"] = fp.ctp_slices.reindex(L.index)
    L.reset_index().to_csv(VDATA / "patient_provenance_ledger_extended.csv", index=False)
    return L


def compare(L):
    ref = L[L.S1_S2_agree].copy()
    ref["cluster"] = np.where(ref.S1_vote == "Zurich", "Zurich-like (storage and ID agree)", "Munich-like (storage and ID agree)")
    rows = []
    for sig, kind in (("S3_ncct_slice_mm", "num"), ("S4_inplane_mm", "num"), ("S5_ctp_slab_mm", "num"),
                      ("S10_ctp_slices", "num"), ("S8_n_imputed_of_4", "num"), ("S9_nihss24h_recorded", "bin")):
        for cl, g in ref.groupby("cluster"):
            v = g[sig].dropna()
            if kind == "bin":
                v = v.astype(float)
            rows.append({"signature": sig, "cluster": cl, "n": len(v), "mean": v.mean(), "median": v.median(),
                         "p05": v.quantile(0.05), "p95": v.quantile(0.95)})
    C = pd.DataFrame(rows)
    C.to_csv(VTAB / "vC2_signature_by_cluster.csv", index=False)
    a = L.loc[AMB]
    out = []
    for sig in C.signature.unique():
        val = a[sig]
        if pd.isna(val):
            continue
        val = float(val)
        g = C[C.signature == sig].set_index("cluster")
        m, z = g.loc["Munich-like (storage and ID agree)"], g.loc["Zurich-like (storage and ID agree)"]
        pm = (ref.loc[ref.cluster.str.startswith("Munich"), sig].dropna().astype(float) == val).mean()
        pz = (ref.loc[ref.cluster.str.startswith("Zurich"), sig].dropna().astype(float) == val).mean()
        closer = "Munich-like" if abs(val - m["median"]) < abs(val - z["median"]) else (
            "Zurich-like" if abs(val - z["median"]) < abs(val - m["median"]) else "neither")
        out.append({"signature": sig, "value_sub_stroke0008": val, "munich_like_median": m["median"],
                    "zurich_like_median": z["median"], "share_munich_like_with_same_value": pm,
                    "share_zurich_like_with_same_value": pz, "closer_to": closer})
    out.append({"signature": "S1 storage precision (primary mapping)", "value_sub_stroke0008": np.nan,
                "closer_to": "Zurich-like (float storage)"})
    out.append({"signature": "S2 subject-ID block", "value_sub_stroke0008": np.nan,
                "closer_to": "Munich-like (ID 8 inside block 1-119)"})
    O = pd.DataFrame(out)
    O["interpretation"] = "consistency only; no source provides the centre of this subject"
    O.to_csv(VTAB / "vC2_ambiguous_case_signatures.csv", index=False)
    print(C.round(3).to_string(index=False))
    print(O.round(3).to_string(index=False))


if __name__ == "__main__":
    print(sources().to_string(index=False))
    compare(extended_ledger())
