import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import time
import threading
import sqlite3
import yfinance as yf

st.set_page_config(page_title="Upstox Algo Bot & Journal", layout="wide", page_icon="📈")

st.title("🤖 Upstox അൽഗോരിതം ട്രേഡിങ് ബോട്ട് & ജേർണൽ")
st.caption("തത്സമയ ബോട്ടും മുൻ ദിവസങ്ങളിലെ വിവരങ്ങൾ വിശകലനം ചെയ്യാനുള്ള സമ്പൂർണ്ണ ഡാറ്റാബേസും.")

# ==========================================
# 🗄️ സ്ഥിരമായ ഡാറ്റാബേസ് സെറ്റപ്പ് (SQLite Database)
# ==========================================
def init_db():
    conn = sqlite3.connect("trading_journal.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT, time TEXT, symbol TEXT, price REAL,
                    vwap REAL, rsi REAL, vol_surge TEXT, ema_cross TEXT,
                    status TEXT, reason TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT, time TEXT, symbol TEXT, type TEXT,
                    buy_price REAL, sell_price REAL, qty INTEGER, pnl REAL)''')
    conn.commit()
    conn.close()

init_db()

def save_audit_log(date_str, time_str, sym, price, vwap, rsi, vol_surge, ema_cross, status, reason):
    try:
        conn = sqlite3.connect("trading_journal.db")
        c = conn.cursor()
        c.execute('''INSERT INTO audit_logs (date, time, symbol, price, vwap, rsi, vol_surge, ema_cross, status, reason)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (date_str, time_str, sym, price, vwap, rsi, vol_surge, ema_cross, status, reason))
        conn.commit()
        conn.close()
    except Exception:
        pass

def save_trade_record(date_str, time_str, sym, t_type, bp, sp, qty, pnl):
    try:
        conn = sqlite3.connect("trading_journal.db")
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

BACKTEST_STOCKS = [
    'SBIN.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'AXISBANK.NS', 'KOTAKBANK.NS', 'BAJFINANCE.NS',
    'TCS.NS', 'INFY.NS', 'HCLTECH.NS', 'WIPRO.NS', 'M&M.NS', 'MARUTI.NS',
    'RELIANCE.NS', 'NTPC.NS', 'POWERGRID.NS', 'ONGC.NS', 'LT.NS', 'TATASTEEL.NS', 'BHARTIARTL.NS', 'ITC.NS'
]

@st.cache_resource
def get_global_state():
    return {
        'running': False, 'token': '', 'capital': 5000.0, 'risk': 100.0,
        'mode': 'പേപ്പർ ട്രേഡിംഗ്', 'tg_token': '', 'tg_chat': '', 'thread': None
    }

state = get_global_state()

# സൈഡ്‌ബാർ
st.sidebar.header("⚙️ കൺട്രോൾ പാനൽ")
mode_input = st.sidebar.radio("ട്രേഡിംഗ് മോഡ്:", ["പേപ്പർ ട്രേഡിംഗ്", "ലൈവ് റിയൽ മണി"], index=0 if state['mode']=="പേപ്പർ ട്രേഡിംഗ്" else 1)
token_input = st.sidebar.text_input("Upstox Access Token:", value=state['token'], type="password")
capital_input = st.sidebar.number_input("ക്യാപിറ്റൽ (₹):", value=float(state['capital']), step=500.0)
risk_input = st.sidebar.number_input("ഒരു ട്രേഡിലെ റിസ്ക് (₹):", value=float(state['risk']), step=25.0)

tg_token_input = st.sidebar.text_input("Telegram Bot Token (Optional):", value=state['tg_token'], type="password")
tg_chat_input = st.sidebar.text_input("Telegram Chat ID (Optional):", value=state['tg_chat'])

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
    return df

