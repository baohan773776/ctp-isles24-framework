"""Round-4 summary (PLAN_v4_prespecified.md): Holm adjustment of the three PRIMARY tests and Fig. 9 (timeline)."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from config import TAB
from s09_figures import S, INK2, MUTED, save


def holm():
    t = pd.read_csv(TAB / "timeline_paired.csv"); l = pd.read_csv(TAB / "location_lvo_paired.csv")
    prim = pd.concat([t[t.role.str.startswith("PRIMARY")], l[l.role.str.startswith("PRIMARY")]]).reset_index(drop=True)
    o = np.argsort(prim.p_bootstrap.values); m = len(prim); adj = np.empty(m); run = 0
    for k, i in enumerate(o):
        run = max(run, min(1.0, (m - k) * prim.p_bootstrap.values[i])); adj[i] = run
    prim["p_holm"] = adj
    prim.to_csv(TAB / "round4_primary_holm.csv", index=False)
    print(prim[["role", "delta_auc", "ci_lo", "ci_hi", "p_bootstrap", "p_holm"]].round(3).to_string(index=False))


def fig9():
    p = pd.read_csv(TAB / "timeline_performance.csv")
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.3), gridspec_kw={"width_ratios": [1.15, 1]})
    # (a) Munich timeline
    b = p[p.set == "B: Munich"].set_index("model")
    x = np.arange(3)
    for models, col, lab, dx in ((["R1_clin_LR4", "R1_N24", "R1_N24_DWI"], S[0], "clinical course", -0.06),
                                 (["R1_plus_E", "R1_N24_plus_E", "R1_N24_DWI_plus_E"], S[1], "+ pre-treatment CTP", 0.06)):
        v = b.loc[models]
        axs[0].errorbar(x + dx, v.auc, yerr=[v.auc - v.auc_lo, v.auc_hi - v.auc], color=col, marker="o", ms=6,
                        lw=2, capsize=0, mec="white", mew=1.2, label=lab)
        for xi, a in zip(x + dx, v.auc):
            axs[0].text(xi + (0.09 if dx > 0 else -0.09), a + (-0.012 if dx > 0 else 0.012), f"{a:.2f}", fontsize=7,
                        color=INK2, va="top" if dx > 0 else "bottom", ha="left" if dx > 0 else "right")
    axs[0].set_xticks(x); axs[0].set_xticklabels(["Admission\n(age, NIHSS,\npremorbid mRS, glucose)", "+ NIHSS 24 h", "+ DWI infarct\nvolume (2–9 d)"], fontsize=7.5)
    axs[0].set_ylabel("AUC (mean of 5 seeds, 95% CI)"); axs[0].set_ylim(0.5, 1.0); axs[0].set_xlim(-0.5, 2.5)
    axs[0].set_title("a  Munich (n = 88, 38 poor outcomes)", loc="left", fontsize=9)
    axs[0].legend(loc="lower right", fontsize=7.5)
    # (b) full cohort
    a = p[p.set == "A: full cohort"].set_index("model")
    rows = [("R1_clin_LR4", "4-predictor admission model", "pre"), ("P1_clin_GBM", "Clinical GBM (22 predictors)", "pre"),
            ("F_late_P1_E", "Clinical GBM + CTP", "pre"), ("R1_DWI", "4-predictor + DWI volume", "post"),
            ("P1_plus_DWI", "Clinical GBM + DWI volume", "post"), ("R1_DWI_plus_E", "4-predictor + DWI + CTP", "post")]
    yy = np.arange(len(rows))[::-1]
    for yi, (m, lab, ph) in zip(yy, rows):
        r = a.loc[m]; col = S[0] if ph == "pre" else S[2]
        axs[1].hlines(yi, r.auc_lo, r.auc_hi, color=col, lw=2)
        axs[1].plot(r.auc, yi, "o", color=col, ms=6, mec="white", mew=1.2)
        axs[1].text(0.995, yi, f"{r.auc:.3f}", fontsize=7, color=INK2, va="center", ha="right")
    axs[1].set_yticks(yy); axs[1].set_yticklabels([r[1] for r in rows], fontsize=7.5)
    axs[1].set_xlim(0.55, 1.0); axs[1].set_xlabel("AUC (95% CI)"); axs[1].grid(axis="y", visible=False)
    axs[1].set_title("b  Full cohort (N = 129)", loc="left", fontsize=9)
    axs[1].legend(handles=[Line2D([], [], color=S[0], marker="o", lw=2, label="pre-treatment"),
                           Line2D([], [], color=S[2], marker="o", lw=2, label="after follow-up MRI")],
                  loc="upper center", bbox_to_anchor=(0.35, -0.2), ncol=2, fontsize=7.5)
    fig.tight_layout()
    save(fig, "Fig9_timeline")


if __name__ == "__main__":
    holm(); fig9()
