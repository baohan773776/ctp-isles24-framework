"""Assembles the final package: submission files, code-repository bundle and internal (not-for-submission) files.
Run after s11 and s12.

HISTORICAL (2026-11-14): assembles a superseded package (FINAL_PACKAGE_BMC_MIDM). The current delivery is built by
validity/w11_final_package.py (see README.md)."""
import os as _os
import sys as _sys
if _os.environ.get("BRANCH3_ALLOW_HISTORICAL") != "1":
    _sys.exit("Historical script (superseded package); set BRANCH3_ALLOW_HISTORICAL=1 to run it anyway.")
import json
import re
import shutil
import pandas as pd
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import Pt, Cm
from config import ROOT, OUT, FIG, TAB, DATA

PKG = ROOT / "FINAL_PACKAGE_BMC_MIDM"
SUB, REPO, INT = PKG / "01_Submission", PKG / "02_Code_repository", PKG / "03_Internal_not_for_submission"
if PKG.exists():
    shutil.rmtree(PKG)
for p in [SUB / "Figures", SUB / "Additional_files", REPO / "results" / "tables", REPO / "results" / "oof",
          REPO / "results" / "derived", INT]:
    p.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------ 01 submission
shutil.copy(OUT / "Manuscript_BMC_MIDM.docx", SUB / "Manuscript_BMC_MIDM.docx")
FIGS = ["Fig1_framework", "Fig2_unit_recovery_validation", "Fig3_auc_forest", "Fig8_robustness", "Fig9_timeline",
        "Fig5_calibration"]
for i, f in enumerate(FIGS, 1):
    for ext in ("pdf", "png"):
        shutil.copy(FIG / f"{f}.{ext}", SUB / "Figures" / f"Figure{i}.{ext}")
for f in ["Additional_file_1_TRIPOD_AI_checklist.docx", "Additional_file_2_supplementary_tables.xlsx",
          "Additional_file_3_supplementary_analysis_plan.docx", "Additional_file_4_supplementary_methods_figures.docx"]:
    shutil.copy(OUT / f, SUB / "Additional_files" / f)

TITLE = ("A reproducible framework for evaluating the incremental prognostic value of CT perfusion after thrombectomy: "
         "feasibility study on the public ISLES'24 dataset and design parameters for a definitive study")
d = Document(); st = d.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(11)
for s in d.sections:
    s.left_margin = s.right_margin = Cm(2.5)


def para(text):
    p = d.add_paragraph()
    for part in re.split(r"(\[[A-Z][^\]]*\])", text):
        if part:
            r = p.add_run(part)
            if re.fullmatch(r"\[[A-Z][^\]]*\]", part):
                r.font.highlight_color = WD_COLOR_INDEX.YELLOW


for t in ["[Date]", "The Editor-in-Chief\nBMC Medical Informatics and Decision Making", "Dear Editor,",
          f"We are pleased to submit our manuscript entitled \"{TITLE}\" for consideration as a Research article in "
          "BMC Medical Informatics and Decision Making.",
          "Public multimodal stroke datasets are increasingly used to develop prognostic models, yet their small size, "
          "pre-processing and undocumented centre structure make it unclear what such studies can establish. We propose "
          "a reproducible five-module framework that assesses data readiness, applies a locked evaluation protocol with "
          "precision analysis, estimates prognostic signal, examines transportability across centres and converts the "
          "estimates into design parameters and post hoc go/no-go proposals for a definitive study. We apply it to a "
          "clinically relevant question: whether pre-treatment CT perfusion adds to clinical prediction of 90-day outcome "
          "after thrombectomy, using the public ISLES'24 training set (129 patients with a 90-day outcome).",
          "The framework recovered the physical units removed by the public pre-processing (with the Tmax scale "
          "identifiable in about two thirds of patients), inferred the two unlabelled centres from data provenance "
          "(consistent with the dataset descriptor, but not independently verified) and revealed large between-centre "
          "differences in outcome rate and data completeness. Pre-treatment CT perfusion showed no statistically "
          "demonstrated incremental value in any form tested (primary ΔAUC +0.011, 95% CI −0.039 to +0.068); because "
          "equivalence within ±0.05 AUC could not be established, a modest benefit is not excluded. Early post-treatment "
          "information (24-h NIHSS and follow-up infarct volume) showed larger estimated increments that were borderline "
          "after multiplicity adjustment. The study ends with explicit sample-size estimates and data requirements for a "
          "definitive, centre-aware study.",
          "We believe the work fits the journal's scope in clinical decision support, data reuse and methodological "
          "rigour in predictive modelling. All results, including null and borderline results, are reported with their "
          "uncertainty; reporting follows TRIPOD+AI, and the analysis code, fold manifests, out-of-fold predictions and "
          "result tables will be made available at [Repository URL and DOI].",
          "The cohort and clinical predictor set overlap with a companion clinical-only study submitted elsewhere, which "
          "is cited and disclosed in the manuscript; the present manuscript addresses a different question (imaging "
          "and post-treatment information) and all results were generated anew. The manuscript is not under "
          "consideration by any other journal, and all authors have approved the submission. The authors declare no "
          "competing interests.",
          "[Suggested reviewers, if required]",
          "Thank you for considering our manuscript.", "Yours sincerely,",
          "Bao Thien Nguyen, on behalf of all authors\nInstitute of Intelligent and Interactive Technologies (3i "
          "Institute), University of Economics Ho Chi Minh City (UEH), Ho Chi Minh City, Vietnam\nbaont@ueh.edu.vn"]:
    para(t)
