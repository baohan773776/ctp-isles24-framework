"""Redraw manuscript Figures 3 and 6 with descriptive model names (no internal model codes such as P1, E, F).
Uses the canonical plotting functions of s09_figures unchanged; only the label dictionary and the output folder are
replaced, so every plotted number is read from the same canonical tables. Output: outputs_validity/figures/final/."""
from v_common import VFIG  # noqa: F401  (sets sys.path)
import s09_figures as S

OUT = VFIG / "final"
OUT.mkdir(parents=True, exist_ok=True)
S.FIG = OUT
S.LABEL.update({
    "P1_clin_GBM": "Clinical GBM (22 predictors)",
    "F_late_P1_E": "Clinical GBM + CTP (late fusion)",
    "E_CTP_all": "CTP, all channels",
    "T_thresholds": "CTP, classical thresholds",
    "A_CBF": "CBF only", "B_CBV": "CBV only", "C_MTT": "MTT only", "D_Tmax": "Tmax only",
})
S.fig3_forest()
S.fig5_calibration()
print(sorted(p.name for p in OUT.iterdir()))
