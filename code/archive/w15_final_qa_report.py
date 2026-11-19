"""FINAL_CONTENT_AND_CODE_QA.md: report of the final content, evidence-ledger and code quality-control pass (2026-11-14).

Stage 'pre' (before packaging): writes BMC_TARGETED_REPAIR_2026-11-14/FINAL_CONTENT_AND_CODE_QA.md from the
code-check results (outputs_validity/tables/qa_code_checks.json), the manuscript and the ledger. Section 8 refers to the
delivery folder, because an archive cannot contain its own checksum.
Stage 'post' (after w11_final_package.py): writes the same report with section 8 filled in (paths, sizes, SHA256 and
CRC test of the three LIGHT ZIPs) to BMC_FINAL_DELIVERY_2026-11-14/FINAL_CONTENT_AND_CODE_QA.md.
Usage: python w15_final_qa_report.py pre|post
"""
import hashlib
import json
import sys
import zipfile

import pandas as pd
from docx import Document

from v_common import ROOT, VTAB

B3 = ROOT.parent
REP = B3 / "BMC_TARGETED_REPAIR_2026-11-14"
STG = B3 / "BMC_FINAL_SUBMISSION_STAGING"
DEL = B3 / "BMC_FINAL_DELIVERY_2026-11-14"
LIGHT = DEL / "LIGHT_FOR_CHATGPT_REVIEW"


