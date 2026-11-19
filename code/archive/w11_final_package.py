"""Final delivery: two folders of ZIPs.
  LIGHT_FOR_CHATGPT_REVIEW/     submission files, result tables, audit summaries, code and lightweight verification files
                                (de-identified OOF predictions, outer-fold manifests, inner-selection records, ISLES 2018
                                per-patient ledger, inferred centre labels); no fitted models, no images, no arrays
  FULL_HANDOVER_WITH_MODELS/    everything needed to hand the project over: submission files, all result tables, OOF
                                predictions, derived per-patient data, all code, the final fitted models and the audit trail
Image volumes, original datasets and arrays (.npy/.npz/.nii/.dcm) are never packaged (listed in EXCLUDED_INPUTS_MANIFEST).
Every ZIP is tested (testzip), kept under 8 MB and hashed (SHA256).
"""
import hashlib
import shutil
import zipfile
from datetime import date
from pathlib import Path

import w09_final_manuscript as W9
from v_common import ROOT

B3 = ROOT.parent
STG = B3 / "BMC_FINAL_SUBMISSION_STAGING"
OLD = B3 / "BMC_MIDM_FEASIBILITY_FINAL_AUDIT_PACKAGE"
VU = B3 / "BMC_FEASIBILITY_VALIDITY_UPGRADE"
REP = B3 / "BMC_TARGETED_REPAIR_2026-11-14"
OUT = ROOT / "outputs"
VOUT = ROOT / "outputs_validity"
VDATA_ = VOUT / "data"
DEL = B3 / "BMC_FINAL_DELIVERY_2026-11-14"
LIGHT, FULL = DEL / "LIGHT_FOR_CHATGPT_REVIEW", DEL / "FULL_HANDOVER_WITH_MODELS"
NEVER = {".npy", ".npz", ".nii", ".gz", ".dcm", ".pkl", ".7z", ".pyc"}
MAXMB = 8.0

FIGS = [("Figure1_framework", OLD / "05_FIGURES" / "Figure1_Fig1_framework"),
        ("Figure2_unit_recovery", OLD / "05_FIGURES" / "Figure2_Fig2_unit_recovery_validation"),
        ("Figure3_auc_forest", VOUT / "figures" / "final" / "Fig3_auc_forest"),
        ("Figure4_robustness", OLD / "05_FIGURES" / "Figure4_Fig8_robustness"),
        ("Figure5_post_treatment", OLD / "05_FIGURES" / "Figure5_Fig9_timeline"),
        ("Figure6_calibration", VOUT / "figures" / "final" / "Fig5_calibration")]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def files_in(d, pattern="*", recursive=False):
    it = d.rglob(pattern) if recursive else d.glob(pattern)
    return sorted(p for p in it if p.is_file() and p.suffix.lower() not in NEVER and "__pycache__" not in p.parts)


def submission_items(with_pdf_figs):
    it = [(STG / "Manuscript_BMC_MIDM_FINAL.docx", "01_manuscript/Manuscript_BMC_MIDM_FINAL.docx"),
          (STG / "Manuscript_BMC_MIDM_FINAL.pdf", "01_manuscript/Manuscript_BMC_MIDM_FINAL_preview.pdf"),
          (STG / "Cover_letter_BMC_MIDM_FINAL.docx", "01_manuscript/Cover_letter_BMC_MIDM_FINAL.docx"),
          (STG / "AUTHOR_TODO.md", "AUTHOR_TODO.md"),
          (STG / "MANUSCRIPT_REPAIR_CHANGE_LOG.md", "01_manuscript/MANUSCRIPT_REPAIR_CHANGE_LOG.md"),
          (REP / "SCIENTIFIC_REPAIR_REPORT.md", "SCIENTIFIC_REPAIR_REPORT.md")]
    for p in files_in(OLD / "06_SUPPLEMENTARY"):
        it.append((p, f"02_additional_files/{p.name}"))
    it += [(STG / "Additional_file_5_post_hoc_analyses_and_external_benchmark.xlsx",
            "02_additional_files/Additional_file_5_post_hoc_analyses_and_external_benchmark.xlsx"),
           (STG / "Additional_file_5_Figure_S8.pdf", "02_additional_files/Additional_file_5_Figure_S8.pdf"),
           (STG / "Additional_file_5_Figure_S8.png", "02_additional_files/Additional_file_5_Figure_S8.png")]
    for name, base in FIGS:
        it.append((base.with_suffix(".png"), f"03_figures/{name}.png"))
        if with_pdf_figs:
            it.append((base.with_suffix(".pdf"), f"03_figures/{name}.pdf"))
    return it


