import pandas as pd
def atr_channel_signal(df: pd.DataFrame, length:int=14, mult:float=2.0):
    ema = df['close'].ewm(span=length, adjust=False).mean()
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift()).abs()
    lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl,hc,lc], axis=1).max(axis=1)
    atr = tr.ewm(span=length, adjust=False).mean()
    upper = ema + mult*atr; lower = ema - mult*atr
    return ((df['close']>upper).astype(int) - (df['close']<lower).astype(int)).rename('signal')
