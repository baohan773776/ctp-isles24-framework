"""Submission version of the manuscript: internal model codes (P1, R1, E, T, V, Loc), internal process words
(canonical, frozen, ledger, Tmax-certain, lettered experiments) and a few stock phrases are replaced by descriptive
scientific wording; author-completed items are left as highlighted placeholders. Numbers are not changed (checked by
comparing the multiset of numeric tokens before and after, apart from deliberately added or removed sentences).
Word formatting is kept: text is replaced inside existing runs; Figures 3 and 6 are swapped for versions with
descriptive labels (same data, redrawn by w07_figures_clean.py).
Input : BMC_FEASIBILITY_VALIDITY_UPGRADE/Manuscript_BMC_MIDM_VALIDITY_REVISED.docx
Output: BMC_FINAL_SUBMISSION_STAGING/Manuscript_BMC_MIDM_FINAL.docx (+ AUTHOR_TODO.md)
"""
import copy
import re
import struct

from docx import Document
from docx.enum.text import WD_COLOR_INDEX

from v_common import ROOT, VFIG

SRC = ROOT.parent / "BMC_FEASIBILITY_VALIDITY_UPGRADE" / "Manuscript_BMC_MIDM_VALIDITY_REVISED.docx"
OUTD = ROOT.parent / "BMC_FINAL_SUBMISSION_STAGING"
OUTD.mkdir(parents=True, exist_ok=True)
DST = OUTD / "_build" / "Manuscript_BMC_MIDM_FINAL_before_repair.docx"   # w13_targeted_repair.py writes the final file
DST.parent.mkdir(parents=True, exist_ok=True)

ABSTRACT = {
    5: ("Background:", " Public multimodal stroke datasets are increasingly used for prognostic modelling, but their small size, "
        "pre-processing and unlabelled centres limit what they can show. We developed a reproducible feasibility framework and "
        "applied it to one question: does pre-treatment CT perfusion (CTP) add to clinical "
        "prediction of 90-day outcome after thrombectomy?"),
    6: ("Methods:", " We analysed 129 patients (44 with modified Rankin Scale 3–6) from the ISLES'24 training set. The framework "
        "has five modules: data readiness (M1), a locked nested cross-validation protocol with precision analysis (M2), signal "
        "estimation (M3), transportability across centres (M4) and design outputs for a definitive study (M5). Post-treatment, "
        "location and occlusion-population models followed a predefined supplementary plan; other sensitivity analyses and an "
        "ISLES 2018 technical benchmark were post hoc."),
    7: ("Results:", " Perfusion map units were recoverable (median ICC 0.96 against native maps; Tmax "
        "scale identifiable in 88/129 patients). Unlabelled centres were inferred from data provenance (99/50) "
        "and differed in outcome rate (38/88 vs 6/41) and imputation. A clinical model reached an AUC of 0.763 (0.698–0.727 with "
        "configurations re-selected within folds); adding CTP changed it by +0.011 (95% CI −0.039 to +0.068). Equivalence within "
        "±0.05 was not established; thresholds, volumes and location gave similar results, also within centres. Refitting models "
        "in bootstrap resamples widened the spread of this increment 1.7-fold. Post-treatment information showed larger "
        "increments: in one centre the AUC rose from 0.72 to 0.81 with 24-h NIHSS and 0.83 with follow-up infarct volume; in the "
        "full cohort infarct volume added +0.093 (95% CI +0.016 to +0.172; Holm-adjusted P = 0.057). Transport to the smaller "
        "centre was inconclusive (6 events). On ISLES 2018 (63 patients), the CTP pipeline needed unit harmonisation and its core "
        "agreed modestly with DWI (Dice 0.21). A definitive study would need about 350 patients (≈120 events), 24-h NIHSS, "
        "follow-up imaging, complete laboratory data and centre labels."),
    8: ("Conclusions:", " In this feasibility study, pre-treatment CTP showed no statistically demonstrated incremental prognostic "
        "value after thrombectomy, although a modest gain could not be excluded; the early post-treatment course showed a larger, "
        "borderline increment. The framework converts a small public dataset into post hoc go/no-go proposals and sample-size "
        "estimates; external prognostic validation was not possible."),
}

