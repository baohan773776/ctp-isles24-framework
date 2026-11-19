"""Builds the BMC Medical Informatics and Decision Making manuscript (framework / feasibility version, .docx).
Every number is read from outputs/tables at build time. References are numbered automatically in order of first
citation. The previous full-length version is kept in s11_manuscript_v3_full.py.
Content revised after the evidence audit of 2026-11-12 (audit_final/).

HISTORICAL (2026-11-14): builds a superseded manuscript version. The current submission manuscript is built by
validity/w09_final_manuscript.py -> validity/w13_targeted_repair.py (see README.md)."""
import os as _os
import sys as _sys
if _os.environ.get("BRANCH3_ALLOW_HISTORICAL") != "1":
    _sys.exit("Historical script (superseded manuscript version); set BRANCH3_ALLOW_HISTORICAL=1 to run it anyway.")
import ast
import json
import re
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Cm, Inches
from config import TAB, FIG, OUT, DATA, ROOT

# ------------------------------------------------------------------ data
T = lambda f: pd.read_csv(TAB / f)
perf = T("performance_all_models_all.csv").set_index("model")
comp = T("paired_auc_comparisons_all.csv")
dnb = T("dca_delta_nb_all.csv")
qc = json.load(open(TAB / "ctp_qc_summary.json"))
agr = T("isles2018_feature_agreement.csv").set_index("feature")
miss = T("missingness_probable_imputed.csv").set_index("variable")
riley = T("sample_size_riley.csv")
stab = T("coef_rank_stability.csv").set_index("model")
po = pd.read_csv(TAB / "ordinal_proportional_odds.csv", index_col=0).iloc[:, 0]
gap = T("overfit_gap.csv").set_index("model")
t1 = T("table1_by_outcome.csv")
prec = T("precision_equivalence.csv").set_index("new")
wca = T("within_centre_auc.csv").set_index("model")
wcp = T("within_centre_paired.csv")
geo = T("geographic_validation_performance.csv"); geop = T("geographic_validation_paired.csv")
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
ss = T("design_sample_size.csv"); rly = T("design_riley.csv"); gng = T("go_nogo.csv")
sens = {k: T(f"paired_vs_P1_clin_GBM{k}.csv").set_index("model")
        for k in ["_sens_features", "_sens_missing", "_sens_tmaxcertain", "_5fold", "_sens_scalefree", "_sens_nestedgbm"]}
nest_perf = T("performance_all_models_sens_nestedgbm.csv").set_index("model")
nest_comp = T("paired_auc_comparisons_sens_nestedgbm.csv")
nest_par = pd.read_csv(OUT / "oof" / "inner_best_params_sens_nestedgbm.csv")
nest_par = nest_par[nest_par.model == "P1_nested_GBM"]
N_GBM_GRID = int(np.prod([len(v) for v in __import__("s04_models_cv").GBM_GRID.values()]))
# share of the 50 training folds in which the inner search selected exactly the companion configuration
LOCKED = {"n_estimators": 80, "max_depth": 3, "learning_rate": 0.1, "subsample": 0.7}
N_LOCKED_SEL = int(np.all([np.isclose(nest_par[k].astype(float), v) for k, v in LOCKED.items()], axis=0).sum())
N_FOLDS_NEST = len(nest_par)
locf = pd.read_csv(DATA / "location_features.csv")
locf = locf[locf.subject_id.isin(pd.read_csv(DATA / "cohort_129.csv").subject_id)]
_coh_ids = pd.read_csv(DATA / "cohort_129.csv").subject_id
ctpq = pd.read_csv(DATA / "ctp_features_v3_149.csv"); ctpq = ctpq[ctpq.subject_id.isin(_coh_ids)]
N_TMAX_CEIL = int((ctpq.qc_Tmax_n_at_ceiling >= 2).sum()); N_MTT_CEIL = int((ctpq.qc_MTT_n_at_ceiling >= 2).sum())
N_DEGEN = int(ctpq.qc_degenerate_norm.sum()); N_TMAXCERT = int(((ctpq.qc_Tmax_n_at_ceiling >= 2) & (~ctpq.qc_degenerate_norm.astype(bool))).sum())
sexck = pd.read_csv(TAB / "sex_coding_check.csv", index_col=0); N_SEX = int(sexck.values.sum())


def icc31(a, b):
    """Two-way mixed, single measures, consistency ICC(3,1)."""
    x = np.column_stack([a, b]); n, k = x.shape
    ms_r = k * x.mean(1).var(ddof=1); ms_e = ((x - x.mean(1, keepdims=True) - x.mean(0) + x.mean()) ** 2).sum() / ((n - 1) * (k - 1))
    return (ms_r - ms_e) / (ms_r + (k - 1) * ms_e)


_nat = pd.read_csv(DATA / "ctp_features_native_149.csv").set_index("subject_id").loc[ctpq.subject_id]
_rec = ctpq.set_index("subject_id")
_ceil = (_rec.qc_Tmax_n_at_ceiling >= 2).values
_natcol = "nat_tmax_gt6_frac" if "nat_tmax_gt6_frac" in _nat.columns else "tmax_gt6_frac"
ICC_T6_CEIL = icc31(_rec.tmax_gt6_frac.values[_ceil], _nat[_natcol].values[_ceil])
ICC_T6_NOCEIL = icc31(_rec.tmax_gt6_frac.values[~_ceil], _nat[_natcol].values[~_ceil])

# ------------------------------------------------------------------ references (auto-numbered)
_old = (ROOT / "s11_manuscript_v3_full.py").read_text(encoding="utf-8")
_REFLIST = ast.literal_eval(re.search(r"REFS = (\[.*?\n\])", _old, re.S).group(1))
KEYS = ["gbd", "goyal", "isles24", "delarosa", "thrive10", "thrive13", "span100", "kremers", "hermes", "campbell11",
        "olivot09", "olivot14", "defuse3", "dawn", "extend", "laredo", "brugnara", "nishi", "vanos", "zeng",
        "christodoulou", "borsos", "jiang", "tripodai", "claim", "riley20", "riley19", "vancalster16", "vancalster19",
        "vickers06", "vickers19", "delong", "pencina", "kerr", "hilden", "varma", "cawley", "lundberg", "harrell",
        "saver09", "bath12", "cereda", "hakim", "meier", "arenillas", "venema", "pedregosa", "orlhac", "probastai",
        "branch2", "hfmirror", "walker", "rubin", "debray", "nilearn", "simpleitk", "juelich", "desikan", "cheng",
        "boers", "rangaraju"]
assert len(KEYS) == len(_REFLIST)
REF = dict(zip(KEYS, _REFLIST))
REF["eldridge"] = ("Eldridge SM, Lancaster GA, Campbell MJ, et al. Defining feasibility and pilot studies in preparation "
                   "for randomised controlled trials: development of a conceptual framework. PLoS One. 2016;11:e0150205. "
                   "doi:10.1371/journal.pone.0150205")
REF["buergel"] = ("Bürgel U, Amunts K, Hoemke L, Mohlberg H, Gilsbach JM, Zilles K. White matter fiber tracts of the human "
                  "brain: three-dimensional mapping at microscopic resolution, topography and intersubject variability. "
                  "NeuroImage. 2006;29:1092–105. doi:10.1016/j.neuroimage.2005.08.040")
ORDER = []


