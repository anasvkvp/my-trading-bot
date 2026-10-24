import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import time
import threading
import sqlite3
import yfinance as yf

st.set_page_config(page_title="Complete Wealth & Trading Hub", layout="wide", page_icon="🏦")

# ==========================================
# 🗄️ ഡാറ്റാബേസ് സെറ്റപ്പ് (v2)
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

# ==========================================
# 🧭 പ്രധാന നാവിഗേഷൻ മെനു
# ==========================================
st.sidebar.title("🏦 വെൽത്ത് & ട്രേഡിംഗ് ഹബ്")
main_menu = st.sidebar.radio(
    "നിങ്ങൾക്ക് ആവശ്യമുള്ള വിഭാഗം തിരഞ്ഞെടുക്കുക:",
    [
        "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്",
        "🏛️ 50-Year Veteran ദീർഘകാല നിക്ഷേപം (AI-Proof)",
        "📈 മികച്ച മ്യൂച്വൽ ഫണ്ടുകൾ (SIP)"
    ]
)

WATCHLIST = {
    'SBIN': 'NSE_EQ|INE062A01020',
    'RELIANCE': 'NSE_EQ|INE002A01018',
    'BHARTIARTL': 'NSE_EQ|INE397D01024',
    'LT': 'NSE_EQ|INE018A01030'
}
NIFTY_KEY = 'NSE_INDEX|Nifty 50'

@st.cache_resource
def get_global_state():
    return {
        'running': False, 'token': '', 'capital': 5000.0, 'risk': 100.0,
        'mode': 'പേപ്പർ ട്രേഡിംഗ്', 'tg_token': '', 'tg_chat': '',
        'thread': None, 'consecutive_losses': 0, 'kill_switch': False,
        'nifty_status': 'പരിശോധിക്കുന്നു...', 'active_pos': None
    }

state = get_global_state()