SUB = {
    12: [("pre-processing choices that can silently change what is measurable", "pre-processing choices that can alter what is measurable")],
    20: [("A post hoc patient-level ledger of seven provenance signatures", "A post hoc patient-level table of seven provenance signatures")],
    25: [("H1 (location): adding CTP location to P1,", "H1 (location): adding CTP location to the clinical GBM,"),
         ("H3 (post-treatment course): adding follow-up DWI infarct volume to R1 in the full cohort",
          "H3 (post-treatment course): adding follow-up DWI infarct volume to the parsimonious model in the full cohort")],
    32: [("The frozen CTP feature extractor and core definition (ipsilateral Tmax >6 s with rCBF <30%) were applied without "
          "modification or learning to",
          "The CTP feature extractor and core definition (ipsilateral Tmax >6 s with rCBF <30%) were applied unchanged, without "
          "any learning, to"),
         ("UniToBrain (no Tmax map; one 50.8 GB archive), the Johns Hopkins head-CT masks (compatible intracranial target, but no "
          "programmatic access), CPAISD and AISD (no matching pipeline output) were not analysed",
          "UniToBrain (no Tmax map), the Johns Hopkins head-CT brain masks (compatible intracranial target, but the data could not "
          "be obtained during this study), CPAISD and AISD (no reference label matching a pipeline output) were not analysed")],
    38: [("), which the Tmax-certain sensitivity analysis (n = 85) addresses by restriction rather than correction.",
          "); a sensitivity analysis restricted to the 85 patients with a reliably recoverable Tmax scale addresses this by "
          "restriction rather than correction.")],
    41: [("and the parsimonious model R1 0.681", "and the parsimonious logistic model 0.681"),
         ("of the coefficient mass of model E.", "of the coefficient mass of the all-channel model.")],
    42: [("Adding CTP to P1 gave", "Adding CTP to the clinical GBM gave"),
         ("with R1 as reference", "with the parsimonious model as reference"),
         ("with a recalibrated P1", "with a recalibrated clinical GBM"),
         ("with CTP location (primary H1:", "with CTP location (H1:")],
    43: [("so P1's absolute AUC should be read", "so the absolute AUC of the clinical GBM should be read"),
         ("against the locked P1 in the same run", "against the locked configuration in the same run")],
    46: [("Adding follow-up infarct volume to R1 raised", "Adding follow-up infarct volume to the parsimonious model raised"),
         ("(primary H3:", "(H3:")],
    48: [("lowered the AUC of P1 from", "lowered the AUC of the clinical GBM from"), ("(P1 0.438", "(clinical GBM 0.438")],
    52: [("This clinical reference was 0.065 lower than the locked P1",
          "This clinical reference was 0.065 lower than the clinical GBM with the locked configuration")],
    53: [("versus 1.000 in the 85 Tmax-certain patients)", "versus 1.000 in the 85 patients with a reliably recoverable Tmax scale)"),
         ("The provenance ledger identified", "The provenance table identified"),
         ("in the 44 patients without certain recovery", "in the 44 patients without a reliably recoverable Tmax scale"),
         ("performed as well as the canonical DWI-based registration", "performed as well as the DWI-based registration of the primary analysis"),
         ("and the admission-time H1 increment was", "and the location increment (H1) with admission-time registration was")],
    55: [("86% and 91% of brain voxels above the frozen clip limits), so the frozen absolute tissue limits removed",
          "86% and 91% of brain voxels above the clip limits used for ISLES'24), so the fixed absolute tissue limits removed"),
         ("the frozen CTP core had", "the CTP core had"),
         ("results were similar across acquisition protocols (Fig. S8).",
          "results were similar across acquisition protocols (Additional file 5, Table S34; Fig. S8).")],
    57: [("the framework gave explicit answers to feasibility questions that a conventional small prediction study leaves implicit.",
          "the framework answered feasibility questions that a conventional small prediction study usually leaves open.")],
    59: [("The framework also exposed problems that matter for anyone reusing ISLES'24.",
          "The framework also identified problems that are relevant to any reuse of ISLES'24."),
         ("both are reminders that small cohorts need", "both findings indicate that small cohorts need")],
    60: [("Positioning this work as a feasibility study is deliberate.", "This work was designed as a feasibility study."),
         ("Rather than overstating a null or a borderline result, the framework reports what the data can establish and converts "
          "the uncertainty into design parameters.",
          "The framework therefore reports what the data can establish and translates the remaining uncertainty into design parameters.")],
    61: [("The post hoc analyses refine rather than overturn these conclusions.", "The post hoc analyses qualified these conclusions without changing them."),
         ("removed the dependence of H1 on a post-treatment image", "removed the dependence of the location analysis on a post-treatment image"),
         ("Externally, the frozen feature extractor ran", "On external data, the unchanged feature extractor ran")],
    63: [("and requests for cohorts with CTP and 90-day mRS have been drafted but not granted.",
          "and no cohort with CTP and 90-day mRS was available to us."),
         ("in the primary H1 analysis, targeted", "in the primary location analysis, targeted"),
         ("which a bootstrap-refit experiment showed", "which a bootstrap-refit analysis showed")],
    144: [("Dashed line: clinical GBM (P1).", "Dashed line: clinical GBM.")],
    129: [("All models: Additional file 2.", "Combined models are equal-weight late fusions of the two probabilities. All models: Additional file 2.")],
}