def C(*keys):
    nums = []
    for k in keys:
        if k not in ORDER:
            ORDER.append(k)
        nums.append(ORDER.index(k) + 1)
    nums = sorted(nums); out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(f"{nums[i]}–{nums[j]}" if j - i >= 2 else ", ".join(str(n) for n in nums[i:j + 1]))
        i = j + 1
    return "[" + ", ".join(out) + "]"


# ------------------------------------------------------------------ formatting helpers
def f3(x): return f"{x:.3f}"
def f2(x): return f"{x:.2f}"
def pv(p): return "<0.001" if p < 0.001 else f"{p:.3f}"
def sg(x):
    s = f"{x:+.3f}"
    return "0.000" if s in ("+0.000", "-0.000") else s.replace("-", "−")
def ci(lo, hi): return f"95% CI {sg(lo)} to {sg(hi)}"
def auc(m, src=perf): r = src.loc[m]; return f"{f3(r.auc_seed_mean)} (95% CI {f3(r.auc_ci_lo)}–{f3(r.auc_ci_hi)})"
def d(new, ref, src=comp):
    r = src[(src.new == new) & (src.reference == ref)].iloc[0]
    return f"ΔAUC {sg(r.delta_auc)} ({ci(r.ci_lo, r.ci_hi)})"
def dwc(new, ref):
    r = wcp[(wcp.new == new) & (wcp.reference == ref)].iloc[0]; return f"Δ {sg(r.delta_within)} ({ci(r.ci_lo, r.ci_hi)})"
def tl(s, m): r = tlp[(tlp.set == s) & (tlp.model == m)].iloc[0]; return f"{f3(r.auc)} (95% CI {f3(r.auc_lo)}–{f3(r.auc_hi)})"
def tlr(s, m): return tlp[(tlp.set == s) & (tlp.model == m)].iloc[0]
def td(s, new, ref, src=tlc):
    r = src[(src.set == s) & (src.new == new) & (src.reference == ref)].iloc[0]
    return f"ΔAUC {sg(r.delta_auc)} ({ci(r.ci_lo, r.ci_hi)})"
def gp(direction, m):
    r = geo[(geo.direction == direction) & (geo.model == m)].iloc[0]; return f"{f3(r.auc)} (95% CI {f3(r.auc_lo)}–{f3(r.auc_hi)})"
def hp(key): return holm[holm.role.str.contains(key)].iloc[0]
def vol(v, s="50%"): return nvol.loc[v, s]


P1, F, E, TT, R1, PR = "P1_clin_GBM", "F_late_P1_E", "E_CTP_all", "T_thresholds", "R1_clin_LR4", "P1_recal"
SA, SB, SBC = "A: full cohort", "B: Munich", "B: Munich, complete NIHSS 24 h"
H1S, H1D, H2S = "H1: full cohort", "H1: registration Dice >= 0.80", "H2: LVO population"
pF = prec.loc[F]; h1, h2, h3 = hp("PRIMARY H1"), hp("PRIMARY H2"), hp("PRIMARY H3")
zur_n, mun_n = int(cmix.loc["Zurich", "n"]), int(cmix.loc["Munich", "n"])
zur_ev, mun_ev = int(cmix.loc["Zurich", "poor"]), int(cmix.loc["Munich", "poor"])
lab_imp_z = min(simp.loc[v, "pct_imputed_Zurich"] for v in ["CRP", "Leucocytes", "INR", "Onset to door_min"])
lab_imp_m = max(simp.loc[v, "pct_imputed_Munich"] for v in ["CRP", "Leucocytes", "INR"])
ssc = ss.iloc[0]; ssd = ss[ss.comparison.str.startswith("Follow-up infarct volume added to admission")].iloc[0]
r80 = rly[(np.isclose(rly.anticipated_auc, 0.80))].set_index("parameters")
r75 = riley[np.isclose(riley.anticipated_auc, 0.75)].iloc[0]
MZ = "Munich -> Zurich"
# eight sensitivity analyses: 5x5-fold, Tmax-certain subset, scale-free features (corrected list, run _sens_scalefree),
# PCA, compact physiological set, CBV-only partner, missing indicators, and native-unit features (reported separately)
sens_d = [sens["_5fold"].loc[F].delta_auc, sens["_sens_tmaxcertain"].loc[F].delta_auc,
          sens["_sens_scalefree"].loc["F_late_P1_Esf"].delta_auc, sens["_sens_features"].loc["F_late_P1_EPCA"].delta_auc,
          sens["_sens_features"].loc["F_late_P1_Ephys"].delta_auc, sens["_sens_features"].loc["F_late_P1_CBV"].delta_auc,
          sens["_sens_missing"].loc["F_late_P1miss_E"].delta_auc]
DEF_N = int(max(r80.loc[6, "n_minimum"], ssc["n_for_delta_0.05"]))
DEF_N = int(np.ceil(DEF_N / 10) * 10)
DEF_EV = int(np.ceil(DEF_N * 44 / 129 / 5) * 5)

# ------------------------------------------------------------------ document
doc = Document()
st = doc.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(11)
st.paragraph_format.line_spacing = 1.5; st.paragraph_format.space_after = Pt(4)
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.5)


def H(t, l=1): doc.add_heading(t, level=l)
def Pp(t, lead=None):
    """Paragraph; text in [square brackets] is an author-completed field and is highlighted."""
    from docx.enum.text import WD_COLOR_INDEX
    p = doc.add_paragraph()
    if lead:
        p.add_run(lead).bold = True
    for part in re.split(r"(\[[A-Z][^\]]*\])", t):
        if part:
            r = p.add_run(part)
            if re.fullmatch(r"\[[A-Z][^\]]*\]", part):
                r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return p


def table(df, caption, font=8):
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
p.add_run("A reproducible framework for evaluating the incremental prognostic value of CT perfusion after "
          "thrombectomy: feasibility study on the public ISLES'24 dataset and design parameters for a definitive "
          "study").bold = True
Pp("Tran Bao Hoang¹, Kiet Tuan Nguyen¹, Bao Thien Nguyen¹*")
Pp("¹ Institute of Intelligent and Interactive Technologies (3i Institute), College of Technology and Design, University of "
   "Economics Ho Chi Minh City (UEH), Ho Chi Minh City, Vietnam")
Pp("* Corresponding author: baont@ueh.edu.vn")

# ------------------------------------------------------------------ abstract
H("Abstract")
Pp("Public multimodal stroke datasets invite prognostic modelling, but their small size, pre-processing and "
   "undocumented centre structure make it unclear what they can establish. We developed a reproducible framework "
   "to judge the feasibility of such studies and applied it to one question: does pre-treatment CT perfusion (CTP) "
   "add to clinical prediction of 90-day outcome after thrombectomy?", "Background: ")
Pp("We analysed 129 patients (44 with modified Rankin Scale 3–6) from the ISLES'24 training set. The framework has "
   "five modules: data readiness (M1), a locked nested cross-validation protocol with precision analysis (M2), signal "
   "estimation (M3), transportability across centres (M4) and design outputs for a definitive study (M5). "
   "Post-treatment, location and occlusion-population models followed a supplementary analysis plan finalised "
   "before those analyses.", "Methods: ")