def audit_summary_items():
    """Current (repaired) audit documents only, so the light package carries no superseded wording."""
    it = [(REP / n, f"audit/{n}") for n in ("FINAL_CONTENT_AND_CODE_QA.md", "SCIENTIFIC_REPAIR_REPORT.md",
                                            "FINAL_VALIDITY_AUDIT_REPAIRED.md", "REMAINING_LIMITATIONS_REPAIRED.md",
                                            "CLAIM_TO_EVIDENCE_REPAIRED.csv")]
    it += [(REP / n, f"audit/{n}") for n in ("EXPERIMENT_EXECUTION_LOG_REPAIRED.csv", "INTERNAL_VALIDITY_RESULTS_REPAIRED.csv")]
    it += [(VU / n, f"audit/{n}") for n in ("EXTERNAL_DATASET_COMPATIBILITY_MATRIX.csv", "EXTERNAL_COMPONENT_BENCHMARK_RESULTS.csv",
                                            "DATA_ACCESS_REQUESTS.md")]
    return it


CONFIG_SNAPSHOT = OLD / "03_RESULTS_M1_M5" / "source_tabular_ISLES24" / "config_snapshot.json"
M1_FILES = ("cohort_129.csv", "cohort_flow_149.csv", "ctp_features_v3_149.csv", "ctp_features_native_149.csv",
            "native_acquisition_fingerprints.csv", "location_features.csv")


VERIFY_PATTERNS = ("oof_long*.csv", "fold_manifest*.csv", "inner_best_params*.csv", "inner_selection*.csv",
                   "pooled_probabilities*.csv", "train_test_auc*.csv")


def verification_items():
    """Lightweight, de-identified files for independent re-computation (public ISLES'24 / ISLES 2018 pseudonymous IDs only)."""
    it = []
    for pat in VERIFY_PATTERNS:
        it += [(p, f"verification/primary_analysis/oof/{p.name}") for p in files_in(OUT / "oof", pat)]
        it += [(p, f"verification/post_hoc_analyses/oof/{p.name}") for p in files_in(VOUT / "oof", pat)]
    it.append((OUT / "data" / "inferred_site.csv", "verification/centres/inferred_site.csv"))
    it.append((VDATA_ / "patient_provenance_ledger_extended.csv", "verification/centres/patient_provenance_ledger_extended.csv"))
    it.append((VU / "PATIENT_LEVEL_PROVENANCE_AUDIT.csv", "verification/centres/PATIENT_LEVEL_PROVENANCE_AUDIT.csv"))
    it += [(OUT / "data" / n, f"verification/m1_data/{n}") for n in M1_FILES]
    it += [(VDATA_ / "vB_native_per_subject.csv", "verification/m1_data/vB_native_per_subject.csv"),
           (CONFIG_SNAPSHOT, "verification/m1_data/config_snapshot.json")]
    for n in ("vX1_isles2018_per_patient.csv", "vX1_isles2018_per_slab.csv", "vX1b_isles2018_per_patient_ledger.csv",
              "vX1b_slab_overlap_per_patient.csv"):
        it.append((VDATA_ / n, f"verification/isles2018_benchmark/{n}"))
    it += [(REP / "VERIFICATION_FILES_README.md", "verification/README.md"),
           (REP / "MODEL_CODE_GLOSSARY.csv", "verification/MODEL_CODE_GLOSSARY.csv")]
    return it


