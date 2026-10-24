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
import xml.etree.ElementTree as ET
import yfinance as yf

# ==========================================
# 🌐 PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Autonomous Wealth OS & Live Market Scanner", layout="wide", page_icon="🏛️")

# ==========================================
# 🔎 LIVE GLOBAL STOCK & MUTUAL FUND SEARCH APIS (ALL NSE, BSE, US & AMFI)
# ==========================================
@st.cache_data(ttl=600)
def live_search_yahoo_tickers(query_str, market_filter="ALL"):
    """Searches Yahoo Finance live database for ANY NSE (.NS), BSE (.BO), or US stock."""
    if not query_str or len(query_str.strip()) < 1:
        return []
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query_str.strip())}&quotesCount=25&newsCount=0"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    results = []
    try:
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            quotes = res.json().get("quotes", [])
            for q in quotes:
                sym = q.get("symbol", "")
                name = q.get("longname") or q.get("shortname") or sym
                exch = q.get("exchDisp") or q.get("exchange") or ""
                qtype = q.get("quoteType", "")
                if qtype not in ["EQUITY", "ETF", "INDEX"]:
                    continue
                if market_filter == "INDIA" and not (sym.endswith(".NS") or sym.endswith(".BO")):
                    continue
                if market_filter == "US" and (sym.endswith(".NS") or sym.endswith(".BO")):
                    continue
                results.append(f"{sym} | {name} ({exch})")
    except Exception:
        pass
    return results

@st.cache_data(ttl=900)
def analyze_any_stock_deep(ticker_sym):
    """Performs a complete institutional Pros, Cons, Shariah & Horizon (1Y/5Y/10Y) audit on ANY stock."""
    tk = yf.Ticker(ticker_sym)
    info = tk.info or {}
    hist = tk.history(period="5y")
    if hist.empty:
        hist = tk.history(period="1y")

    if hist.empty and not info.get("regularMarketPrice") and not info.get("currentPrice"):
        return None

    curr_p = info.get("currentPrice") or info.get("regularMarketPrice") or (float(hist['Close'].iloc[-1]) if not hist.empty else 0.0)
    comp_name = info.get("longName") or info.get("shortName") or ticker_sym
    sector = info.get("sector") or "Diversified / ETF"
    industry = info.get("industry") or sector
    currency = info.get("currency", "INR")
    curr_sym = "₹" if currency == "INR" else "$"

    mcap = info.get("marketCap") or 0
    tot_debt = info.get("totalDebt") or 0
    tot_cash = info.get("totalCash") or 0
    rev_growth = (info.get("revenueGrowth") or 0) * 100
    earn_growth = (info.get("earningsGrowth") or 0) * 100
    op_margin = (info.get("operatingMargins") or 0) * 100
    prof_margin = (info.get("profitMargins") or 0) * 100
    pe_ratio = info.get("trailingPE") or info.get("forwardPE") or 0
    pb_ratio = info.get("priceToBook") or 0
    div_yield = (info.get("dividendYield") or 0) * 100

    # Robust ROE calculation with fallback
    raw_roe = info.get("returnOnEquity")
    if raw_roe is not None:
        roe = raw_roe * 100
    else:
        net_inc = info.get("netIncomeToCommon") or 0
        bv = info.get("bookValue") or 0
        sh = info.get("sharesOutstanding") or 0
        roe = (net_inc / (bv * sh) * 100) if (bv * sh) > 0 else prof_margin

    debt_to_mcap = (tot_debt / mcap * 100) if mcap > 0 else 0.0
    cash_to_mcap = (tot_cash / mcap * 100) if mcap > 0 else 0.0

    # Price Returns & Technical Trend (200 DMA)
    ret_1y, ret_5y, above_200dma = 0.0, 0.0, True
    if not hist.empty:
        closes = hist['Close']
        if len(closes) >= 200:
            dma200 = closes.rolling(200).mean().iloc[-1]
            above_200dma = curr_p >= dma200
        if len(closes) >= 252:
            ret_1y = ((curr_p - float(closes.iloc[-252])) / float(closes.iloc[-252])) * 100
        else:
            ret_1y = ((curr_p - float(closes.iloc[0])) / float(closes.iloc[0])) * 100
        ret_5y = ((curr_p - float(closes.iloc[0])) / float(closes.iloc[0])) * 100

    # AAOIFI Shariah Check
    non_halal_kw = ["Bank", "Financial", "Insurance", "Tobacco", "Cigarette", "Brew", "Distill", "Alcohol", "Casino", "Gambling", "Defense", "Pork"]
    is_prohibited_sec = any(k.lower() in (sector + " " + industry + " " + comp_name).lower() for k in non_halal_kw)
    shariah_pass = (not is_prohibited_sec) and (debt_to_mcap < 33.0)

    # Pros & Cons Generation
    pros, cons = [], []
    if roe >= 15:
        pros.append(f"ഉയർന്ന മൂലധന ലാഭക്ഷമത (Strong ROE: {roe:.1f}% >= 15%)")
    else:
        cons.append(f"കുറഞ്ഞ ലാഭക്ഷമത (Low ROE: {roe:.1f}% < 15%)")

    if debt_to_mcap < 15:
        pros.append(f"വളരെ കുറഞ്ഞ കടബാധ്യത (Low Debt/MCap: {debt_to_mcap:.1f}%)")
    elif debt_to_mcap >= 33:
        cons.append(f"അമിതമായ കടബാധ്യത (High Debt/MCap: {debt_to_mcap:.1f}% >= 33%)")

    if op_margin >= 15:
        pros.append(f"മികച്ച ഓപ്പറേറ്റിംഗ് മാർജിൻ (Operating Margin: {op_margin:.1f}%)")
    elif op_margin < 8 and op_margin != 0:
        cons.append(f"കുറഞ്ഞ ഓപ്പറേറ്റിംഗ് മാർജിൻ ({op_margin:.1f}%)")

    if rev_growth > 10:
        pros.append(f"മികച്ച വരുമാന വളർച്ച (Revenue Growth: +{rev_growth:.1f}% YoY)")
    elif rev_growth < 0:
        cons.append(f"വരുമാനത്തിൽ ഇടിവ് (Revenue Decline: {rev_growth:.1f}%)")

    if 0 < pe_ratio <= 30:
        pros.append(f"ന്യായമായ വില നിലവാരം (Reasonable P/E: {pe_ratio:.1f}x)")
    elif pe_ratio > 60:
        cons.append(f"അമിത വില നിലവാരം (Expensive Valuation P/E: {pe_ratio:.1f}x)")

    if above_200dma:
        pros.append("200-Day Moving Average-ന് മുകളിൽ ശക്തമായ അപ്-ട്രെൻഡിലാണ്")
    else:
        cons.append("200-Day Moving Average-ന് താഴെ ബെയറിഷ് ട്രെൻഡിലാണ്")

    # Horizon Suitability (1Y / 3-5Y / 10+Y)
    suit_1y = "✅ അനുയോജ്യം (Bullish Trend & Momentum)" if (above_200dma and ret_1y > 5 and pe_ratio < 65) else "⚠️ ജാഗ്രത പാലിക്കുക (High Volatility / Weak Trend)"
    suit_5y = "✅ മികച്ചത് (Strong Growth & Margin)" if (roe >= 14 and debt_to_mcap < 33 and rev_growth >= 5) else "⚠️ ശരാശരി (Needs Fundamental Improvement)"
    suit_10y = "🏛️ 10+ വർഷത്തേക്ക് മികച്ച Moat Compounder!" if (roe >= 18 and debt_to_mcap < 20 and op_margin >= 15) else "❌ 10 വർഷത്തേക്ക് അനുയോജ്യമല്ല (Not a Moat Monopoly)"

    overall_score = 0
    if roe >= 15: overall_score += 30
    if debt_to_mcap < 25: overall_score += 25
    if op_margin >= 15: overall_score += 20
    if above_200dma: overall_score += 15
    if 0 < pe_ratio <= 40: overall_score += 10

    if overall_score >= 75:
        verdict = "🟢 STRONG BUY / ACCUMULATE (നിക്ഷേപത്തിന് ഏറ്റവും അനുയോജ്യം)"
    elif overall_score >= 50:
        verdict = "🟡 HOLD / WATCHLIST (തകർച്ചയിൽ വാങ്ങാം / നിരീക്ഷിക്കുക)"
    else:
        verdict = "🔴 AVOID / HIGH RISK (ഒഴിവാക്കുക - ഫണ്ടമെന്റൽ പോരായ്മകൾ)"

    return {
        "symbol": ticker_sym, "name": comp_name, "price": curr_p, "curr_sym": curr_sym,
        "sector": sector, "industry": industry, "roe": roe, "op_margin": op_margin,
        "debt_to_mcap": debt_to_mcap, "cash_to_mcap": cash_to_mcap, "pe": pe_ratio,
        "div_yield": div_yield, "ret_1y": ret_1y, "ret_5y": ret_5y,
        "shariah_pass": shariah_pass, "is_prohibited_sec": is_prohibited_sec,
        "pros": pros, "cons": cons, "suit_1y": suit_1y, "suit_5y": suit_5y, "suit_10y": suit_10y,
        "score": overall_score, "verdict": verdict, "hist": hist
    }