# ബാക്ക്ഗ്രൗണ്ട് ലൂപ്പ്
def background_trading_loop():
    while state['running']:
        token = state['token']
        if not token:
            time.sleep(5)
            continue

        for symbol, instrument_key in WATCHLIST.items():
            if not state['running']:
                break
            df = fetch_candles(instrument_key, token)
            if df is None or len(df) < 30:
                continue

            df = calculate_indicators(df)
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            curr_price = float(curr['close'])
            curr_vol = float(curr['volume'])
            vol_avg = float(curr['Vol_SMA']) if not np.isnan(curr['Vol_SMA']) else 0
            vwap = float(curr['VWAP'])
            rsi = float(curr['RSI'])

            ema_cross = (prev['EMA_Fast'] <= prev['EMA_Slow']) and (curr['EMA_Fast'] > curr['EMA_Slow'])
            rsi_safe = 50 <= rsi <= 68
            above_vwap = curr_price > vwap
            volume_surge = curr_vol >= (1.2 * vol_avg) if vol_avg > 0 else True

            ist_zone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            now_ist = datetime.datetime.now(ist_zone)
            curr_date = now_ist.strftime("%Y-%m-%d")
            curr_time = now_ist.strftime("%I:%M:%S %p")

            if not above_vwap:
                reason, status = "VWAP-ക്ക് താഴെയാണ് (Bearish)", "SKIPPED"
            elif not volume_surge:
                reason, status = "വോളിയം കുറവാണ് (No Surge)", "SKIPPED"
            elif not rsi_safe:
                reason, status = f"RSI അനുകൂലമല്ല ({rsi:.1f})", "SKIPPED"
            elif not ema_cross:
                reason, status = "EMA ക്രോസ് ആയിട്ടില്ല", "WAITING"
            else:
                reason, status = "എല്ലാ ഫിൽട്ടറുകളും വിജയിച്ചു!", "🎯 BUY TRIGGERED"
                send_telegram(f"🚀 *BUY സിഗ്നൽ:* `{symbol}` @ ₹{curr_price:.2f}", state['tg_token'], state['tg_chat'])
                save_trade_record(curr_date, curr_time, symbol, "PAPER_BUY", curr_price, 0.0, 1, 0.0)

            # സ്ഥിരമായി ഡാറ്റാബേസിലേക്ക് സേവ് ചെയ്യുന്നു
            save_audit_log(curr_date, curr_time, symbol, round(curr_price, 2),
                           round(vwap, 2), round(rsi, 1),
                           "Yes" if volume_surge else "No",
                           "Yes" if ema_cross else "No",
                           status, reason)

        time.sleep(10)

# ബട്ടൺ കൺട്രോളുകൾ
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

        if state['thread'] is None or not state['thread'].is_alive():
            t = threading.Thread(target=background_trading_loop, daemon=True)
            t.start()
            state['thread'] = t
        st.sidebar.success("ബോട്ട് ആരംഭിച്ചു!")

if col2.button("⏹️ STOP BOT", use_container_width=True):
    state['running'] = False
    st.sidebar.warning("ബോട്ട് ഓഫ് ചെയ്തു!")

# ==========================================
# 📊 4 പ്രധാന ടാബുകൾ
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 തത്സമയ ലോഗ്",
    "📚 ആർക്കൈവ് & ഹിസ്റ്ററി ജേർണൽ",
    "📜 ട്രേഡുകൾ",
    "📊 20 സ്റ്റോക്ക് മെഗാ ബാക്ക്ടെസ്റ്റ്"
])

# ടാബ് 1: തത്സമയ ലോഗ്
with tab1:
    st.subheader("🟢 ഇന്നത്തെ തത്സമയ സ്കാനിംഗ് പ്രവർത്തനങ്ങൾ")
    conn = sqlite3.connect("trading_journal.db")
    ist_zone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    today_str = datetime.datetime.now(ist_zone).strftime("%Y-%m-%d")
    df_live = pd.read_sql_query(f"SELECT time AS Time, symbol AS Stock, price AS Price, vwap AS VWAP, rsi AS RSI, vol_surge AS [Vol Surge], status AS Status, reason AS Reason FROM audit_logs WHERE date='{today_str}' ORDER BY id DESC LIMIT 50", conn)
    conn.close()
    if not df_live.empty:
        st.dataframe(df_live, use_container_width=True, hide_index=True)
    else:
        st.info("ഇന്നത്തെ സ്കാനിംഗ് ഡാറ്റ വരാൻ കാത്തിരിക്കുന്നു...")

