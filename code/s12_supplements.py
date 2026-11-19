"""Additional file 1 (TRIPOD+AI checklist, docx) and Additional file 2 (supplementary tables, xlsx)."""
import pandas as pd
from docx import Document
from docx.shared import Pt
from config import TAB, DATA, OUT
import features as F

TRIPOD = [
 ("1", "Title", "Identify the study as developing/evaluating a prediction model, target population and outcome", "Title page"),
 ("2", "Abstract", "Structured summary (TRIPOD+AI for Abstracts)", "Abstract"),
 ("3a", "Background", "Medical context, rationale, existing models", "Background ¶1"),
 ("3b", "Background", "Target population and intended use in the care pathway", "Background ¶1–2"),
 ("3c", "Background", "Known health inequalities", "Limitations (single dataset, two centres; not assessable)"),
 ("4", "Objectives", "Study objectives; development and/or validation", "Background ¶3 (framework M1–M5; feasibility)"),
 ("5a", "Data", "Sources of data, rationale", "Methods: Design, data and reporting"),
 ("5b", "Data", "Dates of data collection", "Per ISLES'24 descriptor; not provided per subject"),
 ("6a", "Participants", "Study setting, centres", "Methods: Design; M1 Centres (inferred 99/50); Results M1"),
 ("6b", "Participants", "Eligibility criteria", "Methods: Design, data and reporting"),
 ("6c", "Participants", "Treatments received", "Methods: Design (endovascular reperfusion); Limitations"),
 ("7", "Data preparation", "Pre-processing, data quality, harmonisation", "Methods: M1; Results M1; Fig. 2; Additional file 4, S1–S2"),
 ("8a", "Outcome", "Outcome definition, timing", "Methods: Design, data and reporting (90-day mRS 3–6)"),
 ("8b", "Outcome", "Assessor blinding / qualifications", "Not reported by data provider (limitation)"),
 ("8c", "Outcome", "Consistency of outcome assessment across groups", "Not assessable; single definition used"),
 ("9a", "Predictors", "Choice of initial predictors, pre-selection", "Methods: M1 Clinical data, M3; Additional file 4, S3"),
 ("9b", "Predictors", "Definition, timing of measurement", "Methods: M1, M3 (time points); Additional file 2, S1"),
 ("9c", "Predictors", "Blinding of predictor assessment", "Automated extraction, outcome-blind"),
 ("10", "Sample size", "How sample size was determined, justification", "Methods: M2 (Riley); Results M1, M5; Table 4"),
 ("11", "Missing data", "How missing data were handled", "Methods: M1, M2; Results M1; Additional file 4, S5"),
 ("12a", "Analytical methods", "Data use for development/evaluation", "Methods: M2 (nested CV)"),
 ("12b", "Analytical methods", "Predictor handling (transformations, scaling)", "Methods: M2; pipeline fitted inside folds"),
 ("12c", "Analytical methods", "Model type, rationale, building, tuning", "Methods: M3; Additional file 4, S4"),
 ("12d", "Analytical methods", "Heterogeneity across clusters", "Methods: M4 (within-centre AUC, single-centre CV, leave-one-centre-out)"),
 ("12e", "Analytical methods", "Performance measures and their CIs; model comparison", "Methods: M2 (incl. precision / equivalence)"),
 ("12f", "Analytical methods", "Model updating/recalibration", "Recalibrated clinical GBM (Methods M3; Additional file 4, S4)"),
 ("12g", "Analytical methods", "Model output (probabilities)", "Methods: Design (P(poor))"),
 ("13", "Class imbalance", "Methods for class imbalance", "None (no resampling, to preserve calibration)"),
 ("14", "Fairness", "Approaches to address model fairness", "Not assessable (no ethnicity data); centre effects in M4"),
 ("15", "Model output", "Output and thresholds", "Methods: M2 (decision-curve thresholds 0.20–0.50)"),
 ("16", "Training vs evaluation", "Differences in setting/eligibility between development and evaluation", "Results: M1 (case mix and imputation by centre), M4"),
 ("17", "Ethics", "Ethics approval", "Declarations"),
 ("18a", "Open science", "Funding", "Declarations"),
 ("18b", "Open science", "Conflicts of interest", "Declarations"),
 ("18c", "Open science", "Protocol", "Primary configuration from the companion study; supplementary analysis plan finalised before the H1–H3 analyses (Additional file 3)"),
 ("18d", "Open science", "Registration", "Not registered (stated in Limitations)"),
 ("18e", "Open science", "Data sharing", "Declarations: availability of data and materials"),
 ("18f", "Open science", "Code sharing", "Declarations: availability of data and materials (analysis code repository)"),
 ("19", "Patient & public involvement", "PPI details", "None"),
 ("20a", "Participants (results)", "Flow of participants", "Results M1; Fig. 1"),
 ("20b", "Participants (results)", "Characteristics, including predictors and outcome", "Table 1"),
 ("20c", "Participants (results)", "Comparison with development data", "Included vs excluded (Additional file 2, S3)"),
 ("21", "Model development", "Number of participants and outcome events in each analysis", "Results; Tables 2, 4; Additional file 2"),
 ("22", "Model specification", "Full model details / access", "Methods M3; Additional file 4, S4; code; Additional file 2, S6"),
 ("23a", "Model performance", "Performance with CIs, including subgroups", "Table 2; Figs. 3–6; Additional file 4, Figs. S1–S5"),
 ("23b", "Model performance", "Heterogeneity across clusters", "Results M4; Fig. 4; Additional file 2, S14–S15"),
 ("24", "Model updating", "Results of updating", "Results M3 (recalibrated GBM; time-resolved models)"),
 ("25", "Interpretation", "Overall interpretation incl. fairness", "Discussion"),
 ("26", "Limitations", "Limitations (non-representative sample, sample size, overfitting, missing data)", "Discussion: Limitations"),
 ("27a", "Usability", "Handling of poor-quality or unavailable input data", "Methods M1; Results M1"),
 ("27b", "Usability", "User interaction / expertise required", "Automated pipeline; not a deployed tool"),
 ("27c", "Usability", "Future research steps", "Results M5; Tables 3–4; Conclusions"),
]


