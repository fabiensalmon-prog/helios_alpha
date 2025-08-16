import streamlit as st, yaml, os, requests, io, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from src.data.loader import load_or_fetch, fetch_last_price
from src.strategies import ALL, TREND_STRATS, MR_STRATS
from src.risk.levels import adaptive_levels, size_fixed_pct, size_fixed_usd, size_kelly_fraction
from src.risk.portfolio import inverse_vol_weights, min_var_weights, cap_gross_exposure
from src.backtest.engine import backtest
from src.backtest.metrics import sharpe, sortino, max_drawdown, calmar
from src.research.ensemble import ensemble_weights, blended_signal
from src.research.regime import kmeans_regime
from src.research.pdf_report import build_pdf
from src.journal.db import add_trade, list_trades, update_trade_result

st.set_page_config(page_title='HELIOS ALPHA — V7', page_icon='assets/logo.png', layout='centered')
brand = yaml.safe_load(open('configs/brand.yml'))
cfg = yaml.safe_load(open('configs/default.yml'))

col1, col2 = st.columns([1,5])
with col1: st.image(brand.get('logo_path','assets/logo.png'), width=64)
with col2:
    st.title(brand.get('app_name','HELIOS ALPHA — V7'))
    st.caption(brand.get('tagline','Ensemble + Regime Clustering + Portfolio Risk · Manual signals'))

with st.expander('Branding (Logo)'):
    f = st.file_uploader('Changer le logo', type=['png','jpg','jpeg'])
    if f:
        open(brand.get('logo_path','assets/logo.png'),'wb').write(f.read())
        st.success('Logo mis à jour. Recharge la page.')

with st.expander('Settings', expanded=False):
    exchange = st.selectbox('Exchange', ['okx','bybit','kraken','coinbase','kucoin','binance'], index=0)
    symbols = st.multiselect('Pairs', cfg['app']['symbols'], default=cfg['app']['symbols'][:8])
    tf = st.selectbox('Timeframe', cfg['app']['timeframes'], index=1)
    account_equity = st.number_input('Account USD', value=float(cfg['backtest']['initial_cash']), step=1000.0)
    sizing_mode = st.selectbox('Position sizing', ['Fixed %', 'Fixed $ risk', 'Kelly (capped)'], index=0)
    risk_pct = st.slider('Risk % (Fixed %)', 0.1, 5.0, float(cfg['risk']['risk_pct_per_trade']), 0.1)
    risk_usd = st.number_input('Risk USD (Fixed $)', value=50.0, step=10.0)
    kelly_cap = st.slider('Kelly cap %', 0.1, 3.0, float(cfg['risk']['kelly_cap_pct']), 0.1)
    max_gross = st.slider('Max gross exposure % (portfolio)', 10.0, 200.0, float(cfg['risk']['max_gross_exposure_pct']), 1.0)
    send_tg = st.checkbox('Telegram alerts (R/R ≥ seuil)', value=False)
    rr_thresh = st.number_input('Seuil R/R', value=float(cfg['app']['rr_alert_threshold']), step=0.1)

def send_telegram(msg: str):
    token = os.getenv('TELEGRAM_BOT_TOKEN'); chat = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat: return False
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/sendMessage", params={'chat_id': chat, 'text': msg}, timeout=8)
        return r.status_code==200
    except Exception: return False

tab_scan, tab_port, tab_journal, tab_bt, tab_report = st.tabs(['Scanner (Regime + Ensemble)', 'Allocation Portefeuille', 'Journal', 'Backtest', 'Rapport'])