# ടാബ് 2: കഴിഞ്ഞ ദിവസങ്ങളിലെ ഹിസ്റ്ററി ജേർണൽ (പഠിക്കാൻ വേണ്ടിയുള്ളത്)
with tab2:
    st.subheader("📚 മുൻ ദിവസങ്ങളിലെ സമ്പൂർണ്ണ ട്രേഡിംഗ് ജേർണൽ (Audit History)")
    st.caption("മുൻപ് ബോട്ട് പ്രവർത്തിച്ച ദിവസങ്ങളിലെ എല്ലാ കണക്കുകളും പരിശോധിച്ച് പഠിക്കാനുള്ള സംവിധാനം.")

    conn = sqlite3.connect("trading_journal.db")
    dates_df = pd.read_sql_query("SELECT DISTINCT date FROM audit_logs ORDER BY date DESC", conn)
    
    if not dates_df.empty:
        available_dates = dates_df['date'].tolist()
        selected_date = st.selectbox("📅 പരിശോധിക്കേണ്ട തീയതി തിരഞ്ഞെടുക്കുക:", available_dates)

        if selected_date:
            df_hist = pd.read_sql_query(f"SELECT time AS [Time (IST)], symbol AS Stock, price AS Price, vwap AS VWAP, rsi AS RSI, vol_surge AS [Volume Surge], ema_cross AS [EMA Cross], status AS Status, reason AS [Detailed Decision / Filter Reason] FROM audit_logs WHERE date='{selected_date}' ORDER BY id DESC", conn)
            
            # സംഗ്രഹം
            total_checks = len(df_hist)
            triggers = len(df_hist[df_hist['Status'] == '🎯 BUY TRIGGERED'])
            skips = total_checks - triggers

            c_h1, c_h2, c_h3 = st.columns(3)
            c_h1.metric("ആകെ സ്കാൻ ചെയ്തത്", total_checks)
            c_h2.metric("ബൈ സിഗ്നൽ വന്നത്", triggers)
            c_h3.metric("ഫിൽട്ടർ ചെയ്തത് (ഒഴിവാക്കിയത്)", skips)

            st.write(f"### 📋 {selected_date}-ലെ മുഴുവൻ തീരുമാനങ്ങൾ:")
            st.dataframe(df_hist, use_container_width=True, hide_index=True)

            # എക്സൽ ഡൗൺലോഡ് ബട്ടൺ
            csv_data = df_hist.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 {selected_date}-ലെ ഹിസ്റ്ററി Excel (CSV) ആയി ഡൗൺലോഡ് ചെയ്യുക",
                data=csv_data,
                file_name=f"trading_audit_{selected_date}.csv",
                mime='text/csv'
            )
    else:
        st.info("ഡാറ്റാബേസിൽ ഇതുവരെ പഴയ ദിവസങ്ങളിലെ ഡാറ്റ രേഖപ്പെടുത്തിയിട്ടില്ല. ബോട്ട് റൺ ചെയ്യുമ്പോൾ ഇവിടെ സ്വയം ശേഖരിക്കപ്പെടും.")
    conn.close()

# ടാബ് 3: എടുത്ത ട്രേഡുകൾ
with tab3:
    st.subheader("📜 പൂർത്തിയായതും നിലവിലുള്ളതുമായ ട്രേഡുകൾ")
    conn = sqlite3.connect("trading_journal.db")
    df_trades = pd.read_sql_query("SELECT date AS Date, time AS Time, symbol AS Stock, type AS Action, buy_price AS [Buy Price], sell_price AS [Sell Price], pnl AS PnL FROM trades ORDER BY id DESC", conn)
    conn.close()
    if not df_trades.empty:
        st.dataframe(df_trades, use_container_width=True, hide_index=True)
    else:
        st.info("ഇതുവരെ ട്രേഡുകൾ ഒന്നും നടന്നിട്ടില്ല.")

