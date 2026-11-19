"""Builds the BMC Medical Informatics and Decision Making manuscript (.docx).
Every number in the text is read from outputs/tables at build time.

HISTORICAL (2026-11-14): builds a superseded full-length manuscript version (see README.md)."""
import os as _os
import sys as _sys
if _os.environ.get("BRANCH3_ALLOW_HISTORICAL") != "1":
    _sys.exit("Historical script (superseded manuscript version); set BRANCH3_ALLOW_HISTORICAL=1 to run it anyway.")
import json
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Cm, Inches
from config import TAB, FIG, OUT

T = lambda f: pd.read_csv(TAB / f)
# primary + additional models share one fold manifest and one bootstrap; *_all is a superset of the primary tables
perf = T("performance_all_models_all.csv").set_index("model")
comp = T("paired_auc_comparisons_all.csv")
dnb = T("dca_delta_nb_all.csv")
rc = T("reclassification_all.csv")
prec = T("precision_equivalence.csv").set_index("new")
wca = T("within_centre_auc.csv").set_index("model")
wcp = T("within_centre_paired.csv")
geo = T("geographic_validation_performance.csv")
geop = T("geographic_validation_paired.csv")
cmix = pd.read_csv(TAB / "site_case_mix.csv", index_col=0)
simp = T("site_imputation.csv").set_index("variable")
site = json.load(open(TAB / "site_inference.json"))
nval = json.load(open(TAB / "native_validity.json"))
nagr = T("native_vs_recovered_agreement.csv").set_index("feature")
nvol = pd.read_csv(TAB / "native_volumes_summary.csv", index_col=0)
sub = T("subgroup_incremental_value.csv")
mperf = T("performance_all_models_munich.csv").set_index("model")
mcomp = T("paired_auc_comparisons_munich.csv")
tlp = T("timeline_performance.csv"); tlc = T("timeline_paired.csv")
llp = T("location_lvo_performance.csv"); llc = T("location_lvo_paired.csv")
holm = T("round4_primary_holm.csv")
from config import DATA
locf = pd.read_csv(DATA / "location_features.csv")
locf = locf[locf.subject_id.isin(pd.read_csv(DATA / "cohort_129.csv").subject_id)]


def tl(setname, m):
    r = tlp[(tlp.set == setname) & (tlp.model == m)].iloc[0]
    return f"{r.auc:.3f} (95% CI {r.auc_lo:.3f}–{r.auc_hi:.3f})"
def tlr(setname, m): return tlp[(tlp.set == setname) & (tlp.model == m)].iloc[0]
def tld(setname, new, ref, src=None):
    src = tlc if src is None else src
    r = src[(src.set == setname) & (src.new == new) & (src.reference == ref)].iloc[0]
    return f"ΔAUC {r.delta_auc:+.3f} (95% CI {r.ci_lo:+.3f} to {r.ci_hi:+.3f}; P = {pv(r.p_bootstrap)})"
def ll(setname, m):
    r = llp[(llp.set == setname) & (llp.model == m)].iloc[0]
    return f"{r.auc:.3f} (95% CI {r.auc_lo:.3f}–{r.auc_hi:.3f})"
def hp(key): return holm[holm.role.str.contains(key)].iloc[0]
SA, SB, SBC = "A: full cohort", "B: Munich", "B: Munich, complete NIHSS 24 h"
H1S, H1D, H2S = "H1: full cohort", "H1: registration Dice >= 0.80", "H2: LVO population"
qc = json.load(open(TAB / "ctp_qc_summary.json"))
sim = T("isles2018_unit_recovery_summary.csv").set_index("channel")
agr = T("isles2018_feature_agreement.csv").set_index("feature")
miss = T("missingness_probable_imputed.csv").set_index("variable")
ivx = T("included_vs_excluded.csv").set_index("variable")
riley = T("sample_size_riley.csv")
ordc = T("ordinal_c_index.csv").set_index("model")
po = pd.read_csv(TAB / "ordinal_proportional_odds.csv", index_col=0).iloc[:, 0]
gap = T("overfit_gap.csv").set_index("model")
stab = T("coef_rank_stability.csv").set_index("model")
tstab = pd.read_csv(TAB / "treeshap_rank_stability.csv", index_col=0)
shp = T("treeshap_P1_clin_GBM.csv")
sens = {k: T(f"paired_vs_P1_clin_GBM{k}.csv").set_index("model") for k in ["_sens_features", "_sens_missing", "_sens_tmaxcertain", "_5fold"]}
sensp = {k: T(f"performance_all_models{k}.csv").set_index("model") for k in ["_sens_features", "_sens_missing", "_sens_tmaxcertain", "_5fold"]}
t1 = T("table1_by_outcome.csv")
cut = T("cumulative_cutpoint_auc.csv").set_index("cut")
thr_audit = json.load(open(TAB / "audit_thrive_legacy.json"))


def f3(x): return f"{x:.3f}"
def f2(x): return f"{x:.2f}"
def pv(p): return "<0.001" if p < 0.001 else f"{p:.3f}"
def sg3(x): return f"{x:+.3f}".replace("-0.000", "0.000").replace("+0.000", "0.000")
def peq(p):return "P < 0.001" if p < 0.001 else f"P = {p:.3f}"
def auc(m, src=perf): r = src.loc[m]; return f"{f3(r.auc_seed_mean)} (95% CI {f3(r.auc_ci_lo)}–{f3(r.auc_ci_hi)})"
def cmp(new, ref):
    r = comp[(comp.new == new) & (comp.reference == ref)].iloc[0]
    return f"ΔAUC {r.delta_auc:+.3f} (95% CI {r.ci_lo:+.3f} to {r.ci_hi:+.3f}; P = {pv(r.p_bootstrap)})"
def scmp(tag, m):
    r = sens[tag].loc[m]; return f"ΔAUC {r.delta_auc:+.3f} ({r.ci_lo:+.3f} to {r.ci_hi:+.3f})"
def dnbs(new, ref, t):
    r = dnb[(dnb.new == new) & (dnb.reference == ref) & (np.isclose(dnb.threshold, t))].iloc[0]
    return f"{r.delta_nb:+.3f} (95% CI {r.ci_lo:+.3f} to {r.ci_hi:+.3f})"
def nri(new, ref, typ):
    r = rc[(rc.new == new) & (rc.reference == ref) & (rc.nri_type.str.startswith(typ))].iloc[0]; return r
def mcmp(new, ref):
    r = mcomp[(mcomp.new == new) & (mcomp.reference == ref)].iloc[0]
    return f"ΔAUC {r.delta_auc:+.3f} (95% CI {r.ci_lo:+.3f} to {r.ci_hi:+.3f})"
def wcmp(new, ref):
    r = wcp[(wcp.new == new) & (wcp.reference == ref)].iloc[0]
    return f"Δ {r.delta_within:+.3f} (95% CI {r.ci_lo:+.3f} to {r.ci_hi:+.3f})"
def gperf(direction, m):
    r = geo[(geo.direction == direction) & (geo.model == m)].iloc[0]
    return f"{f3(r.auc)} (95% CI {f3(r.auc_lo)}–{f3(r.auc_hi)})"
def gcmp(direction, new, ref):
    r = geop[(geop.direction == direction) & (geop.new == new) & (geop.reference == ref)].iloc[0]
    return f"ΔAUC {r.delta_auc:+.3f} (95% CI {r.ci_lo:+.3f} to {r.ci_hi:+.3f})"
def sg(name):
    q = sub[sub.subgroup == name]; yes = q[q.level.str.endswith("yes")].iloc[0]; no = q[q.level.str.endswith("no")].iloc[0]
    return (f"{yes.delta:+.3f} ({yes.ci_lo:+.3f} to {yes.ci_hi:+.3f}) vs {no.delta:+.3f} ({no.ci_lo:+.3f} to {no.ci_hi:+.3f}); "
            f"{peq(yes.p_interaction)} for interaction")
def vol(v, s="50%"): return nvol.loc[v, s]

P1, F, E, TT = "P1_clin_GBM", "F_late_P1_E", "E_CTP_all", "T_thresholds"
r75 = riley[np.isclose(riley.anticipated_auc, 0.75)].iloc[0]
lvo_n = qc["lvo_mask_available"]; lvo_agree = round(qc["ipsi_agrees_with_lvo"] * lvo_n)
nri_cf = nri(F, P1, "category-free"); nri_cat = nri(F, P1, "categorical")
nri_th = nri(P1, "THRIVE", "category-free")
pF = prec.loc[F]
R1, PR = "R1_clin_LR4", "P1_recal"
zur_n, mun_n = int(cmix.loc["Zurich", "n"]), int(cmix.loc["Munich", "n"])
zur_ev, mun_ev = int(cmix.loc["Zurich", "poor"]), int(cmix.loc["Munich", "poor"])
lab_imp_z = min(simp.loc[v, "pct_imputed_Zurich"] for v in ["CRP", "Leucocytes", "INR", "Onset to door_min"])
lab_imp_m = max(simp.loc[v, "pct_imputed_Munich"] for v in ["CRP", "Leucocytes", "INR"])
MZ = "Munich -> Zurich"; ZM = "Zurich -> Munich"

doc = Document()
st = doc.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(11)
st.paragraph_format.line_spacing = 1.5; st.paragraph_format.space_after = Pt(4)
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.5)


def H(t, l=1): doc.add_heading(t, level=l)
def Pp(t, bold_lead=None):
    p = doc.add_paragraph()
    if bold_lead:
        p.add_run(bold_lead).bold = True
    p.add_run(t); return p


def table(df, caption, widths=None, font=8):
    doc.add_paragraph().add_run(caption).bold = True
    tb = doc.add_table(rows=1, cols=len(df.columns)); tb.style = "Table Grid"
    for i, c in enumerate(df.columns):
        cell = tb.rows[0].cells[i]; cell.text = str(c)
        for r in cell.paragraphs[0].runs: r.bold = True; r.font.size = Pt(font)
    for _, row in df.iterrows():
        cells = tb.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = "" if pd.isna(v) else str(v)
            for r in cells[i].paragraphs[0].runs: r.font.size = Pt(font)
    doc.add_paragraph()


# ------------------------------------------------------------------ title page
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("Pre-treatment CT perfusion versus the early post-treatment course for 90-day prognosis after endovascular "
          "thrombectomy: a channel-wise, time-resolved and centre-aware study of the public ISLES'24 dataset").bold = True
Pp("Tran Bao Hoang¹, Kiet Tuan Nguyen¹, Bao Thien Nguyen¹* [author list and order to be confirmed by the team]")
Pp("¹ Institute of Intelligent and Interactive Technologies (3i Institute), College of Technology and Design, University of "
   "Economics Ho Chi Minh City (UEH), Ho Chi Minh City, Vietnam")
Pp("* Corresponding author: baont@ueh.edu.vn")
Pp("Article type: Research article (prediction model development and internal validation; TRIPOD+AI).")

# ------------------------------------------------------------------ abstract
H("Abstract")
Pp(f"Perfusion CT (CTP) selects patients for thrombectomy, but whether it adds prognostic information once reperfusion "
   f"is achieved, which channel carries it, and how it compares with information gained after treatment is unknown.",
   "Background: ")
Pp(f"We analysed 129 of 149 patients in the public ISLES'24 training set with a 90-day modified Rankin Scale (mRS) score "
   f"(44 poor outcomes, mRS 3–6). Physical units of the per-patient-normalised perfusion maps were recovered analytically "
   f"and checked against the native-unit maps of the original release. We extracted 53 prespecified perfusion features and "
   f"absolute volumes (mL). Nested repeated cross-validation (5 seeds × 10-fold) compared clinical models, single-channel "
   f"and all-channel CTP models, a classical-threshold model and clinical–CTP fusion, with an equivalence analysis "
   f"(±0.05 AUC) and centre-aware analyses (centres inferred from data provenance). A second analysis plan, written before analysis, "
   f"tested time-resolved models (24-h NIHSS, follow-up DWI infarct volume), atlas-based lesion location and an "
   f"occlusion population.", "Methods: ")
