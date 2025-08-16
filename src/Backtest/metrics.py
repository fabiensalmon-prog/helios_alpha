import numpy as np, pandas as pd
def sharpe(pnl: pd.Series, periods_per_year=365*24):
    s = pnl.std(); return 0.0 if s==0 or np.isnan(s) else float(pnl.mean()/s * np.sqrt(periods_per_year))
def sortino(pnl: pd.Series, periods_per_year=365*24):
    d = pnl[pnl<0].std(); return 0.0 if d==0 or np.isnan(d) else float(pnl.mean()/d * np.sqrt(periods_per_year))
def max_drawdown(equity: pd.Series):
    peak = equity.cummax(); dd = equity/peak - 1; return float(dd.min())
def calmar(equity: pd.Series, periods_per_year=365*24):
    if len(equity)<2: return 0.0
    years = len(equity)/periods_per_year
    CAGR = (equity.iloc[-1]/max(equity.iloc[0],1e-9))**(1/years)-1 if years>0 else 0.0
    MDD = abs(max_drawdown(equity)) or 1e-9
    return float(CAGR/MDD)