with tab_scan:
    st.subheader('Scan — Regime-gated ensemble')
    if st.button('🚀 Scanner maintenant'):
        rows = []; per_symbol_weights = {}
        for sym in symbols:
            df = load_or_fetch(exchange, sym, tf, limit=3000)
            regime = kmeans_regime(df)
            reg_now = str(regime.iloc[-1])
            sigs_all = {}
            for name, func in ALL.items():
                if reg_now in ('up','down') and name in MR_STRATS: continue
                if reg_now in ('high_vol',) and name in TREND_STRATS: continue
                sigs_all[name] = func(df)
            if not sigs_all: sigs_all = {name: func(df) for name, func in ALL.items()}
            w = ensemble_weights(df, sigs_all, window=int(cfg['app']['ensemble_window']))
            sig_blend = blended_signal(sigs_all, w)
            per_symbol_weights[sym] = w.to_dict()
            direction = int(sig_blend.iloc[-1])
            lvl = adaptive_levels(df, direction, atr_mult_sl=cfg['risk']['atr_k_sl'], atr_mult_tp=cfg['risk']['atr_k_tp'])
            if not lvl: continue
            if sizing_mode=='Fixed %':
                qty = size_fixed_pct(account_equity, lvl['entry'], lvl['sl'], risk_pct)
            elif sizing_mode=='Fixed $ risk':
                qty = size_fixed_usd(risk_usd, lvl['entry'], lvl['sl'])
            else:
                macd_pnl = backtest(df, list(sigs_all.values())[0])['pnl'].iloc[-200:]
                p_win = float((macd_pnl>0).mean()) if len(macd_pnl)>20 else 0.5
                qty = size_kelly_fraction(p_win, win_mult=2.0, loss_mult=1.0, cap_pct=kelly_cap, account_equity=account_equity, entry=lvl['entry'], stop=lvl['sl'])
            r = abs(lvl['entry']-lvl['sl']); rr = abs(lvl['tp']-lvl['entry'])/max(r,1e-9)
            rows.append({'symbol': sym, 'regime': reg_now, 'dir': 'LONG' if direction>0 else 'SHORT' if direction<0 else 'FLAT',
                         'entry': lvl['entry'], 'sl': lvl['sl'], 'tp': lvl['tp'], 'rr': rr, 'qty': qty})
            if send_tg and rr>=rr_thresh and direction!=0:
                send_telegram(f"[{sym} {tf}] {reg_now.upper()} ENSEMBLE | {rows[-1]['dir']} | Entry {lvl['entry']:.6f} SL {lvl['sl']:.6f} TP {lvl['tp']:.6f} R/R {rr:.2f}")
        if rows:
            df_rows = pd.DataFrame(rows).sort_values('rr', ascending=False)
            st.dataframe(df_rows[['symbol','regime','dir','entry','sl','tp','rr','qty']].round(6), use_container_width=True)
            sel = st.selectbox('Ticket pour', [r['symbol'] for r in rows])
            rsel = [r for r in rows if r['symbol']==sel][0]
            st.json(per_symbol_weights.get(sel, {}))
            st.markdown(f"**Ticket {sel} — {rsel['dir']}** | Entry {rsel['entry']:.6f} SL {rsel['sl']:.6f} TP {rsel['tp']:.6f} Qty {rsel['qty']:.6f} R/R {rsel['rr']:.2f}")
            if st.button('📌 Enregistrer ce trade'):
                add_trade(sel, rsel['dir'], float(rsel['entry']), float(rsel['sl']), float(rsel['tp']), float(rsel['qty']), float(rsel['rr']), note='ENSEMBLE/REGIME')
                st.success('Trade ajouté.')

with tab_port:
    st.subheader('Allocation portefeuille & contrôle exposure')
    lookback = st.slider('Lookback (bars)', 100, 1000, 400, 50)
    if st.button('🧮 Calculer allocation'):
        rets = {}
        for sym in symbols:
            df = load_or_fetch(exchange, sym, tf, limit=max(lookback+10, 500))
            rets[sym] = df['close'].pct_change().dropna().iloc[-lookback:]
        R = pd.DataFrame(rets).dropna()
        w_iv = inverse_vol_weights(R); w_mv = min_var_weights(R)
        w_cap = cap_gross_exposure(w_mv, max_gross)
        st.write('Min-Var Weights (capped):', w_cap.round(4))
        st.bar_chart(w_cap)

