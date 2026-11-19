"""Targeted scientific repair of the final manuscript (2026-11-14, second pass). No model is refitted and no canonical
output changes. Input: the w09 output (_build/Manuscript_BMC_MIDM_FINAL_before_repair.docx). Output:
BMC_FINAL_SUBMISSION_STAGING/Manuscript_BMC_MIDM_FINAL.docx. Every edit is anchored on exact text (asserted unique) and
is made inside the existing run, so Word formatting is unchanged.

Repairs: (1) ISLES'24 centre counts from three descriptor versions, (2) bootstrap-refit described as exploratory, not
as a correction factor, (3) ISLES 2018 slab overlap and de-duplicated metrics, (4) limited core agreement separated
from technical execution, harmonisation not fully independent, (5) approximate voxel alignment and automatic-mask
registration Dice, (6) abstract AUCs 0.727 and 0.698 stated as separate estimates, (7) conditional recommendations
for CTP and a provisional 350-patient planning figure, (8) Methods statement on voxelwise analysis reconciled.
"""
import re
from collections import Counter

import pandas as pd
from docx import Document
from docx.enum.text import WD_COLOR_INDEX

from v_common import ROOT, VTAB

STG = ROOT.parent / "BMC_FINAL_SUBMISSION_STAGING"
SRC = STG / "_build" / "Manuscript_BMC_MIDM_FINAL_before_repair.docx"
DST = STG / "Manuscript_BMC_MIDM_FINAL.docx"

ABSTRACT = {
    "Results:": (
        "Perfusion map units were recoverable (median ICC 0.96 against native maps; Tmax scale identifiable in 88/129 "
        "patients). Unlabelled centres were inferred from data provenance (99/50; published count 100/49). The clinical "
        "model reached an AUC of 0.763; re-selecting GBM settings within folds gave 0.727 and post hoc fully nested learner "
        "selection 0.698. Adding CTP changed the AUC by +0.011 (95% CI −0.039 to +0.068), and by +0.054 (95% CI −0.006 to "
        "+0.121) under fully nested selection; exploratory refitting (different design) showed greater variability without "
        "calibrating these intervals. In one centre, post-treatment data raised AUC from 0.72 to 0.81 (24-h NIHSS) and 0.83 "
        "(follow-up infarct volume); in the full cohort infarct volume added +0.093 (95% CI "
        "+0.016 to +0.172; Holm-adjusted P = 0.057). Transport to the smaller centre was inconclusive (6 events). On ISLES "
        "2018 (63 patients), the CTP pipeline ran after harmonisation, but its core agreed poorly with expert DWI cores "
        "(Dice 0.21, sensitivity 0.15). A provisional target of about 350 "
        "patients (≈120 events) applies only to a constrained pre-treatment CTP comparison, not to post-treatment, highly "
        "parameterised or external-validation analyses."),
    "Conclusions:": (
        "In this feasibility study, pre-treatment CTP showed no statistically demonstrated incremental prognostic value "
        "after thrombectomy; a modest gain could not be excluded, and its size depended on tuning. Post-treatment "
        "information showed a larger, borderline increment. The framework yields conditional design proposals; external "
        "prognostic validation was not possible."),
}

