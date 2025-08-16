import pandas as pd
def compute(df, signal, fee_bps=2.5, slippage_bps=1.0):
    ret = df['close'].pct_change().fillna(0.0)
    pos = signal.shift().fillna(0.0).clip(-1,1)
    cost = (pos.diff().abs().fillna(0.0)) * (fee_bps+slippage_bps)/10000.0
    pnl = pos*ret - cost
    equity = (1+pnl).cumprod()
    return ret, pos, pnl, equity
def backtest(df, signal, initial_cash=10000, fee_bps=2.5, slippage_bps=1.0):
    ret, pos, pnl, eq = compute(df, signal, fee_bps, slippage_bps)
    return {'ret': ret, 'pos': pos, 'pnl': pnl, 'equity': initial_cash*eq}
