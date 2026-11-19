"""Fig. 1 of the framework manuscript: data sources, cohort and the five modules (M1-M5)."""
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from config import TAB
from s09_figures import INK, INK2, BASE, save

TINT = ["#e3eefb", "#fbe6dc", "#ddf3ea", "#fbf0d6", "#f9e3ec"]


def main():
    site = json.load(open(TAB / "site_inference.json"))
    ss = pd.read_csv(TAB / "design_sample_size.csv")
    fig, ax = plt.subplots(figsize=(7.4, 5.9)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(1.5, 13)

    def box(x, y, w, h, t, fc="#f3f2ef", fs=7.6, bold=None):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12", fc=fc, ec=BASE, lw=1))
        if bold:
            ax.text(x + 0.15, y + h - 0.2, bold, ha="left", va="top", fontsize=fs + 0.6, color=INK, weight="bold")
            ax.text(x + 0.15, y + h - 0.62, t, ha="left", va="top", fontsize=fs, color=INK, linespacing=1.35)
        else:
            ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs, color=INK, linespacing=1.35)

    def arr(x1, y1, x2, y2):
        ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1))

    box(0.1, 11.6, 4.7, 1.25, "Public pre-processed ISLES'24 release\nN = 149; per-patient z-normalised CTP maps;\nclinical table (standardised)")
    box(5.2, 11.6, 4.7, 1.25, "Original ISLES'24 release (per-subject mirror)\nnative-unit CTP maps, voxel size, follow-up DWI,\nlesion and occlusion masks")
    box(1.4, 10.25, 7.2, 0.9, "Analysed cohort: N = 129 with 90-day mRS (44 poor, mRS 3–6)", fc="#cde2fb")
    arr(2.45, 11.6, 3.6, 11.15); arr(7.55, 11.6, 6.4, 11.15)
    mods = [
        ("M1  Data readiness", "unit recovery, verified against native maps · audit of release-level imputation ·\n"
         f"centre inferred from data provenance ({site['cluster_sizes']['quantised']}/{site['cluster_sizes']['float']})"),
        ("M2  Locked evaluation protocol", "nested CV (5 seeds × 10-fold) · seed-mean AUC with patient bootstrap ·\n"
         "calibration · decision curves · precision / equivalence (±0.05 AUC)"),
        ("M3  Signal estimation", "pre-treatment CTP: channels, thresholds, volumes, location ·\n"
         "post-treatment course: 24-h NIHSS, follow-up infarct volume (supplementary analysis plan)"),
        ("M4  Transportability", "within-centre AUC · single-centre nested CV · leave-one-centre-out validation"),
        ("M5  Design outputs", "sample size by target ΔAUC · Riley minimum sample size ·\n"
         f"go / no-go table (e.g. CTP: ≈{int(ss.iloc[0]['n_for_delta_0.05'])} patients to detect ΔAUC 0.05)"),
    ]
    y = 8.75
    for (t, d), fc in zip(mods, TINT):
        box(0.1, y, 9.8, 1.35, d, fc=fc, bold=t)
        y -= 1.75
    arr(5.0, 10.25, 5.0, 10.1)
    for k in range(4):
        arr(5.0, 8.75 - 1.75 * k, 5.0, 8.75 - 1.75 * k - 0.4)
    save(fig, "Fig1_framework")


if __name__ == "__main__":
    main()
