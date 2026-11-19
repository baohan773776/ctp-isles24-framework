# Data notice

The source imaging data are not redistributed with this code.

- ISLES'24 training set: Zenodo, doi:10.5281/zenodo.17652035 (CC BY-NC-SA 4.0); per-subject mirror on Hugging Face
  (`hugging-science/isles24-stroke`). The pre-processed release (z-normalised perfusion maps, masks, standardised
  clinical table) is the input of the primary analysis; the original release (native-unit maps, follow-up DWI) is read
  per subject by HTTP range requests (`s13_fetch_native.py`, `httpfile.py`).
- ISLES 2018 training set: https://www.isles-challenge.org (simulation of the pre-processing, `s03`).

`outputs/` (or `results/` in the code-repository bundle) contains derived, de-identified outputs only: result tables,
fold manifests, out-of-fold predictions, the inferred centre labels, atlas-location features, acquisition
fingerprints and the per-patient CTP feature tables. Three small tabular files of the pre-processed ISLES'24 release
(`clinical_features.csv`, `outcome_labels.csv`, `config_snapshot.json`; pseudonymous subject IDs, standardised
clinical values, outcome scales, pre-processing configuration) are redistributed in the audit package under the same
CC BY-NC-SA 4.0 terms with attribution to the ISLES'24 providers, so that `s01_build_cohort.py` and the unit-recovery
constants can be reproduced without the imaging volumes. Derived data inherit the CC BY-NC-SA 4.0 terms of ISLES'24.

Input locations are set in `config.py` (environment variables `BRANCH3_DATA_ROOT`, `ISLES24_DIR`, `ISLES18_DIR`,
`BRANCH3_OUT`). Run the scripts in the order given in `README.md` to regenerate everything from the public data.
