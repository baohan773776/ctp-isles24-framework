"""Workspace inventory (metadata only; nothing large is opened).
Writes FULL_SOURCE_INVENTORY.csv: one row per file under analysis_v3 and per small text/metadata file elsewhere;
large binary trees (imaging, zips, caches) are summarised per directory with file counts and sizes."""
import os, sys, csv, hashlib
from pathlib import Path

# Workspace root = parent of analysis_v3 (this file lives in analysis_v3/audit_final); override with BRANCH3_WS.
WS = Path(os.environ.get("BRANCH3_WS", Path(__file__).resolve().parents[2]))
OUTDIR = Path(sys.argv[1]) if len(sys.argv) > 1 else WS / "BMC_MIDM_FEASIBILITY_FINAL_AUDIT_PACKAGE" / "07_AUDIT_AND_PROVENANCE"
OUTDIR.mkdir(parents=True, exist_ok=True)

EXCL_EXT = {".pkl", ".pickle", ".joblib", ".pt", ".pth", ".ckpt", ".onnx", ".h5", ".hdf5", ".safetensors", ".npy", ".npz",
            ".nii", ".gz", ".dcm", ".nrrd", ".mha", ".mhd", ".zip", ".parquet", ".pyc"}
SMALL_TEXT = {".csv", ".json", ".md", ".txt", ".py", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".docx", ".xlsx", ".png", ".pdf", ".svg"}


def module_of(name: str) -> str:
    n = name.lower()
    rules = [("s01", "M1 cohort/clinical"), ("s02", "M1 unit recovery/features"), ("s03", "M1 ISLES2018 simulation"),
             ("s13", "M1 native maps"), ("s15", "M1 native features/volumes"), ("s19", "M1 centre inference"),
             ("s04", "M2 nested CV"), ("s05", "M2 evaluation"), ("s17", "M2 precision/equivalence"), ("s16", "M2 combine OOF"),
             ("s06", "M3 sensitivity"), ("s07", "M3 interpretation"), ("s10", "M3 ordinal"), ("s14", "M3 reference models"),
             ("s18", "M3 subgroups"), ("s23", "M3 H3 DWI"), ("s24", "M3 H3 timeline"), ("s25", "M3 H1 atlas"), ("s26", "M3 H1/H2"),
             ("s27", "M3 Holm"), ("s20", "M4 geographic"), ("s21", "M4 within-centre"), ("s28", "M5 design"),
             ("s08", "Table 1 / Riley"), ("s09", "figures"), ("s22", "figures"), ("s29", "figures"), ("s11", "manuscript"),
             ("s12", "additional files"), ("s30", "package"),
             ("table1", "Table 1"), ("riley", "M5 Riley"), ("design_", "M5 design"), ("go_nogo", "M5 go/no-go"),
             ("timeline", "M3 H3"), ("location_lvo", "M3 H1/H2"), ("round4", "M3 Holm"), ("within_centre", "M4"),
             ("geographic", "M4"), ("munich", "M4"), ("site_", "M1 centre inference"), ("native", "M1 native"),
             ("isles2018", "M1 simulation"), ("precision", "M2 precision"), ("paired", "M3 paired comparisons"),
             ("performance", "M3 performance"), ("dca", "M3 decision curves"), ("reclass", "M3 reclassification"),
             ("overfit", "M2 overfit gap"), ("sens_", "M3 sensitivity"), ("subgroup", "M3 subgroups"), ("ordinal", "M3 ordinal"),
             ("coef", "M3 interpretation"), ("shap", "M3 interpretation"), ("missing", "M1 clinical audit"),
             ("included_vs", "M1 cohort"), ("cohort", "M1 cohort"), ("fold_manifest", "M2 fold manifest"),
             ("oof", "M2 OOF predictions"), ("inner_best", "M2 tuning"), ("ctp_features", "M1 features"),
             ("location_features", "M3 H1 features"), ("fingerprint", "M1 centre inference"), ("inferred_site", "M1 centre inference"),
             ("reference_verification", "references"), ("manuscript", "manuscript"), ("cover", "cover letter"),
             ("additional_file", "additional files"), ("fig", "figures"), ("plan", "SAP"), ("sap_", "SAP"),
             ("readme", "documentation"), ("review", "documentation"), ("bao_cao", "documentation"), ("requirements", "environment"),
             ("config", "configuration"), ("features.py", "M1 feature lists"), ("stats_utils", "M2 statistics"), ("httpfile", "M1 data access")]
    for k, v in rules:
        if k in n:
            return v
    return ""