@st.cache_data(ttl=1800)
def fetch_live_ipos_india():
    """Fetches real-time Open & Upcoming Indian IPO news & listings from NSE/Google Finance RSS."""
    ipo_items = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    # 1. Try NSE Live Upcoming/Active IPO API
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=5)
        r = s.get("https://www.nseindia.com/api/ipo-current-issue", headers=headers, timeout=6)
        if r.status_code == 200:
            for item in r.json():
                ipo_items.append({
                    "IPO Company": item.get("companyName", "N/A"),
                    "Symbol": item.get("symbol", ""),
                    "Status": "🟢 OPEN NOW (NSE Live)",
                    "Dates": f"{item.get('issueStartDate', '')} to {item.get('issueEndDate', '')}",
                    "Price Band": f"₹{item.get('issuePrice', 'TBA')}",
                    "Category": item.get("series", "Mainboard / SME")
                })
    except Exception:
        pass

    # 2. Fetch Live Upcoming & Open IPO Updates via Google News RSS (Always works 24/7 on Cloud)
    try:
        rss_url = "https://news.google.com/rss/search?q=IPO+GMP+price+band+subscription+India+when:7d&hl=en-IN&gl=IN&ceid=IN:en"
        r_rss = requests.get(rss_url, headers=headers, timeout=6)
        if r_rss.status_code == 200:
            root = ET.fromstring(r_rss.content)
            for item in root.findall(".//item")[:15]:
                title = item.find("title").text if item.find("title") is not None else ""
                pub = item.find("pubDate").text[:16] if item.find("pubDate") is not None else ""
                status_tag = "🟢 OPEN / GMP UPDATE" if ("open" in title.lower() or "gmp" in title.lower() or "subscri" in title.lower()) else "⏳ UPCOMING / NEWS"
                ipo_items.append({
                    "IPO Company": title.split(" - ")[0],
                    "Symbol": "LIVE FEED",
                    "Status": status_tag,
                    "Dates": pub,
                    "Price Band": "Check Analyzer Below",
                    "Category": title.split(" - ")[-1] if " - " in title else "IPO Desk"
                })
    except Exception:
        pass
    return ipo_items

@st.cache_data(ttl=1800)
def search_live_mutual_funds(query_str):
    """Searches all 10,000+ Indian Mutual Funds live via AMFI API (mfapi.in)."""
    if not query_str or len(query_str.strip()) < 2:
        return []
    try:
        res = requests.get(f"https://api.mfapi.in/mf/search?q={urllib.parse.quote(query_str.strip())}", timeout=8)
        if res.status_code == 200:
            return res.json()[:25]
    except Exception:
        pass
    return []

@st.cache_data(ttl=1800)
def analyze_mutual_fund_scheme(scheme_code):
    """Calculates live 1Y, 3Y, and 5Y CAGR for any Mutual Fund scheme from AMFI historical NAV."""
    try:
        res = requests.get(f"https://api.mfapi.in/mf/{scheme_code}", timeout=8)
        if res.status_code == 200:
            data = res.json()
            meta = data.get("meta", {})
            nav_list = data.get("data", [])
            if not nav_list:
                return None
            curr_nav = float(nav_list[0]["nav"])
            curr_date = nav_list[0]["date"]

            def get_cagr(days_ago, years):
                idx = min(len(nav_list) - 1, int(days_ago * 0.68))
                for item in nav_list:
                    try:
                        d_obj = datetime.datetime.strptime(item["date"], "%d-%m-%Y")
                        if (datetime.datetime.now() - d_obj).days >= days_ago:
                            old_nav = float(item["nav"])
                            if old_nav > 0:
                                return (((curr_nav / old_nav) ** (1.0 / years)) - 1.0) * 100
                            break
                    except Exception:
                        continue
                return 0.0

            cagr_1y = get_cagr(365, 1.0)
            cagr_3y = get_cagr(1095, 3.0)
            cagr_5y = get_cagr(1825, 5.0)
            return {
                "name": meta.get("scheme_name", ""),
                "house": meta.get("fund_house", ""),
                "category": meta.get("scheme_category", ""),
                "nav": curr_nav, "date": curr_date,
                "cagr_1y": cagr_1y, "cagr_3y": cagr_3y, "cagr_5y": cagr_5y
            }
    except Exception:
        pass
    return None

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
# 🌐 SIDEBAR & AUTHENTICATION
# ==========================================
@st.cache_resource
def get_user_vault():
    return {}

user_vault = get_user_vault()

st.sidebar.markdown("# 🏛️ WEALTH OS")
lang = st.sidebar.selectbox("🌐 Language / ഭാഷ:", ["മലയാളം", "English"], index=0)
is_ml = (lang == "മലയാളം")

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
                st.success("🎉 Access Token ഓട്ടോമാറ്റിക് ആയി ജനറേറ്റ് ചെയ്തു!")

if "authenticated_user_hash" not in st.session_state:
    st.session_state["authenticated_user_hash"] = None

if not st.session_state["authenticated_user_hash"]:
    st.subheader("🔒 സ്വകാര്യ ലോക്കർ ലോഗിൻ (100% Data Privacy)" if is_ml else "🔒 Private Vault Login (100% Data Privacy)")
    st.info("നിങ്ങളുടെ സ്വകാര്യ അക്കൗണ്ട് തുറക്കാൻ നിങ്ങൾക്ക് മാത്രം അറിയാവുന്ന ഒരു രഹസ്യ പാസ്‌കീ (Secret ID) നൽകുക." if is_ml else "Enter your personal Secret Passkey to unlock your isolated workspace.")
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
        'mode': 'PAPER', 'tg_token': saved_c.get('tg_token', ''), 'tg_chat': saved_c.get('tg_chat', ''),
        'thread': None, 'consecutive_losses': 0, 'kill_switch': False,
        'nifty_status': 'Checking...', 'active_pos': None, 'shariah_lock': False, 'last_order_error': '',
        'api_key': saved_c.get('api_key', ''), 'api_secret': saved_c.get('api_secret', ''),
        'redirect_uri': saved_c.get('redirect_uri', 'https://my-trading-bot-wyjcnfn2bprzd4ysp8riie.streamlit.app'),
        'broker': saved_c.get('broker', 'Upstox')
    }
state = user_vault[USER_HASH]

st.sidebar.markdown("---")
phil_options = ["🌐 ആഗോള ജനറൽ മോഡ് (Conventional)", "🌙 100% പ്യുവർ ശരീഅത്ത് മോഡ് (Halal AAOIFI)"] if is_ml else ["🌐 Global Conventional Mode", "🌙 100% Pure Shariah Mode (AAOIFI)"]
wealth_mode = st.sidebar.radio("നിക്ഷേപ തത്ത്വശാസ്ത്രം:" if is_ml else "Investment Philosophy:", phil_options)
is_shariah = ("ശരീഅത്ത്" in wealth_mode or "Shariah" in wealth_mode)
state['shariah_lock'] = is_shariah