Pp(f"Physical units of the normalised perfusion maps were recoverable (median ICC {nagr.icc31.median():.2f} against "
   f"native maps; Tmax scale identifiable in {N_TMAX_CEIL}/129 patients). Centres, unlabelled in the release, were "
   f"inferred from data provenance ({site['cluster_sizes']['quantised']}/{site['cluster_sizes']['float']}) and differed "
   f"in outcome rate ({mun_ev}/{mun_n} vs {zur_ev}/{zur_n}) and in release-level imputation. A clinical model reached "
   f"an AUC of {f3(perf.loc[P1].auc_seed_mean)} ({f3(nest_perf.loc['P1_nested_GBM'].auc_seed_mean)} when its configuration "
   f"was re-selected within folds); adding CTP changed "
   f"it by {sg(comp[(comp.new==F)&(comp.reference==P1)].delta_auc.iloc[0])} "
   f"({ci(comp[(comp.new==F)&(comp.reference==P1)].ci_lo.iloc[0], comp[(comp.new==F)&(comp.reference==P1)].ci_hi.iloc[0])}; "
   f"posterior probability of a gain >0.05: {pF['post_p_gt0.05']:.2f}). Equivalence within ±0.05 was not established, "
   f"so a modest benefit is not excluded; thresholds, volumes and location gave similar results, also within "
   f"centres. Post-treatment information showed larger increments: in one centre "
   f"the AUC rose from {tlr(SB,'R1_clin_LR4').auc:.2f} to {tlr(SB,'R1_N24').auc:.2f} with 24-h NIHSS and "
   f"{tlr(SB,'R1_N24_DWI').auc:.2f} with follow-up infarct volume; in the full cohort infarct volume added "
   f"{sg(h3.delta_auc)} ({ci(h3.ci_lo, h3.ci_hi)}; Holm-adjusted P = {h3.p_holm:.3f}). Transport to the smaller "
   f"centre was inconclusive ({zur_ev} events). A definitive study of the CTP question would need about {DEF_N} "
   f"patients (≈{DEF_EV} events), 24-h NIHSS, follow-up imaging, complete laboratory data and centre labels.",
   "Results: ")
Pp("In this feasibility study, pre-treatment CTP showed no statistically demonstrated incremental prognostic value "
   "after thrombectomy, although a modest gain could not be excluded, whereas the early post-treatment course showed "
   "a larger, borderline increment. The framework turns a small public dataset into explicit, post hoc go/no-go "
   "proposals and sample-size estimates for a definitive study.", "Conclusions: ")
Pp("acute ischaemic stroke; thrombectomy; CT perfusion; prognosis; feasibility; reproducibility; public datasets; "
   "calibration; ISLES 2024; TRIPOD+AI", "Keywords: ")

# ------------------------------------------------------------------ background
H("Background")
Pp(f"Endovascular thrombectomy is standard care for large-vessel occlusion stroke, yet many patients remain dependent "
   f"at 90 days despite successful reperfusion {C('goyal')}. Reliable prognosis supports counselling, rehabilitation "
   f"planning and trial design. Clinical scores such as THRIVE and SPAN-100 {C('thrive10', 'span100')} "
   f"discriminate only moderately when applied to thrombectomy cohorts {C('kremers')}. CT perfusion (CTP) quantifies the ischaemic core and "
   f"hypoperfused tissue and drives patient selection {C('campbell11', 'olivot09', 'defuse3', 'dawn')}, but its prognostic "
   f"value after reperfusion is uncertain: core volume, not mismatch, was associated with outcome in HERMES "
   f"{C('hermes')}, and machine-learning studies combining pre-treatment imaging, including CTP, with clinical "
   f"data have reported small or inconsistent gains "
   f"{C('brugnara', 'nishi', 'zeng', 'borsos')}.")
Pp(f"Public datasets such as ISLES'24 {C('isles24', 'delarosa')} make this question testable without new data "
   f"collection, but they are small and come with pre-processing choices that can silently change what is "
   f"measurable. In the widely redistributed pre-processed release, perfusion maps are z-normalised per patient, "
   f"which removes the physical units on which clinical thresholds rely, and centre identity is not labelled. A "
   f"single small study cannot settle the clinical question; it can, however, establish whether a definitive study "
   f"is warranted, which variables it needs and how large it must be. This is the role of a feasibility study "
   f"{C('eldridge')}.")
Pp("We therefore propose a five-module framework for feasibility studies of prognostic imaging biomarkers on public "
   "data, and apply it to pre-treatment CTP after thrombectomy. The modules assess data readiness (M1), fix a locked "
   "evaluation protocol with precision analysis (M2), estimate prognostic signal (M3), test transportability across "
   "centres (M4) and translate the estimates into design parameters and go/no-go decisions for a definitive study "
   "(M5) (Fig. 1).")

# ------------------------------------------------------------------ methods
H("Methods")
H("Design, data and reporting", 2)
Pp(f"This is a methodological framework and feasibility study using the public ISLES'24 training set (149 patients "
   f"treated with endovascular reperfusion; the dataset descriptor reports 100 training cases from Munich and 50 from "
   f"Zurich, of which 149 are in the public release) {C('isles24')}. "
   f"Perfusion maps (CBF, CBV, MTT, Tmax) were generated with icobrain cva and co-registered to non-contrast CT. "
   f"The primary analysis used the pre-processed release (64×128×128 grid) because it is widely redistributed; native-unit "
   f"maps, voxel sizes, follow-up diffusion-weighted imaging (DWI, 2–9 days after treatment) and lesion and "
   f"occlusion masks were read from a per-subject mirror of the original release {C('hfmirror')}. Patients with a "
   f"90-day modified Rankin Scale (mRS) score were included; the outcome was mRS 3–6 (poor) versus 0–2, and all "
   f"probabilities are P(poor). Reporting follows TRIPOD+AI {C('tripodai')} (Additional file 1) with CLAIM items for "
   f"imaging {C('claim')}. The cohort and clinical predictor set overlap with a companion clinical-only study "
   f"{C('branch2')}.")
H("M1 – Data readiness", 2)
Pp(f"Units. Each stored map equals z = (x − μ)/σ of the clipped clinical map x ∈ [0, c], where the clip limits "
   f"c = 100 mL/100 g/min for CBF, 10 mL/100 g for CBV and 30 s for MTT and Tmax are those recorded in the "
   f"pre-processing configuration distributed with the release. Because background is x = 0, "
   f"x = c·(z − z_min)/(z_max − z_min). This recovery is exact only when the clip ceiling c is reached by at least "
   f"one voxel of the resampled map; when it is not, the recovered scale is inflated by c/x_max, which affects "
   f"absolute Tmax (and MTT) values and the features derived from the Tmax >6 s mask, whereas features expressed "
   f"relative to the contralateral median are unaffected. The presence of the ceiling was therefore recorded per "
   f"channel and patient. We checked the recovery with the central volume theorem (MTT = 60·CBV/CBF) {C('meier')}, "
   f"which tests the combined CBF, CBV and MTT scales but not Tmax; by simulating an assumed version of the "
   f"pre-processing (clipping, trilinear resampling to the release grid, per-patient z-normalisation) on 94 ISLES "
   f"2018 cases {C('cereda', 'hakim')}; and, finally, at feature level against the native-unit maps of the original "
   f"release (ICC(3,1)); no voxelwise reconstruction accuracy was computed on ISLES'24. Fifty-three prespecified "
   f"ipsilateral perfusion features in five groups (CBF, CBV, MTT, Tmax, mismatch) were extracted (Additional file 4); "
   f"absolute volumes in mL (core rCBF <30% within Tmax >6 s, Tmax >6 s, mismatch) were computed from the native maps "
   f"and are limited to the CTP slab coverage.")
