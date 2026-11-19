# Status of this document

This plan was finalised on 11 November 2026, after the primary analysis (pre-treatment CTP versus clinical models) and before any of the analyses described below were run. It is reproduced here with editorial changes to wording and layout only; the hypotheses, models, primary comparisons, multiplicity rule and reporting rule are unchanged from the time-stamped original (file PLAN_v4_prespecified.md in the code repository).

# General rules

- Every model is specified here and evaluated with the same protocol as the primary analysis (5 seeds × stratified 10-fold outer cross-validation, inner stratified 5-fold cross-validation).
- Every result is reported, including null results.
- Each hypothesis has one primary comparison (marked PRIMARY); Holm correction is applied across the three primary comparisons.
- Logistic models use L2 penalisation with C = 1; multi-feature imaging models use the elastic net with the same tuning grid as the primary analysis.
- Clinical and imaging models are combined by equal-weight late fusion of out-of-fold probabilities.

# H3 – Prognostic information accrues over the care pathway

Time points: T0, admission (pre-treatment); T1, 24 h after treatment; T2, follow-up MRI (2–9 days).

Set A – full cohort (N = 129, both centres; follow-up DWI available for all patients):
- R1 (T0): age, admission NIHSS, premorbid mRS, glucose.
- R1_DWI (T2): R1 + log(1 + follow-up DWI infarct volume, mL).
- R1_DWI_plus_E (T2 + pre-treatment CTP): late fusion of R1_DWI and the all-channel CTP model E.
- P1_plus_DWI: late fusion of the clinical GBM P1 and a logistic model on log DWI infarct volume.
- PRIMARY H3: R1_DWI versus R1 (ΔAUC).
- Secondary: R1_DWI_plus_E versus R1_DWI (does pre-treatment CTP add once the final infarct is known?); P1_plus_DWI versus P1; within-centre AUCs.

Set B – Munich (n = 88; 24-h NIHSS recorded in about 83%):
- B0: R1; B1: R1 + 24-h NIHSS; B2: R1 + 24-h NIHSS + log DWI infarct volume; each also fused with E.
- Missing 24-h NIHSS: median imputation inside training folds; sensitivity analysis in complete cases.
- mTICI is not used (almost all patients 2c/3).

# H1 – Location rather than volume (atlas-based eloquence)

Registration: the MNI152 2-mm template (nilearn) is registered affinely (SimpleITK; Mattes mutual information; multi-resolution; 12 degrees of freedom) to each patient's skull-stripped follow-up DWI, which shares the NCCT space of the perfusion maps; atlas labels are resampled to the patient grid by nearest-neighbour interpolation. Quality control: Dice coefficient between the warped template brain mask and the patient brain mask; patients with Dice < 0.80 are flagged and excluded in a sensitivity analysis.

Atlases: Juelich (white-matter corticospinal tract); Harvard–Oxford subcortical (caudate, putamen, pallidum, thalamus); Harvard–Oxford cortical (insula; frontal, central and parietal opercular cortex; left inferior frontal gyrus pars opercularis and triangularis, left posterior superior temporal gyrus, left supramarginal and angular gyri).

Four location features are computed for (a) CTP hypoperfusion (Tmax > 6 s, ipsilateral tissue) and (b) the follow-up DWI infarct:
- L_CST: fraction of the ipsilateral corticospinal tract involved.
- L_DEEP: fraction of the ipsilateral basal ganglia and thalamus involved.
- L_INSOP: fraction of the ipsilateral insula and operculum involved.
- L_LANG: fraction of the left-hemisphere language cortex involved (0 for right-sided lesions).
For CTP, fractions are computed over atlas voxels inside the CTP slab, and coverage is recorded.

Models:
- Loc_CTP: elastic net on the four CTP location features.
- F_loc: late fusion of P1 and Loc_CTP. PRIMARY H1: F_loc versus P1.
- R1_Loc_CTP: elastic net on R1 + the four CTP location features (versus R1).
- R1_DWI_Loc: elastic net on R1 + log DWI infarct volume + the four DWI location features (versus R1_DWI).

# H2 – CTP adds value where it is clinically used (visible vessel occlusion)

Population: patients with a non-empty native-resolution vessel-occlusion mask in the original release. This hypothesis was suggested by an exploratory subgroup analysis of the same data; it is therefore not confirmatory and is reported as hypothesis-generating.
- Nested cross-validation within this population: P1, R1, E, Loc_CTP and the fusions P1 + E, R1 + E and P1 + Loc_CTP.
- PRIMARY H2: P1 + E versus P1 within the occlusion population.

# Reporting

All three hypotheses are reported, with Holm-adjusted P values for the three primary comparisons.
