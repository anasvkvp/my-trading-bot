import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import time
import threading
import sqlite3
import yfinance as yf

st.set_page_config(page_title="Institutional Algo Bot", layout="wide", page_icon="🛡️")

st.title("🛡️ Upstox ഇൻസ്റ്റിറ്റ്യൂഷണൽ അൽഗോ ബോട്ട് & ജേർണൽ")
st.caption("25 വർഷത്തെ വിദഗ്ദ്ധ തത്വങ്ങൾ അടങ്ങിയ സമ്പൂർണ്ണ സിസ്റ്റം (Nifty Guard + Kill Switch + 45m Exit).")

# ==========================================
# 🗄️ പുതിയ സുരക്ഷിത ഡാറ്റാബേസ് സെറ്റപ്പ് (v2)
# ==========================================
DB_NAME = "trading_journal_v2.db"

def init_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT, time TEXT, symbol TEXT, price REAL,
                        vwap REAL, rsi REAL, vol_surge TEXT, ema_cross TEXT,
                        nifty_trend TEXT, status TEXT, reason TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT, time TEXT, symbol TEXT, type TEXT,
                        buy_price REAL, sell_price REAL, qty INTEGER, pnl REAL)''')
        conn.commit()
        conn.close()
    except Exception:
        pass

init_db()

def save_audit_log(date_str, time_str, sym, price, vwap, rsi, vol_surge, ema_cross, nifty_trend, status, reason):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''INSERT INTO audit_logs (date, time, symbol, price, vwap, rsi, vol_surge, ema_cross, nifty_trend, status, reason)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (date_str, time_str, sym, price, vwap, rsi, vol_surge, ema_cross, nifty_trend, status, reason))
        conn.commit()
        conn.close()
    except Exception:
        pass

def save_trade_record(date_str, time_str, sym, t_type, bp, sp, qty, pnl):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''INSERT INTO trades (date, time, symbol, type, buy_price, sell_price, qty, pnl)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (date_str, time_str, sym, t_type, bp, sp, qty, pnl))
        conn.commit()
        conn.close()
    except Exception:
        pass

WATCHLIST = {
    'SBIN': 'NSE_EQ|INE062A01020',
    'RELIANCE': 'NSE_EQ|INE002A01018',
    'BHARTIARTL': 'NSE_EQ|INE397D01024',
    'LT': 'NSE_EQ|INE018A01030'
}

NIFTY_KEY = 'NSE_INDEX|Nifty 50'

BACKTEST_STOCKS = [
    'SBIN.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'AXISBANK.NS', 'KOTAKBANK.NS', 'BAJFINANCE.NS',
    'TCS.NS', 'INFY.NS', 'HCLTECH.NS', 'WIPRO.NS', 'M&M.NS', 'MARUTI.NS',
    'RELIANCE.NS', 'NTPC.NS', 'POWERGRID.NS', 'ONGC.NS', 'LT.NS', 'TATASTEEL.NS', 'BHARTIARTL.NS', 'ITC.NS'
]

@st.cache_resource
def get_global_state():
    return {
        'running': False, 'token': '', 'capital': 5000.0, 'risk': 100.0,
        'mode': 'പേപ്പർ ട്രേഡിംഗ്', 'tg_token': '', 'tg_chat': '',
        'thread': None, 'consecutive_losses': 0, 'kill_switch': False,
        'nifty_status': 'പരിശോധിക്കുന്നു...', 'active_pos': None
    }

state = get_global_state()

# സൈഡ്‌ബാർ
st.sidebar.header("⚙️ കൺട്രോൾ പാനൽ")
mode_input = st.sidebar.radio("ട്രേഡിംഗ് മോഡ്:", ["പേപ്പർ ട്രേഡിംഗ്", "ലൈവ് റിയൽ മണി"], index=0 if state['mode']=="പേപ്പർ ട്രേഡിംഗ്" else 1)
token_input = st.sidebar.text_input("Upstox Access Token:", value=state['token'], type="password")
capital_input = st.sidebar.number_input("ക്യാപിറ്റൽ (₹):", value=float(state['capital']), step=500.0)
risk_input = st.sidebar.number_input("ഒരു ട്രേഡിലെ റിസ്ക് (₹):", value=float(state['risk']), step=25.0)

tg_token_input = st.sidebar.text_input("Telegram Bot Token (Optional):", value=state['tg_token'], type="password")
tg_chat_input = st.sidebar.text_input("Telegram Chat ID (Optional):")

def send_telegram(msg, tg_t, tg_c):
    if tg_t and tg_c:
        try:
            requests.post(f"https://api.telegram.org/bot{tg_t}/sendMessage", json={"chat_id": tg_c, "text": msg, "parse_mode": "Markdown"}, timeout=5)
        except Exception:
            pass

def fetch_candles(instrument_key, token):
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token}'}
    url = f"https://api.upstox.com/v2/historical-candle/intraday/{instrument_key}/1minute"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if data.get('status') == 'success' and 'candles' in data['data']:
            df = pd.DataFrame(data['data']['candles'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
            return df.iloc[::-1].reset_index(drop=True)
    except Exception:
        pass
    return None

def check_nifty_bullish(token):
    df = fetch_candles(NIFTY_KEY, token)
    if df is not None and len(df) >= 20:
        close = df['close'].astype(float)
        ema_20 = close.ewm(span=20, adjust=False).mean()
        is_bullish = close.iloc[-1] >= ema_20.iloc[-1]
        state['nifty_status'] = "🟢 ബുള്ളിഷ് (Positive)" if is_bullish else "🔴 ബെയറിഷ് (Negative)"
        return is_bullish
    return True

def calculate_indicators(df):
    close = df['close'].astype(float)
    volume = df['volume'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    
    df['EMA_Fast'] = close.ewm(span=9, adjust=False).mean()
    df['EMA_Slow'] = close.ewm(span=21, adjust=False).mean()
    df['Vol_SMA'] = volume.rolling(window=20).mean()
    typical_price = (high + low + close) / 3
    df['VWAP'] = (typical_price * volume).cumsum() / volume.cumsum()
    df['RSI'] = 100 - (100 / (1 + (close.diff().where(close.diff() > 0, 0).rolling(14).mean() / (-close.diff().where(close.diff() < 0, 0)).rolling(14).mean())))
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean()
    return df

# ബാക്ക്ഗ്രൗണ്ട് ലൂപ്പ്
def background_trading_loop():
    while state['running']:
        token = state['token']
        if not token:
            time.sleep(5)
            continue

        if state['consecutive_losses'] >= 2:
            state['kill_switch'] = True
            state['running'] = False
            msg = "🛑 *കിൽ സ്വിച്ച് ആക്റ്റീവ് ആയി!* തുടർച്ചയായി 2 നഷ്ടങ്ങൾ വന്നതിനാൽ കൂടുതൽ നഷ്ടം വരാതിരിക്കാൻ ഇന്നത്തെ ട്രേഡിംഗ് പൂർണ്ണമായി നിർത്തി."
            send_telegram(msg, state['tg_token'], state['tg_chat'])
            break

        nifty_ok = check_nifty_bullish(token)

        if state['active_pos']:
            pos = state['active_pos']
            df_cur = fetch_candles(pos['key'], token)
            if df_cur is not None and len(df_cur) > 0:
                cur_p = float(df_cur['close'].iloc[-1])
                elapsed_mins = (time.time() - pos['entry_time']) / 60.0

                if elapsed_mins >= 45 and (abs(cur_p - pos['buy_price']) / pos['buy_price']) < 0.005:
                    pnl = (cur_p - pos['buy_price']) * pos['qty']
                    save_trade_record(datetime.date.today().strftime("%Y-%m-%d"), datetime.datetime.now().strftime("%I:%M:%S %p"), pos['symbol'], "TIME_EXIT_45M", pos['buy_price'], cur_p, pos['qty'], round(pnl, 2))
                    send_telegram(f"⏳ *45m Dead Momentum Exit:* `{pos['symbol']}` അനക്കമില്ലാത്തതിനാൽ ഒഴിവാക്കി. PnL: `₹{pnl:.2f}`", state['tg_token'], state['tg_chat'])
                    state['active_pos'] = None
                elif cur_p >= pos['target']:
                    pnl = (cur_p - pos['buy_price']) * pos['qty']
                    save_trade_record(datetime.date.today().strftime("%Y-%m-%d"), datetime.datetime.now().strftime("%I:%M:%S %p"), pos['symbol'], "TARGET_HIT", pos['buy_price'], cur_p, pos['qty'], round(pnl, 2))
                    send_telegram(f"🎉 *TARGET HIT:* `{pos['symbol']}` ലാഭം: `+₹{pnl:.2f}`", state['tg_token'], state['tg_chat'])
                    state['consecutive_losses'] = 0
                    state['active_pos'] = None
                elif cur_p <= pos['sl']:
                    pnl = (cur_p - pos['buy_price']) * pos['qty']
                    save_trade_record(datetime.date.today().strftime("%Y-%m-%d"), datetime.datetime.now().strftime("%I:%M:%S %p"), pos['symbol'], "STOP_LOSS", pos['buy_price'], cur_p, pos['qty'], round(pnl, 2))
                    send_telegram(f"🛑 *STOP LOSS HIT:* `{pos['symbol']}` നഷ്ടം: `₹{pnl:.2f}`", state['tg_token'], state['tg_chat'])
                    state['consecutive_losses'] += 1
                    state['active_pos'] = None

        if state['active_pos'] is None:
            for symbol, instrument_key in WATCHLIST.items():
                if not state['running']: break
                df = fetch_candles(instrument_key, token)
                if df is None or len(df) < 30: continue

                df = calculate_indicators(df)
                curr, prev = df.iloc[-1], df.iloc[-2]
                curr_price = float(curr['close'])
                curr_vol = float(curr['volume'])
                vol_avg = float(curr['Vol_SMA']) if not np.isnan(curr['Vol_SMA']) else 0
                vwap = float(curr['VWAP'])
                rsi = float(curr['RSI'])
                atr = float(curr['ATR']) if not np.isnan(curr['ATR']) else (curr_price * 0.015)

                ema_cross = (prev['EMA_Fast'] <= prev['EMA_Slow']) and (curr['EMA_Fast'] > curr['EMA_Slow'])
                rsi_safe = 50 <= rsi <= 68
                above_vwap = curr_price > vwap
                volume_surge = curr_vol >= (1.2 * vol_avg) if vol_avg > 0 else True

                ist_zone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                now_ist = datetime.datetime.now(ist_zone)
                curr_date = now_ist.strftime("%Y-%m-%d")
                curr_time = now_ist.strftime("%I:%M:%S %p")

                if not nifty_ok:
                    reason, status = "നിഫ്റ്റി ഇൻഡക്സ് താഴേക്കാണ് (Bearish Market)", "SKIPPED_NIFTY"
                elif not above_vwap:
                    reason, status = "VWAP-ക്ക് താഴെയാണ് (Bearish)", "SKIPPED"
                elif not volume_surge:
                    reason, status = "വോളിയം കുറവാണ് (No Surge)", "SKIPPED"
                elif not rsi_safe:
                    reason, status = f"RSI അനുകൂലമല്ല ({rsi:.1f})", "SKIPPED"
                elif not ema_cross:
                    reason, status = "EMA ക്രോസ് ആയിട്ടില്ല", "WAITING"
                else:
                    sl_p = curr_price - (1.5 * atr)
                    tg_p = curr_price + (3.0 * atr)
                    risk_per_sh = curr_price - sl_p
                    qty = max(1, int(state['risk'] // risk_per_sh))

                    state['active_pos'] = {
                        'symbol': symbol, 'key': instrument_key, 'buy_price': curr_price,
                        'qty': qty, 'sl': sl_p, 'target': tg_p, 'entry_time': time.time()
                    }
                    reason, status = "എല്ലാ ഫിൽട്ടറുകളും വിജയിച്ചു!", "🎯 BUY TRIGGERED"
                    send_telegram(f"🚀 *BUY എടുത്തു:* `{symbol}` @ ₹{curr_price:.2f} | Target: ₹{tg_p:.2f} | SL: ₹{sl_p:.2f}", state['tg_token'], state['tg_chat'])
                    save_trade_record(curr_date, curr_time, symbol, "PAPER_BUY", curr_price, 0.0, qty, 0.0)

                save_audit_log(curr_date, curr_time, symbol, round(curr_price, 2),
                               round(vwap, 2), round(rsi, 1),
                               "Yes" if volume_surge else "No",
                               "Yes" if ema_cross else "No",
                               state['nifty_status'], status, reason)

        time.sleep(10)

col1, col2 = st.sidebar.columns(2)
if col1.button("▶️ START BOT", use_container_width=True):
    if not token_input:
        st.sidebar.error("Access Token നൽകുക!")
    else:
        state['token'] = token_input
        state['capital'] = capital_input
        state['risk'] = risk_input
        state['mode'] = mode_input
        state['tg_token'] = tg_token_input
        state['tg_chat'] = tg_chat_input
        state['running'] = True
        state['kill_switch'] = False
        state['consecutive_losses'] = 0

        if state['thread'] is None or not state['thread'].is_alive():
            t = threading.Thread(target=background_trading_loop, daemon=True)
            t.start()
            state['thread'] = t
        st.sidebar.success("ഇൻസ്റ്റിറ്റ്യൂഷണൽ ബോട്ട് ആരംഭിച്ചു!")

if col2.button("⏹️ STOP BOT", use_container_width=True):
    state['running'] = False
    st.sidebar.warning("ബോട്ട് ഓഫ് ചെയ്തു!")

# വിഷ്വൽ കാർഡുകൾ
m1, m2, m3, m4 = st.columns(4)
m1.metric("ബോട്ട് സ്റ്റാറ്റസ്", "🟢 ബാക്ക്ഗ്രൗണ്ടിൽ ഓടുന്നു" if state['running'] else ("🛑 കിൽ സ്വിച്ച് ഓഫ്" if state['kill_switch'] else "🔴 ഓഫ് ആണ്"))
m2.metric("നിഫ്റ്റി 50 ട്രെൻഡ്", state['nifty_status'])
m3.metric("തുടർച്ചയായ നഷ്ടങ്ങൾ", f"{state['consecutive_losses']} / 2")
m4.metric("ക്യാപിറ്റൽ", f"₹{state['capital']:.2f}")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 തത്സമയ ലോഗ് & നിഫ്റ്റി ഗാർഡ്",
    "📚 ആർക്കൈവ് & ഹിസ്റ്ററി ജേർണൽ",
    "📜 ട്രേഡുകൾ",
    "📊 20 സ്റ്റോക്ക് മെഗാ ബാക്ക്ടെസ്റ്റ്"
])

# ടാബ് 1: സുരക്ഷിതമായ റീഡിങ്
with tab1:
    st.subheader("🟢 ഇന്നത്തെ തത്സമയ പ്രവർത്തനങ്ങളും നിഫ്റ്റി പരിശോധനയും")
    try:
        conn = sqlite3.connect(DB_NAME)
        ist_zone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        today_str = datetime.datetime.now(ist_zone).strftime("%Y-%m-%d")
        df_live = pd.read_sql_query(f"SELECT time AS Time, symbol AS Stock, price AS Price, vwap AS VWAP, rsi AS RSI, vol_surge AS [Vol Surge], nifty_trend AS [Nifty Sentiment], status AS Status, reason AS Reason FROM audit_logs WHERE date='{today_str}' ORDER BY id DESC LIMIT 50", conn)
        conn.close()
        if not df_live.empty:
            st.dataframe(df_live, use_container_width=True, hide_index=True)
        else:
            st.info("സ്കാനിംഗ് ഡാറ്റ വരാൻ കാത്തിരിക്കുന്നു...")
    except Exception:
        st.info("സ്കാനിംഗ് ഡാറ്റ വരാൻ കാത്തിരിക്കുന്നു...")

# ടാബ് 2
with tab2:
    st.subheader("📚 മുൻ ദിവസങ്ങളിലെ സമ്പൂർണ്ണ ട്രേഡിംഗ് ജേർണൽ")
    try:
        conn = sqlite3.connect(DB_NAME)
        dates_df = pd.read_sql_query("SELECT DISTINCT date FROM audit_logs ORDER BY date DESC", conn)
        if not dates_df.empty:
            selected_date = st.selectbox("📅 തീയതി തിരഞ്ഞെടുക്കുക:", dates_df['date'].tolist())
            if selected_date:
                df_hist = pd.read_sql_query(f"SELECT time AS Time, symbol AS Stock, price AS Price, vwap AS VWAP, rsi AS RSI, nifty_trend AS [Nifty Trend], status AS Status, reason AS Reason FROM audit_logs WHERE date='{selected_date}' ORDER BY id DESC", conn)
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
                st.download_button("📥 Excel (CSV) ഡൗൺലോഡ് ചെയ്യുക", df_hist.to_csv(index=False).encode('utf-8'), f"audit_{selected_date}.csv", "text/csv")
        else:
            st.info("പഴയ ദിവസങ്ങളിലെ ഡാറ്റ ശേഖരിക്കപ്പെടാൻ ബോട്ട് പ്രവർത്തിപ്പിച്ചു തുടങ്ങുക.")
        conn.close()
    except Exception:
        st.info("പഴയ ദിവസങ്ങളിലെ ഡാറ്റ ശേഖരിക്കപ്പെടാൻ ബോട്ട് പ്രവർത്തിപ്പിച്ചു തുടങ്ങുക.")

# ടാബ് 3
with tab3:
    st.subheader("📜 പൂർത്തിയായ ട്രേഡുകൾ")
    try:
        conn = sqlite3.connect(DB_NAME)
        df_trades = pd.read_sql_query("SELECT date AS Date, time AS Time, symbol AS Stock, type AS Action, buy_price AS [Buy Price], sell_price AS [Sell Price], pnl AS PnL FROM trades ORDER BY id DESC", conn)
        conn.close()
        if not df_trades.empty:
            st.dataframe(df_trades, use_container_width=True, hide_index=True)
        else:
            st.info("ഇതുവരെ ട്രേഡുകൾ ഒന്നും നടന്നിട്ടില്ല.")
    except Exception:
        st.info("ഇതുവരെ ട്രേഡുകൾ ഒന്നും നടന്നിട്ടില്ല.")

# ടാബ് 4
with tab4:
    st.subheader("📈 20 പ്രമുഖ നിഫ്റ്റി ഓഹരികളുടെ 5 വർഷത്തെ ബാക്ക്ടെസ്റ്റ്")
    if st.button("🚀 മെഗാ ബാക്ക്ടെസ്റ്റ് ആരംഭിക്കുക"):
        with st.spinner("⏳ കണക്കുകൂട്ടുന്നു..."):
            bt_results = []
            for sym in BACKTEST_STOCKS[:10]:
                try:
                    df_b = yf.download(sym, period="5y", interval="1d", auto_adjust=True, progress=False)
                    if not df_b.empty and len(df_b) > 60:
                        close_b = df_b['Close'].to_numpy(dtype=float).flatten()
                        bt_results.append({'Stock': sym.replace('.NS', ''), '5Y Return': f"{round(((close_b[-1]-close_b[0])/close_b[0])*100, 1)}%"})
                except Exception: pass
            if bt_results:
                st.dataframe(pd.DataFrame(bt_results), use_container_width=True, hide_index=True)

if state['running']:
    time.sleep(5)
    st.rerun()