MENU_ITEMS = [
    "🧭 തുടക്കക്കാരുടെ വഴികാട്ടി (Start Here)" if is_ml else "🧭 Beginner Quick-Start Guide",
    "🔎 ഏത് സ്റ്റോക്കും പരിശോധിക്കാം (NSE/BSE/US Live Scanner)" if is_ml else "🔎 Universal Stock Scanner & Screener (NSE/BSE/US)",
    "🎟️ ലൈവ് ഐ.പി.ഒ (IPO) റഡാർ & അനലൈസർ" if is_ml else "🎟️ Live IPO Radar (Open & Upcoming)",
    "📈 മ്യൂച്വൽ ഫണ്ട് ലൈവ് സ്ക്രീനർ (All 10,000+ Funds)" if is_ml else "📈 Live Mutual Fund Screener (All AMFI Funds)",
    "💳 കടം തീർക്കൽ & ലോൺ പ്ലാനർ (Debt Freedom)" if is_ml else "💳 Debt Freedom & Loan Elimination Planner",
    "🎯 ലക്ഷ്യാധിഷ്ഠിത പോർട്ട്ഫോളിയോ (Goal Engine)" if is_ml else "🎯 Dynamic Goal Allocator",
    "💼 എന്റെ ലൈവ് പോർട്ട്ഫോളിയോ (All Brokers)" if is_ml else "💼 Live Portfolio & Exit Watchdog",
    "🌍 ആഗോള വിപണികൾ (US Live Screener & INDmoney)" if is_ml else "🌍 Global Markets (US Screener & Portfolio)",
    "📜 ബോണ്ടുകൾ, കടപ്പത്രങ്ങൾ & ഹലാൽ വരുമാനം" if is_ml else "📜 Bonds, G-Secs & Halal Fixed-Income",
    "🥇 ഗോൾഡ് & സുരക്ഷിത ആസ്തികൾ" if is_ml else "🥇 Gold & Crisis Hedge Assets",
    "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട് (Algo Engine)" if is_ml else "⚡ Intraday Algo Trading Bot",
    "📚 അഡ്വൈസറി ജേർണൽ" if is_ml else "📚 Investment Audit Journal"
]

st.sidebar.markdown("---")
main_menu = st.sidebar.radio("പ്രധാന വിഭാഗം തിരഞ്ഞെടുക്കുക:" if is_ml else "Select Core Module:", MENU_ITEMS)

# Helper UI component: Live Search Box that queries Yahoo Finance for ANY stock on Earth
def render_universal_stock_search(key_prefix, market_filter="ALL", default_query="Polycab"):
    c_s1, c_s2 = st.columns([2, 3])
    q_input = c_s1.text_input(
        "🔍 കമ്പനിയുടെ പേര് അല്ലെങ്കിൽ അക്ഷരങ്ങൾ ടൈപ്പ് ചെയ്യുക (ഉദാ: Kitex, Kalyan, Tata, Apple):" if is_ml else "🔍 Type Company Name or Letters (e.g. Kitex, Kalyan, Tata, Apple):",
        value=default_query,
        key=f"{key_prefix}_q"
    )
    matches = live_search_yahoo_tickers(q_input, market_filter=market_filter)
    if matches:
        sel = c_s2.selectbox(
            f"✅ '{q_input}' എന്നതിൽ തുടങ്ങുന്ന കമ്പനികൾ (ഇതിൽ നിന്ന് തിരഞ്ഞെടുക്കുക):" if is_ml else f"✅ Matching Companies for '{q_input}':",
            matches,
            key=f"{key_prefix}_sel"
        )
        return sel.split(" | ")[0].strip()
    else:
        c_s2.warning("ഈ പേരിൽ കമ്പനികൾ കണ്ടില്ല. അക്ഷരങ്ങൾ മാറ്റി ടൈപ്പ് ചെയ്യുക.")
        return q_input.upper().strip()

# ##################################################################
# 🧭 MODULE 0: BEGINNER QUICK-START GUIDE
# ##################################################################
if main_menu == MENU_ITEMS[0]:
    st.title("🧭 സ്വാഗതം! ഈ പ്ലാറ്റ്‌ഫോം എങ്ങനെ ഉപയോഗിക്കാം?" if is_ml else "🧭 Welcome! Step-by-Step Financial Life Roadmap")
    st.success("👋 **ആദ്യമായിട്ടാണോ ഇവിടെ?** താഴെ കാണുന്ന 4 ഘട്ടങ്ങൾ വായിച്ചാൽ ഈ ആപ്പിലെ എല്ലാ സൗകര്യങ്ങളും ഒരു ബുദ്ധിമുട്ടുമില്ലാതെ നിങ്ങൾക്ക് ഉപയോഗിക്കാം!")
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("""
        ### 1️⃣ ഏതൊരു സ്റ്റോക്കും (NSE / BSE / US) എങ്ങനെ പരിശോധിക്കാം?
        * ഇടതുവശത്തെ മെനുവിൽ **'🔎 ഏത് സ്റ്റോക്കും പരിശോധിക്കാം'** എടുക്കുക.
        * അവിടെയുള്ള സെർച്ച് ബോക്സിൽ നിങ്ങൾക്ക് അറിയേണ്ട ഏത് കമ്പനിയുടെയും പേര് (ഉദാഹരണത്തിന് `Kalyan`, `Kitex`, `Cochin`, `Reliance`, `Nvidia`) ടൈപ്പ് ചെയ്യുക.
        * ഉടൻ തന്നെ വലതുവശത്തെ ബോക്സിൽ ആ പേരിലുള്ള എല്ലാ കമ്പനികളും ലിസ്റ്റ് ആയി വരും! അതിൽ ക്ലിക്ക് ചെയ്താൽ ആ സ്റ്റോക്കിൽ **ഇൻവെസ്റ്റ് ചെയ്യാമോ, 1 വർഷത്തേക്കാണോ 5 വർഷത്തേക്കാണോ നല്ലത്, അതിന്റെ ഗുണങ്ങളും ദോഷങ്ങളും എന്തൊക്കെയാണ്** എന്ന് തത്സമയം കാണാം!
        
        ### 2️⃣ കടങ്ങളും ലോണുകളും ഉള്ളവർ എവിടെ തുടങ്ങണം?
        * **'💳 കടം തീർക്കൽ & ലോൺ പ്ലാനർ'** തുറന്ന് നിങ്ങളുടെ എല്ലാ ലോണുകളും ചേർക്കുക. ഏത് ലോൺ ആദ്യം അടക്കണമെന്ന് സിസ്റ്റം പ്ലാൻ ചെയ്തു തരും.
        """)
    with g2:
        st.markdown("""
        ### 3️⃣ നിലവിലുള്ളതും വരാൻ പോകുന്നതുമായ IPO-കളും മ്യൂച്വൽ ഫണ്ടുകളും
        * **'🎟️ ലൈവ് ഐ.പി.ഒ റഡാർ'** തുറന്നാൽ ഇപ്പോൾ മാർക്കറ്റിൽ ഓപ്പൺ ആയിട്ടുള്ളതും ഇനി വരാൻ പോകുന്നതുമായ IPO-കളുടെ ലൈവ് ലിസ്റ്റും അവയുടെ ഗുണനിലവാരവും പരിശോധിക്കാം.
        * **'📈 മ്യൂച്വൽ ഫണ്ട് ലൈവ് സ്ക്രീനർ'** വഴി ഇന്ത്യയിലെ 10,000+ മ്യൂച്വൽ ഫണ്ടുകളിൽ ഏതിന്റെയും പേര് അടിച്ച് 1Y, 3Y, 5Y ലാഭം പരിശോധിക്കാം!
        
        ### 4️⃣ ഓട്ടോമാറ്റിക് ലൈവ് മാർക്കറ്റ് സ്ക്രീനിംഗ് (Rescan Button)
        * സ്റ്റോക്ക് സ്കാനറിലും US മാർക്കറ്റിലും **'🔄 മാർക്കറ്റ് ലൈവ് ആയി സ്ക്രീൻ ചെയ്യുക (Run Live Screener)'** എന്ന ബട്ടൺ അമർത്തിയാൽ കമ്പ്യൂട്ടർ തനിയെ മാർക്കറ്റ് പരിശോധിച്ച് മികച്ച സ്റ്റോക്കുകളെ കണ്ടെത്തി തരും!
        """)