def checklist():
    d = Document(); d.styles["Normal"].font.size = Pt(9)
    d.add_heading("Additional file 1. TRIPOD+AI checklist", 1)
    t = d.add_table(rows=1, cols=4); t.style = "Table Grid"
    for i, h in enumerate(["Item", "Section", "Checklist item (abridged)", "Location in manuscript"]):
        t.rows[0].cells[i].text = h
    for row in TRIPOD:
        c = t.add_row().cells
        for i, v in enumerate(row):
            c[i].text = v
    d.save(OUT / "Additional_file_1_TRIPOD_AI_checklist.docx")


GLOSSARY_MODELS = {
 "THRIVE": "THRIVE score (logistic, recomputed from raw values)",
 "SPAN100": "SPAN-100 (age + admission NIHSS, logistic)",
 "NIHSS_only": "Admission NIHSS only (logistic)",
 "P1_clin_GBM": "P1: clinical gradient-boosting machine, 22 pre-procedural predictors (primary clinical reference)",
 "P2_clin_EN": "Clinical elastic net, same 22 predictors",
 "R1_clin_LR4": "R1: parsimonious logistic model (age, admission NIHSS, premorbid mRS, glucose)",
 "P1_recal": "P1 with Platt recalibration fitted on inner-fold predictions",
 "P1_missind": "P1 + missing-value indicators (sensitivity)",
 "P1_missonly": "Missing-value indicators only (sensitivity)",
 "P1_no_alert2door": "P1 without alert-to-door time (sensitivity)",
 "A_CBF": "CTP single channel: CBF features (elastic net)",
 "B_CBV": "CTP single channel: CBV features (elastic net)",
 "C_MTT": "CTP single channel: MTT features (elastic net)",
 "D_Tmax": "CTP single channel: Tmax features (elastic net)",
 "E_CTP_all": "E: all 53 CTP features (elastic net)",
 "E_minus_CBF": "E without CBF features (leave-one-channel-out)",
 "E_minus_CBV": "E without CBV features (leave-one-channel-out)",
 "E_minus_MTT": "E without MTT features (leave-one-channel-out)",
 "E_minus_Tmax": "E without Tmax features (leave-one-channel-out)",
 "E_native": "E computed from native-unit maps of the original release",
 "E_PCA5": "E reduced to 5 principal components (sensitivity)",
 "E_phys15": "Compact physiological set of 15 CTP features (sensitivity)",
 "E_scalefree": "Scale-free CTP features only (sensitivity; 30 features independent of the absolute Tmax scale, S1 column scale_free)",
 "P1_nested_GBM": "Clinical GBM with the configuration re-selected inside each training fold (sensitivity; inner 5-fold grid search)",
 "F_late_P1nested_E": "P1_nested_GBM + E, late fusion (sensitivity)",
 "T_thresholds": "T: classical thresholds (core rCBF<30%, Tmax>6 s, mismatch ratio, hypoperfusion intensity ratio; logistic)",
 "T_core20": "T with core rCBF<20% (sensitivity)", "T_core38": "T with core rCBF<38% (sensitivity)",
 "T_core_ipsi30": "T with whole-hemisphere core rCBF<30% (sensitivity)",
 "T_tmax4": "T with Tmax>4 s (sensitivity)", "T_tmax8": "T with Tmax>8 s (sensitivity)",
 "V_volumes": "V: absolute volumes in mL from native maps (core, Tmax>6 s, mismatch; logistic)",
 "Loc_CTP": "Loc: fraction of four eloquent atlas regions covered by Tmax>6 s tissue (elastic net)",
 "F_late_P1_E": "P1 + E, equal-weight late fusion (primary comparison vs P1)",
 "F_late_P1_T": "P1 + T, late fusion", "F_late_P1_V": "P1 + V, late fusion",
 "F_late_P1_CBV": "P1 + CBV-only model, late fusion (sensitivity)",
 "F_late_P1_EPCA": "P1 + E_PCA5, late fusion (sensitivity)", "F_late_P1_Ephys": "P1 + E_phys15, late fusion (sensitivity)",
 "F_late_P1_Esf": "P1 + E_scalefree, late fusion (sensitivity)", "F_late_P1_Enat": "P1 + E_native, late fusion",
 "F_late_P1miss_E": "P1_missind + E, late fusion (sensitivity)", "F_late_P1recal_E": "P1_recal + E, late fusion",
 "F_late_R1_E": "R1 + E, late fusion", "F_late_R1_V": "R1 + V, late fusion", "F_loc": "P1 + Loc_CTP, late fusion (H1 primary)",
 "F_EN_clin_CTP": "Early fusion: elastic net on 22 clinical + 53 CTP features",
 "F_GBM_clin_thresh": "Gradient boosting on clinical + threshold features",
 "R1_plus_E": "R1 + E, late fusion", "R1_plus_volumes": "R1 + absolute volumes (single logistic model)",
 "R1_Loc_CTP": "R1 + four CTP location features (elastic net)",
 "DWI_only": "Follow-up DWI infarct volume only (log mL; logistic)",
 "R1_DWI": "R1 + follow-up DWI infarct volume (H3 primary vs R1)", "R1_DWI_plus_E": "R1_DWI + E, late fusion",
 "R1_DWI_Loc": "R1_DWI + four DWI infarct-location features (elastic net)",
 "P1_plus_DWI": "P1 + DWI_only, late fusion",
 "R1_N24": "R1 + 24-h NIHSS (Munich)", "R1_N24_plus_E": "R1_N24 + E, late fusion (Munich)",
 "R1_N24_DWI": "R1 + 24-h NIHSS + follow-up DWI infarct volume (Munich)",
 "R1_N24_DWI_plus_E": "R1_N24_DWI + E, late fusion (Munich)",
}
GLOSSARY_COLUMNS = {
 "auc_seed_mean": "Mean of the five seed-specific out-of-fold AUCs (primary estimand)",
 "auc_ci_lo / auc_ci_hi": "95% CI from 2,000 patient-level bootstrap resamples",
 "auc_pooled": "AUC of seed-averaged out-of-fold probabilities",
 "pooled_slope / pooled_citl": "Calibration slope / calibration-in-the-large of seed-averaged probabilities",
 "pooled_ici / pooled_e90": "Integrated calibration index / 90th percentile of absolute calibration error",
 "brier_seed_mean": "Brier score, mean over seeds",
 "thr50_*": "Classification metrics at a probability threshold of 0.50",
 "new / reference": "Model compared / reference model in a paired comparison",
 "delta_auc, ci_lo, ci_hi, p_bootstrap": "Paired ΔAUC (new − reference), 95% bootstrap CI and two-sided bootstrap P",
 "p_delong_pooled": "DeLong test on seed-averaged probabilities",
 "ci90_lo / ci90_hi": "90% CI used for two one-sided tests (equivalence)",
 "post_p_gt0 / _gt0.03 / _gt0.05": "Bayesian-bootstrap posterior probability that ΔAUC exceeds 0, 0.03, 0.05",
 "mdd_80pct_power": "Minimal detectable ΔAUC at 80% power (2.80 × bootstrap SE)",
 "tost_equiv_0.05 / _0.03": "Equivalence within ±0.05 / ±0.03 AUC shown (90% CI inside the margin)",
 "within_centre_auc": "Concordance restricted to patient pairs from the same (inferred) centre",
 "p_holm": "Holm-adjusted P value across the three primary comparisons (H1–H3)",
}
SHEET_DESC = {
 "S1": "Dictionary of the 53 CTP features", "S2": "Probable release-level imputation by variable",
 "S3": "Included versus excluded patients", "S4": "ISLES 2018 simulation of unit recovery",
 "S5": "All models: discrimination and calibration; paired comparisons; decision curves; reclassification",
 "S6": "Model coefficients and rank stability", "S7": "TreeSHAP values for P1", "S8": "Riley sample-size calculations",
 "S9": "Ordinal analyses", "S10": "Train–test AUC gap", "S11": "Sensitivity analyses",
 "S12": "Native-unit maps: agreement, volumes, validity, sex coding", "S13": "Precision and equivalence",
 "S14": "Centre inference, case mix, imputation, within-centre and Munich-only analyses",
 "S15": "Leave-one-centre-out validation", "S16": "Exploratory subgroup analyses",
 "S17": "Post-treatment (H3) models", "S18": "Location (H1) and occlusion-population (H2) models; location features",
 "S19": "Primary comparisons H1–H3 with Holm adjustment", "S20": "Design parameters and go/no-go summary",
}


