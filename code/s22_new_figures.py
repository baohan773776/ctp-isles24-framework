"""Figures for the additional analyses.
Fig8_robustness: incremental value of CTP (delta AUC, 95% CI) across all analytic settings, with the
                 +/-0.05 equivalence band.
FigS3_native_agreement: native-unit vs recovered features (ICC per feature; two example scatters).
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from config import TAB, FIG, DATA
import features as F
from s09_figures import S, INK, INK2, MUTED, GRID, BASE, save


def fig8():
    comp_all = pd.read_csv(TAB / "paired_auc_comparisons_all.csv")
    mun = pd.read_csv(TAB / "paired_auc_comparisons_munich.csv")
    wc = pd.read_csv(TAB / "within_centre_paired.csv")
    geo = pd.read_csv(TAB / "geographic_validation_paired.csv")

    def g(df, new, ref, dcol="delta_auc", extra=None):
        q = df[(df.new == new) & (df.reference == ref)]
        if extra is not None:
            q = q[q.direction == extra]
        r = q.iloc[0]
        return r[dcol], r.ci_lo, r.ci_hi

    rows = [
        ("Primary: clinical GBM + CTP (recovered units), pooled CV", g(comp_all, "F_late_P1_E", "P1_clin_GBM"), "Pooled nested CV (N = 129)"),
        ("Reference = 4-predictor logistic model", g(comp_all, "F_late_R1_E", "R1_clin_LR4"), "Pooled nested CV (N = 129)"),
        ("Reference = recalibrated clinical GBM", g(comp_all, "F_late_P1recal_E", "P1_recal"), "Pooled nested CV (N = 129)"),
        ("CTP features from native-unit maps", g(comp_all, "F_late_P1_Enat", "P1_clin_GBM"), "Pooled nested CV (N = 129)"),
        ("Absolute CTP volumes (mL), late fusion", g(comp_all, "F_late_P1_V", "P1_clin_GBM"), "Pooled nested CV (N = 129)"),
        ("Absolute CTP volumes (mL), joint logistic model", g(comp_all, "R1_plus_volumes", "R1_clin_LR4"), "Pooled nested CV (N = 129)"),
        ("Within-centre concordance (pooled CV predictions)", g(wc, "F_late_P1_E", "P1_clin_GBM", "delta_within"), "Centre-aware"),
        ("Munich only, nested CV (n = 88)", g(mun, "F_late_P1_E", "P1_clin_GBM"), "Centre-aware"),
        ("Munich only, native-unit CTP features", g(mun, "F_late_P1_Enat", "P1_clin_GBM"), "Centre-aware"),
        ("Developed in Munich, tested in Zurich (n = 41, 6 events)", g(geo, "F_late_P1_E", "P1_clin_GBM", extra="Munich -> Zurich"), "Centre-aware"),
    ]
    fig, ax = plt.subplots(figsize=(7.4, 4.9))
    ax.axvspan(-0.05, 0.05, color="#eef4fc", zorder=0)
    ax.axvline(0, color=MUTED, lw=1, zorder=1)
    y = np.arange(len(rows))[::-1].astype(float)
    groups = [r[2] for r in rows]
    for yi, (lab, (d, lo, hi), grp) in zip(y, rows):
        col = S[0] if grp.startswith("Pooled") else S[1]
        clipped_hi = min(hi, 0.42)
        ax.hlines(yi, max(lo, -0.32), clipped_hi, color=col, lw=2, zorder=2)
        ax.plot(d, yi, "o", color=col, ms=7, mec="white", mew=1.5, zorder=3)
        ax.text(0.445, yi, f"{d:+.3f} ({lo:+.3f}, {hi:+.3f})".replace("-", "−"), va="center", fontsize=7.4, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=7.8)
    ax.set_xlim(-0.33, 0.43)
    ax.set_xlabel("ΔAUC for adding CTP to the clinical reference (95% bootstrap CI)")
    ax.grid(axis="y", visible=False)
    ax.text(0.0, len(rows) - 0.35, "equivalence band ±0.05", ha="center", fontsize=7.4, color=INK2)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], color=S[0], marker="o", lw=2, label="Pooled nested CV (N = 129)"),
                       Line2D([], [], color=S[1], marker="o", lw=2, label="Centre-aware analyses")],
              loc="lower left", bbox_to_anchor=(0.0, -0.3), ncol=2, fontsize=7.8)
    save(fig, "Fig8_robustness")


def figS3():
    ag = pd.read_csv(TAB / "native_vs_recovered_agreement.csv")
    nat = pd.read_csv(DATA / "ctp_features_native_149.csv").set_index("subject_id")
    rec = pd.read_csv(DATA / "ctp_features_v3_149.csv").set_index("subject_id")
    ids = pd.read_csv(DATA / "cohort_129.csv").subject_id
    fig, axs = plt.subplots(1, 3, figsize=(7.4, 2.7), gridspec_kw={"width_ratios": [1.3, 1, 1]})
    ch = ["CBF", "CBV", "MTT", "Tmax", "Mismatch"]
    for i, c in enumerate(ch):
        v = ag[ag.channel == c].icc31.values
        axs[0].scatter(np.full(len(v), i) + np.random.default_rng(i).uniform(-0.15, 0.15, len(v)), v, s=14,
                       color=S[i], edgecolor="white", lw=0.6, zorder=3)
    axs[0].axhline(0.9, color=MUTED, lw=1, ls="--")
    axs[0].set_xticks(range(len(ch))); axs[0].set_xticklabels(ch, fontsize=7.4, rotation=30, ha="right")
    axs[0].set_ylabel("ICC(3,1) native vs recovered"); axs[0].set_ylim(0.65, 1.01)
    axs[0].set_title("a  Feature-level agreement", loc="left", fontsize=9)
    for ax, f, lab, k in ((axs[1], "tmax_gt6_frac", "Tmax >6 s fraction", "b"), (axs[2], "cbv_index_hypo", "CBV index", "c")):
        a, b = nat.loc[ids, f"nat_{f}"], rec.loc[ids, f]
        ax.scatter(b, a, s=12, color=S[0], edgecolor="white", lw=0.5, zorder=3)
        lo, hi = min(a.min(), b.min()), max(a.max(), b.max())
        ax.plot([lo, hi], [lo, hi], color=MUTED, lw=1)
        icc = ag.set_index("feature").loc[f, "icc31"]
        ax.set_title(f"{k}  {lab} (ICC {icc:.2f})", loc="left", fontsize=9)
        ax.set_xlabel("recovered (public release)"); ax.set_ylabel("native units")
    fig.tight_layout()
    save(fig, "FigS3_native_agreement")


if __name__ == "__main__":
    fig8(); figS3(); print("ok")