# (old, new) pairs; each old string must occur exactly once in the body paragraphs
EDITS = [
    # 1. centre counts (Methods: design, centres; Results M1; reference 14)
    ("(149 patients treated with endovascular reperfusion; the first version of the dataset descriptor reports 100 training "
     "cases from Munich and 50 from Zurich, and the revised version 99 and 50 for the 149 released cases) [14].",
     "(149 patients treated with endovascular reperfusion at two centres, Munich and Zurich) [14]. The centre split of the "
     "training set is reported as 100/50 of 150 cases in the first preprint version of the dataset descriptor, 99/50 of 149 "
     "in the revised preprint and 100/49 of 149 in Table 1 of the published article [14]; the revised preprint mentions a "
     "per-case centre list, but none was found in the separately downloadable files."),
    ("and the split reported by the providers (100/50 in the first descriptor version, 99/50 in the revised version). "
     "A post hoc patient-level table of seven provenance signatures is given in Additional file 5.",
     "and the splits reported by the providers (see above). Post hoc patient-level provenance tables are given in "
     "Additional file 5 (Tables S37 and S40–S42)."),
    ("they are inferred, not independently verified, and all centre-level results",
     "because no accessible source identifies the centre of individual patients, they are inferred, not verified, and all "
     "centre-level results"),
    ("identical to the 99/50 split of the revised dataset descriptor (the first version described 150 cases, 100/50)",
     "matching the revised preprint descriptor (99/50)"),
    ("so an identifier-based split would give 100/49, and all 40 patients",
     "so an identifier-based split gives 100/49, matching Table 1 of the published descriptor; all 40 patients"),
    ("doi:10.1148/ryai.250603", "doi:10.1148/ryai.250603. Preprint versions: arXiv:2408.11142 (v1, 2024; v2, 2025)."),
    # 8. voxelwise statement (M1) and 5. approximate grid (post hoc methods)
    ("(ICC(3,1)); no voxelwise reconstruction accuracy was computed on ISLES'24.",
     "(ICC(3,1)). The prespecified analyses included no voxelwise comparison on ISLES'24; an approximate voxelwise "
     "comparison was added post hoc (see below)."),
    ("were compared voxel-wise on a common grid in each patient",
     "were compared voxel-wise in each patient on an approximate common grid"),
    ("stratified by whether the Tmax clip ceiling was present.",
     "stratified by whether the Tmax clip ceiling was present; because the native maps were only resampled to the release "
     "grid and oriented by the axis-flip combination with the highest Tmax correlation, voxel measures combine recovery "
     "error with residual misalignment."),
    ("Third, seven provenance signatures were combined in a patient-level table, and the centre analyses (M4)",
     "Third, seven provenance signatures were combined in a patient-level table, the ambiguous patient was compared with "
     "the concordant patients on three further outcome-independent signatures (release-level imputation pattern, "
     "availability of 24-h NIHSS and CTP slab coverage), and the centre analyses (M4)"),
    ("so that no post-treatment image enters admission-time features.",
     "so that no post-treatment image enters admission-time features; registration quality was summarised as Dice overlap "
     "with this automatically derived mask, a consistency check rather than a comparison with expert manual segmentation."),
    # 2. bootstrap-refit (Methods M2, post hoc methods)
    ("(quantified post hoc; see below)", "(examined post hoc; see below)"),
    ("the primary comparison was refitted in every resample to quantify the model-refitting variability that the "
     "fixed-prediction bootstrap omits.",
     "the primary comparison was refitted in every resample to examine the model-refitting variability that the "
     "fixed-prediction bootstrap omits. Each resample contains only about 63% unique patients and was analysed with a "
     "single cross-validation, a design different from the primary analysis, so this analysis is exploratory: it describes "
     "variability under that design and is not a calibrated correction of the primary intervals."),
    # 3-4. ISLES 2018 methods
    ("slabs, patient-level bootstrap CIs), and maps were analysed as distributed and after a label-free median rescaling "
     "of CBF and CBV.",
     "slabs, patient-level bootstrap CIs). The two slabs of a patient may partially overlap and the files carry no usable "
     "slice position, so overlapping slices were identified from image content (a slice pair more similar, after in-plane "
     "alignment, than adjacent slices of the same slab) and counted once; slab-summed and de-duplicated estimates are both "
     "reported. Maps were analysed as distributed and after a label-free median rescaling of CBF and CBV. This rescaling "
     "was introduced after the as-distributed run on the same data had shown a unit mismatch, and ISLES 2018 had already "
     "been used for the unit-recovery simulation (M1), so the benchmark is not a fully independent, untouched evaluation."),
    # 7. design figure and decisions (M5)
    ("rounded up; it does not cover a 0.03 increment, models with more parameters, the post-treatment comparisons or "
     "external validation.",
     "rounded up; it does not cover a 0.03 increment, models with more parameters, the post-treatment comparisons or "
     "external validation. It is a provisional planning figure for a constrained pre-treatment CTP comparison and must be "
     "recalculated before a definitive study: it rests on fixed-prediction bootstrap standard errors that omit "
     "model-refitting variability and on the models, tuning procedure and case mix of this cohort, and the exploratory "
     "bootstrap-refit analysis can neither calibrate these standard errors nor show the direction or size of any resulting "
     "bias."),
    ("Table 3 lists the proposed decisions: no-go for pre-treatment CTP, thresholds, volumes and location as general "
     "prognostic markers after thrombectomy; conditional for CTP in severe strokes and for infarct location; go (as a "
     "proposal) for collecting 24-h NIHSS and follow-up infarct volume,",
     "Table 3 lists the proposed decisions, all conditional on study design and measurement validity. Pre-treatment CTP "
     "as measured here (pre-processed maps, fixed thresholds, late fusion with a locked clinical reference) is not proposed "
     "as a priority, but it is not ruled out: the post hoc fully nested comparison gave ΔAUC +0.054 (95% CI −0.006 to "
     "+0.121), and a definitive test would need native-unit maps, prespecified learners and tuning for both arms and a "
     "recalculated sample size. Classical thresholds, absolute volumes and atlas location are deprioritised as general "
     "prognostic markers after thrombectomy; CTP in severe strokes and infarct location are conditional; collecting 24-h "
     "NIHSS and follow-up infarct volume is proposed (go),"),
    ("; and centre-aware evaluation with complete laboratory data as a requirement.",
     ". Centre-aware evaluation with complete laboratory data is a requirement."),
    ("not progression criteria fixed in advance;",
     "not progression criteria fixed in advance, and are conditional on study design and measurement validity;"),
    # 2. bootstrap-refit (results)
    ("Refitting the whole procedure on bootstrap resamples gave a standard deviation of ΔAUC 1.7 times that of the "
     "fixed-prediction bootstrap (0.047 vs 0.027; 95% interval width 0.173 vs 0.107), so the primary confidence intervals "
     "understate uncertainty.",
     "In the exploratory bootstrap-refit analysis (100 resamples with about 63% unique patients each, one cross-validation "
     "per resample), the standard deviation of ΔAUC was 0.047 versus 0.027 for the fixed-prediction bootstrap (ratio 1.72; "
     "95% interval width 0.173 vs 0.107), and the refitted AUCs were lower on average (clinical GBM 0.691 vs 0.763), "
     "consistent with smaller effective training sets (Additional file 5, Table S32). Because this design differs from the "
     "primary analysis (fewer unique patients per resample, a single cross-validation), the greater variability does not "
     "show that the primary intervals are too narrow by any specific amount, and it does not establish the direction or "
     "size of any bias in the sample-size estimates."),
    # 5. voxel results, centre signatures, registration Dice
    ("In the 41 patients without a Tmax ceiling, recovered Tmax was inflated",
     "On the approximate common grid, recovered Tmax was inflated in the 41 patients without a Tmax ceiling"),
    ("remained uninformative (5–6 events).",
     "remained uninformative (5–6 events). On three further case-level signatures (release-level imputation pattern, "
     "recorded 24-h NIHSS and CT pixel spacing) this patient resembled the larger cluster; on each of them its value occurred "
     "in none of the 49 concordant patients of the smaller cluster. This is consistent with the 100/49 count of the published descriptor; "
     "without a subject-level list from the data providers its centre remains unverified (Additional file 5, Tables "
     "S40–S42)."),
    ("(median Dice with the CT intracranial mask 0.92 vs 0.91; 5 vs 21 registrations below 0.80)",
     "(median Dice with the automatically derived CT intracranial mask 0.92 vs 0.91; 5 vs 21 registrations below 0.80; a "
     "consistency measure, not agreement with expert segmentation)"),
    # 3-4. ISLES 2018 results
    ("monotone in every slab (a sanity check only). Against the expert DWI core, the CTP core had a patient-level Dice",
     "monotone in every slab; these are checks of technical execution only. Anatomical agreement with the expert DWI core "
     "was limited. With voxel counts summed over slabs, the CTP core had a patient-level Dice"),
    ("(Spearman 0.62, 95% CI 0.40–0.76); results were similar across acquisition protocols (Additional file 5, Table S34; "
     "Fig. S8). These results describe technical operation and core agreement on external data; they do not address the "
     "prognostic transportability of the models.",
     "(Spearman 0.62, 95% CI 0.40–0.76). In {n_dup} of the {n_two} patients with two slabs, image similarity indicated that "
     "one slice location appeared in both slabs (median Dice of the reference masks at these slice pairs {ot_dup}, versus "
     "{ot_other} at other matched pairs; physical slice positions were not available to verify this); counting these "
     "locations once gave a Dice of {d_est} (95% CI {d_lo}–{d_hi}), sensitivity {s_est} (95% CI "
     "{s_lo}–{s_hi}) and a mean volume difference of −{v_est} mL (95% CI −{v_lo} to −{v_hi}). Results were similar across "
     "acquisition protocols (Additional file 5, Tables S34, S38 and S39; Fig. S8). The pipeline thus executed reliably after "
     "harmonisation, but its fixed-threshold core detected on average only about 15% of each patient's DWI core; this is "
     "not a validation of clinical core segmentation, and it does not address the prognostic transportability of the "
     "models."),
    # Discussion
    ("These estimates translate into a specification for a definitive study of the pre-treatment CTP question: about 350 "
     "patients",
     "These estimates translate into a provisional specification for a definitive study of the pre-treatment CTP question, "
     "to be recalculated at the design stage: about 350 patients for a constrained pre-treatment CTP comparison (not "
     "sufficient for post-treatment, highly parameterised or external-validation analyses),"),
    # optimism of the locked clinical GBM: concern, not quantified (final content-only repair)
    ("This difference combines the optimism of a configuration chosen on the same cohort with the different selection "
     "criterion used here (log-loss), so the absolute AUC of the clinical GBM should be read as optimistic by up to about "
     "0.04.",
     "Because the two procedures differ in tuning strategy and objective (log-loss here), this difference does not isolate "
     "selection-induced optimism; that the locked configuration was chosen on the same cohort remains a concern, but its "
     "magnitude cannot be estimated from this comparison."),
    ("so its absolute AUC is optimistic;", "so its absolute AUC may be optimistic, although this comparison cannot isolate by how much;"),
    # final QA (content and code QA pass): null results not phrased as absence of effect; reproducibility scope
    ("whereas the CTP increment stayed null (Δ +0.005", "whereas the CTP increment stayed close to zero (Δ +0.005"),
    ("and CTP again added nothing (ΔAUC −0.025", "and CTP again did not improve discrimination (ΔAUC −0.025"),
    ("The analysis code regenerates every number, table and figure from the public data (see Availability of data and "
     "materials).",
     "The analysis code is intended to regenerate every number, table and figure from the public data; statistical results "
     "can be recomputed from the shared predictions, whereas image-derived quantities require the original imaging datasets "
     "(see Availability of data and materials)."),
    ("a nested re-selection changed the clinical AUC by −0.036 and left the CTP increment near zero,",
     "a nested re-selection with a different tuning objective gave a clinical AUC 0.036 lower (a difference that does not "
     "isolate selection-induced optimism) and left the CTP increment near zero,"),
    ("The post hoc analyses qualified these conclusions without changing them.", "The post hoc analyses qualified these conclusions."),
    ("in a definitive study, not for a positive conclusion here.",
     "in a definitive study; it supports neither a positive conclusion nor a firm no-go decision for CTP."),
    ("its fixed-threshold core agreed only modestly with an early DWI core [22, 23].",
     "its fixed-threshold core agreed poorly with an early DWI core (Dice 0.21) [22, 23]; technical execution, not "
     "anatomical accuracy, was shown."),
    # Limitations
    ("external benchmarking was technical only (ISLES 2018 has no outcome data)",
     "external benchmarking was technical only (ISLES 2018 has no outcome data; its median rescaling was introduced after a "
     "first run on the same data, and overlapping slab slices were identified from image content because slice positions "
     "were not available)"),
    ("Centres were inferred, not labelled; the labels were assigned by matching cluster size to the descriptor and one "
     "patient is assigned differently by the two provenance signatures (reassigning or excluding it did not change the "
     "conclusions);",
     "Centres were inferred, not labelled: centre counts differ between descriptor versions (99/50 and 100/49), one patient "
     "is assigned differently by the storage and identifier signatures (case-level signatures and the published count "
     "favour the larger centre; reassigning or excluding it did not change the conclusions), and no subject-level list was "
     "available to verify any assignment;"),
    ("a post hoc voxel-level comparison confirmed a median 4.8% Tmax inflation",
     "a post hoc voxel-level comparison on an approximate common grid indicated a median 4.8% Tmax inflation"),
    (", which a bootstrap-refit analysis showed to increase the standard deviation of ΔAUC about 1.7-fold, so the reported "
     "intervals are too narrow and the sample sizes optimistic;",
     "; an exploratory bootstrap-refit analysis (100 resamples with about 63% unique patients each, one cross-validation "
     "each) showed greater variability of ΔAUC (standard deviation ratio 1.72), but because of its different design it "
     "neither calibrates the reported intervals nor establishes the direction or size of any bias in the sample sizes;"),
    # Conclusions and additional-file list
    ("a centre-aware study of about 350 patients",
     "a centre-aware study of provisionally about 350 patients for the constrained pre-treatment comparison (a figure to "
     "be recalculated)"),
    ("Supplementary Tables S21–S37 and Figure S8.", "Supplementary Tables S21–S42 and Figure S8."),
    ("external technical component benchmarking on ISLES 2018, and the compatibility matrix of external datasets.",
     "external technical component benchmarking on ISLES 2018 (slab-summed and de-duplicated), the reconciliation of "
     "published centre counts, and the compatibility matrix of external datasets."),
]