Pp("Clinical data. Twenty-two pre-procedural variables were back-transformed to physical units using the scaler "
   "parameters distributed with the release. Values equal to the stored training median were classified as "
   "probable release-level imputations. THRIVE and SPAN-100 were recomputed from raw values.")
Pp("Centres. Because centres are not labelled, we inferred them from an outcome-independent provenance signature "
   "of the original release, the storage precision of the perfusion maps (values quantised to 1/64 versus floating "
   "point), and checked the resulting clusters against CT slice thickness, CTP slab coverage, contiguous subject-ID "
   "blocks and the 100/50 split reported by the providers. The labels 'Munich' and 'Zurich' were assigned by "
   "matching cluster size to the descriptor; they are inferred, not independently verified, and all centre-level "
   "results should be read with this uncertainty.")
H("M2 – Locked evaluation protocol", 2)
Pp(f"All models were evaluated with nested cross-validation {C('varma', 'cawley')}: an outer stratified 10-fold loop "
   f"repeated with five seeds (one shared fold manifest) and an inner stratified 5-fold grid search for penalised "
   f"models; imputation and scaling were fitted inside training folds. The primary estimand was the mean of the five "
   f"seed-specific out-of-fold AUCs, with percentile 95% CIs from 2,000 patient-level bootstrap resamples in which "
   f"each resampled patient carries all five seed predictions; paired differences used the same resamples, and the "
   f"two-sided bootstrap P value is reported. DeLong tests {C('delong')} were computed on the per-patient mean of "
   f"the five probabilities as a supplementary check; they address the five-model ensemble rather than the primary "
   f"estimand and are reported only in Additional file 2. Because the bootstrap resamples stored out-of-fold "
   f"predictions without refitting, the intervals reflect patient sampling only and omit model-refitting "
   f"variability. Calibration (slope, calibration-in-the-large, Brier score, integrated calibration index) "
   f"{C('vancalster16', 'vancalster19')} and decision curves at threshold probabilities 0.20–0.50 "
   f"{C('vickers06', 'vickers19')} were assessed on the seed-averaged probabilities. Because a non-significant "
   f"difference does not show absence of benefit, each incremental value was summarised by its 90% CI against "
   f"equivalence margins of ±0.05 and ±0.03 AUC (two one-sided tests; equivalence is declared only when the 90% CI "
   f"lies entirely within the margin) {C('walker')}, Bayesian-bootstrap posterior probabilities of a gain "
   f"{C('rubin')} and the minimal detectable difference at 80% power (2.80 × bootstrap SE, a post hoc quantity). "
   f"Riley criteria defined how many parameters the cohort supports {C('riley20', 'riley19')}.")
H("M3 – Signal estimation", 2)
Pp(f"Pre-treatment models: P1, a clinical gradient-boosting machine on the 22 variables with the configuration locked "
   f"by the companion study (80 trees, depth 3, learning rate 0.1, subsample 0.7), which that study had selected by "
   f"non-nested cross-validation on the same cohort. Because this selection could bias P1's out-of-fold AUC, and the "
   f"direction of any effect on the CTP increment is not known a priori, a sensitivity analysis re-selected the GBM "
   f"configuration inside each training fold (inner 5-fold grid search over {N_GBM_GRID} configurations including the "
   f"locked one, minimising log-loss) and repeated the primary comparison against this nested-tuned reference. R1, a "
   f"parsimonious logistic model without tuning (age, admission NIHSS, premorbid mRS, glucose), provides a tuning-free "
   f"reference; single-channel "
   "elastic-net models (CBF, CBV, MTT, Tmax); E, an all-channel elastic net; T, a classical-threshold model (core, "
   "Tmax >6 s, mismatch ratio, hypoperfusion intensity ratio) {}; V, absolute volumes; and Loc, the fraction of four "
   "eloquent atlas regions (corticospinal tract, deep grey matter, insula/operculum, left language cortex) covered by "
   "Tmax >6 s tissue. CTP models were combined with clinical models by equal-weight averaging of probabilities "
   "(late fusion, no trainable fusion parameters). The prespecified primary comparison was P1 + E versus P1; "
   "robustness was checked against R1, a recalibrated P1, native-unit features and eight sensitivity analyses "
   "(Additional file 4).".format(C("olivot14")))
Pp(f"Three further hypotheses were tested under a supplementary analysis plan finalised before these analyses were "
   f"run (Additional file 3), with one primary comparison per hypothesis and Holm correction across the three "
   f"(bootstrap P values). H1 (location): adding CTP location to P1, with atlas regions carried to patient space by "
   f"affine registration of the MNI152 template to each patient's follow-up DWI "
   f"{C('nilearn', 'simpleitk', 'juelich', 'buergel', 'desikan')}. Because the registration target is a post-treatment "
   f"image, H1 is a retrospective anatomical analysis of where hypoperfusion lay, not an admission-time prediction "
   f"model that could be deployed as such; the lesion content of the DWI enters only the post-treatment location "
   f"models. H2 (occlusion population): the CTP increment within patients with a vessel-occlusion mask; because an "
   f"exploratory subgroup analysis suggested it, H2 is hypothesis-generating. H3 (post-treatment course): adding "
   f"follow-up DWI infarct volume to R1 in the full cohort, with the complete sequence admission → 24-h NIHSS → "
   f"follow-up infarct volume modelled in Munich, where 24-h NIHSS was recorded. H3 models describe updated prognosis "
   f"once post-treatment information exists and are not admission-time models.")
H("M4 – Transportability", 2)
Pp(f"Using the inferred centres we computed within-centre AUCs (concordance over patient pairs from the same centre, "
   f"which removes discrimination that merely reflects different outcome rates), repeated the nested CV within the "
   f"larger centre, and developed models in one centre for application to the other {C('debray')}.")
H("M5 – Design outputs", 2)
Pp("Two different sample sizes were derived. First, for each increment, the number of patients needed to detect "
   "ΔAUC = 0.03, 0.05 and 0.08 with 80% power (two-sided α = 0.05), obtained by scaling the paired-bootstrap SE by "
   "1/√n at the observed event rate; this assumes the same models, case mix and prediction correlation as in the "
   "present cohort and is a post hoc calculation. Second, the Riley minimum sample size for developing a new model "
   "with 4–20 candidate parameters (shrinkage ≥0.9 and intercept precision ±0.05). The two targets answer different "
   "questions and are reported separately (Table 4). A go/no-go table summarises, per research direction, the "
   "estimate and a proposed decision for a definitive study; these decisions were formulated after the estimates "
   "were known and are proposals, not progression criteria fixed in advance.")
H("Software", 2)
Pp(f"Python 3.10 with scikit-learn {C('pedregosa')}, statsmodels, SimpleITK, nilearn and nibabel. The analysis code "
   "regenerates every number, table and figure from the public data (see Availability of data and materials). An AI "
   "assistant (Claude, Anthropic) helped write analysis code and "
   "draft text; the authors reviewed all code, outputs and text and take full responsibility.")

# ------------------------------------------------------------------ results
H("Results")
nm = t1.set_index("variable")
H("Cohort and data readiness (M1)", 2)
Pp(f"Of 149 patients, 129 had a 90-day mRS (85 good, 44 poor; Table 1). Riley criteria supported only "
   f"≈{r75['max_params_for_shrinkage_0.9']:.1f} parameters at an anticipated AUC of 0.75, so the study is, by design, "
   f"a feasibility study.")