with tab_journal:
    st.subheader('Trade Journal (auto + expectancy par setup)')
    from src.journal.db import list_trades, update_trade_result
    trades = list_trades(limit=1000)
    if trades.empty:
        st.info('Journal vide.')
    else:
        st.dataframe(trades[['id','ts','symbol','side','entry','sl','tp','qty','rr','result','pnl','note']], use_container_width=True)
        if st.button('🔍 Auto-check WIN/LOSS'):
            updates = []
            for _, t in trades.iterrows():
                if str(t['result']).upper() in ('WIN','LOSS','CLOSE'): continue
                price = fetch_last_price(exchange, t['symbol'])
                result = ''; pnl = None
                if t['side']=='LONG':
                    if price >= t['tp']: result='WIN'
                    elif price <= t['sl']: result='LOSS'
                elif t['side']=='SHORT':
                    if price <= t['tp']: result='WIN'
                    elif price >= t['sl']: result='LOSS'
                if result:
                    exit_price = t['tp'] if result=='WIN' else t['sl']
                    pnl = (exit_price - t['entry']) * (t['qty']) * (1 if t['side']=='LONG' else -1)
                    update_trade_result(int(t['id']), result, float(pnl))
                    updates.append({'id': t['id'], 'symbol': t['symbol'], 'result': result, 'pnl': pnl})
            if updates: st.write(pd.DataFrame(updates)); st.rerun()
        # Expectancy by setup
        df = trades.dropna(subset=['entry','sl','tp','qty']).copy()
        def r_multiple(row):
            R = abs(row['entry']-row['sl'])
            if R==0 or row['pnl'] is None or row['qty'] in (None, 0): return None
            sign = 1 if row['side']=='LONG' else -1
            return sign*((row['pnl']/row['qty'])/R)
        df['R_multiple'] = df.apply(r_multiple, axis=1)
        exp = df.groupby('note')['R_multiple'].mean().dropna()
        st.write('Expectancy (R) par setup:', exp.round(3))
        # Excel export
        import io
        xls = io.BytesIO()
        with pd.ExcelWriter(xls, engine='xlsxwriter') as writer:
            trades.to_excel(writer, sheet_name='trades', index=False)
            exp.reset_index().to_excel(writer, sheet_name='expectancy', index=False)
        st.download_button('⬇️ Export Excel', data=xls.getvalue(), file_name='journal_export.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

with tab_bt:
    st.subheader('Backtest (single stratégie)')
    sym = st.selectbox('Symbole', symbols, key='bt_sym')
    from src.strategies import ALL as STRATS
    strat = st.selectbox('Stratégie', list(STRATS.keys()), key='bt_strat')
    if st.button('▶️ Backtest', key='bt_run'):
        df = load_or_fetch(exchange, sym, tf, limit=3000)
        sig = STRATS[strat](df)
        bt = backtest(df, sig, initial_cash=cfg['backtest']['initial_cash'],
                      fee_bps=cfg['risk']['fee_bps'], slippage_bps=cfg['risk']['slippage_bps'])
        st.line_chart(pd.Series(bt['equity'], name='equity'))
        st.write({'Sharpe': sharpe(bt['pnl']), 'Sortino': sortino(bt['pnl']), 'MaxDD': max_drawdown(bt['equity']), 'Calmar': calmar(bt['equity'])})

with tab_report:
    st.subheader('Rapport (CSV + PDF avec graphiques)')
    if st.button('🧾 Générer rapport'):
        rows = []; equities = {}
        for sym in symbols:
            df = load_or_fetch(exchange, sym, tf, limit=1200)
            sigs = {name: func(df) for name, func in ALL.items()}
            w = ensemble_weights(df, sigs, window=int(cfg['app']['ensemble_window']))
            sig_blend = blended_signal(sigs, w)
            from src.backtest.engine import backtest
            bt = backtest(df, sig_blend, initial_cash=1.0)
            equities[sym] = bt['equity']
            dir_now = int(sig_blend.iloc[-1])
            lvl = adaptive_levels(df, dir_now, atr_mult_sl=cfg['risk']['atr_k_sl'], atr_mult_tp=cfg['risk']['atr_k_tp'])
            if lvl:
                r = abs(lvl['entry']-lvl['sl']); rr = abs(lvl['tp']-lvl['entry'])/max(r,1e-9)
                rows.append({'symbol': sym, 'dir': dir_now, 'entry': lvl['entry'], 'sl': lvl['sl'], 'tp': lvl['tp'], 'R/R': rr})
        rep = pd.DataFrame(rows)
        csv = rep.to_csv(index=False).encode('utf-8')
        st.download_button('⬇️ CSV', data=csv, file_name='report.csv', mime='text/csv')
        # charts
        fig1 = plt.figure()
        try:
            df_eq = pd.DataFrame(equities).dropna()
            (df_eq.mean(axis=1)).plot()
            plt.title('Aggregate equity (normalized)')
            p1 = 'reports/eq.png'; fig1.savefig(p1, bbox_inches='tight'); plt.close(fig1)
        except Exception:
            p1 = None
        fig2 = plt.figure()
        try:
            corr = pd.DataFrame({k: v.pct_change() for k,v in equities.items()}).corr()
            plt.imshow(corr, aspect='auto')
            plt.xticks(range(len(corr.columns)), corr.columns, rotation=90)
            plt.yticks(range(len(corr.index)), corr.index)
            plt.title('Correlation heatmap')
            p2 = 'reports/heatmap.png'; fig2.savefig(p2, bbox_inches='tight'); plt.close(fig2)
        except Exception:
            p2 = None
        lines = [f"{r['symbol']} | dir={r['dir']} | R/R={round(r['R/R'],2)} | entry={round(r['entry'],6)} | SL={round(r['sl'],6)} | TP={round(r['tp'],6)}" for _,r in rep.iterrows()]
        os.makedirs('reports', exist_ok=True)
        build_pdf('reports/daily_report.pdf', 'HELIOS ALPHA — Daily Report', lines, images=[x for x in [p1,p2] if x])
        with open('reports/daily_report.pdf','rb') as f:
            st.download_button('⬇️ PDF', data=f.read(), file_name='daily_report.pdf', mime='application/pdf')

st.markdown('---')
st.caption('ℹ️ TF = cadence de recalcul (ex: 1h). Pas une promesse de gain en 1h. Exécution manuelle.')
