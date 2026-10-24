import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import time
import threading
import sqlite3
import urllib.parse
import hashlib
import yfinance as yf

st.set_page_config(page_title="Autonomous Wealth OS & Algo Bot", layout="wide", page_icon="🏛️")

# ==========================================
# 🔑 URL-ൽ വരുന്ന Upstox കോഡ് ഉടൻ പിടിച്ചെടുക്കുന്നു (പാസ്‌കീക്ക് മുൻപേ!)
# ==========================================
if "pending_auth_code" not in st.session_state:
    st.session_state["pending_auth_code"] = ""

if "code" in st.query_params:
    st.session_state["pending_auth_code"] = st.query_params["code"]

# ==========================================
# 🗄️ മൾട്ടി-യൂസർ പ്രൈവറ്റ് ഡാറ്റാബേസ് സെറ്റപ്പ്
# ==========================================
DB_NAME = "trading_journal_v3.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_hash TEXT, date TEXT, time TEXT, symbol TEXT, price REAL,
                        vwap REAL, rsi REAL, vol_surge TEXT, ema_cross TEXT,
                        nifty_trend TEXT, status TEXT, reason TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_hash TEXT, date TEXT, time TEXT, symbol TEXT, type TEXT,
                        buy_price REAL, sell_price REAL, qty INTEGER, pnl REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS wealth_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_hash TEXT, date TEXT, asset TEXT, category TEXT, action TEXT,
                        status TEXT, veteran_reason TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS manual_portfolio (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_hash TEXT, symbol TEXT, qty REAL, buy_price REAL, buy_date TEXT, notes TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_settings (
                        user_hash TEXT PRIMARY KEY, api_key TEXT, api_secret TEXT,
                        redirect_uri TEXT, tg_token TEXT, tg_chat TEXT)''')
        conn.commit()
        conn.close()
    except Exception:
        pass

init_db()

def save_user_creds(u_hash, api_k, api_s, red_u, tg_t, tg_c):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO user_settings (user_hash, api_key, api_secret, redirect_uri, tg_token, tg_chat)
                     VALUES (?, ?, ?, ?, ?, ?)''', (u_hash, api_k, api_s, red_u, tg_t, tg_c))
        conn.commit()
        conn.close()
    except Exception:
        pass

def load_user_creds(u_hash):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT api_key, api_secret, redirect_uri, tg_token, tg_chat FROM user_settings WHERE user_hash=?", (u_hash,))
        row = c.fetchone()
        conn.close()
        if row:
            return {'api_key': row[0], 'api_secret': row[1], 'redirect_uri': row[2], 'tg_token': row[3], 'tg_chat': row[4]}
    except Exception:
        pass
    return None

# ==========================================
# 🔐 സ്വകാര്യ യൂസർ ലോക്കർ (Multi-User Isolation)
# ==========================================
@st.cache_resource
def get_user_vault():
    return {}

user_vault = get_user_vault()

st.sidebar.markdown("# 🏛️ WEALTH OS")

if st.session_state["pending_auth_code"]:
    st.sidebar.success(f"✅ Upstox കോഡ് ലഭിച്ചു (`{st.session_state['pending_auth_code']}`)! താഴെ നിങ്ങളുടെ പാസ്‌കീ നൽകുക.")

user_passkey = st.sidebar.text_input(
    "🔐 നിങ്ങളുടെ സ്വകാര്യ പാസ്‌കീ (Secret ID):",
    type="password",
    help="നിങ്ങളുടെ ഡാറ്റയും ബോട്ടും മറ്റാരും കാണാതിരിക്കാൻ നിങ്ങൾക്ക് മാത്രം അറിയാവുന്ന ഒരു രഹസ്യ വാക്ക്/നമ്പർ നൽകുക."
)

if not user_passkey:
    if st.session_state["pending_auth_code"]:
        st.info(f"🔑 **Upstox ലോഗിൻ കോഡ് ലഭിച്ചു (`{st.session_state['pending_auth_code']}`)!** ടോക്കൺ ഓട്ടോമാറ്റിക് ആയി ജനറേറ്റ് ചെയ്യാൻ ഇടതുവശത്തെ സൈഡ്‌ബാറിൽ നിങ്ങളുടെ **സ്വകാര്യ പാസ്‌കീ (Secret ID)** നൽകുക.")
    else:
        st.warning("🔒 **സ്വകാര്യതയും സുരക്ഷയും (100% Data Privacy):** ഈ ആപ്പ് ഉപയോഗിക്കാൻ ഇടതുവശത്തെ സൈഡ്‌ബാറിൽ നിങ്ങൾക്ക് ഇഷ്ടമുള്ള ഒരു **രഹസ്യ പാസ്‌കീ (Secret ID)** നൽകുക. നിങ്ങളുടെ ടോക്കണുകളും ട്രേഡുകളും പോർട്ട്ഫോളിയോയും ആ പാസ്‌കീ നൽകുമ്പോൾ മാത്രമേ ദൃശ്യമാകൂ.")
    st.stop()

USER_HASH = hashlib.sha256(user_passkey.strip().encode()).hexdigest()[:16]

if USER_HASH not in user_vault:
    saved_c = load_user_creds(USER_HASH) or {}
    user_vault[USER_HASH] = {
        'running': False, 'token': '', 'capital': 5000.0, 'risk': 100.0,
        'mode': 'പേപ്പർ ട്രേഡിംഗ് (സുരക്ഷിതം)',
        'tg_token': saved_c.get('tg_token', ''), 'tg_chat': saved_c.get('tg_chat', ''),
        'thread': None, 'consecutive_losses': 0, 'kill_switch': False,
        'nifty_status': 'പരിശോധിക്കുന്നു...', 'active_pos': None,
        'shariah_lock': False, 'last_order_error': '',
        'api_key': saved_c.get('api_key', ''),
        'api_secret': saved_c.get('api_secret', ''),
        'redirect_uri': saved_c.get('redirect_uri', 'https://my-trading-bot-wyjcnfn2bprzd4ysp8riie.streamlit.app')
    }

state = user_vault[USER_HASH]

# ==========================================
# ⚡ ഓട്ടോമാറ്റിക് ടോക്കൺ എക്സ്ചേഞ്ച് ഫങ്ക്ഷൻ
# ==========================================
def exchange_code_for_token(auth_code, api_k, api_s, red_u):
    token_url = "https://api.upstox.com/v2/login/authorization/token"
    headers = {'accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {
        'code': auth_code.strip(),
        'client_id': api_k.strip(),
        'client_secret': api_s.strip(),
        'redirect_uri': red_u.strip(),
        'grant_type': 'authorization_code'
    }
    try:
        res = requests.post(token_url, headers=headers, data=payload, timeout=10)
        res_data = res.json()
        if res.status_code == 200 and 'access_token' in res_data:
            return True, res_data['access_token']
        else:
            err_detail = res_data.get('errors', [{}])[0].get('message', str(res_data))
            return False, err_detail
    except Exception as e:
        return False, str(e)

# URL-ൽ കോഡ് വന്നിട്ടുണ്ടെങ്കിൽ തനിയെ ടോക്കൺ ആക്കി മാറ്റുന്നു!
if st.session_state["pending_auth_code"] and state.get('api_key') and state.get('api_secret'):
    code_to_use = st.session_state["pending_auth_code"]
    st.session_state["pending_auth_code"] = ""
    st.query_params.clear()
    ok, result = exchange_code_for_token(code_to_use, state['api_key'], state['api_secret'], state['redirect_uri'])
    if ok:
        state['token'] = result
        st.toast("🎉 Upstox Access Token ഓട്ടോമാറ്റിക് ആയി ജനറേറ്റ് ചെയ്തു!", icon="✅")
    else:
        st.sidebar.error(f"Auto-Token Error: {result}")

