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
        "🏛️ 50-Year Veteran ദീർഘകാല നിക്ഷേപം (1Y, 5Y, 10Y)",
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
# 🏛️ വിഭാഗം 2: 50-Year Veteran ദീർഘകാല നിക്ഷേപം (1Y, 5Y, 10Y Screener)
# ##################################################################
elif main_menu == "🏛️ 50-Year Veteran ദീർഘകാല നിക്ഷേപം (1Y, 5Y, 10Y)":
    st.title("🏛️ 50-Year Veteran ദീർഘകാല നിക്ഷേപ നിലവറ")
    st.caption("കാലാവധിയും (1 Year, 5 Years, 10+ Years) നിക്ഷേപ ശൈലിയും അനുസരിച്ച് ശാസ്ത്രീയമായി ചിട്ടപ്പെടുത്തിയ മാസ്റ്റർ പോർട്ട്ഫോളിയോ.")

    # ഫിൽട്ടറുകൾ
    c_f1, c_f2 = st.columns([1.5, 1.5])
    with c_f1:
        time_horizon = st.radio(
            "⏳ നിങ്ങളുടെ നിക്ഷേപ കാലാവധി തിരഞ്ഞെടുക്കുക:",
            [
                "⏳ 1 വർഷം (Tactical & High Momentum Compounders)",
                "🚀 5 വർഷം (High Growth Multibagger Champions)",
                "🏛️ 10+ വർഷം (Generational Wealth / Coffee Can Monopolies)"
            ]
        )
    with c_f2:
        style_choice = st.radio(
            "🎯 നിക്ഷേപ ശൈലി (Investment Style):",
            [
                "🔥 അതിവേഗ ഗ്രോത്ത് ഓഹരികൾ (High Growth & Sales Expansion)",
                "🛡️ സുരക്ഷിതമായ വാല്യൂ കുത്തകകൾ (Defensive Monopolies & High ROCE)"
            ]
        )

    st.divider()

    # 1. ഒരു വർഷത്തെ പോർട്ട്‌ഫോളിയോ (1-Year Horizon)
    if "1 വർഷം" in time_horizon:
        st.subheader("⏳ 1 വർഷത്തെ നിക്ഷേപത്തിന് ഏറ്റവും അനുയോജ്യമായ ഓഹരികൾ")
        st.info("💡 **വിദഗ്ദ്ധ തത്വം:** 1 വർഷത്തിൽ ബിസിനസ്സ് പൂർണ്ണമായി വളരുന്നതിനേക്കാൾ, ഉയർന്ന ഓർഡറുകളും, ലാഭം 25%-ൽ കൂടുതൽ കുതിച്ചുയരുന്നതുമായ (Quarterly Earnings Momentum) സൈക്ലിക്കൽ കമ്പനികളാണ് ഏറ്റവും കൂടുതൽ റിട്ടേൺ തരുന്നത്.")

        if "അതിവേഗ ഗ്രോത്ത്" in style_choice:
            data_1y_growth = [
                {"Stock": "Zomato / Eternal", "Sector": "Quick Commerce / Food Delivery", "Quarterly Profit Growth": "120%+", "Expected 1Y CAGR": "25% - 35%", "Moat & Catalyst": "Blinkit വഴി ക്വിക്ക് കൊമേഴ്‌സ് വിപണി പിടിച്ചെടുക്കുന്നു. ലാഭക്ഷമത അതിവേഗം കൂടുന്നു."},
                {"Stock": "Varun Beverages (VBL)", "Sector": "FMCG / Beverages", "Quarterly Profit Growth": "28%+", "Expected 1Y CAGR": "20% - 25%", "Moat & Catalyst": "പെപ്സികോയുടെ ആഗോള വിതരണ കുത്തക. ആഫ്രിക്കൻ വിപണിയിലെ അതിവേഗ വിപുലീകരണം."},
                {"Stock": "Tata Power", "Sector": "Energy / EV / Solar", "Quarterly Profit Growth": "30%+", "Expected 1Y CAGR": "20% - 30%", "Moat & Catalyst": "ഇന്ത്യയിലെ ഇലക്ട്രിക് വാഹന ചാർജിംഗ് ശൃംഖല, പുനരുപയോഗ ഊർജ്ജ ഓർഡറുകളുടെ വൻകുതിപ്പ്."},
                {"Stock": "Persistent Systems", "Sector": "IT / Digital Engineering", "Quarterly Profit Growth": "24%+", "Expected 1Y CAGR": "22% - 28%", "Moat & Catalyst": "ജനറേറ്റീവ് AI, ക്ലൗഡ് പ്രൊജക്റ്റുകളിൽ ഏറ്റവും വേഗത്തിൽ ഡീലുകൾ സ്വന്തമാക്കുന്ന ഐടി താരം."},
                {"Stock": "Bharat Forge", "Sector": "Auto Ancillary / Defence", "Quarterly Profit Growth": "35%+", "Expected 1Y CAGR": "20% - 26%", "Moat & Catalyst": "പ്രതിരോധ പീരങ്കികളും, ആഗോള എയ്റോസ്പേസ് പാർട്സുകളും നിർമ്മിക്കുന്നതിലൂടെ വൻ വരുമാനം."}
            ]
            st.dataframe(pd.DataFrame(data_1y_growth), use_container_width=True, hide_index=True)
        else:
            data_1y_value = [
                {"Stock": "Bharat Electronics (BEL)", "Sector": "Defence Electronics", "P/E": 38.0, "ROCE": "28.5%", "Debt/Equity": "0.0", "Expected 1Y CAGR": "18% - 24%", "Moat & Catalyst": "പൂർണ്ണമായും കടരഹിതം. പ്രതിരോധ റഡാറുകളിൽ 70% വിപണി കുത്തക. ബജറ്റ് വിഹിതം വർദ്ധിക്കുന്നു."},
                {"Stock": "State Bank of India (SBIN)", "Sector": "Banking / PSU", "P/E": 11.0, "ROCE": "18.5%", "Debt/Equity": "0.8", "Expected 1Y CAGR": "16% - 22%", "Moat & Catalyst": "ഇന്ത്യയിലെ ഏറ്റവും വലിയ വായ്പാ ദാതാവ്. കുറഞ്ഞ വാല്യുവേഷൻ, സുരക്ഷിതമായ ക്രെഡിറ്റ് വളർച്ച."},
                {"Stock": "Coal India", "Sector": "Energy Mining", "P/E": 8.5, "ROCE": "52.0%", "Debt/Equity": "0.1", "Expected 1Y CAGR": "15% - 20%", "Moat & Catalyst": "5.5%+ ഡിവിഡന്റ് യീൽഡ്. ഇന്ത്യയുടെ വൈദ്യുതി ഉൽപ്പാദനത്തിന് കൽക്കരി അല്ലാതെ മറ്റൊരു ബദലില്ല."},
                {"Stock": "Cummins India", "Sector": "Industrial Engines", "P/E": 39.0, "ROCE": "24.0%", "Debt/Equity": "0.0", "Expected 1Y CAGR": "18% - 25%", "Moat & Catalyst": "ഡാറ്റാ സെന്ററുകൾക്ക് ആവശ്യമായ ജനറേറ്ററുകൾ നൽകുന്ന കുത്തക."}
            ]
            st.dataframe(pd.DataFrame(data_1y_value), use_container_width=True, hide_index=True)

    # 2. അഞ്ചു വർഷത്തെ പോർട്ട്‌ഫോളിയോ (5-Year Horizon)
    elif "5 വർഷം" in time_horizon:
        st.subheader("🚀 5 വർഷത്തെ നിക്ഷേപത്തിന് ഏറ്റവും അനുയോജ്യമായ ഓഹരികൾ")
        st.info("💡 **പീറ്റർ ലിഞ്ച് ശൈലി:** ഇന്ത്യയിലെ ഉപഭോഗ സംസ്കാരം മാറുന്നതിനൊപ്പം വർഷം തോറും 20%-30% വേഗതയിൽ വിറ്റുവരവും ലാഭവും ഇരട്ടിയാക്കാൻ ശേഷിയുള്ള 'ഹൈ-ഗ്രോത്ത് ചാമ്പ്യന്മാർ'.")

        if "അതിവേഗ ഗ്രോത്ത്" in style_choice:
            data_5y_growth = [
                {"Stock": "Trent Ltd (Zudio / Westside)", "Sector": "Retail / Fashion", "3Y Sales CAGR": "48%+", "ROCE": "26.5%", "Expected 5Y CAGR": "28% - 35%", "50-Year Veteran Thesis": "ടാറ്റാ ഗ്രൂപ്പിന്റെ ഏറ്റവും വിജയകരമായ റീട്ടെയിൽ വിപ്ലവം. അതിവേഗ സ്റ്റോർ വിപുലീകരണത്തിലൂടെ ഇന്ത്യയിലെ അൺ-ഓർഗനൈസ്ഡ് തുണി വിപണി പിടിച്ചെടുക്കുന്നു."},
                {"Stock": "Polycab India", "Sector": "Cables & Wires / FMEG", "3Y Sales CAGR": "22%+", "ROCE": "28.5%", "Expected 5Y CAGR": "22% - 28%", "50-Year Veteran Thesis": "ഇന്ത്യയിലെ ഓരോ പുതിയ വീടിനും ഇൻഫ്രാസ്ട്രക്ചറിനും വയറുകൾ നൽകുന്ന 25% വിപണി വിഹിതമുള്ള രാജാവ്. വൻ റീട്ടെയിൽ ശൃംഖല."},
                {"Stock": "Dixon Technologies", "Sector": "Electronics Manufacturing (EMS)", "3Y Sales CAGR": "35%+", "ROCE": "25.0%", "Expected 5Y CAGR": "25% - 32%", "50-Year Veteran Thesis": "ഇന്ത്യയിലെ ഫോക്സ്കോൺ (Foxconn of India). മൊബൈലുകളും ടിവികളും ഇന്ത്യയിൽ നിർമ്മിക്കാൻ സാംസങ്, ഷവോമി അടക്കമുള്ളവർ ഡിക്സണെ ആശ്രയിക്കുന്നു."},
                {"Stock": "Solar Industries", "Sector": "Industrial Explosives / Defence", "3Y Sales CAGR": "30%+", "ROCE": "27.0%", "Expected 5Y CAGR": "24% - 30%", "50-Year Veteran Thesis": "ഖനനത്തിനും മിസൈലുകൾക്കും ആവശ്യമായ സ്ഫോടകവസ്തുക്കളിലെ അന്താരാഷ്ട്ര കുത്തക. വലിയ എൻട്രി ബാരിയർ."},
                {"Stock": "Astral Limited", "Sector": "Building Materials / Pipes", "3Y Sales CAGR": "20%+", "ROCE": "23.0%", "Expected 5Y CAGR": "20% - 25%", "50-Year Veteran Thesis": "പ്ലംബിംഗ് പൈപ്പുകളിലെ പ്രീമിയം ബ്രാൻഡ് പവർ. അഡെസിവുകളിലേക്കും പെയിന്റുകളിലേക്കും ബിസിനസ്സ് വ്യാപിപ്പിക്കുന്നു."}
            ]
            st.dataframe(pd.DataFrame(data_5y_growth), use_container_width=True, hide_index=True)
        else:
            data_5y_value = [
                {"Stock": "Titan Company", "Sector": "Jewellery / Luxury Watches", "3Y Sales CAGR": "24%+", "ROCE": "31.0%", "Expected 5Y CAGR": "18% - 23%", "50-Year Veteran Thesis": "ഇന്ത്യയിലെ സ്വർണ്ണാഭരണ വിപണി തനിഷ്കിലേക്ക് മാറുന്നു. ടാറ്റാ ബ്രാൻഡിലുള്ള അന്ധമായ വിശ്വാസ്യതയാണ് ഇവരുടെ സാമ്പത്തിക കോട്ട."},
                {"Stock": "Hindustan Aeronautics (HAL)", "Sector": "Defence Manufacturing", "3Y Sales CAGR": "12%+", "ROCE": "31.8%", "Expected 5Y CAGR": "20% - 26%", "50-Year Veteran Thesis": "പൂർണ്ണമായും കടരഹിതം. തദ്ദേശീയ ഫൈറ്റർ ജെറ്റുകളുടെയും ഹെലികോപ്റ്ററുകളുടെയും അടുത്ത 8 വർഷത്തെ നിർമ്മാണ ഓർഡറുകൾ ഉറപ്പാണ്."},
                {"Stock": "Larsen & Toubro (L&T)", "Sector": "Infrastructure / Hi-Tech", "3Y Sales CAGR": "18%+", "ROCE": "16.5%", "Expected 5Y CAGR": "17% - 22%", "50-Year Veteran Thesis": "ഇന്ത്യയുടെ ₹100 ലക്ഷം കോടിയുടെ ദേശീയ അടിസ്ഥാന സൗകര്യ വികസനത്തിന്റെ (NIP) ഏറ്റവും വലിയ ഗുണഭോക്താവ്."},
                {"Stock": "Tata Motors", "Sector": "Automobile / EV", "3Y Sales CAGR": "25%+", "ROCE": "19.5%", "Expected 5Y CAGR": "18% - 24%", "50-Year Veteran Thesis": "ഇന്ത്യൻ ഇലക്ട്രിക് പാസഞ്ചർ കാർ വിപണിയുടെ 70% കുത്തക. JLR ആഡംബര കാറുകളുടെ ആഗോള ലാഭം."}
            ]
            st.dataframe(pd.DataFrame(data_5y_value), use_container_width=True, hide_index=True)

    # 3. പത്തു വർഷത്തിലധികം (10+ Years Generational Horizon)
    else:
        st.subheader("🏛️ 10+ വർഷത്തെ തലമുറകൾക്കായുള്ള 'കോഫി കാൻ' (Coffee Can) ഓഹരികൾ")
        st.info("💡 **വാറൻ ബഫറ്റ് ശൈലി:** വാങ്ങിയിട്ട് മറന്നുപോയാലും പണം പല മടങ്ങായി വളരുന്ന, പൂജ്യം കടമുള്ള, എഐ (AI) വിപ്ലവത്തിലും മാർക്കറ്റ് ക്രാഷിലും തകരാത്ത നിത്യഹരിത കുത്തകകൾ.")

        if "അതിവേഗ ഗ്രോത്ത്" in style_choice:
            data_10y_growth = [
                {"Stock": "CDSL", "Sector": "Capital Markets Depository", "10Y Compounding Power": "ഉയർന്ന ഡിമാറ്റ് അക്കൗണ്ട് വളർച്ച", "Debt": "0.0", "ROCE": "33.5%", "Expected 10Y CAGR": "20% - 25%", "Veteran Thesis": "ഇന്ത്യയിൽ 140 കോടി ജനങ്ങളിൽ വെറും 10 കോടി ഡിമാറ്റ് അക്കൗണ്ടുകൾ മാത്രമേ ആയിട്ടുള്ളൂ. അടുത്ത 10 വർഷം കൊണ്ട് ഇത് 3 ഇരട്ടിയാകും. ടോൾ ബൂത്ത് പോലെ ലാഭം."},
                {"Stock": "CAMS", "Sector": "Mutual Fund Registrar", "10Y Compounding Power": "SIP സംസ്കാരത്തിന്റെ വർദ്ധനവ്", "Debt": "0.0", "ROCE": "44.2%", "Expected 10Y CAGR": "18% - 23%", "Veteran Thesis": "ഇന്ത്യൻ മ്യൂച്വൽ ഫണ്ടുകളുടെ 70% ബാക്ക്-എൻഡ് നിയന്ത്രിക്കുന്നു. ഓരോ മാസവും പുതിയ SIP വരുമ്പോഴും CAMS പണം ഉണ്ടാക്കുന്നു."},
                {"Stock": "Bajaj Finance", "Sector": "Consumer Lending / Fintech", "10Y Compounding Power": "ഇന്ത്യയുടെ കൺസംപ്ഷൻ വായ്പകൾ", "Debt": "നിയന്ത്രിതം", "ROCE": "19.5%", "Expected 10Y CAGR": "18% - 22%", "Veteran Thesis": "ഇന്ത്യയിലെ ഏറ്റവും മികച്ച ഡാറ്റാബേസും റിസ്ക് മാനേജ്മെന്റുമുള്ള ബാങ്കിംഗ് ഇതര സ്ഥാപനം."},
                {"Stock": "Tata Consumer Products", "Sector": "FMCG / Essentials", "10Y Compounding Power": "ബ്രാൻഡഡ് പലവ്യഞ്ജനങ്ങൾ", "Debt": "0.1", "ROCE": "14.5%", "Expected 10Y CAGR": "16% - 20%", "Veteran Thesis": "ഉപ്പ്, ചായ, പയർവർഗ്ഗങ്ങൾ തുടങ്ങിയ പാക്കേജ്ഡ് ഭക്ഷണങ്ങളിലെ ടാറ്റാ ബ്രാൻഡ് പവർ."}
            ]
            st.dataframe(pd.DataFrame(data_10y_growth), use_container_width=True, hide_index=True)
        else:
            data_10y_value = [
                {"Stock": "Tata Consultancy Services (TCS)", "Sector": "IT Software", "10Y Compounding Power": "ആഗോള ഡിജിറ്റൽ പരിവർത്തനം", "Debt": "0.0", "ROCE": "58.2%", "Expected 10Y CAGR": "14% - 17%", "Veteran Thesis": "ലോകത്തെ ഏറ്റവും സുരക്ഷിതമായ ഐടി ഭീമൻ. ഭീമമായ ക്യാഷ് ഫ്ലോ. ഡിവിഡന്റും ബോണസും വഴി നിക്ഷേപകരെ ധനികരാക്കുന്ന ചരിത്രം."},
                {"Stock": "ITC Limited", "Sector": "FMCG / Cash Cow", "10Y Compounding Power": "കുത്തക പുകയില & വൻകിട FMCG", "Debt": "0.0", "ROCE": "39.1%", "Expected 10Y CAGR": "15% - 18%", "Veteran Thesis": "പൂർണ്ണമായും കടരഹിതം. മാർക്കറ്റ് തകർന്നാലും ആളുകൾ പുകവലിയും ബിസ്ക്കറ്റ് വാങ്ങലും നിർത്തില്ല. സ്ഥിരമായ 3%+ ഡിവിഡന്റ്."},
                {"Stock": "Asian Paints", "Sector": "Home Improvement", "10Y Compounding Power": "വിതരണ ശൃംഖലയുടെ കുത്തക", "Debt": "0.05", "ROCE": "34.0%", "Expected 10Y CAGR": "15% - 19%", "Veteran Thesis": "ഇന്ത്യയിലെ പെയിന്റ് വിപണിയിൽ 50 വർഷമായി ഒന്നാം സ്ഥാനം. ആർക്കും തകർക്കാനാവാത്ത ഡീലർ ശൃംഖല."},
                {"Stock": "Sun Pharma", "Sector": "Healthcare & Medicine", "10Y Compounding Power": "ജീവൻരക്ഷാ മരുന്നുകൾ", "Debt": "0.05", "ROCE": "17.8%", "Expected 10Y CAGR": "14% - 18%", "Veteran Thesis": "ആഗോള തലത്തിൽ അസുഖങ്ങൾക്ക് മരുന്ന് കഴിക്കാതിരിക്കാൻ മനുഷ്യർക്ക് കഴിയില്ല. പൂർണ്ണമായും സാമ്പത്തിക മാന്ദ്യത്തെ അതിജീവിക്കുന്ന ബിസിനസ്സ്."}
            ]
            st.dataframe(pd.DataFrame(data_10y_value), use_container_width=True, hide_index=True)

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
# 🌙 വിഭാഗം 6: ശരീഅത്ത് & എത്തിക്കൽ നിക്ഷേപം (Halal Wealth Hub)
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
        halal_indian = [
            {"Stock": "Tata Consultancy Services (TCS)", "Sector": "IT Services", "Debt": "0.0", "ROCE (%)": "58.2%", "Shariah Status": "✅ 100% Compliant"},
            {"Stock": "Tata Elxsi", "Sector": "High-Tech Design / EV", "Debt": "0.0", "ROCE (%)": "42.5%", "Shariah Status": "✅ 100% Compliant"},
            {"Stock": "Cipla Limited", "Sector": "Pharmaceuticals", "Debt": "0.02", "ROCE (%)": "24.1%", "Shariah Status": "✅ 100% Compliant"},
            {"Stock": "Asian Paints", "Sector": "Consumer / Paints", "Debt": "0.05", "ROCE (%)": "34.0%", "Shariah Status": "✅ 100% Compliant"},
            {"Stock": "Polycab India", "Sector": "Cables & Wires", "Debt": "0.01", "ROCE (%)": "28.5%", "Shariah Status": "✅ 100% Compliant"}
        ]
        st.dataframe(pd.DataFrame(halal_indian), use_container_width=True, hide_index=True)

    with h_tab2:
        halal_global = [
            {"Company": "Nvidia (NVDA)", "Sector": "AI Computing / Hardware", "Shariah Status": "✅ Compliant"},
            {"Company": "Microsoft (MSFT)", "Sector": "Enterprise Software", "Shariah Status": "✅ Compliant (Filtered)"},
            {"Company": "Alphabet (Google)", "Sector": "Search & Cloud", "Shariah Status": "✅ Compliant"},
            {"Company": "Johnson & Johnson (JNJ)", "Sector": "Healthcare & MedTech", "Shariah Status": "✅ Compliant"}
        ]
        st.dataframe(pd.DataFrame(halal_global), use_container_width=True, hide_index=True)

    with h_tab3:
        st.markdown("""
        1. **❌ ഫ്യൂച്ചേഴ്സ് & ഓപ്ഷൻസ് (F&O / Derivatives) - പൂർണ്ണമായും ഹറാം.**
        2. **❌ ലിവറേജും ഇൻട്രാഡേ ഷോർട്ട് സെല്ലിംഗും - വിലക്കപ്പെട്ടത്.**
        3. **✅ ഡെലിവറി ഇക്വിറ്റി ഇൻവെസ്റ്റ്മെന്റ് (Cash Delivery) - 100% ഹലാൽ.**
        4. **💧 ലാഭ ശുദ്ധീകരണം (Purification):** പലിശ വരുമാനം (5%-ൽ താഴെ) വന്നിട്ടുണ്ടെങ്കിൽ അത് ചാരിറ്റിയിലേക്ക് നൽകണം.
        """)

    with h_tab4:
        ethical_funds = [
            {"Fund Name": "Tata Ethical Fund", "Type": "Shariah Equity Mutual Fund", "3Y CAGR": "20.8%", "5Y CAGR": "22.5%"},
            {"Fund Name": "Taurus Ethical Fund", "Type": "Shariah Equity Mutual Fund", "3Y CAGR": "22.1%", "5Y CAGR": "21.2%"},
            {"Fund Name": "Nippon Gold BeES / HDFC Gold", "Type": "Physical Gold ETF", "Purity": "99.5% 24K Physical Gold"}
        ]
        st.dataframe(pd.DataFrame(ethical_funds), use_container_width=True, hide_index=True)

# റൺ ചെയ്യുമ്പോൾ ഓട്ടോ റിഫ്രഷ്
if main_menu == "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്" and state['running']:
    time.sleep(5)
    st.rerun()