h3 = hp("PRIMARY H3")
Pp(f"Recovered and native-unit features agreed closely (median ICC {nagr.icc31.median():.3f}). The clinical model achieved "
   f"an AUC of {auc(P1)} and clinical + CTP fusion {f3(perf.loc[F].auc_seed_mean)} (ΔAUC "
   f"{comp[(comp.new==F)&(comp.reference==P1)].delta_auc.iloc[0]:+.3f}, 95% CI "
   f"{comp[(comp.new==F)&(comp.reference==P1)].ci_lo.iloc[0]:+.3f} to {comp[(comp.new==F)&(comp.reference==P1)].ci_hi.iloc[0]:+.3f}); "
   f"P(gain >0.05) was {pF['post_p_gt0.05']:.2f}. CTP-only models, classical thresholds, absolute volumes and lesion "
   f"location discriminated poorly (AUC {perf.loc['V_volumes'].auc_seed_mean:.2f}–{perf.loc['B_CBV'].auc_seed_mean:.2f}; CBV "
   f"best). Results held within Munich ({mcmp(F, P1)}) and across centres, which differed in outcome rate "
   f"({mun_ev}/{mun_n} vs {zur_ev}/{zur_n}) and data completeness. By contrast, post-treatment information improved "
   f"prognosis: in Munich the AUC rose from {tlr(SB,'R1_clin_LR4').auc:.2f} at admission to {tlr(SB,'R1_N24').auc:.2f} with "
   f"24-h NIHSS and {tlr(SB,'R1_N24_DWI').auc:.2f} with DWI infarct volume, and in the full cohort infarct volume added "
   f"{h3.delta_auc:+.3f} (95% CI {h3.ci_lo:+.3f} to {h3.ci_hi:+.3f}; Holm-adjusted P = {h3.p_holm:.3f}). Pre-treatment CTP "
   f"never added discrimination at any time point.", "Results: ")
Pp("After thrombectomy, prognostic information came from routine clinical data and from the early post-treatment "
   "course, not from pre-treatment CTP; larger CTP gains cannot be excluded. Public derivatives require unit "
   "verification and centre-aware evaluation before reuse.", "Conclusions: ")
Pp("acute ischaemic stroke; thrombectomy; CT perfusion; prognosis; machine learning; calibration; decision curve analysis; "
   "ISLES 2024; TRIPOD+AI; reproducibility", "Keywords: ")

# ------------------------------------------------------------------ background
H("Background")
Pp("Endovascular thrombectomy (EVT) is standard care for large-vessel occlusion stroke, yet roughly half of treated "
   "patients remain dependent or die at 90 days despite technically successful reperfusion [1, 2]. Early, accurate "
   "prognosis supports family counselling, rehabilitation planning and the design of adjunctive-therapy trials. Simple "
   "clinical scores such as THRIVE [5, 6] and SPAN-100 [7] were derived in thrombolysis or early-device cohorts and "
   "showed only moderate discrimination (AUC ≈0.61–0.73) in contemporary thrombectomy registries [8, 46].")
Pp("CT perfusion (CTP) quantifies the ischaemic core (relative cerebral blood flow, rCBF <30%) and hypoperfused tissue "
   "(Tmax >6 s) and underpins patient selection in the extended window [9–15]. Its role in prognosis after reperfusion "
   "is less clear. In HERMES, core volume but not mismatch volume was associated with functional outcome [9]. The "
   "core–outcome association weakens when reperfusion is fast [16]. Machine-learning studies that added CTP to clinical "
   "and conventional imaging data reported small or non-significant gains [17–19, 22, 23]. No study has compared the four "
   "standard perfusion channels (CBF, CBV, MTT, Tmax) on the same cohort and pipeline, so it remains unknown which "
   "channel, if any, carries prognostic information beyond clinical data.")
Pp("The public ISLES'24 dataset [3, 4] combines acute multimodal CT, including perfusion maps, with clinical variables "
   "and 90-day mRS in patients treated with endovascular reperfusion, most with successful (mTICI 2c/3) reperfusion. In "
   "the pre-processed form widely redistributed for outcome research, the perfusion maps were z-normalised per patient. "
   "That normalisation removes the physical units (seconds, mL/100 g) on which clinical thresholds rely. Features "
   "computed naively on such maps are physically meaningless, a pitfall we encountered in earlier internal analyses of "
   "this cohort.")
Pp("We therefore aimed (i) to recover and verify the physical units of the normalised ISLES'24 perfusion maps; (ii) to "
   "rank the four perfusion channels by prognostic information in a systematic ablation; (iii) to quantify the "
   "incremental discrimination, calibration and clinical utility of CTP over a leakage-free clinical model and over "
   "classical perfusion thresholds, with an explicit precision (equivalence) analysis; (iv) to test the robustness of "
   "the conclusion to the choice of clinical reference model, to native-unit and absolute-volume CTP measures, and to "
   "centre effects; (v) to place pre-treatment CTP on the timeline of information that becomes available after "
   "treatment (24-h neurological status, follow-up infarct volume and location); and (vi) to report all analyses "
   "under TRIPOD+AI [24] with fully reproducible code.")

# ------------------------------------------------------------------ methods
H("Methods")
H("Study design, data source and reporting", 2)
Pp(f"This is a prognostic prediction-model development and internal-validation study, a secondary analysis of the "
   f"public ISLES'24 training set (149 cases in the public release; the dataset descriptor reports 150 training cases, "
   f"100 from Klinikum rechts der Isar, Technical University of Munich, and 50 from University Hospital Zurich [3]). "
   f"Adults underwent non-contrast CT, CT angiography "
   f"and CTP before endovascular reperfusion therapy. Perfusion maps (CBF, CBV, MTT, Tmax) were generated by the "
   f"providers with FDA-cleared software (icobrain cva) and co-registered to NCCT space [3, 4]. We used the "
   f"pre-processed release resampled to a 64×128×128 grid for the prespecified primary analysis, because this is the "
   f"form widely redistributed for outcome research. For verification and additional analyses we also read the "
   f"native-unit perfusion maps, vessel-occlusion masks, follow-up DWI lesion masks and voxel sizes of the original "
   f"release (one file per subject in a public mirror of the Zenodo record [3, 51]); only the needed image columns "
   f"were downloaded. Neither release labels the centre of each subject (see Centre inference below). According to the providers, laboratory values carry "
   f"±5% anonymisation noise [3]. Reporting follows TRIPOD+AI [24] (Additional file 1), with CLAIM 2024 items for the "
   f"imaging pipeline [25]; PROBAST+AI domains [49] informed the design. Model development reused the cohort and clinical predictor set of a companion clinical-only "
   f"study (Branch 2, [50]); the overlap is disclosed in the Declarations. All numbers reported here come from a new, "
   f"single locked pipeline.")
H("Participants and outcome", 2)
Pp(f"Patients with a recorded 90-day mRS were included. The primary outcome was poor functional outcome (mRS 3–6, event "
   f"= 1) versus good outcome (mRS 0–2). All probabilities refer to P(poor). Ordinal 90-day mRS (0–6) was analysed as a "
   f"sensitivity outcome. We compared included and excluded patients with standardised mean differences (SMD).")
H("Clinical predictors", 2)
Pp(f"Twenty-two pre-procedural variables were used. Demographics: age, sex. Stroke circumstances: wake-up, in-house, "
   f"referral. Risk factors and medication: atrial fibrillation, hypertension, diabetes, hyperlipidaemia, anticoagulants, "
   f"lipid-lowering drugs, antiplatelets. Severity and function: admission NIHSS, premorbid mRS, admission mRS. "
   f"Laboratory: glucose, leucocytes, CRP, INR. Workflow times: onset-to-door, alert-to-door, door-to-imaging. Four "
   f"intra-procedural times (door-to-groin, door-to-first-series, door-to-recanalisation, procedure duration) were "
   f"excluded because they are unavailable at the time of prediction. The release stores standardised continuous "
   f"variables; we back-transformed them to physical units using the stored scaler parameters, which we read with a "
   f"restricted unpickler that executes no code. Values equal to the stored training median were classified as probable "
   f"median imputations by the data release (raw missingness indicators were not distributed; Additional file 2). We "
   f"recomputed THRIVE (age, NIHSS 0/2/4 points for ≤10/11–20/≥21, hypertension, diabetes, atrial fibrillation) [5] and "
   f"SPAN-100 (age + NIHSS) [7] from the raw values.")
H("Recovery of physical units of the perfusion maps", 2)
Pp("Each stored map equals z = (x − μ)/σ, where x is the clinical map after clipping to [0, c] (c = 100 mL/100 g/min "
   "for CBF, 10 mL/100 g for CBV, 30 s for MTT and Tmax) and μ, σ are unknown subject-level constants. Because "
   "background is x = 0 and the clip ceiling is reached in high-perfusion voxels, x = c·(z − z_min)/(z_max − z_min). "
   "This is exact when the ceiling is present. Relative quantities (rCBF, rCBV, rMTT) are invariant to the scale factor "
   "in any case. We verified the recovery in two independent ways. First, with the central volume theorem, "
   "MTT = 60·CBV/CBF [44], which must hold voxel-wise only if all three scales are correct. Second, with a simulation "
   "on the 94 ISLES 2018 training cases [42, 43]: we reproduced the public pre-processing (clip, trilinear resampling, "
   "per-subject z-normalisation), applied the recovery, and compared recovered with true maps and features "
   "(ICC(A,1)). Channel order was confirmed by the same identity. The left–right axis was confirmed by mirror symmetry. "
   "Third, after the primary analysis was locked, we recomputed all 53 features from the native-unit maps of the "
   "original release (clipped to the same [0, c] ranges, block-averaged to ≈1.9 × 1.9 × 2 mm) and compared them with "
   "the recovered features (ICC(3,1), Spearman ρ).")
H("Perfusion feature extraction", 2)
Pp("Within brain tissue (excluding vessels: CBV ≥8 mL/100 g or CBF ≥99 mL/100 g/min), the midline was located by "
   "maximising mirror symmetry. The ipsilateral hemisphere was the one with the larger Tmax >6 s fraction, and we "
   "cross-checked it against the provided vessel-occlusion mask. CBF, CBV and MTT were expressed relative to the "
   "contralateral median. Because voxel size is not available in the pre-processed release, volumes were expressed as "
   "fractions of covered tissue. We prespecified 53 features in five groups:")
Pp("CBF (14): rCBF <20/30/38% core within ipsilateral Tmax >6 s tissue; rCBF <30% in the whole ipsilateral hemisphere; "
   "ipsilateral rCBF ratio; mean rCBF in hypoperfused tissue; distribution statistics of ipsilateral rCBF.")
Pp("CBV (11): ipsilateral rCBV ratio; rCBV <0.6 fraction; CBV index in hypoperfused tissue [45]; distribution statistics.")
Pp("MTT (11): ipsilateral rMTT ratio; rMTT >145% fraction; rMTT in hypoperfused tissue; distribution statistics.")
Pp("Tmax (15): Tmax >4/6/8/10 s fractions; hypoperfusion intensity ratio (HIR, Tmax >10 s/Tmax >6 s) [12]; "
   "ipsilateral-minus-contralateral median Tmax; distribution statistics.")
