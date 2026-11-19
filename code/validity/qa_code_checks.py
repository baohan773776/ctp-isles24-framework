"""Lightweight code-quality and reproducibility checks (no imaging volumes, no model training).

Checks
  1. py_compile of every .py under analysis_v3/ (top level, validity/, audit_final/) and of the historical copy in
     FINAL_PACKAGE_BMC_MIDM/ (reported separately).
  2. Static import scan (ast): every imported module is stdlib, a local script, or a third-party package that is
     installed and declared in analysis_v3/requirements.txt.
  3. Hard-coded drive-letter or home-directory paths in code (comments and regex literals excluded by inspection).
  4. Schema of every OOF and fold-manifest CSV (primary and post hoc): required columns, y in {0,1}, p in [0,1], one
     prediction per subject x seed x model, y constant per subject and equal to cohort_129.poor (y = 1 = mRS 3-6).
  5. Fold consistency: the fold of every OOF row equals the fold in the manifest of the same run.
  6. Reproduction from stored predictions: seed-mean AUC and paired ΔAUC of the primary and fully nested comparisons,
     compared with the exported result tables; ISLES 2018 de-duplicated Dice and sensitivity from the per-patient ledger.
  7. Canonical outputs byte-identical to the baseline snapshot (SHA256).
  8. Post hoc scripts (validity/) never write into the canonical output folders (static scan).
Output: outputs_validity/tables/qa_code_checks.json (and a printed summary). Nothing is modified.
"""
import ast
import hashlib
import importlib.util
import json
import py_compile
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from v_common import VTAB, VDATA  # noqa: E402
from config import OUT, SEEDS  # noqa: E402

PIP = {"sklearn": "scikit-learn", "docx": "python-docx", "SimpleITK": "SimpleITK", "yaml": "pyyaml", "PIL": "pillow"}
RES = {}


def py_files():
    main = sorted(p for d in (ROOT, HERE, ROOT / "audit_final") for p in d.glob("*.py"))
    hist = sorted((ROOT / "FINAL_PACKAGE_BMC_MIDM").rglob("*.py")) if (ROOT / "FINAL_PACKAGE_BMC_MIDM").exists() else []
    return main, hist


def check_compile(files):
    bad = {}
    for f in files:
        try:
            py_compile.compile(str(f), doraise=True)
        except py_compile.PyCompileError as e:
            bad[str(f.relative_to(ROOT))] = str(e)[:200]
    return bad


def check_imports(files):
    local = {p.stem for d in (ROOT, HERE, ROOT / "audit_final") for p in d.glob("*.py")}
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    declared = {ln.split("==")[0].split("#")[0].strip().lower() for ln in req.splitlines() if ln.strip() and not ln.startswith("#")}
    third, missing_local, not_installed = {}, {}, set()
    for f in files:
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods = [node.module.split(".")[0]]
            for m in mods:
                if m in sys.stdlib_module_names or m in local:
                    continue
                if m in ("s30_package",):        # optional local modules referenced only by historical scripts
                    missing_local.setdefault(m, []).append(f.name)
                    continue
                third.setdefault(m, set()).add(f.name)
                if importlib.util.find_spec(m) is None:
                    not_installed.add(m)
    undeclared = sorted(m for m in third if PIP.get(m, m).lower() not in declared)
    return {"third_party": {m: sorted(v) for m, v in sorted(third.items())}, "undeclared_in_requirements": undeclared,
            "not_installed": sorted(not_installed), "missing_local_modules": missing_local}


def check_paths(files):
    pat = re.compile(r"""["'][A-Za-z]:[\\/]|["']/(home|Users)/""")
    hits = []
    for f in files:
        for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(ln) and "re.search" not in ln and "re.compile" not in ln:
                hits.append(f"{f.relative_to(ROOT)}:{i}: {ln.strip()[:120]}")
    return hits


def oof_runs():
    runs = []
    for d, tag in ((OUT / "oof", "primary"), (ROOT / "outputs_validity" / "oof", "post_hoc")):
        for f in sorted(d.glob("oof_long*.csv")):
            suf = f.stem[len("oof_long"):]
            man = d / f"fold_manifest{suf}.csv"
            if suf == "_all":                    # concatenation of primary-run models; shares the primary manifest
                man = d / "fold_manifest.csv"
            runs.append((tag, f, man if man.exists() else None))
    return runs


