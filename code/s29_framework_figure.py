"""Fig. 1 of the framework manuscript: data sources, cohort and the five modules (M1-M5)."""
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from config import TAB
from s09_figures import save

# Arial; neu may khong co Arial thi tu dong dung Liberation Sans / Helvetica (cung kich thuoc chu)
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "Liberation Sans", "Helvetica", "DejaVu Sans"]
plt.rcParams["pdf.fonttype"] = 42   # nhung font dang TrueType, de chinh sua duoc trong PDF/AI
plt.rcParams["ps.fonttype"] = 42

K = "black"


def main():
    site = json.load(open(TAB / "site_inference.json"))
    ss = pd.read_csv(TAB / "design_sample_size.csv")
    fig, ax = plt.subplots(figsize=(7.4, 5.9))
    ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(1.5, 13)

    def box(x, y, w, h, body, title=None, center=False, fs=8):
        ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=K, lw=1))
        if title is None:                       # hop chi co 1 dong in dam, can giua
            ax.text(x + w / 2, y + h / 2, body, ha="center", va="center",
                    fontsize=fs + 0.4, color=K, weight="bold")
        elif center:                            # tieu de dam o tren, noi dung duoi, can giua
            ax.text(x + w / 2, y + h - 0.2, title, ha="center", va="top",
                    fontsize=fs + 0.4, color=K, weight="bold")
            ax.text(x + w / 2, y + h - 0.62, body, ha="center", va="top",
                    fontsize=fs, color=K, linespacing=1.35)
        else:                                   # can trai
            ax.text(x + 0.15, y + h - 0.2, title, ha="left", va="top",
                    fontsize=fs + 0.4, color=K, weight="bold")
            ax.text(x + 0.15, y + h - 0.62, body, ha="left", va="top",
                    fontsize=fs, color=K, linespacing=1.35)

    def arr(x1, y1, x2, y2):
        # Leave a small visible gap before the target box border so the arrowhead
        # does not merge visually with the horizontal rule.
        gap = 0.09
        dx, dy = x2 - x1, y2 - y1
        length = (dx * dx + dy * dy) ** 0.5
        # Start just beyond the source border as well; short arrows keep a minimum head length.
        source_gap = min(0.025, max(0.0, length - gap - 0.09))
        x1 += source_gap * dx / length
        y1 += source_gap * dy / length
        x2 -= gap * dx / length
        y2 -= gap * dy / length
        ax.annotate("", (x2, y2), (x1, y1),
                    arrowprops=dict(arrowstyle="-|>", mutation_scale=8, color=K, lw=1, shrinkA=0, shrinkB=0))

    box(0.1, 11.6, 4.7, 1.25,
        "N = 149; per-patient z-normalised CTP maps;\nclinical table (standardised)",
        title="Public pre-processed ISLES'24 release", center=True)
    box(5.2, 11.6, 4.7, 1.25,
        "native-unit CTP maps, voxel size, follow-up DWI,\nlesion and occlusion masks",
        title="Original ISLES'24 release (per-subject mirror)", center=True)
    box(1.4, 10.5, 7.2, 0.65,
        "Analysed cohort: N = 129 with 90-day mRS (44 poor, mRS 3–6)")
    arr(2.45, 11.6, 3.6, 11.15); arr(7.55, 11.6, 6.4, 11.15)

    mods = [
        ("M1  Data readiness",
         "unit recovery, verified against native maps · audit of release-level imputation ·\n"
         f"centre inferred from data provenance ({site['cluster_sizes']['quantised']}/{site['cluster_sizes']['float']})"),
        ("M2  Locked evaluation protocol",
         "nested CV (5 seeds × 10-fold) · seed-mean AUC with patient bootstrap ·\n"
         "calibration · decision curves · precision / equivalence (±0.05 AUC)"),
        ("M3  Signal estimation",
         "pre-treatment CTP: channels, thresholds, volumes, location ·\n"
         "post-treatment course: 24-h NIHSS, follow-up infarct volume (supplementary analysis plan)"),
        ("M4  Transportability",
         "within-centre AUC · single-centre nested CV · leave-one-centre-out validation"),
        ("M5  Design outputs",
         "sample size by target ΔAUC · Riley minimum sample size ·\n"
         f"go / no-go table (e.g. CTP: ≈{int(ss.iloc[0]['n_for_delta_0.05'])} patients to detect ΔAUC 0.05)"),
    ]
    y = 8.75
    for t, d in mods:
        box(0.1, y, 9.8, 1.35, d, title=t)
        y -= 1.75
    arr(5.0, 10.5, 5.0, 10.1)
    for k in range(4):
        arr(5.0, 8.75 - 1.75 * k, 5.0, 8.75 - 1.75 * k - 0.4)
    save(fig, "Fig1_framework")


if __name__ == "__main__":
    main()