def supp():
    fd = pd.DataFrame([{"feature": f, "channel": F.CHANNEL_OF.get(f, "Mismatch"),
                        "in_threshold_model_T": f in F.THRESH, "scale_free": f in F.SCALE_FREE} for f in F.CTP_ALL])
    sheets = {
        "S1_feature_dictionary": fd,
        "S2_missingness": pd.read_csv(TAB / "missingness_probable_imputed.csv"),
        "S3_included_vs_excluded": pd.read_csv(TAB / "included_vs_excluded.csv"),
        "S4_ISLES2018_recovery": pd.read_csv(TAB / "isles2018_unit_recovery_summary.csv"),
        "S4b_ISLES2018_features": pd.read_csv(TAB / "isles2018_feature_agreement.csv"),
        "S5_all_models": pd.read_csv(TAB / "performance_all_models_all.csv"),
        "S5b_paired": pd.read_csv(TAB / "paired_auc_comparisons_all.csv"),
        "S5c_DCA": pd.read_csv(TAB / "dca_delta_nb_all.csv"),
        "S5d_NRI_IDI": pd.read_csv(TAB / "reclassification_all.csv"),
        "S6_coefficients": pd.read_csv(TAB / "coef_importance.csv"),
        "S6b_rank_stability": pd.read_csv(TAB / "coef_rank_stability.csv"),
        "S7_TreeSHAP_P1": pd.read_csv(TAB / "treeshap_P1_clin_GBM.csv"),
        "S8_sample_size": pd.read_csv(TAB / "sample_size_riley.csv"),
        "S9_ordinal": pd.read_csv(TAB / "ordinal_c_index.csv"),
        "S9b_cutpoints": pd.read_csv(TAB / "cumulative_cutpoint_auc.csv"),
        "S10_overfit_gap": pd.read_csv(TAB / "overfit_gap.csv"),
    }
    for tag in ["_sens_features", "_sens_missing", "_sens_tmaxcertain", "_5fold", "_sens_scalefree", "_sens_nestedgbm"]:
        pf, pr = pd.read_csv(TAB / f"performance_all_models{tag}.csv"), pd.read_csv(TAB / f"paired_vs_P1_clin_GBM{tag}.csv")
        if tag == "_sens_features":   # E_scalefree rows of this run used the superseded 31-feature list; see S11_sens_scalefree
            pf, pr = pf[~pf.model.isin(["E_scalefree", "F_late_P1_Esf"])], pr[~pr.model.isin(["E_scalefree", "F_late_P1_Esf"])]
        sheets[f"S11{tag}"[:31]] = pf
        sheets[f"S11d{tag}"[:31]] = pr
    sheets["S11e_nestedgbm_paired"] = pd.read_csv(TAB / "paired_auc_comparisons_sens_nestedgbm.csv")
    import json
    site = json.load(open(TAB / "site_inference.json"))
    sheets.update({
        "S12_native_agreement": pd.read_csv(TAB / "native_vs_recovered_agreement.csv"),
        "S12b_native_volumes": pd.read_csv(TAB / "native_volumes_summary.csv"),
        "S12c_native_validity": pd.Series(json.load(open(TAB / "native_validity.json"))).rename("value").reset_index(),
        "S12d_sex_coding": pd.read_csv(TAB / "sex_coding_check.csv"),
        "S13_precision_equivalence": pd.read_csv(TAB / "precision_equivalence.csv"),
        "S14_centre_inference": pd.DataFrame([{"item": k, "value": json.dumps(v)} for k, v in site.items()]),
        "S14b_case_mix_by_centre": pd.read_csv(TAB / "site_case_mix.csv"),
        "S14c_imputation_by_centre": pd.read_csv(TAB / "site_imputation.csv"),
        "S14d_within_centre_auc": pd.read_csv(TAB / "within_centre_auc.csv"),
        "S14e_within_centre_paired": pd.read_csv(TAB / "within_centre_paired.csv"),
        "S14f_Munich_only_models": pd.read_csv(TAB / "performance_all_models_munich.csv"),
        "S14g_Munich_only_paired": pd.read_csv(TAB / "paired_auc_comparisons_munich.csv"),
        "S15_leave_centre_out": pd.read_csv(TAB / "geographic_validation_performance.csv"),
        "S15b_leave_centre_out_pair": pd.read_csv(TAB / "geographic_validation_paired.csv"),
        "S16_subgroups": pd.read_csv(TAB / "subgroup_incremental_value.csv"),
        "S17_timeline_models": pd.read_csv(TAB / "timeline_performance.csv"),
        "S17b_timeline_paired": pd.read_csv(TAB / "timeline_paired.csv"),
        "S18_location_lvo_models": pd.read_csv(TAB / "location_lvo_performance.csv"),
        "S18b_location_lvo_paired": pd.read_csv(TAB / "location_lvo_paired.csv"),
        "S18c_location_features": pd.read_csv(DATA / "location_features.csv"),
        "S19_primary_holm": pd.read_csv(TAB / "round4_primary_holm.csv"),
        "S20_design_sample_size": pd.read_csv(TAB / "design_sample_size.csv"),
        "S20b_design_riley": pd.read_csv(TAB / "design_riley.csv"),
        "S20c_go_nogo": pd.read_csv(TAB / "go_nogo.csv"),
    })
    contents = pd.DataFrame({"Sheet": [k[:31] for k in sheets]})
    contents["Table"] = contents.Sheet.str.extract(r"^(S\d+)")[0]
    contents["Content"] = contents.Table.map(SHEET_DESC)
    gm = pd.DataFrame([{"Model code": k, "Description": v} for k, v in GLOSSARY_MODELS.items()])
    gc = pd.DataFrame([{"Column": k, "Meaning": v} for k, v in GLOSSARY_COLUMNS.items()])
    note = pd.DataFrame({"Note": [
        "Additional file 2. Supplementary Tables S1–S20 for the manuscript on the incremental prognostic value of CT "
        "perfusion after thrombectomy (ISLES'24).",
        "Outcome: poor 90-day outcome (mRS 3–6) = 1; all probabilities are P(poor).",
        "Evaluation: nested cross-validation, 5 seeds × stratified 10-fold, inner 5-fold; 2,000 patient-level bootstrap resamples.",
        "Centres (Munich, Zurich) are inferred from data provenance (Additional file 4, S7).",
        "Model codes and column names are defined in the sheets 'Glossary_models' and 'Glossary_columns'."]})
    with pd.ExcelWriter(OUT / "Additional_file_2_supplementary_tables.xlsx") as w:
        note.to_excel(w, sheet_name="README", index=False)
        contents.to_excel(w, sheet_name="Contents", index=False)
        gm.to_excel(w, sheet_name="Glossary_models", index=False)
        gc.to_excel(w, sheet_name="Glossary_columns", index=False)
        for k, v in sheets.items():
            v.round(4).to_excel(w, sheet_name=k[:31], index=False)