# ##################################################################
# 🔎 MODULE 1: UNIVERSAL STOCK SCANNER & LIVE SCREENER (NSE / BSE / US)
# ##################################################################
elif main_menu == MENU_ITEMS[1]:
    st.title("🔎 യൂണിവേഴ്സൽ സ്റ്റോക്ക് സ്കാനർ & ലൈവ് മാർക്കറ്റ് സ്ക്രീനർ (NSE / BSE / US)")
    st.caption("ഇന്ത്യയിലെയും (NSE/BSE) അമേരിക്കയിലെയും (US) ഏതൊരു കമ്പനിയുടെയും പേര് ടൈപ്പ് ചെയ്ത് അതിന്റെ ഗുണങ്ങളും ദോഷങ്ങളും, 1Y / 5Y / 10Y അനുയോജ്യതയും തത്സമയം പരിശോധിക്കുക.")

    tab_search, tab_screener = st.tabs([
        "🔍 ഏത് കമ്പനിയും തിരഞ്ഞ് പരിശോധിക്കുക (Universal Stock Audit)",
        "📡 ഓട്ടോമാറ്റിക് ലൈവ് മാർക്കറ്റ് സ്ക്രീനർ (Live Rescan & Filter)"
    ])

    with tab_search:
        mkt_choice = st.radio("ഏത് മാർക്കറ്റാണ് പരിശോധിക്കേണ്ടത്?", ["🇮🇳 ഇന്ത്യൻ മാർക്കറ്റ് (NSE & BSE)", "🇺🇸 യു.എസ് മാർക്കറ്റ് (NASDAQ & NYSE)", "🌐 എല്ലാ മാർക്കറ്റുകളും (All Global)"], horizontal=True)
        m_filt = "INDIA" if "ഇന്ത്യൻ" in mkt_choice else ("US" if "യു.എസ്" in mkt_choice else "ALL")
        def_q = "Polycab" if m_filt != "US" else "Nvidia"

        selected_sym = render_universal_stock_search("univ_scan", market_filter=m_filt, default_query=def_q)

        if st.button("🔄 ഈ സ്റ്റോക്ക് ഇപ്പോൾ തത്സമയം റീ-സ്കാൻ ചെയ്യുക (Refresh Live Audit)", type="primary"):
            st.cache_data.clear()

        if selected_sym:
            with st.spinner(f"⏳ `{selected_sym}`-ന്റെ പൂർണ്ണമായ ഫണ്ടമെന്റൽ, ടെക്നിക്കൽ, ശരീഅത്ത് വിവരങ്ങൾ പരിശോധിക്കുന്നു..."):
                audit = analyze_any_stock_deep(selected_sym)
                if not audit:
                    st.error(f"❌ `{selected_sym}` എന്ന കമ്പനിയുടെ ഡാറ്റ ലഭ്യമല്ല. മുകളിലെ സെർച്ച് ബോക്സിൽ പേര് ടൈപ്പ് ചെയ്ത് വലതുവശത്തെ ലിസ്റ്റിൽ നിന്ന് തിരഞ്ഞെടുക്കുക.")
                else:
                    st.subheader(f"🏢 {audit['name']} (`{audit['symbol']}`) — നിലവിലെ വില: {audit['curr_sym']}{audit['price']:,.2f}")
                    
                    # Final Verdict Banner
                    if "STRONG BUY" in audit['verdict']:
                        st.success(f"### 🏆 അന്തിമ വിധി (Final Verdict): {audit['verdict']} (Score: {audit['score']}/100)")
                    elif "HOLD" in audit['verdict']:
                        st.warning(f"### ⚖️ അന്തിമ വിധി (Final Verdict): {audit['verdict']} (Score: {audit['score']}/100)")
                    else:
                        st.error(f"### 🛑 അന്തിമ വിധി (Final Verdict): {audit['verdict']} (Score: {audit['score']}/100)")

                    # Key Metrics Row
                    k1, k2, k3, k4, k5 = st.columns(5)
                    k1.metric("സെക്ടർ (Sector)", audit['sector'])
                    k2.metric("ലാഭക്ഷമത (ROE)", f"{audit['roe']:.1f}%", "✅ മികച്ചത്" if audit['roe'] >= 15 else "⚠️ കുറവ്")
                    k3.metric("കടം (Debt / MCap)", f"{audit['debt_to_mcap']:.1f}%", "✅ സുരക്ഷിതം (<33%)" if audit['debt_to_mcap'] < 33 else "❌ അമിത കടം")
                    k4.metric("P/E & ഓപ്പറേറ്റിംഗ് മാർജിൻ", f"PE: {audit['pe']:.1f}x", f"Margin: {audit['op_margin']:.1f}%")
                    k5.metric("AAOIFI ശരീഅത്ത് സ്റ്റാറ്റസ്", "✅ ഹലാൽ (HALAL)" if audit['shariah_pass'] else "❌ നോൺ-ഹലാൽ", f"1Y Return: {audit['ret_1y']:+.1f}%")

                    st.markdown("---")
                    # Horizon Suitability (1 Year vs 3-5 Years vs 10+ Years)
                    st.subheader("⏳ എത്ര കാലത്തേക്ക് നിക്ഷേപിക്കാൻ അനുയോജ്യമാണ്? (Time-Horizon Suitability)")
                    h1, h2, h3 = st.columns(3)
                    h1.info(f"**📅 1 വർഷത്തേക്ക് (Short-Term):**\n\n{audit['suit_1y']}")
                    h2.info(f"**🚀 3 - 5 വർഷത്തേക്ക് (Medium-Term):**\n\n{audit['suit_5y']}")
                    h3.info(f"**🏛️ 10+ വർഷത്തേക്ക് (Long-Term Moat):**\n\n{audit['suit_10y']}")

                    # Pros & Cons Columns
                    pc1, pc2 = st.columns(2)
                    with pc1:
                        st.success("#### 🟢 ഈ കമ്പനിയുടെ നല്ല കാര്യങ്ങൾ (Strengths / Pros)")
                        if audit['pros']:
                            for p in audit['pros']:
                                st.markdown(f"- ✅ {p}")
                        else:
                            st.write("- കാര്യമായ പോസിറ്റീവ് സൂചകങ്ങൾ കാണുന്നില്ല.")
                    with pc2:
                        st.error("#### 🔴 ശ്രദ്ധിക്കേണ്ട പോരായ്മകൾ (Weaknesses / Red Flags)")
                        if audit['cons']:
                            for c_item in audit['cons']:
                                st.markdown(f"- ⚠️ {c_item}")
                        else:
                            st.write("- ഫണ്ടമെന്റൽ പോരായ്മകൾ ഒന്നും കണ്ടെത്തിയില്ല!")

                    if not audit['hist'].empty:
                        st.caption(f"📈 **{audit['name']} — ലൈവ് പ്രൈസ് ചാർട്ട്:**")
                        st.line_chart(audit['hist']['Close'])

    with tab_screener:
        st.subheader("📡 ഓട്ടോമാറ്റിക് ലൈവ് മാർക്കറ്റ് സ്ക്രീനർ (Live Market Auto-Screener)")
        st.caption("നിങ്ങളുടെ മാനദണ്ഡങ്ങൾ (ROE, Debt, Shariah Mode) അനുസരിച്ച് മാർക്കറ്റിലെ സ്റ്റോക്കുകളെ ഇപ്പോൾത്തന്നെ തത്സമയം സ്കാൻ ചെയ്ത് മികച്ചവയെ കണ്ടെത്തുക.")

        sc_col1, sc_col2, sc_col3 = st.columns(3)
        universe_choice = sc_col1.selectbox("സ്കാൻ ചെയ്യേണ്ട മാർക്കറ്റ് ബാസ്കറ്റ്:", [
            "🇮🇳 ഇന്ത്യൻ ലാർജ് & മിഡ് ക്യാപ് ലീഡേഴ്സ് (NSE Top Basket)",
            "🇮🇳 ഐ.ടി, ഫാർമ & എൻജിനീയറിംഗ് (Moat Basket)",
            "🇺🇸 യു.എസ് ടെക് & ഗ്ലോബൽ ടൈറ്റൻസ് (US Wall Street Basket)"
        ])
        min_roe_filter = sc_col2.slider("കുറഞ്ഞ ലാഭക്ഷമത (Minimum ROE %):", 0, 40, 14)
        max_debt_filter = sc_col3.slider("പരമാവധി കടം (Max Debt/MCap %):", 5, 100, 33 if is_shariah else 50)

        if st.button("🔄 ഇപ്പോൾ മാർക്കറ്റ് ലൈവ് ആയി സ്ക്രീൻ ചെയ്യുക (Run Live Market Scan Now)", type="primary"):
            if "US" in universe_choice:
                basket = ["NVDA", "MSFT", "AAPL", "GOOGL", "AMZN", "META", "AVGO", "LLY", "TSLA", "BRK-B"]
            elif "Moat" in universe_choice:
                basket = ["TCS.NS", "INFY.NS", "HCLTECH.NS", "PERSISTENT.NS", "POLYCAB.NS", "TATAELXSI.NS", "SUNPHARMA.NS", "DRREDDY.NS", "ASTRAL.NS", "CUMMINSIND.NS"]
            else:
                basket = ["TCS.NS", "RELIANCE.NS", "INFY.NS", "SUNPHARMA.NS", "TITAN.NS", "POLYCAB.NS", "LT.NS", "BHARTIARTL.NS", "MARUTI.NS", "TRENT.NS", "BEL.NS", "HAL.NS", "ITC.NS", "SBIN.NS"]

            screened_rows = []
            prog = st.progress(0, text="⏳ ലൈവ് മാർക്കറ്റ് ഡാറ്റ സ്കാൻ ചെയ്യുന്നു...")
            for idx, sym in enumerate(basket):
                prog.progress((idx + 1) / len(basket), text=f"⏳ പരിശോധിക്കുന്നു: {sym}...")
                res_a = analyze_any_stock_deep(sym)
                if res_a:
                    if is_shariah and not res_a['shariah_pass']:
                        continue
                    if res_a['roe'] >= min_roe_filter and res_a['debt_to_mcap'] <= max_debt_filter:
                        screened_rows.append({
                            "Symbol": sym.replace(".NS", ""),
                            "Company": res_a['name'],
                            "Price": f"{res_a['curr_sym']}{res_a['price']:,.1f}",
                            "ROE (%)": f"{res_a['roe']:.1f}%",
                            "Debt/MCap (%)": f"{res_a['debt_to_mcap']:.1f}%",
                            "P/E": f"{res_a['pe']:.1f}x",
                            "1Y Return": f"{res_a['ret_1y']:+.1f}%",
                            "Shariah": "✅ Halal" if res_a['shariah_pass'] else "❌ Non-Halal",
                            "10Y Moat": res_a['suit_10y'][:18],
                            "Verdict": res_a['verdict'].split(" (")[0]
                        })
            prog.empty()
            if screened_rows:
                st.success(f"✅ നിങ്ങളുടെ മാനദണ്ഡങ്ങൾ പാസ്സായ **{len(screened_rows)} മികച്ച കമ്പനികൾ** തത്സമയം കണ്ടെത്തി!")
                st.dataframe(pd.DataFrame(screened_rows), use_container_width=True, hide_index=True)
            else:
                st.warning("ഈ ഫിൽട്ടറിൽ കമ്പനികൾ ഒന്നും വന്നില്ല. ROE അല്ലെങ്കിൽ Debt പരിധി അല്പം മാറ്റി വീണ്ടും സ്കാൻ ചെയ്യുക.")

