"""Content-only update of the manuscript (Word formatting untouched: text is replaced inside existing runs and new
paragraphs are deep copies of neighbouring paragraphs of the same style). Source: the scientifically revised manuscript
in the read-only baseline snapshot. Output: BMC_FEASIBILITY_VALIDITY_UPGRADE/Manuscript_BMC_MIDM_VALIDITY_REVISED.docx
and MANUSCRIPT_CHANGE_LOG.md. Every number below is taken from outputs_validity/tables (see CLAIM_TO_EVIDENCE_FINAL_UPDATED.csv).

HISTORICAL (2026-11-14): its output is the frozen input of w09_final_manuscript.py; re-running it is not needed to
rebuild the submission files (see README.md).
"""
import os as _os
import sys as _sys
if _os.environ.get("BRANCH3_ALLOW_HISTORICAL") != "1":
    _sys.exit("Historical script (validity-revised manuscript, input of w09); set BRANCH3_ALLOW_HISTORICAL=1 to run it anyway.")
import copy
import re
import docx
from v_common import ROOT

U = ROOT.parent / "BMC_FEASIBILITY_VALIDITY_UPGRADE"
SRC = U / "00_BASELINE_SNAPSHOT" / "manuscript" / "Manuscript_BMC_MIDM_SCIENTIFIC_REVISED.docx"
OUT = U / "Manuscript_BMC_MIDM_VALIDITY_REVISED.docx"
LOG = []


def find(d, start):
    hits = [p for p in d.paragraphs if p.text.startswith(start)]
    assert len(hits) == 1, (start, len(hits))
    return hits[0]


def replace(p, old, new):
    for r in p.runs:
        if old in r.text:
            r.text = r.text.replace(old, new, 1)
            LOG.append(f"- REPLACED in «{p.text[:60]}…»:\n  - old: {old}\n  - new: {new}")
            return
    raise AssertionError(f"not found in a single run: {old[:80]}")


def insert_after(anchor, template, text):
    el = copy.deepcopy(template._p)
    for r in el.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r")[1:]:
        r.getparent().remove(r)
    anchor._p.addnext(el)
    newp = docx.text.paragraph.Paragraph(el, anchor._parent)
    newp.runs[0].text = text
    LOG.append(f"- INSERTED after «{anchor.text[:60]}…» ({template.style.name}):\n  - {text}")
    return newp


M_HEAD = "Post hoc validity analyses and external technical component benchmarking"
M1 = ("After the primary results were known, five post hoc analyses addressed remaining internal-validity concerns; they are "
      "sensitivity analyses, not prespecified primary analyses (Additional file 5). (A) Consistent fully nested comparison: for "
      "the clinical (22 variables), CTP (53 recovered-unit or native-unit features) and joint feature sets alike, the learner "
      "family (elastic net or gradient boosting) and its hyperparameters were selected jointly by inner 5-fold log-loss within each "
      "outer training fold of the canonical fold manifest (verified identical), followed by the same equal-weight late fusion. "
      "(B) Native-unit verification: per patient, recovered and native Tmax maps were compared voxel-wise on a common grid "
      "(absolute error; Dice and disagreement of the Tmax >4, >6, >8 and >10 s masks), and core, Tmax >6 s and mismatch volumes "
      "were compared in mL, stratified by Tmax-recovery quality control. (C) A patient-level provenance ledger combined seven "
      "provenance signatures; M4 was repeated with the ambiguous assignment reversed and with the ambiguous patient excluded. "
      "(D) Admission-time registration: the H1 atlas registration was repeated with the admission non-contrast CT as the only "
      "target (intracranial cavity of −20 to 100 HU enclosed by the skull), so that no post-treatment image enters admission-time "
      "features. (E) Bootstrap-refit: with a budget fixed in advance (100 patient-level resamples, each with one 10-fold CV in which "
      "duplicated patients stay in the same fold), the primary comparison was refitted on every resample to quantify the "
      "model-refitting variability that the fixed-prediction bootstrap omits.")
M2 = ("External technical component benchmarking used only datasets whose reference labels match an output of the pipeline "
      "(compatibility matrix in Additional file 5). The frozen CTP feature extractor and core definition (ipsilateral Tmax >6 s "
      "with rCBF <30%) were applied without modification or learning to the ISLES 2018 training set [23]: 94 CTP slabs from 63 "
      "patients, RAPID perfusion maps and an expert-delineated infarct core on DWI acquired within 3 h of CTP. The patient was the "
      "unit of analysis (voxel counts pooled over a patient's slabs, patient-level bootstrap CIs), and maps were analysed as "
      "distributed and after a label-free median rescaling of CBF and CBV. ISLES 2018 has no outcome data, so no prognostic metric "
      "was computed. UniToBrain (no Tmax map; one 50.8 GB archive), the Johns Hopkins head-CT masks (compatible intracranial "
      "target, but no programmatic access), CPAISD and AISD (no matching pipeline output) were not analysed, and no independent "
      "cohort with CTP and 90-day mRS was accessible.")
