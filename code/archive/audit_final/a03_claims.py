"""Claim-to-evidence matrix (CLAIM_TO_EVIDENCE_FINAL.csv), generated from the result tables.

Every number in a claim is read from the result tables / OOF-derived files at run time (same conventions as
s11_manuscript.py), and each claim's key numbers are searched in the built manuscript (text + tables) so that the
matrix cannot drift from the manuscript: column in_manuscript_text = yes / no / n.a.
Verification statuses mirror the numerical ledger (a02): VERIFIED, VERIFIED_WITH_LIMITATION, SOURCE_MISSING.
Usage: python a03_claims.py [package_dir] [manuscript.docx]   (env BRANCH3_WS / BRANCH3_OUT as in config.py)"""
import csv, json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
from docx import Document

A = Path(__file__).resolve().parents[1]
WS = Path(os.environ.get("BRANCH3_WS", A.parent))
OUT = Path(os.environ.get("BRANCH3_OUT", A / "outputs")); TAB = OUT / "tables"; OOF = OUT / "oof"; DATA = OUT / "data"
PKG = Path(sys.argv[1]) if len(sys.argv) > 1 else WS / "BMC_MIDM_FEASIBILITY_FINAL_AUDIT_PACKAGE"
DOCX = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT / "Manuscript_BMC_MIDM.docx"
sys.path.insert(0, str(A))
import features as FEAT

doc = Document(str(DOCX))
CORPUS = "\n".join(p.text for p in doc.paragraphs) + "\n" + "\n".join(c.text for t in doc.tables for r in t.rows for c in r.cells)
CORPUS = CORPUS.replace("−", "-").replace("–", "-")

T = lambda f: pd.read_csv(TAB / f)
perf = T("performance_all_models_all.csv").set_index("model"); comp = T("paired_auc_comparisons_all.csv")
prec = T("precision_equivalence.csv").set_index("new"); holm = T("round4_primary_holm.csv")
wca = T("within_centre_auc.csv").set_index("model"); wcp = T("within_centre_paired.csv")
geo = T("geographic_validation_performance.csv"); mperf = T("performance_all_models_munich.csv").set_index("model")
mcomp = T("paired_auc_comparisons_munich.csv"); tlp = T("timeline_performance.csv"); tlc = T("timeline_paired.csv")
llc = T("location_lvo_paired.csv"); ss = T("design_sample_size.csv"); rly = T("design_riley.csv"); riley = T("sample_size_riley.csv")
cmix = pd.read_csv(TAB / "site_case_mix.csv", index_col=0); simp = T("site_imputation.csv").set_index("variable")
miss = T("missingness_probable_imputed.csv").set_index("variable"); site = json.load(open(TAB / "site_inference.json"))
nagr = T("native_vs_recovered_agreement.csv").set_index("feature"); agr = T("isles2018_feature_agreement.csv").set_index("feature")
qc = json.load(open(TAB / "ctp_qc_summary.json")); gap = T("overfit_gap.csv").set_index("model"); dnb = T("dca_delta_nb_all.csv")
t1 = T("table1_by_outcome.csv").set_index("variable")
nest_perf = T("performance_all_models_sens_nestedgbm.csv").set_index("model"); nest_comp = T("paired_auc_comparisons_sens_nestedgbm.csv")
sens = {k: T(f"paired_vs_P1_clin_GBM{k}.csv").set_index("model") for k in ["_sens_features", "_sens_missing", "_sens_tmaxcertain", "_5fold", "_sens_scalefree"]}
coh = pd.read_csv(DATA / "cohort_129.csv"); flow = pd.read_csv(DATA / "cohort_flow_149.csv"); isite = pd.read_csv(DATA / "inferred_site.csv")
ctpq = pd.read_csv(DATA / "ctp_features_v3_149.csv"); ctpq = ctpq[ctpq.subject_id.isin(coh.subject_id)]
locf = pd.read_csv(DATA / "location_features.csv"); locf = locf[locf.subject_id.isin(coh.subject_id)]
npar = pd.read_csv(OOF / "inner_best_params_sens_nestedgbm.csv"); npar = npar[npar.model == "P1_nested_GBM"]