def code_items(full):
    it = [(p, f"code/analysis_v3/{p.name}") for p in files_in(ROOT, "*.py")]
    it += [(ROOT / n, f"code/analysis_v3/{n}") for n in ("README.md", "DATA_NOTICE.md", "PLAN_v4_prespecified.md",
                                                          "SAP_supplementary_analysis_plan.md") if (ROOT / n).exists()]
    req = ROOT / "requirements.txt"
    assert req.exists(), "analysis_v3/requirements.txt is required"
    it.append((req, "code/analysis_v3/requirements.txt"))
    it += [(p, f"code/analysis_v3/validity/{p.name}") for p in files_in(ROOT / "validity", "*.py")]
    if full:
        it += [(p, f"code/analysis_v3/audit_final/{p.name}") for p in files_in(ROOT / "audit_final", "*.py")]
    return it


def results_items(full):
    it = [(p, f"results/primary_analysis/tables/{p.name}") for p in files_in(OUT / "tables")]
    it += [(p, f"results/post_hoc_analyses/tables/{p.name}") for p in files_in(VOUT / "tables")]
    if full:
        for sub in ("oof", "data", "figures"):
            it += [(p, f"results/primary_analysis/{sub}/{p.name}") for p in files_in(OUT / sub)]
            it += [(p, f"results/post_hoc_analyses/{sub}/{p.relative_to(VOUT / sub).as_posix()}")
                   for p in files_in(VOUT / sub, recursive=True)]
        it.append((VU / "PATIENT_LEVEL_PROVENANCE_AUDIT.csv", "results/post_hoc_analyses/data/PATIENT_LEVEL_PROVENANCE_AUDIT.csv"))
        it.append((CONFIG_SNAPSHOT, "results/primary_analysis/data/config_snapshot.json"))
    return it


def model_items():
    md = VOUT / "models"
    it = [(p, f"models/{p.name}") for p in sorted(md.iterdir()) if p.is_file()]
    it += [(ROOT / "validity" / "apply_frozen_models.py", "models/apply_frozen_models.py"),
           (ROOT / "validity" / "w08_freeze_models.py", "models/w08_freeze_models.py"),
           (STG / "MODELS_README.md", "models/README.md")]
    return it


def full_audit_items():
    it = [(REP / n, f"audit/targeted_repair_2026-11-14/{n}") for n in (
        "FINAL_CONTENT_AND_CODE_QA.md", "SCIENTIFIC_REPAIR_REPORT.md", "FINAL_VALIDITY_AUDIT_REPAIRED.md",
        "REMAINING_LIMITATIONS_REPAIRED.md", "CLAIM_TO_EVIDENCE_REPAIRED.csv", "VERIFICATION_FILES_README.md",
        "MODEL_CODE_GLOSSARY.csv", "EXPERIMENT_EXECUTION_LOG_REPAIRED.csv", "INTERNAL_VALIDITY_RESULTS_REPAIRED.csv")]
    it.append((REP / "CLAIM_TO_EVIDENCE_HISTORICAL_NOTES.csv",
               "audit/historical_records/CLAIM_TO_EVIDENCE_HISTORICAL_NOTES.csv"))
    it.append((STG / "_build" / "Manuscript_BMC_MIDM_FINAL_before_repair.docx",
               "audit/earlier_manuscript_versions/Manuscript_BMC_MIDM_FINAL_before_targeted_repair.docx"))
    it.append((STG / "MANUSCRIPT_CHANGE_LOG_FINAL.md",
               "audit/earlier_manuscript_versions/MANUSCRIPT_CHANGE_LOG_first_final_pass_SUPERSEDED.md"))
    it += [(VU / n, f"audit/validity_upgrade_superseded_wording/{n}") for n in (
        "FINAL_VALIDITY_AUDIT.md", "REMAINING_LIMITATIONS.md", "DATA_ACCESS_REQUESTS.md", "MANUSCRIPT_CHANGE_LOG.md",
        "CLAIM_TO_EVIDENCE_FINAL_UPDATED.csv", "EXPERIMENT_EXECUTION_LOG.csv", "EXTERNAL_DATASET_COMPATIBILITY_MATRIX.csv",
        "INTERNAL_VALIDITY_RESULTS.csv", "EXTERNAL_COMPONENT_BENCHMARK_RESULTS.csv", "PATIENT_LEVEL_PROVENANCE_AUDIT.csv",
        "EXCLUDED_INPUTS_MANIFEST.csv", "Manuscript_BMC_MIDM_VALIDITY_REVISED.docx")]
    it.append((VU / "00_BASELINE_SNAPSHOT" / "SHA256SUMS_BASELINE.txt", "audit/validity_upgrade_superseded_wording/SHA256SUMS_BASELINE.txt"))
    it += [(p, f"audit/earlier_audit_2026-11-13/{p.name}") for p in files_in(OLD / "07_AUDIT_AND_PROVENANCE")]
    it += [(p, f"audit/earlier_audit_2026-11-13/numerical_evidence/{p.name}") for p in files_in(OLD / "02_NUMERICAL_EVIDENCE")]
    it += [(OLD / "01_MANUSCRIPT" / n, f"audit/earlier_manuscript_versions/{n}") for n in
           ("Manuscript_BMC_MIDM_ORIGINAL_2026-11-12.docx", "Manuscript_BMC_MIDM_SCIENTIFIC_REVISED.docx")]
    it += [(ROOT / n, f"audit/internal_reviews/{n}") for n in ("BAO_CAO_AUDIT_NHANH3.md", "REVIEW_KIEN_TRUC_BAI.md") if (ROOT / n).exists()]
    return it