FULL = {
    24: ("Pre-treatment models: P1,",
         "Pre-treatment models. The clinical reference was a gradient-boosting machine (GBM) on the 22 variables with the "
         "configuration locked by the companion study (80 trees, depth 3, learning rate 0.1, subsample 0.7), which that study had "
         "selected by non-nested cross-validation on the same cohort. Because this selection could bias the out-of-fold AUC of the "
         "clinical GBM, and the direction of any effect on the CTP increment is not known a priori, a sensitivity analysis "
         "re-selected the GBM configuration inside each training fold (inner 5-fold grid search over 24 configurations including "
         "the locked one, minimising log-loss) and repeated the primary comparison against this nested-tuned reference. A "
         "parsimonious logistic model without tuning (age, admission NIHSS, premorbid mRS, glucose) served as a tuning-free "
         "reference. The CTP models were single-channel elastic-net models (CBF, CBV, MTT, Tmax); an all-channel elastic net on "
         "all 53 features; a classical-threshold model (core, Tmax >6 s, mismatch ratio, hypoperfusion intensity ratio) [35]; an "
         "absolute-volume model; and a location model using the fraction of four eloquent atlas regions (corticospinal tract, "
         "deep grey matter, insula/operculum, left language cortex) covered by Tmax >6 s tissue. CTP models were combined with "
         "clinical models by equal-weight averaging of probabilities (late fusion, no trainable fusion parameters). The "
         "prespecified primary comparison was the clinical GBM combined with the all-channel CTP model versus the clinical GBM "
         "alone; robustness was checked against the parsimonious model, a recalibrated clinical GBM, native-unit features and "
         "eight sensitivity analyses (Additional file 4)."),
    31: ("After the primary results were known, five post hoc analyses",
         "After the primary results were known, five post hoc sensitivity analyses addressed remaining threats to internal "
         "validity; none was prespecified (Additional file 5). First, in a consistent fully nested comparison, the learner family "
         "(elastic net or gradient boosting) and its hyperparameters were selected jointly by inner 5-fold log-loss within each "
         "outer training fold for the clinical (22 variables), CTP (53 features, recovered or native units) and joint feature sets "
         "alike, using the same outer folds as the primary analysis and the same equal-weight late fusion. Second, recovered and "
         "native Tmax maps were compared voxel-wise on a common grid in each patient (absolute error; Dice and disagreement of the "
         "Tmax >4, >6, >8 and >10 s masks), and core, Tmax >6 s and mismatch volumes were compared in mL, stratified by whether "
         "the Tmax clip ceiling was present. Third, seven provenance signatures were combined in a patient-level table, and the "
         "centre analyses (M4) were repeated with the ambiguous assignment reversed and with the ambiguous patient excluded. "
         "Fourth, the atlas registration of the location hypothesis (H1) was repeated with the admission non-contrast CT as the "
         "only target (intracranial cavity of −20 to 100 HU enclosed by the skull), so that no post-treatment image enters "
         "admission-time features. Fifth, with a budget fixed in advance (100 patient-level bootstrap resamples, each analysed "
         "with one 10-fold cross-validation in which duplicated patients stay in the same fold), the primary comparison was "
         "refitted in every resample to quantify the model-refitting variability that the fixed-prediction bootstrap omits."),
    67: ("AUC, area under",
         "AUC, area under the receiver-operating-characteristic curve; CBF, cerebral blood flow; CBV, cerebral blood volume; CI, "
         "confidence interval; CITL, calibration-in-the-large; CTP, CT perfusion; CV, cross-validation; DWI, diffusion-weighted "
         "imaging; GBM, gradient-boosting machine; HU, Hounsfield unit; ICC, intraclass correlation coefficient; mRS, modified "
         "Rankin Scale; MTT, mean transit time; NIHSS, National Institutes of Health Stroke Scale; OOF, out-of-fold; rCBF, "
         "relative cerebral blood flow; Tmax, time-to-maximum of the residue function."),
    156: ("Additional file 5",
          "Additional file 5 (.xlsx, .pdf). Supplementary Tables S21–S37 and Figure S8. Post hoc sensitivity analyses (consistent "
          "nested comparison, native-unit verification, centre provenance, admission-time registration, bootstrap-refit), "
          "external technical component benchmarking on ISLES 2018, and the compatibility matrix of external datasets."),
}