Pp("Mismatch (2): log mismatch ratio; mismatch fraction.")
Pp("Distribution statistics were the mean, SD, skewness, kurtosis and the 10th, 25th, 75th and 90th percentiles "
   "(Additional file 2).")
Pp("From the native-unit maps and voxel sizes we also computed absolute volumes as used in clinical practice: ischaemic "
   "core (rCBF <30% within ipsilateral Tmax >6 s tissue), hypoperfused tissue (Tmax >6 s) and mismatch volume, in mL. "
   "As a construct-validity check we correlated them with the follow-up DWI final-infarct volume provided with the release.")
H("Models", 2)
Pp("All models were fixed before evaluation:")
Pp("P1: clinical gradient-boosting machine on the 22 predictors, with the companion study's locked configuration "
   "(80 trees, depth 3, learning rate 0.1, subsample 0.7).")
Pp("P2: clinical elastic-net logistic regression.")
Pp("A–D: single-channel elastic-net models (CBF, CBV, MTT, Tmax).")
Pp("E: all-channel elastic net (53 features).")
Pp("T: classical-threshold logistic model with core rCBF <30%, Tmax >6 s, log mismatch ratio and HIR.")
Pp("F: multimodal equal-weight late fusion, P_F = 0.5·P_P1 + 0.5·P_E, with no trainable fusion parameters. "
   "Prespecified alternatives were early-fusion elastic net (clinical + all CTP), GBM on clinical + threshold features, "
   "and P1 + T late fusion.")
Pp("Clinical-score benchmarks: THRIVE, SPAN-100 and NIHSS alone, each converted to probabilities by logistic regression "
   "fitted inside training folds.")
Pp("Penalised models were chosen over unpenalised ones because Riley criteria [26, 27] showed that the cohort supports "
   "few parameters (see Results).")
Pp("Additional reference and imaging models (added after the primary analysis, run on the identical fold manifest): "
   "R1, a parsimonious logistic model with four established predictors (age, admission NIHSS, premorbid mRS, glucose; "
   "within the Riley budget); P1-recal, the locked GBM with Platt recalibration fitted by inner 5-fold cross-validation "
   "and the GBM refitted on the full training fold (ranking within a fold unchanged); E-native, model E on features "
   "recomputed from native-unit maps; V, a logistic model on log absolute volumes (core, Tmax >6 s, mismatch); and "
   "R1 + V. Each CTP model was fused with each clinical reference by the same equal-weight average.")
H("Validation protocol", 2)
Pp("We used nested cross-validation [36, 37]. The outer loop was stratified 10-fold, repeated with five seeds (42, 100, "
   "2024, 777, 999), giving one shared fold manifest for all models. The inner loop was stratified 5-fold, with grid "
   "search of C ∈ {0.01–1} and l1-ratio ∈ {0.2, 0.5, 0.8} minimising log-loss. Median imputation and standardisation "
   "were fitted inside training folds only. Feature extraction has no learned parameters, so it cannot leak outcome "
   "information.")
H("Performance measures and statistical comparisons", 2)
Pp("Primary estimand: the mean over seeds of the per-seed out-of-fold AUC. 95% CIs came from 2,000 patient-level "
   "bootstrap resamples, in which each resampled patient carries all five seed predictions. Paired ΔAUCs used the same "
   "resamples; we also report DeLong tests [32] on seed-averaged probabilities.")
Pp("Calibration [28, 29] was summarised by the calibration slope, calibration-in-the-large (CITL), Brier score, "
   "integrated calibration index (ICI) and LOESS curves.")
Pp("Clinical utility was assessed by decision curve analysis [30, 31], with prespecified thresholds of 0.20, 0.35 and "
   "0.50 and bootstrap CIs for the difference in net benefit (ΔNB).")
Pp("Category-free and categorical (<0.20/0.20–0.50/>0.50) NRI and IDI [33] are reported, with their known limitations "
   "[34, 35].")
Pp("The prespecified primary comparison was F versus P1. Key secondary comparisons were E versus T and the "
   "channel-wise ranking.")
H("Precision and equivalence analysis", 2)
Pp("Because a non-significant ΔAUC does not show absence of benefit, we quantified what the data can exclude. For each "
   "incremental-value comparison we report the 90% bootstrap CI and two one-sided tests against equivalence margins "
   "of ±0.05 and ±0.03 AUC [52]; posterior probabilities P(ΔAUC > 0) and P(ΔAUC > 0.05) from a Bayesian bootstrap "
   "(Dirichlet patient weights, flat prior) [53]; the minimal detectable difference at 80% power (2.80 × bootstrap SE); "
   "and the sample size needed to detect ΔAUC = 0.05 with 80% power, scaling the SE by 1/√n.")
H("Centre inference and centre-aware validation", 2)
Pp("The dataset descriptor reports 99 training cases from Munich (Center 1) and 50 from Zurich (Center 2) but does not "
   "label subjects [3]. We inferred the centre from two provenance signatures of the original release that are "
   "independent of outcome: the storage precision of the perfusion maps (voxel values quantised to multiples of 1/64 "
   "versus unquantised floating point) and the NCCT slice thickness and CTP slab coverage. We then (i) described case mix "
   "and release-level imputation by centre; (ii) computed within-centre AUCs from the pooled-CV predictions, using only "
   "patient pairs from the same centre, which removes discrimination that merely reflects different outcome rates "
   "between centres; (iii) repeated the nested CV within Munich only; and (iv) performed leave-one-centre-out "
   "validation, developing each model on one centre and applying it unchanged to the other [54].")
H("Subgroup analyses", 2)
Pp("Exploratory, without multiplicity adjustment: ΔAUC of F over P1 within strata of age (≥80 years), admission NIHSS "
   "(≥10), premorbid mRS (≥1), visible vessel occlusion on CTA, wake-up stroke, inferred centre, and native core and "
   "Tmax >6 s volume (≥ median). Effect modification was tested by a likelihood-ratio test of the interaction between "
   "the out-of-fold CTP score and the subgroup indicator in a logistic model that also contained the clinical score.")
H("Second prespecified plan: timeline, location and occlusion population", 2)
Pp("After the analyses above, we wrote a second analysis plan before running any of the following models (Additional "
   "file 3), with one primary comparison per hypothesis and Holm correction across the three. All models used the "
   "same nested-CV protocol; all results are reported.")
Pp("H3, timeline. Three time points were distinguished: admission (T0), 24 h after treatment (T1, NIHSS at 24 h) and "
   "follow-up MRI 2–9 days after treatment (T2, DWI final-infarct volume from the provided lesion masks, log-transformed). "
   "In the full cohort (both centres; DWI available for all) we compared R1 with R1 + infarct volume (primary), and "
   "tested whether pre-treatment CTP (fused with model E) added information once infarct volume was known. Because "
   "24-h NIHSS was recorded almost only in Munich, the complete timeline (R1 → + 24-h NIHSS → + infarct volume, each "
   "with and without CTP) was modelled in Munich, with median imputation of missing 24-h NIHSS inside training folds "
   "and a complete-case sensitivity analysis. Post-interventional mTICI was not modelled (almost all 2c/3).")
Pp("H1, location. The MNI152 2-mm template [55] was registered affinely to each patient's skull-stripped follow-up DWI, "
   "which shares the NCCT space of the perfusion maps (SimpleITK [56]; Mattes mutual information; three-level pyramid). "
   "Atlas regions were carried to patient space by nearest-neighbour interpolation: corticospinal tract (Juelich "
   "atlas [57]); caudate, putamen, pallidum and thalamus; insula and frontal, central and parietal operculum; and left "
   "inferior frontal (pars opercularis/triangularis), posterior superior temporal, supramarginal and angular gyri "
   "(Harvard–Oxford [58]). For each region we computed the fraction involved by ipsilateral Tmax >6 s tissue (within "
   "the CTP slab) and by the DWI infarct. Registration quality was the Dice coefficient between the warped template "
   "brain mask and the patient's brain mask; patients with Dice <0.80 were excluded in a sensitivity analysis. Models: "
   "an elastic net on the four CTP location features fused with P1 (primary), R1 + CTP location, and R1 + infarct "
   "volume + infarct location versus R1 + infarct volume [59].")
Pp("H2, occlusion population. The exploratory subgroup analysis suggested benefit of CTP in patients with a visible "
   "occlusion. We repeated the nested CV within patients with a non-empty native-resolution vessel-occlusion mask; "
   "because this hypothesis arose from the same data, it is reported as hypothesis-generating.")
H("Interpretability", 2)
Pp("Channel contribution was quantified as each channel's share of Σ|standardised coefficient| in model E across the 50 "
   "outer folds, and by leave-one-channel-out ablation. TreeSHAP [38] values were computed for gradient-boosting models "
   "on outer-test patients. Stability was the median pairwise Spearman correlation of importance vectors across folds "
   "(threshold >0.6).")
H("Sensitivity analyses", 2)
Pp("(1) Ordinal mRS: ordinal c-index [39, 41], and a proportional-odds model testing whether the out-of-fold CTP score "
   "adds information to the clinical score.")
Pp("(2) Alternative thresholds: Tmax >4 or >8 s; core rCBF <20% or <38%, or whole-hemisphere core.")
Pp("(3) Scale-free features only, independent of the absolute Tmax scale.")
Pp("(4) Restriction to patients whose Tmax ceiling was present (scale exactly identified).")
Pp("(5) Compact physiological set (15 features) and PCA (5 components) CTP models.")
Pp("(6) Missing-value indicators added to P1, and alert-to-door removed.")
Pp("(7) 5 × 5-fold protocol.")
Pp("(8) Fusion with the CBV-only model (exploratory).")
H("Software", 2)
Pp("Python 3.10 with scikit-learn 1.7.2 [47], statsmodels, shap, nibabel, pyarrow and SciPy. The complete pipeline (scripts s01–s22, "
   "one command per stage) regenerates every number, table and figure in this manuscript. An AI assistant (Claude, "
   "Anthropic) was used to help write analysis code and draft text; the authors reviewed all code, outputs and text and "
   "take full responsibility.")

# ------------------------------------------------------------------ results
H("Results")
H("Cohort", 2)
nm = t1.set_index("variable")
Pp(f"Of 149 cases, 20 lacked a 90-day mRS and were excluded. The analysed cohort comprised 129 patients: 85 with a good "
   f"outcome and 44 with a poor outcome (34.1%). The 90-day mRS distribution was {nm.loc['90-day mRS 0/1/2/3/4/5/6, n', 'all']} "
   f"for mRS 0/1/2/3/4/5/6. Post-interventional mTICI was recorded in 89 patients, of whom 87 had 2c/3 reperfusion. "
   f"Characteristics are shown in Table 1.")
Pp(f"Excluded patients were older (SMD {abs(ivx.loc['Age','SMD']):.2f}) and more often had atrial fibrillation (SMD "
   f"{abs(ivx.loc['Atrial fibrillation','SMD']):.2f}) (Additional file 2).")
Pp(f"Probable median imputations by the data release affected CRP ({miss.loc['CRP','pct']:.0f}%), INR "
   f"({miss.loc['INR','pct']:.0f}%), leucocytes ({miss.loc['Leucocytes','pct']:.0f}%), onset-to-door "
   f"({miss.loc['Onset to door_min','pct']:.0f}%) and alert-to-door ({miss.loc['Alert to door_min','pct']:.0f}%). "
   f"Laboratory values were imputed more often in good-outcome patients.")
Pp(f"Riley's criteria showed how few parameters the cohort supports. With 44 events and an anticipated AUC of 0.75, "
   f"only ≈{r75.max_params_for_shrinkage_09 if 'max_params_for_shrinkage_09' in r75 else r75['max_params_for_shrinkage_0.9']:.1f} "
   f"predictor parameters are supported for a target shrinkage of 0.9, and precise estimation of the overall risk would "
   f"need n ≈ {r75.n_required_intercept_precision:.0f}. The events per candidate parameter were "
   f"{r75.EPV_22_clinical:.1f} for the clinical model and {r75.EPV_22_plus_53_ctp:.2f} for the combined set, which "
   f"justifies penalisation and fixed-weight fusion.")
