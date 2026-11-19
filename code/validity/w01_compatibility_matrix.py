"""Writes EXTERNAL_DATASET_COMPATIBILITY_MATRIX.csv (facts verified 2026-11-14 from primary sources; see
DATA_ACCESS_REQUESTS.md and FINAL_VALIDITY_AUDIT.md for source URLs). UNVERIFIED marks facts not confirmed."""
import csv
from v_common import VTAB

COLS = ["dataset", "official_source", "version_checked", "independent_patients", "scans_or_slabs", "modalities",
        "ctp_maps_and_units", "baseline_clinical_predictors", "mrs_90d_available", "imaging_ground_truth_type",
        "annotation_provenance", "anatomical_target_definition", "treatment_population", "outcome_timing", "license",
        "access_class", "local_availability", "overlap_risk_with_ISLES24", "modules_validatable", "compatible_component",
        "frozen_model_evaluation_possible", "scientific_status", "status_reason", "used_in_this_revision"]

ROWS = [
    ["ISLES'24 training set (development cohort; reference row)", "doi:10.5281/zenodo.17652035; HF mirror hugging-science/isles24-stroke; descriptor arXiv:2408.11142 v1/v2",
     "Zenodo 2025-11-20 (149 cases); descriptor v2 2025-07-06", "149 (129 with 90-day mRS)", "149", "NCCT, CTA, CTP 4D, CTP maps, follow-up DWI/ADC, lesion/LVO/CoW masks",
     "CBF, CBV, MTT, Tmax from icobrain cva; native maps in the original release; pre-processed release z-normalised",
     "age, sex, NIHSS, premorbid mRS, glucose, labs, times (22 used)", "yes (3-month mRS)", "DWI final infarct (manual/semi-automatic per descriptor)",
     "challenge organisers", "final infarct on follow-up DWI", "thrombectomy, mTICI 2c/3", "90 days", "CC BY-NC-SA 4.0", "PUBLIC_DIRECT",
     "local (pre-processed release + per-subject native maps, DWI, NCCT)", "is the development cohort", "M1-M5 (internal only)",
     "all", "no (development data)", "INTERNAL_DEVELOPMENT", "Any subset (incl. inferred Zurich) is part of the development data and is never an independent external cohort", "yes (internal analyses)"],
    ["ISLES 2018 (training set)", "SMIR (now inactive); Hakim et al. Stroke 2021;52:2328; arXiv:1811.01085", "local copy, SMIR object metadata 2018-07-03",
     "63 (training; verified from SMIR descriptions Train_<patient>_<slab>)", "94 slabs (31 patients with 2 slabs)", "CTP 4D (resampled 1 s), CTP maps, DWI-derived mask (no NCCT/CTA)",
     "CBF, CBV, MTT, Tmax from RAPID (iSchemaView); Tmax/MTT in s; CBF/CBV absolute scale differs from ISLES'24 (median CBF ~210, CBV ~30 in brain; units UNVERIFIED, 'each image had different units')",
     "none distributed (aggregate only)", "no", "manual DWI infarct core (single stroke neurologist, group-reviewed), DWI within 3 h of CTP",
     "expert manual", "early DWI infarct core (no treatment between CTP and DWI)", "anterior LVO <= 8 h (2 trials incl. DEFUSE 2); treatment not per case",
     "none", "SMIR licence (ODC-ODbL file distributed with data)", "UNVERIFIED (was PUBLIC_REGISTRATION via SMIR, now defunct)", "local",
     "none (different continent/period)", "M1 (CTP feature extraction, physical consistency, core vs DWI)", "CTP feature extractor (s02.features_from_maps) and CTP-core mask",
     "yes for technical component; no prognostic", "TECHNICAL_COMPONENT", "CTP maps + expert DWI core but no clinical predictors and no 90-day mRS", "yes: benchmark 1 (vX1)"],
    ["UniToBrain", "doi:10.5281/zenodo.5084647 (Gava et al. 2021)", "V1.2 (2021-06-03)", "115 subjects (100 train / 15 test; subsample of 258)", "115 CTP studies",
     "raw 4D CTP (DICOM), registered/filtered series, perfusion maps", "CBF, CBV, Delay, MTT, TTP (no Tmax) from in-house nonlinear-regression software (GE 64-slice, 40 mm); described as relative maps; units UNVERIFIED",
     "none", "no", "software-derived reference perfusion maps (not manual, not physiological truth)", "in-house software", "n/a (maps)", "unselected CTP patients (Molinette, Turin)",
     "none", "CC BY 4.0", "PUBLIC_DIRECT", "not local; single archive ctp_data.7z = 50.8 GB", "none", "M1 (map-level transportability) only if Tmax and comparable units existed",
     "partially: CBF/CBV/MTT relative features; NOT Tmax, thresholds, mismatch (no Tmax map)", "no", "TECHNICAL_COMPONENT (not executed)",
     "No Tmax map (the pipeline's hypoperfusion, core gating and mismatch are Tmax-based); relative maps from a different algorithm; 50.8 GB solid archive judged an unnecessarily large download for a partial check", "no (BLOCKED: size/semantic mismatch)"],
    ["Johns Hopkins head CT brain extraction", "doi:10.7281/T1/CZDPSX (Muschelli et al. NeuroImage 2015;114:379)", "v1.1 (2019-09-18, updated 2025-05-30)",
     "35 subjects", "~38 scans (2 subjects with 2 scans; 1 with 2 kernels)", "NCCT", "n/a", "none", "no", "manual binary masks (2 readers)", "expert manual",
     "brain areas INCLUDING CSF (intracranial-type mask; repository abstract)", "intracerebral/intraventricular haemorrhage (MISTIE II/III, CLEAR III) - not ischaemic stroke",
     "none", "CC BY-NC 4.0", "PUBLIC_DIRECT (per rights statement; automated download refused: HTTP 403 / browser challenge)", "not local (~430 MB)", "none",
     "M1 pre-processing (admission-NCCT intracranial mask used by Experiment D)", "vD_registration.intracranial_mask (target = intracranial cavity incl. CSF -> definitions match)",
     "yes (technical)", "TECHNICAL_COMPONENT (prepared, not executed)", "Target definitions compatible; data could not be retrieved programmatically; script vX3 ready for a manual download", "no (BLOCKED: access)"],
    ["CPAISD", "doi:10.5281/zenodo.10892316 (Umerenkov et al., arXiv:2404.02518; Sci Data 2025)", "revision 6 (2024-03-28)", "112 (implied: 112 studies after exclusions)",
     "112 NCCT studies (local: 71 of 92 training studies)", "NCCT only (CTP not released)", "none", "age, sex, NIHSS, time, DSA flag, lethality", "no (lethality only)",
     "manual core and penumbra drawn on NCCT while viewing CTP maps; labels 0/1/2 (verified locally)", "single radiologist", "NCCT-visible core (1) and penumbra (2); NO brain/parenchyma mask",
     "mixed; 41 selected for EVT, no per-patient treatment field", "n/a", "CC BY 4.0", "PUBLIC_DIRECT", "local (partial)", "none",
     "none", "none: the pipeline has no NCCT core/penumbra output and no CTP input for CPAISD", "no", "INCOMPATIBLE",
     "No matching pipeline output (modality NCCT, task core/penumbra segmentation); not a brain-mask or CTP-map ground truth. Legacy 'brain-mask Dice 0.962' result is invalid (no such reference exists)", "no (SKIPPED_NOT_APPLICABLE)"],
    ["AISD", "github.com/GriffinLiang/AISD (Liang et al. MICCAI 2021)", "README checked 2026-11-14", "UNVERIFIED (397 scans reported)", "397 NCCT scans",
     "NCCT (5 mm)", "none", "none", "no", "manual NCCT lesion contours guided by DWI within 24 h", "expert manual, double-reviewed", "acute/remote ischaemic lesion classes on NCCT",
     "acute ischaemic stroke < 24 h; treatment unknown", "n/a", "non-commercial", "PUBLIC_DIRECT (Google Drive/Baidu)", "not local", "none", "none",
     "none: no NCCT lesion output in the pipeline", "no", "INCOMPATIBLE", "Lesion masks are not brain-extraction or CTP ground truth; no CTP, no mRS", "no (SKIPPED_NOT_APPLICABLE)"],
    ["CONTRAST consortium (MR CLEAN-NO IV / -MED / -LATE)", "https://www.contrast-consortium.nl/data-requests", "page checked 2026-11-14",
     "NO IV 539; LATE ~500; MED ~1500 (trial publications)", "per trial", "NCCT, CTA, CTP in a subset (NO IV: 259/539 admission CTP; LATE: 313 with CTP; MED: UNVERIFIED)",
     "site/vendor-specific CTP processing; harmonisation required", "age, NIHSS, premorbid mRS, glucose expected in trial CRFs (UNVERIFIED per variable)",
     "yes (90-day mRS primary outcome of the trials; UNVERIFIED here)", "n/a", "trial core lab", "n/a", "EVT-treated (randomised trials)", "90 days", "data-use agreement",
     "REQUEST_REQUIRED", "not available", "none", "M3/M4/M5: true external prognostic validation", "R1 clinical model + CTP features (frozen), possibly full 22 predictors",
     "yes, if granted", "FULL_PROGNOSTIC (potential; not available)", "Independent EVT cohorts with baseline CTP subset and 90-day mRS; access requires an approved request", "no (request drafted)"],
    ["CRISP (NCT01622517)", "Lansberg et al. Lancet Neurol 2017; clinicaltrials.gov NCT01622517", "registry checked 2026-11-14", "190 analysed (201 enrolled), 6 US centres",
     "1 baseline CTP each", "NCCT, CTP (RAPID), MRI follow-up", "RAPID: rCBF<30% core, Tmax>6 s", "age, NIHSS; premorbid mRS>=2 excluded; glucose UNVERIFIED",
     "yes (secondary outcome)", "n/a", "core lab", "n/a", "all EVT (88 also IV tPA)", "90 days (secondary); 30-day NIHSS primary", "none stated",
     "UNVERIFIED (REQUEST_REQUIRED presumed)", "not available", "none", "M3/M4: external prognostic validation (R1 + RAPID-derived volumes)",
     "R1 clinical + threshold volumes (absolute RAPID volumes; not the 53-feature set without raw maps)", "partially, if granted", "PARTIAL_PROGNOSTIC (potential; not available)",
     "EVT cohort with RAPID CTP and 90-day mRS; no IPD-sharing statement; raw maps availability unknown", "no (request drafted)"],
    ["VISTA Endovascular", "https://vistacollaboration.org/vista/ (TLS certificate invalid at check)", "UNVERIFIED", "pooled EVT trial IPD (size UNVERIFIED)", "UNVERIFIED",
     "imaging availability UNVERIFIED (CT lesion data only for selected trials)", "UNVERIFIED (CTP likely absent)", "age, NIHSS, glucose typical of trial IPD", "yes (trial outcomes)", "n/a",
     "trial data", "n/a", "EVT trials", "90 days", "steering-committee agreement", "REQUEST_REQUIRED", "not available", "possible overlap with CONTRAST trials (MR CLEAN)",
     "M4/M5: R1 clinical external validation; CTP unlikely", "R1 clinical model only", "partially", "PARTIAL_PROGNOSTIC (clinical only; potential)",
     "Outcome and clinical predictors likely present; CTP maps not confirmed; policy restricts reanalysis of treatment effects", "no (request drafted)"],
]


def main(out):
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLS)
        for r in ROWS:
            assert len(r) == len(COLS), (r[0], len(r))
            w.writerow(r)


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else VTAB / "EXTERNAL_DATASET_COMPATIBILITY_MATRIX.csv")