f3 = lambda x: f"{x:.3f}"; f2 = lambda x: f"{x:.2f}"
sg = lambda x: ("0.000" if abs(x) < 5e-4 else f"{x:+.3f}")
P1, F, R1, E = "P1_clin_GBM", "F_late_P1_E", "R1_clin_LR4", "E_CTP_all"
def row(src, new, ref): return src[(src.new == new) & (src.reference == ref)].iloc[0]
def dd(src, new, ref): r = row(src, new, ref); return r.delta_auc, r.ci_lo, r.ci_hi
def dci(src, new, ref): d, lo, hi = dd(src, new, ref); return f"dAUC {sg(d)} (95% CI {sg(lo)} to {sg(hi)})"
def auc(m, src=perf): r = src.loc[m]; return f"{f3(r.auc_seed_mean)} (95% CI {f3(r.auc_ci_lo)}-{f3(r.auc_ci_hi)})"
def tl(s, m): r = tlp[(tlp.set == s) & (tlp.model == m)].iloc[0]; return r
SA, SB, H1S, H1D = "A: full cohort", "B: Munich", "H1: full cohort", "H1: registration Dice >= 0.80"
hp = lambda k: holm[holm.role.str.contains(k)].iloc[0]
h1, h2, h3 = hp("PRIMARY H1"), hp("PRIMARY H2"), hp("PRIMARY H3")
pF = prec.loc[F]; pV = prec.loc["F_late_P1_V"]
mun_n, zur_n = int(cmix.loc["Munich", "n"]), int(cmix.loc["Zurich", "n"]); mun_ev, zur_ev = int(cmix.loc["Munich", "poor"]), int(cmix.loc["Zurich", "poor"])
N_CEIL = int((ctpq.qc_Tmax_n_at_ceiling >= 2).sum()); N_MTT = int((ctpq.qc_MTT_n_at_ceiling >= 2).sum()); N_DEG = int(ctpq.qc_degenerate_norm.sum())
N_CERT = int(((ctpq.qc_Tmax_n_at_ceiling >= 2) & (~ctpq.qc_degenerate_norm.astype(bool))).sum())
r75 = riley[np.isclose(riley.anticipated_auc, 0.75)].iloc[0]; pmax75 = 129 * (0.9 - 1) * np.log(1 - r75.anticipated_R2cs / 0.9)
r80 = rly[np.isclose(rly.anticipated_auc, 0.80)].set_index("parameters")
ssc = ss.iloc[0]; ssd = ss[ss.comparison.str.startswith("Follow-up infarct volume added to admission")].iloc[0]
DEF_N = int(np.ceil(int(max(r80.loc[6, "n_minimum"], ssc["n_for_delta_0.05"])) / 10) * 10); DEF_EV = int(np.ceil(DEF_N * 44 / 129 / 5) * 5)
sens_d = [sens["_5fold"].loc[F].delta_auc, sens["_sens_tmaxcertain"].loc[F].delta_auc, sens["_sens_scalefree"].loc["F_late_P1_Esf"].delta_auc,
          sens["_sens_features"].loc["F_late_P1_EPCA"].delta_auc, sens["_sens_features"].loc["F_late_P1_Ephys"].delta_auc,
          sens["_sens_features"].loc["F_late_P1_CBV"].delta_auc, sens["_sens_missing"].loc["F_late_P1miss_E"].delta_auc]
gMZ = geo[(geo.direction == "Munich -> Zurich") & (geo.model == P1)].iloc[0]
lab_imp_z = min(simp.loc[v, "pct_imputed_Zurich"] for v in ["CRP", "Leucocytes", "INR", "Onset to door_min"])
lab_imp_m = max(simp.loc[v, "pct_imputed_Munich"] for v in ["CRP", "Leucocytes", "INR"])
nlock = int(((npar.n_estimators == 80) & (npar.max_depth == 3) & np.isclose(npar.learning_rate, 0.1) & np.isclose(npar.subsample, 0.7)).sum())
dn = row(nest_comp, "P1_nested_GBM", P1); dnF = row(nest_comp, "F_late_P1nested_E", "P1_nested_GBM"); dnL = row(nest_comp, F, P1)
sf_new = sens["_sens_scalefree"].loc["F_late_P1_Esf"]; sf_old = sens["_sens_features"].loc["F_late_P1_Esf"]
t1core, t1tmax = t1.loc["core_rcbf30_hypo_frac, median [IQR]"], t1.loc["tmax_gt6_frac, median [IQR]"]