# ##################################################################
# 🎟️ MODULE 2: LIVE IPO RADAR (OPEN & UPCOMING IPOS + ANALYZER)
# ##################################################################
elif main_menu == MENU_ITEMS[2]:
    st.title("🎟️ ലൈവ് ഐ.പി.ഒ (IPO) റഡാർ — നിലവിലുള്ളതും വരാൻ പോകുന്നതുമായ IPO-കൾ")
    st.caption("ഇപ്പോൾ മാർക്കറ്റിൽ ഓപ്പൺ ആയിട്ടുള്ളതും (Open IPOs), ഇനി വരാൻ പോകുന്നതുമായ (Upcoming IPOs) ഐ.പി.ഒകളുടെ തത്സമയ വിവരങ്ങളും വാറൻ ബഫറ്റ് റെഡ്-ഫ്ലാഗ് പരിശോധനയും.")

    col_ipo1, col_ipo2 = st.columns([3, 1])
    col_ipo1.subheader("📡 നിലവിൽ ഓപ്പൺ ആയതും വരാൻ പോകുന്നതുമായ ലൈവ് IPO ഫീഡ് (Live NSE & Market Feed)")
    if col_ipo2.button("🔄 ലൈവ് IPO ലിസ്റ്റ് റിഫ്രഷ് ചെയ്യുക", use_container_width=True):
        st.cache_data.clear()

    with st.spinner("⏳ നിലവിലുള്ളതും വരാൻ പോകുന്നതുമായ IPO വിവരങ്ങൾ ഇന്റർനെറ്റിൽ നിന്ന് ശേഖരിക്കുന്നു..."):
        live_ipos = fetch_live_ipos_india()
        if live_ipos:
            st.dataframe(pd.DataFrame(live_ipos), use_container_width=True, hide_index=True)
        else:
            st.info("നിലവിൽ ലൈവ് ഫീഡ് ലഭ്യമല്ല. താഴെയുള്ള IPO അനലൈസർ ഉപയോഗിക്കുക.")

    st.markdown("---")
    st.subheader("🧮 ഏതൊരു പുതിയ IPO-യും നിക്ഷേപത്തിന് നല്ലതാണോ എന്ന് പരിശോധിക്കാം (IPO Eligibility & Risk Checker)")
    st.info("💡 **എങ്ങനെ നിക്ഷേപിക്കാം?** Upstox, Groww, അല്ലെങ്കിൽ Zerodha ആപ്പിലെ **IPO** വിഭാഗത്തിൽ പോയി **UPI ID** നൽകി അപേക്ഷിക്കാം. പണം ബാങ്കിൽ ബ്ലോക്ക് ആകുകയേ ഉള്ളൂ, അലോട്ട്മെന്റ് കിട്ടിയാൽ മാത്രമേ പണം കട്ട് ആവുകയുള്ളൂ!")

    ic1, ic2, ic3 = st.columns(3)
    ipo_name = ic1.text_input("പരിശോധിക്കേണ്ട IPO കമ്പനിയുടെ പേര്:", value="Upcoming Mainboard IPO")
    ipo_type = ic2.selectbox("IPO വിഭാഗം:", ["🟢 Mainboard IPO (മിനിമം ~₹15,000 - സുരക്ഷിതം)", "🔴 SME IPO (മിനിമം ₹1.2 ലക്ഷം - ഉയർന്ന റിസ്ക്)"])
    ofs_pct = ic3.slider("OFS ശതമാനം (പഴയ ഉടമകൾ ഓഹരി വിറ്റ് പുറത്തുപോകുന്നത് %):", 0, 100, 20)

    ic4, ic5, ic6 = st.columns(3)
    gmp_pct = ic4.slider("നിലവിലെ GMP (Grey Market Premium %):", -20, 120, 25)
    pe_val = ic5.selectbox("കമ്പനിയുടെ വില നിലവാരം (P/E Valuation):", ["🟢 മറ്റ് കമ്പനികളേക്കാൾ കുറഞ്ഞ വില (Undervalued)", "🟡 ന്യായമായ വില (Fairly Priced)", "🔴 അമിത വില (Overpriced > 50x P/E)"])
    debt_stat = ic6.selectbox("കമ്പനിയുടെ കടവും ബിസിനസ്സും:", ["🟢 കടം < 33% & ഹലാൽ ബിസിനസ്സ്", "🟡 കടം കമ്പനി IPO പണം കൊണ്ട് വീട്ടുന്നു", "🔴 അമിത കടം / ബാങ്കിംഗ് / നോൺ-ഹലാൽ"])

    score = 100
    notes = []
    if "SME" in ipo_type:
        score -= 25
        notes.append("⚠️ **SME IPO മുന്നറിയിപ്പ്:** SME ഐ.പി.ഒകളിൽ ലിക്വിഡിറ്റി കുറവാണ്, കൃത്രിമത്വം നടക്കാൻ സാധ്യതയുള്ളതിനാൽ ചെറുകിട നിക്ഷേപകർ ജാഗ്രത പാലിക്കുക.")
    if ofs_pct > 50:
        score -= 35
        notes.append(f"🚨 **OFS കെണി ({ofs_pct}%):** സമാഹരിക്കുന്ന പണത്തിന്റെ ഭൂരിഭാഗവും പഴയ ഉടമകളുടെ കീശയിലേക്കാണ് പോകുന്നത്, കമ്പനിയുടെ വളർച്ചയ്ക്കല്ല!")
    else:
        notes.append(f"✅ **Fresh Issue ({100-ofs_pct}%):** പണം കമ്പനിയുടെ വികസനത്തിനും കടം വീട്ടാനും ഉപയോഗിക്കുന്നു.")
    if gmp_pct >= 20:
        notes.append(f"✅ **മികച്ച GMP (+{gmp_pct}%):** ലിസ്റ്റിംഗ് ദിവസം ലാഭം (Listing Gain) കിട്ടാൻ സാധ്യത വളരെ കൂടുതലാണ്.")
    elif gmp_pct < 10:
        score -= 25
        notes.append(f"🚨 **കുറഞ്ഞ GMP ({gmp_pct}%):** ലിസ്റ്റിംഗിൽ നഷ്ടം വരാൻ സാധ്യതയുണ്ട്.")
    if "🔴" in pe_val:
        score -= 25
        notes.append("🚨 **അമിത വില (Valuation Trap):** ലിസ്റ്റിംഗിന് ശേഷം വില ഇടിയാൻ സാധ്യതയുണ്ട്.")
    if "🔴" in debt_stat and is_shariah:
        score -= 40
        notes.append("🛑 **ശരീഅത്ത് വിരുദ്ധം:** ഉയർന്ന കടമോ നിരോധിത ബിസിനസ്സോ ആയതിനാൽ ശരീഅത്ത് മോഡിൽ ഒഴിവാക്കുക.")

    if score >= 75:
        st.success(f"🏆 **{ipo_name} — സ്കോർ: {score}/100 -> നിക്ഷേപത്തിന് അനുയോജ്യം (APPLY FOR IPO)!** (റീട്ടെയിൽ ക്വാട്ടയിൽ 1 Lot = ~₹14,800-ന് അപേക്ഷിക്കുക).")
    elif score >= 50:
        st.warning(f"⚖️ **{ipo_name} — സ്കോർ: {score}/100 -> ശരാശരി (അവസാന ദിവസം QIB സബ്സ്ക്രിപ്ഷൻ > 15x ആണെങ്കിൽ മാത്രം അപേക്ഷിക്കുക).**")
    else:
        st.error(f"🛑 **{ipo_name} — സ്കോർ: {score}/100 -> ഒഴിവാക്കുക (AVOID THIS IPO)!** നിങ്ങളുടെ മൂലധനം സംരക്ഷിക്കുക.")

    for n in notes:
        st.markdown(f"- {n}")