TABLE3 = {
    "No-go for general post-thrombectomy prognosis; a definitive test needs ≈306 patients":
        "Not a priority as measured here, but not excluded (post hoc fully nested ΔAUC +0.054, 95% CI −0.006 to +0.121); a "
        "definitive test needs native-unit maps, prespecified tuning of both arms and a recalculated sample size "
        "(provisional ≈306 patients)",
}
TABLE3_ROW = {"Classical CTP thresholds and absolute volumes (mL)": "Deprioritise as general prognostic markers",
              "Location of hypoperfusion (atlas)": "Deprioritise as an admission-time marker"}
# Table 2: the primary location models use atlas registration to the follow-up DWI (H1 is retrospective), so their
# time point is not a pure admission-time model (final QA, item K)
TABLE2_TIME = {"CTP, location": "admission CTP; atlas registered to follow-up DWI",
               "Clinical GBM + CTP location": "admission CTP; atlas registered to follow-up DWI"}
AVAIL_ADD = (" Statistical results (AUCs, paired differences, bootstrap intervals, calibration and sample-size calculations) "
             "can be recomputed from the shared out-of-fold predictions and patient-level derived tables; image-derived "
             "quantities (unit recovery, perfusion features, voxel comparisons, registration and the ISLES 2018 benchmark) "
             "require the original public imaging datasets.")