rows = []
def add(cid, section, claim, etype, files, ledger, status, keys, notes=""):
    """keys: numeric strings that must appear in the manuscript (text or tables); None = not applicable."""
    if keys is None:
        present = "n.a."
    else:
        missing = [k for k in keys if k.replace("−", "-").replace("–", "-") not in CORPUS]
        present = "yes" if not missing else "no: " + "; ".join(missing)
    rows.append({"claim_id": cid, "section": section, "claim": claim, "evidence_type": etype, "evidence_files": files, "ledger_ids": ledger,
                 "status": status, "in_manuscript_text": present, "notes": notes})

add("CL-01", "Abstract/Methods", f"{len(coh)} patients with 90-day mRS analysed from the {len(flow)}-case ISLES'24 release; {int(coh.poor.sum())} poor (mRS 3-6), {int((coh.poor==0).sum())} good",
    "cohort files recomputed from the release clinical/outcome tables", "03_RESULTS_M1_M5/data/cohort_flow_149.csv; cohort_129.csv; source_tabular_ISLES24/; AUDIT_A", "COH-01..05", "VERIFIED",
    [f"{len(coh)} patients", f"{int(coh.poor.sum())} with modified Rankin"], f"Sole exclusion criterion: missing 90-day mRS ({len(flow)-len(coh)} cases)")
add("CL-02", "Methods M1", "Physical units of the z-normalised maps are recoverable as x = c(z-zmin)/(zmax-zmin) with c from the release pre-processing configuration (config_snapshot.json)",
    "code audit + stored QC tables + the configuration file itself", "s02_ctp_features.py; config.py; source_tabular_ISLES24/config_snapshot.json; AUDIT_B; ctp_qc_summary.json", "M1-01..04",
    "VERIFIED_WITH_LIMITATION", None, f"Exact only when the clip ceiling is reached; Tmax ceiling absent in {129-N_CEIL}/129 (reported)")
add("CL-03", "Results M1", f"Central volume theorem ratio median {qc['cvt_ratio_median_of_medians']:.3f}; ISLES 2018 simulation median ICC {agr.ICC_true_vs_recovered.median():.3f}; native-map median ICC {nagr.icc31.median():.3f} with {int((nagr.icc31>=0.9).sum())}/{len(nagr)} features >= 0.90",
    "stored tables (imaging needed to regenerate)", "ctp_qc_summary.json; isles2018_feature_agreement.csv; native_vs_recovered_agreement.csv", "M1-01..04", "VERIFIED_WITH_LIMITATION",
    [f"{qc['cvt_ratio_median_of_medians']:.3f}", f"{nagr.icc31.median():.3f}", f"{int((nagr.icc31>=0.9).sum())}/{len(nagr)}"], "CVT does not test Tmax; simulation ICC = 1 for ratio features is guaranteed; feature-level, not voxelwise")
add("CL-04", "Results M1", f"Tmax clip ceiling present in {N_CEIL}/129, MTT {N_MTT}/129, CBF/CBV all; {N_DEG} degenerate CBF maps; Tmax-certain n = {N_CERT}",
    "recomputed from ctp_features_v3_149.csv qc columns", "03_RESULTS_M1_M5/data/ctp_features_v3_149.csv; AUDIT_B", "M1-13..16 (revised ledger)", "VERIFIED",
    [f"{N_CEIL}/129", f"{N_MTT}/129", f"n = {N_CERT}"], "Reported in Results M1 and Limitations")
add("CL-05", "Results M1", f"Centres inferred from map quantisation signature: {site['cluster_sizes']['quantised']}/{site['cluster_sizes']['float']} in the release, {mun_n}/{zur_n} analysed ({mun_ev} vs {zur_ev} poor); consistent with the descriptor's 100/50 of 150",
    "recomputed from inferred_site.csv + cohort; descriptor fetched (arXiv 2408.10966 v2; Zenodo 17652035)", "inferred_site.csv; native_acquisition_fingerprints.csv; site_inference.json; AUDIT_A", "COH-06..11",
    "VERIFIED_WITH_LIMITATION", [f"{site['cluster_sizes']['quantised']}/{site['cluster_sizes']['float']}", f"{mun_ev}/{mun_n} vs {zur_ev}/{zur_n}"],
    "Labels assigned by size matching, not independently verified; sub-stroke0008 assigned differently by ID block (100/49)")