def body(zip_section):
    q = json.loads((VTAB / "qa_code_checks.json").read_text(encoding="utf-8"))
    d = Document(STG / "Manuscript_BMC_MIDM_FINAL.docx")
    sec = [(p.runs[0].text.strip(), len("".join(r.text for r in p.runs[1:]).split())) for p in d.paragraphs[6:10]]
    nb = sum(s[1] for s in sec)
    C = pd.read_csv(REP / "CLAIM_TO_EVIDENCE_REPAIRED.csv")
    changed = C[~C.final_qa_2026_11_14.str.startswith("reviewed")]
    rep = q["reproduction"]
    smoke = q["smoke_tests"]
    oof_ok = all(all(v for k, v in r.items() if isinstance(v, bool)) for r in q["oof_schema"])
    T = f"""# Final content, evidence-ledger and code QA: BMC MIDM feasibility manuscript (2026-11-14)

Scope: evidence-ledger annotations, README files, scientific consistency of the final manuscript, static and lightweight
runtime checks of the code, and the three light review ZIPs. No model was retrained, no experiment was rerun, no dataset
was added, no reported number was changed and no Word formatting was altered. Administrative items are out of scope.

## 1. Evidence-ledger corrections

Generator: `analysis_v3/validity/w14_repair_documents.py` (dictionaries `CURRENT`, `FINAL_QA`, `REPAIR_NOTES`,
`CLAIM_TEXT`; the export `BMC_TARGETED_REPAIR_2026-11-14/CLAIM_TO_EVIDENCE_REPAIRED.csv` is regenerated from it, so a
rerun cannot restore the old wording). A guard (`FORBIDDEN_CURRENT`) stops the generator if outdated phrases ("lower
bound", "is real", "about 0.04", "1.7x", "1.7-fold", "No descriptor version reports", "not re-read", "biased low")
reappear in any current field. Superseded wording is kept only in `CLAIM_TO_EVIDENCE_HISTORICAL_NOTES.csv`, labelled
historical (FULL package). Ledger: {len(C)} claims; status counts: {C.status_after_repair.value_counts().to_dict()}.

| Claim | Field | Before | After |
|---|---|---|---|
| CL-09 | notes | "CI reproduced within Monte-Carlo error; P1's absolute AUC is optimistic (CL-29)" | "{C.loc[C.claim_id == 'CL-09', 'notes'].iloc[0]}" |
| CL-29 | notes | "Selection optimism of P1 is real (locked > nested by about 0.04 AUC, CI excludes 0) …" | "{C.loc[C.claim_id == 'CL-29', 'notes'].iloc[0]}" |
| CL-29 | repair_2026_11_14 | quoted the removed phrase | "{C.loc[C.claim_id == 'CL-29', 'repair_2026_11_14'].iloc[0]}" |
| CL-36 | notes | "… voxel Dice is a lower bound" | "{C.loc[C.claim_id == 'CL-36', 'notes'].iloc[0]}" |
| CL-05 | validity_upgrade_update, repair | "No descriptor version reports 100/49"; "figure not re-read here" | three descriptor counts listed; published Table 1 count confirmed by the authors |
| CL-30 | validity_upgrade_update | "SD of dAUC 1.7x the fixed-prediction bootstrap" | larger SD (ratio 1.72) under a different design; not a calibrated correction |
| CL-40 | notes | "refit levels biased low" | refit AUCs lower on average, consistent with ~63% unique patients |
| CL-20, CL-21, CL-26 | notes | correction histories from 2026-11-13 | current statements only (histories in the historical file) |
| CL-27 | notes | — | Table 2 location rows relabelled |
| CL-28 | evidence, notes | — | `w07_figures_clean.py` added (Figures 3 and 6 redrawn) |
| CL-31 | notes | pointed to an internal file not in the package | points to `reference_verification_crossref.json`; reference 14 extension and reference 20 placeholder noted |
| CL-35 | claim | internal label "Exp A" | "Fully nested comparison" |
| CL-52 | notes | — | abstract wording that attributes 0.727 and 0.698 |
| audit CSVs (LIGHT) | `INTERNAL_VALIDITY_RESULTS`, `EXPERIMENT_EXECUTION_LOG` | "level biased low"; "abstract 347 words" (validity-revised manuscript) | `*_REPAIRED.csv` copies written by w14 (`repaired_csvs`): neutral wording; log extended with the later passes; originals kept in FULL |
| audit report | Phase 3 E caveat | "the refit levels are biased low" | "the refit AUCs are lower on average, consistent with ~63% unique patients per resample" |

All other claims were reviewed against the final manuscript; {len(C) - len(changed)} needed no change. Verified by
rerunning the generator (guard passed) and reading the exported rows.

## 2. Manuscript consistency (items A–P)

Source of edits: `analysis_v3/validity/w13_targeted_repair.py` (`ABSTRACT`, `EDITS`, `TABLE2_TIME`, `AVAIL_ADD`); every
edit is anchored on unique text and made inside the existing run. Final abstract: {nb} words without and {nb + len(sec)}
with the four structured labels (limit 350; the generator asserts ≤ 350 including labels).

| Item | Finding | Action |
|---|---|---|
| A primary vs post hoc separated | separate Results subsections; abstract labels the fully nested analysis as post hoc | abstract wording tightened (item B) |
| B 0.727 vs 0.698 | abstract listed both as "two sensitivity analyses" without attribution | Abstract: "re-selecting GBM settings within folds gave 0.727 and post hoc fully nested learner selection 0.698" |
| C optimism not quantified | Results, Discussion and Limitations already state that the 0.036 difference does not isolate optimism | none |
| D bootstrap-refit exploratory | consistent in Abstract, Methods, M5, Results, Limitations | abstract shortened to "exploratory refitting (different design) showed greater variability without calibrating these intervals" |
| E 350 provisional and conditional | consistent in Abstract, M5, Discussion, Conclusions | none |
| F centres inferred | consistent | none |
| G 99/50 vs 100/49 | consistent (storage signature 99/50 = revised preprint; identifier blocks 100/49 = published Table 1) | none |
| H 41-patient Tmax limitation | restriction, not correction; "did not change the fused model" | none |
| I ISLES 2018 | technical execution only; poor core agreement; no prognostic validation | none |
| J approximate-grid Dice | not described as a bound | none |
| K post-treatment information | Table 2 labelled the two location models "admission" although their atlas registration targets the follow-up DWI | cells changed to "admission CTP; atlas registered to follow-up DWI" |
| L Holm P = 0.057 | correctly "not significant after Holm correction" | none |
| M null results | "stayed null" and "added nothing" (within-centre and Munich-only increments) read as absence of effect | "stayed close to zero"; "did not improve discrimination" |
| N data availability | did not state what the shared files reproduce | sentence added after the repository placeholder; Software sentence changed from "regenerates every number" to "is intended to regenerate … statistical results can be recomputed from the shared predictions, whereas image-derived quantities require the original imaging datasets" |
| O references, figures, tables, supplementary citations | Figures 1–6, Tables 1–4, Additional files 1–5 and Tables S32, S34, S37–S42 point to the correct content; references 1–47 cited in range | none |
| P abstract length | 349 + 4 labels = 353 | shortened to {nb} + {len(sec)} = {nb + len(sec)} without removing information |

Numbers: the token comparison printed by w13 shows no change to any canonical value; the primary and fully nested
results, ISLES 2018 Dice and sensitivity are unchanged.

## 3. Python syntax, dependencies and smoke tests (executed)

Script: `analysis_v3/validity/qa_code_checks.py` → `outputs_validity/tables/qa_code_checks.json`.

| Check | Result |
|---|---|
| py_compile, analysis_v3 + validity + audit_final | {q['files_checked']} files, {len(q['compile_errors'])} errors |
| py_compile, historical copy FINAL_PACKAGE_BMC_MIDM | {q['historical_copy_files']} files, {len(q['compile_errors_historical_copy'])} errors |
| third-party imports | {', '.join(q['imports']['third_party'])} |
| imports not declared in requirements.txt | {q['imports']['undeclared_in_requirements'] or 'none'} |
| imports not installed | {q['imports']['not_installed'] or 'none'} |
| missing local modules | {q['imports']['missing_local_modules'] or 'none'} |
| hard-coded personal paths | {q['hardcoded_paths'] or 'none'} |
| outcome coding (poor = mRS ≥ 3; y = 1 poor) | {q['cohort']} |
| OOF schema and fold-manifest consistency | {len(q['oof_schema'])} OOF files; all checks passed: {oof_ok} |
| primary AUC recomputed vs table | P1 {rep['primary P1_clin_GBM']['recomputed']} vs {rep['primary P1_clin_GBM']['table']}; fusion {rep['primary F_late_P1_E']['recomputed']} vs {rep['primary F_late_P1_E']['table']}; ΔAUC {rep['primary dAUC F_late_P1_E - P1']['recomputed']} |
| fully nested AUC recomputed vs table | clinical {rep['fully nested A_clin']['recomputed']} vs {rep['fully nested A_clin']['table']}; fusion {rep['fully nested A_late_rec']['recomputed']} vs {rep['fully nested A_late_rec']['table']}; ΔAUC {rep['fully nested dAUC A_late_rec - A_clin']['recomputed']} |
| ISLES 2018 de-duplicated (ledger) | Dice {rep['ISLES 2018 de-duplicated Dice (mean of patients)']['recomputed']}, sensitivity {rep['ISLES 2018 de-duplicated sensitivity']['recomputed']} (n = {rep['ISLES 2018 de-duplicated Dice (mean of patients)']['n']}) |
| smoke tests | {smoke} |
| canonical outputs vs baseline SHA256 | {q['canonical_outputs']} |
| post hoc scripts writing into canonical folders (static) | {q['validity_writes_to_canonical_folders'] or 'none'} |
| frozen-model application (`apply_frozen_models.py`, models + 129-patient input) | ran; apparent AUCs 1.000 / 0.775 / 1.000 / 0.734 as in the model card |
| historical-script guards | `s11_manuscript.py`, `s30_package.py`, `w04_claims_and_log.py`, `w06_package.py` exit with a message unless `BRANCH3_ALLOW_HISTORICAL=1` (executed) |

Static review of methodology-relevant code: `s04_models_cv.py` fits median imputation, scaling and the inner grid search
inside each outer training fold (Pipeline + GridSearchCV on the training indices); late fusion is a fixed 0.5/0.5
average (confirmed on stored predictions); `y = 1` and `p_poor = predict_proba[:, 1]` throughout. No methodological
blocker was found.

Code changes in this pass (hygiene only, no algorithm changed):
- `analysis_v3/requirements.txt` (new): pinned direct dependencies, adding `requests` (used by `httpfile.py`) and
  `joblib`, and pinning `python-docx`; packaging now uses this file instead of the older audit-package copy.
- `validity/v_common.py`: optional overrides `BRANCH3_VOUT` (refuses the canonical folder) and `NATIVE_ISLES24_DIR`;
  defaults unchanged.
- Guards and "HISTORICAL" docstrings in `s11_manuscript.py`, `s11_manuscript_v3_full.py`, `s30_package.py`,
  `validity/w03_manuscript.py`, `validity/w04_claims_and_log.py`, `validity/w06_package.py`.
- `validity/w11_final_package.py`: LIGHT ZIP names `*_FINAL.zip`; adds this report; historical ledger notes to FULL only.
- `validity/w13_targeted_repair.py`, `validity/w14_repair_documents.py`: edits listed in sections 1–2.
- New: `validity/qa_code_checks.py`, `validity/w15_final_qa_report.py`.

Noted, not changed: `warnings.filterwarnings("ignore")` in modelling scripts suppresses convergence warnings, not
exceptions; `vX1_isles2018_benchmark.py` records per-slab exceptions as technical failures (0 occurred), by design.

## 4. Files tested versus not tested

Tested: compilation of all {q['files_checked']} scripts; imports; OOF and manifest CSVs ({len(q['oof_schema'])} runs);
reproduction of the headline numbers from stored predictions and ledgers; helper functions; frozen-model application;
historical guards; canonical-output integrity. Not tested (need the original imaging data or long computation):
end-to-end execution of s01–s30 and of the image-reading validity scripts (s02, s03, s13, s15, s19, s23, s25, vB, vD,
vX1, vX1b), model retraining, figure regeneration and the Word PDF export path on another machine.

## 5. Reproducibility limitations

Statistical results are reproducible from the light package; image-derived quantities can be checked at patient level
but need the original public images (ISLES'24 99 GB release; ISLES 2018 under its own terms). Full end-to-end
reproduction from raw images was performed when the analyses were run but was not repeated in this pass. The ledger
column `reproducibility_from_LIGHT` gives the level for every claim.

## 6. Remaining scientific blockers

None found in this pass. Scientific limitations stated in the manuscript remain: small sample, no external prognostic
validation, inferred centres without a subject-level list, Tmax recovery error in 41 patients, ISLES 2018 slab overlap
estimated from image similarity, selection optimism of the locked clinical GBM not quantifiable.

## 7. Administrative items intentionally deferred

Author e-mails/ORCID, ethics waiver, repository URL and DOI, competing interests, funding, CRediT contributions,
acknowledgements, AI-use statement wording, companion-study status (9 highlighted placeholders; `AUTHOR_TODO.md`), and
final data/model sharing decisions.

## 8. Final ZIPs

{zip_section}

This report does not declare the manuscript submission-ready: the administrative items above remain open and the
scientific limitations stand.
"""
    return T


