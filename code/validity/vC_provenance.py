"""Experiment C (post hoc): patient-level centre-provenance ledger and sensitivity of M4 to ambiguous assignments.

The public release carries no centre label. The canonical inference (s19) clusters on the storage precision of the
native perfusion maps (quantised to 1/64 vs float) and obtains 99/50. This script does NOT change the canonical
mapping; it (1) tabulates every available provenance signature per patient, (2) flags patients whose signatures
disagree, and (3) re-runs the M4 analyses (within-centre AUC, leave-one-centre-out Munich -> Zurich) under each
alternative mapping of the ambiguous patients.
Signatures: S1 map quantisation (s19), S2 subject-ID block (contiguous blocks 1-119/183-189 vs 133-182),
S3 NCCT slice thickness (2 mm typical of cluster 'quantised', 4 mm of cluster 'float'; overlapping),
S4 native in-plane pixel size, S5 CTP slab coverage, S6 NiftyReg descriptor string, S7 Tmax minimum value.
Outputs: outputs_validity/data/patient_provenance_ledger.csv, tables/vC_site_sensitivity_*.csv
"""
import json
import numpy as np
import pandas as pd
from v_common import VDATA, VTAB, DATA, OOF, SEEDS, N_BOOT, BOOT_SEED
from stats_utils import auc_fast, calib


def ledger():
    meta = pd.DataFrame([json.loads(l) for l in (DATA / "native_meta.jsonl").read_text(encoding="utf-8").splitlines()])
    meta = meta.drop_duplicates("subject_id").set_index("subject_id").sort_index()
    site = pd.read_csv(DATA / "inferred_site.csv").set_index("subject_id")
    coh = pd.read_csv(DATA / "cohort_129.csv").set_index("subject_id")
    flow = pd.read_csv(DATA / "cohort_flow_149.csv").set_index("subject_id")
    L = pd.DataFrame(index=meta.index)
    L["hf_shard"] = meta.shard
    L["idnum"] = L.index.str.extract(r"(\d+)$")[0].astype(int).values
    L["S1_quantised_share"] = site.quantised_share
    L["S1_cluster"] = site.provenance
    L["S2_id_block"] = np.where((L.idnum >= 133) & (L.idnum <= 182), "block_133_182", "block_1_119_183_189")
    L["S3_ncct_slice_mm"] = meta.zooms.apply(lambda z: round(z[2], 2))
    L["S4_inplane_mm"] = meta.zooms.apply(lambda z: round(z[0], 3))
    L["S5_ctp_slab_mm"] = meta.ctp_slab_mm.round(1)
    L["S6_descrip"] = meta.descrip.str[:40]
    L["S7_tmax_min"] = meta.Tmax_min
    L["n_slices"] = meta["shape"].apply(lambda s: s[2])
    L["canonical_site_inferred"] = site.site_inferred
    s1 = np.where(L.S1_cluster == "float", "Zurich", "Munich")
    s2 = np.where(L.S2_id_block == "block_133_182", "Zurich", "Munich")
    s3 = np.where(L.S3_ncct_slice_mm >= 3.5, "Zurich", "Munich")
    L["S1_vote"], L["S2_vote"], L["S3_vote"] = s1, s2, s3
    L["S1_S2_agree"] = s1 == s2
    L["n_votes_zurich"] = (s1 == "Zurich").astype(int) + (s2 == "Zurich") + (s3 == "Zurich")
    L["certainty"] = np.select(
        [~L.S1_S2_agree, L.S1_S2_agree & (s1 == s3), L.S1_S2_agree & (s1 != s3)],
        ["AMBIGUOUS: storage signature and ID block disagree",
         "CONCORDANT: storage, ID block and slice thickness agree",
         "PROBABLE: storage and ID block agree; slice thickness atypical for the cluster"], "UNCLASSIFIED")
    L["in_analysed_cohort_129"] = L.index.isin(coh.index)
    L["exclusion_reason"] = flow.reindex(L.index).get("exclusion_reason", pd.Series(index=L.index, dtype=object))
    L["poor_outcome"] = coh.poor.reindex(L.index)
    L["exact_centre_identity"] = "NOT ESTABLISHED (no centre label in the public release)"
    L.reset_index().to_csv(VDATA / "patient_provenance_ledger.csv", index=False)
    summ = {
        "n_subjects_release": int(len(L)),
        "canonical_counts": L.canonical_site_inferred.value_counts().to_dict(),
        "S1_counts": pd.Series(s1).value_counts().to_dict(),
        "S2_counts": pd.Series(s2).value_counts().to_dict(),
        "certainty_counts": L.certainty.value_counts().to_dict(),
        "ambiguous_ids": L.index[~L.S1_S2_agree].tolist(),
        "ambiguous_in_cohort_129": L.index[~L.S1_S2_agree & L.in_analysed_cohort_129].tolist(),
        "ids_absent_in_block_133_182": sorted(set(range(133, 183)) - set(L.idnum)),
        "ids_absent_in_1_119": sorted(set(range(1, 120)) - set(L.idnum)),
        "ids_present_120_132": sorted(set(range(120, 133)) & set(L.idnum)),
        "probable_count_cohort": L[L.in_analysed_cohort_129].groupby("canonical_site_inferred").size().to_dict(),
    }
    json.dump(summ, open(VTAB / "vC_provenance_summary.json", "w"), indent=2, default=str)
    print(json.dumps(summ, indent=2, default=str))
    return L