# ##################################################################
# 🟢 വിഭാഗം 1: ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്
# ##################################################################
if main_menu == "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്":
    st.title("⚡ Upstox ഇൻസ്റ്റിറ്റ്യൂഷണൽ ഇൻട്രാഡേ ബോട്ട്")
    st.caption("കർശനമായ റിസ്ക് മാനേജ്മെന്റോടെയുള്ള ഓട്ടോമാറ്റിക് ഇൻട്രാഡേ സിസ്റ്റം (Nifty Guard + Kill Switch + 45m Exit).")

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ ബോട്ട് കൺട്രോൾ")
    mode_input = st.sidebar.radio("ട്രേഡിംഗ് മോഡ്:", ["പേപ്പർ ട്രേഡിംഗ്", "ലൈവ് റിയൽ മണി"], index=0 if state['mode']=="പേപ്പർ ട്രേഡിംഗ്" else 1)
    token_input = st.sidebar.text_input("Upstox Access Token:", value=state['token'], type="password")
    capital_input = st.sidebar.number_input("ക്യാപിറ്റൽ (₹):", value=float(state['capital']), step=500.0)
    risk_input = st.sidebar.number_input("ഒരു ട്രേഡിലെ റിസ്ക് (₹):", value=float(state['risk']), step=25.0)

    tg_token_input = st.sidebar.text_input("Telegram Bot Token (Optional):", value=state['tg_token'], type="password")
    tg_chat_input = st.sidebar.text_input("Telegram Chat ID (Optional):")

    def send_telegram(msg, tg_t, tg_c):
        if tg_t and tg_c:
            try: requests.post(f"https://api.telegram.org/bot{tg_t}/sendMessage", json={"chat_id": tg_c, "text": msg, "parse_mode": "Markdown"}, timeout=5)
            except Exception: pass

    def fetch_candles(instrument_key, token):
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token}'}
        try:
            res = requests.get(f"https://api.upstox.com/v2/historical-candle/intraday/{instrument_key}/1minute", headers=headers, timeout=10)
            data = res.json()
            if data.get('status') == 'success' and 'candles' in data['data']:
                df = pd.DataFrame(data['data']['candles'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
                return df.iloc[::-1].reset_index(drop=True)
        except Exception: pass
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
        df['VWAP'] = (((high + low + close) / 3) * volume).cumsum() / volume.cumsum()
        df['RSI'] = 100 - (100 / (1 + (close.diff().where(close.diff() > 0, 0).rolling(14).mean() / (-close.diff().where(close.diff() < 0, 0)).rolling(14).mean())))
        tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(window=14).mean()
        return df

    def background_trading_loop():
        while state['running']:
            token = state['token']
            if not token:
                time.sleep(5)
                continue

            if state['consecutive_losses'] >= 2:
                state['kill_switch'] = True
                state['running'] = False
                send_telegram("🛑 *കിൽ സ്വിച്ച് ആക്റ്റീവ് ആയി!* തുടർച്ചയായി 2 നഷ്ടങ്ങൾ വന്നതിനാൽ ട്രേഡിംഗ് നിർത്തി.", state['tg_token'], state['tg_chat'])
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
                        send_telegram(f"⏳ *45m Dead Momentum Exit:* `{pos['symbol']}` PnL: `₹{pnl:.2f}`", state['tg_token'], state['tg_chat'])
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
                    vol_avg = float(curr['Vol_SMA']) if not np.isnan(curr['Vol_SMA']) else 0
                    vwap = float(curr['VWAP'])
                    rsi = float(curr['RSI'])
                    atr = float(curr['ATR']) if not np.isnan(curr['ATR']) else (curr_price * 0.015)

                    ema_cross = (prev['EMA_Fast'] <= prev['EMA_Slow']) and (curr['EMA_Fast'] > curr['EMA_Slow'])
                    rsi_safe = 50 <= rsi <= 68
                    above_vwap = curr_price > vwap
                    volume_surge = float(curr['volume']) >= (1.2 * vol_avg) if vol_avg > 0 else True

                    ist_zone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                    now_ist = datetime.datetime.now(ist_zone)
                    curr_date = now_ist.strftime("%Y-%m-%d")
                    curr_time = now_ist.strftime("%I:%M:%S %p")

                    if not nifty_ok: reason, status = "നിഫ്റ്റി ഇൻഡക്സ് താഴേക്കാണ്", "SKIPPED_NIFTY"
                    elif not above_vwap: reason, status = "VWAP-ക്ക് താഴെയാണ് (Bearish)", "SKIPPED"
                    elif not volume_surge: reason, status = "വോളിയം കുറവാണ്", "SKIPPED"
                    elif not rsi_safe: reason, status = f"RSI അനുകൂലമല്ല ({rsi:.1f})", "SKIPPED"
                    elif not ema_cross: reason, status = "EMA ക്രോസ് ആയിട്ടില്ല", "WAITING"
                    else:
                        sl_p = curr_price - (1.5 * atr)
                        tg_p = curr_price + (3.0 * atr)
                        qty = max(1, int(state['risk'] // (curr_price - sl_p)))
                        state['active_pos'] = {'symbol': symbol, 'key': instrument_key, 'buy_price': curr_price, 'qty': qty, 'sl': sl_p, 'target': tg_p, 'entry_time': time.time()}
                        reason, status = "ഫിൽട്ടറുകൾ പാസായി!", "🎯 BUY TRIGGERED"
                        send_telegram(f"🚀 *BUY എടുത്തു:* `{symbol}` @ ₹{curr_price:.2f}", state['tg_token'], state['tg_chat'])
                        save_trade_record(curr_date, curr_time, symbol, "PAPER_BUY", curr_price, 0.0, qty, 0.0)

                    save_audit_log(curr_date, curr_time, symbol, round(curr_price, 2), round(vwap, 2), round(rsi, 1), "Yes" if volume_surge else "No", "Yes" if ema_cross else "No", state['nifty_status'], status, reason)
            time.sleep(10)

        col1, col2 = st.sidebar.columns(2)
        if col1.button("▶️ START BOT", use_container_width=True):
            if not token_input: st.sidebar.error("Access Token നൽകുക!")
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
                st.sidebar.success("ബോട്ട് ആരംഭിച്ചു!")

        if col2.button("⏹️ STOP BOT", use_container_width=True):
            state['running'] = False
            st.sidebar.warning("ബോട്ട് നിർത്തി!")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ബോട്ട് സ്റ്റാറ്റസ്", "🟢 ബാക്ക്ഗ്രൗണ്ടിൽ ഓടുന്നു" if state['running'] else ("🛑 കിൽ സ്വിച്ച് ഓഫ്" if state['kill_switch'] else "🔴 ഓഫ് ആണ്"))
    m2.metric("നിഫ്റ്റി 50 ട്രെൻഡ്", state['nifty_status'])
    m3.metric("തുടർച്ചയായ നഷ്ടങ്ങൾ", f"{state['consecutive_losses']} / 2")
    m4.metric("ക്യാപിറ്റൽ", f"₹{state['capital']:.2f}")

    st.divider()

    t1, t2, t3 = st.tabs(["🔍 തത്സമയ ലോഗ് & നിഫ്റ്റി ഗാർഡ്", "📚 ആർക്കൈവ് & ഹിസ്റ്ററി ജേർണൽ", "📜 ട്രേഡുകൾ"])
    with t1:
        try:
            conn = sqlite3.connect(DB_NAME)
            today_str = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")
            df_live = pd.read_sql_query(f"SELECT time AS Time, symbol AS Stock, price AS Price, vwap AS VWAP, rsi AS RSI, nifty_trend AS [Nifty Sentiment], status AS Status, reason AS Reason FROM audit_logs WHERE date='{today_str}' ORDER BY id DESC LIMIT 50", conn)
            conn.close()
            if not df_live.empty: st.dataframe(df_live, use_container_width=True, hide_index=True)
            else: st.info("സ്കാനിംഗ് ഡാറ്റ വരാൻ കാത്തിരിക്കുന്നു...")
        except Exception: st.info("സ്കാനിംഗ് ഡാറ്റ വരാൻ കാത്തിരിക്കുന്നു...")

    with t2:
        try:
            conn = sqlite3.connect(DB_NAME)
            dates_df = pd.read_sql_query("SELECT DISTINCT date FROM audit_logs ORDER BY date DESC", conn)
            if not dates_df.empty:
                sel_date = st.selectbox("📅 തീയതി തിരഞ്ഞെടുക്കുക:", dates_df['date'].tolist())
                if sel_date:
                    df_hist = pd.read_sql_query(f"SELECT time AS Time, symbol AS Stock, price AS Price, vwap AS VWAP, rsi AS RSI, nifty_trend AS [Nifty Trend], status AS Status, reason AS Reason FROM audit_logs WHERE date='{sel_date}' ORDER BY id DESC", conn)
                    st.dataframe(df_hist, use_container_width=True, hide_index=True)
                    st.download_button("📥 Excel (CSV) ഡൗൺലോഡ് ചെയ്യുക", df_hist.to_csv(index=False).encode('utf-8'), f"audit_{sel_date}.csv", "text/csv")
            conn.close()
        except Exception: st.info("പഴയ ഡാറ്റ ലഭ്യമായിട്ടില്ല.")

    with t3:
        try:
            conn = sqlite3.connect(DB_NAME)
            df_tr = pd.read_sql_query("SELECT date AS Date, time AS Time, symbol AS Stock, type AS Action, buy_price AS [Buy Price], sell_price AS [Sell Price], pnl AS PnL FROM trades ORDER BY id DESC", conn)
            conn.close()
            if not df_tr.empty: st.dataframe(df_tr, use_container_width=True, hide_index=True)
            else: st.info("ട്രേഡുകൾ ഒന്നും നടന്നിട്ടില്ല.")
        except Exception: st.info("ട്രേഡുകൾ ഒന്നും നടന്നിട്ടില്ല.")

# ##################################################################
# 🏛️ വിഭാഗം 2: 50-Year Veteran ദീർഘകാല നിക്ഷേപം (AI-Proof Framework)
# ##################################################################
elif main_menu == "🏛️ 50-Year Veteran ദീർഘകാല നിക്ഷേപം (AI-Proof)":
    st.title("🏛️ 50-Year Veteran ദീർഘകാല വെൽത്ത് നിലവറ")
    st.caption("വാറൻ ബഫറ്റ് ശൈലി: കടമില്ലാത്ത, ശക്തമായ കുത്തകയുള്ള, എഐ (AI) ഭീഷണിയില്ലാത്ത ഇന്ത്യയിലെ ഏറ്റവും കരുത്തുറ്റ കമ്പനികൾ.")

    v_tab1, v_tab2, v_tab3 = st.tabs([
        "🛡️ ഓൾ-വെതർ കുത്തകകൾ (Crash & AI Proof)",
        "⚡ എഐ യുഗത്തിൽ കുതിക്കുന്നവ (AI Beneficiaries)",
        "⚠️ എഐ വാല്യൂ ട്രാപ്പ് മുന്നറിയിപ്പ് (The Warning Checklist)"
    ])

    with v_tab1:
        st.subheader("🛡️ ഓൾ-വെതർ കുത്തകകൾ (മാർക്കറ്റ് വീണാലും ഉറച്ചുനിൽക്കുന്നവ)")
        st.markdown("""
        **50-വർഷത്തെ വിദഗ്ദ്ധ മാനദണ്ഡം:**
        * **പൂജ്യം കടം (Zero Debt):** പലിശ ഭാരമില്ലാത്തതിനാൽ സാമ്പത്തിക മാന്ദ്യത്തിലും കമ്പനി തകരില്ല.
        * **ROCE > 25%:** ബിസിനസ്സിൽ നിക്ഷേപിക്കുന്ന ഓരോ രൂപയ്ക്കും അത്യുഗ്രൻ റിട്ടേൺ.
        * **പ്രൈസിംഗ് പവർ (Pricing Power):** പണപ്പെരുപ്പമോ ചെലവുകളോ കൂടിയാൽ വില വർദ്ധിപ്പിക്കാൻ സാധിക്കുന്ന കുത്തക ശക്തി.
        """)

        all_weather_stocks = [
            {
                "Stock": "CDSL (Central Depository)",
                "Moat Type": "റെഗുലേറ്ററി കുത്തക (Duopoly)",
                "ROCE (%)": "33.5%",
                "Debt / Equity": "0.0 (പൂർണ്ണ കടരഹിതം)",
                "AI Disruption Risk": "🟢 പൂജ്യം (Zero Risk)",
                "Crash Resilience": "⭐⭐⭐⭐⭐ (Highest)",
                "Veteran Thesis": "ഇന്ത്യക്കാർ ഡിമാറ്റ് അക്കൗണ്ട് എടുക്കുന്നിടത്തോളം കാലം, ട്രേഡ് ചെയ്യുന്നിടത്തോളം കാലം ഒരു ടോൾ ബൂത്ത് പോലെ വരുമാനം നേടുന്നു."
            },
            {
                "Stock": "CAMS (Computer Age Management)",
                "Moat Type": "ഡാറ്റ & പ്രോസസ്സിംഗ് കുത്തക",
                "ROCE (%)": "44.2%",
                "Debt / Equity": "0.0 (പൂർണ്ണ കടരഹിതം)",
                "AI Disruption Risk": "🟢 പൂജ്യം (Zero Risk)",
                "Crash Resilience": "⭐⭐⭐⭐⭐ (Highest)",
                "Veteran Thesis": "ഇന്ത്യയിലെ 70% മ്യൂച്വൽ ഫണ്ടുകളുടെയും ബാക്ക്-എൻഡ് നിയന്ത്രിക്കുന്നു. ആളുകൾ SIP ചെയ്യുന്ന ഓരോ മാസവും CAMS പണം ഉണ്ടാക്കുന്നു."
            },
            {
                "Stock": "HAL (Hindustan Aeronautics)",
                "Moat Type": "പ്രതിരോധ കുത്തക (Monopoly)",
                "ROCE (%)": "31.8%",
                "Debt / Equity": "0.0 (പൂർണ്ണ കടരഹിതം)",
                "AI Disruption Risk": "🟢 പൂജ്യം (AI cannot build jets)",
                "Crash Resilience": "⭐⭐⭐⭐⭐ (Highest)",
                "Veteran Thesis": "ഇന്ത്യൻ വ്യോമസേനയ്ക്ക് ആവശ്യമായ ഫൈറ്റർ ജെറ്റുകളും ഹെലികോപ്റ്ററുകളും നിർമ്മിക്കാൻ മറ്റാർക്കും അനുമതിയില്ല. 10 വർഷത്തെ ഓർഡർ ബുക്ക്."
            },
            {
                "Stock": "ITC Limited",
                "Moat Type": "ഉപഭോക്തൃ കുത്തക (Cash Machine)",
                "ROCE (%)": "39.1%",
                "Debt / Equity": "0.0 (പൂർണ്ണ കടരഹിതം)",
                "AI Disruption Risk": "🟢 പൂജ്യം (Zero Risk)",
                "Crash Resilience": "⭐⭐⭐⭐⭐ (Highest)",
                "Veteran Thesis": "ഭീമമായ ഫ്രീ ക്യാഷ് ഫ്ലോ. മാർക്കറ്റ് തകരുമ്പോഴും 3%-ൽ കൂടുതൽ ഡിവിഡന്റ് നൽകുന്ന സുരക്ഷിത താവളം."
            },
            {
                "Stock": "Sun Pharmaceutical",
                "Moat Type": "ഇലാസ്തികതയില്ലാത്ത ഡിമാൻഡ് (Pharma)",
                "ROCE (%)": "17.8%",
                "Debt / Equity": "0.05 (നെഗ്ലിജിബിൾ)",
                "AI Disruption Risk": "🟢 പൂജ്യം (മരുന്നുകൾ ഫിസിക്കൽ ആണ്)",
                "Crash Resilience": "⭐⭐⭐⭐ (High)",
                "Veteran Thesis": "ആഗോള തലത്തിൽ അസുഖങ്ങൾക്ക് മരുന്ന് കഴിക്കാതിരിക്കാൻ മനുഷ്യർക്ക് കഴിയില്ല. മാർക്കറ്റ് തകർച്ചകളിൽ റെസഷൻ-പ്രൂഫ് ആണ്."
            }
        ]
        st.dataframe(pd.DataFrame(all_weather_stocks), use_container_width=True, hide_index=True)

    with v_tab2:
        st.subheader("⚡ എഐ യുഗത്തിൽ ഡിമാൻഡ് ഇരട്ടിയാകുന്ന വൻകിട കമ്പനികൾ")
        st.markdown("""
        **50-വർഷത്തെ വിദഗ്ദ്ധ നിരീക്ഷണം:**
        * AI സോഫ്റ്റ്‌വെയറുകൾക്ക് പ്രവർത്തിക്കാൻ **അതിഭീമമായ പവറും (Power / Electricity), ഹൈ-വോൾട്ടേജ് ട്രാൻസ്മിഷനും, വൻകിട ഫിസിക്കൽ ഇൻഫ്രാസ്ട്രക്ചറും** വേണം.
        * അതിനാൽ AI കൂടുതൽ വികസിക്കുന്തോറും താഴെ പറയുന്ന കമ്പനികളുടെ ഡിമാൻഡ് കുതിച്ചുയരും:
        """)

        ai_beneficiaries = [
            {
                "Stock": "Power Grid Corp (PGCIL)",
                "Core Moat": "ഇന്ത്യയുടെ പവർ ട്രാൻസ്മിഷൻ കുത്തക (~85% വിപണി)",
                "Why AI Drives Demand?": "AI ഡാറ്റാ സെന്ററുകൾക്ക് 24 മണിക്കൂറും തടസ്സമില്ലാത്ത ഹൈ-വോൾട്ടേജ് വൈദ്യുതി ആവശ്യമാണ്. ഇവ എത്തിക്കാൻ പവർഗ്രിഡ് അല്ലാതെ മറ്റൊരു ബദലില്ല.",
                "Dividend Yield": "3.5%+",
                "Balance Sheet": "സ്ഥിരമായ ക്യാഷ് ഫ്ലോ, സർക്കാർ പിന്തുണ"
            },
            {
                "Stock": "NTPC Limited",
                "Core Moat": "ഇന്ത്യയിലെ ഏറ്റവും വലിയ വൈദ്യുതി ഉൽപ്പാദകൻ",
                "Why AI Drives Demand?": "ക്ലൗഡ് സെർവറുകൾക്ക് ആവശ്യമായ ബേസ്‌ലോഡ് പവറും ഗ്രീൻ ഹൈഡ്രജനും വിതരണം ചെയ്യാൻ ശേഷിയുള്ള ഏക ഭീമൻ.",
                "Dividend Yield": "3.0%+",
                "Balance Sheet": "വലിയ തോതിലുള്ള ഗ്രീൻ എനർജി വിപുലീകരണം"
            },
            {
                "Stock": "Larsen & Toubro (L&T)",
                "Core Moat": "ഇന്ത്യയിലെ ഏറ്റവും വലിയ ഹൈ-ടെക് നിർമ്മാണ കമ്പനി",
                "Why AI Drives Demand?": "ഡാറ്റാ സെന്ററുകൾ, സെമികണ്ടക്ടർ ചിപ്പ് ഫാക്ടറികൾ, ഹൈ-സ്പീഡ് ഇൻഫ്രാസ്ട്രക്ചർ എന്നിവ നിർമ്മിക്കാൻ കഴിവുള്ള ഒരേയൊരു ഇന്ത്യൻ കമ്പനി.",
                "Dividend Yield": "1.2%",
                "Balance Sheet": "₹5 ലക്ഷം കോടിയുടെ കൂറ്റൻ ഓർഡർ ബുക്ക്"
            },
            {
                "Stock": "Bharti Airtel",
                "Core Moat": "ഡിജിറ്റൽ ഡാറ്റാ ഹൈവേ (Telecom Duopoly)",
                "Why AI Drives Demand?": "AI മോഡലുകൾ വഴി വൻതോതിലുള്ള ഡാറ്റ മൊബൈലുകളിലേക്കും സെർവറുകളിലേക്കും കൈമാറാൻ 5G സ്പെക്‌ട്രവും ഒപ്റ്റിക് ഫൈബറും ഉടമസ്ഥതയിലുള്ള ഭീമൻ.",
                "Dividend Yield": "1.0%",
                "Balance Sheet": "സ്ഥിരമായി വർദ്ധിക്കുന്ന പ്രതിമാസ വരുമാനം (ARPU)"
            }
        ]
        st.dataframe(pd.DataFrame(ai_beneficiaries), use_container_width=True, hide_index=True)

    with v_tab3:
        st.subheader("⚠️ എഐ വാല്യൂ ട്രാപ്പ് മുന്നറിയിപ്പ് (The Warning Checklist)")
        st.error("""
        **50-വർഷത്തെ പരിചയമുള്ള ഒരു ഇൻവെസ്റ്ററുടെ മുന്നറിയിപ്പ്: താഴെ പറയുന്ന കമ്പനികൾ എത്ര വില കുറഞ്ഞാലും വാങ്ങരുത്!**
        """)
        st.markdown("""
        1. **❌ ജനറിക് ഐടി ഔട്ട്‌സോഴ്സിംഗ് (Low-End IT / Body Shopping):**
           * അടിസ്ഥാന കോഡിംഗ്, ഡാറ്റ എൻട്രി, ലളിതമായ സോഫ്റ്റ്‌വെയർ മെയിന്റനൻസ് എന്നിവ ചെയ്യുന്ന കമ്പനികൾ AI കാരണം തകരും. ഇവയുടെ P/E 10-ൽ താഴെ വന്നാൽ പോലും അത് വാല്യൂ ട്രാപ്പ് ആണ്.
        2. **❌ വലിയ കടബാധ്യതയുള്ള കമ്പനികൾ (High Debt Businesses):**
           * Debt to Equity > 1.5 ഉള്ള കമ്പനികൾ മാർക്കറ്റ് തകർച്ചയിൽ പലിശ താങ്ങാനാവാതെ പാപ്പരാകും.
        3. **❌ പ്രൈസിംഗ് പവർ ഇല്ലാത്ത ഇടനിലക്കാർ (Commodity Middlemen):**
           * തങ്ങളുടെ ഉൽപ്പന്നത്തിന് സ്വന്തമായി വില നിശ്ചയിക്കാൻ കഴിയാത്ത, മറ്റുള്ളവർ നൽകുന്ന വിലയ്ക്ക് സാധനങ്ങൾ വിൽക്കാൻ നിർബന്ധിതരാകുന്ന കമ്പനികൾ.
        4. **❌ ഫ്രീ ക്യാഷ് ഫ്ലോ ഇല്ലാത്തവ (No Real Cash):**
           * ബാലൻസ് ഷീറ്റിൽ കടലാസ് ലാഭം മാത്രം കാണിച്ച്, ബാങ്ക് അക്കൗണ്ടിൽ യഥാർത്ഥ പണമില്ലാത്ത ബിസിനസ്സുകൾ.
        """)

# ##################################################################
# 📈 വിഭാഗം 3: മികച്ച മ്യൂച്വൽ ഫണ്ടുകൾ (SIP)
# ##################################################################
elif main_menu == "📈 മികച്ച മ്യൂച്വൽ ഫണ്ടുകൾ (SIP)":
    st.title("📈 മികച്ച മ്യൂച്വൽ ഫണ്ടുകൾ (Top Mutual Funds)")
    st.caption("ദീർഘകാലത്തേക്ക് സ്ഥിരതയോടെ കോടികളുടെ വെൽത്ത് സൃഷ്ടിക്കാൻ തെരഞ്ഞെടുത്ത ഫണ്ടുകൾ.")

    mf_category = st.selectbox(
        "നിക്ഷേപ വിഭാഗം തിരഞ്ഞെടുക്കുക:",
        ["🌟 ഫ്ലെക്സി ക്യാപ് ഫണ്ടുകൾ (Flexi Cap - ഏറ്റവും അനുയോജ്യം)", "🛡️ ലാർജ് ക്യാപ് & ഇൻഡെക്സ് ഫണ്ടുകൾ (സുരക്ഷിതമായവ)", "🚀 മിഡ് & സ്മോൾ ക്യാപ് ഫണ്ടുകൾ (ഉയർന്ന റിട്ടേൺ)"]
    )

    if "ഫ്ലെക്സി ക്യാപ്" in mf_category:
        st.subheader("🌟 മികച്ച ഫ്ലെക്സി ക്യാപ് ഫണ്ടുകൾ (Flexi Cap Funds)")
        st.info("💡 ഫണ്ട് മാനേജർക്ക് ലാർജ്, മിഡ്, സ്മോൾ ക്യാപ് ഓഹരികളിൽ എവിടെ വേണമെങ്കിലും അവസരത്തിനൊത്ത് നിക്ഷേപിക്കാനുള്ള സ്വാതന്ത്ര്യമുണ്ട്.")
        funds = [
            {"Fund Name": "Parag Parikh Flexi Cap Fund", "3Y CAGR": "21.5%", "5Y CAGR": "24.2%", "Expense Ratio": "0.62%", "Risk": "മിതമായ റിസ്ക് (Moderate)", "Why Invest?": "വിദേശ ഓഹരികളിലും വാല്യൂ ഓഹരികളിലും മിതത്വത്തോടെയുള്ള നിക്ഷേപം."},
            {"Fund Name": "HDFC Flexi Cap Fund", "3Y CAGR": "25.1%", "5Y CAGR": "22.8%", "Expense Ratio": "0.85%", "Risk": "മിതമായ റിസ്ക് (Moderate)", "Why Invest?": "ഇന്ത്യയിലെ ഏറ്റവും വിശ്വസനീയമായ ഫണ്ട് ഹൗസ്, സ്ഥിരതയാർന്ന ചരിത്രം."},
            {"Fund Name": "JM Flexicap Fund", "3Y CAGR": "32.0%", "5Y CAGR": "26.4%", "Expense Ratio": "0.55%", "Risk": "ഉയർന്ന വളർച്ച (Aggressive)", "Why Invest?": "മൊമെന്റം ഉള്ള വളർച്ചാ ഓഹരികളെ കൃത്യമായി കണ്ടെത്തുന്നു."}
        ]
        st.dataframe(pd.DataFrame(funds), use_container_width=True, hide_index=True)

    elif "ലാർജ് ക്യാപ്" in mf_category:
        st.subheader("🛡️ ലാർജ് ക്യാപ് & ഇൻഡെക്സ് ഫണ്ടുകൾ (Large Cap & Nifty 50)")
        funds = [
            {"Fund Name": "UTI Nifty 50 Index Fund", "3Y CAGR": "15.8%", "5Y CAGR": "16.5%", "Expense Ratio": "0.18%", "Risk": "കുറഞ്ഞ റിസ്ക് (Low)", "Why Invest?": "ഏറ്റവും കുറഞ്ഞ ചിലവ് (0.18%), നിഫ്റ്റി 50 കമ്പനികളുടെ മുഴുവൻ വളർച്ചയും കിട്ടുന്നു."},
            {"Fund Name": "HDFC Top 100 Fund", "3Y CAGR": "21.2%", "5Y CAGR": "18.2%", "Expense Ratio": "0.98%", "Risk": "കുറഞ്ഞ റിസ്ക് (Low)", "Why Invest?": "ഇന്ത്യയിലെ മുൻനിര 100 വൻകിട കമ്പനികളിലെ സുരക്ഷിത നിക്ഷേപം."}
        ]
        st.dataframe(pd.DataFrame(funds), use_container_width=True, hide_index=True)

    else:
        st.subheader("🚀 മിഡ് & സ്മോൾ ക്യാപ് ഫണ്ടുകൾ (Mid & Small Cap Funds)")
        st.warning("⚠️ ശ്രദ്ധിക്കുക: കുറഞ്ഞത് 7 വർഷമെങ്കിലും ഹോൾഡ് ചെയ്യാൻ ഉദ്ദേശിക്കുന്നവർ മാത്രം ഇതിൽ നിക്ഷേപിക്കുക.")
        funds = [
            {"Fund Name": "Quant Small Cap Fund", "3Y CAGR": "34.2%", "5Y CAGR": "38.5%", "Expense Ratio": "0.77%", "Risk": "വളരെ ഉയർന്ന റിസ്ക്", "Why Invest?": "അൽഗോരിതം മോഡൽ ഉപയോഗിച്ച് വിപണിയിലെ ട്രെൻഡുകൾ അതിവേഗം പിടിച്ചെടുക്കുന്നു."},
            {"Fund Name": "Nippon India Small Cap Fund", "3Y CAGR": "30.1%", "5Y CAGR": "32.4%", "Expense Ratio": "0.68%", "Risk": "ഉയർന്ന റിസ്ക്", "Why Invest?": "ഇന്ത്യയിലെ ഏറ്റവും വലിയ സ്മോൾ ക്യാപ് ഫണ്ട്, മികച്ച ഡൈവേഴ്സിഫിക്കേഷൻ."}
        ]
        st.dataframe(pd.DataFrame(funds), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🧮 ദീർഘകാല SIP കാൽക്കുലേറ്റർ (Compounding Power)")
    col_s1, col_s2, col_s3 = st.columns(3)
    sip_amount = col_s1.number_input("പ്രതിമാസ SIP തുക (₹):", value=5000, step=1000)
    sip_years = col_s2.slider("നിക്ഷേപ കാലാവധി (വർഷങ്ങൾ):", min_value=1, max_value=30, value=10)
    sip_rate = col_s3.slider("പ്രതീക്ഷിക്കുന്ന ശരാശരി ലാഭം (% CAGR):", min_value=8, max_value=25, value=15)

    months = sip_years * 12
    monthly_rate = (sip_rate / 100) / 12
    total_invested = sip_amount * months
    future_value = sip_amount * (((1 + monthly_rate)**months - 1) / monthly_rate) * (1 + monthly_rate)
    total_gain = future_value - total_invested

    r1, r2, r3 = st.columns(3)
    r1.metric("ആകെ നിക്ഷേപിച്ച തുക", f"₹{total_invested:,.0f}")
    r2.metric("ലഭിച്ച പലിശ / ലാഭം", f"₹{total_gain:,.0f}")
    r3.metric("🎯 കാലാവധി പൂർത്തിയാകുമ്പോൾ ലഭിക്കുന്ന തുക", f"₹{future_value:,.0f}")

# റൺ ചെയ്യുമ്പോൾ ഓട്ടോ റിഫ്രഷ്
if main_menu == "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്" and state['running']:
    time.sleep(5)
    st.rerun()
