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

# ==========================================
# 🌐 PAGE CONFIGURATION & MASTER STOCK DIRECTORY (FOR AUTO-COMPLETE)
# ==========================================
st.set_page_config(page_title="Autonomous Wealth OS & Financial Life Doctor", layout="wide", page_icon="🏛️")

# Popular NSE & Global Stocks Directory for Instant Auto-Complete Dropdowns (Type 'I' -> sees ITC, INFY, etc.)
NSE_STOCK_DIRECTORY = [
    "TCS - Tata Consultancy Services Ltd",
    "INFY - Infosys Ltd",
    "RELIANCE - Reliance Industries Ltd",
    "POLYCAB - Polycab India Ltd",
    "SUNPHARMA - Sun Pharmaceutical Industries",
    "TATAELXSI - Tata Elxsi Ltd",
    "TITAN - Titan Company Ltd",
    "ITC - ITC Limited",
    "SBIN - State Bank of India",
    "HDFCBANK - HDFC Bank Ltd",
    "ICICIBANK - ICICI Bank Ltd",
    "BHARTIARTL - Bharti Airtel Ltd",
    "LT - Larsen & Toubro Ltd",
    "CDSL - Central Depository Services (India) Ltd",
    "HAL - Hindustan Aeronautics Ltd",
    "MARUTI - Maruti Suzuki India Ltd",
    "M&M - Mahindra & Mahindra Ltd",
    "TATAMOTORS - Tata Motors Ltd",
    "WIPRO - Wipro Ltd",
    "HCLTECH - HCL Technologies Ltd",
    "ASIANPAINT - Asian Paints Ltd",
    "PIDILITIND - Pidilite Industries Ltd",
    "DMART - Avenue Supermarts Ltd (DMart)",
    "NESTLEIND - Nestle India Ltd",
    "HINDUNILVR - Hindustan Unilever Ltd",
    "BAJFINANCE - Bajaj Finance Ltd",
    "IRCTC - Indian Railway Catering & Tourism Corp",
    "BEL - Bharat Electronics Ltd",
    "COALINDIA - Coal India Ltd",
    "NTPC - NTPC Ltd",
    "POWERGRID - Power Grid Corporation of India",
    "ULTRACEMCO - UltraTech Cement Ltd",
    "DRREDDY - Dr. Reddy's Laboratories",
    "CIPLA - Cipla Ltd",
    "DIVISLAB - Divi's Laboratories Ltd",
    "DIXON - Dixon Technologies (India) Ltd",
    "KPITTECH - KPIT Technologies Ltd",
    "PERSISTENT - Persistent Systems Ltd",
    "COFORGE - Coforge Ltd",
    "ASTRAL - Astral Ltd",
    "SUPREMEIND - Supreme Industries Ltd",
    "CUMMINSIND - Cummins India Ltd",
    "ABB - ABB India Ltd",
    "SIEMENS - Siemens Ltd",
    "TRENT - Trent Ltd",
    "ZOMATO - Zomato Ltd",
    "JIOFIN - Jio Financial Services Ltd",
    "GOLDBEES - Nippon India ETF Gold BeES",
    "SILVERBEES - Nippon India Silver ETF",
    "CUSTOM - ✍️ Type Any Other NSE Symbol Manually..."
]

US_STOCK_DIRECTORY = [
    "NVDA - Nvidia Corporation",
    "MSFT - Microsoft Corporation",
    "AAPL - Apple Inc.",
    "GOOGL - Alphabet Inc. (Google)",
    "AMZN - Amazon.com Inc.",
    "META - Meta Platforms Inc.",
    "TSLA - Tesla Inc.",
    "BRK-B - Berkshire Hathaway Inc.",
    "SPUS - SP Funds S&P 500 Sharia Industry Exclusions ETF",
    "HLAL - Wahed FTSE USA Shariah ETF",
    "QQQ - Invesco QQQ Trust (Nasdaq-100)",
    "VOO - Vanguard S&P 500 ETF",
    "CUSTOM - ✍️ Type Any Other US Ticker Manually..."
]

# ==========================================
# 🗄️ MULTI-USER SQLITE DATABASE SETUP (WAL MODE)
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
        c.execute('''CREATE TABLE IF NOT EXISTS us_portfolio (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_hash TEXT, symbol TEXT, qty REAL, buy_price_usd REAL, buy_usd_inr REAL, platform TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_debts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_hash TEXT, loan_type TEXT, lender TEXT, total_amount REAL,
                        interest_rate REAL, emi REAL, status TEXT, notes TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_settings (
                        user_hash TEXT PRIMARY KEY, api_key TEXT, api_secret TEXT,
                        redirect_uri TEXT, tg_token TEXT, tg_chat TEXT, access_token TEXT, broker TEXT)''')
        for col in ["access_token", "broker"]:
            try:
                c.execute(f"ALTER TABLE user_settings ADD COLUMN {col} TEXT")
            except Exception:
                pass
        conn.commit()
        conn.close()
    except Exception:
        pass

init_db()

def save_user_creds(u_hash, api_k, api_s, red_u, tg_t, tg_c, acc_tok="", broker="Upstox"):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO user_settings 
                     (user_hash, api_key, api_secret, redirect_uri, tg_token, tg_chat, access_token, broker)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (u_hash, api_k, api_s, red_u, tg_t, tg_c, acc_tok, broker))
        conn.commit()
        conn.close()
    except Exception:
        pass

def load_user_creds(u_hash):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT api_key, api_secret, redirect_uri, tg_token, tg_chat, access_token, broker FROM user_settings WHERE user_hash=?", (u_hash,))
        row = c.fetchone()
        conn.close()
        if row:
            return {
                'api_key': row[0] or '', 'api_secret': row[1] or '',
                'redirect_uri': row[2] or 'https://my-trading-bot-wyjcnfn2bprzd4ysp8riie.streamlit.app',
                'tg_token': row[3] or '', 'tg_chat': row[4] or '',
                'access_token': row[5] or '', 'broker': row[6] or 'Upstox'
            }
    except Exception:
        pass
    return None

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

# ==========================================
# 🌐 MULTILINGUAL UI LABELS
# ==========================================
st.sidebar.markdown("# 🏛️ WEALTH OS")
lang = st.sidebar.selectbox("🌐 Language / ഭാഷ:", ["മലയാളം", "English", "हिन्दी", "العربية"], index=0)
is_ml = (lang == "മലയാളം")

MENU_ITEMS = [
    "🧭 തുടക്കക്കാരുടെ വഴികാട്ടി (Start Here Guide)" if is_ml else "🧭 Beginner Quick-Start Guide",
    "💳 കടം തീർക്കൽ & ലോൺ പ്ലാനർ (Debt Freedom)" if is_ml else "💳 Debt Freedom & Loan Elimination Planner",
    "🎯 ലക്ഷ്യാധിഷ്ഠിത പോർട്ട്ഫോളിയോ (Goal Engine)" if is_ml else "🎯 Dynamic Goal Allocator",
    "🏛️ 50-Year സ്റ്റോക്ക് നിലവറ & ലൈവ് സ്കാനർ" if is_ml else "🏛️ 50-Year Moat Vault & Live Scanner",
    "💼 എന്റെ ലൈവ് പോർട്ട്ഫോളിയോ & വാച്ച്ഡോഗ്" if is_ml else "💼 Live Portfolio & Exit Watchdog",
    "🎟️ ഐ.പി.ഒ (IPO) റഡാർ & അനലൈസർ" if is_ml else "🎟️ IPO Radar & Red-Flag Analyzer",
    "📜 ബോണ്ടുകൾ, കടപ്പത്രങ്ങൾ & സുരക്ഷിത വരുമാനം" if is_ml else "📜 Bonds, G-Secs & Halal Fixed-Income",
    "📈 മ്യൂച്വൽ ഫണ്ടുകൾ & ഇ.ടി.എഫുകൾ" if is_ml else "📈 Mutual Funds & ETFs",
    "🌍 ആഗോള വിപണികൾ (US & INDmoney)" if is_ml else "🌍 Global Markets (US & Currency)",
    "🥇 ഗോൾഡ് & സുരക്ഷിത ആസ്തികൾ" if is_ml else "🥇 Gold & Crisis Hedge Assets",
    "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട് (Algo Engine)" if is_ml else "⚡ Intraday Algo Trading Bot",
    "📚 അഡ്വൈസറി ജേർണൽ & ചേഞ്ച് ലോഗ്" if is_ml else "📚 Investment Audit Journal"
]

# ==========================================
# 🔐 OAUTH STATE MATCHER & SESSION AUTHENTICATION
# ==========================================
@st.cache_resource
def get_user_vault():
    return {}

user_vault = get_user_vault()

if "code" in st.query_params:
    incoming_code = st.query_params["code"]
    incoming_state_hash = st.query_params.get("state", "")
    st.query_params.clear()
    
    if incoming_state_hash:
        u_creds = load_user_creds(incoming_state_hash)
        if u_creds and u_creds['api_key'] and u_creds['api_secret']:
            ok, tok_or_err = exchange_code_for_token(incoming_code, u_creds['api_key'], u_creds['api_secret'], u_creds['redirect_uri'])
            if ok:
                save_user_creds(incoming_state_hash, u_creds['api_key'], u_creds['api_secret'], u_creds['redirect_uri'], u_creds['tg_token'], u_creds['tg_chat'], tok_or_err, u_creds['broker'])
                if incoming_state_hash in user_vault:
                    user_vault[incoming_state_hash]['token'] = tok_or_err
                st.session_state["authenticated_user_hash"] = incoming_state_hash
                st.success("🎉 OAuth 2.0 Access Token generated and securely saved to your vault!")
            else:
                st.error(f"OAuth Token Error: {tok_or_err}")
    else:
        st.session_state["pending_auth_code"] = incoming_code

if "authenticated_user_hash" not in st.session_state:
    st.session_state["authenticated_user_hash"] = None

if not st.session_state["authenticated_user_hash"]:
    st.subheader("🔒 സ്വകാര്യ ലോക്കർ ലോഗിൻ (100% Data Privacy)" if is_ml else "🔒 Private Vault Login (100% Data Privacy)")
    st.info("നിങ്ങളുടെ സ്വകാര്യ അക്കൗണ്ട് തുറക്കാൻ നിങ്ങൾക്ക് മാത്രം അറിയാവുന്ന ഒരു രഹസ്യ പാസ്‌കീ (Secret ID) നൽകുക. നിങ്ങളുടെ കടവിവരങ്ങളോ പോർട്ട്ഫോളിയോയോ മറ്റാർക്കും കാണാൻ കഴിയില്ല." if is_ml else "Enter your personal Secret Passkey to unlock your isolated workspace. No other user can view your data.")
    with st.form("vault_login_form"):
        passkey_input = st.text_input("നിങ്ങളുടെ രഹസ്യ പാസ്‌കീ (Secret ID) നൽകുക:" if is_ml else "Enter Secret Passkey / ID:", type="password")
        login_submitted = st.form_submit_button("🔓 അക്കൗണ്ട് തുറക്കുക (Login)" if is_ml else "🔓 Unlock Workspace", type="primary")
        if login_submitted and passkey_input.strip():
            st.session_state["authenticated_user_hash"] = hashlib.sha256(passkey_input.strip().encode()).hexdigest()[:16]
            st.rerun()
    st.stop()