def zip_section_post():
    sums = dict(reversed(l.split("  ")) for l in (LIGHT / "SHA256SUMS.txt").read_text().splitlines())
    rows = ["| ZIP | Files | Size (MB) | CRC test | SHA256 |", "|---|---|---|---|---|"]
    for z in sorted(LIGHT.glob("*_FINAL.zip")):
        h = hashlib.sha256(z.read_bytes()).hexdigest()
        assert h == sums[z.name]
        with zipfile.ZipFile(z) as zf:
            bad, n = zf.testzip(), len(zf.namelist())
        rows.append(f"| `{z}` | {n} | {z.stat().st_size / 1e6:.2f} | {'OK' if bad is None else bad} | `{h}` |")
    return "\n".join(rows)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "pre"
    if stage == "pre":
        (REP / "FINAL_CONTENT_AND_CODE_QA.md").write_text(body(
            "Paths, sizes, CRC tests and SHA256 checksums of the three LIGHT ZIPs are in the delivery-folder copy of this "
            "report (`BMC_FINAL_DELIVERY_2026-11-14/FINAL_CONTENT_AND_CODE_QA.md`) and in `SHA256SUMS.txt` / "
            "`ZIP_REPORT.txt`; an archive cannot contain its own checksum."), encoding="utf-8")
        print("pre report written")
    else:
        (DEL / "FINAL_CONTENT_AND_CODE_QA.md").write_text(body(zip_section_post()), encoding="utf-8")
        print("post report written")