H("Physical-unit recovery and technical validation", 2)
Pp(f"Recovered maps satisfied the central volume theorem: the median per-patient ratio of observed MTT to 60·CBV/CBF "
   f"was {qc['cvt_ratio_median_of_medians']:.3f} (IQR {qc['cvt_ratio_IQR'][0]:.3f}–{qc['cvt_ratio_IQR'][1]:.3f}), and "
   f"{100*qc['cvt_ratio_within_5pct']:.1f}% of patients were within ±5% (Fig. 2a). The contralateral medians were "
   f"Tmax {qc['contra_tmax_median']:.1f} s, CBF {qc['contra_cbf_median']:.1f} mL/100 g/min, CBV "
   f"{qc['contra_cbv_median']:.1f} mL/100 g and MTT {qc['contra_mtt_median']:.1f} s. These values are plausible for "
   f"this software and agree with the providers' display windows [4]. The automatically detected ipsilateral hemisphere "
   f"agreed with the vessel-occlusion mask in {lvo_agree}/{lvo_n} patients ({100*qc['ipsi_agrees_with_lvo']:.1f}%).")
Pp(f"In the ISLES 2018 simulation, CBF and CBV scales were recovered exactly in all cases. MTT and Tmax scales were "
   f"exact when the 30-s ceiling was present ({sim.loc['MTT','pct_ceiling_reached']:.0f}% and "
   f"{sim.loc['Tmax','pct_ceiling_reached']:.0f}% of cases) (Fig. 2b). At feature level, the median ICC between true and "
   f"recovered features was {agr.ICC_true_vs_recovered.median():.3f} (range {agr.ICC_true_vs_recovered.min():.3f}–1.000). "
   f"The lowest values were for Tmax-dependent features (Fig. 2c). The rCBF <30% core fraction correlated with the "
   f"DWI-defined core fraction (Spearman ρ = {agr.loc['core_rcbf30_hypo_frac','spearman_with_DWI_core']:.2f}).")
Pp(f"Against the native-unit maps of the original release, the recovered features agreed closely: median ICC "
   f"{nagr.icc31.median():.3f} (IQR {nagr.icc31.quantile(.25):.3f}–{nagr.icc31.quantile(.75):.3f}), with "
   f"{int((nagr.icc31 >= 0.9).sum())}/{len(nagr)} features ≥0.90. The lowest value ({nagr.icc31.min():.2f}) was for the "
   f"10th percentile of ipsilateral Tmax, which is zero in most patients (Fig. S3). The central volume theorem held in "
   f"the native maps (median ratio {nval['cvt_ratio_median']:.3f}), and the detected ipsilateral hemisphere agreed with "
   f"the native vessel-occlusion mask in {100*nval['ipsi_agrees_lvo']:.1f}% of {int(nval['lvo_n'])} patients. The release's "
   f"text labels confirmed that sex code 1 denotes male.")
Pp(f"Native absolute volumes were small for the core (median {vol('core_ml'):.1f} mL, IQR {vol('core_ml','25%'):.1f}–"
   f"{vol('core_ml','75%'):.1f}) and large for Tmax >6 s tissue (median {vol('tmax6_ml'):.0f} mL, IQR "
   f"{vol('tmax6_ml','25%'):.0f}–{vol('tmax6_ml','75%'):.0f}). Core and Tmax >6 s volumes correlated weakly with the "
   f"follow-up DWI infarct (ρ = {nval['rho_core_ml_vs_dwi']:.2f} and {nval['rho_tmax6_ml_vs_dwi']:.2f}), and not with "
   f"90-day mRS (ρ = {nval['rho_core_ml_vs_mrs90']:.2f} and {nval['rho_tmax6_ml_vs_mrs90']:.2f}). Core volume did not "
   f"differ between outcome groups (median {nval['median_core_ml_poor']:.1f} vs {nval['median_core_ml_good']:.1f} mL; "
   f"P = {pv(nval['mw_p_core'])}). By contrast, the follow-up DWI volume correlated with 90-day mRS "
   f"(ρ = {nval['rho_dwi_vs_mrs90']:.2f}).")
H("Discrimination", 2)
Pp(f"The clinical GBM (P1) achieved an AUC of {auc(P1)}; the seed SD was {perf.loc[P1].auc_seed_sd:.3f}. This is "
   f"comparable to the 0.750 previously reported for the same configuration [50] (Table 2, Fig. 3).")
Pp(f"CTP-only models performed worse. The single-channel models ranked CBV {f3(perf.loc['B_CBV'].auc_seed_mean)} > "
   f"Tmax {f3(perf.loc['D_Tmax'].auc_seed_mean)} > MTT {f3(perf.loc['C_MTT'].auc_seed_mean)} > CBF "
   f"{f3(perf.loc['A_CBF'].auc_seed_mean)}. CBV and Tmax outperformed CBF ({cmp('B_CBV','A_CBF')}; "
   f"{cmp('D_Tmax','A_CBF')}). The all-channel model E ({auc(E)}) did not exceed CBV alone, and the "
   f"classical-threshold model T reached {auc(TT)} (E vs T: {cmp(E, TT)}).")
Pp(f"The multimodal fusion model F reached {auc(F)}, giving {cmp(F, P1)} over P1 (DeLong P on pooled probabilities = "
   f"{pv(comp[(comp.new==F)&(comp.reference==P1)].p_delong_pooled.iloc[0])}). Early fusion did not improve on P1 "
   f"({cmp('F_EN_clin_CTP', P1)}), and neither did clinical + threshold GBM ({cmp('F_GBM_clin_thresh', P1)}). "
   f"Compared with the clinical scores, P1 discriminated better than THRIVE ({cmp(P1,'THRIVE')}) and non-significantly "
   f"better than SPAN-100 ({cmp(P1,'SPAN100')}).")
Pp(f"The conclusion did not depend on the clinical reference. The four-predictor logistic model R1 reached {auc(R1)}; "
   f"adding CTP gave {cmp('F_late_R1_E', R1)}. The recalibrated GBM reached {auc(PR)} with a calibration slope of "
   f"{f2(perf.loc[PR].pooled_slope)}; adding CTP gave {cmp('F_late_P1recal_E', PR)}. Features from native-unit maps "
   f"performed like recovered ones (E-native {auc('E_native')}; fusion {cmp('F_late_P1_Enat', P1)}). Absolute volumes "
   f"had no discriminative value (V {auc('V_volumes')}), and adding them lowered the AUC slightly "
   f"({cmp('F_late_P1_V', P1)}; R1 + V vs R1: {cmp('R1_plus_volumes', R1)}).")
H("Calibration, clinical utility and reclassification", 2)
Pp(f"P1 was overconfident: calibration slope {f2(perf.loc[P1].pooled_slope)} (95% CI {f2(perf.loc[P1].pooled_slope_lo)}–"
   f"{f2(perf.loc[P1].pooled_slope_hi)}), CITL {f2(perf.loc[P1].pooled_citl)}, ICI {f3(perf.loc[P1].pooled_ici)}. The "
   f"apparent training AUC was 1.00, a train–test gap of {gap.loc[P1,'gap']:.2f}. Fusion averaging shrank the "
   f"probabilities, giving slope {f2(perf.loc[F].pooled_slope)} ({f2(perf.loc[F].pooled_slope_lo)}–"
   f"{f2(perf.loc[F].pooled_slope_hi)}), ICI {f3(perf.loc[F].pooled_ici)} and a lower Brier score "
   f"({f3(perf.loc[F].brier_seed_mean)} vs {f3(perf.loc[P1].brier_seed_mean)}). Linear models were close to "
   f"calibrated (Fig. 5).")
Pp(f"Decision curves showed no net-benefit gain of F over P1: ΔNB {dnbs(F,P1,0.20)} at 0.20, {dnbs(F,P1,0.35)} at "
   f"0.35 and {dnbs(F,P1,0.50)} at 0.50 (Fig. 6). P1 had a higher net benefit than THRIVE at 0.35 "
   f"({dnbs(P1,'THRIVE',0.35)}) and 0.50 ({dnbs(P1,'THRIVE',0.50)}).")
Pp(f"Category-free NRI for F versus P1 was negative ({nri_cf.nri:+.2f}, 95% CI {nri_cf.nri_lo:+.2f} to "
   f"{nri_cf.nri_hi:+.2f}), as was IDI ({nri_cf.idi:+.3f}). Categorical NRI was {nri_cat.nri:+.3f} "
   f"({nri_cat.nri_lo:+.3f} to {nri_cat.nri_hi:+.3f}). These negative values reflect the shrinkage of overconfident P1 "
   f"probabilities, not a loss of ranking ability. They illustrate why NRI/IDI should not be read without calibration "
   f"[34, 35]. P1 versus THRIVE: NRI {nri_th.nri:+.2f} ({nri_th.nri_lo:+.2f} to {nri_th.nri_hi:+.2f}), IDI "
   f"{nri_th.idi:+.3f} (Table 3).")
H("Which channel carries prognostic information?", 2)
Pp(f"In model E, CBV features accounted for {100*stab.loc[E,'share_CBV']:.0f}% of the total standardised coefficient "
   f"mass, Tmax {100*stab.loc[E,'share_Tmax']:.0f}%, CBF {100*stab.loc[E,'share_CBF']:.0f}% and MTT "
   f"{100*stab.loc[E,'share_MTT']:.0f}% (rank stability ρ = {stab.loc[E,'rank_spearman_median']:.2f}) (Fig. 7a). "
   f"Removing CBV degraded model E the most (AUC {f3(sensp['_sens_features'].loc['E_minus_CBV'].auc_seed_mean)} vs "
   f"{f3(sensp['_sens_features'].loc['E_CTP_all'].auc_seed_mean)}), whereas removing any other channel changed it by "
   f"≤0.01 (Fig. 7b). The most consistently selected imaging features were the skewness of ipsilateral rCBV, the CBV "
   f"index (lower → poor outcome), the small rCBF <20% core and the interhemispheric Tmax difference (higher → poor "
   f"outcome).")
top = shp.head(5)
Pp(f"In P1, the TreeSHAP ranking was stable (ρ = {tstab.loc[P1,'rank_spearman_median']:.2f}). The leading predictors "
   f"were {', '.join(top.feature.str.replace('_min',''))}. Higher CRP, premorbid mRS and age increased the predicted "
   f"risk, and male sex decreased it (Fig. 7c). Because laboratory values were almost entirely median-imputed in one "
   f"centre (below), part of the CRP signal may reflect centre rather than biology.")
H("Sensitivity analyses", 2)
sf = sens["_sens_features"]
Pp(f"The fusion–clinical difference was small and non-significant in every sensitivity analysis (Additional file 2; "
   f"Fig. S1):")
Pp(f"5 × 5-fold protocol: {scmp('_5fold', F)}.")
Pp(f"Patients with an exactly identified Tmax scale (n = 85): {scmp('_sens_tmaxcertain', F)}.")
Pp(f"Scale-free CTP features: {scmp('_sens_features','F_late_P1_Esf')}.")
Pp(f"PCA CTP model: {scmp('_sens_features','F_late_P1_EPCA')}.")
Pp(f"Compact physiological set: {scmp('_sens_features','F_late_P1_Ephys')}.")
Pp(f"CBV-only partner (exploratory): {scmp('_sens_features','F_late_P1_CBV')}.")
Pp(f"Missing-value indicators: {scmp('_sens_missing','F_late_P1miss_E')}.")
Pp(f"Alternative Tmax or core thresholds did not rescue model T (AUC range "
   f"{min(sensp['_sens_features'].loc[m].auc_seed_mean for m in ['T_tmax4','T_tmax8','T_core20','T_core38','T_core_ipsi30']):.3f}–"
   f"{max(sensp['_sens_features'].loc[m].auc_seed_mean for m in ['T_tmax4','T_tmax8','T_core20','T_core38','T_core_ipsi30']):.3f}).")