R_HEAD1 = "Post hoc validity analyses"
R1 = ("Under one consistent nested procedure, the clinical model reached an AUC of 0.698 (95% CI 0.607–0.783), CTP alone 0.681 "
      "(95% CI 0.596–0.763; gradient boosting selected in 48 of 50 folds) and their late fusion 0.752 (95% CI 0.666–0.828): ΔAUC "
      "+0.054 (95% CI −0.006 to +0.121; P = 0.08), and +0.052 (95% CI −0.017 to +0.119) within inferred centres. This clinical "
      "reference was 0.065 lower than the locked P1 (95% CI −0.101 to −0.032); because the two tuning procedures differ, this "
      "difference is not a pure estimate of selection optimism. With native-unit CTP features the increment was +0.023 (95% CI "
      "−0.033 to +0.086). Refitting the whole procedure on bootstrap resamples gave a standard deviation of ΔAUC 1.7 times that of "
      "the fixed-prediction bootstrap (0.047 vs 0.027; 95% interval width 0.173 vs 0.107), so the primary confidence intervals "
      "understate uncertainty.")
R2 = ("In the 41 patients without a Tmax ceiling, recovered Tmax was inflated (median recovered/native ratio 1.048, IQR "
      "1.017–1.147, versus 1.000 in the 85 Tmax-certain patients), and Tmax >6 s volume was overestimated by a median of 6.2 mL "
      "(IQR 2.9–27.9) versus −0.1 mL (IQR −1.7 to 1.8); core volume was unaffected (median difference 0.0 mL). Replacing recovered "
      "by native-unit features in the primary fused model nevertheless changed the AUC by only +0.003 (95% CI −0.011 to +0.018), "
      "and by +0.006 (95% CI −0.029 to +0.045) in the 44 patients without certain recovery. The provenance ledger identified one "
      "ambiguous patient (float storage like the smaller cluster, identifier inside the larger cluster's block); reassigning it "
      "(100/49) or excluding it left the within-centre CTP increment at +0.005 and +0.009, and the Munich→Zurich estimates remained "
      "uninformative (5–6 events). Registration to the admission CT performed as well as the canonical DWI-based registration "
      "(median Dice with the CT intracranial mask 0.92 vs 0.91; 5 vs 21 registrations below 0.80), the regional location features "
      "agreed closely (ICC 0.92–0.99), and the admission-time H1 increment was −0.001 (95% CI −0.037 to +0.038), or −0.013 "
      "(95% CI −0.044 to +0.019) after excluding the 5 poor registrations.")
R_HEAD2 = "External technical component benchmarking"
R3 = ("ISLES 2018 (63 patients, 94 slabs; technical evaluation only): as distributed, CBF and CBV were on a different absolute "
      "scale from ISLES'24 (median brain values ≈210 and ≈30 in the distributed units; 86% and 91% of brain voxels above the frozen "
      "clip limits), so the frozen absolute tissue limits removed most tissue (feature completeness 95.4%; side agreement with the "
      "DWI lesion 86%); the extractor is therefore not unit-transportable without harmonisation. After label-free median rescaling "
      "there were no technical failures, all 53 features were finite, the detected ipsilateral side agreed with the DWI lesion in "
      "99% of slabs, and Tmax-threshold volumes were monotone in every slab (a sanity check only). Against the expert DWI core, the "
      "frozen CTP core had a patient-level Dice of 0.21 (95% CI 0.18–0.24), sensitivity 0.15 (95% CI 0.13–0.18) and precision 0.46 "
      "(95% CI 0.40–0.52), underestimated volume by 33 mL on average (Bland–Altman limits −116 to +49 mL, with larger "
      "underestimation of larger lesions) and ranked patients moderately (Spearman 0.62, 95% CI 0.40–0.76); results were similar "
      "across acquisition protocols (Fig. S8). These results describe technical operation and core agreement on external data; "
      "they do not address the prognostic transportability of the models.")
D1 = ("The post hoc analyses refine rather than overturn these conclusions. A single consistent nested procedure lowered the "
      "clinical reference and, because the CTP branch then mostly used gradient boosting, produced a larger increment (+0.054) whose "
      "interval still included zero; the size of the CTP increment therefore depends on how both arms are tuned, which argues for "
      "prespecifying the learner and tuning objective of both arms in a definitive study, not for a positive conclusion here. The "
      "Tmax-recovery error is real in 41 patients but did not change the fused model, and admission-time registration removed the "
      "dependence of H1 on a post-treatment image without changing its result. Externally, the frozen feature extractor ran "
      "without failure on another vendor-processed dataset once units were harmonised, but its absolute limits did not transfer as "
      "distributed and its fixed-threshold core agreed only modestly with an early DWI core [22, 23]. None of these analyses is an "
      "external prognostic validation.")
AF5 = ("Additional file 5 (.xlsx, .pdf). Supplementary Tables S21–S35 and Figure S8. Post hoc validity analyses (consistent nested "
       "comparison, native-unit verification, provenance ledger, admission-time registration, bootstrap-refit) and external "
       "technical component benchmarking on ISLES 2018, with the external dataset compatibility matrix.")