USER_HASH = st.session_state["authenticated_user_hash"]

if st.sidebar.button("🔒 ലോഗൗട്ട് / സ്ക്രീൻ പൂട്ടുക" if is_ml else "🔒 Logout / Lock Screen", use_container_width=True):
    st.session_state["authenticated_user_hash"] = None
    st.rerun()

saved_c = load_user_creds(USER_HASH) or {}

if USER_HASH not in user_vault:
    user_vault[USER_HASH] = {
        'running': False, 'token': saved_c.get('access_token', ''), 'capital': 5000.0, 'risk': 100.0,
        'mode': 'PAPER',
        'tg_token': saved_c.get('tg_token', ''), 'tg_chat': saved_c.get('tg_chat', ''),
        'thread': None, 'consecutive_losses': 0, 'kill_switch': False,
        'nifty_status': 'Checking...', 'active_pos': None,
        'shariah_lock': False, 'last_order_error': '',
        'api_key': saved_c.get('api_key', ''),
        'api_secret': saved_c.get('api_secret', ''),
        'redirect_uri': saved_c.get('redirect_uri', 'https://my-trading-bot-wyjcnfn2bprzd4ysp8riie.streamlit.app'),
        'broker': saved_c.get('broker', 'Upstox')
    }
else:
    if saved_c.get('access_token') and not user_vault[USER_HASH].get('token'):
        user_vault[USER_HASH]['token'] = saved_c['access_token']

state = user_vault[USER_HASH]

# ==========================================
# 👑 MASTER PHILOSOPHY & NAVIGATION MENU
# ==========================================
st.sidebar.markdown("---")
phil_options = ["🌐 ആഗോള ജനറൽ മോഡ് (Conventional)", "🌙 100% പ്യുവർ ശരീഅത്ത് മോഡ് (Halal AAOIFI)"] if is_ml else ["🌐 Global Conventional Mode", "🌙 100% Pure Shariah Mode (AAOIFI)"]
wealth_mode = st.sidebar.radio("നിക്ഷേപ തത്ത്വശാസ്ത്രം:" if is_ml else "Investment Philosophy:", phil_options)
is_shariah = ("ശരീഅത്ത്" in wealth_mode or "Shariah" in wealth_mode)
state['shariah_lock'] = is_shariah

st.sidebar.markdown("---")
main_menu = st.sidebar.radio("പ്രധാന വിഭാഗം തിരഞ്ഞെടുക്കുക:" if is_ml else "Select Core Module:", MENU_ITEMS)

# Helper function for Auto-Complete Stock Selection
def select_stock_autocomplete(label_text, directory_list, key_prefix, default_index=0):
    choice = st.selectbox(label_text, directory_list, index=default_index, key=f"{key_prefix}_sel")
    if choice.startswith("CUSTOM"):
        custom_val = st.text_input("✍️ സ്റ്റോക്ക് സിംബൽ ടൈപ്പ് ചെയ്യുക (ഉദാ: FEDERALBNK, IDEA):" if is_ml else "✍️ Enter Custom Symbol:", key=f"{key_prefix}_cust").upper().strip()
        return custom_val
    return choice.split(" - ")[0].strip()

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
# 🧭 MODULE 0: BEGINNER QUICK-START GUIDE (USER-FRIENDLY ONBOARDING)
# ##################################################################
if main_menu == MENU_ITEMS[0]:
    st.title("🧭 സ്വാഗതം! എവിടെ തുടങ്ങണം? (Beginner Financial Roadmap)" if is_ml else "🧭 Welcome! Step-by-Step Financial Life Roadmap")
    st.caption("ഓഹരി വിപണിയോ സാമ്പത്തിക ആസൂത്രണമോ ഒട്ടും അറിയാത്തവർക്കും ഏറ്റവും എളുപ്പത്തിൽ ഉപയോഗിക്കാവുന്ന വഴികാട്ടി." if is_ml else "A zero-jargon guide for beginners to achieve debt freedom and generational wealth.")

    st.success("👋 **ആദ്യമായിട്ടാണോ ഇവിടെ?** താഴെ കൊടുത്തിരിക്കുന്ന 4 ഘട്ടങ്ങൾ ക്രമമായി പിന്തുടരുക. ഇടതുവശത്തെ മെനുവിൽ ക്ലിക്ക് ചെയ്ത് ഓരോ വിഭാഗത്തിലേക്കും പോകാം!" if is_ml else "👋 **New here?** Follow the 4 steps below in order using the left sidebar menu!")

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("""
        ### 🛑 ഘട്ടം 1: നിങ്ങൾക്ക് കടങ്ങളോ ലോണുകളോ ഉണ്ടോ?
        * **എന്ത് ചെയ്യണം?** ഇടതുവശത്തെ മെനുവിൽ **'💳 കടം തീർക്കൽ & ലോൺ പ്ലാനർ'** തിരഞ്ഞെടുക്കുക.
        * **എന്തുകൊണ്ട്?** 14%–36% പലിശയുള്ള പേഴ്സണൽ ലോണും ക്രെഡിറ്റ് കാർഡ് കടവും വെച്ചുകൊണ്ട് സ്റ്റോക്ക് മാർക്കറ്റിൽ ട്രേഡ് ചെയ്യരുത്! ആദ്യം നിങ്ങളുടെ എല്ലാ കടങ്ങളും അവിടെ ലിസ്റ്റ് ചെയ്യുക. ഏത് കടമാണ് ആദ്യം വീട്ടേണ്ടതെന്നും EMI മുടങ്ങിയാൽ എങ്ങനെ പരിഹരിക്കാമെന്നും ആ സിസ്റ്റം പറഞ്ഞുതരും.
        
        ---
        ### 🛡️ ഘട്ടം 2: അത്യാവശ്യ ഫണ്ടും (Emergency Fund) സ്വർണ്ണവും
        * **എന്ത് ചെയ്യണം?** **'🎯 ലക്ഷ്യാധിഷ്ഠിത പോർട്ട്ഫോളിയോ'**, **'🥇 ഗോൾഡ് & സുരക്ഷിത ആസ്തികൾ'** എന്നിവ തുറക്കുക.
        * **എന്തുകൊണ്ട്?** നിങ്ങളുടെ 3 മുതൽ 6 മാസത്തെ വീട്ടുചെലവിനുള്ള പണം സുരക്ഷിതമായി മാറ്റിവെക്കണം. അതിനുശേഷം മാത്രമേ ഓഹരി വിപണിയിലേക്ക് കടക്കാവൂ.
        """ if is_ml else """
        ### 🛑 Step 1: Do You Have High-Interest Debt or Loans?
        * **Action:** Open **'💳 Debt Freedom & Loan Elimination Planner'** in the sidebar.
        * **Why?** Never trade or invest while paying 14%–36% interest on personal loans or credit cards. List your debts there to generate a step-by-step payoff priority plan.
        
        ---
        ### 🛡️ Step 2: Build Your Emergency Shield & Gold Hedge
        * **Action:** Open **'🎯 Dynamic Goal Allocator'** and **'🥇 Gold & Crisis Hedge Assets'**.
        * **Why?** Secure 3–6 months of living expenses in liquid reserves and physical gold ETFs before taking equity risk.
        """)

    with g2:
        st.markdown("""
        ### 🏛️ ഘട്ടം 3: ദീർഘകാല നിക്ഷേപം (സ്റ്റോക്കുകൾ, മ്യൂച്വൽ ഫണ്ട്, IPO, ബോണ്ട്)
        * **എന്ത് ചെയ്യണം?** **'🏛️ 50-Year സ്റ്റോക്ക് നിലവറ'**, **'📈 മ്യൂച്വൽ ഫണ്ടുകൾ'**, **'🎟️ ഐ.പി.ഒ റഡാർ'** എന്നിവ പരിശോധിക്കുക.
        * **എന്തുകൊണ്ട്?** ഏതൊരു കമ്പനിയുടെയും പേര് ടൈപ്പ് ചെയ്യുമ്പോൾത്തന്നെ ഓട്ടോമാറ്റിക് ലിസ്റ്റിൽ നിന്ന് തിരഞ്ഞെടുത്ത് അതിന്റെ കടവും ലാഭവും ഹലാൽ സ്റ്റാറ്റസും ഒറ്റ ക്ലിക്കിൽ പരിശോധിക്കാം!
        
        ---
        ### ⚡ ഘട്ടം 4: ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട് (പരിചയസമ്പന്നർക്ക് മാത്രം)
        * **എന്ത് ചെയ്യണം?** **'⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്'** തുറന്ന് ആദ്യം **'പേപ്പർ ട്രേഡിംഗ് (സുരക്ഷിതം)'** മോഡിൽ മാത്രം പ്രവർത്തിപ്പിച്ചു പഠിക്കുക.
        * **എന്തുകൊണ്ട്?** യഥാർത്ഥ പണം നഷ്ടപ്പെടാതെ ലൈവ് മാർക്കറ്റിൽ ബോട്ട് എങ്ങനെ പ്രവർത്തിക്കുന്നു എന്ന് പഠിക്കാൻ പേപ്പർ ട്രേഡിംഗ് സഹായിക്കും.
        """ if is_ml else """
        ### 🏛️ Step 3: Long-Term Wealth (Moat Stocks, Mutual Funds, IPOs & Bonds)
        * **Action:** Explore **'🏛️ 50-Year Moat Vault'**, **'📈 Mutual Funds'**, and **'🎟️ IPO Radar'**.
        * **Why?** Use our Auto-Complete Stock Scanner to check any company's debt, ROE, and AAOIFI Shariah compliance in one click.
        
        ---
        ### ⚡ Step 4: Intraday Algo Bot (Start with Paper Trading!)
        * **Action:** Open **'⚡ Intraday Algo Trading Bot'** and keep it in **Paper Trading Mode**.
        * **Why?** Test live market execution with zero financial risk before deploying real capital.
        """)

