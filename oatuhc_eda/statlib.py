"""Small statistics helpers shared by the OAUTHC EDA stages.

Only NumPy/SciPy are available in the pinned environment (no statsmodels, no
scikit-learn), so the few estimators the report needs are implemented here:
Wilson intervals, bootstrap intervals, rank effect sizes, Cramer's V, an
intraclass correlation for paired ears, a k-means with silhouette selection and
a local-linear smoother.

Every function returns plain Python floats so the results can be JSON-dumped.
"""
from __future__ import annotations

import numpy as np
from scipy import stats


# ---------------------------------------------------------------- intervals
def wilson(k, n, z=1.959964):
    """Wilson score interval for a proportion."""
    k, n = float(k), float(n)
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (float(max(0.0, centre - half)), float(min(1.0, centre + half)))


def boot_ci(values, stat=np.median, n=2000, seed=5, alpha=0.05):
    """Percentile bootstrap interval for a statistic of a 1-D sample."""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if len(v) < 5:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), (n, len(v)))
    draws = stat(v[idx], axis=1)
    return (float(np.percentile(draws, 100 * alpha / 2)),
            float(np.percentile(draws, 100 * (1 - alpha / 2))))


def boot_ci_diff(a, b, stat=np.median, n=2000, seed=5):
    """Bootstrap interval for stat(a) - stat(b)."""
    a = np.asarray(a, float); a = a[np.isfinite(a)]
    b = np.asarray(b, float); b = b[np.isfinite(b)]
    rng = np.random.default_rng(seed)
    da = stat(a[rng.integers(0, len(a), (n, len(a)))], axis=1)
    db = stat(b[rng.integers(0, len(b), (n, len(b)))], axis=1)
    d = da - db
    return (float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)))


def boot_spearman(x, y, n=2000, seed=5):
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    rng = np.random.default_rng(seed)
    out = np.empty(n)
    for i in range(n):
        k = rng.integers(0, len(x), len(x))
        out[i] = stats.spearmanr(x[k], y[k]).statistic
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


# ---------------------------------------------------------------- summaries
def desc(v):
    """Median, quartiles, range and mean for a continuous variable."""
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return {}
    return {"n": int(len(v)), "median": float(np.median(v)),
            "q1": float(np.percentile(v, 25)), "q3": float(np.percentile(v, 75)),
            "min": float(v.min()), "max": float(v.max()),
            "mean": float(v.mean()), "sd": float(v.std(ddof=1)) if len(v) > 1 else 0.0}


# ---------------------------------------------------------------- tests
def mannwhitney(a, b):
    """Mann-Whitney U with rank-biserial effect size and a median-difference CI."""
    a = np.asarray(a, float); a = a[np.isfinite(a)]
    b = np.asarray(b, float); b = b[np.isfinite(b)]
    res = stats.mannwhitneyu(a, b, alternative="two-sided")
    n1, n2 = len(a), len(b)
    # rank-biserial from U for group a
    rb = 2 * res.statistic / (n1 * n2) - 1
    lo, hi = boot_ci_diff(a, b)
    return {"test": "Mann-Whitney U", "U": float(res.statistic), "p": float(res.pvalue),
            "rank_biserial": float(rb), "median_a": float(np.median(a)),
            "median_b": float(np.median(b)), "diff": float(np.median(a) - np.median(b)),
            "diff_ci": [lo, hi], "n_a": n1, "n_b": n2}


def kruskal(groups, labels=None):
    """Kruskal-Wallis with epsilon-squared and a bootstrap CI for the largest gap."""
    groups = [np.asarray(g, float) for g in groups]
    groups = [g[np.isfinite(g)] for g in groups if len(g) > 1]
    h = stats.kruskal(*groups)
    n = sum(len(g) for g in groups)
    k = len(groups)
    eps2 = (h.statistic - k + 1) / (n - k) if n > k else float("nan")
    med = [float(np.median(g)) for g in groups]
    return {"test": "Kruskal-Wallis", "H": float(h.statistic), "df": k - 1,
            "p": float(h.pvalue), "epsilon_squared": float(eps2),
            "medians": med, "n_groups": [len(g) for g in groups],
            "labels": labels}