def within_auc(y, p, site):
    num = den = 0.0
    for s in np.unique(site):
        k = site == s
        n1, n0 = y[k].sum(), (1 - y[k]).sum()
        if n1 and n0:
            num += auc_fast(y[k], p[k]) * n1 * n0; den += n1 * n0
    return num / den


def sensitivity(L):
    """Within-centre AUC (from canonical OOF, no refitting) and Munich->Zurich geographic validation (refit)
    under: canonical mapping, ambiguous -> ID-block centre, ambiguous excluded."""
    import s20_geographic as G
    o = pd.read_csv(OOF / "oof_long_all.csv")
    ids = np.sort(o.subject_id.unique())
    y = o.drop_duplicates("subject_id").set_index("subject_id").loc[ids, "y"].values
    P = {m: g.pivot(index="subject_id", columns="seed", values="p_poor").loc[ids, SEEDS].values.T for m, g in o.groupby("model")}
    canon = np.where(L.loc[ids, "canonical_site_inferred"].str.startswith("Zurich"), "Zurich", "Munich")
    amb = ~L.loc[ids, "S1_S2_agree"].values
    alt = canon.copy(); alt[amb] = L.loc[ids, "S2_vote"].values[amb]
    maps = {"canonical (S1 storage; 99/50 release)": (canon, np.ones(len(ids), bool)),
            "ambiguous -> ID block (100/49 release)": (alt, np.ones(len(ids), bool)),
            "ambiguous excluded": (canon, ~amb)}
    rng = np.random.default_rng(BOOT_SEED)
    rows, geo, geo_c = [], [], []
    for lab, (site, keep) in maps.items():
        yy, ss = y[keep], site[keep]
        idx_s = {s: np.nonzero(ss == s)[0] for s in np.unique(ss)}
        boots = [np.concatenate([rng.choice(ix, len(ix)) for ix in idx_s.values()]) for _ in range(N_BOOT)]
        wb = {}
        for m in ("P1_clin_GBM", "F_late_P1_E", "R1_clin_LR4", "F_late_R1_E", "E_CTP_all", "F_late_P1_Enat"):
            Pm = P[m][:, keep]
            wb[m] = np.array([np.mean([within_auc(yy[b], p[b], ss[b]) for p in Pm]) for b in boots])
            rows.append({"mapping": lab, "model": m, "n": int(keep.sum()), "n_zurich": int((ss == "Zurich").sum()),
                         "events_zurich": int(yy[ss == "Zurich"].sum()),
                         "within_centre_auc": np.mean([within_auc(yy, p, ss) for p in Pm]),
                         "within_lo": np.percentile(wb[m], 2.5), "within_hi": np.percentile(wb[m], 97.5)})
        for new, ref in (("F_late_P1_E", "P1_clin_GBM"), ("F_late_R1_E", "R1_clin_LR4")):
            db = wb[new] - wb[ref]
            rows.append({"mapping": lab, "model": f"delta {new} - {ref}", "n": int(keep.sum()),
                         "within_centre_auc": np.mean([within_auc(yy, p, ss) for p in P[new][:, keep]]) -
                         np.mean([within_auc(yy, p, ss) for p in P[ref][:, keep]]),
                         "within_lo": np.percentile(db, 2.5), "within_hi": np.percentile(db, 97.5)})
        # leave-one-centre-out, Munich -> Zurich (same code path as s20)
        df = G.data().set_index("subject_id").loc[ids].reset_index()
        df["site"] = site
        df = df[keep].reset_index(drop=True)
        dev, ext = df[df.site == "Munich"].reset_index(drop=True), df[df.site == "Zurich"].reset_index(drop=True)
        Pg = G.predict(dev, ext)
        r, c = G.evaluate(ext.poor.astype(int).values, Pg, "Munich -> Zurich", np.random.default_rng(BOOT_SEED))
        geo += [dict(x, mapping=lab) for x in r]; geo_c += [dict(x, mapping=lab) for x in c]
    pd.DataFrame(rows).to_csv(VTAB / "vC_site_sensitivity_within_centre.csv", index=False)
    pd.DataFrame(geo).to_csv(VTAB / "vC_site_sensitivity_geographic_perf.csv", index=False)
    pd.DataFrame(geo_c).to_csv(VTAB / "vC_site_sensitivity_geographic_paired.csv", index=False)
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    print(pd.DataFrame(geo_c).round(3).to_string(index=False))


if __name__ == "__main__":
    L = ledger()
    sensitivity(L)