# ==========================================
# 👑 മാസ്റ്റർ ഗ്ലോബൽ സ്വിച്ച്
# ==========================================
wealth_mode = st.sidebar.radio(
    "നിക്ഷേപ തത്ത്വശാസ്ത്രം (Philosophy):",
    ["🌐 ആഗോള ജനറൽ മോഡ് (Global Conventional)", "🌙 100% പ്യുവർ ശരീഅത്ത് മോഡ് (Pure Halal AAOIFI)"]
)
is_shariah = "ശരീഅത്ത്" in wealth_mode
state['shariah_lock'] = is_shariah

st.sidebar.markdown("---")
main_menu = st.sidebar.radio(
    "പ്രധാന വിഭാഗം തിരഞ്ഞെടുക്കുക:",
    [
        "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട് (Active Algo Engine)",
        "🎯 ലക്ഷ്യാധിഷ്ഠിത പോർട്ട്ഫോളിയോ (Goal Engine)",
        "💼 എന്റെ ലൈവ് പോർട്ട്ഫോളിയോ & എക്സിറ്റ് വാച്ച്ഡോഗ്",
        "🏛️ 50-Year Veteran സ്റ്റോക്ക് നിലവറ (Why Buy & Exit Rules)",
        "📈 മ്യൂച്വൽ ഫണ്ടുകൾ & ഇ.ടി.എഫുകൾ",
        "🌍 ആഗോള വിപണികൾ (US & Currency Advisor)",
        "🥇 ഗോൾഡ് & സുരക്ഷിത ആസ്തികൾ",
        "📚 അഡ്വൈസറി ജേർണൽ & ചേഞ്ച് ലോഗ്"
    ]
)

WATCHLIST_CONVENTIONAL = {
    'SBIN': 'NSE_EQ|INE062A01020',
    'RELIANCE': 'NSE_EQ|INE002A01018',
    'BHARTIARTL': 'NSE_EQ|INE397D01024',
    'LT': 'NSE_EQ|INE018A01030'
}

WATCHLIST_SHARIAH = {
    'TCS': 'NSE_EQ|INE467B01029',
    'INFY': 'NSE_EQ|INE009A01021',
    'SUNPHARMA': 'NSE_EQ|INE044A01036',
    'RELIANCE': 'NSE_EQ|INE002A01018'
}

NIFTY_KEY = 'NSE_INDEX|Nifty 50'