Pp(f"Missing-value indicators alone carried little signal (AUC "
   f"{f3(sensp['_sens_missing'].loc['P1_missonly'].auc_seed_mean)}), and adding them to P1 changed its AUC by "
   f"{sens['_sens_missing'].loc['P1_missind'].delta_auc:+.3f}.")
Pp(f"For the ordinal outcome, the c-index was {ordc.loc[F,'ordinal_c']:.3f} for F and {ordc.loc[P1,'ordinal_c']:.3f} for "
   f"P1 (Δ {ordc.loc[F,'delta_vs_P1']:+.3f}, {ordc.loc[F,'delta_lo']:+.3f} to {ordc.loc[F,'delta_hi']:+.3f}). In a "
   f"proportional-odds model, the out-of-fold CTP score added information to the clinical score (likelihood-ratio "
   f"χ² = {po['LR_chi2_add_CTP_to_P1']:.1f}, P = {pv(po['p'])}; OR {po['OR_per_unit_lp_E']:.2f} per logit unit). "
   f"The corresponding binary test was not significant (P = {pv(po['binary_p'])}). This exploratory signal, spread "
   f"across the mRS spectrum, warrants confirmation.")

H("Precision of the incremental-value estimate", 2)
Pp(f"For the primary comparison (F vs P1), the 90% CI of ΔAUC was {pF.ci90_lo:+.3f} to {pF.ci90_hi:+.3f}, so "
   f"equivalence within ±0.05 could not be shown and a gain of 0.05 could not be excluded. The posterior probability of any gain was "
   f"{pF.post_p_gt0:.2f}, of a gain >0.03 {pF['post_p_gt0.03']:.2f} and of a gain >0.05 {pF['post_p_gt0.05']:.2f}. The "
   f"minimal detectable difference at 80% power was {pF.mdd_80pct_power:.3f}, and detecting ΔAUC = 0.05 would require "
   f"≈{int(pF['n_needed_delta0.05'])} patients (≈{int(pF['events_needed_delta0.05'])} events). Results were similar with "
   f"the R1 reference (P(gain >0.05) = {prec.loc['F_late_R1_E','post_p_gt0.05']:.2f}) and with native-unit features "
   f"({prec.loc['F_late_P1_Enat','post_p_gt0.05']:.2f}). For absolute volumes, equivalence within ±0.05 was shown "
   f"(late fusion 90% CI {sg3(prec.loc['F_late_P1_V','ci90_lo'])} to {sg3(prec.loc['F_late_P1_V','ci90_hi'])}; joint model "
   f"{sg3(prec.loc['R1_plus_volumes','ci90_lo'])} to {sg3(prec.loc['R1_plus_volumes','ci90_hi'])}), and a gain of ≥0.03 "
   f"was excluded (Additional file 2).")

H("Centre effects and geographic validation", 2)
Pp(f"The provenance signatures split the 149 cases into {site['cluster_sizes']['quantised']} and "
   f"{site['cluster_sizes']['float']}, consistent with the descriptor's 100 Munich and 50 Zurich cases (149 of 150 released). All "
   f"{site['crosstab_slice_mm']['4.0']['Zurich (inferred)']} cases with 4-mm NCCT slices fell in the 50-case cluster. "
   f"Median CTP slab coverage was {site['ctp_slab_mm_median']['Munich (inferred)']:.0f} mm in Munich and "
   f"{site['ctp_slab_mm_median']['Zurich (inferred)']:.0f} mm in Zurich. In the analysed cohort, poor outcome was "
   f"more frequent in Munich ({mun_ev}/{mun_n}, {cmix.loc['Munich','poor_pct']:.0f}%) than in Zurich "
   f"({zur_ev}/{zur_n}, {cmix.loc['Zurich','poor_pct']:.0f}%; {peq(cmix.loc['Munich','fisher_p_poor'])}). Zurich "
   f"patients were younger (median age {cmix.loc['Zurich','age_median']:.0f} vs {cmix.loc['Munich','age_median']:.0f}), and "
   f"none had premorbid mRS >0 (vs {cmix.loc['Munich','premorbid_mrs_gt0_pct']:.0f}% in Munich). In Zurich, CRP, "
   f"leucocytes, INR and onset-to-door time were median-imputed by the release in ≥{lab_imp_z:.0f}% of patients, versus "
   f"≤{lab_imp_m:.0f}% for the laboratory values in Munich. The centre indicator alone gave a pooled AUC of "
   f"{wca.loc['Centre indicator alone','auc_pooled_seedmean']:.3f}.")
Pp(f"Restricting concordance to pairs within the same centre lowered the AUC of P1 from "
   f"{wca.loc[P1,'auc_pooled_seedmean']:.3f} to {wca.loc[P1,'within_centre_auc']:.3f} (95% CI "
   f"{wca.loc[P1,'within_lo']:.3f}–{wca.loc[P1,'within_hi']:.3f}). The incremental value of CTP was unchanged "
   f"({wcmp(F, P1)}). In nested CV within Munich only (n = {mun_n}, {mun_ev} events), the clinical GBM reached "
   f"{auc(P1, mperf)} and the clinical elastic net {auc('P2_clin_EN', mperf)}, with a calibration slope of "
   f"{f2(mperf.loc['P2_clin_EN'].pooled_slope)}. CTP alone reached {auc(E, mperf)}, and fusion did not improve on P1 "
   f"({mcmp(F, P1)}; native-unit features {mcmp('F_late_P1_Enat', P1)}).")
Pp(f"Leave-one-centre-out validation was limited by the small number of Zurich events. Models developed in Munich "
   f"discriminated poorly in Zurich (P1 {gperf(MZ, P1)}; R1 {gperf(MZ, R1)}; F {gperf(MZ, F)}), with overestimated "
   f"risk (observed/expected {geo[(geo.direction==MZ)&(geo.model==P1)].o_e.iloc[0]:.2f} for P1), as expected from the "
   f"lower Zurich event rate. The CTP increment was imprecise ({gcmp(MZ, F, P1)}). In the reverse direction "
   f"(development on {zur_ev} events), P1 reached {gperf(ZM, P1)} in Munich and CTP added "
   f"{gcmp(ZM, F, P1).replace('ΔAUC ', '')} (Fig. 8; Additional file 2).")

H("Exploratory subgroup analyses", 2)
Pp(f"CTP tended to add discrimination in patients with more severe or larger-vessel strokes, and to subtract it "
   f"otherwise (Fig. S2): NIHSS ≥10 vs <10, ΔAUC {sg('NIHSS >= 10')}; visible vessel occlusion vs none, "
   f"{sg('LVO visible on CTA')}; core volume ≥ vs < median, {sg('Core volume >= median')}. No interaction was seen for "
   f"age, premorbid mRS, wake-up onset, centre or Tmax >6 s volume. These subgroup findings are hypothesis-generating; "
   f"within each subgroup the CI of ΔAUC included zero.")

h1, h2 = hp("PRIMARY H1"), hp("PRIMARY H2")
d80 = locf.reg_dice
H("Prognostic information across the care pathway (second plan, H3)", 2)
Pp(f"In the full cohort, adding follow-up infarct volume to the four-predictor admission model raised the AUC from "
   f"{tl(SA,'R1_clin_LR4')} to {tl(SA,'R1_DWI')} (ΔAUC {h3.delta_auc:+.3f}, 95% CI {h3.ci_lo:+.3f} to {h3.ci_hi:+.3f}; "
   f"P = {pv(h3.p_bootstrap)}, Holm-adjusted P = {h3.p_holm:.3f}). The within-centre AUC was "
   f"{tlr(SA,'R1_DWI').within_centre_auc:.3f}, so the gain did not depend on centre differences. Combining the clinical "
   f"GBM with infarct volume gave {tl(SA,'P1_plus_DWI')} ({tld(SA,'P1_plus_DWI','P1_clin_GBM')}), the highest "
   f"discrimination in this study, with a Brier score of {tlr(SA,'P1_plus_DWI').brier:.3f}. Once infarct volume was "
   f"known, pre-treatment CTP did not help ({tld(SA,'R1_DWI_plus_E','R1_DWI')}).")
Pp(f"In Munich (n = {int(tlr(SB,'R1_clin_LR4').n)}, {int(tlr(SB,'R1_clin_LR4').events)} events), discrimination "
   f"increased along the care pathway: admission {tl(SB,'R1_clin_LR4')}; + 24-h NIHSS {tl(SB,'R1_N24')} "
   f"({tld(SB,'R1_N24','R1_clin_LR4')}); + infarct volume {tl(SB,'R1_N24_DWI')} (T2 vs T0: "
   f"{tld(SB,'R1_N24_DWI','R1_clin_LR4')}). Calibration slopes of these logistic models were "
   f"{tlr(SB,'R1_clin_LR4').cal_slope:.2f}, {tlr(SB,'R1_N24').cal_slope:.2f} and {tlr(SB,'R1_N24_DWI').cal_slope:.2f}. "
   f"Adding pre-treatment CTP lowered the AUC at every time point (T0 {tld(SB,'R1_plus_E','R1_clin_LR4')}; T1 "
   f"{tld(SB,'R1_N24_plus_E','R1_N24')}; T2 {tld(SB,'R1_N24_DWI_plus_E','R1_N24_DWI')}) (Fig. 9). Complete-case analysis "
   f"(n = {int(tlr(SBC,'R1_clin_LR4').n)}) gave the same pattern (T2 vs T0: {tld(SBC,'R1_N24_DWI','R1_clin_LR4')}).")
H("Location of hypoperfusion and of the final infarct (H1)", 2)
Pp(f"Registration Dice had a median of {d80.median():.2f} (IQR {d80.quantile(.25):.2f}–{d80.quantile(.75):.2f}); "
   f"{int((d80 < 0.80).sum())} of {len(d80)} patients were below 0.80 (examples in Fig. S4). The location of Tmax >6 s tissue carried no prognostic signal (location model "
   f"{ll(H1S,'Loc_CTP')}), and adding it to the clinical GBM did not help (primary H1: ΔAUC {h1.delta_auc:+.3f}, 95% CI "
   f"{h1.ci_lo:+.3f} to {h1.ci_hi:+.3f}; Holm-adjusted P = {h1.p_holm:.2f}). The location of the final infarct tended "
   f"to add to its volume in the full cohort ({tld(H1S,'R1_DWI_Loc','R1_DWI',llc)}), but not among well-registered patients "
   f"({tld(H1D,'R1_DWI_Loc','R1_DWI',llc)}), so this signal is not robust.")
H("Occlusion population (H2, hypothesis-generating)", 2)
Pp(f"A vessel-occlusion mask was present at native resolution in {int(llp[llp.set==H2S].n.iloc[0])} of 129 patients, "
   f"so this population was nearly the whole cohort. Within it, CTP did not add to the clinical GBM (ΔAUC "
   f"{h2.delta_auc:+.3f}, 95% CI {h2.ci_lo:+.3f} to {h2.ci_hi:+.3f}; Holm-adjusted P = {h2.p_holm:.2f}). The earlier "
   f"'visible occlusion' subgroup, defined on the down-sampled masks of the pre-processed release, therefore probably "
   f"selected patients with larger occlusion masks rather than patients with versus without an occlusion.")