def plan_docx():
    from config import ROOT
    d = Document(); d.styles["Normal"].font.size = Pt(10)
    d.add_heading("Additional file 3. Supplementary analysis plan", 1)
    for line in (ROOT / "SAP_supplementary_analysis_plan.md").read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            d.add_heading(s.lstrip("#").strip(), 2)
        elif s.startswith("- "):
            d.add_paragraph(s[2:], style="List Bullet")
        else:
            d.add_paragraph(s)
    d.save(OUT / "Additional_file_3_supplementary_analysis_plan.docx")


SUPP_METHODS = [
 ("S1. Recovery of physical units", [
  "Each stored map equals z = (x − μ)/σ, where x is the clinical map clipped to [0, c] (c = 100 mL/100 g/min for CBF, "
  "10 mL/100 g for CBV, 30 s for MTT and Tmax) and μ, σ are unknown subject-level constants. Background voxels have "
  "x = 0, so x = b(z − z_min); when the clip ceiling is present b = c/(z_max − z_min), which is exact. Relative "
  "quantities (rCBF, rCBV, rMTT) are invariant to b. Verification: (i) the central volume theorem MTT = 60·CBV/CBF must "
  "hold voxel-wise only if all three scales are correct, which also confirms the channel order; (ii) on the 94 ISLES 2018 "
  "training cases we reproduced the public pre-processing (clip, trilinear resampling, per-subject z-normalisation), "
  "applied the recovery and compared recovered with true maps and features (ICC(A,1)); (iii) after the primary analysis "
  "was locked, all features were recomputed from the native-unit maps of the original release (clipped to the same "
  "ranges, block-averaged to about 1.9 × 1.9 × 2 mm) and compared with the recovered features (ICC(3,1))."]),
 ("S2. Perfusion features (53)", [
  "Within brain tissue (excluding vessels: CBV ≥ 8 mL/100 g or CBF ≥ 99 mL/100 g/min) the midline was located by "
  "maximising mirror symmetry; the ipsilateral hemisphere was the one with the larger Tmax > 6 s fraction and was "
  "cross-checked against the occlusion mask. CBF, CBV and MTT were expressed relative to the contralateral median; "
  "volumes in the pre-processed release are fractions of covered tissue.",
  "CBF (14): rCBF < 20/30/38% core within ipsilateral Tmax > 6 s tissue; rCBF < 30% in the whole ipsilateral hemisphere; "
  "ipsilateral rCBF ratio; mean rCBF in hypoperfused tissue; distribution statistics of ipsilateral rCBF.",
  "CBV (11): ipsilateral rCBV ratio; rCBV < 0.6 fraction; CBV index in hypoperfused tissue; distribution statistics.",
  "MTT (11): ipsilateral rMTT ratio; rMTT > 145% fraction; rMTT in hypoperfused tissue; distribution statistics.",
  "Tmax (15): Tmax > 4/6/8/10 s fractions; hypoperfusion intensity ratio (Tmax > 10 s / Tmax > 6 s); "
  "ipsilateral-minus-contralateral median Tmax; distribution statistics.",
  "Mismatch (2): log mismatch ratio; mismatch fraction. Distribution statistics: mean, SD, skewness, kurtosis and the "
  "10th, 25th, 75th and 90th percentiles. Absolute volumes (native maps): core (rCBF < 30% within Tmax > 6 s), "
  "Tmax > 6 s and mismatch, in mL, log(1 + x) in models."]),
 ("S3. Clinical predictors and scores", [
  "Twenty-two pre-procedural variables: age, sex; wake-up, in-house, referral; atrial fibrillation, hypertension, "
  "diabetes, hyperlipidaemia, anticoagulants, lipid-lowering drugs, antiplatelets; admission NIHSS, premorbid mRS, "
  "admission mRS; glucose, leucocytes, CRP, INR; onset-to-door, alert-to-door and door-to-imaging times. Four "
  "intra-procedural times were excluded because they are not available at the time of prediction. THRIVE (age, NIHSS "
  "0/2/4 points for ≤ 10/11–20/≥ 21, hypertension, diabetes, atrial fibrillation) and SPAN-100 (age + NIHSS) were "
  "recomputed from raw values."]),
 ("S4. Models and tuning", [
  "P1: gradient boosting (80 trees, depth 3, learning rate 0.1, subsample 0.7; locked configuration of the companion "
  "study, which selected it by non-nested cross-validation on the same cohort). Sensitivity analysis P1_nested_GBM: "
  "configuration re-selected inside each training fold by inner stratified 5-fold grid search over trees ∈ {50, 80, "
  "150, 300}, depth ∈ {2, 3, 4}, learning rate ∈ {0.03, 0.1}, subsample 0.7, minimising log-loss. "
  "Elastic-net models: inner stratified 5-fold grid search over C ∈ {0.01, 0.03, 0.1, 0.3, 1} and "
  "l1-ratio ∈ {0.2, 0.5, 0.8}, minimising log-loss. Logistic models (R1, T, V, scores): L2, C = 1. P1-recal: Platt "
  "recalibration fitted on inner 5-fold predictions with the GBM refitted on the whole training fold. Fusion: "
  "equal-weight average of the two out-of-fold probabilities. Additional prespecified alternatives: early-fusion "
  "elastic net (clinical + all CTP), GBM on clinical + threshold features, P1 + T fusion."]),
 ("S5. Sensitivity analyses", [
  "(1) ordinal mRS (ordinal c-index; proportional-odds likelihood-ratio test of the out-of-fold CTP score added to the "
  "clinical score); (2) alternative thresholds (Tmax > 4 or > 8 s; core rCBF < 20% or < 38%; whole-hemisphere core); "
  "(3) scale-free CTP features only (the 30 features that do not depend on the absolute Tmax scale: ratios to the "
  "contralateral median and fractions defined without a Tmax threshold; features computed inside the Tmax > 6 s mask "
  "are excluded); (4) patients with an exactly identified Tmax scale; (5) compact physiological set "
  "and PCA (5 components) CTP models; (6) missing-value indicators added to P1 and alert-to-door removed; "
  "(7) 5 × 5-fold protocol; (8) fusion with the CBV-only model; and, added after the evidence audit, (9) the clinical "
  "GBM re-tuned inside each training fold as the reference for the primary comparison."]),
 ("S6. Subgroup analyses", [
  "Exploratory, without multiplicity adjustment: ΔAUC of P1 + E over P1 within strata of age (≥ 80 y), NIHSS (≥ 10), "
  "premorbid mRS (≥ 1), occlusion mask visible after down-sampling, wake-up onset, inferred centre, and native core and "
  "Tmax > 6 s volume (≥ median). Effect modification: likelihood-ratio test of the interaction between the "
  "out-of-fold CTP score and the subgroup indicator in a logistic model that also contained the clinical score."]),
 ("S7. Centre inference", [
  "Two provenance signatures of the original release were used: (i) whether the voxel maxima of the four perfusion maps "
  "are multiples of 1/64 (integer-scaled export) or unquantised floating point; (ii) NCCT slice thickness and CTP slab "
  "coverage. The cluster sizes (99/50) were compared with the 100/50 split reported in the dataset descriptor, of whose "
  "150 training cases 149 are in the public release; the cluster of size 50 was labelled Zurich (inferred)."]),
 ("S8. Atlas registration and location features", [
  "The MNI152 2-mm template (nilearn) was registered affinely (12 degrees of freedom; SimpleITK; Mattes mutual "
  "information, 32 bins, 25% random sampling; regular-step gradient descent; three-level pyramid with shrink factors "
  "4/2/1 and smoothing 2/1/0 voxels; moments initialisation) to each patient's skull-stripped follow-up DWI, which "
  "shares the NCCT space of the perfusion maps. Atlas labels and a hemisphere map were resampled with nearest-neighbour "
  "interpolation. Regions: corticospinal tract (Juelich, maximum probability, 25%); caudate, putamen, pallidum and "
  "thalamus (Harvard–Oxford subcortical); insular cortex and frontal, central and parietal opercular cortex; left "
  "inferior frontal gyrus pars opercularis and triangularis, posterior superior temporal gyrus, supramarginal gyrus "
  "(anterior and posterior) and angular gyrus (Harvard–Oxford cortical). Features: fraction of the ipsilateral region "
  "(left region for language) covered by Tmax > 6 s tissue within the CTP slab, and by the DWI infarct. Quality: Dice "
  "between the warped template brain mask and the patient's DWI brain mask."]),
]
SUPP_FIGS = [
 ("Fig4_roc", "Fig. S1. ROC curves from seed-averaged out-of-fold probabilities."),
 ("Fig6_dca", "Fig. S2. Decision curve analysis for predicting poor 90-day outcome."),
 ("Fig7_interpretability", "Fig. S3. Channel contribution and interpretability: (a) share of standardised coefficient mass by channel in the all-channel model; (b) single-channel and leave-one-channel-out AUCs; (c) TreeSHAP for the clinical + threshold GBM."),
 ("FigS1_sensitivity_delta_auc", "Fig. S4. Sensitivity analyses: ΔAUC of clinical + CTP fusion over the clinical GBM (last row: over the nested-tuned clinical GBM)."),
 ("FigS2_subgroups", "Fig. S5. Exploratory subgroup analyses: ΔAUC of fusion over the clinical GBM, with P values for interaction."),
 ("FigS3_native_agreement", "Fig. S6. Agreement between features from recovered units and from native-unit maps: (a) ICC per feature by channel; (b, c) examples."),
 ("FigS4_atlas_registration_qc", "Fig. S7. Atlas registration quality for the patients with the lowest, median and highest Dice. Contours: corticospinal tract (orange), deep grey matter (green), insula/operculum (yellow), language cortex (pink), DWI infarct (blue)."),
]


def supp_methods_figs():
    from docx.shared import Inches
    from config import FIG
    d = Document(); d.styles["Normal"].font.size = Pt(10)
    d.add_heading("Additional file 4. Supplementary methods and figures", 1)
    for h, paras in SUPP_METHODS:
        d.add_heading(h, 2)
        for t in paras:
            d.add_paragraph(t)
    d.add_page_break(); d.add_heading("Supplementary figures", 1)
    for f, cap in SUPP_FIGS:
        d.add_picture(str(FIG / f"{f}.png"), width=Inches(6.0)); d.add_paragraph(cap)
    d.save(OUT / "Additional_file_4_supplementary_methods_figures.docx")


if __name__ == "__main__":
    checklist(); supp(); plan_docx(); supp_methods_figs(); print("ok")