Pp(f"Unit recovery was confirmed by physical identity (median MTT/(60·CBV/CBF) {qc['cvt_ratio_median_of_medians']:.3f}), "
   f"in simulation (median ICC {agr.ICC_true_vs_recovered.median():.3f}) and against the native maps (median ICC "
   f"{nagr.icc31.median():.3f}, {int((nagr.icc31 >= 0.9).sum())}/{len(nagr)} features ≥0.90; Fig. 2). The clip "
   f"ceiling was present in the resampled map for all patients for CBF and CBV, for {N_MTT_CEIL}/129 for MTT and for "
   f"only {N_TMAX_CEIL}/129 for Tmax, and {N_DEGEN} patients had a CBF map that had evidently not been z-normalised; in "
   f"the {129 - N_TMAX_CEIL} patients without a Tmax ceiling the recovered Tmax scale is overestimated (feature-level "
   f"ICC for the Tmax >6 s fraction {ICC_T6_NOCEIL:.2f} versus {ICC_T6_CEIL:.3f} with the ceiling), which the Tmax-certain sensitivity "
   f"analysis (n = {N_TMAXCERT}) addresses by restriction rather than correction. The detected ipsilateral hemisphere "
   f"agreed with the native occlusion mask in {100*nval['ipsi_agrees_lvo']:.0f}% of patients, and the sex coding "
   f"(1 = male) agreed with the text labels of the original release in all {N_SEX} patients for whom a label was "
   f"available. Native volumes were small for the core (median {vol('core_ml'):.1f} mL) and large for Tmax >6 s tissue "
   f"(median {vol('tmax6_ml'):.0f} mL).")
Pp(f"The quantisation signature split the 149 patients into {site['cluster_sizes']['quantised']} and "
   f"{site['cluster_sizes']['float']}, consistent with the reported centre sizes of 100 and 50 (one of the 150 described "
   f"cases is absent from the release); the smaller cluster occupies one contiguous block of subject identifiers with "
   f"one exception, so an identifier-based split would give 100/49, and all "
   f"{site['crosstab_slice_mm']['4.0']['Zurich (inferred)']} patients with 4-mm CT slices fell in the smaller cluster. "
   f"The centres differed markedly: poor outcome {cmix.loc['Munich','poor_pct']:.0f}% vs "
   f"{cmix.loc['Zurich','poor_pct']:.0f}%, median age {cmix.loc['Munich','age_median']:.0f} vs "
   f"{cmix.loc['Zurich','age_median']:.0f} years, and probable release-level imputation of CRP, leucocytes, INR and "
   f"onset-to-door time in ≥{lab_imp_z:.0f}% of Zurich patients versus ≤{lab_imp_m:.0f}% for laboratory values in "
   f"Munich. Overall, imputation affected CRP ({miss.loc['CRP','pct']:.0f}%), INR ({miss.loc['INR','pct']:.0f}%) and "
   f"onset-to-door time ({miss.loc['Onset to door_min','pct']:.0f}%). The centre indicator alone had an AUC of "
   f"{wca.loc['Centre indicator alone','auc_pooled_seedmean']:.2f}.")
H("Incremental value of pre-treatment CTP (M2–M3)", 2)
Pp(f"The clinical GBM reached {auc(P1)} and the parsimonious model R1 {auc(R1)} (Table 2, Fig. 3). Pre-treatment CTP "
   f"alone discriminated poorly: all channels {f3(perf.loc[E].auc_seed_mean)}, classical thresholds "
   f"{f3(perf.loc[TT].auc_seed_mean)}, absolute volumes {f3(perf.loc['V_volumes'].auc_seed_mean)} and location "
   f"{f3(perf.loc['Loc_CTP'].auc_seed_mean)}. Among channels, CBV ranked first ({f3(perf.loc['B_CBV'].auc_seed_mean)}) "
   f"and CBF last ({f3(perf.loc['A_CBF'].auc_seed_mean)}; {d('B_CBV', 'A_CBF')}); CBV features carried "
   f"{100*stab.loc[E,'share_CBV']:.0f}% of the coefficient mass of model E.")
Pp(f"Adding CTP to P1 gave {d(F, P1)}, with a 90% CI of {sg(pF.ci90_lo)} to {sg(pF.ci90_hi)}. Because the upper "
   f"bound exceeds +0.05, equivalence within ±0.05 was not established and a gain of this size is not excluded; the "
   f"result shows no statistically demonstrated benefit rather than demonstrated absence of benefit. The posterior "
   f"probability of any gain was {pF.post_p_gt0:.2f}, and that of a gain above 0.05 was {pF['post_p_gt0.05']:.2f}; the minimal "
   f"detectable difference was {pF.mdd_80pct_power:.3f}. The increment stayed close to zero with R1 as reference "
   f"({d('F_late_R1_E', R1)}), with a recalibrated P1 ({d('F_late_P1recal_E', PR)}), with native-unit features "
   f"({d('F_late_P1_Enat', P1)}), with CTP location (primary H1: {td(H1S, 'F_loc', P1, llc)}; Holm-adjusted P = {h1.p_holm:.2f}) "
   f"and across eight sensitivity analyses (ΔAUC {sg(min(sens_d))} to {sg(max(sens_d))}). For absolute volumes only, "
   f"equivalence within ±0.05 was shown (90% CI {sg(prec.loc['F_late_P1_V'].ci90_lo)} to {sg(prec.loc['F_late_P1_V'].ci90_hi)}) "
   f"and a gain of 0.03 or more was excluded by the 95% upper bound ({d('F_late_P1_V', P1)}). Within "
   f"patients with an occlusion mask (127 of 129; H2, hypothesis-generating), the increment was {sg(h2.delta_auc)} "
   f"({ci(h2.ci_lo, h2.ci_hi)}; Holm-adjusted P = {h2.p_holm:.2f}). Fig. 4 summarises all settings.")
Pp(f"Re-selecting the GBM configuration inside each training fold gave a clinical reference with an AUC of "
   f"{auc('P1_nested_GBM', nest_perf)} versus {auc(P1, nest_perf)} for the locked configuration in the same run "
   f"({d('P1_nested_GBM', P1, nest_comp)}); the locked configuration was selected in {N_LOCKED_SEL} of {N_FOLDS_NEST} "
   f"training folds, and the nested-tuned model was better calibrated (slope {f2(nest_perf.loc['P1_nested_GBM'].pooled_slope)}). "
   f"This difference combines the optimism of a configuration chosen on the same cohort with the different selection "
   f"criterion used here (log-loss), so P1's absolute AUC should be read as optimistic by up to about "
   f"{abs(nest_comp[(nest_comp.new=='P1_nested_GBM')&(nest_comp.reference==P1)].delta_auc.iloc[0]):.2f}. Against the "
   f"nested-tuned reference the CTP increment was {d('F_late_P1nested_E', 'P1_nested_GBM', nest_comp)}, compared with "
   f"{d(F, P1, nest_comp)} against the locked P1 in the same run; the conclusion on CTP did not depend on how the "
   f"clinical reference was tuned.")
