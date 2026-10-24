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
# 🗄️ ഡാറ്റാബേസ് സെറ്റപ്പ്
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
# 🧭 പ്രധാന നാവിഗേഷൻ മെനു (Separate Hubs)
# ==========================================
st.sidebar.title("🏦 വെൽത്ത് & ട്രേഡിംഗ് ഹബ്")
main_menu = st.sidebar.radio(
    "നിങ്ങൾക്ക് ആവശ്യമുള്ള വിഭാഗം തിരഞ്ഞെടുക്കുക:",
    ["⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്", "💎 ദീർഘകാല ഓഹരികൾ (Value & Growth)", "📈 മികച്ച മ്യൂച്വൽ ഫണ്ടുകൾ (SIP)"]
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
    st.caption("ഇൻട്രാഡേ അവസരങ്ങൾ കണ്ടെത്താനും കർശനമായ റിസ്ക് മാനേജ്മെന്റോടെ ട്രേഡ് ചെയ്യാനുമുള്ള സിസ്റ്റം.")

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

    t1, t2, t3 = st.tabs(["🔍 തത്സമയ ലോഗ്", "📚 ആർക്കൈവ് & ഹിസ്റ്ററി ജേർണൽ", "📜 ട്രേഡുകൾ"])
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
# 💎 വിഭാഗം 2: ദീർഘകാല ഓഹരികൾ (Value & Growth Stock Finder)
# ##################################################################
elif main_menu == "💎 ദീർഘകാല ഓഹരികൾ (Value & Growth)":
    st.title("💎 ദീർഘകാല ഓഹരി നിക്ഷേപം (Long-Term Stocks)")
    st.caption("5 മുതൽ 10 വർഷത്തേക്ക് മികച്ച സമ്പത്തുണ്ടാക്കാൻ സഹായിക്കുന്ന വാല്യൂ, ഗ്രോത്ത് ഓഹരികൾ കണ്ടെത്തുക.")

    stock_type = st.radio("നിങ്ങൾക്ക് താല്പര്യമുള്ള തരം തിരഞ്ഞെടുക്കുക:", ["🏛️ വാല്യൂ ഓഹരികൾ (Value Stocks - വാറൻ ബഫറ്റ് ശൈലി)", "🚀 ഗ്രോത്ത് ഓഹരികൾ (High Growth Stocks)"], horizontal=True)

    if "വാല്യൂ ഓഹരികൾ" in stock_type:
        st.subheader("🏛️ വാല്യൂ ഓഹരികൾ (Undervalued Quality Stocks)")
        st.markdown("""
        **എന്താണ് വാല്യൂ സ്റ്റോക്കുകൾ?**
        ശക്തമായ ഫണ്ടമെന്റലുകൾ ഉള്ളതും, എന്നാൽ മാർക്കറ്റിൽ ന്യായമായ വിലയിൽ (Fair / Cheap Valuation) ലഭിക്കുന്നതുമായ ഓഹരികൾ.
        * **മാനദണ്ഡങ്ങൾ:** P/E < 25, Debt/Equity < 0.5 (കുറഞ്ഞ കടം), ROE > 15%, ഉയർന്ന ലാഭം.
        """)

        value_data = [
            {"Stock": "ITC", "Sector": "FMCG / Tobacco", "P/E": 26.5, "ROE (%)": 29.1, "Debt/Equity": 0.0, "Dividend Yield (%)": 3.2, "Strengths": "പൂർണ്ണമായും കടമില്ലാത്ത കമ്പനി, ഉയർന്ന ക്യാഷ് ഫ്ലോ, മികച്ച ഡിവിഡന്റ്"},
            {"Stock": "State Bank of India (SBIN)", "Sector": "Banking", "P/E": 11.2, "ROE (%)": 18.5, "Debt/Equity": 0.8, "Dividend Yield (%)": 1.6, "Strengths": "ഇന്ത്യയിലെ ഏറ്റവും വലിയ ബാങ്ക്, കുറഞ്ഞ P/E വാല്യുവേഷൻ"},
            {"Stock": "Coal India", "Sector": "Energy / Mining", "P/E": 8.5, "ROE (%)": 52.0, "Debt/Equity": 0.1, "Dividend Yield (%)": 5.8, "Strengths": "ഏറ്റവും ഉയർന്ന ഡിവിഡന്റ്, സർക്കാരിന്റെ കുത്തക ബിസിനസ്സ്"},
            {"Stock": "Larsen & Toubro (LT)", "Sector": "Infrastructure", "P/E": 32.0, "ROE (%)": 16.2, "Debt/Equity": 0.6, "Dividend Yield (%)": 1.1, "Strengths": "ഇന്ത്യയുടെ വികസനത്തിൽ ഏറ്റവും മുൻനിരയിലുള്ള ഇൻഫ്രാ ഭീമൻ"},
            {"Stock": "HCL Technologies", "Sector": "IT Services", "P/E": 24.1, "ROE (%)": 23.5, "Debt/Equity": 0.1, "Dividend Yield (%)": 3.0, "Strengths": "സ്ഥിരമായ റിട്ടേൺ, മികച്ച ഡിവിഡന്റ്, AI രംഗത്തെ വളർച്ച"}
        ]
        st.dataframe(pd.DataFrame(value_data), use_container_width=True, hide_index=True)

    else:
        st.subheader("🚀 ഗ്രോത്ത് ഓഹരികൾ (High Compounding Stocks)")
        st.markdown("""
        **എന്താണ് ഗ്രോത്ത് സ്റ്റോക്കുകൾ?**
        വർഷം തോറും 15%-25% വേഗതയിൽ വിറ്റുവരവും ലാഭവും വർദ്ധിപ്പിക്കുന്ന, മാർക്കറ്റിന്റെ കുതിപ്പിന് നേതൃത്വം നൽകുന്ന കമ്പനികൾ.
        * **മാനദണ്ഡങ്ങൾ:** 3Y Sales Growth > 15%, 3Y Profit Growth > 20%, ഉയർന്ന വിപണി മേധാവിത്വം (Market Moat).
        """)

        growth_data = [
            {"Stock": "Tata Motors", "Sector": "Automobile / EV", "3Y Profit Growth": "45%+", "Market Moat": "EV വിപണിയിലെ ഒന്നാം സ്ഥാനം, JLR ആഗോള കുതിപ്പ്", "Risk Level": "ഇടത്തരം (Medium)"},
            {"Stock": "Titan Company", "Sector": "Retail / Jewellery", "3Y Profit Growth": "22%+", "Market Moat": "ടാറ്റാ ബ്രാൻഡ് വിശ്വാസ്യത, ജ്വല്ലറി വിപണിയിലെ ആധിപത്യം", "Risk Level": "കുറഞ്ഞ റിസ്ക് (Low)"},
            {"Stock": "Bajaj Finance", "Sector": "NBFC / Fintech", "3Y Profit Growth": "28%+", "Market Moat": "ഇന്ത്യയിലെ ഏറ്റവും വലിയ കൺസ്യൂമർ ഫിനാൻസ് ലെൻഡർ", "Risk Level": "ഇടത്തരം (Medium)"},
            {"Stock": "Trent (Westside / Zudio)", "Sector": "Retail Fashion", "3Y Profit Growth": "50%+", "Market Moat": "Zudio-യുടെ അതിവേഗ സ്റ്റോർ വിപുലീകരണവും അത്യുഗ്രൻ വളർച്ചയും", "Risk Level": "ഉയർന്ന വളർച്ച (High Growth)"},
            {"Stock": "Bharti Airtel", "Sector": "Telecom / 5G", "3Y Profit Growth": "30%+", "Market Moat": "ഡാറ്റാ ഉപയോഗത്തിലെ വർദ്ധനവ്, സ്ഥിരമായ ARPU വളർച്ച", "Risk Level": "കുറഞ്ഞ റിസ്ക് (Low)"}
        ]
        st.dataframe(pd.DataFrame(growth_data), use_container_width=True, hide_index=True)

# ##################################################################
# 📈 വിഭാഗം 3: മികച്ച മ്യൂച്വൽ ഫണ്ടുകൾ (Top Mutual Funds & SIP)
# ##################################################################
elif main_menu == "📈 മികച്ച മ്യൂച്വൽ ഫണ്ടുകൾ (SIP)":
    st.title("📈 മികച്ച മ്യൂച്വൽ ഫണ്ടുകൾ (Top Mutual Funds)")
    st.caption("ടെൻഷനില്ലാതെ മാസ നിക്ഷേപം (SIP) വഴി ദീർഘകാല സമ്പത്ത് സൃഷ്ടിക്കാൻ അനുയോജ്യമായ ഫണ്ടുകൾ.")

    mf_category = st.selectbox(
        "നിക്ഷേപ വിഭാഗം തിരഞ്ഞെടുക്കുക:",
        ["🌟 ഫ്ലെക്സി ക്യാപ് ഫണ്ടുകൾ (Flexi Cap - ഏറ്റവും അനുയോജ്യം)", "🛡️ ലാർജ് ക്യാപ് & ഇൻഡെക്സ് ഫണ്ടുകൾ (സുരക്ഷിതമായവ)", "🚀 മിഡ് & സ്മോൾ ക്യാപ് ഫണ്ടുകൾ (ഉയർന്ന റിട്ടേൺ)"]
    )

    if "ഫ്ലെക്സി ക്യാപ്" in mf_category:
        st.subheader("🌟 മികച്ച ഫ്ലെക്സി ക്യാപ് ഫണ്ടുകൾ (Flexi Cap Funds)")
        st.info("💡 ഫണ്ട് മാനേജർക്ക് ലാർജ്, മിഡ്, സ്മോൾ ക്യാപ് ഓഹരികളിൽ എവിടെ വേണമെങ്കിലും അവസരത്തിനൊത്ത് നിക്ഷേപിക്കാനുള്ള സ്വാതന്ത്ര്യമുണ്ട്. തുടക്കക്കാർക്ക് ഏറ്റവും മികച്ച ചോയ്‌സ് ഇതാണ്.")
        funds = [
            {"Fund Name": "Parag Parikh Flexi Cap Fund", "3Y Return (CAGR)": "21.5%", "5Y Return (CAGR)": "24.2%", "Expense Ratio": "0.62%", "Risk": "മിതമായ റിസ്ക് (Moderate)"},
            {"Fund Name": "HDFC Flexi Cap Fund", "3Y Return (CAGR)": "25.1%", "5Y Return (CAGR)": "22.8%", "Expense Ratio": "0.85%", "Risk": "മിതമായ റിസ്ക് (Moderate)"},
            {"Fund Name": "JM Flexicap Fund", "3Y Return (CAGR)": "32.0%", "5Y Return (CAGR)": "26.4%", "Expense Ratio": "0.55%", "Risk": "ഉയർന്ന വളർച്ച (Aggressive)"}
        ]
        st.dataframe(pd.DataFrame(funds), use_container_width=True, hide_index=True)

    elif "ലാർജ് ക്യാപ്" in mf_category:
        st.subheader("🛡️ ലാർജ് ക്യാപ് & ഇൻഡെക്സ് ഫണ്ടുകൾ (Large Cap & Nifty 50)")
        st.info("💡 ഇന്ത്യയിലെ മുൻനിര 50 വൻകിട കമ്പനികളിൽ നിക്ഷേപിക്കുന്നു. ബാങ്ക് FD-യേക്കാൾ ഉയർന്ന വളർച്ചയും കുറഞ്ഞ റിസ്കും തരുന്നു.")
        funds = [
            {"Fund Name": "UTI Nifty 50 Index Fund", "3Y Return (CAGR)": "15.8%", "5Y Return (CAGR)": "16.5%", "Expense Ratio": "0.18%", "Risk": "കുറഞ്ഞ റിസ്ക് (Low)"},
            {"Fund Name": "HDFC Top 100 Fund", "3Y Return (CAGR)": "21.2%", "5Y Return (CAGR)": "18.2%", "Expense Ratio": "0.98%", "Risk": "കുറഞ്ഞ റിസ്ക് (Low)"},
            {"Fund Name": "ICICI Prudential Bluechip Fund", "3Y Return (CAGR)": "19.5%", "5Y Return (CAGR)": "17.4%", "Expense Ratio": "0.89%", "Risk": "കുറഞ്ഞ റിസ്ക് (Low)"}
        ]
        st.dataframe(pd.DataFrame(funds), use_container_width=True, hide_index=True)

    else:
        st.subheader("🚀 മിഡ് & സ്മോൾ ക്യാപ് ഫണ്ടുകൾ (Mid & Small Cap Funds)")
        st.warning("⚠️ ശ്രദ്ധിക്കുക: ഈ ഫണ്ടുകളിൽ റിസ്ക് കൂടുതലാണ്. കുറഞ്ഞത് 7 വർഷമെങ്കിലും ഹോൾഡ് ചെയ്യാൻ ഉദ്ദേശിക്കുന്നവർ മാത്രം ഇതിൽ നിക്ഷേപിക്കുക.")
        funds = [
            {"Fund Name": "Quant Small Cap Fund", "3Y Return (CAGR)": "34.2%", "5Y Return (CAGR)": "38.5%", "Expense Ratio": "0.77%", "Risk": "വളരെ ഉയർന്ന റിസ്ക് (Very High)"},
            {"Fund Name": "Nippon India Small Cap Fund", "3Y Return (CAGR)": "30.1%", "5Y Return (CAGR)": "32.4%", "Expense Ratio": "0.68%", "Risk": "വളരെ ഉയർന്ന റിസ്ക് (Very High)"},
            {"Fund Name": "Motilal Oswal Midcap Fund", "3Y Return (CAGR)": "36.8%", "5Y Return (CAGR)": "29.2%", "Expense Ratio": "0.65%", "Risk": "ഉയർന്ന റിസ്ക് (High)"}
        ]
        st.dataframe(pd.DataFrame(funds), use_container_width=True, hide_index=True)

    st.markdown("---")
    # 🧮 SIP കാൽക്കുലേറ്റർ
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