# ------------------------------------------------------------------ discussion
H("Discussion")
Pp("In a public cohort treated with endovascular reperfusion, most patients with successful reperfusion, pre-treatment "
   "CTP added no measurable discrimination or net benefit to a clinical model built from routinely available "
   "pre-procedural variables. Combining the two improved calibration only, through the shrinkage that averaging "
   "provides. Among the four perfusion channels, relative CBV carried the most prognostic information and CBF the "
   "least. Classical treatment-selection thresholds and absolute perfusion volumes performed close to chance for "
   "prognosis. The conclusion held across eight sensitivity analyses, three clinical reference models, native-unit "
   "features and centre-aware analyses (Fig. 8). The precision analysis shows what the data support: a gain larger "
   "than 0.05 AUC is unlikely but not excluded, whereas a gain of 0.03 or more from absolute volumes is excluded. "
   "Prognostic information did accumulate after treatment: 24-h neurological status and follow-up infarct volume "
   "raised discrimination to 0.82–0.83, and pre-treatment CTP added nothing at any point on this timeline.")
Pp("This contrast is the clinically useful message. Perfusion imaging answers a treatment-selection question (is there "
   "salvageable tissue?), and after successful reperfusion that question has been answered. What remains uncertain "
   "at admission is how much tissue was lost despite reperfusion and how the patient responds, which the 24-h "
   "examination and the follow-up infarct capture directly [60, 61]. For counselling families and planning "
   "rehabilitation, prognostic models should therefore be updated at 24 h and after follow-up imaging rather than "
   "built on pre-treatment perfusion. The location analysis points the same way: where hypoperfusion lay before "
   "treatment did not matter, whereas where the infarct ended up may, although that signal was not robust here [59].")
Pp("These findings are consistent with the pathophysiology of successful reperfusion. Tmax-defined hypoperfusion and "
   "mismatch describe tissue at risk, most of which is salvaged when reperfusion is achieved, so their prognostic "
   "weight falls. HERMES likewise found no association of mismatch volume with outcome after EVT [9], and the "
   f"core–outcome association attenuates with rapid reperfusion [16]. Our cores were small (median {vol('core_ml'):.1f} mL), "
   f"which leaves little room for core volume to discriminate, whereas the post-treatment DWI infarct, which integrates "
   f"reperfusion success and lesion growth, was associated with outcome. The subgroup pattern points the same way: the "
   f"only hints of benefit were in patients with severe deficits, a visible occlusion or a larger core, in whom "
   f"perfusion deficits are larger and more consequential.")
Pp("Relative CBV within hypoperfused tissue (the CBV index) is a surrogate of collateral status [45]. Collateral status "
   "determines lesion growth before reperfusion and is independently associated with outcome. This makes CBV the "
   "physiologically plausible winner of the ablation. Our results agree with Brugnara et al., in whom adding CTP to "
   "clinical and conventional imaging raised the AUC from 0.740 to 0.747 (P = 0.15) [17], and with reviews reporting "
   "little consistent benefit of complex ML over well-specified clinical models [20, 21].")
Pp("The ordinal analysis suggested that CTP may carry information spread across the mRS spectrum, for example "
   "separating mRS 0 from 1–2, that the 0–2 vs 3–6 dichotomy discards [40, 41]. Larger cohorts analysed with ordinal "
   "endpoints should test this.")
Pp("The centre analysis matters for anyone reusing ISLES'24 for outcome prediction. The two centres differed threefold "
   "in the rate of poor outcome, and laboratory and onset-time variables were almost entirely median-imputed in one "
   "centre. A pooled model can therefore earn part of its AUC by recognising the centre from the imputation pattern, "
   "which is a form of shortcut learning that would not transport. Within-centre concordance removed about 0.03 AUC "
   "from the clinical model, and models developed in one centre did not transport to the other, although the Zurich "
   "estimates rest on six events and are too imprecise to support conclusions. Importantly, the incremental value of "
   "CTP was close to zero whether or not centre was accounted for, so our main conclusion is not an artefact of centre "
   "mixing. Centre labels are not distributed with the data; the provenance signatures we used give a 99/50 split consistent with the published "
   "100/50 (149 of 150 cases released) and can be recomputed by other groups with our code.")
Pp("This study has three methodological implications. First, pre-processed derivatives of public imaging datasets can "
   "silently remove physical units. Clinical thresholds such as Tmax >6 s are then meaningless unless units are "
   "recovered and verified. Our recovery can be verified with a physical identity (the central volume theorem), by "
   "simulation and, here, directly against the native-unit maps, and it is reusable by other groups working with the "
   "same release. Second, re-analysis from a single "
   "locked pipeline exposed errors that are easy to make in multi-stage projects: mis-scored THRIVE points "
   f"({thr_audit['thrive_mismatches']}/129 patients in an earlier internal benchmark), undisclosed median imputation "
   "of laboratory variables, and inverted probability orientation in SHAP interpretation. We recommend automated "
   "consistency checks and patient-level audit tables. Third, the clinical GBM was markedly overconfident despite good "
   "discrimination. With n = 129, Riley's criteria support only two to three parameters, so recalibration, "
   "penalisation or fixed-weight ensembling should be considered default safeguards and calibration should be "
   "reported alongside AUC.")
H("Limitations", 2)
Pp(f"First, the sample is small (129 patients, 44 events). The precision analysis shows that a gain of 0.05 AUC from "
   f"CTP features cannot be excluded; about {int(pF['n_needed_delta0.05'])} patients would be needed to detect it.")
Pp(f"Second, there is no independent external cohort. Centres were inferred rather than labelled, and geographic "
   f"validation rested on only {zur_ev} Zurich events, so it informs about transportability only qualitatively. "
   f"External validation in an independent thrombectomy cohort with complete laboratory data is required.")
Pp(f"Third, the primary analysis used recovered rather than native units. Agreement with the native maps was high, and "
   f"native-unit features gave the same results. CTP slab coverage differed between centres (median "
   f"{site['ctp_slab_mm_median']['Munich (inferred)']:.0f} vs {site['ctp_slab_mm_median']['Zurich (inferred)']:.0f} mm), "
   "which affects absolute hypoperfusion volumes, and voxel-level registration differences between releases contribute "
   "to the residual disagreement.")
Pp("Fourth, the dataset includes predominantly mTICI 2c/3 reperfusion. Our conclusions may not hold for incomplete "
   "reperfusion, in which hypoperfusion metrics are expected to matter more.")
Pp("Fifth, laboratory and workflow variables were median-imputed by the data release and perturbed for anonymisation. "
   "Imputation was concentrated in one centre and therefore associated with outcome. Missing-indicator and "
   "within-centre analyses did not change the conclusions, but the absolute performance of the clinical model is "
   "probably optimistic for a single-centre setting.")
Pp("Sixth, algorithm families and the clinical configuration were chosen on the same cohort in the companion study, "
   "leaving residual selection optimism. Twenty excluded patients were older and more often had atrial fibrillation.")
Pp("Seventh, the timeline analysis relies on 24-h NIHSS recorded almost only in Munich, and the follow-up MRI was "
   "acquired 2–9 days after treatment, which varies between patients; the post-treatment models are therefore "
   "time-point specific. The second analysis plan was internal and not publicly registered, and its primary H3 result "
   "was borderline after Holm correction. Atlas registration was affine and CT perfusion covered only part of the brain.")
H("Conclusions")
Pp("After thrombectomy, routinely available pre-procedural clinical variables carried most of the prognostic "
   "information available at admission, and the early post-treatment course (24-h NIHSS, follow-up infarct volume) "
   "added substantially more. Pre-treatment CTP, including classical thresholds, absolute volumes and lesion location, "
   "added no discrimination or net benefit at any time point, consistently across reference models, unit definitions "
   "and centres; gains above 0.05 AUC are unlikely but not excluded. Relative CBV was the most informative channel. "
   "Prognostic models after thrombectomy should be updated with post-treatment information. Public derivatives of ISLES'24 can be "
   "reused validly only after unit verification and centre-aware evaluation. A cohort of about 300 patients with "
   "complete clinical data and ordinal endpoints is needed to settle the question.")

H("List of abbreviations")
Pp("AUC, area under the receiver-operating-characteristic curve; CBF, cerebral blood flow; CBV, cerebral blood volume; "
   "CITL, calibration-in-the-large; CTP, CT perfusion; DCA, decision curve analysis; DWI, diffusion-weighted imaging; "
   "EVT, endovascular thrombectomy; GBM, gradient-boosting machine; HIR, hypoperfusion intensity ratio; ICC, intraclass "
   "correlation coefficient; ICI, integrated calibration index; IDI, integrated discrimination improvement; mRS, "
   "modified Rankin Scale; MTT, mean transit time; NB, net benefit; NIHSS, National Institutes of Health Stroke Scale; "
   "NRI, net reclassification improvement; OOF, out-of-fold; SHAP, Shapley additive explanations; SMD, standardised "
   "mean difference; Tmax, time-to-maximum of the residue function.")

H("Declarations")
Pp("Not applicable. This secondary analysis used the public, de-identified ISLES'24 and ISLES 2018 datasets, collected "
   "with local ethics approvals by the providers [3, 42] [authors to confirm the local institutional waiver wording].",
   "Ethics approval and consent to participate: ")
Pp("Not applicable.", "Consent for publication: ")
Pp("ISLES'24 is available from Zenodo (doi:10.5281/zenodo.17652035; CC BY-NC-SA 4.0) and as a per-subject mirror on "
   "Hugging Face (hugging-science/isles24-stroke); ISLES 2018 from the ISLES challenge website. Analysis code, the "
   "inferred centre labels, fold manifests and out-of-fold predictions will be deposited at "
   "[repository DOI to be inserted before submission].", "Availability of data and materials: ")
Pp("The authors declare that they have no competing interests.", "Competing interests: ")
Pp("[to be completed].", "Funding: ")
Pp("[to be completed according to CRediT].", "Authors' contributions: ")
Pp("We thank the ISLES'24 and ISLES 2018 organisers and data providers. The cohort and clinical predictor set overlap "
   "with a companion clinical-only study [50]; all results reported here were generated anew by a single locked "
   "pipeline, and the clinical model is reused as a comparator only.", "Acknowledgements and overlap disclosure: ")

