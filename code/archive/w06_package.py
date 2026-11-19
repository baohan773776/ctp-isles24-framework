"""Assemble BMC_FEASIBILITY_VALIDITY_UPGRADE/: code, lightweight results, manifests, three ZIPs (< 8 MB each),
SHA256 sums and ZIP integrity verification. Large inputs (.npy/.npz/.nii/.dcm, datasets, baseline snapshot) are
listed in EXCLUDED_INPUTS_MANIFEST.csv instead of being copied.

HISTORICAL (2026-11-14): builds the superseded validity-upgrade ZIPs. The current delivery is built by
w11_final_package.py (see README.md)."""
import os as _os
import sys as _sys
if _os.environ.get("BRANCH3_ALLOW_HISTORICAL") != "1":
    _sys.exit("Historical script (superseded validity-upgrade ZIPs); set BRANCH3_ALLOW_HISTORICAL=1 to run it anyway.")
import hashlib
import shutil
import zipfile
from pathlib import Path
import pandas as pd
from v_common import ROOT, VOUT, NATIVE_DIR

U = ROOT.parent / "BMC_FEASIBILITY_VALIDITY_UPGRADE"
Z = U / "ZIPS"
HERE = Path(__file__).resolve().parent
CANON_DEPS = ["config.py", "features.py", "stats_utils.py", "httpfile.py", "s02_ctp_features.py", "s04_models_cv.py",
              "s05_evaluate.py", "s13_fetch_native.py", "s14_extra_models.py", "s20_geographic.py", "s25_atlas_location.py"]
BAD_EXT = {".npy", ".npz", ".nii", ".gz", ".dcm", ".pkl", ".7z"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def copy_tree():
    for d in ("code", "results"):
        shutil.rmtree(U / d, ignore_errors=True)
    (U / "code" / "canonical_dependencies").mkdir(parents=True)
    for p in sorted(HERE.glob("*.py")):
        shutil.copy2(p, U / "code" / p.name)
    for n in CANON_DEPS:
        shutil.copy2(ROOT / n, U / "code" / "canonical_dependencies" / n)
    for sub in ("tables", "oof", "data", "figures"):
        src = VOUT / sub
        if src.exists():
            for p in src.iterdir():
                if p.is_file() and p.suffix.lower() not in BAD_EXT:
                    (U / "results" / sub).mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, U / "results" / sub / p.name)
    shutil.copy2(VOUT / "tables" / "EXTERNAL_DATASET_COMPATIBILITY_MATRIX.csv", U / "results" / "tables") if \
        (VOUT / "tables" / "EXTERNAL_DATASET_COMPATIBILITY_MATRIX.csv").exists() else None


def excluded():
    rows = []
    for p in sorted(NATIVE_DIR.glob("*_ncct.npz")):
        rows.append({"path": f"native_isles24/{p.name}", "bytes": p.stat().st_size, "reason": "derived image array (Exp D input; regenerate with vD_fetch_ncct.py)"})
    rows += [
        {"path": "native_isles24/<sid>.npz, <sid>_dwi.npz", "bytes": "", "reason": "canonical native maps / DWI (s13, s23); not redistributed"},
        {"path": "extracted/branch3/01_DATASET_ISLES2024_PRIMARY", "bytes": "", "reason": "ISLES'24 pre-processed release (CC BY-NC-SA); public source"},
        {"path": "extracted/branch3/02_DATASET_EXTERNAL_TECHNICAL/ISLES2018_DTS", "bytes": "", "reason": "ISLES 2018 images (SMIR licence); public source"},
        {"path": "extracted/branch3/02_DATASET_EXTERNAL_TECHNICAL/dataset_CPAISD", "bytes": "", "reason": "CPAISD (not used: incompatible)"},
        {"path": "BMC_FEASIBILITY_VALIDITY_UPGRADE/00_BASELINE_SNAPSHOT", "bytes": sum(f.stat().st_size for f in (U / "00_BASELINE_SNAPSHOT").rglob("*") if f.is_file()),
         "reason": "read-only local snapshot of canonical results (17 MB); only its SHA256 manifest is zipped"},
        {"path": "atlases/ (nilearn MNI152, Harvard-Oxford, Juelich)", "bytes": "", "reason": "third-party atlases, fetched by nilearn"},
    ]
    pd.DataFrame(rows).to_csv(U / "EXCLUDED_INPUTS_MANIFEST.csv", index=False)