add("CL-06", "Results M1", f"Centres differ: poor outcome {cmix.loc['Munich','poor_pct']:.0f}% vs {cmix.loc['Zurich','poor_pct']:.0f}%, median age {cmix.loc['Munich','age_median']:.0f} vs {cmix.loc['Zurich','age_median']:.0f}, release imputation >= {lab_imp_z:.0f}% (Zurich) vs <= {lab_imp_m:.0f}% (Munich labs); overall CRP {miss.loc['CRP','pct']:.0f}%, INR {miss.loc['INR','pct']:.0f}%, onset-to-door {miss.loc['Onset to door_min','pct']:.0f}% imputed",
    "recomputed from cohort + site files", "site_case_mix.csv; site_imputation.csv; missingness_probable_imputed.csv; AUDIT_A A2", "COH-09, COH-10, M1-10..12", "VERIFIED",
    [f"{cmix.loc['Munich','poor_pct']:.0f}% vs {cmix.loc['Zurich','poor_pct']:.0f}%", f"{cmix.loc['Munich','age_median']:.0f} vs {cmix.loc['Zurich','age_median']:.0f}", f"CRP ({miss.loc['CRP','pct']:.0f}%)"],
    "Imputation flag = value equal to the stored training median")
add("CL-07", "Results M1", f"Riley criteria support about {pmax75:.1f} parameters at AUC 0.75 (two to three parameters overall)", "formula recomputed from sample_size_riley.csv R2cs",
    "sample_size_riley.csv; AUDIT_C C6", "M1-09, DIS-03", "VERIFIED", [f"{pmax75:.1f} parameters"], "R2cs derived from the C-statistic by simulation")
add("CL-08", "Methods M2", "Nested CV: 5 seeds x stratified 10-fold outer, inner 5-fold grid search, shared fold manifest, preprocessing inside training folds, fixed 0.5/0.5 late fusion",
    "code audit + on-disk manifest comparison (all sensitivity runs incl. _sens_scalefree/_sens_nestedgbm share fold_manifest.csv)", "s04_models_cv.py; s16_combine.py; fold_manifest*.csv; AUDIT_D", "n/a", "VERIFIED", None, "No train/test contamination found")
add("CL-09", "Results M3", f"Clinical GBM P1 AUC {auc(P1)}; R1 {auc(R1)}", "recomputed from oof_long_all.csv (exact) + fresh bootstrap",
    "02_NUMERICAL_EVIDENCE/oof/oof_long_all.csv; performance_all_models_all.csv", "M3-01..03, T2-*", "VERIFIED", [f3(perf.loc[P1].auc_seed_mean), f3(perf.loc[R1].auc_seed_mean)],
    "CI reproduced within Monte-Carlo error; P1's absolute AUC is optimistic (CL-29)")
add("CL-10", "Results M3 (primary)", f"Adding CTP to P1: {dci(comp, F, P1)}; 90% CI {sg(pF.ci90_lo)} to {sg(pF.ci90_hi)}; P(gain>0.05) = {pF['post_p_gt0.05']:.2f}; MDD {pF.mdd_80pct_power:.3f}",
    "recomputed (exact point estimate; fresh bootstrap and Dirichlet posterior)", "paired_auc_comparisons_all.csv; precision_equivalence.csv; AUDIT_C C1, C4", "M3-07..12", "VERIFIED",
    [sg(row(comp, F, P1).delta_auc), f"{sg(pF.ci90_lo)} to {sg(pF.ci90_hi)}", f"{pF['post_p_gt0.05']:.2f}", f"{pF.mdd_80pct_power:.3f}"],
    f"Equivalence within +/-0.05 NOT established (upper 90% bound {sg(pF.ci90_hi)} > 0.05); the manuscript says so explicitly")
add("CL-11", "Results M3", f"Increment near zero with R1 ({dci(comp,'F_late_R1_E',R1)}), recalibrated P1 ({dci(comp,'F_late_P1recal_E','P1_recal')}), native-unit features ({dci(comp,'F_late_P1_Enat',P1)}), CTP location (H1 {dci(llc,'F_loc',P1) if 'set' not in llc.columns else dci(llc[llc.set==H1S],'F_loc',P1)}; Holm P = {h1.p_holm:.2f}) and across eight sensitivity analyses (dAUC {sg(min(sens_d))} to {sg(max(sens_d))})",
    "recomputed from stored OOF files (scale-free term from the corrected run _sens_scalefree)", "paired_vs_P1_clin_GBM_sens_*.csv; location_lvo_paired.csv; round4_primary_holm.csv", "M3-13..17", "VERIFIED",
    [sg(row(comp,'F_late_R1_E',R1).delta_auc), sg(row(comp,'F_late_P1_Enat',P1).delta_auc), f"{sg(min(sens_d))} to {sg(max(sens_d))}"], "7 of 8 sensitivity deltas recomputed; CIs within Monte-Carlo error")