Pp(f"Fusion changed calibration more than discrimination: the GBM was overconfident (slope {f2(perf.loc[P1].pooled_slope)}, "
   f"apparent training AUC 1.00, train–test gap {gap.loc[P1,'gap']:.2f}), and averaging with CTP moved the slope to "
   f"{f2(perf.loc[F].pooled_slope)} (now underconfident), the Brier score from {f3(perf.loc[P1].pooled_brier)} to "
   f"{f3(perf.loc[F].pooled_brier)} and the integrated calibration index from {f3(perf.loc[P1].pooled_ici)} to "
   f"{f3(perf.loc[F].pooled_ici)} (all on seed-averaged probabilities), while the net benefit changed by "
   f"{sg(dnb[(dnb.new==F)&(dnb.reference==P1)&np.isclose(dnb.threshold,0.35)].delta_nb.iloc[0])} "
   f"at a threshold of 0.35 (Fig. 6; Additional file 4). Decision curves describe net benefit under stated "
   f"thresholds and do not demonstrate patient benefit or clinical readiness. Exploratory analyses suggested benefit of "
   f"CTP in patients with NIHSS ≥10 and in larger cores, and an ordinal (proportional-odds) signal (P = {pv(po['p'])}, "
   f"from an in-sample test on out-of-fold scores); these are hypothesis-generating (Additional file 2).")
H("Prognostic information after treatment (M3)", 2)
Pp(f"These analyses describe prognosis updated with information that becomes available after treatment, not "
   f"admission-time prediction. Adding follow-up infarct volume to R1 raised the AUC from {tl(SA,'R1_clin_LR4')} to "
   f"{tl(SA,'R1_DWI')} (primary H3: {td(SA,'R1_DWI','R1_clin_LR4')}; unadjusted bootstrap P = {pv(h3.p_bootstrap)}; "
   f"Holm-adjusted P = {h3.p_holm:.3f}, which does not reach significance at α = 0.05 under the prespecified "
   f"multiplicity rule); the within-centre AUC was {tlr(SA,'R1_DWI').within_centre_auc:.3f} (no paired within-centre "
   f"test was prespecified). The clinical GBM combined with infarct volume "
   f"reached {tl(SA,'P1_plus_DWI')}, the highest discrimination in the study. In Munich (n = "
   f"{int(tlr(SB,'R1_clin_LR4').n)}, {int(tlr(SB,'R1_clin_LR4').events)} events), discrimination rose from "
   f"{tl(SB,'R1_clin_LR4')} at admission to {tl(SB,'R1_N24')} with 24-h NIHSS and {tl(SB,'R1_N24_DWI')} with infarct "
   f"volume ({td(SB,'R1_N24_DWI','R1_clin_LR4')}), with calibration slopes of {tlr(SB,'R1_clin_LR4').cal_slope:.2f}–"
   f"{tlr(SB,'R1_N24').cal_slope:.2f}. Pre-treatment CTP lowered the AUC at every time point (after follow-up imaging "
   f"{td(SB,'R1_N24_DWI_plus_E','R1_N24_DWI')}) (Fig. 5). Results were similar in complete cases (n = "
   f"{int(tlr(SBC,'R1_clin_LR4').n)}). Infarct location tended to add to infarct volume "
   f"({td(H1S,'R1_DWI_Loc','R1_DWI',llc)}), but not among the {int((locf.reg_dice >= 0.8).sum())} patients with "
   f"good registration ({td(H1D,'R1_DWI_Loc','R1_DWI',llc)}).")
H("Transportability (M4)", 2)
Pp(f"Restricting concordance to pairs within a centre lowered the AUC of P1 from {wca.loc[P1,'auc_pooled_seedmean']:.3f} "
   f"to {wca.loc[P1,'within_centre_auc']:.3f}, whereas the CTP increment stayed null ({dwc(F, P1)}). In nested CV "
   f"within Munich, the clinical GBM reached {auc(P1, mperf)}, the clinical elastic net {auc('P2_clin_EN', mperf)} with "
   f"a calibration slope of {f2(mperf.loc['P2_clin_EN'].pooled_slope)}, and CTP again added nothing ({d(F, P1, mcomp)}). "
   f"Models developed in Munich gave a low AUC in Zurich (P1 {gp(MZ, P1)}), but with {zur_ev} events in "
   f"{zur_n} patients this estimate is statistically inconclusive and is evidence neither of transportability "
   f"failure nor of success; it is not an external validation.")
H("Design parameters and go/no-go decisions (M5)", 2)
Pp(f"Detecting a CTP increment of 0.05 AUC with 80% power would require ≈{int(ssc['n_for_delta_0.05'])} patients "
   f"(≈{int(ssc['events_for_delta_0.05'])} events); 0.03 would require ≈{int(ssc['n_for_delta_0.03'])}. The increment "
   f"observed for follow-up infarct volume would be detectable with ≈{int(ssd['n_for_delta_observed'])} patients, "
   f"and an increment of 0.05 for that comparison with ≈{int(ssd['n_for_delta_0.05'])}. Developing a new model with "
   f"up to 6–10 candidate parameters at an anticipated AUC of 0.80 requires "
   f"{int(r80.loc[6,'n_minimum'])}–{int(r80.loc[10,'n_minimum'])} patients, where the lower figure is set by the "
   f"intercept-precision criterion (Table 4). The figure of about {DEF_N} patients used in the Abstract is the larger of "
   f"these two targets for the pre-treatment CTP question (≈{int(ssc['n_for_delta_0.05'])} to detect ΔAUC 0.05 with "
   f"80% power; {int(r80.loc[6,'n_minimum'])} for model development with ≤6 parameters), rounded up; it does not cover "
   f"a 0.03 increment, models with more parameters, the post-treatment comparisons or external validation. Table 3 "
   f"lists the proposed decisions: no-go for pre-treatment CTP, thresholds, volumes and location as general "
   f"prognostic markers after thrombectomy; conditional for CTP in severe strokes and for infarct location; go "
   f"(as a proposal) for collecting 24-h NIHSS and follow-up infarct volume, noting that the 24-h NIHSS interval "
   f"includes zero and the infarct-volume result was not significant after Holm correction; and centre-aware "
   f"evaluation with complete laboratory data as a requirement.")

# ------------------------------------------------------------------ discussion
H("Discussion")
Pp("Applied to a public thrombectomy cohort, the framework gave explicit answers to feasibility questions that a "
   "conventional small prediction study leaves implicit. The data were usable after unit recovery, with the Tmax "
   "scale identifiable in about two thirds of patients, and only with centre-aware evaluation. Pre-treatment CTP "
   "showed no statistically demonstrated incremental value beyond clinical variables in any form we tested; the "
   "precision analysis shows that gains of up to about 0.06 AUC remain compatible with the data for the primary "
   "comparison, so absence of benefit is not demonstrated, whereas for absolute volumes equivalence within ±0.05 "
   "was shown. Post-treatment information (24-h neurological status and follow-up infarct volume) showed larger "
   "estimated increments that were borderline after multiplicity adjustment. These estimates translate into a "
   f"specification for a definitive study of the pre-treatment CTP question: about {DEF_N} patients with complete "
   "clinical data, 24-h NIHSS, follow-up imaging and centre labels.")