# ##################################################################
# 📈 MODULE 3: LIVE MUTUAL FUND SCREENER (ALL 10,000+ AMFI FUNDS)
# ##################################################################
elif main_menu == MENU_ITEMS[3]:
    st.title("📈 ലൈവ് മ്യൂച്വൽ ഫണ്ട് സെർച്ച് & സ്ക്രീനർ (All 10,000+ Indian Mutual Funds)")
    st.caption("ഇന്ത്യയിലെ ഏതൊരു മ്യൂച്വൽ ഫണ്ടിന്റെയും പേര് ടൈപ്പ് ചെയ്ത് അതിന്റെ തത്സമയ NAV-യും, 1Y, 3Y, 5Y CAGR ലാഭവും പരിശോധിക്കാം.")

    mf_q = st.text_input("🔍 മ്യൂച്വൽ ഫണ്ടിന്റെ പേര് ടൈപ്പ് ചെയ്യുക (ഉദാ: Tata Ethical, Parag Parikh, Quant, SBI, Gold):", value="Tata Ethical")
    mf_results = search_live_mutual_funds(mf_q)

    if mf_results:
        mf_options = [f"{item['schemeCode']} | {item['schemeName']}" for item in mf_results]
        sel_mf = st.selectbox("✅ താഴെ കാണുന്ന ഫണ്ടുകളിൽ നിന്ന് നിങ്ങൾക്ക് പരിശോധിക്കേണ്ടത് തിരഞ്ഞെടുക്കുക:", mf_options)
        sel_code = sel_mf.split(" | ")[0].strip()

        with st.spinner("⏳ AMFI സെർവറിൽ നിന്ന് ഫണ്ടിന്റെ ലൈവ് NAV-യും 5 വർഷത്തെ ലാഭവും കണക്കാക്കുന്നു..."):
            mf_data = analyze_mutual_fund_scheme(sel_code)
            if mf_data:
                st.success(f"🏛️ **{mf_data['name']}** ({mf_data['house']} | {mf_data['category']})")
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("നിലവിലെ NAV", f"₹{mf_data['nav']:.2f}", f"Date: {mf_data['date']}")
                mc2.metric("1 വർഷത്തെ ലാഭം (1Y Return)", f"{mf_data['cagr_1y']:.1f}%")
                mc3.metric("3 വർഷത്തെ ശരാശരി (3Y CAGR)", f"{mf_data['cagr_3y']:.1f}% p.a.", "✅ മികച്ചത്" if mf_data['cagr_3y'] >= 15 else "ശരാശരി")
                mc4.metric("5 വർഷത്തെ ശരാശരി (5Y CAGR)", f"{mf_data['cagr_5y']:.1f}% p.a.", "🏆 Compounder" if mf_data['cagr_5y'] >= 15 else "Hold")

                if "Direct" not in mf_data['name']:
                    st.warning("⚠️ **ശ്രദ്ധിക്കുക:** ഇതൊരു 'Regular Plan' ആണ്. കമ്മീഷൻ ഒഴിവാക്കി കൂടുതൽ ലാഭം കിട്ടാൻ എപ്പോഴും ഇതേ ഫണ്ടിന്റെ **'Direct Plan - Growth'** തിരഞ്ഞെടുക്കുക!")
                else:
                    st.info("✅ ഇതൊരു **Direct Plan** ആണ് (കമ്മീഷൻ ഇല്ലാത്തത്). 5+ വർഷത്തെ SIP നിക്ഷേപത്തിന് അനുയോജ്യം.")