add("CL-12", "Results M3", f"Absolute volumes: equivalence within +/-0.05 shown (90% CI {sg(pV.ci90_lo)} to {sg(pV.ci90_hi)}) and gain >= 0.03 excluded (95% upper {sg(row(comp,'F_late_P1_V',P1).ci_hi)})",
    "recomputed", "precision_equivalence.csv; AUDIT_C C4", "M3-13-P1+V, M3-14-P1+V, M3-15", "VERIFIED", [f"{sg(pV.ci90_lo)} to {sg(pV.ci90_hi)}", sg(row(comp,'F_late_P1_V',P1).ci_hi)],
    "Exclusion uses the 95% upper bound (stricter than TOST); applies to volumes only")
add("CL-13", "Results M3 (H2)", f"Within occlusion-mask patients (127/129) dAUC {sg(h2.delta_auc)} ({sg(h2.ci_lo)} to {sg(h2.ci_hi)}); hypothesis-generating; Holm P = {h2.p_holm:.2f}",
    "recomputed from oof_long_lvo.csv", "location_lvo_paired.csv; round4_primary_holm.csv", "M3-18, M3-19", "VERIFIED", [sg(h2.delta_auc), f"{h2.p_holm:.2f}"], "Exploratory status preserved")
nb = dnb[(dnb.new == F) & (dnb.reference == P1) & np.isclose(dnb.threshold, 0.35)].delta_nb.iloc[0]
add("CL-14", "Results M3", f"P1 overconfident (slope {f2(perf.loc[P1].pooled_slope)}, training AUC {gap.loc[P1,'train_auc']:.2f}, gap {gap.loc[P1,'gap']:.2f}); fusion slope {f2(perf.loc[F].pooled_slope)} (underconfident), Brier {f3(perf.loc[P1].pooled_brier)} -> {f3(perf.loc[F].pooled_brier)}, ICI {f3(perf.loc[P1].pooled_ici)} -> {f3(perf.loc[F].pooled_ici)}, dNB {sg(nb)} at 0.35",
    "recomputed on seed-averaged probabilities", "performance_all_models_all.csv; overfit_gap.csv; dca_delta_nb_all.csv; AUDIT_C C3", "M3-20..26", "VERIFIED",
    [f"slope {f2(perf.loc[P1].pooled_slope)}", f2(perf.loc[F].pooled_slope), f3(perf.loc[P1].pooled_brier), f3(perf.loc[F].pooled_brier), f3(perf.loc[P1].pooled_ici), f3(perf.loc[F].pooled_ici)],
    "Pooled (seed-averaged) convention throughout; DCA does not show patient benefit (stated)")
rA, rD = tl(SA, R1), tl(SA, "R1_DWI"); hd = row(tlc[tlc.set == SA], "R1_DWI", R1)
add("CL-15", "Results post-treatment (H3)", f"Follow-up infarct volume added to R1: AUC {f3(rA.auc)} -> {f3(rD.auc)}; dAUC {sg(hd.delta_auc)} (95% CI {sg(hd.ci_lo)} to {sg(hd.ci_hi)}); bootstrap P = {h3.p_bootstrap:.3f}; Holm P = {h3.p_holm:.3f} (not significant at alpha 0.05)",
    "recomputed (exact point estimates; fresh bootstrap P about 0.03)", "timeline_paired.csv; round4_primary_holm.csv; AUDIT_C C5", "H3-01..06", "VERIFIED",
    [f3(rA.auc), f3(rD.auc), sg(hd.delta_auc), f"{h3.p_holm:.3f}"], "Manuscript states non-significance after Holm; Monte-Carlo SE of raw P about 0.004")