# The published Table 1 count (100/49, N = 149) was confirmed by the authors; no placeholder is added (final content-only repair).


def fmt2(x):
    return f"{x:.2f}"


def dedup_numbers():
    S = pd.read_csv(VTAB / "vX1b_slab_overlap_summary.csv").iloc[0]
    R = pd.read_csv(VTAB / "vX1b_isles2018_core_vs_dwi_dedup.csv").set_index(["analysis", "metric"])
    key = "s03_harmonised: all patients | dedup_adjacency_keepA (primary)"
    d, s, v = R.loc[(key, "dice_mean")], R.loc[(key, "sensitivity_mean")], R.loc[(key, "vol_bias_ml")]
    return {"n_dup": int(S.patients_with_duplicated_slices_adjacency), "n_two": int(S.two_slab_patients),
            "ot_dup": fmt2(S.ot_slice_dice_median_duplicated_pairs), "ot_other": fmt2(S.ot_slice_dice_median_other_matched_pairs),
            "d_est": fmt2(d.estimate), "d_lo": fmt2(d.ci_lo), "d_hi": fmt2(d.ci_hi),
            "s_est": fmt2(s.estimate), "s_lo": fmt2(s.ci_lo), "s_hi": fmt2(s.ci_hi),
            "v_est": f"{-v.estimate:.0f}", "v_lo": f"{-v.ci_lo:.0f}", "v_hi": f"{-v.ci_hi:.0f}"}


