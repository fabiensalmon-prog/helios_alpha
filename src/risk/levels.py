import pandas as pd, numpy as np
def atr(df: pd.DataFrame, length: int = 14):
    hl = df['high'] - df['low']; hc = (df['high'] - df['close'].shift()).abs(); lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl,hc,lc], axis=1).max(axis=1)
    return tr.ewm(span=length, adjust=False).mean()

def adaptive_levels(df: pd.DataFrame, direction: int, atr_mult_sl=2.5, atr_mult_tp=3.8, trail_start_R=1.0, trail_atr_mult=2.0):
    if direction == 0 or len(df)<2: return None
    a = float(atr(df, 14).iloc[-1]); price = float(df['close'].iloc[-1])
    if direction>0: sl = price - atr_mult_sl*a; tp = price + atr_mult_tp*a
    else: sl = price + atr_mult_sl*a; tp = price - atr_mult_tp*a
    return {'entry': price, 'sl': sl, 'tp': tp, 'atr': a, 'trail_start_R': trail_start_R, 'trail_atr_mult': trail_atr_mult}

def size_fixed_pct(account_equity: float, entry: float, stop: float, risk_pct: float):
    risk_amt = account_equity*(risk_pct/100.0); per_unit_loss = abs(entry-stop)
    return 0.0 if per_unit_loss<=0 else risk_amt/per_unit_loss

def size_fixed_usd(risk_usd: float, entry: float, stop: float):
    per_unit_loss = abs(entry-stop)
    return 0.0 if per_unit_loss<=0 else risk_usd/per_unit_loss

def size_kelly_fraction(p_win: float, win_mult: float, loss_mult: float, cap_pct: float, account_equity: float, entry: float, stop: float):
    b = max(win_mult, 1e-6); p = min(max(p_win, 0.0), 1.0); q = 1-p
    f_star = (b*p - q)/b
    f_star = max(min(f_star, cap_pct/100.0), 0.0)
    risk_amt = account_equity * f_star
    per_unit_loss = abs(entry-stop)
    return 0.0 if per_unit_loss<=0 else risk_amt/per_unit_loss
