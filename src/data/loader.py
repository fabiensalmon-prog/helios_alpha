import pandas as pd, os
from .ccxt_client import build_exchange

FALLBACK_EXCHANGES = ['okx','bybit','kraken','coinbase','kucoin']

def _map_symbol(exchange_id: str, symbol: str) -> str:
    if exchange_id=='kraken' and symbol.startswith('BTC/'):
        symbol = symbol.replace('BTC/','XBT/')
    if exchange_id=='coinbase' and symbol.endswith('/USDT'):
        symbol = symbol.replace('/USDT','/USDC')
    return symbol

def fetch_ohlcv(exchange_name: str, symbol: str, timeframe: str = '1h', limit: int = 3000):
    ex = build_exchange(exchange_name)
    sym = _map_symbol(exchange_name, symbol)
    if sym not in ex.markets: raise ValueError(f"{exchange_name}: symbole indisponible: {sym}")
    data = ex.fetch_ohlcv(sym, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(data, columns=['ts','open','high','low','close','volume'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms', utc=True)
    df.set_index('ts', inplace=True)
    return df

def cache_path(cache_dir: str, exchange: str, symbol: str, timeframe: str):
    os.makedirs(cache_dir, exist_ok=True)
    key = f"{exchange}_{symbol.replace('/','-')}_{timeframe}.parquet"
    return os.path.join(cache_dir, key)

def load_or_fetch(exchange: str, symbol: str, timeframe: str, cache_dir='app_cache', limit=3000, refresh=False):
    try_order = [exchange] + [e for e in FALLBACK_EXCHANGES if e!=exchange]
    last_err = None
    for ex_id in try_order:
        p = cache_path(cache_dir, ex_id, symbol, timeframe)
        if os.path.exists(p) and not refresh: return pd.read_parquet(p)
        try:
            df = fetch_ohlcv(ex_id, symbol, timeframe, limit)
            df.to_parquet(p); return df
        except Exception as e:
            last_err = e; continue
    raise RuntimeError(f"Aucun exchange dispo pour {symbol} {timeframe}. Dernière erreur: {last_err}")

def fetch_last_price(exchange_name: str, symbol: str):
    ex = build_exchange(exchange_name)
    sym = _map_symbol(exchange_name, symbol)
    t = ex.fetch_ticker(sym)
    return float(t.get('last') or t.get('close') or 0.0)