TABLE_ROWS = {
    "R1 4-predictor logistic": "Parsimonious logistic (4 predictors)",
    "P1 clinical GBM (22 predictors)": "Clinical GBM (22 predictors)",
    "P1 recalibrated": "Clinical GBM, recalibrated",
    "E all CTP channels": "CTP, all channels",
    "T classical thresholds": "CTP, classical thresholds",
    "V absolute volumes (mL)": "CTP, absolute volumes (mL)",
    "Loc CTP location": "CTP, location",
    "P1 + E fusion": "Clinical GBM + CTP, all channels",
    "R1 + E fusion": "Parsimonious logistic + CTP, all channels",
    "P1 + V fusion": "Clinical GBM + CTP volumes",
    "P1 + Loc fusion": "Clinical GBM + CTP location",
    "R1 + follow-up infarct volume": "Parsimonious logistic + follow-up infarct volume",
    "P1 + follow-up infarct volume": "Clinical GBM + follow-up infarct volume",
}

# placeholders: (paragraph index, run index to replace or None to append, text)
PH_ETHICS = "[AUTHORS TO CONFIRM: whether the authors' institution requires a formal ethics waiver for secondary analysis of public de-identified data; if so, name the committee and reference number.]"
PH_REPO = "[AUTHORS TO COMPLETE: repository URL and DOI, e.g. a Zenodo record of the GitHub release]"
PH_COMP = "[AUTHORS TO CONFIRM]"
PH_FUND = "[AUTHORS TO COMPLETE: funding sources with grant numbers and the role of the funder, or “This research received no specific funding.”]"
# author line as set by the authors in Word on 2026-11-14 (first author renamed; the line stays highlighted for confirmation)
AUTHOR_OLD, AUTHOR_NEW = "Tran Bao Hoang¹", "Bao Han…¹"
PH_CRED = ("[AUTHORS TO COMPLETE: contribution of each author (Bao Han…, KTN, BTN) using CRediT roles, e.g. conceptualisation, methodology, "
           "software, formal analysis, writing – original draft, writing – review and editing, supervision; end with “All authors "
           "read and approved the final manuscript.”]")
