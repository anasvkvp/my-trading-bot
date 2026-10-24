import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import time
import threading
import sqlite3
import yfinance as yf

st.set_page_config(page_title="Complete Global Wealth & Trading Hub", layout="wide", page_icon="🏦")

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
# 🧭 6 പ്രധാന മാസ്റ്റർ ഹബ്ബുകൾ (Navigation)
# ==========================================
st.sidebar.title("🏦 വെൽത്ത് & ട്രേഡിംഗ് ഹബ്")
main_menu = st.sidebar.radio(
    "നിങ്ങൾക്ക് ആവശ്യമുള്ള വിഭാഗം തിരഞ്ഞെടുക്കുക:",
    [
        "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്",
        "🏛️ 50-Year Veteran ഇന്ത്യൻ നിക്ഷേപം",
        "📈 മികച്ച മ്യൂച്വൽ ഫണ്ടുകൾ (SIP)",
        "🌍 ആഗോള നിക്ഷേപം (US & Global Markets)",
        "🥇 ഗോൾഡ്, സിൽവർ & റിയൽ എസ്റ്റേറ്റ് (REITs)",
        "🌙 ശരീഅത്ത് & എത്തിക്കൽ നിക്ഷേപം (Halal Wealth)"
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
# 🏛️ വിഭാഗം 2: 50-Year Veteran ഇന്ത്യൻ നിക്ഷേപം
# ##################################################################
elif main_menu == "🏛️ 50-Year Veteran ഇന്ത്യൻ നിക്ഷേപം":
    st.title("🏛️ 50-Year Veteran ഇന്ത്യൻ വെൽത്ത് നിലവറ")
    st.caption("വാറൻ ബഫറ്റ് ശൈലി: കടമില്ലാത്ത, ശക്തമായ കുത്തകയുള്ള, എഐ (AI) ഭീഷണിയില്ലാത്ത കമ്പനികൾ.")

    v_tab1, v_tab2 = st.tabs(["🛡️ ഓൾ-വെതർ കുത്തകകൾ", "⚡ എഐ യുഗത്തിൽ കുതിക്കുന്നവ"])
    with v_tab1:
        all_weather_stocks = [
            {"Stock": "CDSL", "Moat": "റെഗുലേറ്ററി കുത്തക", "ROCE": "33.5%", "Debt": "0.0", "AI Risk": "🟢 പൂജ്യം", "Resilience": "⭐⭐⭐⭐⭐"},
            {"Stock": "CAMS", "Moat": "ഡാറ്റ കുത്തക", "ROCE": "44.2%", "Debt": "0.0", "AI Risk": "🟢 പൂജ്യം", "Resilience": "⭐⭐⭐⭐⭐"},
            {"Stock": "HAL", "Moat": "പ്രതിരോധ കുത്തക", "ROCE": "31.8%", "Debt": "0.0", "AI Risk": "🟢 പൂജ്യം", "Resilience": "⭐⭐⭐⭐⭐"},
            {"Stock": "ITC Limited", "Moat": "ഉപഭോക്തൃ കുത്തക", "ROCE": "39.1%", "Debt": "0.0", "AI Risk": "🟢 പൂജ്യം", "Resilience": "⭐⭐⭐⭐⭐"},
            {"Stock": "Sun Pharma", "Moat": "ഇലാസ്തികതയില്ലാത്ത ഫാർമ", "ROCE": "17.8%", "Debt": "0.05", "AI Risk": "🟢 പൂജ്യം", "Resilience": "⭐⭐⭐⭐"}
        ]
        st.dataframe(pd.DataFrame(all_weather_stocks), use_container_width=True, hide_index=True)

    with v_tab2:
        ai_beneficiaries = [
            {"Stock": "Power Grid", "Moat": "പവർ ട്രാൻസ്മിഷൻ കുത്തക", "Why AI Drives?": "AI ഡാറ്റാ സെന്ററുകൾക്ക് ഹൈ-വോൾട്ടേജ് പവർ എത്തിക്കാൻ മറ്റൊരു ബദലില്ല.", "Yield": "3.5%+"},
            {"Stock": "NTPC", "Moat": "വൈദ്യുതി ഉൽപ്പാദകൻ", "Why AI Drives?": "സെർവറുകൾക്ക് ആവശ്യമായ ബേസ്‌ലോഡ് പവറും ഗ്രീൻ എനർജിയും നൽകുന്നു.", "Yield": "3.0%+"},
            {"Stock": "L&T", "Moat": "ഹൈ-ടെക് നിർമ്മാണം", "Why AI Drives?": "ഡാറ്റാ സെന്ററുകളും ചിപ്പ് ഫാക്ടറികളും പണിയാൻ കഴിവുള്ള ഏക ഭീമൻ.", "Yield": "1.2%"},
            {"Stock": "Bharti Airtel", "Moat": "ടെലികോം ഡ്യുവോപൊളി", "Why AI Drives?": "5G സ്പെക്‌ട്രവും ഒപ്റ്റിക് ഫൈബറും ഉള്ള സ്ഥാപനം.", "Yield": "1.0%"}
        ]
        st.dataframe(pd.DataFrame(ai_beneficiaries), use_container_width=True, hide_index=True)

# ##################################################################
# 📈 വിഭാഗം 3: മികച്ച മ്യൂച്വൽ ഫണ്ടുകൾ (SIP)
# ##################################################################
elif main_menu == "📈 മികച്ച മ്യൂച്വൽ ഫണ്ടുകൾ (SIP)":
    st.title("📈 മികച്ച മ്യൂച്വൽ ഫണ്ടുകൾ (Top Mutual Funds)")
    st.caption("ദീർഘകാലത്തേക്ക് സ്ഥിരതയോടെ കോടികളുടെ വെൽത്ത് സൃഷ്ടിക്കാൻ തെരഞ്ഞെടുത്ത ഫണ്ടുകൾ.")

    mf_category = st.selectbox("നിക്ഷേപ വിഭാഗം തിരഞ്ഞെടുക്കുക:", ["🌟 ഫ്ലെക്സി ക്യാപ് ഫണ്ടുകൾ", "🛡️ ലാർജ് ക്യാപ് & ഇൻഡെക്സ് ഫണ്ടുകൾ", "🚀 മിഡ് & സ്മോൾ ക്യാപ് ഫണ്ടുകൾ"])
    if "ഫ്ലെക്സി ക്യാപ്" in mf_category:
        funds = [
            {"Fund Name": "Parag Parikh Flexi Cap Fund", "3Y CAGR": "21.5%", "5Y CAGR": "24.2%", "Expense Ratio": "0.62%"},
            {"Fund Name": "HDFC Flexi Cap Fund", "3Y CAGR": "25.1%", "5Y CAGR": "22.8%", "Expense Ratio": "0.85%"},
            {"Fund Name": "JM Flexicap Fund", "3Y CAGR": "32.0%", "5Y CAGR": "26.4%", "Expense Ratio": "0.55%"}
        ]
        st.dataframe(pd.DataFrame(funds), use_container_width=True, hide_index=True)
    elif "ലാർജ് ക്യാപ്" in mf_category:
        funds = [
            {"Fund Name": "UTI Nifty 50 Index Fund", "3Y CAGR": "15.8%", "5Y CAGR": "16.5%", "Expense Ratio": "0.18%"},
            {"Fund Name": "HDFC Top 100 Fund", "3Y CAGR": "21.2%", "5Y CAGR": "18.2%", "Expense Ratio": "0.98%"}
        ]
        st.dataframe(pd.DataFrame(funds), use_container_width=True, hide_index=True)
    else:
        funds = [
            {"Fund Name": "Quant Small Cap Fund", "3Y CAGR": "34.2%", "5Y CAGR": "38.5%", "Expense Ratio": "0.77%"},
            {"Fund Name": "Nippon India Small Cap Fund", "3Y CAGR": "30.1%", "5Y CAGR": "32.4%", "Expense Ratio": "0.68%"}
        ]
        st.dataframe(pd.DataFrame(funds), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🧮 ദീർഘകാല SIP കാൽക്കുലേറ്റർ")
    col_s1, col_s2, col_s3 = st.columns(3)
    sip_amount = col_s1.number_input("പ്രതിമാസ SIP തുക (₹):", value=5000, step=1000)
    sip_years = col_s2.slider("കാലാവധി (വർഷങ്ങൾ):", min_value=1, max_value=30, value=10)
    sip_rate = col_s3.slider("പ്രതീക്ഷിക്കുന്ന ലാഭം (% CAGR):", min_value=8, max_value=25, value=15)
    months = sip_years * 12
    monthly_rate = (sip_rate / 100) / 12
    total_invested = sip_amount * months
    future_value = sip_amount * (((1 + monthly_rate)**months - 1) / monthly_rate) * (1 + monthly_rate)

    r1, r2, r3 = st.columns(3)
    r1.metric("ആകെ നിക്ഷേപം", f"₹{total_invested:,.0f}")
    r2.metric("ലഭിച്ച ലാഭം", f"₹{(future_value - total_invested):,.0f}")
    r3.metric("🎯 കാലാവധി പൂർത്തിയാകുമ്പോൾ", f"₹{future_value:,.0f}")

# ##################################################################
# 🌍 വിഭാഗം 4: ആഗോള നിക്ഷേപം (US & Global Markets)
# ##################################################################
elif main_menu == "🌍 ആഗോള നിക്ഷേപം (US & Global Markets)":
    st.title("🌍 ആഗോള നിക്ഷേപം (US & Global Wealth Hub)")
    st.caption("വാൾസ്ട്രീറ്റ് കുത്തകകൾ, കറൻസി നേട്ടം, നികുതികൾ, നിയമപരമായ മുൻകരുതലുകൾ.")
    st.warning("⚠️ **നിയമപരമായ മുന്നറിയിപ്പ് (RBI LRS):** വിദേശ മാർക്കറ്റുകളിൽ ഇൻട്രാഡേ ട്രേഡിംഗോ ഡെറിവേറ്റീവ്സോ (F&O) ഇന്ത്യക്കാർക്ക് അനുവദനീയമല്ല. എന്നാൽ ദീർഘകാല ഓഹരി നിക്ഷേപവും ഇ.ടി.എഫുകളും (ETFs) 100% നിയമപരമാണ്!")

    g_tab1, g_tab2 = st.tabs(["🇺🇸 വാൾസ്ട്രീറ്റ് കുത്തകകൾ", "💵 ഡോളർ കറൻസി കാൽക്കുലേറ്റർ"])
    with g_tab1:
        us_monopolies = [
            {"Company": "Microsoft (MSFT)", "Moat": "Enterprise & Cloud (Azure, Office 365, OpenAI)", "Market Cap": "$3.1T+"},
            {"Company": "Apple (AAPL)", "Moat": "ബ്രാൻഡ് പവറും 200 കോടി ഉപയോക്താക്കളും", "Market Cap": "$3.4T+"},
            {"Company": "Nvidia (NVDA)", "Moat": "AI കമ്പ്യൂട്ടിംഗ് ചിപ്പുകളിലെ കുത്തക (CUDA എക്കോസിസ്റ്റം)", "Market Cap": "$3.0T+"},
            {"Company": "Alphabet (Google)", "Moat": "തിരച്ചിൽ & വിഡിയോ കുത്തക (Google & YouTube)", "Market Cap": "$2.1T+"},
            {"Company": "Berkshire Hathaway (BRK.B)", "Moat": "വാറൻ ബഫറ്റിന്റെ കോട്ട (Cash & Insurance)", "Market Cap": "$900B+"}
        ]
        st.dataframe(pd.DataFrame(us_monopolies), use_container_width=True, hide_index=True)

    with g_tab2:
        c_col1, c_col2, c_col3 = st.columns(3)
        inv_inr = c_col1.number_input("നിക്ഷേപിക്കുന്ന തുക (INR ₹):", value=100000, step=10000)
        stock_cagr = c_col2.slider("പ്രതീക്ഷിക്കുന്ന യു.എസ് ഓഹരി റിട്ടേൺ (% CAGR):", min_value=8, max_value=25, value=12)
        usd_growth = c_col3.slider("പ്രതീക്ഷിക്കുന്ന ഡോളർ മൂല്യവർദ്ധനവ് (% വർഷം):", min_value=1, max_value=8, value=4)
        inv_period = st.slider("നിക്ഷേപ കാലയളവ് (വർഷങ്ങൾ):", min_value=1, max_value=25, value=10)
        combined_rate = ((1 + (stock_cagr / 100)) * (1 + (usd_growth / 100))) - 1
        final_inr = inv_inr * ((1 + combined_rate) ** inv_period)
        pure_stock_inr = inv_inr * ((1 + (stock_cagr / 100)) ** inv_period)

        f1, f2, f3 = st.columns(3)
        f1.metric("ആകെ നിക്ഷേപം", f"₹{inv_inr:,.0f}")
        f2.metric("ഡോളർ കയറിയതുകൊണ്ട് മാത്രം കിട്ടിയ ലാഭം", f"₹{(final_inr - pure_stock_inr):,.0f}")
        f3.metric("🎯 തിരികെ കിട്ടുന്ന തുക", f"₹{final_inr:,.0f}")

# ##################################################################
# 🥇 വിഭാഗം 5: ഗോൾഡ്, സിൽവർ & റിയൽ എസ്റ്റേറ്റ് (REITs)
# ##################################################################
elif main_menu == "🥇 ഗോൾഡ്, സിൽവർ & റിയൽ എസ്റ്റേറ്റ് (REITs)":
    st.title("🥇 ഗോൾഡ്, സിൽവർ & റിയൽ എസ്റ്റേറ്റ് നിലവറ")
    st.caption("മാർക്കറ്റ് തകർച്ചകളിൽ കവചമാകുന്ന സ്വർണ്ണവും, ഭൂമി വാങ്ങാതെ വാടക വരുമാനം തരുന്ന റിയൽ എസ്റ്റേറ്റും (REITs).")

    gold_tab1, gold_tab2, gold_tab3 = st.tabs(["🥇 ഗോൾഡ് & സിൽവർ ഇ.ടി.എഫുകൾ", "🏢 റിയൽ എസ്റ്റേറ്റ് വാടക വരുമാനം (REITs)", "⚖️ ഓൾ-വെതർ പോർട്ട്ഫോളിയോ റീബാലൻസർ"])
    with gold_tab1:
        st.info("💡 **എന്തുകൊണ്ട് ഗോൾഡ് ഇ.ടി.എഫ്?** പണിക്കൂലിയോ ജിഎസ്ടിയോ ലോക്കർ വാടകയോ ഇല്ലാതെ 99.5% ശുദ്ധമായ 24K സ്വർണ്ണത്തിൽ നിക്ഷേപിക്കാം. 12 മാസം കഴിഞ്ഞാൽ വെറും 12.5% മാത്രമാണ് ലോങ്ങ്-ടേം നികുതി!")
        gold_data = [
            {"Instrument": "Nippon India ETF Gold BeES (GOLDBEES)", "Asset": "Gold", "Expense Ratio": "0.55%", "Liquidity": "⭐⭐⭐⭐⭐"},
            {"Instrument": "HDFC Gold ETF (HDFCGOLD)", "Asset": "Gold", "Expense Ratio": "0.30%", "Liquidity": "⭐⭐⭐⭐"},
            {"Instrument": "Nippon India Silver ETF (SILVERBEES)", "Asset": "Silver", "Expense Ratio": "0.50%", "Liquidity": "⭐⭐⭐⭐⭐"}
        ]
        st.dataframe(pd.DataFrame(gold_data), use_container_width=True, hide_index=True)

    with gold_tab2:
        reit_data = [
            {"REIT Name": "Embassy Office Parks REIT", "Type": "ഐടി പാർക്കുകൾ & ഓഫീസുകൾ", "Dividend Yield (%)": "6.8% - 7.5%", "Top Tenants": "Google, IBM, Microsoft"},
            {"REIT Name": "Nexus Select Trust", "Type": "ഷോപ്പിംഗ് മാളുകൾ", "Dividend Yield (%)": "7.5% - 8.2%", "Top Tenants": "Zara, PVR, Reliance Retail"}
        ]
        st.dataframe(pd.DataFrame(reit_data), use_container_width=True, hide_index=True)

    with gold_tab3:
        total_savings = st.number_input("നിക്ഷേപ തുക (₹):", value=100000, step=10000)
        al1, al2, al3 = st.columns(3)
        al1.metric("🇮🇳 ഇന്ത്യൻ ഓഹരികൾ & MF (40%)", f"₹{(total_savings*0.4):,.0f}")
        al2.metric("🇺🇸 യു.എസ് വാൾസ്ട്രീറ്റ് (20%)", f"₹{(total_savings*0.2):,.0f}")
        al3.metric("🥇 ഗോൾഡ് & സിൽവർ ഇ.ടി.എഫ് (15%)", f"₹{(total_savings*0.15):,.0f}")
        al4, al5 = st.columns(2)
        al4.metric("🏢 റിയൽ എസ്റ്റേറ്റ് REITs (10%)", f"₹{(total_savings*0.1):,.0f}")
        al5.metric("💵 ക്രാഷ് ക്യാഷ് / സേവിങ്സ് (15%)", f"₹{(total_savings*0.15):,.0f}")

# ##################################################################
# 🌙 വിഭാഗം 6: ശരീഅത്ത് & എത്തിക്കൽ നിക്ഷേപം (Halal Wealth Hub) - NEW!
# ##################################################################
elif main_menu == "🌙 ശരീഅത്ത് & എത്തിക്കൽ നിക്ഷേപം (Halal Wealth)":
    st.title("🌙 ശരീഅത്ത് & എത്തിക്കൽ വെൽത്ത് ഹബ് (Halal Investing)")
    st.caption("ഇസ്‌ലാമിക ശരീഅത്ത് നിയമങ്ങൾക്ക് വിധേയമായി, 50-വർഷത്തെ വിദഗ്ദ്ധ തത്വങ്ങൾ പാലിക്കുന്ന ഹലാൽ നിക്ഷേപങ്ങൾ.")

    st.success("✅ **ശരീഅത്ത് തത്വം:** പലിശയില്ലാത്ത (Zero Riba), കടബാധ്യത കുറഞ്ഞ (Debt < 33%), സമൂഹത്തിന് ഹാനികരമല്ലാത്ത ശുദ്ധമായ ബിസിനസ്സുകളിൽ മാത്രം നിക്ഷേപിക്കുക.")

    h_tab1, h_tab2, h_tab3, h_tab4 = st.tabs([
        "🇮🇳 ഇന്ത്യൻ ടോപ്പ് ശരീഅത്ത് ഓഹരികൾ",
        "🇺🇸 ആഗോള ഹലാൽ ഓഹരികൾ",
        "📜 ഇസ്‌ലാമിക നിയമങ്ങളും ട്രേഡിംഗ് വിധികളും",
        "🕋 എത്തിക്കൽ ഫണ്ടുകൾ & ഗോൾഡ്"
    ])

    with h_tab1:
        st.subheader("🇮🇳 ഇന്ത്യയിലെ ഏറ്റവും മികച്ച ശരീഅത്ത് ഓഹരികൾ (Nifty Shariah)")
        st.markdown("""
        **50-വർഷത്തെ വിദഗ്ദ്ധ ഫിൽട്ടർ:**
        പൂർണ്ണമായും കടരഹിതമായ, ഉയർന്ന ROCE ഉള്ള, ഇസ്‌ലാമിക പണ്ഡിതന്മാരുടെ നിരീക്ഷണത്തിലുള്ള കമ്പനികൾ:
        """)

        halal_indian = [
            {"Stock": "Tata Consultancy Services (TCS)", "Sector": "IT Services", "Debt": "0.0 (കടരഹിതം)", "ROCE (%)": "58.2%", "Shariah Status": "✅ 100% Compliant", "Why Invest?": "ഇന്ത്യയിലെ ഏറ്റവും വലിയ ഐടി കമ്പനി, ഭീമമായ ക്യാഷ് ഫ്ലോ, ഉയർന്ന ഡിവിഡന്റ്."},
            {"Stock": "Tata Elxsi", "Sector": "High-Tech Design / EV", "Debt": "0.0 (കടരഹിതം)", "ROCE (%)": "42.5%", "Shariah Status": "✅ 100% Compliant", "Why Invest?": "ഇലക്ട്രിക് വാഹന സോഫ്റ്റ്‌വെയറിലും AI ഡിസൈനിലും വിപണി മേധാവിത്വം."},
            {"Stock": "Cipla Limited", "Sector": "Pharmaceuticals", "Debt": "0.02 (നെഗ്ലിജിബിൾ)", "ROCE (%)": "24.1%", "Shariah Status": "✅ 100% Compliant", "Why Invest?": "ആഗോള തലത്തിൽ ജീവൻരക്ഷാ മരുന്നുകൾ നിർമ്മിക്കുന്ന വിശ്വസനീയ കമ്പനി."},
            {"Stock": "Asian Paints", "Sector": "Consumer / Paints", "Debt": "0.05", "ROCE (%)": "34.0%", "Shariah Status": "✅ 100% Compliant", "Why Invest?": "ഇന്ത്യയിലെ പെയിന്റ് വിപണിയുടെ 50% കൈയ്യാളുന്ന അത്യുഗ്രൻ കുത്തക."},
            {"Stock": "Polycab India", "Sector": "Cables & Wires", "Debt": "0.01", "ROCE (%)": "28.5%", "Shariah Status": "✅ 100% Compliant", "Why Invest?": "ഇന്ത്യയുടെ വികസനത്തിൽ വീടുകൾക്കും ഇൻഫ്രാസ്ട്രക്ചറിനും കേബിളുകൾ നൽകുന്ന ഭീമൻ."}
        ]
        st.dataframe(pd.DataFrame(halal_indian), use_container_width=True, hide_index=True)

    with h_tab2:
        st.subheader("🇺🇸 ആഗോള ഹലാൽ വമ്പന്മാർ (Global Halal Monopolies)")
        st.markdown("""
        ആഗോള ഇസ്‌ലാമിക ഇ.ടി.എഫുകളായ **SPUS**, **HLAL** എന്നിവയിൽ മുൻനിരയിൽ നിൽക്കുന്ന കടബാധ്യത കുറഞ്ഞ ആഗോള ഭീമന്മാർ:
        """)

        halal_global = [
            {"Company": "Nvidia (NVDA)", "Sector": "AI Computing / Hardware", "Shariah Status": "✅ Compliant", "Moat": "AI കമ്പ്യൂട്ടിംഗ് ചിപ്പുകളിലെ ആഗോള കുത്തക. പലിശ വരുമാനമില്ലാത്ത ശുദ്ധമായ ഹാർഡ്‌വെയർ ബിസിനസ്സ്."},
            {"Company": "Microsoft (MSFT)", "Sector": "Enterprise Software", "Shariah Status": "✅ Compliant (Filtered)", "Moat": "ലോകത്തെ എല്ലാ ഓഫീസുകളും പ്രവർത്തിക്കുന്ന സോഫ്റ്റ്‌വെയർ ശൃംഖല."},
            {"Company": "Alphabet (Google)", "Sector": "Search & Cloud", "Shariah Status": "✅ Compliant", "Moat": "സൗജന്യ അറിവും യൂട്യൂബും വഴി പരസ്യ വരുമാനം നേടുന്ന കുത്തക."},
            {"Company": "Johnson & Johnson (JNJ)", "Sector": "Healthcare & MedTech", "Shariah Status": "✅ Compliant", "Moat": "ആഗോള ആരോഗ്യ സംരക്ഷണ വിപണിയിലെ അതികായന്മാർ."}
        ]
        st.dataframe(pd.DataFrame(halal_global), use_container_width=True, hide_index=True)

    with h_tab3:
        st.subheader("📜 ഇസ്‌ലാമിക വിധികൾ: ട്രേഡിംഗ് vs ഇൻവെസ്റ്റ്മെന്റ്")
        st.markdown("""
        **ആഗോള ഇസ്‌ലാമിക പണ്ഡിത സഭകളുടെ (AAOIFI, OIC Fiqh Academy) വ്യക്തമായ വിധികൾ:**

        1. **❌ ഫ്യൂച്ചേഴ്സ് & ഓപ്ഷൻസ് (F&O / Derivatives) - പൂർണ്ണമായും ഹറാം:**
           * കയ്യിലില്ലാത്തത് വിൽക്കൽ (Gharar), അമിതമായ ഊഹക്കച്ചവടവും ചൂതാട്ടവും (Qimar) വരുന്നതിനാൽ ഡെറിവേറ്റീവ്സ് ഇസ്‌ലാമിൽ അനുവദനീയമല്ല.
        2. **❌ ലിവറേജും ഇൻട്രാഡേ ഷോർട്ട് സെല്ലിംഗും - വിലക്കപ്പെട്ടത്:**
           * ബ്രോക്കറുടെ കയ്യിൽ നിന്ന് കടമെടുത്ത് (Leverage) വ്യാപാരം ചെയ്യുന്നതും, കയ്യിലില്ലാത്ത ഓഹരികൾ വിൽക്കുന്നതും (Short Selling) അനുവദനീയമല്ല.
        3. **✅ ഡെലിവറി ഇക്വിറ്റി ഇൻവെസ്റ്റ്മെന്റ് (Cash Delivery) - 100% ഹലാൽ:**
           * സ്വന്തം പണം നൽകി ഒരു കമ്പനിയുടെ ഓഹരികൾ വാങ്ങി, അത് ഡിമാറ്റ് അക്കൗണ്ടിൽ ഉടമസ്ഥാവകാശം (Qabd) നേടി ലാഭത്തിലോ നഷ്ടത്തിലോ പങ്കാളിയാകുന്നത് പൂർണ്ണമായും അനുവദനീയമാണ്.
        4. **💧 ലാഭ ശുദ്ധീകരണം (Purification):**
           * കമ്പനിയുടെ പക്കൽ ബാങ്ക് ഡിപ്പോസിറ്റുകളിൽ നിന്നുള്ള ചെറിയ പലിശ വരുമാനം (5%-ൽ താഴെ) വന്നിട്ടുണ്ടെങ്കിൽ, ആ അനുപാതത്തിലുള്ള തുക സ്വന്തം ആവശ്യങ്ങൾക്ക് ഉപയോഗിക്കാതെ പാവങ്ങൾക്ക് ദാനം ചെയ്യണം.
        """)

    with h_tab4:
        st.subheader("🕋 ഇന്ത്യയിലെ ശരീഅത്ത് മ്യൂച്വൽ ഫണ്ടുകളും ഗോൾഡും")
        st.markdown("""
        ടെൻഷനില്ലാതെ മാസം തോറും (SIP) ഹലാൽ രീതിയിൽ നിക്ഷേപിക്കാൻ പറ്റിയ ലൈസൻസുള്ള ഇന്ത്യൻ ഫണ്ടുകൾ:
        """)

        ethical_funds = [
            {"Fund Name": "Tata Ethical Fund", "Type": "Shariah Equity Mutual Fund", "3Y CAGR": "20.8%", "5Y CAGR": "22.5%", "Shariah Board": "ശരീഅത്ത് സമിതിയുടെ നിരന്തര മേൽനോട്ടം", "Details": "ഇന്ത്യയിലെ ഏറ്റവും പഴയതും വലുതുമായ ശരീഅത്ത് ഫണ്ട്. പലിശ ബാങ്കുകളിലോ മദ്യ കമ്പനികളിലോ നിക്ഷേപിക്കില്ല."},
            {"Fund Name": "Taurus Ethical Fund", "Type": "Shariah Equity Mutual Fund", "3Y CAGR": "22.1%", "5Y CAGR": "21.2%", "Shariah Board": "S&P BSE 500 Shariah ഇൻഡക്സ് ട്രാക്കിംഗ്", "Details": "കർശനമായ ഇസ്‌ലാമിക ഫിൽട്ടറിംഗ് നടത്തുന്ന പ്യുവർ ഇക്വിറ്റി ഫണ്ട്."},
            {"Fund Name": "Nippon Gold BeES / HDFC Gold", "Type": "Physical Gold ETF", "Purity": "99.5% 24K Physical Gold", "AAOIFI Standard": "സ്റ്റാൻഡേർഡ് 57 പ്രകാരം അനുവദനീയം", "Details": "100% യഥാർത്ഥ സ്വർണ്ണം ലോക്കറുകളിൽ സൂക്ഷിച്ചിട്ടുള്ളതിനാൽ പേപ്പർ ഗോൾഡ് പോലെയല്ല, അനുവദനീയമാണ്."}
        ]
        st.dataframe(pd.DataFrame(ethical_funds), use_container_width=True, hide_index=True)

# റൺ ചെയ്യുമ്പോൾ ഓട്ടോ റിഫ്രഷ്
if main_menu == "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്" and state['running']:
    time.sleep(5)
    st.rerun()