REFS = [
 "GBD 2019 Stroke Collaborators. Global, regional, and national burden of stroke and its risk factors, 1990–2019. Lancet Neurol. 2021;20:795–820. doi:10.1016/S1474-4422(21)00252-0",
 "Goyal M, Menon BK, van Zwam WH, et al. Endovascular thrombectomy after large-vessel ischaemic stroke: a meta-analysis of individual patient data from five randomised trials. Lancet. 2016;387:1723–31. doi:10.1016/S0140-6736(16)00163-X",
 "Riedel EO, de la Rosa E, Baran TA, et al. The Ischemic Stroke Lesion Segmentation Challenge (ISLES)'24 dataset: a multimodal stroke imaging dataset with hyperacute CT, acute postinterventional MRI, and 3-month clinical outcomes. Radiol Artif Intell. 2026;8(3):e250603. doi:10.1148/ryai.250603",
 "de la Rosa E, Su R, Reyes M, et al. ISLES'24: final infarct prediction with multimodal imaging and clinical data. Where do we stand? arXiv. 2024. arXiv:2408.10966 (version 2, 2025).",
 "Flint AC, Cullen SP, Faigeles BS, Rao VA. Predicting long-term outcome after endovascular stroke treatment: the totaled health risks in vascular events score. AJNR Am J Neuroradiol. 2010;31:1192–6. doi:10.3174/ajnr.A2050",
 "Flint AC, Xiang B, Gupta R, et al. THRIVE score predicts outcomes with a third-generation endovascular stroke treatment device in the TREVO-2 trial. Stroke. 2013;44:3370–5. doi:10.1161/STROKEAHA.113.002796",
 "Saposnik G, Guzik AK, Reeves M, Ovbiagele B, Johnston SC. Stroke Prognostication using Age and NIH Stroke Scale: SPAN-100. Neurology. 2013;80:21–8. doi:10.1212/WNL.0b013e31827b1ace",
 "Kremers F, Venema E, Duvekot M, et al. Outcome prediction models for endovascular treatment of ischemic stroke: systematic review and external validation. Stroke. 2022;53:825–36. doi:10.1161/STROKEAHA.120.033445",
 "Campbell BCV, Majoie CBLM, Albers GW, et al. Penumbral imaging and functional outcome in patients with anterior circulation ischaemic stroke treated with endovascular thrombectomy versus medical therapy: a meta-analysis of individual patient-level data. Lancet Neurol. 2019;18:46–55. doi:10.1016/S1474-4422(18)30314-4",
 "Campbell BCV, Christensen S, Levi CR, et al. Cerebral blood flow is the optimal CT perfusion parameter for assessing infarct core. Stroke. 2011;42:3435–40. doi:10.1161/STROKEAHA.111.618355",
 "Olivot JM, Mlynash M, Thijs VN, et al. Optimal Tmax threshold for predicting penumbral tissue in acute stroke. Stroke. 2009;40:469–75. doi:10.1161/STROKEAHA.108.526954",
 "Olivot JM, Mlynash M, Inoue M, et al. Hypoperfusion intensity ratio predicts infarct progression and functional outcome in the DEFUSE 2 cohort. Stroke. 2014;45:1018–23. doi:10.1161/STROKEAHA.113.003857",
 "Albers GW, Marks MP, Kemp S, et al. Thrombectomy for stroke at 6 to 16 hours with selection by perfusion imaging. N Engl J Med. 2018;378:708–18. doi:10.1056/NEJMoa1713973",
 "Nogueira RG, Jadhav AP, Haussen DC, et al. Thrombectomy 6 to 24 hours after stroke with a mismatch between deficit and infarct. N Engl J Med. 2018;378:11–21. doi:10.1056/NEJMoa1706442",
 "Campbell BCV, Mitchell PJ, Kleinig TJ, et al. Endovascular therapy for ischemic stroke with perfusion-imaging selection. N Engl J Med. 2015;372:1009–18. doi:10.1056/NEJMoa1414792",
 "Laredo C, Renú A, Tudela R, et al. The accuracy of ischemic core perfusion thresholds varies according to time to recanalization in stroke patients treated with mechanical thrombectomy. J Cereb Blood Flow Metab. 2020;40:966–77. doi:10.1177/0271678X19855885",
 "Brugnara G, Neuberger U, Mahmutoglu MA, et al. Multimodal predictive modeling of endovascular treatment outcome for acute ischemic stroke using machine-learning. Stroke. 2020;51:3541–51. doi:10.1161/STROKEAHA.120.030287",
 "Nishi H, Oishi N, Ishii A, et al. Predicting clinical outcomes of large vessel occlusion before mechanical thrombectomy using machine learning. Stroke. 2019;50:2379–88. doi:10.1161/STROKEAHA.119.025411",
 "van Os HJA, Ramos LA, Hilbert A, et al. Predicting outcome of endovascular treatment for acute ischemic stroke: potential value of machine learning algorithms. Front Neurol. 2018;9:784. doi:10.3389/fneur.2018.00784",
 "Zeng M, Oakden-Rayner L, Bird A, et al. Pre-thrombectomy prognostic prediction of large-vessel ischemic stroke using machine learning: a systematic review and meta-analysis. Front Neurol. 2022;13:945813. doi:10.3389/fneur.2022.945813",
 "Christodoulou E, Ma J, Collins GS, Steyerberg EW, Verbakel JY, Van Calster B. A systematic review shows no performance benefit of machine learning over logistic regression for clinical prediction models. J Clin Epidemiol. 2019;110:12–22. doi:10.1016/j.jclinepi.2019.02.004",
 "Borsos B, Allaart CG, van Halteren A. Predicting stroke outcome: a case for multimodal deep learning methods with tabular and CT perfusion data. Artif Intell Med. 2024;147:102719. doi:10.1016/j.artmed.2023.102719",
 "Jiang B, Zhu G, Xie Y, et al. Prediction of clinical outcome in patients with large-vessel acute ischemic stroke: performance of machine learning versus SPAN-100. AJNR Am J Neuroradiol. 2021;42:240–6. doi:10.3174/ajnr.A6918",
 "Collins GS, Moons KGM, Dhiman P, et al. TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. BMJ. 2024;385:e078378. doi:10.1136/bmj-2023-078378",
 "Tejani AS, Klontzas ME, Gatti AA, et al. Checklist for Artificial Intelligence in Medical Imaging (CLAIM): 2024 update. Radiol Artif Intell. 2024;6:e240300. doi:10.1148/ryai.240300",
 "Riley RD, Ensor J, Snell KIE, et al. Calculating the sample size required for developing a clinical prediction model. BMJ. 2020;368:m441. doi:10.1136/bmj.m441",
 "Riley RD, Snell KIE, Ensor J, et al. Minimum sample size for developing a multivariable prediction model: part II – binary and time-to-event outcomes. Stat Med. 2019;38:1276–96. doi:10.1002/sim.7992",
 "Van Calster B, Nieboer D, Vergouwe Y, et al. A calibration hierarchy for risk models was defined: from utopia to empirical data. J Clin Epidemiol. 2016;74:167–76. doi:10.1016/j.jclinepi.2015.12.005",
 "Van Calster B, McLernon DJ, van Smeden M, Wynants L, Steyerberg EW. Calibration: the Achilles heel of predictive analytics. BMC Med. 2019;17:230. doi:10.1186/s12916-019-1466-7",
 "Vickers AJ, Elkin EB. Decision curve analysis: a novel method for evaluating prediction models. Med Decis Making. 2006;26:565–74. doi:10.1177/0272989X06295361",
 "Vickers AJ, van Calster B, Steyerberg EW. A simple, step-by-step guide to interpreting decision curve analysis. Diagn Progn Res. 2019;3:18. doi:10.1186/s41512-019-0064-7",
 "DeLong ER, DeLong DM, Clarke-Pearson DL. Comparing the areas under two or more correlated receiver operating characteristic curves: a nonparametric approach. Biometrics. 1988;44:837–45. doi:10.2307/2531595",
 "Pencina MJ, D'Agostino RB Sr, D'Agostino RB Jr, Vasan RS. Evaluating the added predictive ability of a new marker: from area under the ROC curve to reclassification and beyond. Stat Med. 2008;27:157–72. doi:10.1002/sim.2929",
 "Kerr KF, Wang Z, Janes H, et al. Net reclassification indices for evaluating risk prediction instruments: a critical review. Epidemiology. 2014;25:114–21. doi:10.1097/EDE.0000000000000018",
 "Hilden J, Gerds TA. A note on the evaluation of novel biomarkers: do not rely on integrated discrimination improvement and net reclassification index. Stat Med. 2014;33:3405–14. doi:10.1002/sim.5804",
 "Varma S, Simon R. Bias in error estimation when using cross-validation for model selection. BMC Bioinformatics. 2006;7:91. doi:10.1186/1471-2105-7-91",
 "Cawley GC, Talbot NLC. On over-fitting in model selection and subsequent selection bias in performance evaluation. J Mach Learn Res. 2010;11:2079–107.",
 "Lundberg SM, Erion G, Chen H, et al. From local explanations to global understanding with explainable AI for trees. Nat Mach Intell. 2020;2:56–67. doi:10.1038/s42256-019-0138-9",
 "Harrell FE Jr, Lee KL, Mark DB. Multivariable prognostic models: issues in developing models, evaluating assumptions and adequacy, and measuring and reducing errors. Stat Med. 1996;15:361–87.",
 "Saver JL, Gornbein J. Treatment effects for which shift or binary analyses are advantageous in acute stroke trials. Neurology. 2009;72:1310–5. doi:10.1212/01.wnl.0000341308.73506.b7",
 "Bath PM, Lees KR, Schellinger PD, et al. Statistical analysis of the primary outcome in acute stroke trials. Stroke. 2012;43:1171–8. doi:10.1161/STROKEAHA.111.641456",
 "Cereda CW, Christensen S, Campbell BCV, et al. A benchmarking tool to evaluate computer tomography perfusion infarct core predictions against a DWI standard. J Cereb Blood Flow Metab. 2016;36:1780–9. doi:10.1177/0271678X15610586",
 "Hakim A, Christensen S, Winzeck S, et al. Predicting infarct core from computed tomography perfusion in acute ischemia with machine learning: lessons from the ISLES challenge. Stroke. 2021;52:2328–37. doi:10.1161/STROKEAHA.120.030696",
 "Meier P, Zierler KL. On the theory of the indicator-dilution method for measurement of blood flow and volume. J Appl Physiol. 1954;6:731–44. doi:10.1152/jappl.1954.6.12.731",
 "Arenillas JF, Cortijo E, García-Bermejo P, et al. Relative cerebral blood volume is associated with collateral status and infarct growth in stroke patients in SWIFT PRIME. J Cereb Blood Flow Metab. 2018;38:1839–47. doi:10.1177/0271678X17740293",
 "Venema E, Mulder MJHL, Roozenbeek B, et al. Selection of patients for intra-arterial treatment for acute ischaemic stroke: development and validation of a clinical decision tool in two randomised trials. BMJ. 2017;357:j1710. doi:10.1136/bmj.j1710",
 "Pedregosa F, Varoquaux G, Gramfort A, et al. Scikit-learn: machine learning in Python. J Mach Learn Res. 2011;12:2825–30.",
 "Orlhac F, Eertink JJ, Cottereau AS, et al. A guide to ComBat harmonization of imaging biomarkers in multicenter studies. J Nucl Med. 2022;63:172–9. doi:10.2967/jnumed.121.262464",
 "Moons KGM, Damen JAA, Kaul T, et al. PROBAST+AI: an updated quality, risk of bias, and applicability assessment tool for prediction models using regression or artificial intelligence methods. BMJ. 2025;388:e082505. doi:10.1136/bmj-2024-082505",
 "Hoang TB, Nguyen KT, Nguyen BT. Machine learning for 90-day functional outcome prognosis in ischemic stroke: a 22-predictor clinical-only gradient boosting model. Manuscript submitted.",
 "hugging-science. ISLES'24 stroke training dataset (per-subject Parquet mirror of the ISLES'24 Zenodo release). Hugging Face; 2025. https://huggingface.co/datasets/hugging-science/isles24-stroke",
 "Walker E, Nowacki AS. Understanding equivalence and noninferiority testing. J Gen Intern Med. 2011;26:192–6. doi:10.1007/s11606-010-1513-8",
 "Rubin DB. The Bayesian bootstrap. Ann Stat. 1981;9:130–4. doi:10.1214/aos/1176345338",
 "Debray TPA, Vergouwe Y, Koffijberg H, Nieboer D, Steyerberg EW, Moons KGM. A new framework to enhance the interpretation of external validation studies of clinical prediction models. J Clin Epidemiol. 2015;68:279–89. doi:10.1016/j.jclinepi.2014.06.018",
 "Abraham A, Pedregosa F, Eickenberg M, et al. Machine learning for neuroimaging with scikit-learn. Front Neuroinform. 2014;8:14. doi:10.3389/fninf.2014.00014",
 "Lowekamp BC, Chen DT, Ibáñez L, Blezek D. The design of SimpleITK. Front Neuroinform. 2013;7:45. doi:10.3389/fninf.2013.00045",
 "Eickhoff SB, Stephan KE, Mohlberg H, et al. A new SPM toolbox for combining probabilistic cytoarchitectonic maps and functional imaging data. NeuroImage. 2005;25:1325–35. doi:10.1016/j.neuroimage.2004.12.034",
 "Desikan RS, Ségonne F, Fischl B, et al. An automated labeling system for subdividing the human cerebral cortex on MRI scans into gyral based regions of interest. NeuroImage. 2006;31:968–80. doi:10.1016/j.neuroimage.2006.01.021",
 "Cheng B, Forkert ND, Zavaglia M, et al. Influence of stroke infarct location on functional outcome measured by the modified Rankin scale. Stroke. 2014;45:1695–702. doi:10.1161/STROKEAHA.114.005152",
 "Boers AMM, Jansen IGH, Beenen LFM, et al. Association of follow-up infarct volume with functional outcome in acute ischemic stroke: a pooled analysis of seven randomized trials. J Neurointerv Surg. 2018;10:1137–42. doi:10.1136/neurintsurg-2017-013724",
 "Rangaraju S, Frankel M, Jovin TG. Prognostic value of the 24-hour neurological examination in anterior circulation ischemic stroke: a post hoc analysis of two randomized controlled stroke trials. Interv Neurol. 2016;4:120–9. doi:10.1159/000443801",
]
H("References")
for i, r in enumerate(REFS, 1):
    doc.add_paragraph(f"{i}. {r}").paragraph_format.line_spacing = 1.15