# ##################################################################
# 💳 MODULE 1: DEBT FREEDOM & LOAN ELIMINATION PLANNER (NEW!)
# ##################################################################
elif main_menu == MENU_ITEMS[1]:
    st.title("💳 കടം തീർക്കൽ & സാമ്പത്തിക മോചന എൻജിൻ (Debt Freedom Planner)" if is_ml else "💳 Debt Freedom & Loan Elimination Planner")
    st.caption("നിങ്ങളുടെ എല്ലാ ലോണുകളും കടങ്ങളും ഇവിടെ ലളിതമായി ലിസ്റ്റ് ചെയ്യുക. ഏത് കടമാണ് ആദ്യം വീട്ടേണ്ടതെന്നും, EMI മുടങ്ങിയാൽ എന്ത് ചെയ്യണമെന്നും കൃത്യമായി പ്ലാൻ ചെയ്യാം." if is_ml else "List all your loans and informal debts to calculate interest drain, payoff priority, and default recovery strategies.")

    with st.expander("➕ പുതിയ ലോൺ / കടം ചേർക്കുക (ഇവിടെ ക്ലിക്ക് ചെയ്യുക)" if is_ml else "➕ Add a Loan or Debt to Your Tracker", expanded=True):
        dc1, dc2, dc3 = st.columns(3)
        loan_cat = dc1.selectbox(
            "കടത്തിന്റെ വിഭാഗം തിരഞ്ഞെടുക്കുക:" if is_ml else "Select Loan / Debt Category:",
            [
                "💳 ക്രെഡിറ്റ് കാർഡ് കുടിശ്ശിക (Credit Card - 36% to 42%)",
                "⚠️ വ്യക്തിഗത കടം / പുറത്തുനിന്ന് വാങ്ങിയത് (Informal / Private Debt)",
                "🏦 പേഴ്സണൽ ലോൺ / ആപ്പ് ലോൺ (Personal / App Loan - 14% to 28%)",
                "🪙 ഗോൾഡ് ലോൺ / സ്വർണ്ണപ്പണയം (Gold Loan - 9% to 18%)",
                "🚗 വാഹന ലോൺ (Vehicle Loan - 9% to 14%)",
                "🏠 ഹോം ലോൺ / ഭവന വായ്പ (Home Loan - 8% to 10%)",
                "🎓 എജ്യുക്കേഷൻ / മറ്റ് ലോണുകൾ (Education / Other Loan)"
            ]
        )
        lender_name = dc2.text_input("ബാങ്ക് / വ്യക്തിയുടെ പേര് (ഉദാ: HDFC, സുഹൃത്ത്):" if is_ml else "Bank / Lender Name (e.g. HDFC, Friend):")
        loan_status = dc3.selectbox(
            "നിലവിലെ അവസ്ഥ (Current Status):" if is_ml else "Current Repayment Status:",
            [
                "🟢 കൃത്യമായി EMI അടച്ചുപോകുന്നു (Regular / Active)",
                "🟡 1-2 മാസം അടവ് മുടങ്ങി (Overdue / Stress)",
                "🔴 പൂർണ്ണമായി മുടങ്ങി / റിക്കവറി ഭീഷണി (Defaulted / NPA / Critical)"
            ]
        )

        dc4, dc5, dc6 = st.columns(3)
        tot_debt_amt = dc4.number_input("ഇനി കൊടുത്തുതീർക്കാനുള്ള ആകെ തുക (₹):" if is_ml else "Total Outstanding Principal (₹):", min_value=500.0, value=50000.0, step=5000.0)
        int_rate = dc5.number_input("വാർഷിക പലിശ നിരക്ക് (% - അറിയില്ലെങ്കിൽ 0):" if is_ml else "Annual Interest Rate (% - 0 if interest-free):", min_value=0.0, max_value=120.0, value=14.0, step=1.0)
        monthly_emi = dc6.number_input("പ്രതിമാസ അടവ് / EMI (₹ - ഇല്ലെങ്കിൽ 0):" if is_ml else "Monthly EMI (₹ - 0 if lump-sum):", min_value=0.0, value=2500.0, step=500.0)

        col_btn1, col_btn2 = st.columns([2, 1])
        if col_btn1.button("💾 കടങ്ങളുടെ ലിസ്റ്റിലേക്ക് ചേർക്കുക (Save Debt)" if is_ml else "💾 Add to My Debt Priority List", type="primary", use_container_width=True):
            try:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute('''INSERT INTO user_debts (user_hash, loan_type, lender, total_amount, interest_rate, emi, status, notes)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                          (USER_HASH, loan_cat, lender_name or "Lender", tot_debt_amt, int_rate, monthly_emi, loan_status, ""))
                conn.commit()
                conn.close()
                st.success("✅ കടം ലിസ്റ്റിൽ ചേർത്തു! താഴെ നിങ്ങളുടെ പ്രയോറിറ്റി പ്ലാൻ കാണാം." if is_ml else "✅ Debt added! View your priority payoff plan below.")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        if col_btn2.button("🗑️ ലിസ്റ്റ് മുഴുവൻ മായ്ക്കുക (Clear All)" if is_ml else "🗑️ Clear All Debts", use_container_width=True):
            conn = get_db_connection()
            conn.execute("DELETE FROM user_debts WHERE user_hash=?", (USER_HASH,))
            conn.commit()
            conn.close()
            st.rerun()

    # Load and Analyze User Debts
    conn = get_db_connection()
    df_debts = pd.read_sql_query("SELECT id, loan_type, lender, total_amount, interest_rate, emi, status FROM user_debts WHERE user_hash=?", conn, params=(USER_HASH,))
    conn.close()

    if not df_debts.empty:
        total_debt_sum = df_debts['total_amount'].sum()
        total_emi_sum = df_debts['emi'].sum()
        # Calculate annual interest drain
        df_debts['annual_interest_rs'] = (df_debts['total_amount'] * df_debts['interest_rate']) / 100.0
        df_debts['monthly_interest_rs'] = df_debts['annual_interest_rs'] / 12.0
        total_monthly_interest = df_debts['monthly_interest_rs'].sum()

        # Priority Scoring: Defaulted/Overdue + High Interest gets #1 Priority (Debt Avalanche + Crisis Triage)
        def calc_urgency_score(row):
            status_boost = 50.0 if "🔴" in str(row['status']) else (25.0 if "🟡" in str(row['status']) else 0.0)
            return float(row['interest_rate']) + status_boost

        df_debts['urgency_score'] = df_debts.apply(calc_urgency_score, axis=1)
        df_sorted = df_debts.sort_values(by=['urgency_score', 'total_amount'], ascending=[False, True]).reset_index(drop=True)
        df_sorted['Priority Rank'] = [f"🔥 #{i+1} (ആദ്യം വീട്ടുക)" if i == 0 else f"#{i+1}" for i in range(len(df_sorted))]

        st.markdown("---")
        m_d1, m_d2, m_d3 = st.columns(3)
        m_d1.metric("ആകെ കൊടുത്തുതീർക്കാനുള്ള കടം" if is_ml else "Total Debt Burden", f"₹{total_debt_sum:,.0f}")
        m_d2.metric("മാസം തോറും അടയ്ക്കുന്ന ആകെ EMI" if is_ml else "Total Monthly EMI Outflow", f"₹{total_emi_sum:,.0f}")
        m_d3.metric("മാസം തോറും പലിശയായി നഷ്ടപ്പെടുന്നത്!" if is_ml else "Monthly Interest Drain (Wasted)", f"₹{total_monthly_interest:,.0f}", delta="-Interest Drain", delta_color="inverse")

        st.subheader("🎯 നിങ്ങൾ കടം വീട്ടേണ്ട മുൻഗണനാ ക്രമം (Priority Payoff Order)" if is_ml else "🎯 Your Automated Debt Payoff Priority List")
        display_df = pd.DataFrame({
            "മുൻഗണന (Priority)": df_sorted['Priority Rank'],
            "ലോൺ വിഭാഗം (Loan Type)": df_sorted['loan_type'],
            "ബാങ്ക് / വ്യക്തി": df_sorted['lender'],
            "ആകെ തുക (₹)": df_sorted['total_amount'].map(lambda x: f"₹{x:,.0f}"),
            "പലിശ (%)": df_sorted['interest_rate'].map(lambda x: f"{x:.1f}%"),
            "മാസ പലിശ നഷ്ടം": df_sorted['monthly_interest_rs'].map(lambda x: f"₹{x:,.0f}/m"),
            "EMI (₹)": df_sorted['emi'].map(lambda x: f"₹{x:,.0f}"),
            "നിലവിലെ അവസ്ഥ (Status)": df_sorted['status']
        })
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        top_debt = df_sorted.iloc[0]
        st.error(f"🚨 **ഏറ്റവും ആദ്യം തീർക്കേണ്ട കടം (Priority #1):** `{top_debt['lender']} - {top_debt['loan_type']}` (തുക: ₹{top_debt['total_amount']:,.0f} | പലിശ: {top_debt['interest_rate']}%). മറ്റെല്ലാ ലോണുകളുടെയും സാധാരണ EMI മുടങ്ങാതെ അടച്ചുകൊണ്ട്, നിങ്ങളുടെ കയ്യിൽ കിട്ടുന്ന ഓരോ അധിക രൂപയും ഈ ഒന്നാമത്തെ കടം പൂർണ്ണമായി തീർക്കാൻ മാത്രം ഉപയോഗിക്കുക!")

    st.markdown("---")
    st.subheader("🛠️ എത്രയും വേഗം കടം തീർക്കാനും EMI മുടങ്ങിയവർക്ക് രക്ഷപ്പെടാനുമുള്ള 5 പ്രായോഗിക മാർഗ്ഗങ്ങൾ" if is_ml else "🛠️ 5 Proven Institutional & Legal Strategies to Escape Debt")
    with st.expander("1️⃣ അസറ്റ് ലിക്വിഡേഷൻ (സ്വർണ്ണമോ ഉപയോഗിക്കാത്ത വസ്തുക്കളോ വിറ്റ് വലിയ പലിശ ഒഴിവാക്കുക)", expanded=True):
        st.markdown("""
        * **തെറ്റായ രീതി:** കയ്യിൽ സ്വർണ്ണമോ, ഉപയോഗിക്കാത്ത വാഹനമോ, സ്ഥലമോ വെച്ചുകൊണ്ട് 18%–36% പലിശയുള്ള പേഴ്സണൽ ലോണും ക്രെഡിറ്റ് കാർഡ് കടവും വർഷങ്ങളോളം അടച്ചുകൊണ്ടിരിക്കുന്നത് വലിയ സാമ്പത്തിക നഷ്ടമാണ്.
        * **ശരിയായ രീതി:** ഉയർന്ന പലിശയുള്ള കടങ്ങൾ ഒറ്റയടിക്ക് തീർക്കാൻ കയ്യിലുള്ള നിഷ്ക്രിയ ആസ്തികൾ (Idle Assets / Gold) വിൽക്കുകയോ, അല്ലെങ്കിൽ 9% പലിശയുള്ള ഗോൾഡ് ലോൺ എടുത്ത് 36% പലിശയുള്ള ക്രെഡിറ്റ് കാർഡ്/പേഴ്സണൽ ലോൺ അന്ന് തന്നെ ക്ലോസ് ചെയ്യുകയോ ചെയ്യുക (**Debt Consolidation**). കടം തീർത്ത ശേഷം ആ EMI തുക വെച്ച് സ്വർണ്ണം തിരികെ വാങ്ങാം!
        """)
    with st.expander("2️⃣ EMI പൂർണ്ണമായി മുടങ്ങിയവർ അറിയേണ്ട നിയമപരമായ വഴികൾ (Loan Default / OTS / Restructuring)"):
        st.markdown("""
        * **മോറട്ടോറിയം / റീസ്ട്രക്ചറിംഗ് (Loan Restructuring):** ജോലി നഷ്ടപ്പെടുകയോ ബിസിനസ്സ് തകരുകയോ ചെയ്താൽ ബാങ്ക് മാനേജരെ നേരിട്ട് കണ്ട് ലോൺ കാലാവധി കൂട്ടി EMI തുക കുറച്ചുതരാൻ (Tenure Extension) രേഖാമൂലം അപേക്ഷിക്കാം.
        * **വൺ-ടൈം സെറ്റിൽമെന്റ് (One-Time Settlement - OTS):** അൺസെക്യൂർഡ് ലോണുകൾ (ക്രെഡിറ്റ് കാർഡ്, പേഴ്സണൽ ലോൺ) 90 ദിവസത്തിലധികം മുടങ്ങി NPA ആയാൽ, പിഴപ്പലിശ ഒഴിവാക്കി മുതലിന്റെ ഒരു നിശ്ചിത ശതമാനം മാത്രം ഒറ്റത്തവണയായി അടച്ച് ലോൺ ക്ലോസ് ചെയ്യാൻ ബാങ്കുമായി ചർച്ച ചെയ്യാം (ശ്രദ്ധിക്കുക: ഇത് CIBIL സ്കോറിനെ ബാധിക്കും, പക്ഷേ കടക്കെണിയിൽ നിന്ന് രക്ഷപ്പെടാം).
        * **RBI നിയമം:** റിക്കവറി ഏജന്റുമാർക്ക് രാവിലെ 8 മണിക്ക് മുൻപോ വൈകുന്നേരം 7 മണിക്ക് ശേഷമോ വിളിക്കാനോ ഭീഷണിപ്പെടുത്താനോ അനുവാദമില്ല. അങ്ങനെ ചെയ്താൽ RBI Ombudsman-ൽ പരാതി നൽകാം.
        """)
    with st.expander("3️⃣ അവലാഞ്ച് vs സ്നോബോൾ രീതി (Avalanche vs. Snowball Method)"):
        st.markdown("""
        * **ഡെബ്റ്റ് അവലാഞ്ച് (Debt Avalanche - ഗണിതശാസ്ത്രപരമായി ഏറ്റവും മികച്ചത്):** ഏറ്റവും കൂടുതൽ പലിശയുള്ള കടം (ഉദാ: ക്രെഡിറ്റ് കാർഡ് / ബ്ലേഡ് പലിശ) ഒന്നാമതായി എടുത്ത് പൂർണ്ണമായി അടച്ചുതീർക്കുക.
        * **ഡെബ്റ്റ് സ്നോബോൾ (Debt Snowball - മാനസിക ആശ്വാസത്തിന്):** തുക ഏറ്റവും കുറവുള്ള ചെറിയ കടങ്ങൾ (ഉദാ: ₹5,000, ₹10,000 സുഹൃത്തുക്കൾക്ക് കൊടുക്കാനുള്ളത്) ആദ്യം കൊടുത്തുതീർത്ത് കടങ്ങളുടെ എണ്ണം കുറയ്ക്കുക.
        """)

# ##################################################################
# 🎯 MODULE 2: DYNAMIC GOAL ALLOCATOR
# ##################################################################
elif main_menu == MENU_ITEMS[2]:
    st.title(MENU_ITEMS[2])
    with st.expander("📐 നിക്ഷേപ വിഹിതം നിശ്ചയിക്കുന്നതിന്റെ അടിസ്ഥാന തത്വങ്ങൾ (Criteria)" if is_ml else "📐 Asset Allocation Methodology"):
        st.markdown("""
        * **1 വർഷത്തെ ലക്ഷ്യം:** ഓഹരി വിപണിയിലെ ചാഞ്ചാട്ടം ഒഴിവാക്കാൻ ഇക്വിറ്റി **15%** ആയി പരിമിതപ്പെടുത്തി **50% ലിക്വിഡ് ക്യാഷും 25–35% സ്വർണ്ണവും** നിർദ്ദേശിക്കുന്നു.
        * **3–5 വർഷത്തെ ലക്ഷ്യം:** സാധാരണ വിപണിയിൽ **60% ഇക്വിറ്റി**, യുദ്ധ സാഹചര്യത്തിൽ **40% ഇക്വിറ്റി**.
        * **10+ വർഷത്തെ ലക്ഷ്യം:** കടരഹിത കുത്തക കമ്പനികളിൽ **65–75%** നിക്ഷേപിക്കുന്നു.
        """)

    c1, c2, c3 = st.columns(3)
    inv_type = c1.selectbox("നിക്ഷേപ രീതി:" if is_ml else "Investment Mode:", ["Monthly SIP (പ്രതിമാസം)", "Lump-Sum (ഒറ്റത്തവണ)"])
    inv_amount = c2.number_input("നിക്ഷേപ തുക (₹):" if is_ml else "Investment Amount (₹):", value=10000.0, step=1000.0)
    goal_horizon = c3.selectbox(
        "നിക്ഷേപ കാലാവധി:" if is_ml else "Time Horizon:",
        [
            "⏳ 1 Year (ഹ്രസ്വകാലം / Emergency)",
            "🚀 3 - 5 Years (ഇടത്തരം വളർച്ച / വീട് / ബിസിനസ്സ്)",
            "🏛️ 10+ Years (ദീർഘകാല സമ്പത്ത് / വിരമിക്കൽ)"
        ]
    )

    market_climate = st.selectbox(
        "നിലവിലെ വിപണി സാഹചര്യം:" if is_ml else "Current Market Regime:",
        [
            "🟢 Normal Bull (ശാന്തമായ വിപണി)",
            "⚠️ War / Crude Oil Spike (യുദ്ധം / അസ്ഥിരത)",
            "🔴 Extreme Market Crash (കടുത്ത തകർച്ച)"
        ]
    )

    if "1 Year" in goal_horizon:
        eq_pct, gold_pct, cash_pct, reit_pct = (0.15, 0.35, 0.50, 0.0) if is_shariah else (0.15, 0.25, 0.50, 0.10)
    elif "3 - 5 Years" in goal_horizon:
        if "War" in market_climate: eq_pct, gold_pct, cash_pct, reit_pct = 0.40, 0.30 if is_shariah else 0.25, 0.30 if is_shariah else 0.25, (0.0 if is_shariah else 0.10)
        else: eq_pct, gold_pct, cash_pct, reit_pct = 0.60, 0.20 if is_shariah else 0.15, 0.20 if is_shariah else 0.15, (0.0 if is_shariah else 0.10)
    else:
        if "Crash" in market_climate: eq_pct, gold_pct, cash_pct, reit_pct = 0.75, 0.15, 0.10, 0.0
        else: eq_pct, gold_pct, cash_pct, reit_pct = 0.70 if is_shariah else 0.65, 0.20 if is_shariah else 0.15, 0.10, (0.0 if is_shariah else 0.10)

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("ഇക്വിറ്റി ഓഹരികൾ", f"₹{(inv_amount * eq_pct):,.0f}", f"{int(eq_pct*100)}%")
    a2.metric("ഗോൾഡ് & സിൽവർ", f"₹{(inv_amount * gold_pct):,.0f}", f"{int(gold_pct*100)}%")
    a3.metric("ക്യാഷ് കരുതൽ", f"₹{(inv_amount * cash_pct):,.0f}", f"{int(cash_pct*100)}%")
    if not is_shariah: a4.metric("REITs / Bonds", f"₹{(inv_amount * reit_pct):,.0f}", f"{int(reit_pct*100)}%")
    else: a4.metric("ശരീഅത്ത് പാലനം", "100% Halal", "AAOIFI")

# ##################################################################
# 🏛️ MODULE 3: 50-YEAR MOAT VAULT & AUTO-COMPLETE LIVE SCANNER
# ##################################################################
elif main_menu == MENU_ITEMS[3]:
    st.title(MENU_ITEMS[3])

    with st.expander("📐 സ്റ്റോക്കുകൾ തിരഞ്ഞെടുക്കുന്നതിന്റെ മാനദണ്ഡങ്ങൾ (Stock Selection Criteria Blueprint)", expanded=False):
        st.markdown("""
        #### 1. വാറൻ ബഫറ്റ് & ചാർളി മംഗർ ക്വാളിറ്റി ഫിൽട്ടറുകൾ (Quantitative Moat Rules)
        * **ROCE / ROE >= 15%–20%:** മുടക്കുന്ന മൂലധനത്തിന് മുകളിൽ മികച്ച ലാഭം നേടുന്ന കമ്പനികൾ.
        * **Debt / Market Cap < 30% (കടരഹിത കമ്പനികൾ):** കടുത്ത സാമ്പത്തിക മാന്ദ്യം വന്നാലും തകർന്നുപോകാത്തവ.
        * **ഉയർന്ന ക്യാഷ് ഫ്ലോ & മാർജിൻ:** യഥാർത്ഥ പണം കമ്പനിയിലേക്ക് വരുന്നത്.
        
        #### 2. AAOIFI ശരീഅത്ത് സ്ക്രീനിംഗ് നിയമങ്ങൾ
        * **ബിസിനസ്സ് പരിശോധന:** പലിശ ബാങ്കിംഗ് (Riba), മദ്യം, പുകയില, ചൂതാട്ടം, ആയുധ നിർമ്മാണം എന്നിവയിലൊന്നും ഉൾപ്പെടാത്ത കമ്പനികൾ.
        * **സാമ്പത്തിക അനുപാതം:** കമ്പനിയുടെ ആകെ കടം മാർക്കറ്റ് ക്യാപ്പിന്റെ **33%-ൽ താഴെ** ആയിരിക്കണം (`Total Debt / Market Cap < 33%`).
        """)

    # FIXED: Auto-Complete Stock Dropdown + Robust Yahoo Finance Data Extraction!
    st.subheader("🔎 ഏത് സ്റ്റോക്കും പരിശോധിക്കാം: ഓട്ടോ-സെർച്ച് ലൈവ് സ്കാനർ" if is_ml else "🔎 Auto-Complete Live Fundamental, Shariah & Chart Scanner")
    st.caption("💡 താഴെയുള്ള ബോക്സിൽ ക്ലിക്ക് ചെയ്ത് സ്റ്റോക്കിന്റെ ആദ്യ അക്ഷരങ്ങൾ (ഉദാ: `I` അല്ലെങ്കിൽ `P`) ടൈപ്പ് ചെയ്യുമ്പോൾത്തന്നെ പേരുകൾ ലിസ്റ്റ് ആയി വരും!" if is_ml else "💡 Click the box below and type the first letters (e.g., 'I' or 'P') to see matching stocks instantly!")

    sc1, sc2 = st.columns([3, 1])
    with sc1:
        scan_ticker = select_stock_autocomplete(
            "പരിശോധിക്കേണ്ട സ്റ്റോക്ക് തിരഞ്ഞെടുക്കുക (Type to Search):" if is_ml else "Type to Search & Select NSE Stock:",
            NSE_STOCK_DIRECTORY,
            key_prefix="moat_scanner",
            default_index=3  # Defaults to POLYCAB so user immediately sees it working!
        )

    if scan_ticker:
        yf_sym = scan_ticker if (".NS" in scan_ticker or ".BO" in scan_ticker) else f"{scan_ticker}.NS"
        with st.spinner(f"⏳ {yf_sym} ഡാറ്റ പരിശോധിക്കുന്നു..."):
            try:
                tk = yf.Ticker(yf_sym)
                info = tk.info or {}
                hist_df = tk.history(period="1y")

                # Validate that ticker actually exists and has market data
                mcap = info.get("marketCap") or 0
                curr_p = info.get("currentPrice") or info.get("regularMarketPrice") or (float(hist_df['Close'].iloc[-1]) if not hist_df.empty else 0)

                if mcap == 0 and hist_df.empty:
                    st.error(f"❌ `{scan_ticker}` എന്ന സിംബൽ കണ്ടെത്താനായില്ല! മുകളിലെ ലിസ്റ്റിൽ നിന്ന് കമ്പനിയുടെ ശരിയായ NSE സിംബൽ തിരഞ്ഞെടുക്കുക.")
                else:
                    comp_name = info.get("longName") or info.get("shortName") or scan_ticker
                    sector = info.get("sector") or "Industrial / Diversified"
                    industry = info.get("industry") or sector
                    tot_debt = info.get("totalDebt") or 0
                    tot_cash = info.get("totalCash") or 0

                    # Robust ROE / Profit Margin calculation (Fallbacks if returnOnEquity is None)
                    raw_roe = info.get("returnOnEquity")
                    if raw_roe is None:
                        net_inc = info.get("netIncomeToCommon") or 0
                        book_val = info.get("bookValue") or 1
                        shares = info.get("sharesOutstanding") or 1
                        tot_eq = book_val * shares
                        roe = (net_inc / tot_eq * 100) if tot_eq > 0 else ((info.get("profitMargins") or 0) * 100)
                    else:
                        roe = raw_roe * 100

                    op_margin = (info.get("operatingMargins") or 0) * 100
                    pe_ratio = info.get("trailingPE") or info.get("forwardPE") or 0

                    debt_to_mcap = (tot_debt / mcap * 100) if mcap > 0 else 0.0
                    cash_to_mcap = (tot_cash / mcap * 100) if mcap > 0 else 0.0

                    non_halal_keywords = ["Bank", "Financial", "Insurance", "Tobacco", "Cigarette", "Brew", "Distill", "Alcohol", "Casino", "Gambling", "Aerospace & Defense"]
                    is_prohibited_sector = any(k.lower() in (sector + " " + industry + " " + comp_name).lower() for k in non_halal_keywords)
                    shariah_pass = (not is_prohibited_sector) and (debt_to_mcap < 33.0)
                    buffett_pass = (roe >= 14.0) and (debt_to_mcap < 30.0)

                    st.success(f"🏢 **{comp_name}** (`{yf_sym}`) | നിലവിലെ വില: **₹{curr_p:,.2f}** | P/E: `{pe_ratio:.1f}` | Op. Margin: `{op_margin:.1f}%`")
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("സെക്ടർ (Sector)", sector)
                    k2.metric("ROE / ലാഭക്ഷമത", f"{roe:.1f}%", "✅ മികച്ചത് (>=15%)" if roe >= 15 else "⚠️ ശരാശരി")
                    k3.metric("കടം / Market Cap", f"{debt_to_mcap:.1f}%", "✅ സുരക്ഷിതം (<33%)" if debt_to_mcap < 33 else "❌ അമിത കടം")
                    k4.metric("ശരീഅത്ത് & Moat സ്റ്റാറ്റസ്", "✅ ഹലാൽ (HALAL)" if shariah_pass else "❌ നോൺ-ഹലാൽ", "Buffett Moat: " + ("✅ Pass" if buffett_pass else "⚠️ Review"))

                    if is_prohibited_sector:
                        st.warning(f"⚠️ **ശരീഅത്ത് അറിയിപ്പ്:** `{comp_name}` ഉൾപ്പെടുന്ന സെക്ടർ (`{sector} - {industry}`) പലിശ/നിരോധിത വിഭാഗത്തിൽ വരുന്നതിനാൽ AAOIFI ശരീഅത്ത് പ്രകാരം ഹലാൽ അല്ല.")

                    if not hist_df.empty:
                        st.caption(f"📈 **{comp_name} - കഴിഞ്ഞ 1 വർഷത്തെ ലൈവ് പ്രൈസ് ചാർട്ട്:**")
                        st.line_chart(hist_df['Close'])
            except Exception as e:
                st.error(f"ഡാറ്റ എടുക്കുന്നതിൽ തടസ്സം: {e}")

    st.markdown("---")
    st.subheader("🏛️ തിരഞ്ഞെടുത്ത 50-Year Moat ഓഹരികളും എക്സിറ്റ് നിയമങ്ങളും")
    stocks_data = [
        {"Stock": "TCS", "Sector": "IT Services", "Metrics": "ROCE: 58% | കടം: 0.6% | മാർജിൻ: 25%", "Why Buy?": "കടരഹിത ഭീമൻ, ഉയർന്ന ക്യാഷ് ഫ്ലോ, ആഗോള ഐ.ടി കുത്തക.", "Red Flags": "AI കാരണം ബില്ലിംഗ് കുറയുന്നത്.", "Exit Trigger": "ഓപ്പറേറ്റിംഗ് മാർജിൻ 20%-ൽ താഴെയാകുകയോ കടം 33% കടക്കുകയോ ചെയ്താൽ വിൽക്കുക.", "Status": "✅ ഹലാൽ (AAOIFI Pass)"},
        {"Stock": "POLYCAB", "Sector": "Cables & Wires", "Metrics": "ROCE: 28% | കടം: 0.8% | മാർജിൻ: 14%", "Why Buy?": "ഇന്ത്യൻ വയർ-കേബിൾ വിപണിയിലെ 25%+ കുത്തക.", "Red Flags": "ചെമ്പ് വിലയിലുണ്ടാകുന്ന വലിയ ചാഞ്ചാട്ടം.", "Exit Trigger": "ഗവേണൻസ് പ്രശ്നങ്ങളോ വിപണി വിഹിതം നഷ്ടപ്പെടലോ ഉണ്ടായാൽ.", "Status": "✅ ഹലാൽ (AAOIFI Pass)"},
        {"Stock": "TATAELXSI", "Sector": "Design & EV", "Metrics": "ROCE: 42% | കടം: 0.4% | മാർജിൻ: 27%", "Why Buy?": "ഇലക്ട്രിക് വാഹന സോഫ്റ്റ്‌വെയർ മേഖലയിലെ കുത്തക.", "Red Flags": "യൂറോപ്യൻ വാഹന വിപണിയിലെ മാന്ദ്യം.", "Exit Trigger": "വാർഷിക വരുമാന വളർച്ച 10%-ൽ താഴെയായാൽ ഒഴിവാക്കുക.", "Status": "✅ ഹലാൽ (AAOIFI Pass)"},
        {"Stock": "SUNPHARMA", "Sector": "Specialty Pharma", "Metrics": "ROCE: 18% | കടം: 1.5% | മാർജിൻ: 26%", "Why Buy?": "ജീവൻരക്ഷാ മരുന്നുകൾ നിർമ്മിക്കുന്നതിനാൽ മാന്ദ്യത്തെ അതിജീവിക്കും.", "Red Flags": "USFDA റെഗുലേറ്ററി തടസ്സങ്ങൾ.", "Exit Trigger": "പ്രധാന പ്ലാന്റുകൾക്ക് സ്ഥിരമായി USFDA നിരോധനം വന്നാൽ.", "Status": "✅ ഹലാൽ (AAOIFI Pass)"}
    ]
    for s in stocks_data:
        with st.expander(f"📌 {s['Stock']} — ({s['Sector']}) | 📊 {s['Metrics']}"):
            st.markdown(f"**📐 തിരഞ്ഞെടുക്കാൻ കാരണമായ കണക്കുകൾ:** `{s['Metrics']}`")
            st.markdown(f"**🟢 എന്തുകൊണ്ട് വാങ്ങണം:** {s['Why Buy?']}")
            st.markdown(f"**⚠️ ശ്രദ്ധിക്കേണ്ട റിസ്കുകൾ:** {s['Red Flags']}")
            st.error(f"🛑 **എപ്പോൾ വിറ്റ് ഒഴിവാക്കണം (Exit Trigger):** {s['Exit Trigger']}")

# ##################################################################
# 💼 MODULE 4: LIVE PORTFOLIO & ALL-BROKER WATCHDOG (WITH AUTO-COMPLETE)
# ##################################################################
elif main_menu == MENU_ITEMS[4]:
    st.title(MENU_ITEMS[4])
    h_tab1, h_tab2 = st.tabs(["⚡ ലൈവ് ബ്രോക്കർ സിങ്ക് (Upstox / Dhan / Zerodha)", "📝 മാനുവൽ പോർട്ട്ഫോളിയോ (Groww / Other - Auto Search)"])

    with h_tab1:
        b_choice = st.selectbox("ബ്രോക്കർ തിരഞ്ഞെടുക്കുക:", ["Upstox", "Dhan", "Zerodha"])
        user_token = st.sidebar.text_input(f"{b_choice} Token:", value=state['token'], type="password", key="holdings_token")
        if st.button(f"🔄 {b_choice}-ൽ നിന്ന് പോർട്ട്ഫോളിയോ എടുക്കുക"):
            if not user_token:
                st.error(f"സൈഡ്‌ബാറിൽ {b_choice} Access Token നൽകുക!")
            else:
                headers = {'Accept': 'application/json', 'Authorization': f'Bearer {user_token}'}
                try:
                    res = requests.get('https://api.upstox.com/v2/portfolio/long-term-holdings', headers=headers, timeout=10)
                    data = res.json()
                    if data.get('status') == 'success' and len(data.get('data', [])) > 0:
                        st.dataframe(pd.DataFrame(data['data']), use_container_width=True)
                    else:
                        st.info(f"നിങ്ങളുടെ {b_choice} അക്കൗണ്ടിൽ നിലവിൽ ഹോൾഡിംഗ്സുകൾ ഒന്നും കണ്ടെത്തിയില്ല.")
                except Exception as e:
                    st.error(f"Error: {e}")

    with h_tab2:
        st.subheader("📝 Groww / Zerodha / മറ്റ് ആപ്പുകളിലെ ഓഹരികൾ ചേർക്കുക (Auto-Complete Search)")
        col_m1, col_m2, col_m3, col_m4 = st.columns([2, 1, 1, 1])
        with col_m1:
            m_sym = select_stock_autocomplete("സ്റ്റോക്ക് തിരഞ്ഞെടുക്കുക (Type to Search):", NSE_STOCK_DIRECTORY, key_prefix="port_man", default_index=0)
        m_qty = col_m2.number_input("വാങ്ങിയ എണ്ണം (Qty):", value=1, min_value=1, step=1)
        m_bp = col_m3.number_input("വാങ്ങിയ വില (₹):", value=1000.0, min_value=1.0, step=10.0)
        m_plat = col_m4.selectbox("പ്ലാറ്റ്‌ഫോം:", ["Groww", "Zerodha", "AngelOne", "Upstox", "Other"])

        if st.button("➕ പോർട്ട്ഫോളിയോയിലേക്ക് ചേർക്കുക", type="primary"):
            if m_sym:
                conn = get_db_connection()
                conn.execute("INSERT INTO manual_portfolio (user_hash, symbol, qty, buy_price, buy_date, notes) VALUES (?, ?, ?, ?, ?, ?)",
                             (USER_HASH, m_sym, m_qty, m_bp, datetime.date.today().strftime("%Y-%m-%d"), m_plat))
                conn.commit()
                conn.close()
                st.success(f"✅ {m_sym} പോർട്ട്ഫോളിയോയിൽ ചേർത്തു!")
                st.rerun()

        conn = get_db_connection()
        df_man = pd.read_sql_query("SELECT symbol AS Stock, qty AS Qty, buy_price AS [Buy Price], buy_date AS [Date], notes AS Broker FROM manual_portfolio WHERE user_hash=? ORDER BY id DESC", conn, params=(USER_HASH,))
        conn.close()
        if not df_man.empty:
            st.dataframe(df_man, use_container_width=True, hide_index=True)

# ##################################################################
# 🎟️ MODULE 5: IPO RADAR & RED-FLAG ANALYZER (NEW!)
# ##################################################################
elif main_menu == MENU_ITEMS[5]:
    st.title("🎟️ ഐ.പി.ഒ (IPO) റഡാർ & വാറൻ ബഫറ്റ് റെഡ്-ഫ്ലാഗ് ചെക്കർ" if is_ml else "🎟️ IPO Radar & Institutional Red-Flag Analyzer")
    st.caption("പുതിയതായി വരുന്ന ഐ.പി.ഒകളിൽ (IPO) പണം നിക്ഷേപിക്കുന്നത് സുരക്ഷിതമാണോ? അതോ പ്രൊമോട്ടർമാരുടെ കെണിയാണോ എന്ന് പരിശോധിക്കാം." if is_ml else "Evaluate upcoming IPOs against institutional valuation, OFS traps, and Shariah compliance.")

    with st.expander("📐 ഒരു IPO-യിൽ നിക്ഷേപിക്കുന്നതിന് മുൻപ് നിർബന്ധമായും നോക്കേണ്ട 5 നിയമങ്ങൾ (IPO Selection Criteria)", expanded=True):
        st.markdown("""
        1. **OFS കെണി (Offer For Sale vs. Fresh Issue):** IPO വഴി സമാഹരിക്കുന്ന പണം കമ്പനിയുടെ വളർച്ചയ്ക്കാണോ (**Fresh Issue**), അതോ പഴയ ഉടമകൾ അവരുടെ ഓഹരി വിറ്റ് പണവുമായി പുറത്തുപോകാനാണോ (**OFS**) എന്ന് നോക്കുക. **OFS 50%-ൽ കൂടുതലാണെങ്കിൽ സൂക്ഷിക്കുക!**
        2. **വില നിലവാരം (P/E Valuation Trap):** അതേ മേഖലയിലുള്ള മറ്റ് ലിസ്റ്റഡ് കമ്പനികളേക്കാൾ അമിതമായ വിലയിലാണ് (High P/E) IPO വരുന്നതെങ്കിൽ ലിസ്റ്റിംഗിന് ശേഷം വില കുത്തനെ ഇടിയാൻ സാധ്യതയുണ്ട്.
        3. **കടം വീട്ടൽ vs വളർച്ച:** Fresh Issue പണം പുതിയ ഫാക്ടറികൾ തുടങ്ങുന്നതിനും കടം പൂർണ്ണമായി തീർക്കുന്നതിനും ആണെങ്കിൽ അത് പോസിറ്റീവ് ആണ്.
        4. **SME IPO അപകടം:** ₹1 ലക്ഷം രൂപയിലധികം മിനിമം നിക്ഷേപം വേണ്ട **SME IPO-കളിൽ** കൃത്രിമത്വം (Pump & Dump) നടക്കാൻ സാധ്യത കൂടുതലാണ്. തുടക്കക്കാർ **Mainboard IPO** (1 Lot = ~₹14,000 - ₹15,000) മാത്രം തിരഞ്ഞെടുക്കുക.
        5. **എങ്ങനെ അപേക്ഷിക്കാം?** നിങ്ങളുടെ ബ്രോക്കർ ആപ്പിൽ (Upstox / Groww / Zerodha) **UPI ASBA** വഴി അപേക്ഷിക്കാം. പണം ബാങ്കിൽ ബ്ലോക്ക് ആകുകയേ ഉള്ളൂ, ഓഹരി ലഭിച്ചാൽ മാത്രമേ പണം കട്ട് ആവുകയുള്ളൂ!
        """)

    st.subheader("🧮 ലൈവ് IPO ഗുണനിലവാര കാൽക്കുലേറ്റർ (Test Any Upcoming IPO)" if is_ml else "🧮 Interactive IPO Quality & Risk Scorecard")
    ic1, ic2, ic3 = st.columns(3)
    ipo_name = ic1.text_input("IPO കമ്പനിയുടെ പേര്:", value="Sample Tech IPO")
    ofs_pct = ic2.slider("OFS ശതമാനം (പഴയ ഉടമകൾ വിൽക്കുന്നത് %):", 0, 100, 25)
    pe_diff = ic3.selectbox("സെക്ടറിലെ മറ്റ് കമ്പനികളുമായി താരതമ്യം ചെയ്യുമ്പോൾ വില (P/E):", ["🟢 കുറഞ്ഞ/ന്യായമായ വില (Fair Valuation)", "🟡 ശരാശരി വില (Fully Priced)", "🔴 അമിത വില (Overpriced > 50x P/E)"])

    ic4, ic5, ic6 = st.columns(3)
    gmp_pct = ic4.slider("നിലവിലെ GMP (Grey Market Premium %):", -20, 100, 20)
    debt_post = ic5.selectbox("IPO-ക്ക് ശേഷം കമ്പനിയുടെ കടം:", ["🟢 കടരഹിതം (< 20% Debt)", "🟡 മിതമായ കടം", "🔴 അമിത കടം (> 33% Debt)"])
    ipo_lot_size = ic6.number_input("1 ലോട്ടിന്റെ തുക (Retail 1 Lot Amount ₹):", value=14800.0, step=200.0)

    score = 100
    reasons = []
    if ofs_pct > 50:
        score -= 35
        reasons.append(f"🚨 **OFS കെണി ({ofs_pct}%):** പഴയ ഉടമകൾ കമ്പനി വിട്ടുപോകുന്നു! കമ്പനിക്ക് ഈ പണം ലഭിക്കില്ല.")
    else:
        reasons.append(f"✅ **Fresh Issue മുൻഗണന ({100-ofs_pct}%):** പണം കമ്പനിയുടെ വളർച്ചയ്ക്ക് ഉപയോഗിക്കുന്നു.")

    if "🔴" in pe_diff:
        score -= 30
        reasons.append("🚨 **അമിത വില (Overpriced):** ലിസ്റ്റിംഗിന് ശേഷം ഓഹരി വില ഇടിയാൻ സാധ്യതയുണ്ട്.")
    if gmp_pct < 10:
        score -= 20
        reasons.append(f"⚠️ **കുറഞ്ഞ GMP ({gmp_pct}%):** ലിസ്റ്റിംഗ് ലാഭം (Listing Gain) കിട്ടാൻ സാധ്യത കുറവാണ്.")
    if "🔴" in debt_post:
        score -= 25
        reasons.append("🚨 **ഉയർന്ന കടം:** ശരീഅത്ത് മോഡിലും ദീർഘകാല നിക്ഷേപത്തിനും അനുയോജ്യമല്ല.")

    if score >= 75:
        st.success(f"🌟 **IPO സ്കോർ: {score}/100 — മികച്ച IPO (Apply for Listing Gain / Long Term)!** നിക്ഷേപിക്കേണ്ട തുക: 1 Lot (`₹{ipo_lot_size:,.0f}`).")
    elif score >= 50:
        st.warning(f"⚠️ **IPO സ്കോർ: {score}/100 — ശരാശരി (ജാഗ്രത പാലിക്കുക)!** അവസാന ദിവസത്തെ QIB സബ്സ്ക്രിപ്ഷൻ (>10x) നോക്കി മാത്രം തീരുമാനിക്കുക.")
    else:
        st.error(f"🛑 **IPO സ്കോർ: {score}/100 — അപകടകരം (AVOID IPO)!** വാറൻ ബഫറ്റ് നിയമപ്രകാരം ഇത്തരം അമിത വിലയുള്ള OFS ഐ.പി.ഒകൾ ഒഴിവാക്കുക.")

    for r in reasons:
        st.markdown(f"- {r}")

# ##################################################################
# 📜 MODULE 6: BONDS, G-SECS & HALAL FIXED-INCOME ALTERNATIVES (NEW!)
# ##################################################################
elif main_menu == MENU_ITEMS[6]:
    st.title("📜 ബോണ്ടുകൾ, കടപ്പത്രങ്ങൾ & സ്ഥിരവരുമാന മാർഗ്ഗങ്ങൾ" if is_ml else "📜 Bonds, G-Secs & Halal Fixed-Income Alternatives")

    if is_shariah:
        st.error("🌙 **പ്രധാന ശരീഅത്ത് നിയമം (AAOIFI Standard):** സാധാരണ ഗവൺമെന്റ് ബോണ്ടുകളും കോർപ്പറേറ്റ് കടപ്പത്രങ്ങളും ബാങ്ക് എഫ്.ഡിയും (FD) 100% പലിശ (Riba) അധിഷ്ഠിതമായതിനാൽ ശരീഅത്ത് പ്രകാരം നിഷിദ്ധമാണ്.")
        st.success("✅ **പലിശയില്ലാതെ സ്ഥിരവരുമാനവും സുരക്ഷയും നേടാനുള്ള 4 ഹലാൽ ബദൽ മാർഗ്ഗങ്ങൾ (Halal Fixed-Income Alternatives):**")
        halal_income = [
            {"ഹലാൽ മാർഗ്ഗം (Instrument)": "1. ഉയർന്ന ഡിവിഡന്റ് നൽകുന്ന കടരഹിത ഹലാൽ ഓഹരികൾ (High-Dividend Halal Stocks)", "പ്രതീക്ഷിക്കുന്ന വരുമാനം": "2.5% - 4.5% Div + വളർച്ച", "എങ്ങനെ പ്രവർത്തിക്കുന്നു?": "പലിശയ്ക്ക് പകരം കമ്പനിയുടെ യഥാർത്ഥ ലാഭവിഹിതം (Dividend) വർഷാവർഷം ബാങ്ക് അക്കൗണ്ടിലേക്ക് ലഭിക്കുന്നു (ഉദാ: TCS, HCLTECH, INFOSYS)."},
            {"ഹലാൽ മാർഗ്ഗം (Instrument)": "2. വാടക വരുമാനം നൽകുന്ന റിയൽ എസ്റ്റേറ്റ് / കമേഴ്സ്യൽ ഷോപ്പുകൾ (Ijarah / Rental Yield)", "പ്രതീക്ഷിക്കുന്ന വരുമാനം": "6% - 9% വാർഷിക വാടക", "എങ്ങനെ പ്രവർത്തിക്കുന്നു?": "യഥാർത്ഥ ഭൂമിയിലോ കെട്ടിടങ്ങളിലോ നിക്ഷേപിച്ച് പലിശരഹിതമായി മാസവാടക കൈപ്പറ്റുന്ന രീതി."},
            {"ഹലാൽ മാർഗ്ഗം (Instrument)": "3. ഫിസിക്കൽ ഗോൾഡ് ഇ.ടി.എഫ് (GOLDBEES - AAOIFI #57)", "പ്രതീക്ഷിക്കുന്ന വരുമാനം": "11% - 14% വാർഷിക വളർച്ച", "എങ്ങനെ പ്രവർത്തിക്കുന്നു?": "പണപ്പെരുപ്പത്തെ തോൽപ്പിക്കാൻ പലിശ ബാങ്കിൽ ഇടുന്നതിന് പകരം 24K ഫിസിക്കൽ സ്വർണ്ണമായി സൂക്ഷിക്കാം, ആവശ്യമുള്ളപ്പോൾ 1 മിനിറ്റിൽ വിറ്റ് പണമാക്കാം."},
            {"ഹലാൽ മാർഗ്ഗം (Instrument)": "4. സുക്കൂക്ക് / ഇസ്‌ലാമിക് അസറ്റ് ലീസിംഗ് (Sukuk / Equipment Leasing)", "പ്രതീക്ഷിക്കുന്ന വരുമാനം": "8% - 11% ലാഭവിഹിതം", "എങ്ങനെ പ്രവർത്തിക്കുന്നു?": "വ്യവസായ സ്ഥാപനങ്ങൾക്ക് യന്ത്രസാമഗ്രികൾ വാങ്ങി വാടകയ്ക്ക് നൽകി അതിന്റെ വാടക പങ്കിട്ടെടുക്കുന്ന രീതി."}
        ]
        st.dataframe(pd.DataFrame(halal_income), use_container_width=True, hide_index=True)
    else:
        st.info("💡 **കൺവെൻഷണൽ ബോണ്ട് നിക്ഷേപകർ ശ്രദ്ധിക്കാൻ:** ഉയർന്ന പലിശ വാഗ്ദാനം ചെയ്യുന്ന (12%–15%) ബി-ഗ്രേഡ് കമ്പനികളുടെ ബോണ്ടുകൾ വാങ്ങിയാൽ കമ്പനി പൂട്ടിപ്പോകുമ്പോൾ മുതലും നഷ്ടപ്പെടും! എപ്പോഴും **Sovereign (RBI)** അല്ലെങ്കിൽ **AAA Rated** ബോണ്ടുകൾ മാത്രം തിരഞ്ഞെടുക്കുക.")
        bonds_list = [
            {"Bond / Instrument": "1. RBI Retail Direct G-Secs (സർക്കാർ കടപ്പത്രങ്ങൾ)", "Safety Rating": "🛡️ 100% Sovereign Guarantee", "Yield / Return": "7.0% - 7.3% p.a.", "How to Buy": "RBI Retail Direct അല്ലെങ്കിൽ Zerodha Coin / Upstox വഴി ₹10,000 മുതൽ വാങ്ങാം."},
            {"Bond / Instrument": "2. RBI Treasury Bills (91 / 182 / 364 Days T-Bills)", "Safety Rating": "🛡️ 100% Sovereign Guarantee", "Yield / Return": "6.8% - 7.0% p.a.", "How to Buy": "1 വർഷത്തിൽ താഴെ പണം സുരക്ഷിതമായി സൂക്ഷിക്കാൻ ബാങ്ക് FD-യേക്കാൾ മികച്ചത്."},
            {"Bond / Instrument": "3. AAA-Rated PSU Corporate Bonds (NHAI, REC, PFC, IRFC)", "Safety Rating": "✅ AAA (Highest Safety)", "Yield / Return": "7.5% - 8.2% p.a.", "How to Buy": "സർക്കാർ പൊതുമേഖലാ സ്ഥാപനങ്ങളുടെ സുരക്ഷിത ബോണ്ടുകൾ."},
            {"Bond / Instrument": "4. Bharat Bond ETF (Edelweiss)", "Safety Rating": "✅ AAA PSU Basket", "Yield / Return": "7.2% - 7.6% p.a.", "How to Buy": "സ്റ്റോക്ക് പോലെ എപ്പോൾ വേണമെങ്കിലും വാങ്ങാനും വിൽക്കാനും കഴിയുന്ന ബോണ്ട് ETF."}
        ]
        st.dataframe(pd.DataFrame(bonds_list), use_container_width=True, hide_index=True)

# ##################################################################
# 📈 MODULE 7: MUTUAL FUNDS & ETFS
# ##################################################################
elif main_menu == MENU_ITEMS[7]:
    st.title(MENU_ITEMS[7])
    if is_shariah:
        funds = [
            {"Fund": "Tata Ethical Fund (Direct Growth)", "Type": "Shariah Equity", "3Y CAGR": "20.8%", "5Y CAGR": "22.5%", "Expense": "0.85%", "തിരഞ്ഞെടുക്കാൻ കാരണം": "Nifty 500 Shariah ബെഞ്ച്മാർക്ക്, ബാങ്കിംഗ് ഓഹരികളില്ല, 28+ വർഷത്തെ മികച്ച ചരിത്രം."},
            {"Fund": "Taurus Ethical Fund (Direct Growth)", "Type": "Shariah Equity", "3Y CAGR": "22.1%", "5Y CAGR": "21.2%", "Expense": "0.95%", "തിരഞ്ഞെടുക്കാൻ കാരണം": "കർശനമായ AAOIFI സ്ക്രീനിംഗ്, മികച്ച മിഡ്-ക്യാപ് വളർച്ച."},
            {"Fund": "Nippon India Gold BeES", "Type": "Physical Gold ETF", "3Y CAGR": "16.4%", "5Y CAGR": "14.8%", "Expense": "0.55%", "തിരഞ്ഞെടുക്കാൻ കാരണം": "99.5% ശുദ്ധമായ ഫിസിക്കൽ സ്വർണ്ണ പിന്തുണ (AAOIFI Standard #57)."}
        ]
    else:
        funds = [
            {"Fund": "Parag Parikh Flexi Cap Fund", "Type": "Flexi Cap", "3Y CAGR": "21.5%", "5Y CAGR": "24.2%", "Expense": "0.62%", "തിരഞ്ഞെടുക്കാൻ കാരണം": "വാല്യൂ ഇൻവെസ്റ്റിംഗ്, യു.എസ് ടെക് കമ്പനികളിലെ നിക്ഷേപം."},
            {"Fund": "UTI Nifty 50 Index Fund", "Type": "Passive Index", "3Y CAGR": "15.8%", "5Y CAGR": "16.5%", "Expense": "0.18%", "തിരഞ്ഞെടുക്കാൻ കാരണം": "ഏറ്റവും കുറഞ്ഞ ചെലവ് (0.18%), ഇന്ത്യയിലെ മികച്ച 50 കമ്പനികൾ."},
            {"Fund": "Quant Small Cap Fund", "Type": "Small Cap", "3Y CAGR": "34.2%", "5Y CAGR": "38.5%", "Expense": "0.77%", "തിരഞ്ഞെടുക്കാൻ കാരണം": "ഉയർന്ന ദീർഘകാല വളർച്ചയ്ക്ക്."}
        ]
    st.dataframe(pd.DataFrame(funds), use_container_width=True, hide_index=True)

# ##################################################################
# 🌍 MODULE 8: GLOBAL MARKETS (INDMONEY / VESTED WITH AUTO-COMPLETE)
# ##################################################################
elif main_menu == MENU_ITEMS[8]:
    st.title(MENU_ITEMS[8])
    uc1, uc2, uc3, uc4 = st.columns([2, 1, 1, 1])
    with uc1:
        u_sym = select_stock_autocomplete("US സ്റ്റോക്ക് തിരഞ്ഞെടുക്കുക (Type to Search):", US_STOCK_DIRECTORY, key_prefix="us_port", default_index=0)
    u_qty = uc2.number_input("എണ്ണം (Fractional Qty):", value=1.0, min_value=0.01, step=0.1)
    u_bp = uc3.number_input("വാങ്ങിയ വില ($ USD):", value=100.0, min_value=1.0, step=5.0)
    u_plat = uc4.selectbox("പ്ലാറ്റ്‌ഫോം:", ["INDmoney", "Vested", "Alpaca API", "Interactive Brokers"])

    if st.button("➕ US പോർട്ട്ഫോളിയോയിലേക്ക് ചേർക്കുക", type="primary"):
        if u_sym:
            conn = get_db_connection()
            conn.execute("INSERT INTO us_portfolio (user_hash, symbol, qty, buy_price_usd, buy_usd_inr, platform) VALUES (?, ?, ?, ?, ?, ?)",
                         (USER_HASH, u_sym, u_qty, u_bp, 84.0, u_plat))
            conn.commit()
            conn.close()
            st.success(f"✅ {u_sym} saved!")
            st.rerun()

    conn = get_db_connection()
    df_us = pd.read_sql_query("SELECT symbol, qty, buy_price_usd, platform FROM us_portfolio WHERE user_hash=? ORDER BY id DESC", conn, params=(USER_HASH,))
    conn.close()
    if not df_us.empty:
        st.dataframe(df_us, use_container_width=True, hide_index=True)

# ##################################################################
# 🥇 MODULE 9: GOLD & CRISIS HEDGE ASSETS
# ##################################################################
elif main_menu == MENU_ITEMS[9]:
    st.title(MENU_ITEMS[9])
    gold_data = [
        {"Instrument": "Nippon India Gold BeES (GOLDBEES)", "Backing": "99.5% Physical Bullion", "Expense": "0.55%", "Compliance": "✅ AAOIFI Standard #57", "തിരഞ്ഞെടുക്കാൻ കാരണം": "NSE-ൽ ഏറ്റവും ഉയർന്ന വോളിയം, 100% ഫിസിക്കൽ ഗോൾഡ് പിന്തുണ."},
        {"Instrument": "HDFC Gold ETF (HDFCGOLD)", "Backing": "99.5% Physical Bullion", "Expense": "0.30%", "Compliance": "✅ AAOIFI Standard #57", "തിരഞ്ഞെടുക്കാൻ കാരണം": "ദീർഘകാല നിക്ഷേപത്തിന് ഏറ്റവും കുറഞ്ഞ ചെലവ് (0.30%)."},
        {"Instrument": "Nippon India Silver ETF (SILVERBEES)", "Backing": "99.9% Physical Silver", "Expense": "0.50%", "Compliance": "✅ AAOIFI Standard #57", "തിരഞ്ഞെടുക്കാൻ കാരണം": "ഇലക്ട്രിക് വാഹന/സോളാർ വ്യവസായ ആവശ്യകതയും സുരക്ഷിത നിക്ഷേപവും."}
    ]
    st.dataframe(pd.DataFrame(gold_data), use_container_width=True, hide_index=True)

# ##################################################################
# ⚡ MODULE 10: INTRADAY ALGO TRADING BOT
# ##################################################################
elif main_menu == MENU_ITEMS[10]:
    st.title("⚡ മൾട്ടി-ബ്രോക്കർ ഇൻസ്റ്റിറ്റ്യൂഷണൽ ഇൻട്രാഡേ ബോട്ട്")
    with st.expander("📐 ബോട്ട് എങ്ങനെയാണ് ട്രേഡ് തിരഞ്ഞെടുക്കുന്നത്? (6-ഇന മാനദണ്ഡങ്ങൾ)", expanded=False):
        st.markdown("""
        1. **നിഫ്റ്റി 50 ട്രെൻഡ് ഗാർഡ്:** `Nifty Price >= 20 EMA` (1-min)
        2. **VWAP ഫിൽട്ടർ:** `Stock Price > Intraday VWAP`
        3. **EMA മൊമെന്റം ക്രോസ്:** `EMA 9 crosses above EMA 21`
        4. **വോളിയം സർജ്:** `Volume >= 1.2x (20-period SMA)`
        5. **RSI സുരക്ഷാ പരിധി:** `50 <= RSI (14) <= 68`
        6. **ATR സ്റ്റോപ്പ്-ലോസ് & 3:15 PM എക്സിറ്റ്:** `SL = 1.5x ATR` / `Target = 3.0x ATR`
        """)

    selected_broker = st.selectbox("🏦 ബ്രോക്കർ തിരഞ്ഞെടുക്കുക:", ["Upstox (API v2)", "Dhan (DhanHQ API)", "Zerodha (Kite Connect)", "Angel One (SmartAPI)"])
    state['broker'] = selected_broker.split(" ")[0]

    if state['token']:
        st.success("✅ **Access Token റെഡിയാണ്!** ഇനി ഇടതുവശത്തെ സൈഡ്‌ബാറിൽ **▶️ START BOT** അമർത്താം.")

    with st.expander("🔑 ഓട്ടോമാറ്റിക് ടോക്കൺ ജനറേറ്റർ (1-Click Auto Login)", expanded=not bool(state['token'])):
        oa1, oa2, oa3 = st.columns(3)
        api_k = oa1.text_input(f"{state['broker']} API Key:", value=state['api_key'], type="password")
        api_s = oa2.text_input(f"{state['broker']} API Secret:", value=state['api_secret'], type="password")
        red_u = oa3.text_input("Redirect URL:", value=state['redirect_uri'])

        if api_k != state['api_key'] or api_s != state['api_secret'] or red_u != state['redirect_uri']:
            state['api_key'], state['api_secret'], state['redirect_uri'] = api_k.strip(), api_s.strip(), red_u.strip()
            save_user_creds(USER_HASH, state['api_key'], state['api_secret'], state['redirect_uri'], state['tg_token'], state['tg_chat'], state['token'], state['broker'])

        if state['broker'] == "Upstox" and state['api_key'] and state['api_secret'] and state['redirect_uri']:
            encoded_redir = urllib.parse.quote(state['redirect_uri'], safe='')
            auth_url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={state['api_key']}&redirect_uri={encoded_redir}&state={USER_HASH}"
            st.link_button("🚀 Step 1: 1-Click Auto Login with Upstox", auth_url, type="primary")

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ ബോട്ട് കൺട്രോൾ പാനൽ")
    mode_choice = st.sidebar.radio("ട്രേഡിംഗ് മോഡ്:", ["പേപ്പർ ട്രേഡിംഗ് (സുരക്ഷിതം)", "ലൈവ് റിയൽ മണി"], index=0 if state['mode'] == "PAPER" else 1)
    token_input = st.sidebar.text_input(f"{state['broker']} Access Token:", value=state['token'], type="password")
    capital_input = st.sidebar.number_input("ക്യാപിറ്റൽ (₹):", value=float(state['capital']), min_value=500.0, step=500.0)
    risk_input = st.sidebar.number_input("ഒരു ട്രേഡിലെ റിസ്ക് (₹):", value=float(state['risk']), min_value=10.0, step=25.0)
    tg_token_input = st.sidebar.text_input("Telegram Bot Token:", value=state['tg_token'], type="password")
    tg_chat_input = st.sidebar.text_input("Telegram Chat ID:", value=state['tg_chat'])

    col1, col2 = st.sidebar.columns(2)
    if col1.button("▶️ START BOT", use_container_width=True):
        if not token_input:
            st.sidebar.error("Access Token നൽകുക!")
        else:
            state['token'] = token_input
            state['capital'] = capital_input
            state['risk'] = risk_input
            state['mode'] = "PAPER" if "പേപ്പർ" in mode_choice else "LIVE"
            state['tg_token'] = tg_token_input
            state['tg_chat'] = tg_chat_input
            save_user_creds(USER_HASH, state['api_key'], state['api_secret'], state['redirect_uri'], state['tg_token'], state['tg_chat'], state['token'], state['broker'])
            state['running'] = True
            st.sidebar.success("ബോട്ട് സജീവം!")

    if col2.button("⏹️ STOP BOT", use_container_width=True):
        state['running'] = False
        st.sidebar.warning("ബോട്ട് നിർത്തി!")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ബോട്ട് സ്റ്റാറ്റസ്", "🟢 സർവറിൽ ഓടുന്നു" if state['running'] else "🔴 ഓഫ് ആണ്")
    m2.metric("നിഫ്റ്റി 50 ട്രെൻഡ്", state['nifty_status'])
    m3.metric("തുടർച്ചയായ നഷ്ടങ്ങൾ", f"{state['consecutive_losses']} / 2")
    m4.metric("ക്യാപിറ്റൽ", f"₹{state['capital']:,.2f}")

# ##################################################################
# 📚 MODULE 11: INVESTMENT AUDIT JOURNAL (WITH AUTO-COMPLETE)
# ##################################################################
elif main_menu == MENU_ITEMS[11]:
    st.title(MENU_ITEMS[11])
    with st.expander("➕ പുതിയ നിക്ഷേപ തീരുമാനം രേഖപ്പെടുത്തുക", expanded=True):
        j_col1, j_col2, j_col3 = st.columns([2, 1, 1])
        with j_col1:
            j_asset = select_stock_autocomplete("സ്റ്റോക്ക് / അസറ്റ് തിരഞ്ഞെടുക്കുക:", NSE_STOCK_DIRECTORY, key_prefix="journal_sel", default_index=0)
        j_action = j_col2.selectbox("തീരുമാനം:", ["BUY (വാങ്ങി)", "HOLD (തുടരുന്നു)", "SELL (വിറ്റു)", "WATCHLIST"])
        j_status = j_col3.selectbox("വിഭാഗം:", ["✅ Long-Term Moat", "🌙 Halal Verified", "⚠️ Tactical Bet", "🛑 Rule Exit"])
        j_reason = st.text_area("എന്തുകൊണ്ട് ഈ തീരുമാനം എടുത്തു? (Thesis & Exit Rule):")

        if st.button("💾 ജേർണലിൽ സേവ് ചെയ്യുക", type="primary"):
            if j_asset and j_reason:
                conn = get_db_connection()
                conn.execute("INSERT INTO wealth_audit (user_hash, date, asset, category, action, status, veteran_reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (USER_HASH, datetime.date.today().strftime("%Y-%m-%d"), j_asset, "Equity/Asset", j_action, j_status, j_reason))
                conn.commit()
                conn.close()
                st.success("✅ സേവ് ചെയ്തു!")
                st.rerun()

    conn = get_db_connection()
    df_audit = pd.read_sql_query("SELECT date AS Date, asset AS Asset, action AS Action, status AS Classification, veteran_reason AS [Thesis / Notes] FROM wealth_audit WHERE user_hash=? ORDER BY id DESC LIMIT 50", conn, params=(USER_HASH,))
    conn.close()
    if not df_audit.empty:
        st.dataframe(df_audit, use_container_width=True, hide_index=True)