Pp(f"The clinical interpretation is consistent with physiology. Perfusion imaging answers a selection question, whether "
   f"salvageable tissue exists; after successful reperfusion most tissue at risk is saved, so hypoperfusion metrics lose "
   f"prognostic weight {C('hermes', 'laredo')}. What remains uncertain at admission is how much tissue is lost despite "
   f"treatment and how the patient responds, which the 24-h examination and the follow-up infarct capture directly "
   f"{C('rangaraju', 'boers')}. That CBV ranked first among channels fits its link to collateral status "
   f"{C('arenillas')}, and our results agree with studies reporting little gain from CTP over clinical and conventional "
   f"imaging data {C('brugnara')} and with reviews finding no consistent advantage of complex machine learning over "
   f"well-specified clinical models {C('christodoulou')}.")
Pp(f"The framework also exposed problems that matter for anyone reusing ISLES'24. Pre-processed perfusion maps lack "
   f"physical units, so thresholds such as Tmax >6 s are meaningless without recovery. Centres differed threefold in "
   f"outcome rate and almost completely in data completeness, so a pooled model can earn part of its AUC by recognising "
   f"the centre; within-centre evaluation removed about 0.03 AUC from the clinical model. The clinical GBM was "
   f"overconfident despite good discrimination, and its locked configuration discriminated better than one re-selected "
   f"within folds, so its absolute AUC is optimistic; both are reminders that small cohorts need penalisation, "
   f"recalibration or fixed-weight ensembling, nested tuning, and reported calibration {C('vancalster19', 'riley20')}. Because each "
   f"of these problems was detected by a predefined module rather than by chance, the same checks can be applied "
   f"systematically to other public imaging datasets.")
Pp("Positioning this work as a feasibility study is deliberate. With 129 patients, Riley criteria support two to three "
   "parameters, and a gain of 0.05 AUC cannot be excluded. Rather than overstating a null or a borderline result, the "
   "framework reports what the data can establish and converts the uncertainty into design parameters. The go/no-go "
   "decisions are proposals, derived after the estimates were known, and should be read as such; the sample-size "
   "estimates are likewise post hoc and condition on the models and case mix of this cohort.")
H("Limitations", 2)
Pp(f"The sample is small and there is no independent external cohort. Centres were inferred, not labelled; the labels "
   f"were assigned by matching cluster size to the descriptor and one patient is assigned differently by the two "
   f"provenance signatures; the smaller centre contributed only {zur_ev} events, so all centre-specific estimates "
   f"are imprecise. The Tmax clip ceiling was absent in {129 - N_TMAX_CEIL} of 129 patients, in whom absolute Tmax "
   f"values and Tmax-threshold features are overestimated; this was handled by a sensitivity subset, not corrected, "
   f"and unit recovery was validated at feature level only. The 24-h NIHSS was recorded almost only in Munich, and "
   f"follow-up MRI timing varied (2–9 days), so post-treatment models are time-point specific. The supplementary "
   f"analysis plan was not publicly registered, and its primary result was not significant after Holm correction. "
   f"Confidence intervals, posterior probabilities and sample sizes were obtained by resampling stored out-of-fold "
   f"predictions and omit model-refitting variability; exploratory interaction and ordinal tests were fitted "
   f"in-sample on out-of-fold scores. Laboratory and time variables were median-imputed by the data release, and "
   f"laboratory values were perturbed for anonymisation. Atlas registration was affine and targeted the follow-up "
   f"DWI, and CTP covered only part of the brain. Most patients had complete reperfusion, so the findings may not "
   f"apply to incomplete reperfusion. The clinical GBM configuration was selected by non-nested cross-validation on "
   f"the same cohort in the companion study; a nested re-selection changed the clinical AUC by "
   f"{sg(nest_comp[(nest_comp.new=='P1_nested_GBM')&(nest_comp.reference==P1)].delta_auc.iloc[0])} and left the CTP "
   f"increment near zero, but it cannot remove the fact that the primary reference was fixed with knowledge of this cohort.")
H("Conclusions")
Pp(f"A five-module framework made a small public dataset informative about what a definitive study should test. "
   f"After thrombectomy, pre-treatment CTP showed no statistically demonstrated incremental prognostic value as a "
   f"general marker, although a modest gain was not excluded, whereas 24-h neurological status and follow-up infarct "
   f"volume showed larger, borderline increments. If the pre-treatment CTP question is pursued, a centre-aware study "
   f"of about {DEF_N} patients with complete clinical data and post-treatment information would be required; public "
   f"derivatives should be reused only after unit verification and centre-aware evaluation.")

H("List of abbreviations")
Pp("AUC, area under the receiver-operating-characteristic curve; CBF, cerebral blood flow; CBV, cerebral blood volume; "
   "CI, confidence interval; CTP, CT perfusion; CV, cross-validation; DWI, diffusion-weighted imaging; GBM, "
   "gradient-boosting machine; ICC, intraclass correlation coefficient; mRS, modified Rankin Scale; MTT, mean transit "
   "time; NIHSS, National Institutes of Health Stroke Scale; Tmax, time-to-maximum of the residue function.")
H("Declarations")
Pp(f"Not applicable. This secondary analysis used the public, de-identified ISLES'24 and ISLES 2018 datasets, collected "
   f"under the approval of the local ethics committees of the contributing centres "
   f"{C('isles24', 'cereda')}. No new data were collected.", "Ethics approval and consent to participate: ")
Pp("Not applicable.", "Consent for publication: ")
Pp("Not applicable.", "Clinical trial number: ")
Pp("ISLES'24 is available from Zenodo (doi:10.5281/zenodo.17652035; CC BY-NC-SA 4.0) and as a per-subject mirror on "
   "Hugging Face (https://huggingface.co/datasets/hugging-science/isles24-stroke); ISLES 2018 is available from the ISLES "
   "challenge website (https://www.isles-challenge.org). The analysis code, the inferred centre labels, fold manifests, "
   "out-of-fold predictions and all result tables are available at [Repository URL and DOI].",
   "Availability of data and materials: ")
Pp("The authors declare that they have no competing interests.", "Competing interests: ")
Pp("[Funding statement].", "Funding: ")
Pp("[Author contributions according to CRediT].", "Authors' contributions: ")
Pp("We thank the ISLES'24 and ISLES 2018 organisers and data providers.", "Acknowledgements: ")

# ------------------------------------------------------------------ references
H("References")
for i, k in enumerate(ORDER, 1):
    doc.add_paragraph(f"{i}. {REF[k]}").paragraph_format.line_spacing = 1.15

# ------------------------------------------------------------------ tables
doc.add_page_break(); H("Tables")
sel = ["N", "Age, median [IQR]", "Sex, n (%)", "NIHSS at admission, median [IQR]", "mRS premorbid, median [IQR]",
       "Atrial fibrillation, n (%)", "Glucose, median [IQR]", "Door to imaging_min, median [IQR]",
       "core_rcbf30_hypo_frac, median [IQR]", "tmax_gt6_frac, median [IQR]", "cbv_index_hypo, median [IQR]"]
t1s = t1[t1.variable.isin(sel)].copy()
for _pc in [c for c in t1s.columns if c.lower() == "p"]:
    t1s[_pc] = t1s[_pc].map(lambda v: "<0.001" if str(v) in ("0.000", "0.0") else v)
# s08_tables.py multiplies core_rcbf30_hypo_frac and tmax_gt6_frac by 100 before tabulation: the cells are percentages
t1s["variable"] = (t1s.variable.str.replace("core_rcbf30_hypo_frac", "Core rCBF<30% (% of covered tissue)")
                   .str.replace("tmax_gt6_frac", "Tmax>6 s (% of covered tissue)").str.replace("cbv_index_hypo", "CBV index")
                   .str.replace("_min", " (min)").str.replace("Sex", "Sex (male)"))