def main():
    d = docx.Document(SRC)
    # abstract (no added length: limit 350 words)
    replace(find(d, "Results: "), "(0.727 when its configuration was re-selected within folds)",
            "(0.698–0.727 when configurations were re-selected within folds)")
    # methods
    replace(find(d, "This is a methodological framework"),
            "the dataset descriptor reports 100 training cases from Munich and 50 from Zurich, of which 149 are in the public release",
            "the first version of the dataset descriptor reports 100 training cases from Munich and 50 from Zurich, and the revised "
            "version 99 and 50 for the 149 released cases")
    pc = find(d, "Centres. Because centres")
    replace(pc, "and the 100/50 split reported by the providers.",
            "and the split reported by the providers (100/50 in the first descriptor version, 99/50 in the revised version). "
            "A post hoc patient-level ledger of seven provenance signatures is given in Additional file 5.")
    replace(find(d, "All models were evaluated with nested"),
            "the intervals reflect patient sampling only and omit model-refitting variability.",
            "the intervals reflect patient sampling only and omit model-refitting variability (quantified post hoc; see below).")
    replace(find(d, "Three further hypotheses"), "the lesion content of the DWI enters only the post-treatment location models.",
            "the lesion content of the DWI enters only the post-treatment location models. A post hoc variant registered the "
            "template to the admission non-contrast CT instead (see below).")
    m5_text = find(d, "Two different sample sizes were derived")
    m5_head = find(d, "M5 – Design outputs") if any(p.text.startswith("M5 – Design outputs") for p in d.paragraphs) else \
        [p for p in d.paragraphs if p.style.name == "Heading 2" and p.text.startswith("M5")][0]
    h = insert_after(m5_text, m5_head, M_HEAD)
    p = insert_after(h, m5_text, M1)
    insert_after(p, m5_text, M2)
    # results
    replace(find(d, "The quantisation signature split"),
            "consistent with the reported centre sizes of 100 and 50 (one of the 150 described cases is absent from the release)",
            "identical to the 99/50 split of the revised dataset descriptor (the first version described 150 cases, 100/50)")
    r5 = find(d, "Detecting a CTP increment of 0.05 AUC")
    r5_head = [p for p in d.paragraphs if p.style.name == "Heading 2" and p.text.startswith("Design parameters and go/no-go")][0]
    h = insert_after(r5, r5_head, R_HEAD1)
    p = insert_after(h, r5, R1)
    p = insert_after(p, r5, R2)
    h = insert_after(p, r5_head, R_HEAD2)
    insert_after(h, r5, R3)
    # discussion
    insert_after(find(d, "Positioning this work as a feasibility study"), find(d, "Positioning this work as a feasibility study"), D1)
    lim = find(d, "The sample is small and there is no independent external cohort.")
    replace(lim, "The sample is small and there is no independent external cohort.",
            "The sample is small and there is no independent external cohort: external benchmarking was technical only (ISLES 2018 "
            "has no outcome data), and requests for cohorts with CTP and 90-day mRS have been drafted but not granted.")
    replace(lim, "one patient is assigned differently by the two provenance signatures;",
            "one patient is assigned differently by the two provenance signatures (reassigning or excluding it did not change the "
            "conclusions);")
    replace(lim, "this was handled by a sensitivity subset, not corrected, and unit recovery was validated at feature level only.",
            "this was handled by a sensitivity subset, not corrected; a post hoc voxel-level comparison confirmed a median 4.8% "
            "Tmax inflation in these patients without a detectable effect on the fused model.")
    replace(lim, "and omit model-refitting variability;",
            "and omit model-refitting variability, which a bootstrap-refit experiment showed to increase the standard deviation "
            "of ΔAUC about 1.7-fold, so the reported intervals are too narrow and the sample sizes optimistic;")
    replace(lim, "Atlas registration was affine and targeted the follow-up DWI,",
            "Atlas registration was affine and, in the primary H1 analysis, targeted the follow-up DWI (an admission-CT "
            "registration gave the same result),")
    replace(find(d, "Availability of data and materials"), "ISLES 2018 is available from the ISLES challenge website",
            "ISLES 2018 was distributed through the SMIR platform linked from the ISLES challenge website")
    af4 = find(d, "Additional file 4 (.docx)")
    insert_after(af4, af4, AF5)
    d.save(OUT)
    # abstract word count check
    abs_words = sum(len(re.findall(r"\S+", p.text)) for p in d.paragraphs[:12]
                    if re.match(r"(Background|Methods|Results|Conclusions): ", p.text))
    LOG.insert(0, f"# Manuscript change log (content only)\n\nSource: {SRC.name} (baseline snapshot). Output: {OUT.name}.\n"
                  f"Abstract length after edit: {abs_words} words (limit 350).\n")
    (U / "MANUSCRIPT_CHANGE_LOG.md").write_text("\n".join(LOG), encoding="utf-8")
    print("abstract words", abs_words, "; changes", len(LOG) - 1)


if __name__ == "__main__":
    main()

