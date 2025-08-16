import pandas as pd
def kama(series: pd.Series, er_len=10, fast=2, slow=30):
    change = series.diff(er_len).abs()
    vol = series.diff().abs().rolling(er_len).sum()
    er = change / (vol + 1e-9)
    sc = (er*(2/(fast+1) - 2/(slow+1)) + 2/(slow+1))**2
    out = [series.iloc[0]]
    for i in range(1, len(series)):
        out.append(out[-1] + sc.iloc[i]*(series.iloc[i]-out[-1]))
    return pd.Series(out, index=series.index)
def kama_trend_signal(df: pd.DataFrame, er_len:int=10, fast:int=2, slow:int=30):
    k = kama(df['close'], er_len, fast, slow)
    return ((df['close']>k).astype(int) - (df['close']<k).astype(int)).rename('signal')