mB = tl(SB, R1); n24 = tl(SB, "R1_N24"); n24d = tl(SB, "R1_N24_DWI"); ctp_t = row(tlc[tlc.set == SB], "R1_N24_DWI_plus_E", "R1_N24_DWI")
add("CL-16", "Results post-treatment", f"Munich (n = {int(mB.n)}, {int(mB.events)} events): AUC {f3(mB.auc)} (admission) -> {f3(n24.auc)} (24-h NIHSS) -> {f3(n24d.auc)} (+ infarct volume); CTP lowers AUC at every time point (after follow-up imaging dAUC {sg(ctp_t.delta_auc)})",
    "recomputed from oof_long_munich_timeline.csv", "timeline_performance.csv; timeline_paired.csv", "H3-09..13", "VERIFIED", [f3(mB.auc), f3(n24.auc), f3(n24d.auc), sg(ctp_t.delta_auc)],
    "Updated prognosis, not admission-time prediction (stated); 24-h NIHSS 95% CI includes 0")
lf = row(llc[llc.set == H1S], "R1_DWI_Loc", "R1_DWI"); ld = row(llc[llc.set == H1D], "R1_DWI_Loc", "R1_DWI"); n80 = int((locf.reg_dice >= 0.8).sum())
add("CL-17", "Results post-treatment", f"Infarct location adds to volume in the full cohort ({sg(lf.delta_auc)}, {sg(lf.ci_lo)} to {sg(lf.ci_hi)}) but not in the {n80} patients with Dice >= 0.80 ({sg(ld.delta_auc)}, {sg(ld.ci_lo)} to {sg(ld.ci_hi)})",
    "recomputed", "location_lvo_paired.csv; location_features.csv", "H3-16..18", "VERIFIED", [sg(lf.delta_auc), f"{n80} patients", sg(ld.delta_auc)], "Registration quality dependent")
add("CL-18", "Methods M3 / H1", "CTP location features use affine registration whose target is the follow-up DWI; H1 is a retrospective anatomical analysis, not a deployable admission-time model",
    "code audit", "s25_atlas_location.py:111-118; AUDIT_D item 7", "n/a", "VERIFIED", None, "Stated in Methods M3")
wc = row(wcp, F, P1)
add("CL-19", "Results M4", f"Within-centre AUC of P1 {wca.loc[P1,'within_centre_auc']:.3f} vs pooled {wca.loc[P1,'auc_pooled_seedmean']:.3f}; within-centre CTP increment {sg(wc.delta_within)} ({sg(wc.ci_lo)} to {sg(wc.ci_hi)}); centre indicator AUC {wca.loc['Centre indicator alone','auc_pooled_seedmean']:.2f}",
    "recomputed with independent within-centre concordance", "within_centre_auc.csv; within_centre_paired.csv; AUDIT_C C7", "M4-01..03, COH-12, DIS-01", "VERIFIED",
    [f"{wca.loc[P1,'auc_pooled_seedmean']:.3f}", f"{wca.loc[P1,'within_centre_auc']:.3f}", sg(wc.delta_within)], "Zurich contributes 10% of pairs")
mP1, mP2 = mperf.loc[P1], mperf.loc["P2_clin_EN"]; md = row(mcomp, F, P1)
add("CL-20", "Results M4", f"Munich-only nested CV (n = {mun_n}): P1 AUC {auc(P1, mperf)}; P2 (clinical elastic net) {auc('P2_clin_EN', mperf)} with calibration slope {f2(mP2.pooled_slope)} (seed-averaged probabilities); CTP increment {dci(mcomp, F, P1)}",
    "recomputed from oof_long_munich.csv", "performance_all_models_munich.csv; paired_auc_comparisons_munich.csv", "M4-04..07", "VERIFIED",
    [f3(mP1.auc_seed_mean), f3(mP2.auc_seed_mean), f2(mP2.pooled_slope), sg(md.delta_auc)],
    "Corrected 2026-11-13: an earlier version of this matrix stated P2 0.70 (slope 1.02) and dAUC -0.004, which did not match the tables")
add("CL-21", "Results M4", f"Munich -> Zurich: P1 AUC {f3(gMZ.auc)} (95% CI {f3(gMZ.auc_lo)}-{f3(gMZ.auc_hi)}) with {int(gMZ.events)} events in {int(gMZ.n)} patients - statistically inconclusive, not an external validation",
    "stored table (transfer predictions not stored as OOF)", "geographic_validation_performance.csv; s20_geographic.py", "M4-08, M4-09", "VERIFIED_WITH_LIMITATION",
    [f3(gMZ.auc), f"{f3(gMZ.auc_lo)}-{f3(gMZ.auc_hi)}", f"{int(gMZ.events)} events"],
    "Corrected 2026-11-13: an earlier version stated AUC 0.517 (that is F_late_P1_E, not P1). Wording: inconclusive; evidence neither of failure nor success")
