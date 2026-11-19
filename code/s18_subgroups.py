"""Prespecified subgroup analyses of the incremental value of CTP (F_late_P1_E vs P1_clin_GBM).

Within each subgroup: AUC of both models (mean of per-seed AUCs) and delta with a 2000-resample
patient-level bootstrap. Effect modification: likelihood-ratio test of the interaction between the
CTP score (logit of E_CTP_all OOF probability) and the subgroup indicator, in a logistic model that
also contains the clinical score (logit of P1 OOF probability) and the main effect of the subgroup.
Exploratory; no multiplicity adjustment (stated in the manuscript).
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from config import DATA, TAB, FIG, BOOT_SEED
from s05_evaluate import load, seed_auc

NEW, REF, CTP = "F_late_P1_E", "P1_clin_GBM", "E_CTP_all"
NB = 2000


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def subgroups(coh):
    g = {
        "Age >= 80 y": coh["Age"] >= 80,
        "NIHSS >= 10": coh["NIHSS at admission"] >= 10,
        "Premorbid mRS >= 1": coh["mRS premorbid"] >= 1,
        "LVO visible on CTA": coh["lvo_visible"],
        "Wake-up stroke": coh["Wake-up"] >= 0.5,
    }
    if "site" in coh:
        g["Zurich (inferred centre)"] = coh["site"] == "Zurich"
    if "core_ml" in coh and coh["core_ml"].notna().all():
        g["Core volume >= median"] = coh["core_ml"] >= coh["core_ml"].median()
        g["Tmax>6 s volume >= median"] = coh["tmax6_ml"] >= coh["tmax6_ml"].median()
    return g


def main():
    ids, y, P = load("_all")
    coh = pd.read_csv(DATA / "cohort_129.csv").set_index("subject_id").loc[ids]
    f = pd.read_csv(DATA / "ctp_features_v3_149.csv").set_index("subject_id").loc[ids]
    coh["lvo_visible"] = f["qc_lvo_side"].notna().values
    nf = DATA / "ctp_features_native_149.csv"
    if nf.exists():
        nat = pd.read_csv(nf).set_index("subject_id").reindex(ids)
        coh["core_ml"], coh["tmax6_ml"] = nat["core_ml"].values, nat["tmax6_ml"].values
    sf = DATA / "inferred_site.csv"
    if sf.exists():
        s = pd.read_csv(sf).set_index("subject_id").reindex(ids)
        coh["site"] = np.where(s.site_inferred.str.startswith("Zurich"), "Zurich", "Munich")
    lp1, lpe = logit(P[REF].mean(0)), logit(P[CTP].mean(0))
    rng = np.random.default_rng(BOOT_SEED)
    rows = []
    for name, mask in subgroups(coh).items():
        mask = np.asarray(mask, bool)
        for level, sel in ((f"{name}: yes", mask), (f"{name}: no", ~mask)):
            idx = np.nonzero(sel)[0]
            yy = y[idx]
            r = {"subgroup": name, "level": level, "n": len(idx), "events": int(yy.sum())}
            if yy.sum() < 5 or (len(yy) - yy.sum()) < 5:
                rows.append(r); continue
            a_new, a_ref = seed_auc(y, P[NEW], idx), seed_auc(y, P[REF], idx)
            db = []
            while len(db) < NB:
                b = rng.choice(idx, len(idx))
                if 0 < y[b].sum() < len(b):
                    db.append(seed_auc(y, P[NEW], b) - seed_auc(y, P[REF], b))
            r.update({"auc_ref": a_ref, "auc_new": a_new, "delta": a_new - a_ref,
                      "ci_lo": np.percentile(db, 2.5), "ci_hi": np.percentile(db, 97.5)})
            rows.append(r)
        g = mask.astype(float)
        X0 = sm.add_constant(np.c_[lp1, lpe, g])
        X1 = sm.add_constant(np.c_[lp1, lpe, g, lpe * g])
        m0 = sm.GLM(y, X0, family=sm.families.Binomial()).fit()
        m1 = sm.GLM(y, X1, family=sm.families.Binomial()).fit()
        lr = 2 * (m1.llf - m0.llf)
        rows[-1]["p_interaction"] = rows[-2]["p_interaction"] = stats.chi2.sf(lr, 1)
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "subgroup_incremental_value.csv", index=False)
    print(out.round(3).to_string(index=False))
    forest(out)


def forest(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = out.dropna(subset=["delta"]).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7.2, 0.36 * len(d) + 1.2))
    yy = np.arange(len(d))[::-1]
    ax.axvline(0, color="#8a8a8a", lw=1, zorder=0)
    ax.hlines(yy, d.ci_lo, d.ci_hi, color="#2a78d6", lw=2)
    ax.plot(d.delta, yy, "o", color="#2a78d6", ms=7, mec="white", mew=1.5)
    ax.set_yticks(yy)
    ax.set_yticklabels([f"{l}  (n={n}, {e} poor)" for l, n, e in zip(d.level, d.n, d.events)], fontsize=8)
    for yi, (_, r) in zip(yy, d.iterrows()):
        if "yes" in r.level and pd.notna(r.get("p_interaction")):
            ax.text(1.01, yi - 0.5, f"p-int {r.p_interaction:.2f}", transform=ax.get_yaxis_transform(),
                    fontsize=7.5, color="#555555", va="center")
    ax.set_xlabel("ΔAUC, clinical + CTP (late fusion) minus clinical GBM (95% bootstrap CI)", fontsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", color="#e6e6e6", lw=0.8)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"FigS2_subgroups.{ext}", dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
