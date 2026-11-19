"""Cover letter, scientifically revised (claims limited to what the audit verified). Copy of the cover-letter part of
s30_package.py with content changes only. Placeholders in [square brackets] are highlighted and left for the authors."""
import os, re, sys
from pathlib import Path
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import Pt, Cm

WS = Path(os.environ.get("BRANCH3_WS", Path(__file__).resolve().parents[2]))
PKG = Path(sys.argv[1]) if len(sys.argv) > 1 else WS / "BMC_MIDM_FEASIBILITY_FINAL_AUDIT_PACKAGE"
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
out = PKG / "01_MANUSCRIPT" / "Cover_letter_SCIENTIFIC_REVISED.docx"
out.parent.mkdir(parents=True, exist_ok=True); d.save(out); print("saved", out)
