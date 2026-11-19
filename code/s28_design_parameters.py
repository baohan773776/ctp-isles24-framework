"""Module M5 of the framework: design parameters for a definitive study.

1. Sample size to detect a target delta AUC with 80% power (two-sided alpha 0.05), from the paired-bootstrap SE
   of each observed increment, assuming SE proportional to 1/sqrt(n) and the observed event rate.
2. Riley et al. minimum sample size for developing a new model with p candidate parameters (criterion i,
   shrinkage 0.9, and criterion iii, precise intercept), at the anticipated AUC.
3. Go / no-go table: one row per research direction, numbers read from the result tables; the decision column is
   a PROPOSAL for future work (not a prespecified progression criterion).
Outputs: tables/design_sample_size.csv, tables/design_riley.csv, tables/go_nogo.csv
"""
import numpy as np
import pandas as pd
from config import TAB, N_BOOT, BOOT_SEED
from s05_evaluate import load, seed_auc

PAIRS = [("_all", "F_late_P1_E", "P1_clin_GBM", "Pre-treatment CTP added to clinical GBM (full cohort)"),
         ("_all", "R1_DWI", "R1_clin_LR4", "Follow-up infarct volume added to admission model (full cohort)"),
         ("_all", "P1_plus_DWI", "P1_clin_GBM", "Follow-up infarct volume added to clinical GBM (full cohort)"),
         ("_munich_timeline", "R1_N24", "R1_clin_LR4", "24-h NIHSS added to admission model (Munich)"),
         ("_munich_timeline", "R1_N24_DWI", "R1_clin_LR4", "24-h NIHSS + infarct volume vs admission (Munich)")]
TARGETS = (0.03, 0.05, 0.08)


def sample_size():
    rows, cache = [], {}
    for tag, new, ref, lab in PAIRS:
        if tag not in cache:
            ids, y, P = load(tag)
            rng = np.random.default_rng(BOOT_SEED); n = len(y); boots = []
            while len(boots) < N_BOOT:
                b = rng.integers(0, n, n)
                if 0 < y[b].sum() < n:
                    boots.append(b)
            cache[tag] = (y, P, boots)
        y, P, boots = cache[tag]
        n, prev = len(y), y.mean()
        d = seed_auc(y, P[new]) - seed_auc(y, P[ref])
        se = np.std([seed_auc(y, P[new], b) - seed_auc(y, P[ref], b) for b in boots], ddof=1)
        r = {"comparison": lab, "n_observed": n, "events_observed": int(y.sum()), "delta_observed": d, "se_boot": se}
        for t in TARGETS + (abs(d),):
            key = "observed" if t == abs(d) else f"{t:.2f}"
            nn = int(np.ceil(n * (2.80 * se / t) ** 2)) if t > 0 else np.nan
            r[f"n_for_delta_{key}"] = nn
            r[f"events_for_delta_{key}"] = int(np.ceil(nn * prev)) if t > 0 else np.nan
        rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "design_sample_size.csv", index=False)
    print(out.round(3).to_string(index=False))
    return out


def riley_table():
    rr = pd.read_csv(TAB / "sample_size_riley.csv")
    rows = []
    for _, r in rr.iterrows():
        k = (0.9 - 1) * np.log(1 - r.anticipated_R2cs / 0.9)   # criterion (i): n = p / k
        for p in (4, 6, 10, 20):
            n1 = p / k
            n = int(np.ceil(max(n1, r.n_required_intercept_precision)))
            rows.append({"anticipated_auc": r.anticipated_auc, "parameters": p, "n_criterion_i": int(np.ceil(n1)),
                         "n_criterion_iii": int(np.ceil(r.n_required_intercept_precision)), "n_minimum": n,
                         "events_minimum": int(np.ceil(n * r.prevalence))})
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "design_riley.csv", index=False)
    print(out.to_string(index=False))


