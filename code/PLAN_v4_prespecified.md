# Pre-specified analysis plan, round 4 (written 2026-11-11, BEFORE any of these analyses were run)

The aim is to test three hypotheses that could strengthen the paper. Rules:
- every model is fixed here and run on the same evaluation protocol (5 seeds x stratified 10-fold, inner 5-fold CV);
- every result is reported, including null results;
- primary comparison per hypothesis = the one marked PRIMARY; Holm correction across the three PRIMARY tests;
- logistic models use L2 C = 1 (as before); multi-feature imaging models use elastic net (same grid);
- equal-weight late fusion as before.

## H3 - Prognostic information accrues over the care pathway (timeline model)

Time points: T0 admission (pre-treatment), T1 24 h after treatment, T2 follow-up MRI (2-9 days).

Set A - full cohort (N = 129, both centres; DWI available for all):
- R1 (T0): age, NIHSS, premorbid mRS, glucose (existing)
- R1_DWI (T2): R1 + log(1 + DWI final-infarct volume, mL)
- R1_DWI_plus_E (T2 + pre-treatment CTP): late fusion of R1_DWI and E_CTP_all
- P1_plus_DWI: late fusion of P1 and DWI_only (logistic on log DWI volume)
- PRIMARY H3: R1_DWI vs R1 (delta AUC)
- secondary: R1_DWI_plus_E vs R1_DWI (does pre-treatment CTP add once the final infarct is known?); P1_plus_DWI vs P1; within-centre AUCs

Set B - Munich (n = 88; NIHSS 24 h recorded in about 83%):
- B0 R1; B1 R1 + NIHSS 24 h; B2 R1 + NIHSS 24 h + log DWI volume; each also fused with E_CTP_all
- missing NIHSS 24 h: median imputation inside training folds (sensitivity: complete cases)
- mTICI not used (almost all 2c/3)

## H1 - Location, not volume (atlas-based eloquence)

Registration: MNI152 2-mm template (nilearn) affinely registered (SimpleITK, Mattes MI, multi-resolution, 12 dof)
to each subject's skull-stripped follow-up DWI (same NCCT space as the perfusion maps); atlas labels resampled to
the subject grid with nearest neighbour. QC: Dice of warped MNI brain mask vs subject brain mask; subjects with
Dice < 0.80 are flagged and excluded in a sensitivity analysis.

Atlases: Juelich (WM corticospinal tract), Harvard-Oxford subcortical (caudate, putamen, pallidum, thalamus),
Harvard-Oxford cortical (insula; frontal/central/parietal opercular cortex; left IFG pars opercularis and
triangularis, left posterior STG, left supramarginal and angular gyri).

Four location features, computed for (a) CTP hypoperfusion (Tmax > 6 s, ipsilateral tissue) and (b) the DWI final infarct:
- L_CST: fraction of the ipsilateral corticospinal tract involved
- L_DEEP: fraction of ipsilateral basal ganglia + thalamus involved
- L_INSOP: fraction of ipsilateral insula + operculum involved
- L_LANG: fraction of left-hemisphere language cortex involved (0 for right-sided lesions)
For CTP, fractions are computed over atlas voxels inside the CTP slab; coverage is recorded.

Models:
- Loc_CTP: elastic net on the 4 CTP location features
- F_loc: late fusion P1 + Loc_CTP. PRIMARY H1: F_loc vs P1
- R1_Loc_CTP: elastic net on R1 + 4 CTP location features (vs R1)
- Loc_DWI and R1_DWI_Loc: elastic net on R1 + log DWI volume + 4 DWI location features (vs R1_DWI)

## H2 - CTP adds value where it is clinically used (vessel occlusion visible)

Population: patients with a non-empty native-resolution LVO mask (original release).
This hypothesis was suggested by the exploratory subgroup analysis on the same data, so it is NOT confirmatory and
will be reported as hypothesis-generating.
- nested CV within the population: P1, R1, E_CTP_all, Loc_CTP, fusions P1+E, R1+E, P1+Loc_CTP
- PRIMARY H2: P1+E vs P1 within the LVO population

## Reporting
All three directions are reported in the manuscript (main text: H3 and H1; H2 in supplement), with the Holm-adjusted
P values for the three PRIMARY comparisons.