table(t1s, "Table 1. Characteristics of the analysed cohort by 90-day outcome (N = 129). Laboratory values contain ±5% "
      "anonymisation noise; laboratory values and times contain release-level median imputation (Additional file 2). "
      "Core and Tmax >6 s extents are percentages of the brain tissue covered by the CTP slab (core: rCBF <30% within "
      "ipsilateral Tmax >6 s tissue); the CBV index is the mean relative CBV in Tmax >6 s tissue. "
      "P: Fisher exact / Mann–Whitney.")
order = [(R1, "R1 4-predictor logistic"), (P1, "P1 clinical GBM (22 predictors)"), (PR, "P1 recalibrated"),
         ("B_CBV", "CBV only"), ("D_Tmax", "Tmax only"), ("A_CBF", "CBF only"), (E, "E all CTP channels"),
         (TT, "T classical thresholds"), ("V_volumes", "V absolute volumes (mL)"), ("Loc_CTP", "Loc CTP location"),
         (F, "P1 + E fusion"), ("F_late_R1_E", "R1 + E fusion"), ("F_late_P1_V", "P1 + V fusion"),
         ("F_loc", "P1 + Loc fusion"), ("R1_DWI", "R1 + follow-up infarct volume"),
         ("P1_plus_DWI", "P1 + follow-up infarct volume")]
rows = []
for m, lab in order:
    r = perf.loc[m]
    w = wca.loc[m, "within_centre_auc"] if m in wca.index else tlp[(tlp.set == SA) & (tlp.model == m)].within_centre_auc.iloc[0]
    rows.append({"Model": lab, "Time point": "after follow-up MRI" if "DWI" in m else "admission",
                 "AUC (95% CI)": f"{r.auc_seed_mean:.3f} ({r.auc_ci_lo:.3f}–{r.auc_ci_hi:.3f})",
                 "Within-centre AUC": f"{w:.3f}", "Calibration slope": f"{r.pooled_slope:.2f}", "Brier": f"{r.pooled_brier:.3f}"})
table(pd.DataFrame(rows), "Table 2. Discrimination and calibration of key models (nested CV, 5 seeds × 10-fold; outcome "
      "mRS 3–6). AUC: mean of seed-specific out-of-fold AUCs, 2,000 patient-bootstrap CI. Within-centre AUC: concordance "
      "over patient pairs from the same inferred centre. Calibration slope and Brier score: on seed-averaged "
      "probabilities. All models: Additional file 2.", font=7.5)
MINUS = lambda s: re.sub(r"(?<![A-Za-z0-9])-(?=\d)", "−", s) if isinstance(s, str) else s
gng_t = gng.rename(columns={"Estimate (95% CI)": "Estimate (95% CI)"}).apply(lambda c: c.map(MINUS))
gng_t = gng_t.apply(lambda c: c.map(lambda s: s.replace("Holm P", "Holm-adjusted P").replace("(Munich)", "(Munich only)")
                                     .replace("Go: collect in all centres", "Go (proposal; 95% CI includes 0): collect in all centres")
                                     .replace("Go: primary candidate", "Go (proposal; not significant after Holm): primary candidate")
                                     if isinstance(s, str) else s))
table(gng_t,
      "Table 3. Go/no-go summary by research direction (M5). Decisions are proposals for a definitive study formulated "
      "after the estimates were known, not progression criteria fixed in advance; 'go' denotes a proposal to collect "
      "or test the variable, not a demonstrated effect. 95% CIs from the paired patient bootstrap.", font=7.5)
t4 = ss[["comparison", "delta_observed", "n_for_delta_0.03", "n_for_delta_0.05", "n_for_delta_0.08", "n_for_delta_observed"]].copy()
t4["delta_observed"] = t4.delta_observed.map(lambda x: f"{x:+.3f}")
t4.columns = ["Increment", "Observed ΔAUC", "n for ΔAUC 0.03", "n for ΔAUC 0.05", "n for ΔAUC 0.08", "n for observed ΔAUC"]
r_rows = rly[np.isclose(rly.anticipated_auc, 0.80)][["parameters", "n_minimum", "events_minimum"]]
table(t4, "Table 4a. Sample size to detect a given increment in AUC with 80% power (two-sided α = 0.05), from the "
      "paired-bootstrap SE scaled by 1/√n at the observed event rate (post hoc; assumes the same models and case mix). "
      "These are detection targets, distinct from the model-development targets in Table 4b.", font=7.5)
table(r_rows.rename(columns={"parameters": "Candidate parameters", "n_minimum": "Minimum n",
                             "events_minimum": "Minimum events"}),
      "Table 4b. Riley minimum sample size for developing a new model (anticipated AUC 0.80, shrinkage 0.9, precise intercept).", font=8)

# ------------------------------------------------------------------ figures
doc.add_page_break(); H("Figures")
legends = {
 "Fig1_framework": "Fig. 1. The five-module framework applied to ISLES'24: data sources, analysed cohort and modules M1–M5 with their main outputs.",
 "Fig2_unit_recovery_validation": "Fig. 2. Data readiness: recovery of physical units. (a) Central volume theorem in ISLES'24; (b) recovered/true scale in the ISLES 2018 simulation; (c) feature-level ICC between true and recovered maps; (d) example recovered Tmax map. Agreement with native-unit maps: Additional file 4, Fig. S6.",
 "Fig3_auc_forest": "Fig. 3. Discrimination of pre-treatment models (mean of five seed-specific out-of-fold AUCs, 95% patient-bootstrap CI). Dashed line: clinical GBM (P1).",
 "Fig8_robustness": "Fig. 4. Incremental value of pre-treatment CTP across analytic settings: ΔAUC with 95% bootstrap CI in the pooled nested CV (blue) and in centre-aware analyses (orange). Shaded band: equivalence margin ±0.05.",
 "Fig9_timeline": "Fig. 5. Prognostic information across the care pathway (supplementary analysis plan, hypothesis H3). (a) Munich: admission model, + 24-h NIHSS, + follow-up DWI infarct volume, each without (blue) and with (orange) pre-treatment CTP. (b) Full cohort: pre-treatment versus post-imaging models.",
 "Fig5_calibration": "Fig. 6. LOESS calibration curves and distributions of predicted risk for key pre-treatment models.",
}
for k, v in legends.items():
    doc.add_picture(str(FIG / f"{k}.png"), width=Inches(6.0)); doc.add_paragraph(v)

H("Additional files")
Pp("Additional file 1 (.docx). TRIPOD+AI checklist. Location in the manuscript of each reporting item.")
Pp("Additional file 2 (.xlsx). Supplementary Tables S1–S20. Feature dictionary, missingness, all models and paired "
   "comparisons, sensitivity analyses, precision and equivalence, centre analyses, post-treatment, location and "
   "occlusion-population models, and design parameters; a contents sheet and a glossary of model codes are included.")
Pp("Additional file 3 (.docx). Supplementary analysis plan. Hypotheses H1–H3, models, primary comparisons and "
   "multiplicity rules, finalised before the corresponding analyses were run.")
Pp("Additional file 4 (.docx). Supplementary methods S1–S8 and Figures S1–S7.")
out = OUT / "Manuscript_BMC_MIDM.docx"
doc.save(out); print("saved", out, "| references:", len(ORDER))