def write_texts():
    lines = ["# SUPERSEDED: change log of the first final pass (2026-11-14)", "",
             "> Historical record only. The abstract and several sentences quoted below were revised by the later targeted and "
             "final content-only repairs; the current text is described in MANUSCRIPT_REPAIR_CHANGE_LOG.md.", "",
             "Source: Manuscript_BMC_MIDM_VALIDITY_REVISED.docx. Script: code/analysis_v3/validity/w09_final_manuscript.py.",
             "No reported number was changed. Word formatting kept; Figures 3 and 6 redrawn from the same tables with descriptive labels.", "",
             "## Abstract (rewritten to 349 words; adds the bootstrap-refit and ISLES 2018 results)", ""]
    for i, (lab, body) in W9.ABSTRACT.items():
        lines.append(f"- **{lab}** {body.strip()}")
    lines += ["", "## Text replacements (old → new)", ""]
    for i, subs in W9.SUB.items():
        for old, new in subs:
            lines.append(f"- ¶{i}: “{old}” → “{new}”")
    lines += ["", "## Paragraphs rewritten in full", ""]
    for i, (start, new) in W9.FULL.items():
        lines.append(f"- ¶{i} (started “{start}…”): {new}")
    lines += ["", "## Table 2 row labels", ""] + [f"- {a} → {b}" for a, b in W9.TABLE_ROWS.items()]
    lines += ["", "## Placeholders for the authors (highlighted yellow)", "", "See AUTHOR_TODO.md.", "",
              "A second, targeted scientific repair was applied afterwards; see MANUSCRIPT_REPAIR_CHANGE_LOG.md."]
    (STG / "MANUSCRIPT_CHANGE_LOG_FINAL.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    import w13_targeted_repair as W13
    nums = W13.dedup_numbers()
    from docx import Document
    dfin = Document(STG / "Manuscript_BMC_MIDM_FINAL.docx")
    nabs = sum(len("".join(r.text for r in p.runs[1:]).split()) for p in dfin.paragraphs[6:10])
    rl = ["# Manuscript change log: targeted scientific repair and final content-only repair (2026-11-14)", "",
          "All edits relative to the first final version (kept in FULL_4 as Manuscript_BMC_MIDM_FINAL_before_targeted_repair.docx). "
          "Script: code/analysis_v3/validity/w13_targeted_repair.py. Each edit is anchored on unique text and made inside "
          "the existing run (formatting unchanged). New numbers come from outputs_validity/tables/vX1b_*.csv and vC2_*.csv.", "",
          f"## Abstract: Results and Conclusions as now in the manuscript (whole abstract {nabs} words)", ""]
    rl += [f"- **{k}** {v}" for k, v in W13.ABSTRACT.items()]
    rl += ["", "## Text edits (old → new)", ""]
    for old, new in W13.EDITS:
        rl.append(f"- “{old}” → “{new.format(**nums) if '{n_dup}' in new else new}”")
    rl += ["", "## Table 3 (go/no-go)", ""]
    rl += [f"- “{a}” → “{b}”" for a, b in W13.TABLE3.items()]
    rl += [f"- row “{a}”: “No-go” → “{b}”" for a, b in W13.TABLE3_ROW.items()]
    rl += ["", "## Author placeholders", "",
           "- Unchanged administrative declarations only (AUTHOR_TODO.md); the published ISLES'24 Table 1 count (100/49) is "
           "stated as confirmed, so no placeholder is needed for it."]
    (STG / "MANUSCRIPT_REPAIR_CHANGE_LOG.md").write_text("\n".join(rl) + "\n", encoding="utf-8")

    (STG / "MODELS_README.md").write_text(
        "# Final fitted models (research use only)\n\n"
        "Fitted on all 129 analysed ISLES'24 patients by `w08_freeze_models.py`; the specifications are those of the cross-validated "
        "models in the manuscript. All performance figures in the paper come from nested cross-validation, not from these fits.\n\n"
        "| File | Model |\n|---|---|\n"
        "| clinical_gbm_5seed.joblib | gradient boosting on 22 clinical predictors, locked configuration; five fits (seeds 42, 100, 2024, 777, 999), prediction = mean |\n"
        "| ctp_elastic_net.joblib | elastic-net logistic regression on 53 CTP features (recovered units); C and l1_ratio tuned by 5-fold CV |\n"
        "| parsimonious_logistic.joblib | logistic regression on age, admission NIHSS, premorbid mRS, glucose |\n"
        "| model_card.json | training data, inputs, fusion rule, cross-validated performance, warnings, software versions, SHA256 |\n\n"
        "Fusion rule: p = 0.5 × p(clinical GBM) + 0.5 × p(CTP elastic net).\n\n"
        "Apply to a new cohort: `python apply_frozen_models.py . new_cohort.csv scored.csv` (column lists in features_*.txt).\n\n"
        "Warnings: the clinical GBM is overconfident (cross-validated calibration slope 0.58) and reaches an apparent AUC of 1.00 on its "
        "training data; recalibrate before any use. CTP inputs must be in physical units with the same clip limits; on ISLES 2018 the maps "
        "had to be rescaled first. Use the scikit-learn version recorded in model_card.json. Trained on CC BY-NC-SA 4.0 data: non-commercial use.\n",
        encoding="utf-8")


def build_zip(zpath, items, allow_models):
    seen = set()
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for src, arc in items:
            assert src.exists(), src
            assert src.suffix.lower() not in NEVER, src
            assert allow_models or src.suffix.lower() != ".joblib", src
            assert arc not in seen, arc
            seen.add(arc)
            zf.write(src, arc)
    with zipfile.ZipFile(zpath) as zf:
        bad, n = zf.testzip(), len(zf.namelist())
    mb = zpath.stat().st_size / 1e6
    assert bad is None and mb < MAXMB, (zpath.name, bad, mb)
    return f"{zpath.name}: {n} files, {mb:.2f} MB, testzip=OK, under {MAXMB:g} MB=True"


README_VI = """# Bàn giao cuối – BMC MIDM feasibility (14/11/2026)

## Hai thư mục

| Thư mục | Dùng cho | Có mô hình? |
|---|---|---|
| LIGHT_FOR_CHATGPT_REVIEW/ | gửi ChatGPT (hoặc reviewer) kiểm tra: bản thảo, file bổ sung, bảng kết quả, audit (bản đã sửa), code, và thư mục verification/ (OOF predictions, fold manifest, inner-selection, ledger ISLES 2018 theo bệnh nhân, nhãn trung tâm suy luận) | Không |
| FULL_HANDOVER_WITH_MODELS/ | bàn giao toàn bộ dự án: như bản nhẹ + mô hình đã fit, toàn bộ dữ liệu dẫn xuất theo bệnh nhân, toàn bộ audit trail (kể cả bản trước khi sửa) | Có |

Tên ZIP bản nhẹ: LIGHT_1_submission_manuscript_FINAL.zip, LIGHT_2_results_and_audit_summary_FINAL.zip, LIGHT_3_code_FINAL.zip.

## Kết quả canonical (không đổi qua mọi đợt sửa)
N = 129 (44 kết cục xấu); AUC lâm sàng 0.763; AUC fusion 0.774; ΔAUC +0.011; nested GBM 0.727; fully nested 0.698 / 0.752 / ΔAUC +0.054;
ISLES 2018 sau loại trùng: Dice 0.206, độ nhạy 0.152 (benchmark kỹ thuật, không phải kiểm định tiên lượng).

## Các đợt sửa và QA (14/11/2026)
- FINAL_CONTENT_AND_CODE_QA.md: sửa ledger (CL-09, CL-29, CL-36 và các ghi chú lỗi thời), rà soát bản thảo, kiểm tra code (biên dịch, import, đường dẫn, OOF), README.
- SCIENTIFIC_REPAIR_REPORT.md: Phần A (sửa nội dung cuối) và Phần B (sửa có mục tiêu).
Mỗi claim có cột reproducibility_from_LIGHT trong audit/CLAIM_TO_EVIDENCE_REPAIRED.csv (VERIFIED = đã đối chiếu với file có trong gói; VERIFIED_WITH_LIMITATION = đã đối chiếu nhưng dựa trên suy luận/xấp xỉ có nêu hạn chế).

## Nộp bài
Các file nộp nằm trong ZIP số 1 của mỗi bộ (giống nhau):
- 01_manuscript/Manuscript_BMC_MIDM_FINAL.docx – bản thảo cuối (abstract ≤350 từ kể cả nhãn; Additional file 5 = Tables S21–S42)
- 01_manuscript/Cover_letter_BMC_MIDM_FINAL.docx
- 02_additional_files/ – Additional files 1–5
- 03_figures/ – Figures 1–6
- AUTHOR_TODO.md – các mục tác giả phải điền (tô vàng trong bản thảo)

## Ghi chú quan trọng
- Không có kiểm định tiên lượng ngoài (không có cohort độc lập có CTP + mRS 90 ngày).
- Mô hình trong FULL_3 chỉ dùng cho nghiên cứu/kiểm định ngoài sau này; mọi con số hiệu năng trong bài là từ nested CV.
- Dữ liệu ảnh gốc, .npy/.npz/.nii/.dcm không được đóng gói (xem audit/validity_upgrade_superseded_wording/EXCLUDED_INPUTS_MANIFEST.csv trong FULL_4).
- Kết quả thống kê tính lại được từ LIGHT (OOF, bảng theo bệnh nhân); các đại lượng dẫn xuất từ ảnh cần dữ liệu ảnh công khai gốc.
- Các mục hành chính (tác giả, funding, ethics, CRediT, competing interests, repository/DOI, bài đi kèm) để tác giả điền: AUTHOR_TODO.md.
- Kiểm tra toàn vẹn: SHA256SUMS.txt và ZIP_REPORT.txt trong mỗi thư mục.
"""

README_EN = """# Final delivery: BMC MIDM feasibility manuscript (2026-11-14)

## Contents

| Folder / ZIP | Content |
|---|---|
| LIGHT_FOR_CHATGPT_REVIEW/LIGHT_1_submission_manuscript_FINAL.zip | manuscript (DOCX + PDF preview), cover letter, Additional files 1–5 (Additional file 5 = Tables S21–S42 and Figure S8), Figures 1–6, change log, scientific repair report, AUTHOR_TODO.md |
| LIGHT_FOR_CHATGPT_REVIEW/LIGHT_2_results_and_audit_summary_FINAL.zip | result tables (primary and post hoc), audit/ (final QA report, evidence ledger with 54 claims, repaired audit, limitations), verification/ (OOF predictions, outer-fold manifests, inner-selection records, cohort and M1 patient-level data, inferred centres, ISLES 2018 per-patient ledger, model-code glossary; see verification/README.md) |
| LIGHT_FOR_CHATGPT_REVIEW/LIGHT_3_code_FINAL.zip | analysis code (s01–s30, validity/), README.md, requirements.txt |
| FULL_HANDOVER_WITH_MODELS/ | the same submission files plus fitted models, all derived data and the full audit trail, including superseded versions and historical ledger notes |

No fitted models, checkpoints, arrays or images are in the light ZIPs.

## Canonical results (unchanged by all later passes)

N = 129 (44 poor outcomes); primary clinical AUC 0.763, fusion 0.774, ΔAUC +0.011 (95% CI −0.039 to +0.068); GBM-only
nested tuning 0.727; post hoc fully nested selection: clinical 0.698, fusion 0.752, ΔAUC +0.054 (95% CI −0.006 to +0.121);
ISLES 2018 technical benchmark, de-duplicated: Dice 0.206, sensitivity 0.152.

## Reproducibility

Statistical results can be recomputed from verification/ and the result tables (see analysis_v3/README.md inside
LIGHT_3 for the exact procedure and `validity/qa_code_checks.py`). Image-derived quantities (unit recovery, perfusion
features, voxel comparisons, registration, ISLES 2018 benchmark) require the original public imaging datasets.
No independent external prognostic validation was possible. Benchmarks not executed: UniToBrain, Johns Hopkins head-CT
masks, CPAISD, AISD (reasons in the compatibility matrix).

## Evidence ledger

VERIFIED = checked against a cited file present in the package; VERIFIED_WITH_LIMITATION = checked, but resting on an
inference, approximation or estimate whose limitation is stated; SOURCE_MISSING = author-completed declarations.

## Author-owned items

Author details, funding, ethics waiver, CRediT, competing interests, repository URL/DOI and companion-study status are
left for the authors (AUTHOR_TODO.md; highlighted in the manuscript).
"""


def main():
    write_texts()
    shutil.rmtree(DEL, ignore_errors=True)
    LIGHT.mkdir(parents=True); FULL.mkdir(parents=True)
    (DEL / "README_VI.md").write_text(README_VI, encoding="utf-8")
    (DEL / "README.md").write_text(README_EN, encoding="utf-8")
    readme = [(DEL / "README.md", "README.md")]

    plans = {
        LIGHT: [("LIGHT_1_submission_manuscript_FINAL.zip", submission_items(False) + readme, False),
                ("LIGHT_2_results_and_audit_summary_FINAL.zip", results_items(False) + audit_summary_items()
                 + verification_items() + readme, False),
                ("LIGHT_3_code_FINAL.zip", code_items(False) + readme, False)],
        FULL: [("FULL_1_submission_manuscript.zip", submission_items(True) + readme, False),
               ("FULL_2_results_tables_oof_derived_data.zip", results_items(True) + readme, False),
               ("FULL_3_code_and_final_models.zip", code_items(True) + model_items() + readme, True),
               ("FULL_4_audit_trail_and_provenance.zip", full_audit_items() + readme, False)],
    }
    for folder, zips in plans.items():
        rep = [build_zip(folder / zn, items, allow) for zn, items, allow in zips]
        (folder / "ZIP_REPORT.txt").write_text("\n".join(rep) + f"\nbuilt {date.today()}\n", encoding="utf-8")
        (folder / "SHA256SUMS.txt").write_text("".join(f"{sha(p)}  {p.name}\n" for p in sorted(folder.glob("*.zip"))), encoding="utf-8")
        print(folder.name); print("\n".join("  " + r for r in rep))


if __name__ == "__main__":
    main()