# ##################################################################
# 💳 MODULE 4: DEBT FREEDOM & LOAN ELIMINATION PLANNER
# ##################################################################
elif main_menu == MENU_ITEMS[4]:
    st.title("💳 കടം തീർക്കൽ & സാമ്പത്തിക മോചന എൻജിൻ (Debt Freedom Planner)")
    with st.expander("➕ പുതിയ ലോൺ / കടം ചേർക്കുക", expanded=True):
        dc1, dc2, dc3 = st.columns(3)
        loan_cat = dc1.selectbox("കടത്തിന്റെ വിഭാഗം:", [
            "💳 ക്രെഡിറ്റ് കാർഡ് കുടിശ്ശിക (36% - 42%)",
            "⚠️ വ്യക്തിഗത കടം / പുറത്തുനിന്ന് വാങ്ങിയത് (Private Debt)",
            "🏦 പേഴ്സണൽ ലോൺ / ആപ്പ് ലോൺ (14% - 28%)",
            "🪙 ഗോൾഡ് ലോൺ / സ്വർണ്ണപ്പണയം (9% - 18%)",
            "🚗 വാഹന ലോൺ (9% - 14%)",
            "🏠 ഹോം ലോൺ (8% - 10%)"
        ])
        lender_name = dc2.text_input("ബാങ്ക് / വ്യക്തിയുടെ പേര്:")
        loan_status = dc3.selectbox("നിലവിലെ അവസ്ഥ:", [
            "🟢 കൃത്യമായി EMI അടച്ചുപോകുന്നു (Regular)",
            "🟡 1-2 മാസം അടവ് മുടങ്ങി (Overdue)",
            "🔴 പൂർണ്ണമായി മുടങ്ങി / റിക്കവറി ഭീഷണി (Defaulted / Critical)"
        ])
        dc4, dc5, dc6 = st.columns(3)
        tot_debt_amt = dc4.number_input("ഇനി കൊടുത്തുതീർക്കാനുള്ള ആകെ തുക (₹):", min_value=500.0, value=50000.0, step=5000.0)
        int_rate = dc5.number_input("വാർഷിക പലിശ നിരക്ക് (%):", min_value=0.0, max_value=120.0, value=14.0, step=1.0)
        monthly_emi = dc6.number_input("പ്രതിമാസ അടവ് / EMI (₹):", min_value=0.0, value=2500.0, step=500.0)

        b_c1, b_c2 = st.columns([2, 1])
        if b_c1.button("💾 കടങ്ങളുടെ ലിസ്റ്റിലേക്ക് ചേർക്കുക", type="primary", use_container_width=True):
            conn = get_db_connection()
            conn.execute("INSERT INTO user_debts (user_hash, loan_type, lender, total_amount, interest_rate, emi, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (USER_HASH, loan_cat, lender_name or "Lender", tot_debt_amt, int_rate, monthly_emi, loan_status, ""))
            conn.commit()
            conn.close()
            st.rerun()
        if b_c2.button("🗑️ ലിസ്റ്റ് മുഴുവൻ മായ്ക്കുക", use_container_width=True):
            conn = get_db_connection()
            conn.execute("DELETE FROM user_debts WHERE user_hash=?", (USER_HASH,))
            conn.commit()
            conn.close()
            st.rerun()

    conn = get_db_connection()
    df_debts = pd.read_sql_query("SELECT loan_type, lender, total_amount, interest_rate, emi, status FROM user_debts WHERE user_hash=?", conn, params=(USER_HASH,))
    conn.close()
    if not df_debts.empty:
        df_debts['urgency'] = df_debts.apply(lambda r: float(r['interest_rate']) + (50 if "🔴" in str(r['status']) else (25 if "🟡" in str(r['status']) else 0)), axis=1)
        df_sorted = df_debts.sort_values(by=['urgency', 'total_amount'], ascending=[False, True]).reset_index(drop=True)
        df_sorted['Priority'] = [f"🔥 #{i+1} (ആദ്യം വീട്ടുക)" if i == 0 else f"#{i+1}" for i in range(len(df_sorted))]
        st.dataframe(df_sorted[['Priority', 'loan_type', 'lender', 'total_amount', 'interest_rate', 'emi', 'status']], use_container_width=True, hide_index=True)

# ##################################################################
# 🎯 MODULE 5: DYNAMIC GOAL ALLOCATOR
# ##################################################################
elif main_menu == MENU_ITEMS[5]:
    st.title(MENU_ITEMS[5])
    c1, c2, c3 = st.columns(3)
    inv_amount = c1.number_input("നിക്ഷേപ തുക (₹):", value=10000.0, step=1000.0)
    goal_horizon = c2.selectbox("നിക്ഷേപ കാലാവധി:", ["⏳ 1 Year (ഹ്രസ്വകാലം)", "🚀 3 - 5 Years (ഇടത്തരം വളർച്ച)", "🏛️ 10+ Years (ദീർഘകാല സമ്പത്ത്)"])
    market_climate = c3.selectbox("വിപണി സാഹചര്യം:", ["🟢 Normal Bull", "⚠️ War / Oil Spike", "🔴 Market Crash"])

    if "1 Year" in goal_horizon: eq_pct, gold_pct, cash_pct = 0.15, 0.35, 0.50
    elif "3 - 5 Years" in goal_horizon: eq_pct, gold_pct, cash_pct = (0.40, 0.30, 0.30) if "War" in market_climate else (0.60, 0.20, 0.20)
    else: eq_pct, gold_pct, cash_pct = (0.75, 0.15, 0.10) if "Crash" in market_climate else (0.70, 0.20, 0.10)

    a1, a2, a3 = st.columns(3)
    a1.metric("ഇക്വിറ്റി ഓഹരികൾ", f"₹{(inv_amount * eq_pct):,.0f}", f"{int(eq_pct*100)}%")
    a2.metric("ഗോൾഡ് & സിൽവർ", f"₹{(inv_amount * gold_pct):,.0f}", f"{int(gold_pct*100)}%")
    a3.metric("ക്യാഷ് കരുതൽ", f"₹{(inv_amount * cash_pct):,.0f}", f"{int(cash_pct*100)}%")

# ##################################################################
# 💼 MODULE 6: LIVE PORTFOLIO & ALL-BROKER WATCHDOG (WITH LIVE SEARCH)
# ##################################################################
elif main_menu == MENU_ITEMS[6]:
    st.title(MENU_ITEMS[6])
    h_tab1, h_tab2 = st.tabs(["⚡ ലൈവ് ബ്രോക്കർ സിങ്ക് (Upstox / Dhan / Zerodha)", "📝 മറ്റ് ആപ്പുകളിലെ ഓഹരികൾ ചേർക്കുക (Universal Auto-Search)"])

    with h_tab1:
        b_choice = st.selectbox("ബ്രോക്കർ തിരഞ്ഞെടുക്കുക:", ["Upstox", "Dhan", "Zerodha"])
        user_token = st.sidebar.text_input(f"{b_choice} Token:", value=state['token'], type="password", key="holdings_token")
        if st.button(f"🔄 {b_choice}-ൽ നിന്ന് പോർട്ട്ഫോളിയോ എടുക്കുക"):
            if not user_token:
                st.error("സൈഡ്‌ബാറിൽ Access Token നൽകുക!")
            else:
                headers = {'Accept': 'application/json', 'Authorization': f'Bearer {user_token}'}
                res = requests.get('https://api.upstox.com/v2/portfolio/long-term-holdings', headers=headers, timeout=10)
                if res.status_code == 200 and len(res.json().get('data', [])) > 0:
                    st.dataframe(pd.DataFrame(res.json()['data']), use_container_width=True)
                else:
                    st.info("നിങ്ങളുടെ അക്കൗണ്ടിൽ നിലവിൽ ഹോൾഡിംഗ്സുകൾ ഒന്നും കണ്ടെത്തിയില്ല.")

    with h_tab2:
        m_sym = render_universal_stock_search("port_univ", market_filter="INDIA", default_query="TCS")
        col_m1, col_m2, col_m3 = st.columns(3)
        m_qty = col_m1.number_input("വാങ്ങിയ എണ്ണം (Qty):", value=1, min_value=1, step=1)
        m_bp = col_m2.number_input("വാങ്ങിയ വില (₹):", value=500.0, min_value=1.0, step=10.0)
        m_plat = col_m3.selectbox("പ്ലാറ്റ്‌ഫോം:", ["Groww", "Zerodha", "AngelOne", "Upstox", "Other"])

        if st.button("➕ പോർട്ട്ഫോളിയോയിലേക്ക് ചേർക്കുക & ലൈവ് ഓഡിറ്റ് കാണുക", type="primary"):
            if m_sym:
                conn = get_db_connection()
                conn.execute("INSERT INTO manual_portfolio (user_hash, symbol, qty, buy_price, buy_date, notes) VALUES (?, ?, ?, ?, ?, ?)",
                             (USER_HASH, m_sym, m_qty, m_bp, datetime.date.today().strftime("%Y-%m-%d"), m_plat))
                conn.commit()
                conn.close()
                st.success(f"✅ {m_sym} ചേർത്തു!")

        conn = get_db_connection()
        df_man = pd.read_sql_query("SELECT symbol AS Stock, qty AS Qty, buy_price AS [Buy Price], buy_date AS [Date], notes AS Broker FROM manual_portfolio WHERE user_hash=? ORDER BY id DESC", conn, params=(USER_HASH,))
        conn.close()
        if not df_man.empty:
            st.dataframe(df_man, use_container_width=True, hide_index=True)

# ##################################################################
# 🌍 MODULE 7: GLOBAL MARKETS (US LIVE AUTO-SEARCH & SCREENER)
# ##################################################################
elif main_menu == MENU_ITEMS[7]:
    st.title("🌍 ആഗോള വിപണികൾ — ഏത് യു.എസ് (US) കമ്പനിയും തിരയാം & പോർട്ട്ഫോളിയോ ട്രാക്ക് ചെയ്യാം")
    u_sym = render_universal_stock_search("us_univ", market_filter="US", default_query="Nvidia")

    if u_sym:
        with st.spinner(f"⏳ യു.എസ് കമ്പനി `{u_sym}` പരിശോധിക്കുന്നു..."):
            us_audit = analyze_any_stock_deep(u_sym)
            if us_audit:
                st.info(f"🇺🇸 **{us_audit['name']} (`{us_audit['symbol']}`)** | Live Price: **${us_audit['price']:,.2f}** | ROE: `{us_audit['roe']:.1f}%` | Debt/MCap: `{us_audit['debt_to_mcap']:.1f}%` | Shariah: `{'✅ Halal' if us_audit['shariah_pass'] else '❌ Non-Halal'}` | **{us_audit['verdict']}**")

    uc1, uc2, uc3 = st.columns(3)
    u_qty = uc1.number_input("വാങ്ങിയ എണ്ണം (Fractional Qty):", value=1.0, min_value=0.01, step=0.1)
    u_bp = uc2.number_input("വാങ്ങിയ വില ($ USD):", value=100.0, min_value=1.0, step=5.0)
    u_plat = uc3.selectbox("US ആപ്പ് / ബ്രോക്കർ:", ["INDmoney", "Vested", "Alpaca API", "Interactive Brokers"])

    if st.button("➕ എന്റെ US പോർട്ട്ഫോളിയോയിലേക്ക് ചേർക്കുക", type="primary"):
        conn = get_db_connection()
        conn.execute("INSERT INTO us_portfolio (user_hash, symbol, qty, buy_price_usd, buy_usd_inr, platform) VALUES (?, ?, ?, ?, ?, ?)",
                     (USER_HASH, u_sym, u_qty, u_bp, 84.5, u_plat))
        conn.commit()
        conn.close()
        st.success(f"✅ {u_sym} ചേർത്തു!")

    conn = get_db_connection()
    df_us = pd.read_sql_query("SELECT symbol, qty, buy_price_usd, platform FROM us_portfolio WHERE user_hash=? ORDER BY id DESC", conn, params=(USER_HASH,))
    conn.close()
    if not df_us.empty:
        st.dataframe(df_us, use_container_width=True, hide_index=True)

# ##################################################################
# 📜 MODULE 8: BONDS, G-SECS & HALAL FIXED-INCOME
# ##################################################################
elif main_menu == MENU_ITEMS[8]:
    st.title(MENU_ITEMS[8])
    if is_shariah:
        st.error("🌙 **ശരീഅത്ത് നിയമം:** സാധാരണ ബോണ്ടുകളും ബാങ്ക് FD-യും പലിശ (Riba) ആയതിനാൽ ഹലാൽ അല്ല. പകരം താഴെ കാണുന്ന പലിശരഹിത മാർഗ്ഗങ്ങൾ തിരഞ്ഞെടുക്കുക:")
        st.dataframe(pd.DataFrame([
            {"ഹലാൽ മാർഗ്ഗം": "1. ഉയർന്ന ഡിവിഡന്റ് നൽകുന്ന കടരഹിത ഹലാൽ ഓഹരികൾ (TCS, INFOSYS, HCLTECH)", "വരുമാനം": "2.5% - 4.5% Div + വളർച്ച"},
            {"ഹലാൽ മാർഗ്ഗം": "2. ഫിസിക്കൽ ഗോൾഡ് & സിൽവർ ഇ.ടി.എഫ് (GOLDBEES / SILVERBEES)", "വരുമാനം": "12% - 14% വാർഷിക വളർച്ച"},
            {"ഹലാൽ മാർഗ്ഗം": "3. വാടക വരുമാനം നൽകുന്ന റിയൽ എസ്റ്റേറ്റ് / സുക്കൂക്ക് (Ijarah / Sukuk)", "വരുമാനം": "6% - 9% വാടക വരുമാനം"}
        ]), use_container_width=True, hide_index=True)
    else:
        st.dataframe(pd.DataFrame([
            {"Bond": "1. RBI Retail Direct G-Secs (സർക്കാർ കടപ്പത്രങ്ങൾ)", "Safety": "100% Sovereign Guarantee", "Yield": "7.0% - 7.3% p.a."},
            {"Bond": "2. RBI 91/364 Day Treasury Bills (T-Bills)", "Safety": "100% Sovereign Guarantee", "Yield": "6.8% - 7.0% p.a."},
            {"Bond": "3. Bharat Bond ETF / AAA PSU Bonds (NHAI, REC)", "Safety": "AAA Highest Safety", "Yield": "7.4% - 8.0% p.a."}
        ]), use_container_width=True, hide_index=True)

# ##################################################################
# 🥇 MODULE 9: GOLD & CRISIS HEDGE ASSETS
# ##################################################################
elif main_menu == MENU_ITEMS[9]:
    st.title(MENU_ITEMS[9])
    st.dataframe(pd.DataFrame([
        {"Instrument": "Nippon India Gold BeES (GOLDBEES)", "Backing": "99.5% Physical Bullion", "Expense": "0.55%", "Compliance": "✅ AAOIFI Standard #57"},
        {"Instrument": "HDFC Gold ETF (HDFCGOLD)", "Backing": "99.5% Physical Bullion", "Expense": "0.30%", "Compliance": "✅ AAOIFI Standard #57"},
        {"Instrument": "Nippon India Silver ETF (SILVERBEES)", "Backing": "99.9% Physical Silver", "Expense": "0.50%", "Compliance": "✅ AAOIFI Standard #57"}
    ]), use_container_width=True, hide_index=True)

# ##################################################################
# ⚡ MODULE 10: INTRADAY ALGO TRADING BOT (FULL ENGINE RESTORED)
# ##################################################################
elif main_menu == MENU_ITEMS[10]:
    st.title("⚡ മൾട്ടി-ബ്രോക്കർ ഇൻസ്റ്റിറ്റ്യൂഷണൽ ഇൻട്രാഡേ ബോട്ട്")
    with st.expander("📐 ബോട്ട് എങ്ങനെയാണ് ട്രേഡ് തിരഞ്ഞെടുക്കുന്നത്? (6-ഇന മാനദണ്ഡങ്ങൾ)"):
        st.markdown("1. **Nifty 50 >= 20 EMA** | 2. **Price > VWAP** | 3. **EMA 9 > EMA 21 Cross** | 4. **Volume >= 1.2x SMA** | 5. **RSI 50–68** | 6. **ATR 1:2 Risk-Reward & 3:15 PM Auto Exit**.")

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
# 📚 MODULE 11: INVESTMENT AUDIT JOURNAL
# ##################################################################
elif main_menu == MENU_ITEMS[11]:
    st.title(MENU_ITEMS[11])
    j_asset = render_universal_stock_search("journ_univ", market_filter="ALL", default_query="TCS")
    j_col1, j_col2 = st.columns(2)
    j_action = j_col1.selectbox("തീരുമാനം:", ["BUY (വാങ്ങി)", "HOLD (തുടരുന്നു)", "SELL (വിറ്റു)", "WATCHLIST"])
    j_status = j_col2.selectbox("വിഭാഗം:", ["✅ Long-Term Moat", "🌙 Halal Verified", "⚠️ Tactical Bet", "🛑 Rule Exit"])
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