PH_ACK = "[AUTHORS TO COMPLETE if applicable: other acknowledgements]"
PH_AI = "[AUTHORS TO CONFIRM: wording of the AI-use statement against the journal policy]"
PH_REF20 = "[AUTHORS TO UPDATE: journal, year and DOI, or current status, of the companion study]"
PH_TITLE = "[AUTHORS TO COMPLETE: e-mail addresses of all authors; ORCID iDs if available]"


def set_single(p, new):
    runs = p.runs
    runs[0].text = new
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def add_hl(p, text, template_run=None, sep=" "):
    r = p.add_run(sep + text)
    if template_run is not None:
        r.font.name, r.font.size = template_run.font.name, template_run.font.size
    r.bold = False
    r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return r


def png_size(b):
    assert b[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", b[16:24])


def swap_image(doc, p, png_path):
    blob = png_path.read_bytes()
    xml = p._p
    blips = xml.xpath(".//a:blip")
    assert len(blips) == 1
    rid = blips[0].get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
    part = doc.part.related_parts[rid]
    assert part.content_type == "image/png", part.content_type
    part._blob = blob
    w, h = png_size(blob)
    ext = xml.xpath(".//wp:extent")[0]
    cx, cy = int(ext.get("cx")), int(ext.get("cy"))
    ncx = int(cy * w / h)
    if ncx > cx:                      # keep within the original width
        ncx, ncy = cx, int(cx * h / w)
    else:
        ncy = cy
    for e in xml.xpath(".//wp:extent") + xml.xpath(".//a:ext"):
        e.set("cx", str(ncx)); e.set("cy", str(ncy))


NUM = re.compile(r"[−+-]?\d+(?:\.\d+)?")


def main():
    doc = Document(SRC)
    P = list(doc.paragraphs)
    before = {i: P[i].text for i in range(len(P))}

    for i, (lab, body_text) in ABSTRACT.items():
        assert P[i].runs[0].text.strip() == lab and len(P[i].runs) == 2, (i, P[i].runs[0].text)
        lead = "" if P[i].runs[0].text.endswith(" ") else " "
        P[i].runs[1].text = lead + body_text.lstrip()
    for i, subs in SUB.items():
        t = P[i].text
        for old, new in subs:
            assert t.count(old) == 1, (i, old[:60])
            t = t.replace(old, new)
        if len(P[i].runs) == 1:
            set_single(P[i], t)
        else:                                      # label run + body run (abstract)
            lab = P[i].runs[0].text
            assert t.startswith(lab) and len(P[i].runs) == 2, i
            P[i].runs[1].text = t[len(lab):]
    for i, (start, new) in FULL.items():
        assert P[i].text.startswith(start), (i, P[i].text[:60])
        assert len(P[i].runs) == 1, i
        set_single(P[i], new)

    # tables
    for t in doc.tables:
        for row in t.rows:
            c = row.cells[0]
            if c.text in TABLE_ROWS:
                set_single(c.paragraphs[0], TABLE_ROWS[c.text])

    # author line (text replaced inside the single existing run; highlighted as in the authors' own edit)
    assert len(P[1].runs) == 1 and P[1].runs[0].text.count(AUTHOR_OLD) == 1, P[1].text
    P[1].runs[0].text = P[1].runs[0].text.replace(AUTHOR_OLD, AUTHOR_NEW)
    P[1].runs[0].font.highlight_color = WD_COLOR_INDEX.YELLOW

    # declarations and placeholders
    body = lambda i: P[i].runs[1]
    add_hl(P[69], PH_ETHICS, body(69))
    r72 = P[72].runs
    assert r72[2].text == "[Repository URL and DOI]"
    r72[1].text = r72[1].text.replace("fold manifests, out-of-fold predictions and all result tables are available at ",
                                      "fold assignments, out-of-fold predictions, all result tables and the final models fitted "
                                      "on the full cohort are available at ")
    r72[2].text = PH_REPO; r72[2].font.highlight_color = WD_COLOR_INDEX.YELLOW
    add_hl(P[73], PH_COMP, body(73))
    for i, ph in ((74, PH_FUND), (75, PH_CRED)):
        assert P[i].runs[1].text.startswith("[")
        P[i].runs[1].text = ph; P[i].runs[1].font.highlight_color = WD_COLOR_INDEX.YELLOW
        if len(P[i].runs) > 2 and P[i].runs[2].text == ".":
            P[i].runs[2]._r.getparent().remove(P[i].runs[2]._r)
    add_hl(P[76], PH_ACK, body(76))
    add_hl(P[34], PH_AI, P[34].runs[0])
    assert P[97].text.startswith("20. Hoang TB")
    add_hl(P[97], PH_REF20, P[97].runs[0])

    # figures 3 and 6 with descriptive labels
    assert P[144].text.startswith("Fig. 3.") and P[150].text.startswith("Fig. 6.")
    swap_image(doc, P[143], VFIG / "final" / "Fig3_auc_forest.png")
    swap_image(doc, P[149], VFIG / "final" / "Fig5_calibration.png")

    # title-page placeholder (inserted last so that indices above stay valid)
    newp = copy.deepcopy(P[3]._p)
    P[3]._p.addnext(newp)
    from docx.text.paragraph import Paragraph
    np_ = Paragraph(newp, P[3]._parent)
    set_single(np_, PH_TITLE)
    np_.runs[0].font.highlight_color = WD_COLOR_INDEX.YELLOW

    doc.save(DST)

    # ---------------- checks ----------------
    d2 = Document(DST)
    txt = "\n".join(p.text for p in d2.paragraphs) + "\n" + "\n".join(c.text for t in d2.tables for r in t.rows for c in r.cells)
    codes = re.findall(r"\b(?:P1|R1|Loc|model E|frozen|canonical|ledger|Tmax-certain|Exp [A-E])\b|\([A-E]\) ", txt)
    print("leftover internal codes:", codes)
    stock = re.findall(r"\b(?:delve|crucial|pivotal|leverag\w*|notably|landscape|underscore\w*|showcas\w*|seamless\w*|"
                       r"comprehensive|novel|intricate|furthermore|moreover|paramount|realm|tapestry|groundbreaking|"
                       r"cutting-edge|deliberate|invite)\b", txt, flags=re.I)
    print("stock-phrase hits:", stock)
    sec = [(p.runs[0].text.strip(), len("".join(r.text for r in p.runs[1:]).split())) for p in d2.paragraphs[6:10]]
    print("abstract words (body, excluding labels):", sec, sum(s[1] for s in sec))
    # numbers: removed / added tokens relative to the source text
    from collections import Counter
    a = Counter(NUM.findall("\n".join(before.values()) + "\n" + "\n".join(c.text for t in Document(SRC).tables for r in t.rows for c in r.cells)))
    b = Counter(NUM.findall(txt))
    print("numbers removed:", dict(a - b))
    print("numbers added:", dict(b - a))
    todo = [ph for ph in (PH_TITLE, PH_ETHICS, PH_REPO, PH_COMP, PH_FUND, PH_CRED, PH_ACK, PH_AI, PH_REF20)]
    (OUTD / "AUTHOR_TODO.md").write_text(
        "# Items the authors must complete before submission\n\n"
        "All placeholders are highlighted in yellow in Manuscript_BMC_MIDM_FINAL.docx.\n\n"
        + "\n".join(f"{k}. {ph}" for k, ph in enumerate(todo, 1)) +
        "\n\nAlso:\n- Remove the yellow highlighting after completing each item.\n"
        "- The author line is highlighted as entered by the authors on 14 Nov 2026 (first author: Bao Han…); confirm it "
        "and remove the highlighting.\n"
        "- Send the data-access requests (CONTRAST, CRISP, VISTA) only if you intend to run an external validation; they are not needed for submission.\n"
        "- Additional files 1-4 are unchanged from the 13 Nov 2026 package; Additional file 3 (the supplementary analysis plan) "
        "keeps its original model codes because it is the plan as finalised before the analyses.\n", encoding="utf-8")


if __name__ == "__main__":
    main()
