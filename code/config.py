"""Shared paths and constants for the Branch 3 re-analysis (v3).

All paths are relative to this file; no absolute paths are used. Optional environment variables override them:
  BRANCH3_DATA_ROOT  folder holding the extracted public datasets (default: ../extracted/branch3)
  ISLES24_DIR        pre-processed ISLES'24 release folder (default: <BRANCH3_DATA_ROOT>/01_DATASET_ISLES2024_PRIMARY/
                     DATASET_ISLES2024/processed_ISLES2024/processed)
  ISLES18_DIR        ISLES 2018 training set folder
  BRANCH3_OUT        output folder (default: ./outputs). From the audit package, point it to a folder containing
                     tables/, oof/, data/ and figures/ copied from 03_RESULTS_M1_M5, 02_NUMERICAL_EVIDENCE and 05_FIGURES.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PKG = Path(os.environ.get("BRANCH3_DATA_ROOT", ROOT.parent / "extracted" / "branch3"))
ISLES24 = Path(os.environ.get("ISLES24_DIR", PKG / "01_DATASET_ISLES2024_PRIMARY" / "DATASET_ISLES2024" / "processed_ISLES2024" / "processed"))
ISLES18 = Path(os.environ.get("ISLES18_DIR", PKG / "02_DATASET_EXTERNAL_TECHNICAL" / "ISLES2018_DTS"))
BENCH_CSV = PKG / "03_RESULTS_INTERNAL_CV" / "clinical_benchmark_scores.csv"

OUT = Path(os.environ.get("BRANCH3_OUT", ROOT / "outputs"))
DATA = OUT / "data"
TAB = OUT / "tables"
FIG = OUT / "figures"
OOF = OUT / "oof"
for d in (OUT, DATA, TAB, FIG, OOF):
    d.mkdir(parents=True, exist_ok=True)

SEEDS = [42, 100, 2024, 777, 999]   # same evaluation seeds as Branch 2
N_OUTER = 10                         # primary protocol: 5 repeats x stratified 10-fold
N_INNER = 5
N_BOOT = 2000
BOOT_SEED = 20261111

# Clip limits used by the public pre-processing (config_snapshot.json), in physical units
CLIP = {"CBF": 100.0, "CBV": 10.0, "MTT": 30.0, "Tmax": 30.0}
CHANNELS = ["CBF", "CBV", "MTT", "Tmax"]

CLINICAL_22 = [
    "Sex", "Wake-up", "In-House", "Referral", "Atrial fibrillation", "Hypertension", "Diabetes",
    "Hyperlipidemia", "Anticoagulation", "Lipid lowering drugs", "PAIs", "mRS at admission",
    "mRS premorbid", "NIHSS at admission", "Age", "Glucose", "Leucocytes", "CRP", "INR",
    "Onset to door_min", "Alert to door_min", "Door to imaging_min",
]
INTRA_PROCEDURAL = ["Door to groin_min", "Door to first series_min", "Door to recanalization_min",
                    "Time of intervention_min"]