def check_oof(cohort):
    rows = []
    poor = cohort.set_index("subject_id").poor.astype(int)
    for tag, f, man in oof_runs():
        o = pd.read_csv(f)
        r = {"run": f"{tag}/{f.name}", "rows": len(o)}
        need = {"subject_id", "seed", "fold", "model", "y", "p_poor"}
        r["columns_ok"] = need <= set(o.columns)
        if not r["columns_ok"]:
            rows.append(r); continue
        r["y_binary"] = bool(o.y.isin([0, 1]).all())
        r["p_in_0_1"] = bool(o.p_poor.between(0, 1).all() and o.p_poor.notna().all())
        r["unique_subject_seed_model"] = not o.duplicated(["subject_id", "seed", "model"]).any()
        r["seeds"] = sorted(o.seed.unique().tolist())
        r["y_constant_per_subject"] = bool((o.groupby("subject_id").y.nunique() == 1).all())
        yy = o.drop_duplicates("subject_id").set_index("subject_id").y
        r["y_equals_cohort_poor"] = bool((yy == poor.reindex(yy.index)).all())
        r["n_subjects"] = int(o.subject_id.nunique())
        if man is not None:
            m = pd.read_csv(man)
            mm = o.merge(m, on=["seed", "subject_id"], how="left", suffixes=("", "_man"))
            r["manifest"] = man.name
            r["fold_matches_manifest"] = bool((mm.fold == mm.fold_man).all())
            r["each_subject_once_per_seed_in_manifest"] = not m.duplicated(["seed", "subject_id"]).any()
        else:
            r["manifest"] = None
        rows.append(r)
    return rows


def seed_auc(o, model):
    g = o[o.model == model]
    return float(np.mean([roc_auc_score(s.y, s.p_poor) for _, s in g.groupby("seed")]))


def check_reproduction():
    out = {}
    o = pd.read_csv(OUT / "oof" / "oof_long.csv")
    perf = pd.read_csv(OUT / "tables" / "performance_all_models.csv").set_index("model")
    for m in ("P1_clin_GBM", "F_late_P1_E", "E_CTP_all"):
        out[f"primary {m}"] = {"recomputed": round(seed_auc(o, m), 4), "table": round(float(perf.loc[m, "auc_seed_mean"]), 4)}
    out["primary dAUC F_late_P1_E - P1"] = {"recomputed": round(seed_auc(o, "F_late_P1_E") - seed_auc(o, "P1_clin_GBM"), 4)}
    v = pd.read_csv(ROOT / "outputs_validity" / "oof" / "oof_long_vA.csv")
    vp = pd.read_csv(VTAB / "vA_performance.csv")
    vp = vp[vp.analysis.str.contains("full cohort", case=False)].set_index("model")
    for m in ("A_clin", "A_late_rec"):
        out[f"fully nested {m}"] = {"recomputed": round(seed_auc(v, m), 4), "table": round(float(vp.loc[m, "auc_seed_mean"]), 4)}
    out["fully nested dAUC A_late_rec - A_clin"] = {"recomputed": round(seed_auc(v, "A_late_rec") - seed_auc(v, "A_clin"), 4)}
    L = pd.read_csv(VDATA / "vX1b_isles2018_per_patient_ledger.csv")
    L = L[(L.scaling == "s03_harmonised") & (L.variant == "dedup_adjacency_keepA (primary)")]
    out["ISLES 2018 de-duplicated Dice (mean of patients)"] = {"recomputed": round(float(L.dice.mean()), 4), "n": int(len(L))}
    out["ISLES 2018 de-duplicated sensitivity"] = {"recomputed": round(float(L.sensitivity.mean()), 4)}
    return out


