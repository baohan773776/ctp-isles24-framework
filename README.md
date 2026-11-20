# Analysis code, derived results and frozen models

Code, derived tables, out-of-fold predictions and fitted models accompanying the manuscript
"A reproducible framework for evaluating the incremental prognostic value of CT perfusion after thrombectomy: feasibility study on the public ISLES'24 dataset and design parameters for a definitive study" (submitted to BMC Medical Informatics and Decision Making). Source: https://github.com/baohan773776/ctp-isles24-framework. Archived release: https://doi.org/10.5281/zenodo.24368051.

## Layout
| Path | Content |
|---|---|
| `code/` | Analysis scripts `s01`-`s30` (run in order) and `validity/` (robustness and verification scripts) |
| `code/archive/` | Superseded scripts and manuscript/package builders. **Not needed to reproduce results.** |
| `models/` | Three frozen `.joblib` models, feature lists, `model_card.json`, `apply_frozen_models.py` |
| `results/` | Result tables, out-of-fold predictions, derived data, figures |
| `requirements.txt` | Pinned dependencies (Python 3.10.11) |

## Reproduce
```
python -m venv .venv && pip install -r requirements.txt
cd code && python s01_build_cohort.py   # then s02 ... s30
```
Raw imaging is **not** included; scripts read the public ISLES data (see `code/DATA_NOTICE.md`).

## Figure numbering: manuscript vs `results/`
Final manuscript figures (PNG and PDF) are in `figures/`. Source files in `results/`:

| Manuscript figure | File in `figures/` | Source in `results/primary_analysis/figures/` |
|---|---|---|
| Figure 1 | `Figure1_framework` | `Fig1_framework` |
| Figure 2 | `Figure2_unit_recovery` | `Fig2_unit_recovery_validation` |
| Figure 3 | `Figure3_auc_forest` | `Fig3_auc_forest` |
| Figure 4 | `Figure4_robustness` | `Fig8_robustness` |
| Figure 5 | `Figure5_post_treatment` | `Fig9_timeline` |
| Figure 6 | `Figure6_calibration` | `Fig5_calibration` |

Other `Fig*` / `FigS*` files in `results/` are supplementary or intermediate versions.
## Data and licences
- **Code** (`code/`, `models/*.py`): MIT, see `LICENSE`.
- **Derived tables, predictions, models** (`results/`, `models/*.joblib`): derived from ISLES'24 (CC BY-NC-SA 4.0); released under **CC BY-NC-SA 4.0**, non-commercial use only. Verify against the dataset terms.
- Patient identifiers are the public ISLES codes (e.g. `sub-stroke0001`); no names or dates of birth.

## Models
Research use only; not validated for clinical use. See `models/README.md` and `model_card.json`.

## AI-assistance disclosure
Claude (Anthropic) was used to help write analysis code and draft text. ChatGPT (OpenAI) was used to review the submission package for consistency. The authors reviewed all code, outputs and text and take full responsibility for the content.

## Citation
See `CITATION.cff`.