d.save(SUB / "Cover_letter.docx")

# ------------------------------------------------------------------ 02 code repository
CODE = sorted(ROOT.glob("s[0-9][0-9]_*.py")) + [ROOT / f for f in ["config.py", "features.py", "httpfile.py",
                                                                  "stats_utils.py", "README.md", "DATA_NOTICE.md",
                                                                  "PLAN_v4_prespecified.md",
                                                                  "SAP_supplementary_analysis_plan.md"]]
for f in CODE:
    shutil.copy(f, REPO / f.name)
(REPO / "requirements.txt").write_text(
    "# Python 3.10.11\nscikit-learn==1.7.2\nstatsmodels==0.15.0\nscipy==1.15.3\nnumpy==2.2.6\npandas==2.3.3\n"
    "nibabel==5.4.2\nSimpleITK==2.5.7\nnilearn==0.14.1\npyarrow==25.0.1\nmatplotlib==3.10.9\nshap==0.49.1\n"
    "openpyxl==3.1.5\npython-docx\n", encoding="utf-8")
for f in TAB.glob("*"):
    if f.suffix in (".csv", ".json"):
        shutil.copy(f, REPO / "results" / "tables" / f.name)
for f in (OUT / "oof").glob("*.csv"):
    shutil.copy(f, REPO / "results" / "oof" / f.name)
for f in ["inferred_site.csv", "location_features.csv", "native_acquisition_fingerprints.csv"]:
    shutil.copy(DATA / f, REPO / "results" / "derived" / f)
shutil.copy(ROOT / "DATA_NOTICE.md", REPO / "DATA_NOTICE.md")   # the notice is a repository file (referenced by README.md)

# ------------------------------------------------------------------ 03 internal
cr = json.load(open(TAB / "reference_verification_crossref.json", encoding="utf-8"))
ms = Document(OUT / "Manuscript_BMC_MIDM.docx")
paras = [p.text for p in ms.paragraphs]
refs = paras[paras.index("References") + 1:]
refs = [r for r in refs if re.match(r"^\d+\. ", r)]
rows = []
NOTE = {
 "borsos": "Corrected: full author list and volume (147) added",
 "delarosa": "Checked on arXiv (v1 2024, v2 2025); citation format corrected",
 "buergel": "Added: source of the Juelich corticospinal-tract map used in the atlas analysis",
 "rangaraju": "Crossref print year 2015; PubMed: 2016 Mar;4(3-4):120-9 — kept 2016 (PubMed)",
 "cawley": "No DOI; checked on jmlr.org: 11(70):2079-2107, 2010",
 "pedregosa": "No DOI; checked on jmlr.org: 12(85):2825-2830, 2011",
 "eldridge": "DOI resolves; matches Crossref (PLoS One 2016;11(3):e0150205)",
 "hfmirror": "Dataset URL accessed during the analysis",
 "branch2": "Companion manuscript (submitted); update when published",
}
keymap = {}
for k, v in cr.items():
    if v.get("doi"):
        keymap[v["doi"].lower()] = k
for r in refs:
    n = int(r.split(".")[0]); m = re.search(r"doi:(\S+?)\.?$", r)
    k = keymap.get(m.group(1).lower()) if m else None
    if k is None:
        k = ("buergel" if "Bürgel" in r else "delarosa" if "arXiv" in r else "cawley" if "Cawley" in r else
             "pedregosa" if "Pedregosa F, Varoquaux" in r else "hfmirror" if "hugging-science" in r else
             "branch2" if "Hoang TB" in r else "eldridge" if "Eldridge" in r else "?")
    c = cr.get(k, {})
    status = ("DOI resolves; author, title, journal, year, volume and pages match Crossref" if c.get("first") else "")
    rows.append({"No.": n, "Key": k, "Reference": r[len(str(n)) + 2:],
                 "Crossref record": (f"{c.get('first','')} | {c.get('title','')[:90]} | {c.get('journal','')} "
                                     f"{c.get('year','')};{c.get('vol','')}:{c.get('page') or c.get('article') or ''}")
                 if c.get("first") else "", "Status": NOTE.get(k, status or "Checked")})
pd.DataFrame(rows).to_excel(INT / "Reference_verification.xlsx", index=False)
shutil.copy(OUT / "Branch3_Manuscript_BMC_MIDM_v3_full_backup.docx", INT / "Manuscript_long_version_backup.docx")
shutil.copy(ROOT / "BAO_CAO_AUDIT_NHANH3.md", INT / "BAO_CAO_AUDIT_NHANH3.md")
shutil.copy(ROOT / "REVIEW_KIEN_TRUC_BAI.md", INT / "REVIEW_KIEN_TRUC_BAI.md")
shutil.copy(ROOT / "PACKAGE_README.md", PKG / "00_README.md")
print("package:", PKG)
for p in sorted(PKG.rglob("*")):
    if p.is_file() and "results" not in p.parts:
        print("  ", p.relative_to(PKG))
print("   results files:", sum(1 for p in (REPO / "results").rglob("*") if p.is_file()))
