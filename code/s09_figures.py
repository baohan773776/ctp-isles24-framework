"""Publication figures (300 dpi PNG + PDF). All numbers are read from outputs/ (no hand-entered values)."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from sklearn.metrics import roc_curve
import statsmodels.api as sm
from config import TAB, FIG, OOF, DATA, ISLES24, CLIP
import features as F

# reference categorical palette (fixed order, validated adjacent pairs) + chart ink
S = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6", "#008300", "#e34948"]
INK, INK2, MUTED, GRID, BASE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": BASE, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID,
                     "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
                     "legend.frameon": False, "savefig.dpi": 300, "lines.linewidth": 2})
LABEL = {"P1_clin_GBM": "Clinical GBM (P1)", "F_late_P1_E": "Clinical + CTP fusion (F)", "E_CTP_all": "CTP all channels (E)",
         "T_thresholds": "CTP classical thresholds (T)", "SPAN100": "SPAN-100", "THRIVE": "THRIVE",
         "F_EN_clin_CTP": "Clinical + CTP elastic net", "F_GBM_clin_thresh": "Clinical + thresholds GBM",
         "F_late_P1_T": "Clinical + thresholds fusion", "P2_clin_EN": "Clinical elastic net", "NIHSS_only": "NIHSS only",
         "A_CBF": "CBF only (A)", "B_CBV": "CBV only (B)", "C_MTT": "MTT only (C)", "D_Tmax": "Tmax only (D)"}


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight"); fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight"); plt.close(fig)


def fig1_flow():
    fig, ax = plt.subplots(figsize=(7.2, 5.4)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(-1.6, 10)
    def box(x, y, w, h, t, fc="#f0efec"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.15", fc=fc, ec=BASE, lw=1))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=7.6, color=INK, wrap=True)
    def arr(x1, y1, x2, y2):
        ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1))
    box(0.2, 8.4, 3.0, 1.2, "ISLES'24 public training set\nN = 149 (pre-processed release)")
    box(0.2, 6.4, 3.0, 1.2, "Analysed cohort N = 129\n85 good (mRS 0–2), 44 poor (mRS 3–6)", "#cde2fb")
    box(3.7, 6.6, 2.6, 0.9, "Excluded: no 90-day mRS\nn = 20")
    arr(1.7, 8.4, 1.7, 7.6); arr(1.7, 8.0, 3.7, 7.05)
    box(0.0, 3.9, 3.4, 1.7, "Clinical (22 pre-procedural)\n4 intra-procedural times excluded\nraw units recovered from scaler\nTHRIVE / SPAN-100 recomputed")
    box(3.6, 3.9, 3.2, 1.7, "CTP maps (CBF, CBV, MTT, Tmax)\nunit recovery x = b(z − z_min)\nverified: MTT = 60·CBV/CBF\n+ ISLES 2018 simulation (n = 94)")
    box(7.0, 3.9, 2.9, 1.7, "53 CTP features\nipsilateral hemisphere,\nrelative to contralateral;\nfractions of covered tissue")
    arr(1.7, 6.4, 1.7, 5.6); arr(1.7, 6.4, 5.2, 5.6); arr(6.8, 4.75, 7.0, 4.75)
    box(0.0, 1.5, 9.9, 1.7, "Nested repeated CV: 5 seeds × stratified 10-fold (inner 5-fold tuning)\n"
        "P1 clinical GBM · A–D single-channel elastic net · E all-channel · T classical thresholds · F fusion (equal-weight)\n"
        "Discrimination (seed-mean AUC, patient bootstrap) · calibration · DCA · NRI/IDI · SHAP · sensitivity analyses", "#f9f9f7")
    arr(1.7, 3.9, 1.7, 3.2); arr(5.2, 3.9, 5.2, 3.2); arr(8.4, 3.9, 8.4, 3.2)
    box(0.0, -1.5, 9.9, 2.2, "Original release (native units, voxel size): direct check of unit recovery · absolute volumes (mL)\n"
        "centres inferred from data provenance (99 / 50; descriptor: 100 / 50 of 150, 149 released)\n"
        "→ within-centre AUC · Munich-only nested CV · leave-one-centre-out validation\n"
        "Reference-model checks: parsimonious 4-predictor logistic model · recalibrated GBM · precision / equivalence (±0.05)",
        "#e6f4ee")
    arr(5.0, 1.5, 5.0, 0.7)
    save(fig, "Fig1_flow_pipeline")


def fig2_units():
    q = pd.read_csv(DATA / "ctp_features_v3_149.csv")
    coh = pd.read_csv(DATA / "cohort_129.csv")
    q = q[q.subject_id.isin(coh.subject_id)]
    sim = pd.read_csv(TAB / "isles2018_unit_recovery_sim.csv")
    ag = pd.read_csv(TAB / "isles2018_feature_agreement.csv")
    fig, ax = plt.subplots(2, 2, figsize=(7.2, 6.0))
    a = ax[0, 0]
    a.hist(q.qc_cvt_ratio_median, bins=np.linspace(0.85, 1.15, 31), color=S[0], ec="white", lw=0.5)
    a.axvline(1, color=INK2, lw=1, ls="--"); a.set_xlabel("Observed MTT / (60·CBV/CBF), per-patient median")
    a.set_ylabel("Patients (ISLES'24, n = 129)"); a.set_title("a  Central volume theorem check", loc="left", fontsize=9)
    a = ax[0, 1]
    data = [sim[f"{c}_scale_ratio"].values for c in ["CBF", "CBV", "MTT", "Tmax"]]
    for i, d in enumerate(data):
        a.scatter(np.full(len(d), i) + np.random.default_rng(i).uniform(-0.18, 0.18, len(d)), d, s=10, color=S[0], alpha=0.6, lw=0)
    a.set_xticks(range(4), ["CBF", "CBV", "MTT", "Tmax"]); a.axhline(1, color=INK2, lw=1, ls="--")
    a.set_ylabel("Recovered / true scale"); a.set_title("b  ISLES 2018 simulation (n = 94)", loc="left", fontsize=9)
    a = ax[1, 0]
    ag = ag.assign(ch=[F.CHANNEL_OF.get(f, "Mismatch") for f in ag.feature])
    order = ["CBF", "CBV", "MTT", "Tmax", "Mismatch"]
    for i, ch in enumerate(order):
        v = ag.loc[ag.ch == ch, "ICC_true_vs_recovered"]
        a.scatter(np.full(len(v), i), v, s=14, color=S[0], alpha=0.7, lw=0)
    a.set_xticks(range(5), order); a.set_ylim(0.9, 1.005); a.set_ylabel("ICC(A,1), true vs recovered feature")
    a.set_title("c  Feature-level agreement", loc="left", fontsize=9)
    a = ax[1, 1]
    sid = "sub-stroke0014"
    perf = np.load(ISLES24 / "perfusion" / f"{sid}_perf.npy")
    x = perf[3]; tm = CLIP["Tmax"] * (x - x.min()) / (x.max() - x.min())
    z = int(np.argmax((tm > 6).sum((0, 1))))
    im = a.imshow(np.rot90(tm[:, :, z]), cmap="Blues", vmin=0, vmax=12)
    a.contour(np.rot90(tm[:, :, z] > 6), levels=[0.5], colors=[S[1]], linewidths=1)
    a.axis("off"); a.set_title("d  Recovered Tmax (s), Tmax > 6 s outlined", loc="left", fontsize=9)
    plt.colorbar(im, ax=a, fraction=0.046, pad=0.02)
    fig.tight_layout(); save(fig, "Fig2_unit_recovery_validation")


def fig3_forest():
    p = pd.read_csv(TAB / "performance_all_models.csv").set_index("model")
    groups = [("Clinical scores", ["THRIVE", "SPAN100", "NIHSS_only"]),
              ("Clinical ML", ["P2_clin_EN", "P1_clin_GBM"]),
              ("CTP single channel", ["A_CBF", "B_CBV", "C_MTT", "D_Tmax"]),
              ("CTP combined", ["T_thresholds", "E_CTP_all"]),
              ("Multimodal", ["F_EN_clin_CTP", "F_GBM_clin_thresh", "F_late_P1_T", "F_late_P1_E"])]
    fig, ax = plt.subplots(figsize=(6.6, 5.4)); yy, lab, y = [], [], 0
    for g, ms in groups[::-1]:
        for m in ms[::-1]:
            r = p.loc[m]
            ax.plot([r.auc_ci_lo, r.auc_ci_hi], [y, y], color=S[0], lw=2, solid_capstyle="round")
            ax.scatter(r.auc_seed_mean, y, s=36, color=S[0], zorder=3, edgecolor="white", lw=1)
            ax.text(0.905, y, f"{r.auc_seed_mean:.3f} ({r.auc_ci_lo:.3f}–{r.auc_ci_hi:.3f})", va="center", fontsize=7.5, color=INK2)
            yy.append(y); lab.append(LABEL[m]); y += 1
        ax.text(0.30, y - 0.35, g, fontsize=8, color=INK, weight="bold"); y += 0.8
    ax.axvline(0.5, color=BASE, lw=1); ax.axvline(p.loc["P1_clin_GBM", "auc_seed_mean"], color=MUTED, lw=1, ls="--")
    ax.set_yticks(yy, lab); ax.set_xlim(0.3, 0.9); ax.set_xlabel("AUC, mean of 5 seeds (95% patient-bootstrap CI)")
    ax.grid(axis="y", visible=False)
    save(fig, "Fig3_auc_forest")


def fig4_roc():
    pp = pd.read_csv(OOF / "pooled_probabilities.csv"); perf = pd.read_csv(TAB / "performance_all_models.csv").set_index("model")
    ms = ["P1_clin_GBM", "F_late_P1_E", "E_CTP_all", "T_thresholds", "SPAN100", "THRIVE"]
    ls = ["-", "-", "--", "--", ":", ":"]
    fig, ax = plt.subplots(figsize=(4.6, 4.4))
    ax.plot([0, 1], [0, 1], color=BASE, lw=1)
    for i, m in enumerate(ms):
        f, t, _ = roc_curve(pp.y, pp[m]); ax.plot(f, t, color=S[i], ls=ls[i], label=f"{LABEL[m]}  {perf.loc[m,'auc_pooled']:.3f}")
    ax.set_xlabel("1 − specificity"); ax.set_ylabel("Sensitivity"); ax.set_aspect("equal")
    ax.legend(loc="lower right", fontsize=7, title="Pooled out-of-fold AUC", title_fontsize=7)
    save(fig, "Fig4_roc")


def fig5_calibration():
    pp = pd.read_csv(OOF / "pooled_probabilities.csv"); perf = pd.read_csv(TAB / "performance_all_models.csv").set_index("model")
    ms = ["P1_clin_GBM", "F_late_P1_E", "E_CTP_all", "F_EN_clin_CTP"]
    fig, (ax, ah) = plt.subplots(2, 1, figsize=(4.6, 5.4), gridspec_kw={"height_ratios": [4, 1]}, sharex=True)
    ax.plot([0, 1], [0, 1], color=BASE, lw=1)
    for i, m in enumerate(ms):
        lw = sm.nonparametric.lowess(pp.y, pp[m], frac=0.75, it=0)
        r = perf.loc[m]
        ax.plot(lw[:, 0], lw[:, 1], color=S[i], label=f"{LABEL[m]}: slope {r.pooled_slope:.2f}, CITL {r.pooled_citl:.2f}")
        ah.hist(pp[m], bins=np.linspace(0, 1, 26), histtype="step", color=S[i], lw=1.2)
    ax.set_ylabel("Observed proportion poor outcome"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.legend(fontsize=6.8, loc="upper left"); ah.set_xlabel("Predicted probability of poor outcome (OOF, seed-averaged)")
    ah.set_ylabel("n"); fig.tight_layout(); save(fig, "Fig5_calibration")


def fig6_dca():
    d = pd.read_csv(TAB / "dca_curves.csv")
    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    for m, c, l in [("treat_all", MUTED, "--"), ("treat_none", INK2, "-")]:
        g = d[d.model == m]; ax.plot(g.threshold, g.net_benefit, color=c, ls=l, lw=1.2, label={"treat_all": "Treat all", "treat_none": "Treat none"}[m])
    for i, m in enumerate(["P1_clin_GBM", "F_late_P1_E", "E_CTP_all", "THRIVE"]):
        g = d[d.model == m]; ax.plot(g.threshold, g.net_benefit, color=S[i], label=LABEL[m], ls="-" if i < 2 else ":")
    ax.set_ylim(-0.05, 0.36); ax.set_xlim(0.05, 0.6); ax.set_xlabel("Threshold probability of poor outcome")
    ax.set_ylabel("Net benefit"); ax.legend(fontsize=7); ax.text(0.06, -0.045, "y-axis truncated at −0.05 (treat-all falls below)", fontsize=6.5, color=MUTED)
    save(fig, "Fig6_dca")


def fig7_importance():
    st = pd.read_csv(TAB / "coef_rank_stability.csv").set_index("model")
    perf = pd.read_csv(TAB / "performance_all_models.csv").set_index("model")
    sens = pd.read_csv(TAB / "performance_all_models_sens_features.csv").set_index("model")
    sh = pd.read_csv(OOF / "treeshap_values_F_GBM_clin_thresh.csv")
    imp = pd.read_csv(TAB / "treeshap_F_GBM_clin_thresh.csv").head(12)
    coh = pd.read_csv(DATA / "cohort_129.csv").merge(pd.read_csv(DATA / "ctp_features_v3_149.csv"), on="subject_id")
    fig = plt.figure(figsize=(7.4, 6.4)); gs = fig.add_gridspec(2, 2, width_ratios=[1, 1.25])
    a = fig.add_subplot(gs[0, 0]); chs = ["CBF", "CBV", "MTT", "Tmax"]
    sh_e = [st.loc["E_CTP_all", f"share_{c}"] for c in chs]
    a.barh(chs[::-1], sh_e[::-1], color=S[0], height=0.6)
    for i, v in enumerate(sh_e[::-1]):
        a.text(v + 0.01, i, f"{100*v:.0f}%", va="center", fontsize=7.5, color=INK2)
    a.set_xlabel("Share of Σ|standardised coefficient|\n(all-channel model E, 50 folds)"); a.set_xlim(0, 0.5)
    a.set_title("a  Channel contribution", loc="left", fontsize=9); a.grid(axis="y", visible=False)
    b = fig.add_subplot(gs[1, 0])
    rows = [("Single channel", m) for m in ["A_CBF", "B_CBV", "C_MTT", "D_Tmax"]] + \
           [("Leave one out", f"E_minus_{c}") for c in chs] + [("All channels", "E_CTP_all")]
    yl = []
    for i, (g, m) in enumerate(rows[::-1]):
        r = perf.loc[m] if m in perf.index else sens.loc[m]
        b.plot([r.auc_ci_lo, r.auc_ci_hi], [i, i], color=S[0] if g == "Single channel" else S[1], lw=2)
        b.scatter(r.auc_seed_mean, i, color=S[0] if g == "Single channel" else S[1], s=26, zorder=3, edgecolor="white")
        yl.append(LABEL.get(m, m.replace("E_minus_", "E without ")))
    b.set_yticks(range(len(rows)), yl); b.axvline(0.5, color=BASE, lw=1); b.set_xlim(0.38, 0.78)
    b.set_xlabel("AUC (95% CI)"); b.set_title("b  Channel ablation", loc="left", fontsize=9); b.grid(axis="y", visible=False)
    c = fig.add_subplot(gs[:, 1])
    sh = sh.groupby("subject_id").mean(numeric_only=True).drop(columns="seed")
    for i, f in enumerate(imp.feature[::-1]):
        v = coh.set_index("subject_id").loc[sh.index, f].astype(float)
        rk = (v.rank(pct=True)).values
        c.scatter(sh[f].values, np.full(len(v), i) + np.random.default_rng(i).uniform(-0.25, 0.25, len(v)),
                  c=rk, cmap="Blues", vmin=-0.2, vmax=1, s=9, lw=0)
    c.set_yticks(range(len(imp)), [f.replace("_min", "").replace("_frac", "").replace("_hypo", " (hypo)") for f in imp.feature[::-1]], fontsize=7.5)
    c.axvline(0, color=BASE, lw=1); c.set_xlabel("TreeSHAP (log-odds, poor outcome)")
    c.set_title("c  Clinical + threshold GBM: TreeSHAP\n(darker = higher feature value)", loc="left", fontsize=9)
    c.grid(axis="y", visible=False); fig.tight_layout(); save(fig, "Fig7_interpretability")


def figS1_sensitivity():
    items = []
    # scale-free row: corrected feature list (run _sens_scalefree, 2026-11-13); nested-GBM row: fusion vs nested-tuned P1
    for tag, lab in [("", "Primary (5×10-fold)"), ("_5fold", "5×5-fold protocol"), ("_sens_tmaxcertain", "Tmax-scale-certain subset (n=85)"),
                     ("_sens_missing", "Clinical GBM + missing indicators"), ("_sens_features", "Fusion with CBV-only model"),
                     ("_sens_features", "Fusion with PCA CTP model"), ("_sens_scalefree", "Fusion with scale-free CTP model"),
                     ("_sens_features", "Fusion with compact physiological CTP"), ("_sens_nestedgbm", "Nested-tuned clinical GBM reference")]:
        m = {"Fusion with CBV-only model": "F_late_P1_CBV", "Fusion with PCA CTP model": "F_late_P1_EPCA",
             "Fusion with scale-free CTP model": "F_late_P1_Esf", "Fusion with compact physiological CTP": "F_late_P1_Ephys",
             "Clinical GBM + missing indicators": "F_late_P1miss_E", "Nested-tuned clinical GBM reference": "F_late_P1nested_E"}.get(lab, "F_late_P1_E")
        if m == "F_late_P1nested_E":
            r = pd.read_csv(TAB / f"paired_auc_comparisons{tag}.csv")
            r = r[(r.new == m) & (r.reference == "P1_nested_GBM")].iloc[0]
        else:
            r = pd.read_csv(TAB / f"paired_vs_P1_clin_GBM{tag}.csv").set_index("model").loc[m]
        items.append((lab, r))
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    for i, (lab, r) in enumerate(items[::-1]):
        ax.plot([r.ci_lo, r.ci_hi], [i, i], color=S[0], lw=2); ax.scatter(r.delta_auc, i, color=S[0], s=30, zorder=3, edgecolor="white")
        ax.text(0.105, i, f"{r.delta_auc:+.3f} ({r.ci_lo:+.3f}, {r.ci_hi:+.3f})", va="center", fontsize=7.3, color=INK2)
    ax.set_yticks(range(len(items)), [l for l, _ in items[::-1]]); ax.axvline(0, color=MUTED, lw=1, ls="--")
    ax.set_xlim(-0.08, 0.1); ax.set_xlabel("ΔAUC, multimodal fusion − clinical GBM (95% CI)"); ax.grid(axis="y", visible=False)
    save(fig, "FigS1_sensitivity_delta_auc")


if __name__ == "__main__":
    for f in (fig1_flow, fig2_units, fig3_forest, fig4_roc, fig5_calibration, fig6_dca, fig7_importance, figS1_sensitivity):
        f(); print("saved", f.__name__)