def chisq(table):
    """Pearson chi-square with Cramer's V (and Fisher's exact for 2x2)."""
    t = np.asarray(table, float)
    t = t[t.sum(axis=1) > 0][:, t.sum(axis=0) > 0]
    if t.shape[0] < 2 or t.shape[1] < 2:
        return {"test": "none", "p": float("nan")}
    c = stats.chi2_contingency(t, correction=False)
    n = t.sum()
    v = np.sqrt(c.statistic / (n * (min(t.shape) - 1)))
    out = {"test": "Pearson chi-square", "chi2": float(c.statistic),
           "df": int(c.dof), "p": float(c.pvalue), "cramers_v": float(v), "n": int(n)}
    if t.shape == (2, 2):
        out["fisher_p"] = float(stats.fisher_exact(t).pvalue)
    return out


def ols(x, y):
    """Slope, intercept, slope CI and R^2 for a simple linear fit."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    r = stats.linregress(x, y)
    return {"slope": float(r.slope), "intercept": float(r.intercept),
            "slope_ci": [float(r.slope - 1.96 * r.stderr), float(r.slope + 1.96 * r.stderr)],
            "r": float(r.rvalue), "p": float(r.pvalue), "r2": float(r.rvalue ** 2),
            "n": int(len(x))}


def icc1(groups):
    """One-way random-effects ICC(1) for pairs within patients.

    Used to quantify how much of the variance in a measure sits between
    patients rather than between ears, i.e. the design effect for any
    ear-level proportion. `groups` is a list of arrays, one per patient.
    """
    groups = [np.asarray(g, float) for g in groups if len(g) > 1]
    k = np.array([len(g) for g in groups], float)
    n = k.sum()
    grand = np.concatenate(groups).mean()
    msb = sum(len(g) * (g.mean() - grand) ** 2 for g in groups) / (len(groups) - 1)
    msw = sum(((g - g.mean()) ** 2).sum() for g in groups) / (n - len(groups))
    k0 = (n - (k ** 2).sum() / n) / (len(groups) - 1)
    icc = (msb - msw) / (msb + (k0 - 1) * msw)
    return float(icc)


# ---------------------------------------------------------------- clustering
def kmeans(X, k, seed=3, iters=300):
    rng = np.random.default_rng(seed)
    # k-means++ seeding
    centres = [X[rng.integers(0, len(X))]]
    for _ in range(1, k):
        d = np.min(((X[:, None, :] - np.array(centres)[None]) ** 2).sum(-1), axis=1)
        centres.append(X[rng.choice(len(X), p=d / d.sum())])
    C = np.array(centres, float)
    lab = np.zeros(len(X), int)
    for _ in range(iters):
        dist = ((X[:, None, :] - C[None]) ** 2).sum(-1)
        new = dist.argmin(1)
        if (new == lab).all():
            break
        lab = new
        for j in range(k):
            if (lab == j).any():
                C[j] = X[lab == j].mean(0)
    return C, lab


def silhouette(X, lab):
    d = np.sqrt(((X[:, None, :] - X[None]) ** 2).sum(-1))
    s = np.zeros(len(X))
    for i in range(len(X)):
        same = (lab == lab[i]); same[i] = False
        if same.sum() == 0:
            continue
        a = d[i, same].mean()
        b = min(d[i, lab == j].mean() for j in np.unique(lab) if j != lab[i])
        s[i] = (b - a) / max(a, b)
    return float(s.mean())


# ---------------------------------------------------------------- smoothing
def lowess(x, y, frac=0.6, grid=60):
    """Tricube local-linear smoother on a grid (Cleveland's lowess, no package)."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    order = np.argsort(x)
    x, y = x[order], y[order]
    xs = np.linspace(x.min(), x.max(), grid)
    ys = np.empty(grid)
    r = max(2, int(np.ceil(frac * len(x))))
    for i, x0 in enumerate(xs):
        d = np.abs(x - x0)
        h = np.partition(d, min(r - 1, len(d) - 1))[min(r - 1, len(d) - 1)]
        h = max(h, 1e-9)
        w = np.clip(1 - (d / h) ** 3, 0, None) ** 3
        W = w.sum()
        if W <= 0:
            ys[i] = np.interp(x0, x, y); continue
        xb = (w * x).sum() / W; yb = (w * y).sum() / W
        den = (w * (x - xb) ** 2).sum()
        beta = (w * (x - xb) * (y - yb)).sum() / den if den > 0 else 0.0
        ys[i] = yb + beta * (x0 - xb)
    return xs, ys
