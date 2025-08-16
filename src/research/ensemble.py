import numpy as np, pandas as pd
from ..backtest.engine import compute
from ..backtest.metrics import sharpe, max_drawdown

def objective(pnl, equity):
    return sharpe(pnl) + max_drawdown(equity)

def ensemble_weights(df, signals: dict, window: int = 300):
    scores = {}
    for name, sig in signals.items():
        ret, pos, pnl, eq = compute(df.iloc[-window:], sig.iloc[-window:])
        s = objective(pnl, eq)
        scores[name] = s
    keys = list(scores.keys())
    arr = np.array([scores[k] for k in keys], dtype=float)
    arr = arr - np.nanmin(arr)
    arr = np.exp(arr) + 1e-9
    w = arr / arr.sum()
    return pd.Series(w, index=keys)

def blended_signal(signals: dict, weights: pd.Series):
    df = pd.concat(signals.values(), axis=1).fillna(0.0)
    df.columns = list(signals.keys())
    pos = (df * weights.reindex(df.columns).fillna(0)).sum(axis=1)
    return pos.clip(-1,1).rename('signal')