# ------------------------------------------------------------------ tables
doc.add_page_break(); H("Tables")
sel = ["N", "Age, median [IQR]", "Sex, n (%)", "NIHSS at admission, median [IQR]", "mRS premorbid, median [IQR]",
       "mRS at admission, median [IQR]", "Wake-up, n (%)", "Referral, n (%)", "Atrial fibrillation, n (%)",
       "Hypertension, n (%)", "Diabetes, n (%)", "Anticoagulation, n (%)", "Glucose, median [IQR]", "CRP, median [IQR]",
       "Door to imaging_min, median [IQR]", "THRIVE, median [IQR]", "SPAN100_raw, median [IQR]",
       "core_rcbf30_hypo_frac, median [IQR]", "tmax_gt6_frac, median [IQR]", "tmax_gt10_frac, median [IQR]", "hir, median [IQR]",
       "cbv_index_hypo, median [IQR]", "rcbv_ipsi_ratio, median [IQR]", "Post-interventional mTICI, n"]
t1s = t1[t1.variable.isin(sel)].copy()
t1s["variable"] = (t1s.variable.str.replace("core_rcbf30_hypo_frac", "Core rCBF<30% (% tissue)")
                   .str.replace("tmax_gt6_frac", "Tmax>6 s (% tissue)").str.replace("tmax_gt10_frac", "Tmax>10 s (% tissue)")
                   .str.replace("hir", "HIR").str.replace("cbv_index_hypo", "CBV index").str.replace("rcbv_ipsi_ratio", "Ipsilateral rCBV ratio")
                   .str.replace("_min", " (min)").str.replace("SPAN100_raw", "SPAN-100 (age+NIHSS)").str.replace("Sex", "Sex (male)"))
table(t1s, "Table 1. Characteristics of the analysed cohort by 90-day outcome (N = 129). Sex coded 1 = male "
      "(verified against the text labels of the original release). CRP in mg/dL. Laboratory values contain ±5% anonymisation noise and "
      "release-level median imputation (Additional file 2). P: Fisher exact / Mann–Whitney.")
order = ["THRIVE", "SPAN100", "NIHSS_only", R1, "P2_clin_EN", P1, PR, "A_CBF", "B_CBV", "C_MTT", "D_Tmax", TT, E,
         "E_native", "V_volumes", "F_EN_clin_CTP", "F_GBM_clin_thresh", "F_late_P1_T", F, "F_late_R1_E",
         "F_late_P1recal_E", "F_late_P1_Enat", "F_late_P1_V", "R1_plus_volumes"]
names = {"THRIVE": "THRIVE", "SPAN100": "SPAN-100", "NIHSS_only": "NIHSS only", "P2_clin_EN": "P2 clinical elastic net",
         P1: "P1 clinical GBM", "A_CBF": "A CBF", "B_CBV": "B CBV", "C_MTT": "C MTT", "D_Tmax": "D Tmax", TT: "T classical thresholds",
         E: "E all CTP channels", "F_EN_clin_CTP": "Clinical+CTP elastic net", "F_GBM_clin_thresh": "Clinical+thresholds GBM",
         "F_late_P1_T": "P1+T fusion", F: "F P1+E fusion", R1: "R1 4-predictor logistic", PR: "P1 recalibrated",
         "E_native": "E native-unit features", "V_volumes": "V absolute volumes (mL)", "F_late_R1_E": "R1+E fusion",
         "F_late_P1recal_E": "P1-recal+E fusion", "F_late_P1_Enat": "P1+E-native fusion", "F_late_P1_V": "P1+V fusion",
         "R1_plus_volumes": "R1+V logistic"}
t2 = pd.DataFrame([{"Model": names[m], "AUC seed-mean (95% CI)": f"{r.auc_seed_mean:.3f} ({r.auc_ci_lo:.3f}–{r.auc_ci_hi:.3f})",
                    "Seed SD": f"{r.auc_seed_sd:.3f}", "Pooled AUC": f"{r.auc_pooled:.3f}", "AUPRC": f"{r.auprc_pooled:.3f}",
                    "Brier": f"{r.brier_seed_mean:.3f}", "Slope (95% CI)": f"{r.pooled_slope:.2f} ({r.pooled_slope_lo:.2f}–{r.pooled_slope_hi:.2f})",
                    "CITL": f"{r.pooled_citl:.2f}", "ICI": f"{r.pooled_ici:.3f}", "Sens/Spec @0.5": f"{r.thr50_sens:.2f}/{r.thr50_spec:.2f}"}
                   for m, r in ((m, perf.loc[m]) for m in order)])
table(t2, "Table 2. Discrimination and calibration of all models (5 repeats × stratified 10-fold nested CV; outcome mRS 3–6). "
      "AUC CIs: 2,000 patient-level bootstrap resamples carrying all seeds. Calibration on seed-averaged OOF probabilities.", font=7)
rows = []
for new, ref in [(F, P1), ("F_late_R1_E", R1), ("F_late_P1recal_E", PR), ("F_late_P1_Enat", P1), ("F_late_P1_V", P1),
                 ("R1_plus_volumes", R1), ("F_EN_clin_CTP", P1), ("F_GBM_clin_thresh", P1), (E, TT), ("B_CBV", "A_CBF"),
                 ("D_Tmax", "A_CBF"), (P1, "THRIVE"), (P1, "SPAN100"), (P1, R1)]:
    r = comp[(comp.new == new) & (comp.reference == ref)].iloc[0]
    d = dnb[(dnb.new == new) & (dnb.reference == ref)]
    nb = "; ".join(f"{t:.2f}: {x.delta_nb:+.3f}" for t, x in zip(d.threshold, d.itertuples())) if len(d) else "–"
    rows.append({"Comparison": f"{names[new]} vs {names[ref]}", "ΔAUC (95% CI)": f"{r.delta_auc:+.3f} ({r.ci_lo:+.3f}, {r.ci_hi:+.3f})",
                 "P bootstrap": pv(r.p_bootstrap), "P DeLong": pv(r.p_delong_pooled), "ΔNB at 0.20; 0.35; 0.50": nb})
table(pd.DataFrame(rows), "Table 3. Prespecified paired comparisons (ΔAUC on the primary estimand; ΔNB on seed-averaged probabilities).", font=7.5)

# ------------------------------------------------------------------ figures
doc.add_page_break(); H("Figures")
legends = {
 "Fig1_flow_pipeline": "Fig. 1. Study flow and analysis pipeline.",
 "Fig2_unit_recovery_validation": "Fig. 2. Physical-unit recovery and technical validation. (a) Central volume theorem in ISLES'24; (b) recovered/true scale in the ISLES 2018 simulation; (c) feature-level ICC between true and recovered maps; (d) example recovered Tmax map with Tmax >6 s contour.",
 "Fig3_auc_forest": "Fig. 3. Discrimination of all models (mean of five seed-specific out-of-fold AUCs, 95% patient-bootstrap CI). Dashed line: clinical GBM (P1).",
 "Fig4_roc": "Fig. 4. ROC curves from seed-averaged out-of-fold probabilities.",
 "Fig5_calibration": "Fig. 5. LOESS calibration curves and distributions of predicted risk.",
 "Fig6_dca": "Fig. 6. Decision curve analysis for predicting poor 90-day outcome.",
 "Fig7_interpretability": "Fig. 7. Channel contribution and interpretability. (a) Share of standardised coefficient mass by channel in the all-channel model; (b) single-channel and leave-one-channel-out AUCs; (c) TreeSHAP for the clinical + threshold GBM on outer-test patients.",
 "Fig8_robustness": "Fig. 8. Incremental value of CTP across analytic settings: ΔAUC with 95% bootstrap CI for adding CTP to the clinical reference in the pooled nested CV (blue) and in centre-aware analyses (orange). Shaded band: equivalence margin ±0.05.",
 "Fig9_timeline": "Fig. 9. Prognostic information across the care pathway (second analysis plan). (a) Munich: admission model, + 24-h NIHSS, + follow-up DWI infarct volume, each without (blue) and with (orange) pre-treatment CTP. (b) Full cohort: pre-treatment versus post-imaging models. AUC = mean of five seed-specific out-of-fold AUCs with 95% patient-bootstrap CI.",
 "FigS1_sensitivity_delta_auc": "Fig. S1. Sensitivity analyses: ΔAUC of multimodal fusion over the clinical GBM.",
 "FigS2_subgroups": "Fig. S2. Exploratory subgroup analyses: ΔAUC of fusion F over the clinical GBM within subgroups, with P values for interaction.",
 "FigS3_native_agreement": "Fig. S3. Agreement between features from recovered units (public pre-processed release) and from native-unit maps (original release): (a) ICC per feature by channel; (b, c) examples.",
 "FigS4_atlas_registration_qc": "Fig. S4. Atlas registration quality: the patients with the lowest, median and highest registration Dice. Contours: corticospinal tract (orange), deep grey matter (green), insula/operculum (yellow), language cortex (pink), DWI infarct (blue).",
}
for k, v in legends.items():
    doc.add_picture(str(FIG / f"{k}.png"), width=Inches(6.0)); doc.add_paragraph(v)

H("Additional files")
Pp("Additional file 1: TRIPOD+AI checklist (Branch3_TRIPOD_AI_checklist.docx).")
Pp("Additional file 2: Supplementary tables S1–S16 (feature dictionary, missingness, included vs excluded, ISLES 2018 "
   "agreement, all models and comparisons, coefficients, TreeSHAP, Riley sample size, ordinal and cut-point analyses, "
   "sensitivity analyses, native-unit agreement and volumes, precision/equivalence, centre inference, case mix and "
   "imputation by centre, within-centre AUC, Munich-only CV, leave-one-centre-out validation, subgroups, timeline, "
   "location and occlusion-population models; Branch3_Additional_file_2.xlsx).")
Pp("Additional file 3: Second analysis plan, written before the timeline, location and occlusion-population analyses "
   "(Branch3_Additional_file_3_analysis_plan.docx).")
out = OUT / "Branch3_Manuscript_BMC_MIDM_v3_full_backup.docx"
doc.save(out); print("saved", out)