def variants(s):
    yield s
    if "'" in s:
        yield s.replace("'", "’")


def apply_edit(paras, old, new):
    hits = []
    for p in paras:
        for o in variants(old):
            if o in p.text:
                hits.append((p, o))
    assert len(hits) == 1, (len(hits), old[:70])
    p, o = hits[0]
    assert p.text.count(o) == 1, old[:70]
    n = new if o == old else new.replace("'", "’")
    runs = [r for r in p.runs if o in r.text]
    assert len(runs) == 1, ("anchor spans runs", old[:70])
    runs[0].text = runs[0].text.replace(o, n)


def main():
    doc = Document(SRC)
    body = list(doc.paragraphs)
    before_txt = "\n".join(p.text for p in body) + "\n" + "\n".join(c.text for t in doc.tables for r in t.rows for c in r.cells)
    for lab, text in ABSTRACT.items():
        ps = [p for p in body if p.runs and p.runs[0].text.strip() == lab]
        assert len(ps) == 1 and len(ps[0].runs) == 2, lab
        lead = "" if ps[0].runs[0].text.endswith(" ") else " "
        ps[0].runs[1].text = lead + text
    nums = dedup_numbers()
    for old, new in EDITS:
        apply_edit(body, old, new.format(**nums) if "{n_dup}" in new else new)
    # Table 3 (go/no-go)
    t3 = [t for t in doc.tables if t.rows[0].cells[0].text == "Direction"]
    assert len(t3) == 1
    done = 0
    for row in t3[0].rows:
        c0, c2 = row.cells[0].text, row.cells[2]
        new = TABLE3.get(c2.text) or (TABLE3_ROW.get(c0) if c2.text == "No-go" else None)
        if new:
            p = c2.paragraphs[0]
            assert len(p.runs) == 1
            p.runs[0].text = new
            done += 1
    assert done == 3, done
    t2 = [t for t in doc.tables if t.rows[0].cells[0].text == "Model"]
    assert len(t2) == 1
    done = 0
    for row in t2[0].rows:
        if row.cells[0].text in TABLE2_TIME and row.cells[1].text == "admission":
            p = row.cells[1].paragraphs[0]
            assert len(p.runs) == 1
            p.runs[0].text = TABLE2_TIME[row.cells[0].text]
            done += 1
    assert done == 2, done
    # data availability: what the shared files reproduce vs what needs the imaging data (new run, body formatting)
    av = [p for p in body if p.text.startswith("Availability of data and materials:")]
    assert len(av) == 1 and av[0].runs[-1].text == "." and AVAIL_ADD.strip() not in av[0].text
    tmpl = av[0].runs[1]
    r = av[0].add_run(AVAIL_ADD)
    r.font.name, r.font.size, r.bold, r.italic = tmpl.font.name, tmpl.font.size, tmpl.bold, tmpl.italic
    doc.save(DST)

    # ---------------- checks ----------------
    d2 = Document(DST)
    txt = "\n".join(p.text for p in d2.paragraphs) + "\n" + "\n".join(c.text for t in d2.tables for r in t.rows for c in r.cells)
    sec = [(p.runs[0].text.strip(), len("".join(r.text for r in p.runs[1:]).split())) for p in d2.paragraphs[6:10]]
    n_body = sum(s[1] for s in sec)
    print("abstract words:", sec, n_body, "| with structured labels:", n_body + len(sec))
    assert n_body + len(sec) <= 350, "abstract exceeds 350 words including labels"
    bad = re.findall(r"\b(?:P1|R1|Loc|model E|frozen|canonical|ledger|Tmax-certain|Exp [A-E]|lower bound\w*)\b|0\.698–0\.727|1\.7-fold", txt)
    print("leftover codes / forbidden phrasing:", bad)
    stock = re.findall(r"\b(?:delve|crucial|pivotal|leverag\w*|notably|landscape|underscore\w*|showcas\w*|seamless\w*|"
                       r"comprehensive|novel|intricate|furthermore|moreover|paramount|realm|tapestry|groundbreaking|"
                       r"cutting-edge|deliberate|invite)\b", txt, flags=re.I)
    print("stock-phrase hits:", stock)
    print("'no-go' remaining:", [m.start() for m in re.finditer(r"(?i)no-go", txt)], txt.count("No-go"))
    NUM = re.compile(r"[−+-]?\d+(?:\.\d+)?")
    a, b = Counter(NUM.findall(before_txt)), Counter(NUM.findall(txt))
    print("numbers removed:", dict(a - b))
    print("numbers added:", dict(b - a))
    hl = [r.text[:50] for p in d2.paragraphs for r in p.runs if r.font.highlight_color == WD_COLOR_INDEX.YELLOW]
    print("highlighted author placeholders:", len(hl), hl)


if __name__ == "__main__":
    main()
