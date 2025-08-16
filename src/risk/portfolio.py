import numpy as np, pandas as pd
def inverse_vol_weights(returns: pd.DataFrame, min_w: float = 0.0):
    vol = returns.std()
    inv = 1.0/(vol.replace(0, np.nan))
    w = inv / inv.sum()
    w = w.fillna(0.0)
    if min_w>0:
        w = np.maximum(w, min_w); w = w/ w.sum()
    return w

def min_var_weights(returns: pd.DataFrame, l2: float = 1e-3):
    cov = returns.cov() + l2*np.eye(len(returns.columns))
    ones = np.ones(len(returns.columns))
    try:
        inv = np.linalg.inv(cov.values)
        w = inv.dot(ones) / (ones.T.dot(inv).dot(ones))
        return pd.Series(w, index=returns.columns)
    except Exception:
        return inverse_vol_weights(returns)

def cap_gross_exposure(weights: pd.Series, max_gross_pct: float):
    gross = float(weights.abs().sum())
    if gross == 0: return weights
    cap = max_gross_pct/100.0
    if gross <= cap: return weights
    return weights * (cap / gross)
