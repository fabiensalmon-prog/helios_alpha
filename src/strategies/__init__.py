from .ema_trend import ema_trend_signal
from .macd_momentum import macd_momentum_signal
from .donchian import donchian_breakout_signal
from .boll_mr import boll_mr_signal
from .kama_trend import kama_trend_signal
from .rsi_reversion import rsi_reversion_signal
from .ichimoku import ichimoku_signal
from .supertrend import supertrend_signal
from .atr_channel import atr_channel_signal

ALL = {
    'EMA Trend': ema_trend_signal,
    'MACD Momentum': macd_momentum_signal,
    'Donchian Breakout': donchian_breakout_signal,
    'Bollinger MR': boll_mr_signal,
    'KAMA Trend': kama_trend_signal,
    'RSI Mean-Reversion': rsi_reversion_signal,
    'Ichimoku': ichimoku_signal,
    'SuperTrend': supertrend_signal,
    'ATR Channel': atr_channel_signal
}
TREND_STRATS = ['EMA Trend','MACD Momentum','Donchian Breakout','KAMA Trend','Ichimoku','SuperTrend','ATR Channel']
MR_STRATS = ['RSI Mean-Reversion','Bollinger MR']