# ##################################################################
# ⚡ വിഭാഗം 1: ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്
# ##################################################################
if main_menu == "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട് (Active Algo Engine)":
    st.title("⚡ Upstox ഇൻസ്റ്റിറ്റ്യൂഷണൽ ഇൻട്രാഡേ ബോട്ട്")
    st.caption("Private Multi-User Engine + Auto OAuth Token + Nifty Guard + 3:15 PM Auto Square-off.")

    if is_shariah:
        st.warning("🌙 **ശരീഅത്ത് വാച്ച്‌ലിസ്റ്റ് ആക്ടീവ്:** ബാങ്കിംഗ് ഓഹരികൾ (SBIN) ഒഴിവാക്കി TCS, INFY, SUNPHARMA, RELIANCE എന്നിവ മാത്രമാണ് സ്കാൻ ചെയ്യുന്നത്.")

    if state['token']:
        st.success("✅ **Upstox Access Token റെഡിയാണ്!** ഇനി ഇടതുവശത്തെ സൈഡ്‌ബാറിൽ **▶️ START BOT** അമർത്താം.")

    with st.expander("🔑 ഓട്ടോമാറ്റിക് ടോക്കൺ ജനറേറ്റർ (Upstox 1-Click Auto Login)", expanded=not bool(state['token'])):
        st.caption("നിങ്ങളുടെ API Key-യും Secret-ഉം ഒരു തവണ നൽകി സേവ് ചെയ്താൽ, ദിവസവും ഒറ്റ ക്ലിക്കിൽ ടോക്കൺ ഓട്ടോമാറ്റിക് ആയി എടുക്കാം.")
        oa1, oa2, oa3 = st.columns(3)
        api_k = oa1.text_input("Upstox API Key:", value=state['api_key'], type="password")
        api_s = oa2.text_input("Upstox API Secret:", value=state['api_secret'], type="password")
        red_u = oa3.text_input("Redirect URL (നിങ്ങളുടെ ഈ ആപ്പ് ലിങ്ക്):", value=state['redirect_uri'])

        if api_k != state['api_key'] or api_s != state['api_secret'] or red_u != state['redirect_uri']:
            state['api_key'], state['api_secret'], state['redirect_uri'] = api_k.strip(), api_s.strip(), red_u.strip()
            save_user_creds(USER_HASH, state['api_key'], state['api_secret'], state['redirect_uri'], state['tg_token'], state['tg_chat'])

        if state['api_key'] and state['api_secret'] and state['redirect_uri']:
            encoded_redir = urllib.parse.quote(state['redirect_uri'], safe='')
            auth_url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={state['api_key']}&redirect_uri={encoded_redir}"
            
            # ഒരേ ടാബിൽ തന്നെ തുറക്കാൻ സഹായിക്കുന്ന ലിങ്ക് ബട്ടൺ
            st.markdown(f'<a href="{auth_url}" target="_self" style="display:inline-block;padding:10px 20px;background-color:#FF4B4B;color:white;text-decoration:none;border-radius:8px;font-weight:bold;">🚀 ഇവിടെ ക്ലിക്ക് ചെയ്ത് Upstox-ൽ നിന്ന് ഓട്ടോമാറ്റിക് ടോക്കൺ എടുക്കുക</a>', unsafe_allow_html=True)
            st.caption("💡 മുകളിലെ ചുവന്ന ബട്ടണിൽ ക്ലിക്ക് ചെയ്യുമ്പോൾ Upstox ലോഗിൻ വഴി തിരിച്ച് ഈ പേജിലേക്ക് തന്നെ വരികയും, നിങ്ങളുടെ പാസ്‌കീ നൽകുമ്പോൾ ടോക്കൺ തനിയെ സേവ് ആവുകയും ചെയ്യും!")

            with st.form("manual_code_form"):
                manual_code = st.text_input("അല്ലെങ്കിൽ URL-ൽ വരുന്ന 'code=' (അല്ലെങ്കിൽ മുഴുവൻ URL-ഉം) ഇവിടെ പേസ്റ്റ് ചെയ്യുക:", value=st.session_state.get("pending_auth_code", ""))
                submitted = st.form_submit_button("⚡ Generate Token Now")
                if submitted and manual_code:
                    clean_code = manual_code.strip()
                    if "code=" in clean_code:
                        clean_code = clean_code.split("code=")[-1].split("&")[0]
                    ok, res_msg = exchange_code_for_token(clean_code, state['api_key'], state['api_secret'], state['redirect_uri'])
                    if ok:
                        state['token'] = res_msg
                        st.session_state["pending_auth_code"] = ""
                        st.success("🎉 ടോക്കൺ ഓട്ടോമാറ്റിക് ആയി ജനറേറ്റ് ചെയ്ത് സൈഡ്‌ബാറിൽ സേവ് ചെയ്തു!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ Upstox Error: {res_msg}")

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ ബോട്ട് കൺട്രോൾ പാനൽ")
    mode_input = st.sidebar.radio("ട്രേഡിംഗ് മോഡ്:", ["പേപ്പർ ട്രേഡിംഗ് (സുരക്ഷിതം)", "ലൈവ് റിയൽ മണി"], index=0 if "പേപ്പർ" in state['mode'] else 1)
    token_input = st.sidebar.text_input("Upstox Access Token:", value=state['token'], type="password")
    capital_input = st.sidebar.number_input("ക്യാപിറ്റൽ (₹):", value=float(state['capital']), min_value=500.0, step=500.0)
    risk_input = st.sidebar.number_input("ഒരു ട്രേഡിലെ റിസ്ക് (₹):", value=float(state['risk']), min_value=10.0, step=25.0)

    tg_token_input = st.sidebar.text_input("Telegram Bot Token (Optional):", value=state['tg_token'], type="password")
    tg_chat_input = st.sidebar.text_input("Telegram Chat ID (Optional):", value=state['tg_chat'])

    def send_telegram(msg, tg_t, tg_c):
        if tg_t and tg_c:
            try:
                requests.post(f"https://api.telegram.org/bot{tg_t}/sendMessage", json={"chat_id": tg_c, "text": msg, "parse_mode": "Markdown"}, timeout=5)
            except Exception:
                pass

    def place_real_order(symbol, instrument_key, qty, action, token, u_state):
        if "ലൈവ് റിയൽ" in u_state['mode']:
            try:
                url = 'https://api-hft.upstox.com/v2/order/place'
                headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
                order_data = {
                    "quantity": int(qty), "product": "I", "validity": "DAY", "price": 0,
                    "tag": "WealthOS", "instrument_token": instrument_key,
                    "order_type": "MARKET", "transaction_type": action,
                    "disclosed_quantity": 0, "trigger_price": 0, "is_amo": False
                }
                res = requests.post(url, headers=headers, json=order_data, timeout=7)
                res_json = res.json()
                if res.status_code == 200 and res_json.get('status') == 'success':
                    u_state['last_order_error'] = ''
                    return True
                else:
                    err_msg = res_json.get('errors', [{}])[0].get('message', 'Unknown Order Error')
                    u_state['last_order_error'] = f"Order Failed ({symbol}): {err_msg}"
                    send_telegram(f"⚠️ *ഓർഡർ പരാജയപ്പെട്ടു ({symbol}):* `{err_msg}`", u_state['tg_token'], u_state['tg_chat'])
                    return False
            except Exception as e:
                u_state['last_order_error'] = f"Order Error: {str(e)}"
                return False
        return True

    def fetch_candles(instrument_key, token):
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token}'}
        encoded_key = urllib.parse.quote(instrument_key, safe='')
        try:
            res = requests.get(f"https://api.upstox.com/v2/historical-candle/intraday/{encoded_key}/1minute", headers=headers, timeout=10)
            data = res.json()
            if data.get('status') == 'success' and 'candles' in data.get('data', {}):
                candles = data['data']['candles']
                if len(candles) > 0:
                    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
                    return df.iloc[::-1].reset_index(drop=True)
        except Exception:
            pass
        return None

    def check_nifty_bullish(token, u_state):
        df = fetch_candles(NIFTY_KEY, token)
        if df is not None and len(df) >= 20:
            close = df['close'].astype(float)
            ema_20 = close.ewm(span=20, adjust=False).mean()
            is_bullish = close.iloc[-1] >= ema_20.iloc[-1]
            u_state['nifty_status'] = "🟢 ബുള്ളിഷ് (Positive)" if is_bullish else "🔴 ബെയറിഷ് (Negative)"
            return is_bullish
        u_state['nifty_status'] = "⚠️ ഡാറ്റ ലഭ്യമല്ല (Waiting)"
        return False

    def calculate_indicators(df):
        close = df['close'].astype(float)
        volume = df['volume'].astype(float)
        high = df['high'].astype(float)
        low = df['low'].astype(float)
        df['EMA_Fast'] = close.ewm(span=9, adjust=False).mean()
        df['EMA_Slow'] = close.ewm(span=21, adjust=False).mean()
        df['Vol_SMA'] = volume.rolling(window=20).mean()
        vol_cumsum = volume.cumsum().replace(0, np.nan)
        df['VWAP'] = (((high + low + close) / 3) * volume).cumsum() / vol_cumsum
        
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['RSI'] = (100 - (100 / (1 + rs))).fillna(50.0)
        
        tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(window=14).mean()
        return df

    def log_trade(u_hash, date_s, time_s, sym, t_type, bp, sp, qty, pnl):
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("INSERT INTO trades (user_hash, date, time, symbol, type, buy_price, sell_price, qty, pnl) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (u_hash, date_s, time_s, sym, t_type, round(bp, 2), round(sp, 2), int(qty), round(pnl, 2)))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def background_trading_loop(u_hash, u_state):
        while u_state['running']:
            token = u_state['token']
            if not token:
                time.sleep(5)
                continue

            ist_zone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            now_ist = datetime.datetime.now(ist_zone)
            curr_time_obj = now_ist.time()

            market_entry_start = datetime.time(9, 20)
            market_entry_cutoff = datetime.time(15, 5)
            market_close_time = datetime.time(15, 15)

            if curr_time_obj >= market_close_time:
                if u_state['active_pos']:
                    pos = u_state['active_pos']
                    df_cur = fetch_candles(pos['key'], token)
                    exit_p = float(df_cur['close'].iloc[-1]) if (df_cur is not None and len(df_cur) > 0) else pos['buy_price']
                    if place_real_order(pos['symbol'], pos['key'], pos['qty'], "SELL", token, u_state):
                        pnl = (exit_p - pos['buy_price']) * pos['qty']
                        log_trade(u_hash, now_ist.strftime("%Y-%m-%d"), now_ist.strftime("%I:%M:%S %p"), pos['symbol'], "AUTO_315_EXIT", pos['buy_price'], exit_p, pos['qty'], pnl)
                        send_telegram(f"⏰ *3:15 PM ഓട്ടോ സ്ക്വയർ-ഓഫ്:* `{pos['symbol']}` ക്ലോസ് ചെയ്തു. PnL: `₹{pnl:.2f}`", u_state['tg_token'], u_state['tg_chat'])
                        u_state['active_pos'] = None
                u_state['nifty_status'] = "🌙 മാർക്കറ്റ് ക്ലോസ് ആയി (After 3:15 PM)"
                time.sleep(15)
                continue

            if u_state['consecutive_losses'] >= 2:
                u_state['kill_switch'] = True
                u_state['running'] = False
                send_telegram("🛑 *കിൽ സ്വിച്ച് ആക്റ്റീവ് ആയി!* തുടർച്ചയായി 2 നഷ്ടങ്ങൾ വന്നതിനാൽ ട്രേഡിംഗ് പൂർണ്ണമായി നിർത്തി.", u_state['tg_token'], u_state['tg_chat'])
                break

            if u_state['active_pos']:
                pos = u_state['active_pos']
                df_cur = fetch_candles(pos['key'], token)
                if df_cur is not None and len(df_cur) > 0:
                    cur_p = float(df_cur['close'].iloc[-1])
                    elapsed_mins = (time.time() - pos['entry_time']) / 60.0

                    if elapsed_mins >= 45 and (abs(cur_p - pos['buy_price']) / pos['buy_price']) < 0.005:
                        if place_real_order(pos['symbol'], pos['key'], pos['qty'], "SELL", token, u_state):
                            pnl = (cur_p - pos['buy_price']) * pos['qty']
                            log_trade(u_hash, now_ist.strftime("%Y-%m-%d"), now_ist.strftime("%I:%M:%S %p"), pos['symbol'], "TIME_EXIT_45M", pos['buy_price'], cur_p, pos['qty'], pnl)
                            send_telegram(f"⏳ *45m Stale Momentum Exit:* `{pos['symbol']}` ഒഴിവാക്കി. PnL: `₹{pnl:.2f}`", u_state['tg_token'], u_state['tg_chat'])
                            u_state['active_pos'] = None
                    elif cur_p >= pos['target']:
                        if place_real_order(pos['symbol'], pos['key'], pos['qty'], "SELL", token, u_state):
                            pnl = (cur_p - pos['buy_price']) * pos['qty']
                            log_trade(u_hash, now_ist.strftime("%Y-%m-%d"), now_ist.strftime("%I:%M:%S %p"), pos['symbol'], "TARGET_HIT", pos['buy_price'], cur_p, pos['qty'], pnl)
                            send_telegram(f"🎉 *TARGET HIT:* `{pos['symbol']}` ലാഭം: `+₹{pnl:.2f}`", u_state['tg_token'], u_state['tg_chat'])
                            u_state['consecutive_losses'] = 0
                            u_state['active_pos'] = None
                    elif cur_p <= pos['sl']:
                        if place_real_order(pos['symbol'], pos['key'], pos['qty'], "SELL", token, u_state):
                            pnl = (cur_p - pos['buy_price']) * pos['qty']
                            log_trade(u_hash, now_ist.strftime("%Y-%m-%d"), now_ist.strftime("%I:%M:%S %p"), pos['symbol'], "STOP_LOSS", pos['buy_price'], cur_p, pos['qty'], pnl)
                            send_telegram(f"🛑 *STOP LOSS HIT:* `{pos['symbol']}` നഷ്ടം: `₹{pnl:.2f}`", u_state['tg_token'], u_state['tg_chat'])
                            u_state['consecutive_losses'] += 1
                            u_state['active_pos'] = None

            is_weekday = now_ist.weekday() < 5
            is_trading_window = is_weekday and (market_entry_start <= curr_time_obj <= market_entry_cutoff)

            if not is_trading_window:
                if not is_weekday:
                    u_state['nifty_status'] = "📅 അവധി ദിവസമാണ് (Weekend)"
                elif curr_time_obj < market_entry_start:
                    u_state['nifty_status'] = "⏳ 9:20 AM ആകാൻ കാത്തിരിക്കുന്നു..."
                time.sleep(10)
                continue

            nifty_ok = check_nifty_bullish(token, u_state)
            active_watchlist = WATCHLIST_SHARIAH if u_state['shariah_lock'] else WATCHLIST_CONVENTIONAL

            if u_state['active_pos'] is None:
                for symbol, instrument_key in active_watchlist.items():
                    if not u_state['running'] or u_state['active_pos'] is not None:
                        break
                    df = fetch_candles(instrument_key, token)
                    if df is None or len(df) < 30:
                        continue

                    df = calculate_indicators(df)
                    curr, prev = df.iloc[-1], df.iloc[-2]
                    curr_price = float(curr['close'])
                    vol_avg = float(curr['Vol_SMA']) if not np.isnan(curr['Vol_SMA']) else 0
                    vwap = float(curr['VWAP']) if not np.isnan(curr['VWAP']) else curr_price
                    rsi = float(curr['RSI'])
                    atr = float(curr['ATR']) if (not np.isnan(curr['ATR']) and curr['ATR'] > 0) else (curr_price * 0.01)

                    ema_cross = (prev['EMA_Fast'] <= prev['EMA_Slow']) and (curr['EMA_Fast'] > curr['EMA_Slow'])
                    rsi_safe = 50 <= rsi <= 68
                    above_vwap = curr_price > vwap
                    volume_surge = float(curr['volume']) >= (1.2 * vol_avg) if vol_avg > 0 else True

                    curr_date = now_ist.strftime("%Y-%m-%d")
                    curr_time = now_ist.strftime("%I:%M:%S %p")

                    if not nifty_ok:
                        reason, status = "നിഫ്റ്റി ഇൻഡക്സ് ബുള്ളിഷ് അല്ല", "SKIPPED_NIFTY"
                    elif not above_vwap:
                        reason, status = "VWAP-ക്ക് താഴെയാണ് (Bearish)", "SKIPPED"
                    elif not volume_surge:
                        reason, status = "വോളിയം കുറവാണ്", "SKIPPED"
                    elif not rsi_safe:
                        reason, status = f"RSI അനുകൂലമല്ല ({rsi:.1f})", "SKIPPED"
                    elif not ema_cross:
                        reason, status = "EMA ക്രോസ് ആയിട്ടില്ല", "WAITING"
                    else:
                        sl_dist = max(0.5, 1.5 * atr)
                        sl_p = curr_price - sl_dist
                        tg_p = curr_price + (3.0 * atr)
                        
                        risk_based_qty = int(u_state['risk'] // sl_dist)
                        max_affordable_qty = int(u_state['capital'] // curr_price)
                        qty = max(1, min(risk_based_qty, max_affordable_qty))

                        if curr_price > u_state['capital']:
                            reason, status = f"ക്യാപിറ്റൽ തികയില്ല (വില: ₹{curr_price:.0f})", "SKIPPED_CAP"
                        elif place_real_order(symbol, instrument_key, qty, "BUY", token, u_state):
                            u_state['active_pos'] = {
                                'symbol': symbol, 'key': instrument_key, 'buy_price': curr_price,
                                'qty': qty, 'sl': sl_p, 'target': tg_p, 'entry_time': time.time()
                            }
                            reason, status = f"വാങ്ങി (Qty: {qty})", "🎯 BUY TRIGGERED"
                            send_telegram(f"🚀 *BUY എടുത്തു:* `{symbol}` (Qty: {qty}) @ ₹{curr_price:.2f} | Target: ₹{tg_p:.2f} | SL: ₹{sl_p:.2f}", u_state['tg_token'], u_state['tg_chat'])
                        else:
                            reason, status = "ബ്രോക്കർ ഓർഡർ തള്ളി", "ORDER_FAILED"

                    try:
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute('''INSERT INTO audit_logs (user_hash, date, time, symbol, price, vwap, rsi, vol_surge, ema_cross, nifty_trend, status, reason)
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                  (u_hash, curr_date, curr_time, symbol, round(curr_price, 2), round(vwap, 2), round(rsi, 1),
                                   "Yes" if volume_surge else "No", "Yes" if ema_cross else "No", u_state['nifty_status'], status, reason))
                        conn.commit()
                        conn.close()
                    except Exception:
                        pass

                    if u_state['active_pos'] is not None:
                        break

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
            save_user_creds(USER_HASH, state['api_key'], state['api_secret'], state['redirect_uri'], state['tg_token'], state['tg_chat'])
            state['running'] = True
            state['kill_switch'] = False
            state['consecutive_losses'] = 0
            if state['thread'] is None or not state['thread'].is_alive():
                t = threading.Thread(target=background_trading_loop, args=(USER_HASH, state), daemon=True)
                t.start()
                state['thread'] = t
            st.sidebar.success("നിങ്ങളുടെ സ്വകാര്യ ബോട്ട് സജീവം!")

    if col2.button("⏹️ STOP BOT", use_container_width=True):
        state['running'] = False
        st.sidebar.warning("ബോട്ട് നിർത്തി!")

    if state['last_order_error']:
        st.error(f"🚨 ബ്രോക്കർ മുന്നറിയിപ്പ്: {state['last_order_error']}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ബോട്ട് സ്റ്റാറ്റസ്", "🟢 സർവറിൽ ഓടുന്നു" if state['running'] else ("🛑 കിൽ സ്വിച്ച് ഓഫ്" if state['kill_switch'] else "🔴 ഓഫ് ആണ്"))
    m2.metric("നിഫ്റ്റി 50 ട്രെൻഡ്", state['nifty_status'])
    m3.metric("തുടർച്ചയായ നഷ്ടങ്ങൾ", f"{state['consecutive_losses']} / 2")
    m4.metric("ക്യാപിറ്റൽ", f"₹{state['capital']:,.2f}")

    if state['active_pos']:
        ap = state['active_pos']
        st.success(f"📌 **നിലവിലെ ലൈവ് ട്രേഡ്:** `{ap['symbol']}` | എണ്ണം: `{ap['qty']}` | വാങ്ങിയ വില: `₹{ap['buy_price']:.2f}` | ടാർജറ്റ്: `₹{ap['target']:.2f}` | സ്റ്റോപ്പ്-ലോസ്: `₹{ap['sl']:.2f}`")

    st.divider()

    t1, t2 = st.tabs(["🔍 എന്റെ ലൈവ് സ്കാനിംഗ് ലോഗ്", "📜 എന്റെ പൂർത്തിയായ ട്രേഡുകൾ"])
    with t1:
        try:
            conn = get_db_connection()
            today_str = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")
            df_live = pd.read_sql_query("SELECT time AS Time, symbol AS Stock, price AS Price, vwap AS VWAP, rsi AS RSI, nifty_trend AS [Nifty Sentiment], status AS Status, reason AS Reason FROM audit_logs WHERE user_hash=? AND date=? ORDER BY id DESC LIMIT 50", conn, params=(USER_HASH, today_str))
            conn.close()
            if not df_live.empty:
                st.dataframe(df_live, use_container_width=True, hide_index=True)
            else:
                st.info("സ്കാനിംഗ് ഡാറ്റ വരാൻ കാത്തിരിക്കുന്നു (മാർക്കറ്റ് സമയം: 9:20 AM - 3:15 PM)...")
        except Exception:
            st.info("സ്കാനിംഗ് ഡാറ്റ വരാൻ കാത്തിരിക്കുന്നു...")

    with t2:
        try:
            conn = get_db_connection()
            df_tr = pd.read_sql_query("SELECT date AS Date, time AS Time, symbol AS Stock, type AS Action, qty AS Qty, buy_price AS [Buy Price], sell_price AS [Sell Price], pnl AS PnL FROM trades WHERE user_hash=? ORDER BY id DESC", conn, params=(USER_HASH,))
            conn.close()
            if not df_tr.empty:
                st.dataframe(df_tr, use_container_width=True, hide_index=True)
            else:
                st.info("ഇതുവരെ ട്രേഡുകൾ ഒന്നും നടന്നിട്ടില്ല.")
        except Exception:
            st.info("ട്രേഡുകൾ ഒന്നും നടന്നിട്ടില്ല.")

    if state['running']:
        if st.button("🔄 സ്റ്റാറ്റസ് റിഫ്രഷ് ചെയ്യുക"):
            st.rerun()

# ##################################################################
# 🎯 വിഭാഗം 2: ലക്ഷ്യാധിഷ്ഠിത പോർട്ട്ഫോളിയോ
# ##################################################################
elif main_menu == "🎯 ലക്ഷ്യാധിഷ്ഠിത പോർട്ട്ഫോളിയോ (Goal Engine)":
    st.title("🎯 ലക്ഷ്യാധിഷ്ഠിത വെൽത്ത് കാൽക്കുലേറ്റർ")
    st.caption("കാലാവധിയും വിപണി സാഹചര്യവും അനുസരിച്ച് പണം വിന്യസിക്കുക.")

    if is_shariah:
        st.success("🌙 **100% ശരീഅത്ത് മോഡ് സജീവം:** പലിശ ബാങ്കുകളോ, നോൺ-ഹലാൽ കടപത്രങ്ങളോ ഇല്ലാതെ പൂർണ്ണമായും ശുദ്ധമായ ഹലാൽ അസറ്റുകൾ മാത്രം ഉൾപ്പെടുത്തിയിരിക്കുന്നു.")

    c1, c2, c3 = st.columns(3)
    inv_type = c1.selectbox("നിക്ഷേപ രീതി:", ["പ്രതിമാസ നിക്ഷേപം (Monthly SIP)", "ഒറ്റത്തവണ നിക്ഷേപം (Lump-sum)"])
    inv_amount = c2.number_input("നിക്ഷേപിക്കുന്ന തുക (₹):", value=10000.0, step=1000.0)
    goal_horizon = c3.selectbox(
        "നിക്ഷേപ കാലാവധിയും ലക്ഷ്യവും:",
        [
            "⏳ 1 വർഷം (ഹ്രസ്വകാല അത്യാവശ്യ ഫണ്ട് / ലിക്വിഡിറ്റി)",
            "🚀 3 - 5 വർഷം (ഇടത്തരം വളർച്ച / ബിസിനസ്സ് / വീട്)",
            "🏛️ 10+ വർഷം (ദീർഘകാല സാമ്പത്തിക സ്വാതന്ത്ര്യം / വിരമിക്കൽ)"
        ]
    )

    st.markdown("---")
    st.subheader("🛡️ മാക്രോ മാർക്കറ്റ് & യുദ്ധ സാഹചര്യം (Market Climate Sentinel)")
    market_climate = st.selectbox(
        "നിലവിലെ വിപണി സാഹചര്യം വിലയിരുത്തുക:",
        [
            "🟢 ശാന്തമായ വിപണി (Normal Bull / Steady Growth)",
            "⚠️ അസ്ഥിരതയും യുദ്ധ ഭീഷണിയും / എണ്ണവില വർദ്ധനവ് (War / High Oil / Volatility)",
            "🔴 വിപണിയിലെ കടുത്ത തകർച്ച (Blood on the Streets / Extreme Crash)"
        ]
    )

    if "1 വർഷം" in goal_horizon:
        if is_shariah: eq_pct, gold_pct, cash_pct, reit_pct = 0.15, 0.35, 0.50, 0.0
        else: eq_pct, gold_pct, cash_pct, reit_pct = 0.15, 0.25, 0.50, 0.10
        rec_text = "1 വർഷത്തെ ഹ്രസ്വകാലത്തേക്ക് ഇക്വിറ്റി റിസ്ക് കുറയ്ക്കണം. ലിക്വിഡ് കാഷിലും സ്വർണ്ണത്തിലും മുൻഗണന."
    elif "3 - 5 വർഷം" in goal_horizon:
        if "യുദ്ധ" in market_climate: eq_pct, gold_pct, cash_pct, reit_pct = 0.40, 0.30 if is_shariah else 0.25, 0.30 if is_shariah else 0.25, (0.0 if is_shariah else 0.10)
        else: eq_pct, gold_pct, cash_pct, reit_pct = 0.60, 0.20 if is_shariah else 0.15, 0.20 if is_shariah else 0.15, (0.0 if is_shariah else 0.10)
        rec_text = "ഇടത്തരം കാലാവധിയിൽ ഹൈ-ഗ്രോത്ത് കമ്പനികൾക്കും എത്തിക്കൽ ഫണ്ടുകൾക്കും മുൻഗണന."
    else:
        if "തകർച്ച" in market_climate: eq_pct, gold_pct, cash_pct, reit_pct = 0.75, 0.15, 0.10, 0.0
        else: eq_pct, gold_pct, cash_pct, reit_pct = 0.70 if is_shariah else 0.65, 0.20 if is_shariah else 0.15, 0.10, (0.0 if is_shariah else 0.10)
        rec_text = "ദീർഘകാലത്തേക്ക് അൺബ്രേക്കബിൾ കുത്തകകളിൽ പണം കോമ്പൗണ്ട് ചെയ്യാൻ അനുവദിക്കുക."

    st.info(f"💡 **വിദഗ്ദ്ധന്റെ നിർദ്ദേശം:** {rec_text}")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("ഇക്വിറ്റി ഓഹരികൾ", f"₹{(inv_amount * eq_pct):,.0f}", f"{int(eq_pct*100)}%")
    a2.metric("ഗോൾഡ് & സിൽവർ", f"₹{(inv_amount * gold_pct):,.0f}", f"{int(gold_pct*100)}%")
    a3.metric("ക്യാഷ് / കറന്റ് അക്കൗണ്ട്", f"₹{(inv_amount * cash_pct):,.0f}", f"{int(cash_pct*100)}%")
    if not is_shariah: a4.metric("റിയൽ എസ്റ്റേറ്റ് REITs", f"₹{(inv_amount * reit_pct):,.0f}", f"{int(reit_pct*100)}%")
    else: a4.metric("ശരീഅത്ത് പാലിക്കൽ", "100% Halal", "AAOIFI")

# ##################################################################
# 💼 വിഭാഗം 3: എന്റെ ലൈവ് പോർട്ട്ഫോളിയോ & എക്സിറ്റ് വാച്ച്ഡോഗ്
# ##################################################################
elif main_menu == "💼 എന്റെ ലൈവ് പോർട്ട്ഫോളിയോ & എക്സിറ്റ് വാച്ച്ഡോഗ്":
    st.title("💼 എന്റെ സ്വകാര്യ പോർട്ട്ഫോളിയോ & എക്സിറ്റ് വാച്ച്ഡോഗ്")
    st.caption("നിങ്ങളുടെ പാസ്‌കീയിൽ മാത്രം ദൃശ്യമാകുന്ന സ്വകാര്യ പോർട്ട്ഫോളിയോ.")

    h_tab1, h_tab2 = st.tabs(["⚡ Upstox ലൈവ് ഹോൾഡിംഗ്സ് (Auto Sync)", "📝 എന്റെ മാനുവൽ പോർട്ട്ഫോളിയോ (Groww / Zerodha)"])

    with h_tab1:
        st.subheader("⚡ Upstox-ൽ നിലവിലുള്ള ഓഹരികൾ (Demat Holdings)")
        user_token = st.sidebar.text_input("പോർട്ട്ഫോളിയോ കാണാൻ Upstox Token:", value=state['token'], type="password", key="holdings_token")

        if st.button("🔄 Upstox-ൽ നിന്ന് പോർട്ട്ഫോളിയോ എടുക്കുക"):
            if not user_token:
                st.error("സൈഡ്‌ബാറിൽ Upstox Access Token നൽകുക!")
            else:
                with st.spinner("⏳ Upstox ഡിമാറ്റിൽ നിന്ന് ഓഹരികൾ സിങ്ക് ചെയ്യുന്നു..."):
                    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {user_token}'}
                    try:
                        res = requests.get('https://api.upstox.com/v2/portfolio/long-term-holdings', headers=headers, timeout=10)
                        data = res.json()
                        if data.get('status') == 'success' and 'data' in data:
                            holdings = data['data']
                            if len(holdings) > 0:
                                parsed_h = []
                                total_val = 0.0
                                total_pnl = 0.0
                                for h in holdings:
                                    sym = h.get('trading_symbol', 'N/A')
                                    qty = h.get('quantity', 0)
                                    avg_p = h.get('average_price', 0.0)
                                    cur_p = h.get('last_price', 0.0)
                                    pnl = h.get('pnl', 0.0)
                                    total_val += (cur_p * qty)
                                    total_pnl += pnl

                                    pnl_pct = ((cur_p - avg_p) / avg_p * 100) if avg_p > 0 else 0
                                    if pnl_pct < -10.0: sentinel_status = "🚨 എക്സിറ്റ് മുന്നറിയിപ്പ് (Stop-Loss / Review)"
                                    elif pnl_pct > 20.0: sentinel_status = "🟢 മികച്ച ലാഭത്തിൽ (Hold / Trail SL)"
                                    else: sentinel_status = "🟡 സാധാരണ നിലയിൽ (Hold)"

                                    parsed_h.append({
                                        'Stock': sym, 'Quantity': qty, 'Avg Buy Price': round(avg_p, 2),
                                        'Current Price': round(cur_p, 2), 'Total P&L (₹)': round(pnl, 2),
                                        'P&L (%)': f"{round(pnl_pct, 1)}%", 'Watchdog Status': sentinel_status
                                    })

                                hc1, hc2 = st.columns(2)
                                hc1.metric("ആകെ പോർട്ട്ഫോളിയോ മൂല്യം", f"₹{total_val:,.2f}")
                                hc2.metric("ആകെ ലാഭം / നഷ്ടം", f"₹{total_pnl:,.2f}", delta=f"₹{total_pnl:,.2f}")
                                st.dataframe(pd.DataFrame(parsed_h), use_container_width=True, hide_index=True)
                            else:
                                st.info("നിങ്ങളുടെ Upstox അക്കൗണ്ടിൽ നിലവിൽ ഹോൾഡിംഗ്സുകൾ ഒന്നും കണ്ടെത്തിയില്ല.")
                        else:
                            st.warning("Upstox കണക്റ്റിവിറ്റിയിൽ തടസ്സം. ടോക്കൺ കാലാവധി കഴിഞ്ഞിട്ടുണ്ടാകാം.")
                    except Exception as e:
                        st.error(f"ഡാറ്റ ലഭിക്കുന്നതിൽ തടസ്സം: {e}")

    with h_tab2:
        st.subheader("📝 മറ്റ് ആപ്പുകളിൽ വാങ്ങിയ ഓഹരികൾ രേഖപ്പെടുത്തുക")
        col_m1, col_m2, col_m3 = st.columns(3)
        m_sym = col_m1.text_input("സ്റ്റോക്ക് സിംബൽ (ഉദാ: CDSL, TCS):").upper().strip()
        m_qty = col_m2.number_input("വാങ്ങിയ എണ്ണം (Qty):", value=1, min_value=1, step=1)
        m_bp = col_m3.number_input("വാങ്ങിയ വില (₹):", value=100.0, min_value=1.0, step=10.0)

        if st.button("➕ എന്റെ പോർട്ട്ഫോളിയോയിലേക്ക് ചേർക്കുക"):
            if m_sym:
                try:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO manual_portfolio (user_hash, symbol, qty, buy_price, buy_date, notes) VALUES (?, ?, ?, ?, ?, ?)",
                              (USER_HASH, m_sym, m_qty, m_bp, datetime.date.today().strftime("%Y-%m-%d"), "Manual Entry"))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ {m_sym} നിങ്ങളുടെ സ്വകാര്യ പോർട്ട്ഫോളിയോയിൽ ചേർത്തു!")
                except Exception as e:
                    st.error(f"സേവ് ചെയ്യുന്നതിൽ തടസ്സം: {e}")

        st.markdown("---")
        try:
            conn = get_db_connection()
            df_man = pd.read_sql_query("SELECT symbol AS Stock, qty AS Qty, buy_price AS [Buy Price], buy_date AS [Bought Date] FROM manual_portfolio WHERE user_hash=? ORDER BY id DESC", conn, params=(USER_HASH,))
            conn.close()
            if not df_man.empty:
                st.dataframe(df_man, use_container_width=True, hide_index=True)
            else:
                st.info("നിങ്ങളുടെ പാസ്‌കീയിൽ ഇതുവരെ മാനുവൽ ഓഹരികൾ ചേർത്തിട്ടില്ല.")
        except Exception:
            st.info("ഡാറ്റ ലഭ്യമായിട്ടില്ല.")

# ##################################################################
# 🏛️ വിഭാഗം 4: 50-Year Veteran സ്റ്റോക്ക് നിലവറ
# ##################################################################
elif main_menu == "🏛️ 50-Year Veteran സ്റ്റോക്ക് നിലവറ (Why Buy & Exit Rules)":
    st.title("🏛️ 50-Year Veteran ഓഹരി നിലവറ")
    st.caption("ഓരോ ഓഹരിയും എന്തുകൊണ്ട് വാങ്ങി? എപ്പോൾ വിറ്റ് ഒഴിവാക്കണം എന്നതിന്റെ കർശനമായ എക്സിറ്റ് നിയമങ്ങൾ.")

    if is_shariah:
        st.success("🌙 **ശരീഅത്ത് ഓഹരികൾ:** പലിശ രഹിത, കടബാധ്യത 33%-ൽ താഴെയുള്ള കമ്പനികൾ.")
        stocks_data = [
            {"Stock": "TCS", "Sector": "IT Services", "Why Buy?": "കടരഹിത ഭീമൻ, 58% ROCE, ഉയർന്ന ക്യാഷ് ഫ്ലോ.", "Red Flags": "AI കാരണം ബില്ലിംഗ് ഇടിയുന്നത്.", "Exit Trigger": "ഓപ്പറേറ്റിംഗ് മാർജിൻ 20%-ൽ താഴെയായാൽ.", "Status": "✅ Halal"},
            {"Stock": "Tata Elxsi", "Sector": "Design & EV", "Why Buy?": "ഇലക്ട്രിക് വാഹന സോഫ്റ്റ്‌വെയറിലെ കുത്തക. 42% ROCE.", "Red Flags": "യൂറോപ്യൻ വാഹന വിപണിയിലെ മാന്ദ്യം.", "Exit Trigger": "വിറ്റുവരവ് വളർച്ച 10%-ൽ താഴെയായാൽ.", "Status": "✅ Halal"},
            {"Stock": "Sun Pharma", "Sector": "Pharma", "Why Buy?": "ജീവൻരക്ഷാ മരുന്നുകൾ, മാന്ദ്യത്തെ അതിജീവിക്കുന്ന ബിസിനസ്സ്.", "Red Flags": "USFDA റെഗുലേറ്ററി തടസ്സങ്ങൾ.", "Exit Trigger": "പ്രധാന പ്ലാന്റുകൾ സ്ഥിരമായി പൂട്ടിയാൽ.", "Status": "✅ Halal"},
            {"Stock": "Polycab India", "Sector": "Cables & Infra", "Why Buy?": "വയർ വിപണിയിലെ 25% കുത്തക. 28% ROCE.", "Red Flags": "ചെമ്പ് വിലക്കയറ്റം.", "Exit Trigger": "വിപണി വിഹിതം നഷ്ടപ്പെടുകയോ തട്ടിപ്പ് വരികയോ ചെയ്താൽ.", "Status": "✅ Halal"}
        ]
    else:
        stocks_data = [
            {"Stock": "CDSL", "Sector": "Depository", "Why Buy?": "ഡിമാറ്റ് അക്കൗണ്ടുകൾ കൂടുമ്പോൾ ടോൾ ബൂത്ത് പോലെ ലാഭം. 33% ROCE.", "Red Flags": "SEBI ചാർജുകൾ വെട്ടിക്കുറയ്ക്കൽ.", "Exit Trigger": "റെഗുലേറ്ററി കമ്മീഷൻ പകുതിയായി കുറച്ചാൽ.", "Status": "⚠️ കൺവെൻഷണൽ"},
            {"Stock": "L&T", "Sector": "Infrastructure", "Why Buy?": "ഇന്ത്യൻ വികസനത്തിലെ ഏക ഭീമൻ. ₹5 ലക്ഷം കോടി ഓർഡർ ബുക്ക്.", "Red Flags": "സർക്കാർ അടിസ്ഥാന ചെലവുകൾ വെട്ടിക്കുറയ്ക്കൽ.", "Exit Trigger": "കടം (Debt/Equity) 1.5 കടന്നാൽ.", "Status": "⚠️ കൺവെൻഷണൽ"},
            {"Stock": "ITC Limited", "Sector": "FMCG / Cash Cow", "Why Buy?": "ഭീമമായ ക്യാഷ് ഫ്ലോ. 3.5%+ ഡിവിഡന്റ്. മാന്ദ്യത്തെ അതിജീവിക്കും.", "Red Flags": "പുകയില നികുതി വർദ്ധനവ്.", "Exit Trigger": "ക്യാഷ് ഫ്ലോ ഇടിയുകയോ സിഗരറ്റ് നിരോധിക്കുകയോ ചെയ്താൽ.", "Status": "❌ Non-Halal"},
            {"Stock": "HAL", "Sector": "Defence", "Why Buy?": "വ്യോമസേനയ്ക്ക് ഫൈറ്റർ ജെറ്റുകൾ നിർമ്മിക്കുന്ന പരമാധികാര കുത്തക. കടമില്ല.", "Red Flags": "പ്രതിരോധ വിഹിതം വെട്ടിക്കുറയ്ക്കൽ.", "Exit Trigger": "സ്വകാര്യ കമ്പനികൾക്ക് നിർമ്മാണാനുമതി നൽകിയാൽ.", "Status": "⚠️ കൺവെൻഷണൽ"}
        ]

    for s in stocks_data:
        with st.expander(f"📌 {s['Stock']} — ({s['Sector']})"):
            st.markdown(f"**🟢 എന്തുകൊണ്ട് വാങ്ങണം:** {s['Why Buy?']}")
            st.markdown(f"**⚠️ ശ്രദ്ധിക്കേണ്ട റിസ്കുകൾ:** {s['Red Flags']}")
            st.error(f"🛑 **എപ്പോൾ വിറ്റ് ഒഴിവാക്കണം (Exit Trigger):** {s['Exit Trigger']}")
            st.caption(f"സ്റ്റാറ്റസ്: {s['Status']}")

# ##################################################################
# 📈 വിഭാഗം 5: മ്യൂച്വൽ ഫണ്ടുകൾ & ഇ.ടി.എഫുകൾ
# ##################################################################
elif main_menu == "📈 മ്യൂച്വൽ ഫണ്ടുകൾ & ഇ.ടി.എഫുകൾ":
    st.title("📈 മ്യൂച്വൽ ഫണ്ട് & ഇ.ടി.എഫ് സെലക്ടർ")
    if is_shariah:
        funds = [
            {"Fund": "Tata Ethical Fund", "Type": "Shariah Equity", "3Y CAGR": "20.8%", "5Y CAGR": "22.5%", "Expense": "0.85%"},
            {"Fund": "Taurus Ethical Fund", "Type": "Shariah Equity", "3Y CAGR": "22.1%", "5Y CAGR": "21.2%", "Expense": "0.95%"},
            {"Fund": "Nippon Gold BeES", "Type": "Physical Gold", "3Y CAGR": "16.4%", "5Y CAGR": "14.8%", "Expense": "0.55%"}
        ]
    else:
        funds = [
            {"Fund": "Parag Parikh Flexi Cap Fund", "Type": "Flexi Cap", "3Y CAGR": "21.5%", "5Y CAGR": "24.2%", "Expense": "0.62%"},
            {"Fund": "UTI Nifty 50 Index Fund", "Type": "Index", "3Y CAGR": "15.8%", "5Y CAGR": "16.5%", "Expense": "0.18%"},
            {"Fund": "Quant Small Cap Fund", "Type": "Small Cap", "3Y CAGR": "34.2%", "5Y CAGR": "38.5%", "Expense": "0.77%"}
        ]
    st.dataframe(pd.DataFrame(funds), use_container_width=True, hide_index=True)

# ##################################################################
# 🌍 വിഭാഗം 6: ആഗോള വിപണികൾ (US & Currency Advisor)
# ##################################################################
elif main_menu == "🌍 ആഗോള വിപണികൾ (US & Currency Advisor)":
    st.title("🌍 ആഗോള നിക്ഷേപം & കറൻസി അഡ്വൈസർ")
    st.info("💡 **വിദഗ്ദ്ധന്റെ ഉപദേശം:** ₹5 ലക്ഷത്തിൽ താഴെയാണെങ്കിൽ ഇന്ത്യൻ മ്യൂച്വൽ ഫണ്ടുകൾ വഴി (INR റൂട്ട്) യു.എസിൽ നിക്ഷേപിക്കുക. ബാങ്ക് ട്രാൻസ്ഫർ ചാർജും TCS-ഉം ഒഴിവാക്കാം.")
    if is_shariah:
        us_stocks = [
            {"Company": "Nvidia (NVDA)", "Sector": "AI Hardware", "Shariah": "✅ Compliant", "Moat": "AI ചിപ്പുകളിലെ കുത്തക."},
            {"Company": "Microsoft (MSFT)", "Sector": "Software", "Shariah": "✅ Compliant", "Moat": "എന്റർപ്രൈസ് ക്ലൗഡ് ശൃംഖല."},
            {"Company": "Alphabet (Google)", "Sector": "Search & Cloud", "Shariah": "✅ Compliant", "Moat": "തിരച്ചിൽ & യൂട്യൂബ് കുത്തക."}
        ]
    else:
        us_stocks = [
            {"Company": "Microsoft (MSFT)", "Sector": "Cloud / AI", "Market Cap": "$3.1T+"},
            {"Company": "Apple (AAPL)", "Sector": "Consumer Tech", "Market Cap": "$3.4T+"},
            {"Company": "Nvidia (NVDA)", "Sector": "AI Chips", "Market Cap": "$3.0T+"},
            {"Company": "Berkshire Hathaway (BRK.B)", "Sector": "Insurance", "Market Cap": "$900B+"}
        ]
    st.dataframe(pd.DataFrame(us_stocks), use_container_width=True, hide_index=True)

# ##################################################################
# 🥇 വിഭാഗം 7: ഗോൾഡ് & സുരക്ഷിത ആസ്തികൾ
# ##################################################################
elif main_menu == "🥇 ഗോൾഡ് & സുരക്ഷിത ആസ്തികൾ":
    st.title("🥇 ഗോൾഡ് & ക്രൈസിസ് പ്രൊട്ടക്ഷൻ")
    gold_data = [
        {"Instrument": "Nippon India Gold BeES (GOLDBEES)", "Asset": "Physical Gold", "Expense": "0.55%", "Shariah": "✅ Halal"},
        {"Instrument": "HDFC Gold ETF (HDFCGOLD)", "Asset": "Physical Gold", "Expense": "0.30%", "Shariah": "✅ Halal"},
        {"Instrument": "Nippon India Silver ETF (SILVERBEES)", "Asset": "Physical Silver", "Expense": "0.50%", "Shariah": "✅ Halal"}
    ]
    st.dataframe(pd.DataFrame(gold_data), use_container_width=True, hide_index=True)

# ##################################################################
# 📚 വിഭാഗം 8: അഡ്വൈസറി ജേർണൽ & ചേഞ്ച് ലോഗ്
# ##################################################################
elif main_menu == "📚 അഡ്വൈസറി ജേർണൽ & ചേഞ്ച് ലോഗ്":
    st.title("📚 എന്റെ സ്വകാര്യ ഇൻവെസ്റ്റ്മെന്റ് ജേർണൽ")
    st.caption("നിങ്ങളുടെ പാസ്‌കീയിൽ മാത്രം സൂക്ഷിക്കുന്ന നിക്ഷേപ തീരുമാനങ്ങൾ.")

    with st.expander("➕ പുതിയ നിക്ഷേപ തീരുമാനം രേഖപ്പെടുത്തുക"):
        j_col1, j_col2, j_col3 = st.columns(3)
        j_asset = j_col1.text_input("അസറ്റ് / സ്റ്റോക്ക് (ഉദാ: TCS, Gold):").upper().strip()
        j_action = j_col2.selectbox("തീരുമാനം:", ["BUY (വാങ്ങി)", "HOLD (തുടരുന്നു)", "SELL (വിറ്റു)", "WATCHLIST (നിരീക്ഷണത്തിൽ)"])
        j_status = j_col3.selectbox("സ്വഭാവം:", ["✅ Long-Term Moat", "🌙 Halal Verified", "⚠️ Tactical Bet", "🛑 Rule Exit"])
        j_reason = st.text_area("എന്തുകൊണ്ട് ഈ തീരുമാനം എടുത്തു? (Veteran Thesis):")

        if st.button("💾 ജേർണലിൽ സേവ് ചെയ്യുക"):
            if j_asset and j_reason:
                try:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO wealth_audit (user_hash, date, asset, category, action, status, veteran_reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                              (USER_HASH, datetime.date.today().strftime("%Y-%m-%d"), j_asset, "Equity/Asset", j_action, j_status, j_reason))
                    conn.commit()
                    conn.close()
                    st.success("✅ തീരുമാനം നിങ്ങളുടെ സ്വകാര്യ ജേർണലിൽ രേഖപ്പെടുത്തി!")
                except Exception as e:
                    st.error(f"സേവ് ചെയ്യുന്നതിൽ തടസ്സം: {e}")

    try:
        conn = get_db_connection()
        df_audit = pd.read_sql_query("SELECT date AS Date, asset AS Asset, action AS Action, status AS Status, veteran_reason AS [Reason / Thesis] FROM wealth_audit WHERE user_hash=? ORDER BY id DESC LIMIT 50", conn, params=(USER_HASH,))
        conn.close()
        if not df_audit.empty:
            st.dataframe(df_audit, use_container_width=True, hide_index=True)
        else:
            st.info("തീരുമാനങ്ങൾ ഇവിടെ ഓഡിറ്റ് ആയി രേഖപ്പെടുത്തും.")
    except Exception:
        st.info("ഡാറ്റ വരാൻ കാത്തിരിക്കുന്നു...")