add("CL-22", "Results M5", f"Detecting dAUC 0.05 for CTP needs about {int(ssc['n_for_delta_0.05'])} patients ({int(ssc['events_for_delta_0.05'])} events); 0.03 needs {int(ssc['n_for_delta_0.03'])}; observed DWI increment detectable with {int(ssd['n_for_delta_observed'])}",
    "formula verified; recomputed with fresh bootstrap SE (small differences expected)", "design_sample_size.csv; AUDIT_C C6", "M5-01..04, T4a-*", "VERIFIED_WITH_LIMITATION",
    [f"{int(ssc['n_for_delta_0.05'])} patients", f"{int(ssc['n_for_delta_0.03'])}", f"{int(ssd['n_for_delta_observed'])} patients"], "Post hoc; assumes SE ~ 1/sqrt(n), same models, event rate and correlation")
add("CL-23", "Results M5", f"Riley minimum n for development: {int(r80.loc[6,'n_minimum'])} (p <= 6, set by intercept precision) to {int(r80.loc[10,'n_minimum'])} (p = 10), {int(r80.loc[20,'n_minimum'])} (p = 20) at AUC 0.80",
    "recomputed from formulae", "design_riley.csv; sample_size_riley.csv; AUDIT_C C6", "M5-05, M5-06, T4b-*", "VERIFIED", [f"{int(r80.loc[6,'n_minimum'])}-{int(r80.loc[10,'n_minimum'])} patients"],
    f"{int(r80.loc[6,'n_minimum'])} is criterion (iii), not the 6-parameter shrinkage criterion; explained in Results M5")
add("CL-24", "Abstract/Discussion/Conclusions", f"A definitive study of the pre-treatment CTP question needs about {DEF_N} patients (about {DEF_EV} events)", f"derived: ceil(max({int(r80.loc[6,'n_minimum'])}, {int(ssc['n_for_delta_0.05'])})/10)*10",
    "s11 DEF_N; AUDIT_C C6", "M5-07, M5-08", "VERIFIED_WITH_LIMITATION", [f"about {DEF_N} patients", f"{DEF_EV} events"], "Does not cover dAUC 0.03, more parameters, post-treatment comparisons or external validation (stated)")
add("CL-25", "Table 3", "Go/no-go decisions per research direction", "hand-written proposals in s28 built on verified estimates", "go_nogo.csv; s28_design_parameters.py", "T3-01..03", "VERIFIED_WITH_LIMITATION", None,
    "Not prospectively registered progression criteria (stated); 'go' rows annotated: 24-h NIHSS CI includes 0, infarct volume not significant after Holm")
add("CL-26", "Table 1", f"Cohort characteristics by outcome with Fisher / Mann-Whitney P; core rCBF<30% and Tmax>6 s extents are percentages of covered tissue (medians {t1core['all'].split(' ')[0]}% and {t1tmax['all'].split(' ')[0]}%), premorbid mRS P printed as <0.001",
    "independently reconstructed from the raw clinical table (AUDIT_A A2); s08 multiplies the two fractions by 100", "table1_by_outcome.csv; s08_tables.py:28-29; AUDIT_A", "T1-*", "VERIFIED",
    ["% of covered tissue", t1core['all'].replace("–", "-"), t1tmax['all'].replace("–", "-"), "<0.001"], "Label corrected 2026-11-13 from 'fraction of tissue' to '% of covered tissue' (values unchanged)")
add("CL-27", "Table 2", "AUC, within-centre AUC, calibration slope and Brier for 16 key models", "all AUCs recomputed exactly; slope/Brier recomputed on seed-averaged probabilities",
    "performance_all_models_all.csv; within_centre_auc.csv; timeline_performance.csv", "T2-*", "VERIFIED", None, "Brier column pooled (seed-averaged) for consistency with the slope")
add("CL-28", "Figures 1-6, S1-S7", "Figures plot the same result tables (no hand-entered values); Fig. S4 now includes the corrected scale-free run and the nested-GBM reference",
    "figure-script audit", "s09_figures.py; s22_new_figures.py; s29_framework_figure.py", "FIG-1..6", "VERIFIED_WITH_LIMITATION", None, "N labels in Fig 1 hard-coded but verified")
