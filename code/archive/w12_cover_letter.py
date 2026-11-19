"""Submission cover letter: adds one sentence on the post hoc analyses, aligns wording with the final manuscript and
marks author-completed items as highlighted placeholders. Formatting is kept (text replaced inside existing runs)."""
from docx import Document
from docx.enum.text import WD_COLOR_INDEX

from v_common import ROOT

SRC = ROOT.parent / "BMC_MIDM_FEASIBILITY_FINAL_AUDIT_PACKAGE" / "01_MANUSCRIPT" / "Cover_letter_SCIENTIFIC_REVISED.docx"
DST = ROOT.parent / "BMC_FINAL_SUBMISSION_STAGING" / "Cover_letter_BMC_MIDM_FINAL.docx"

SUB = {
    4: [("yet their small size, pre-processing and undocumented centre structure make it unclear what such studies can establish.",
         "yet their small size, pre-processing and unlabelled centre structure limit what such studies can show."),
        ("post hoc go/no-go proposals", "conditional proposals")],
    5: [("(consistent with the dataset descriptor, but not independently verified)",
         "(consistent with the published centre counts, which differ by one patient between descriptor versions, but not "
         "verified at the level of individual patients)"),
        ("The study ends with explicit sample-size estimates and data requirements for a definitive, centre-aware study.",
         "Post hoc analyses showed that the size of the CT perfusion increment depends on how both models are tuned (fully "
         "nested ΔAUC +0.054, 95% CI −0.006 to +0.121); an exploratory bootstrap-refit analysis under a different resampling "
         "design showed greater variability of this increment but does not provide a calibrated correction of the intervals. "
         "A technical benchmark on ISLES 2018 showed that the perfusion pipeline executes on external data after unit "
         "harmonisation, but that its fixed-threshold core agrees poorly with the expert DWI core (Dice 0.21); no external "
         "prognostic validation was possible. The study ends with data requirements and a provisional sample-size target "
         "for a constrained pre-treatment comparison in a definitive, centre-aware study.")],
    6: [("the analysis code, fold manifests, out-of-fold predictions and result tables will be made available at [Repository URL and DOI].",
         "the analysis code, fold assignments, out-of-fold predictions, result tables and the final fitted models will be made "
         "available at ")],
}
PLACEHOLDER = {0: "[AUTHORS TO COMPLETE: date]", 6: "[AUTHORS TO COMPLETE: repository URL and DOI]",
               8: "[AUTHORS TO COMPLETE: suggested reviewers, if required by the journal]"}


def main():
    d = Document(SRC)
    P = d.paragraphs
    for i, subs in SUB.items():
        t = P[i].text
        for old, new in subs:
            assert t.count(old) == 1, (i, old[:50])
            t = t.replace(old, new)
        assert len(P[i].runs) >= 1
        P[i].runs[0].text = t
        for r in P[i].runs[1:]:
            r._r.getparent().remove(r._r)
    for i, ph in PLACEHOLDER.items():
        if i in (0, 8):
            assert P[i].text.startswith("["), (i, P[i].text)
            P[i].runs[0].text = ph
            for r in P[i].runs[1:]:
                r._r.getparent().remove(r._r)
            P[i].runs[0].font.highlight_color = WD_COLOR_INDEX.YELLOW
        else:
            r = P[i].add_run(ph); r.font.highlight_color = WD_COLOR_INDEX.YELLOW
            P[i].add_run(".")
    d.save(DST)
    print("\n".join(p.text for p in Document(DST).paragraphs if p.text.strip())[:200], "... saved", DST.name)


if __name__ == "__main__":
    main()
