import pandas as pd
from sklearn.cluster import KMeans

def kmeans_regime(df: pd.DataFrame, n_clusters: int = 3, lookback: int = 400):
    X = pd.DataFrame({
        'ret': df['close'].pct_change().rolling(5).mean(),
        'vol': df['close'].pct_change().rolling(20).std(),
        'trend': df['close'].pct_change().rolling(50).mean()
    }).dropna().iloc[-lookback:]
    if len(X)<20:
        return pd.Series('neutral', index=df.index)
    km = KMeans(n_clusters=n_clusters, n_init=5, random_state=42)
    labels = km.fit_predict(X)
    X2 = X.copy(); X2['cluster']=labels
    stats = X2.groupby('cluster').agg({'trend':'mean','vol':'mean'})
    up = stats['trend'].idxmax(); down = stats['trend'].idxmin(); highv = stats['vol'].idxmax()
    mapping = {up:'up', down:'down'}
    for c in range(n_clusters):
        if c not in mapping:
            mapping[c] = 'high_vol' if c==highv else 'neutral'
    names = [mapping[l] for l in labels]
    reg = pd.Series('neutral', index=X.index); reg[:] = names
    reg = reg.reindex(df.index).fillna(method='ffill').fillna('neutral')
    return reg