add("CL-29", "Methods M3 / Results M3 / Limitations", f"P1 configuration (80 trees, depth 3, lr 0.1, subsample 0.7) locked from the companion study, selected by non-nested CV on the same cohort. Nested re-selection inside each training fold ({len(npar)} folds, grid of 24 configurations, log-loss): clinical AUC {f3(nest_perf.loc['P1_nested_GBM'].auc_seed_mean)} vs {f3(nest_perf.loc[P1].auc_seed_mean)} locked ({dci(nest_comp,'P1_nested_GBM',P1)}); locked configuration chosen in {nlock}/{len(npar)} folds; CTP increment vs nested reference {dci(nest_comp,'F_late_P1nested_E','P1_nested_GBM')} vs {dci(nest_comp,F,P1)} against locked P1 in the same run",
    "new sensitivity analysis (s06 nestedgbm), recomputed from oof_long_sens_nestedgbm.csv", "performance_all_models_sens_nestedgbm.csv; paired_auc_comparisons_sens_nestedgbm.csv; inner_best_params_sens_nestedgbm.csv; s04_models_cv.py GBM_GRID", "M3-28..31", "VERIFIED",
    [f3(nest_perf.loc['P1_nested_GBM'].auc_seed_mean), sg(dn.delta_auc), f"{nlock} of {len(npar)}", sg(dnF.delta_auc), sg(dnL.delta_auc)],
    "Selection optimism of P1 is real (locked > nested by about 0.04 AUC, CI excludes 0) and is NOT asserted to be conservative; the difference also reflects the log-loss criterion; the CTP conclusion is unchanged")
add("CL-30", "Methods M2", "Bootstrap CIs resample stored OOF predictions without refitting; DeLong tests the 5-model ensemble, not the primary estimand", "code audit", "s05_evaluate.py; stats_utils.py; AUDIT_C C1, C2", "n/a", "VERIFIED", None, "Both limitations stated in Methods M2 / Limitations")
add("CL-31", "References", "47 references verified against Crossref / PubMed / arXiv / jmlr.org (2026-11-11)", "external verification", "analysis_v3/outputs/tables/reference_verification_crossref.json", "n/a", "VERIFIED", ["47. "], "Report in the project's internal folder (Reference_verification.xlsx)")
add("CL-32", "Declarations", "Funding, CRediT contributions, repository URL/DOI, ethics waiver number", "author-supplied", "n/a", "n/a", "SOURCE_MISSING", ["[Funding statement]", "[Repository URL and DOI]"], "Placeholders highlighted; not fabricated. Listed in the action ledger")
add("CL-33", "Methods M3 / Additional file 2 S1, S11", f"Scale-free CTP feature set = {len(FEAT.SCALE_FREE)} features independent of the absolute Tmax scale (rcbf_in_hypo, which depends on the Tmax > 6 s mask, removed 2026-11-13); corrected sensitivity analysis: {dci(pd.DataFrame([{'new':'F_late_P1_Esf','reference':P1,'delta_auc':sf_new.delta_auc,'ci_lo':sf_new.ci_lo,'ci_hi':sf_new.ci_hi}]),'F_late_P1_Esf',P1)} (superseded 31-feature run: {sg(sf_old.delta_auc)}, {sg(sf_old.ci_lo)} to {sg(sf_old.ci_hi)})",
    "rerun of the affected models only (s06 scalefree), same folds", "features.py SCALE_FREE; paired_vs_P1_clin_GBM_sens_scalefree.csv; performance_all_models_sens_scalefree.csv", "M3-17", "VERIFIED", None,
    "Manuscript reports the eight-analysis range (CL-11), which uses the corrected run; the superseded rows are excluded from Additional file 2 and kept in the stored tables for provenance")

cols = ["claim_id", "section", "claim", "evidence_type", "evidence_files", "ledger_ids", "status", "in_manuscript_text", "notes"]
out = PKG / "02_NUMERICAL_EVIDENCE" / "CLAIM_TO_EVIDENCE_FINAL.csv"; out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_ALL); w.writeheader(); w.writerows(rows)
st = pd.Series([r["status"] for r in rows]).value_counts().to_dict()
unsync = [(r["claim_id"], r["in_manuscript_text"]) for r in rows if r["in_manuscript_text"].startswith("no")]
print("claims:", len(rows), st, "| not synchronised:", unsync, "->", out)
