"""Inferred acquisition centre from data-provenance signatures of the original release.

The release does not label centres, but the descriptor reports 100 Munich (Center 1) and 50 Zurich
(Center 2) training cases; the public release contains 149 of the 150. Two independent provenance
signatures separate the cases:
  (1) storage precision of the perfusion maps: values quantised to multiples of 1/64 (integer-scaled
      export) versus unquantised float values;
  (2) NCCT slice thickness (2 mm vs 4 mm) and CTP slab coverage.
We cluster on (1), report its agreement with (2) and with contiguous subject-ID blocks, and use the
cluster whose size matches 50 as the inferred Zurich cohort. This is an inference, stated as such.
Outputs: outputs/data/inferred_site.csv, outputs/tables/site_inference.json
"""
import json
import sys
import numpy as np
import pandas as pd
from config import DATA, TAB

sys.stdout.reconfigure(encoding="utf-8")


def main():
    meta = [json.loads(l) for l in (DATA / "native_meta.jsonl").read_text(encoding="utf-8").splitlines()]
    m = pd.DataFrame(meta).drop_duplicates("subject_id").set_index("subject_id").sort_index()
    # only actual voxel values (maxima) are informative; medians/percentiles are interpolated
    vals = m[[f"{c}_max" for c in ("CBF", "CBV", "MTT", "Tmax")]]
    quant = (np.abs(vals * 64 - np.round(vals * 64)) < 1e-4).mean(axis=1)
    m["quantised_share"] = quant
    m["provenance"] = np.where(quant >= 0.75, "quantised", "float")
    m["slice_mm"] = m.zooms.apply(lambda z: round(z[2], 2))
    m["idnum"] = m.index.str.extract(r"(\d+)$")[0].astype(int).values
    sizes = m.provenance.value_counts().to_dict()
    site2 = min(sizes, key=lambda k: abs(sizes[k] - 50))
    m["site_inferred"] = np.where(m.provenance == site2, "Zurich (inferred)", "Munich (inferred)")
    z = m[m.site_inferred.str.startswith("Zurich")]
    res = {
        "cluster_sizes": sizes, "descriptor_sizes": {"Munich": 99, "Zurich": 50},
        "zurich_id_range": [int(z.idnum.min()), int(z.idnum.max())],
        "ids_in_zurich_range_not_in_cluster": m[(m.idnum >= z.idnum.min()) & (m.idnum <= z.idnum.max())
                                                & (m.site_inferred.str.startswith("Munich"))].index.tolist(),
        "crosstab_slice_mm": pd.crosstab(m.site_inferred, m.slice_mm).to_dict(),
        "ctp_slab_mm_median": m.groupby("site_inferred").ctp_slab_mm.median().to_dict(),
        "quantised_share_by_site": m.groupby("site_inferred").quantised_share.describe()[["min", "max"]].to_dict(),
    }
    coh = pd.read_csv(DATA / "cohort_129.csv")[["subject_id", "poor", "mrs90"]].set_index("subject_id")
    c = coh.join(m[["site_inferred"]])
    res["analysed_by_site"] = c.groupby("site_inferred").agg(n=("poor", "size"), poor=("poor", "sum")).to_dict()
    m[["site_inferred", "provenance", "quantised_share", "slice_mm", "ctp_slab_mm", "idnum"]].to_csv(DATA / "inferred_site.csv")
    json.dump(res, open(TAB / "site_inference.json", "w"), indent=2, default=str)
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