def smoke_tests():
    """Function-level checks of shared helpers, without imaging data or training."""
    import features as F
    from config import CLINICAL_22
    from stats_utils import auc_fast
    from v_common import boot_indices
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 200); p = rng.random(200) + 0.3 * y
    out = {"auc_fast_equals_sklearn": bool(abs(auc_fast(y, p) - roc_auc_score(y, p)) < 1e-12),
           "boot_indices_both_classes": all(0 < y[b].sum() < len(b) for b in boot_indices(y, n_boot=50)),
           "n_ctp_features": len(F.CTP_ALL), "n_clinical": len(CLINICAL_22)}
    o = pd.read_csv(OUT / "oof" / "oof_long.csv").pivot_table(index=["subject_id", "seed"], columns="model", values="p_poor")
    out["late_fusion_rule_0.5_0.5_holds"] = bool(np.allclose(o.F_late_P1_E, 0.5 * o.P1_clin_GBM + 0.5 * o.E_CTP_all))
    v = pd.read_csv(ROOT / "outputs_validity" / "oof" / "oof_long_vA.csv").pivot_table(
        index=["subject_id", "seed"], columns="model", values="p_poor")
    out["fully_nested_fusion_rule_holds"] = bool(np.allclose(v.A_late_rec, 0.5 * v.A_clin + 0.5 * v.A_ctp_rec))
    m1 = pd.read_csv(OUT / "oof" / "fold_manifest.csv"); m2 = pd.read_csv(ROOT / "outputs_validity" / "oof" / "fold_manifest_vA.csv")
    out["fully_nested_uses_primary_folds"] = bool(m1.sort_values(["seed", "subject_id"]).reset_index(drop=True)
                                                  .equals(m2.sort_values(["seed", "subject_id"]).reset_index(drop=True)))
    sel = pd.read_csv(ROOT / "outputs_validity" / "oof" / "inner_selection_vA.csv")
    out["inner_selection_one_choice_per_fold_model"] = not sel.duplicated(["seed", "fold", "model"]).any()
    out["inner_selection_rows"] = int(len(sel))
    return out


def check_canonical():
    base = ROOT.parent / "BMC_FEASIBILITY_VALIDITY_UPGRADE" / "00_BASELINE_SNAPSHOT" / "SHA256SUMS_BASELINE.txt"
    ok = bad = 0
    for ln in base.read_text(encoding="utf-8").splitlines():
        h, rel = ln.split("  ", 1)
        if "outputs/" not in rel:
            continue
        p = ROOT / "outputs" / rel.split("outputs/", 1)[1]
        same = p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == h
        ok += same; bad += not same
    return {"identical": ok, "differing_or_missing": bad}


def check_writes():
    pat = re.compile(r"(to_csv|savefig|write_text|write_bytes|json\.dump|\.save)\(")
    canon = re.compile(r"\b(TAB|DATA|OOF|FIG|OUT)\s*/")
    hits = []
    for f in sorted(HERE.glob("*.py")):
        for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(ln) and canon.search(ln):
                hits.append(f"{f.name}:{i}: {ln.strip()[:120]}")
    return hits


def main():
    main_files, hist = py_files()
    RES["files_checked"] = len(main_files)
    RES["compile_errors"] = check_compile(main_files)
    RES["compile_errors_historical_copy"] = check_compile(hist)
    RES["historical_copy_files"] = len(hist)
    RES["imports"] = check_imports(main_files)
    RES["hardcoded_paths"] = check_paths(main_files)
    cohort = pd.read_csv(OUT / "data" / "cohort_129.csv")
    RES["cohort"] = {"n": int(len(cohort)), "poor": int(cohort.poor.sum()),
                     "poor_definition_ok": bool(((cohort.mrs90 >= 3).astype(int) == cohort.poor).all())}
    RES["oof_schema"] = check_oof(cohort)
    RES["reproduction"] = check_reproduction()
    RES["smoke_tests"] = smoke_tests()
    RES["canonical_outputs"] = check_canonical()
    RES["validity_writes_to_canonical_folders"] = check_writes()
    (VTAB / "qa_code_checks.json").write_text(json.dumps(RES, indent=2, default=str), encoding="utf-8")
    s = RES
    print("files:", s["files_checked"], "| compile errors:", len(s["compile_errors"]), "| historical copy:",
          s["historical_copy_files"], "files,", len(s["compile_errors_historical_copy"]), "errors")
    print("third-party imports:", list(s["imports"]["third_party"]))
    print("undeclared:", s["imports"]["undeclared_in_requirements"], "| not installed:", s["imports"]["not_installed"],
          "| missing local:", s["imports"]["missing_local_modules"])
    print("hard-coded paths:", s["hardcoded_paths"])
    print("cohort:", s["cohort"])
    bad = [r for r in s["oof_schema"] if not all(v for k, v in r.items() if isinstance(v, bool))]
    print("OOF runs:", len(s["oof_schema"]), "| runs failing a check:", [(r["run"], {k: v for k, v in r.items() if v is False}) for r in bad])
    print("runs without manifest:", [r["run"] for r in s["oof_schema"] if r.get("manifest") is None])
    print("reproduction:", json.dumps(s["reproduction"], indent=1))
    print("smoke tests:", s["smoke_tests"])
    print("canonical:", s["canonical_outputs"])
    print("validity writes into canonical folders:", s["validity_writes_to_canonical_folders"])


if __name__ == "__main__":
    main()