def kind_of(p: Path) -> str:
    e = p.suffix.lower()
    if e == ".py":
        return "code"
    if e in (".md", ".txt", ".docx", ".pdf"):
        return "documentation" if e != ".docx" or "manuscript" not in p.name.lower() else "manuscript"
    if e in (".csv", ".json", ".xlsx", ".png", ".svg"):
        return "generated_result"
    if e in EXCL_EXT:
        return "source_data_or_binary"
    return "other"


def sha256(p: Path, limit=200 * 1024 * 1024):
    if p.stat().st_size > limit:
        return ""
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


rows = []
# 1. analysis_v3: every file (except caches and the two package folders, summarised)
A = WS / "analysis_v3"
for p in sorted(A.rglob("*")):
    if not p.is_file():
        continue
    rel = p.relative_to(WS).as_posix()
    if "__pycache__" in rel:
        continue
    if rel.startswith("analysis_v3/FINAL_PACKAGE_BMC_MIDM/") or rel.startswith("analysis_v3/BMC_MIDM_FEASIBILITY_FINAL_AUDIT_PACKAGE/"):
        continue
    e = p.suffix.lower()
    # candidate flag only; a06_package.py rewrites include_in_package from the files actually copied (08_FILE_MANIFEST.csv)
    include = e in SMALL_TEXT and e not in EXCL_EXT and "_superseded" not in rel and "v3_full_backup" not in rel
    rows.append({"relative_path": rel, "size_bytes": p.stat().st_size, "file_type": e or "none", "module_or_claim": module_of(p.name),
                 "kind": kind_of(p), "include_in_package": "candidate" if include else "no",
                 "provenance_verifiable": "yes (regenerated by named script)" if kind_of(p) == "generated_result" else
                 ("yes (source in repository)" if e == ".py" else "n/a"),
                 "sha256": sha256(p) if include else ""})

# 2. other top-level trees: summarise directories, list small metadata files individually
for top in sorted(WS.iterdir()):
    if top.name in ("analysis_v3",) or top.name.startswith("BMC_MIDM_FEASIBILITY"):
        continue
    if top.is_file():
        rows.append({"relative_path": top.name, "size_bytes": top.stat().st_size, "file_type": top.suffix.lower(),
                     "module_or_claim": "raw download / companion" , "kind": "source_data_or_binary" if top.suffix == ".zip" else "documentation",
                     "include_in_package": "no", "provenance_verifiable": "external", "sha256": ""})
        continue
    agg = {}
    for p in top.rglob("*"):
        if not p.is_file():
            continue
        e = p.suffix.lower()
        d = p.parent.relative_to(WS).as_posix()
        if e in (".csv", ".json", ".md", ".txt", ".py", ".xlsx", ".docx", ".pdf") and p.stat().st_size < 5_000_000:
            rows.append({"relative_path": p.relative_to(WS).as_posix(), "size_bytes": p.stat().st_size, "file_type": e,
                         "module_or_claim": "source data / companion study" if "extracted" in d else "M1 source data",
                         "kind": "source_data" if e in (".csv", ".json", ".xlsx") else kind_of(p),
                         "include_in_package": "no", "provenance_verifiable": "external (public dataset / companion)", "sha256": ""})
        else:
            a = agg.setdefault(d, {"n": 0, "bytes": 0, "ext": set()})
            a["n"] += 1; a["bytes"] += p.stat().st_size; a["ext"].add(e)
    for d, a in sorted(agg.items()):
        rows.append({"relative_path": d + "/  [" + str(a["n"]) + " files: " + ",".join(sorted(x for x in a["ext"] if x)) + "]",
                     "size_bytes": a["bytes"], "file_type": "directory summary", "module_or_claim": "M1 source imaging / binaries",
                     "kind": "source_data_or_binary", "include_in_package": "no", "provenance_verifiable": "external (public dataset)", "sha256": ""})

with open(OUTDIR / "FULL_SOURCE_INVENTORY.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("rows:", len(rows), "->", OUTDIR / "FULL_SOURCE_INVENTORY.csv")
print("include=yes:", sum(r["include_in_package"] == "yes" for r in rows),
      "bytes:", sum(r["size_bytes"] for r in rows if r["include_in_package"] == "yes"))