# ടാബ് 4: മെഗാ ബാക്ക്ടെസ്റ്റ്
with tab4:
    st.subheader("📈 20 പ്രമുഖ നിഫ്റ്റി ഓഹരികളുടെ 5 വർഷത്തെ ബാക്ക്ടെസ്റ്റ്")
    if st.button("🚀 5 വർഷത്തെ മെഗാ ബാക്ക്ടെസ്റ്റ് റൺ ചെയ്യുക"):
        with st.spinner("⏳ ഡാറ്റ വിശകലനം ചെയ്യുന്നു... കാത്തിരിക്കൂ..."):
            bt_results = []
            def calculate_charges(buy_val, sell_val):
                turnover = buy_val + sell_val
                brokerage = min(20.0, buy_val * 0.0005) + min(20.0, sell_val * 0.0005)
                return brokerage + (sell_val * 0.00025) + (turnover * 0.0000345) + (turnover * 0.000001) + (buy_val * 0.00003) + (0.18 * (brokerage + turnover * 0.0000345))

            for sym in BACKTEST_STOCKS:
                try:
                    df_b = yf.download(sym, period="5y", interval="1d", auto_adjust=True, progress=False)
                    if df_b.empty or len(df_b) < 60: continue
                    close_b = df_b['Close'].to_numpy(dtype=float).flatten()
                    high_b = df_b['High'].to_numpy(dtype=float).flatten()
                    low_b = df_b['Low'].to_numpy(dtype=float).flatten()
                    
                    tr = np.max(np.vstack([high_b[1:] - low_b[1:], np.abs(high_b[1:] - close_b[:-1]), np.abs(low_b[1:] - close_b[:-1])]), axis=0)
                    tr = np.insert(tr, 0, high_b[0] - low_b[0])
                    atr = pd.Series(tr).rolling(window=10).mean().to_numpy().flatten()
                    hl2 = (high_b + low_b) / 2
                    upperband = hl2 + (3 * atr)
                    lowerband = hl2 - (3 * atr)
                    direction = np.ones(len(close_b))
                    for i in range(10, len(close_b)):
                        if float(close_b[i-1]) > float(upperband[i-1]): direction[i] = 1
                        elif float(close_b[i-1]) < float(lowerband[i-1]): direction[i] = -1
                        else:
                            direction[i] = direction[i-1]
                            if direction[i] == 1 and lowerband[i] < lowerband[i-1]: lowerband[i] = lowerband[i-1]
                            if direction[i] == -1 and upperband[i] > upperband[i-1]: upperband[i] = upperband[i-1]
                    
                    ema_50_b = pd.Series(close_b).ewm(span=50, adjust=False).mean().to_numpy().flatten()
                    cap, wins, losses, win_s, loss_s = 5000.0, 0, 0, 0.0, 0.0
                    in_p, bp, sl, tg, qty = False, 0, 0, 0, 0
                    trailed = False

                    for i in range(50, len(close_b)):
                        cp, c_atr = float(close_b[i]), float(atr[i]) if not np.isnan(atr[i]) else (float(close_b[i]) * 0.02)
                        if not in_p:
                            if (direction[i-1] == -1 and direction[i] == 1) and (cp > ema_50_b[i]):
                                in_p, bp, qty = True, cp, max(1, int(cap // cp))
                                sl, tg, trailed = bp - (1.5 * c_atr), bp + (3.0 * c_atr), False
                                continue
                        if in_p:
                            done, sp = False, 0
                            if not trailed and cp >= (bp + (1.5 * c_atr)): sl, trailed = bp, True
                            if cp >= tg: sp, done, wins = tg, True, wins + 1
                            elif cp <= sl: sp, done, losses = sl, True, losses + 1
                            if done:
                                net = ((sp - bp) * qty) - calculate_charges(bp * qty, sp * qty)
                                cap += net
                                if net > 0: win_s += net
                                else: loss_s += abs(net)
                                in_p = False

                    tot = wins + losses
                    if tot > 0:
                        bt_results.append({
                            'Stock': sym.replace('.NS', ''), 'Trades': tot, 'Wins': wins, 'Losses': losses,
                            'Win Rate (%)': round((wins/tot)*100, 1),
                            'Profit Factor': round(win_s / loss_s, 2) if loss_s > 0 else 99.0,
                            'Net Profit (₹)': round(cap - 5000.0, 2)
                        })
                except Exception: continue

            if bt_results:
                st.dataframe(pd.DataFrame(bt_results).sort_values(by=['Net Profit (₹)'], ascending=False), use_container_width=True, hide_index=True)

# സ്ക്രീനിൽ നിൽക്കുമ്പോൾ തനിയെ അപ്‌ഡേറ്റ് ആകാൻ
if state['running']:
    time.sleep(5)
    st.rerun()
