"""Sensitivity: ordinal 90-day mRS (0-6). Ordinal c-index of OOF risk (seed-averaged) with
patient-bootstrap CIs, and proportional-odds model of mRS on the OOF logits of P1 and E (does CTP add
ordinal information beyond the clinical score?)."""
import numpy as np
import pandas as pd
from statsmodels.miscmodels.ordinal_model import OrderedModel
from scipy import stats
from config import OOF, TAB, BOOT_SEED
from stats_utils import ordinal_c

pp = pd.read_csv(OOF / "pooled_probabilities.csv")
mrs = pp.mrs90.values.astype(int)
models = ["P1_clin_GBM", "F_late_P1_E", "E_CTP_all", "B_CBV", "D_Tmax", "T_thresholds", "SPAN100", "THRIVE", "F_EN_clin_CTP"]
rng = np.random.default_rng(BOOT_SEED)
B = [rng.integers(0, len(pp), len(pp)) for _ in range(1000)]
rows = []
base = {m: np.array([ordinal_c(mrs[b], pp[m].values[b]) for b in B]) for m in models}
for m in models:
    d = base[m] - base["P1_clin_GBM"]
    rows.append({"model": m, "ordinal_c": ordinal_c(mrs, pp[m].values), "lo": np.percentile(base[m], 2.5),
                 "hi": np.percentile(base[m], 97.5), "delta_vs_P1": ordinal_c(mrs, pp[m].values) - ordinal_c(mrs, pp["P1_clin_GBM"].values),
                 "delta_lo": np.percentile(d, 2.5), "delta_hi": np.percentile(d, 97.5)})
out = pd.DataFrame(rows)
lg = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
X1 = pd.DataFrame({"lp_P1": lg(pp.P1_clin_GBM)})
X2 = X1.assign(lp_E=lg(pp.E_CTP_all))
m1 = OrderedModel(mrs, X1, distr="logit").fit(method="bfgs", disp=False)
m2 = OrderedModel(mrs, X2, distr="logit").fit(method="bfgs", disp=False)
lr = 2 * (m2.llf - m1.llf)
po = {"LR_chi2_add_CTP_to_P1": lr, "p": stats.chi2.sf(lr, 1), "OR_per_unit_lp_E": float(np.exp(m2.params["lp_E"])),
      "OR_lo": float(np.exp(m2.conf_int().loc["lp_E", 0])), "OR_hi": float(np.exp(m2.conf_int().loc["lp_E", 1]))}
import statsmodels.api as sm
yb = pp.y.values
b1 = sm.Logit(yb, sm.add_constant(X1)).fit(disp=False); b2 = sm.Logit(yb, sm.add_constant(X2)).fit(disp=False)
lrb = 2 * (b2.llf - b1.llf)
po.update({"binary_LR_chi2_add_CTP_to_P1": lrb, "binary_p": stats.chi2.sf(lrb, 1),
           "binary_OR_lp_E": float(np.exp(b2.params["lp_E"])), "binary_OR_lo": float(np.exp(b2.conf_int().loc["lp_E", 0])),
           "binary_OR_hi": float(np.exp(b2.conf_int().loc["lp_E", 1]))})
out.to_csv(TAB / "ordinal_c_index.csv", index=False)
pd.Series(po).to_csv(TAB / "ordinal_proportional_odds.csv")
print(out.round(3).to_string(index=False)); print(pd.Series(po).round(4))