def go_nogo(ss):
    comp = pd.read_csv(TAB / "paired_auc_comparisons_all.csv")
    prec = pd.read_csv(TAB / "precision_equivalence.csv").set_index("new")
    tl = pd.read_csv(TAB / "timeline_paired.csv"); ll = pd.read_csv(TAB / "location_lvo_paired.csv")
    sub = pd.read_csv(TAB / "subgroup_incremental_value.csv")
    holm = pd.read_csv(TAB / "round4_primary_holm.csv")
    perf = pd.read_csv(TAB / "performance_all_models_all.csv").set_index("model")

    def c(new, ref):
        r = comp[(comp.new == new) & (comp.reference == ref)].iloc[0]
        return f"{r.delta_auc:+.3f} ({r.ci_lo:+.3f} to {r.ci_hi:+.3f})"

    def t(df, s, new, ref):
        r = df[(df.set == s) & (df.new == new) & (df.reference == ref)].iloc[0]
        return f"{r.delta_auc:+.3f} ({r.ci_lo:+.3f} to {r.ci_hi:+.3f})"

    cmix = pd.read_csv(TAB / "site_case_mix.csv", index_col=0)
    simp = pd.read_csv(TAB / "site_imputation.csv").set_index("variable")
    lab_imp = min(simp.loc[v, "pct_imputed_Zurich"] for v in ["CRP", "Leucocytes", "INR"])
    nih = sub[sub.subgroup == "NIHSS >= 10"]
    nih_y = nih[nih.level.str.endswith("yes")].iloc[0]
    n_ctp = int(ss.iloc[0]["n_for_delta_0.05"])
    rows = [
        ("Pre-treatment CTP features (relative, native units)", f"ΔAUC {c('F_late_P1_E', 'P1_clin_GBM')}; P(ΔAUC > 0.05) = {prec.loc['F_late_P1_E', 'post_p_gt0.05']:.2f}",
         f"No-go for general post-thrombectomy prognosis; a definitive test needs ≈{n_ctp} patients"),
        ("Classical CTP thresholds and absolute volumes (mL)", f"AUC {perf.loc['T_thresholds', 'auc_seed_mean']:.2f} and {perf.loc['V_volumes', 'auc_seed_mean']:.2f}; volume increment {c('F_late_P1_V', 'P1_clin_GBM')}, equivalence within ±0.05 shown",
         "No-go"),
        ("Location of hypoperfusion (atlas)", f"ΔAUC {t(ll, 'H1: full cohort', 'F_loc', 'P1_clin_GBM')}",
         "No-go"),
        ("CTP in severe strokes (NIHSS ≥ 10)", f"ΔAUC {nih_y.delta:+.3f} ({nih_y.ci_lo:+.3f} to {nih_y.ci_hi:+.3f}); interaction P = {nih_y.p_interaction:.3f} (exploratory)",
         "Conditional: test only as a prespecified subgroup in an external cohort"),
        ("CBV / collateral signal", f"Best single channel, AUC {perf.loc['B_CBV', 'auc_seed_mean']:.2f}",
         "Conditional: candidate collateral marker, not a stand-alone prognostic model"),
        ("24-h NIHSS", f"ΔAUC {t(tl, 'B: Munich', 'R1_N24', 'R1_clin_LR4')} (Munich)", "Go: collect in all centres"),
        ("Follow-up DWI infarct volume", f"ΔAUC {t(tl, 'A: full cohort', 'R1_DWI', 'R1_clin_LR4')}; Holm P = {holm[holm.role.str.contains('H3')].p_holm.iloc[0]:.3f}",
         "Go: primary candidate for an updated (post-treatment) model"),
        ("Follow-up infarct location", f"ΔAUC {t(ll, 'H1: full cohort', 'R1_DWI_Loc', 'R1_DWI')}; not robust to registration quality",
         "Conditional: requires non-linear registration and larger n"),
        ("Pooled ISLES'24 without centre labels",
         f"Outcome rate {cmix.loc['Munich', 'poor_pct']:.0f}% vs {cmix.loc['Zurich', 'poor_pct']:.0f}%; release imputation "
         f"≥{lab_imp:.0f}% of laboratory values in one centre",
         "Required: centre-aware evaluation and complete laboratory data"),
    ]
    out = pd.DataFrame(rows, columns=["Direction", "Estimate (95% CI)", "Proposed decision for a definitive study"])
    out.to_csv(TAB / "go_nogo.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    ss = sample_size(); riley_table(); go_nogo(ss)
