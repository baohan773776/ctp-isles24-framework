"""Statistical helpers: fast AUC, DeLong, calibration, DCA, NRI/IDI."""
import numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression
import statsmodels.api as sm


def auc_fast(y, p):
    y = np.asarray(y); p = np.asarray(p)
    n1 = y.sum(); n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return np.nan
    r = stats.rankdata(p)
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def delong(y, p1, p2=None):
    """DeLong AUC, SE (and paired difference test if p2 given)."""
    y = np.asarray(y).astype(bool)
    def comps(p):
        pos, neg = p[y], p[~y]
        v10 = np.array([(np.sum(x > neg) + 0.5 * np.sum(x == neg)) / len(neg) for x in pos])
        v01 = np.array([(np.sum(pos > x) + 0.5 * np.sum(pos == x)) / len(pos) for x in neg])
        return v10.mean(), v10, v01
    a1, v10a, v01a = comps(np.asarray(p1))
    if p2 is None:
        se = np.sqrt(v10a.var(ddof=1) / len(v10a) + v01a.var(ddof=1) / len(v01a))
        return a1, se
    a2, v10b, v01b = comps(np.asarray(p2))
    s10 = np.cov(np.vstack([v10a, v10b])); s01 = np.cov(np.vstack([v01a, v01b]))
    var = (s10[0, 0] + s10[1, 1] - 2 * s10[0, 1]) / len(v10a) + (s01[0, 0] + s01[1, 1] - 2 * s01[0, 1]) / len(v01a)
    z = (a1 - a2) / np.sqrt(var) if var > 0 else 0.0
    return a1 - a2, np.sqrt(var), 2 * stats.norm.sf(abs(z))


def calib(y, p, eps=1e-6):
    p = np.clip(p, eps, 1 - eps); lp = np.log(p / (1 - p))
    # slope: logit(y) ~ a + b*lp ; intercept (CITL): logit(y) ~ a + offset(lp)
    m_s = sm.GLM(y, sm.add_constant(lp), family=sm.families.Binomial()).fit()
    m_i = sm.GLM(y, np.ones_like(lp), family=sm.families.Binomial(), offset=lp).fit()
    lw = sm.nonparametric.lowess(y, p, frac=0.75, it=0, return_sorted=False)
    return {"slope": m_s.params[1], "slope_lo": m_s.conf_int()[1][0], "slope_hi": m_s.conf_int()[1][1],
            "citl": m_i.params[0], "citl_lo": m_i.conf_int()[0][0], "citl_hi": m_i.conf_int()[0][1],
            "brier": np.mean((p - y) ** 2), "ici": np.mean(np.abs(lw - p)), "e90": np.quantile(np.abs(lw - p), .9)}


def net_benefit(y, p, t):
    n = len(y); pos = p >= t
    tp = np.sum(pos & (y == 1)); fp = np.sum(pos & (y == 0))
    return tp / n - fp / n * t / (1 - t)


def nb_all(y, t):
    pi = np.mean(y)
    return pi - (1 - pi) * t / (1 - t)


def nri_idi(y, p_new, p_old, cuts=None):
    ev, ne = y == 1, y == 0
    if cuts is None:   # category-free
        up, dn = p_new > p_old, p_new < p_old
    else:
        cn, co = np.digitize(p_new, cuts), np.digitize(p_old, cuts)
        up, dn = cn > co, cn < co
    nri_e = up[ev].mean() - dn[ev].mean()
    nri_n = dn[ne].mean() - up[ne].mean()
    idi = (p_new[ev].mean() - p_old[ev].mean()) - (p_new[ne].mean() - p_old[ne].mean())
    return nri_e + nri_n, nri_e, nri_n, idi


def classif(y, p, t=0.5):
    pr = p >= t
    tp, fp = np.sum(pr & (y == 1)), np.sum(pr & (y == 0))
    fn, tn = np.sum(~pr & (y == 1)), np.sum(~pr & (y == 0))
    return {"TP": tp, "FP": fp, "FN": fn, "TN": tn, "sens": tp / (tp + fn), "spec": tn / (tn + fp),
            "ppv": tp / (tp + fp) if tp + fp else np.nan, "npv": tn / (tn + fn) if tn + fn else np.nan,
            "acc": (tp + tn) / len(y), "f1_poor": 2 * tp / (2 * tp + fp + fn)}


def pr_auc(y, p):
    from sklearn.metrics import average_precision_score
    return average_precision_score(y, p)


def ordinal_c(mrs, risk):
    """Harrell-type c-index for an ordinal outcome (pairs with different mRS)."""
    mrs = np.asarray(mrs); risk = np.asarray(risk)
    d = np.sign(mrs[:, None] - mrs[None, :]); r = np.sign(risk[:, None] - risk[None, :])
    mask = np.triu(d != 0, 1)
    conc = ((d == r) & (r != 0))[mask].sum(); ties = (r == 0)[mask].sum()
    return (conc + 0.5 * ties) / mask.sum()