README = """# BMC_FEASIBILITY_VALIDITY_UPGRADE (2026-11-14)

Post hoc validity upgrade of the BMC MIDM feasibility manuscript (ISLES'24 CTP framework). Start with FINAL_VALIDITY_AUDIT.md.

| File | Content |
|---|---|
| Manuscript_BMC_MIDM_VALIDITY_REVISED.docx | content-updated manuscript (formatting unchanged); edits in MANUSCRIPT_CHANGE_LOG.md |
| FINAL_VALIDITY_AUDIT.md | phases 0-7, QC checklist, scientific verdict A-E |
| EXTERNAL_DATASET_COMPATIBILITY_MATRIX.csv | 9 datasets, status and reasons |
| EXPERIMENT_EXECUTION_LOG.csv | what ran, what was blocked or skipped |
| INTERNAL_VALIDITY_RESULTS.csv | experiments A-E |
| EXTERNAL_COMPONENT_BENCHMARK_RESULTS.csv | benchmark B1 (ISLES 2018) and blocked/skipped B2-B4 |
| PATIENT_LEVEL_PROVENANCE_AUDIT.csv | 149-patient centre provenance ledger |
| CLAIM_TO_EVIDENCE_FINAL_UPDATED.csv | 45 claims (33 previous + 12 new) |
| REMAINING_LIMITATIONS.md, DATA_ACCESS_REQUESTS.md | limitations; draft requests (not sent) |
| code/ | v*.py analyses, w*.py writers; canonical_dependencies/ = unchanged canonical modules they import |
| results/ | tables, lightweight OOF predictions, per-patient derived CSVs |
| supplementary/ | Additional file 5: Tables S21-S35 (.xlsx), Fig. S8 |
| 00_BASELINE_SNAPSHOT/ | read-only copy of canonical code/results/manuscript + SHA256SUMS_BASELINE.txt (local only) |

Re-run order (from analysis_v3/validity): vC_provenance, vB_native_verification, vA_nested_consistent run/eval, vA_within_centre,
vD_fetch_ncct, vD_registration, vD_models, vE_bootstrap_refit, vX1_isles2018_benchmark, w01..w06.
Canonical outputs (analysis_v3/outputs) are never written; all new outputs go to analysis_v3/outputs_validity.
"""

ZIPS = {
    "BMC_VALIDITY_1_manuscript_and_audit.zip": ["Manuscript_BMC_MIDM_VALIDITY_REVISED.docx", "FINAL_VALIDITY_AUDIT.md", "REMAINING_LIMITATIONS.md",
                                                 "DATA_ACCESS_REQUESTS.md", "MANUSCRIPT_CHANGE_LOG.md", "CLAIM_TO_EVIDENCE_FINAL_UPDATED.csv",
                                                 "EXTERNAL_DATASET_COMPATIBILITY_MATRIX.csv", "EXPERIMENT_EXECUTION_LOG.csv", "README.md"],
    "BMC_VALIDITY_2_statistical_and_external_results.zip": ["INTERNAL_VALIDITY_RESULTS.csv", "EXTERNAL_COMPONENT_BENCHMARK_RESULTS.csv",
                                                            "PATIENT_LEVEL_PROVENANCE_AUDIT.csv", "results", "README.md"],
    "BMC_VALIDITY_3_code_and_supplementary.zip": ["code", "supplementary", "EXCLUDED_INPUTS_MANIFEST.csv",
                                                  "00_BASELINE_SNAPSHOT/SHA256SUMS_BASELINE.txt", "SHA256SUMS.txt", "README.md"],
}


def main():
    copy_tree(); excluded()
    (U / "README.md").write_text(README, encoding="utf-8")
    files = sorted(p for p in U.rglob("*") if p.is_file() and "00_BASELINE_SNAPSHOT" not in p.parts and "ZIPS" not in p.parts
                   and p.name != "SHA256SUMS.txt")
    (U / "SHA256SUMS.txt").write_text("".join(f"{sha(p)}  {p.relative_to(U).as_posix()}\n" for p in files), encoding="utf-8")
    shutil.rmtree(Z, ignore_errors=True); Z.mkdir()
    rep = []
    for zn, items in ZIPS.items():
        with zipfile.ZipFile(Z / zn, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for it in items:
                p = U / it
                for f in ([p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file())):
                    assert f.suffix.lower() not in BAD_EXT, f
                    zf.write(f, f.relative_to(U).as_posix())
        with zipfile.ZipFile(Z / zn) as zf:
            bad = zf.testzip(); n = len(zf.namelist())
        mb = (Z / zn).stat().st_size / 1e6
        rep.append(f"{zn}: {n} files, {mb:.2f} MB, testzip={'OK' if bad is None else 'FAIL ' + bad}, under 8 MB={mb < 8}")
    (Z / "SHA256SUMS_ZIPS.txt").write_text("".join(f"{sha(p)}  {p.name}\n" for p in sorted(Z.glob("*.zip"))), encoding="utf-8")
    (Z / "ZIP_REPORT.txt").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep)); print(len(files), "files hashed")


if __name__ == "__main__":
    main()
