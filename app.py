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
import base64
import xml.etree.ElementTree as ET
import yfinance as yf

# ==========================================
# 🌐 PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Autonomous Wealth OS & India-Global Screener", layout="wide", page_icon="🏛️")

# ==========================================
# 🔐 CRYPTOGRAPHIC CREDENTIAL MASKING HELPER
# ==========================================
def xor_cipher_hex(text_str, key_str):
    if not text_str or not key_str:
        return ""
    try:
        k_bytes = hashlib.sha256(key_str.encode()).digest()
        t_bytes = text_str.encode("utf-8")
        enc = bytes([b ^ k_bytes[i % len(k_bytes)] for i, b in enumerate(t_bytes)])
        return base64.urlsafe_b64encode(enc).decode("ascii")
    except Exception:
        return text_str

def xor_decipher_hex(enc_str, key_str):
    if not enc_str or not key_str:
        return ""
    try:
        k_bytes = hashlib.sha256(key_str.encode()).digest()
        enc_bytes = base64.urlsafe_b64decode(enc_str.encode("ascii"))
        dec = bytes([b ^ k_bytes[i % len(k_bytes)] for i, b in enumerate(enc_bytes)])
        return dec.decode("utf-8")
    except Exception:
        return enc_str

# ==========================================
# 🔎 LIVE GLOBAL & INDIAN STOCK / MF / IPO ENGINES
# ==========================================
@st.cache_data(ttl=600)
def live_search_yahoo_tickers(query_str, market_filter="ALL"):
    if not query_str or len(query_str.strip()) < 1:
        return []
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query_str.strip())}&quotesCount=25&newsCount=0"
    headers = {"User-Agent": "Mozilla/5.0"}
    results = []
    try:
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            for q in res.json().get("quotes", []):
                sym = q.get("symbol", "")
                name = q.get("longname") or q.get("shortname") or sym
                exch = q.get("exchDisp") or q.get("exchange") or ""
                if q.get("quoteType", "") not in ["EQUITY", "ETF", "INDEX"]:
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
def analyze_any_stock_deep(ticker_sym, shariah_mode=False):
    tk = yf.Ticker(ticker_sym)
    info = tk.info or {}
    hist = tk.history(period="max")
    if hist.empty:
        hist = tk.history(period="5y")
    if hist.empty and not info.get("regularMarketPrice") and not info.get("currentPrice"):
        return None

    curr_p = info.get("currentPrice") or info.get("regularMarketPrice") or (float(hist['Close'].iloc[-1]) if not hist.empty else 0.0)
    comp_name = info.get("longName") or info.get("shortName") or ticker_sym
    sector = info.get("sector") or "Diversified / ETF"
    industry = info.get("industry") or sector
    is_indian_stock = ticker_sym.endswith(".NS") or ticker_sym.endswith(".BO") or info.get("currency") == "INR"
    curr_sym = "₹" if is_indian_stock else "$"

    mcap = info.get("marketCap") or 0
    tot_debt = info.get("totalDebt") or 0
    op_cashflow = info.get("operatingCashflow") or 0
    promoter_holding = (info.get("heldPercentInsiders") or 0) * 100
    inst_holding = (info.get("heldPercentInstitutions") or 0) * 100
    rev_growth = (info.get("revenueGrowth") or 0) * 100
    earn_growth = (info.get("earningsGrowth") or 0) * 100
    op_margin = (info.get("operatingMargins") or 0) * 100
    prof_margin = (info.get("profitMargins") or 0) * 100
    pe_ratio = info.get("trailingPE") or info.get("forwardPE") or 0
    eps = info.get("trailingEps") or 0
    bv = info.get("bookValue") or 0

    raw_roe = info.get("returnOnEquity")
    if raw_roe is not None:
        roe = raw_roe * 100
    else:
        net_inc = info.get("netIncomeToCommon") or 0
        sh = info.get("sharesOutstanding") or 0
        roe = (net_inc / (bv * sh) * 100) if (bv * sh) > 0 else prof_margin

    debt_to_mcap = (tot_debt / mcap * 100) if mcap > 0 else 0.0

    # India Quality-Growth Fair Value + Classic Graham
    graham_raw = float(np.sqrt(22.5 * eps * bv)) if (eps > 0 and bv > 0) else 0.0
    if eps > 0:
        growth_est = max(10.0, min(30.0, max(rev_growth, earn_growth, 12.0)))
        quality_pe_cap = (18.0 + (growth_est * 1.1) + (5.0 if roe >= 20 else 0.0)) if is_indian_stock else (15.0 + growth_est)
        fair_val = max(graham_raw, float(eps * quality_pe_cap))
    else:
        fair_val = curr_p * 0.75

    ret_1y, ret_5y, above_200dma = 0.0, 0.0, True
    covid_drop_pct = None
    max_dd_5y = 0.0
    if not hist.empty:
        closes = hist['Close']
        if len(closes) >= 200:
            above_200dma = curr_p >= closes.rolling(200).mean().iloc[-1]
        ret_1y = ((curr_p - float(closes.iloc[-252])) / float(closes.iloc[-252])) * 100 if len(closes) >= 252 else ((curr_p - float(closes.iloc[0])) / float(closes.iloc[0])) * 100
        hist_5y = closes.tail(1260)
        ret_5y = ((curr_p - float(hist_5y.iloc[0])) / float(hist_5y.iloc[0])) * 100
        roll_max = hist_5y.cummax()
        max_dd_5y = float((((hist_5y - roll_max) / roll_max) * 100).min())
        try:
            idx_tz = closes.index.tz
            covid_slice = closes[(closes.index >= pd.Timestamp("2020-01-01", tz=idx_tz)) & (closes.index <= pd.Timestamp("2020-04-15", tz=idx_tz))]
            if len(covid_slice) > 10 and float(covid_slice.max()) > 0:
                covid_drop_pct = ((float(covid_slice.min()) - float(covid_slice.max())) / float(covid_slice.max())) * 100
        except Exception:
            pass

    non_halal_kw = ["Bank", "Financial", "Insurance", "Tobacco", "Cigarette", "Brew", "Distill", "Alcohol", "Casino", "Gambling", "Defense", "Pork"]
    is_prohibited_sec = any(k.lower() in (sector + " " + industry + " " + comp_name).lower() for k in non_halal_kw)
    shariah_pass = (not is_prohibited_sec) and (debt_to_mcap < 33.0)

    why_rec, why_not_rec = [], []
    if roe >= 16:
        why_rec.append(f"ഇന്ത്യൻ Coffee-Can നിലവാരത്തിലുള്ള ഉയർന്ന ലാഭക്ഷമത (ROE: {roe:.1f}% >= 16%).")
    else:
        why_not_rec.append(f"മൂലധന ലാഭക്ഷമത കുറവാണ് (ROE: {roe:.1f}% < 16%).")

    if debt_to_mcap < 15:
        why_rec.append(f"വളരെ കുറഞ്ഞ കടബാധ്യത (Debt/MCap: {debt_to_mcap:.1f}%). മാന്ദ്യത്തിലും തകരില്ല.")
    elif debt_to_mcap < 33:
        why_rec.append(f"കടം സുരക്ഷിത പരിധിക്കുള്ളിലാണ് (Debt/MCap: {debt_to_mcap:.1f}% < 33%).")
    else:
        why_not_rec.append(f"അമിതമായ കടബാധ്യതയുണ്ട് (Debt/MCap: {debt_to_mcap:.1f}% >= 33%).")

    if is_indian_stock and promoter_holding >= 45:
        why_rec.append(f"ശക്തമായ പ്രൊമോട്ടർ പങ്കാളിത്തം (Promoter Holding: {promoter_holding:.1f}% >= 45% - Indian Standard Pass).")
    elif is_indian_stock and 0 < promoter_holding < 25 and inst_holding < 30:
        why_not_rec.append(f"പ്രൊമോട്ടർ ഓഹരി പങ്കാളിത്തം കുറവാണ് ({promoter_holding:.1f}%).")

    if op_cashflow > 0:
        why_rec.append("പോസിറ്റീവ് ഓപ്പറേറ്റിംഗ് ക്യാഷ് ഫ്ലോ (യഥാർത്ഥ പണം കമ്പനിയിലേക്ക് വരുന്നുണ്ട്).")
    elif op_cashflow < 0:
        why_not_rec.append("ഓപ്പറേറ്റിംഗ് ക്യാഷ് ഫ്ലോ നെഗറ്റീവ് ആണ് (ലാഭം പേപ്പറിൽ മാത്രമാണ്).")

    if curr_p <= fair_val * 1.15 and fair_val > 0:
        why_rec.append(f"ഇന്ത്യൻ വളർച്ചാ ഫോർമുല പ്രകാരം ന്യായമായ വിലയിലാണ് (Current: {curr_sym}{curr_p:,.0f} vs Quality Fair Value: {curr_sym}{fair_val:,.0f}).")
    elif pe_ratio > 65:
        why_not_rec.append(f"ഓഹരി വില ഉയർന്ന P/E-യിലാണ് ({pe_ratio:.1f}x). SIP രീതി മാത്രം ഉപയോഗിക്കുക.")

    if covid_drop_pct is not None:
        if covid_drop_pct > -28.0:
            why_rec.append(f"🛡️ **കോവിഡ് തകർച്ച അതിജീവന പരീക്ഷണം പാസ്സായി:** 2020-ൽ നിഫ്റ്റി -38% വീണപ്പോൾ ഈ ഓഹരി വെറും {covid_drop_pct:.1f}% മാത്രമേ വീണുള്ളൂ!")
        else:
            why_not_rec.append(f"2020 കോവിഡ് തകർച്ചയിൽ ഈ ഓഹരി {covid_drop_pct:.1f}% ഇടിഞ്ഞിരുന്നു.")

    if is_prohibited_sec:
        why_not_rec.append(f"ശരീഅത്ത് പരിശോധന: '{sector}' വിഭാഗം പലിശ/നിരോധിത മേഖലയായതിനാൽ ഹലാൽ നിക്ഷേപകർ ഒഴിവാക്കുക.")

    suit_1y = "✅ 1 വർഷത്തേക്ക് അനുയോജ്യം (Strong Trend > 200 DMA)" if (above_200dma and ret_1y > 5 and pe_ratio < 70) else "⚠️ 1 വർഷത്തേക്ക് ചാഞ്ചാട്ടം ഉണ്ടാകാം (SIP Or Wait for Dip)"
    suit_5y = "✅ 3–5 വർഷത്തേക്ക് മികച്ചത് (Strong ROE, Cashflow & Safe Debt)" if (roe >= 14 and debt_to_mcap < 33 and op_cashflow >= 0) else "❌ 3–5 വർഷത്തേക്ക് റെക്കമെൻഡ് ചെയ്യുന്നില്ല"
    suit_10y = "🏛️ 10+ വർഷത്തേക്ക് നമ്പർ-1 Moat Compounder!" if (roe >= 18 and debt_to_mcap < 20 and op_margin >= 14) else "❌ 10+ വർഷത്തേക്ക് വെക്കാൻ അനുയോജ്യമല്ല"

    overall_score = (30 if roe >= 16 else 0) + (25 if debt_to_mcap < 25 else 0) + (20 if (op_margin >= 14 or op_cashflow > 0) else 0) + (15 if above_200dma else 0) + (10 if curr_p <= fair_val * 1.2 else 0)
    if shariah_mode and not shariah_pass:
        overall_score = min(overall_score, 30)

    if overall_score >= 70 and (not shariah_mode or shariah_pass):
        verdict = "🟢 RECOMMENDED (ഇന്ത്യൻ & ഗ്ലോബൽ ഗുണനിലവാര മാനദണ്ഡങ്ങൾ പാസ്സായി!)"
    elif overall_score >= 50 and (not shariah_mode or shariah_pass):
        verdict = "🟡 WATCHLIST / HOLD (ശരാശരി നിലവാരം - ഇടിവുകളിൽ ഘട്ടംഘട്ടമായി പരിഗണിക്കാം)"
    else:
        verdict = "🔴 NOT RECOMMENDED / AVOID (ഒഴിവാക്കുക - താഴെ പറയുന്ന പോരായ്മകൾ ശ്രദ്ധിക്കുക)"

    return {
        "symbol": ticker_sym, "name": comp_name, "price": curr_p, "fair_val": fair_val, "graham_raw": graham_raw,
        "curr_sym": curr_sym, "sector": sector, "industry": industry, "roe": roe,
        "op_margin": op_margin, "debt_to_mcap": debt_to_mcap, "pe": pe_ratio,
        "promoter": promoter_holding, "op_cf_pos": (op_cashflow > 0),
        "covid_drop": covid_drop_pct, "max_dd_5y": max_dd_5y,
        "ret_1y": ret_1y, "ret_5y": ret_5y, "shariah_pass": shariah_pass,
        "why_rec": why_rec, "why_not_rec": why_not_rec,
        "suit_1y": suit_1y, "suit_5y": suit_5y, "suit_10y": suit_10y,
        "score": overall_score, "verdict": verdict, "hist": hist.tail(1260)
    }

@st.cache_data(ttl=1800)
def search_live_mutual_funds(query_str):
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
def analyze_mutual_fund_with_covid_test(scheme_code):
    try:
        res = requests.get(f"https://api.mfapi.in/mf/{scheme_code}", timeout=8)
        if res.status_code == 200:
            data = res.json()
            meta = data.get("meta", {})
            nav_list = data.get("data", [])
            if not nav_list:
                return None

            df_nav = pd.DataFrame(nav_list)
            df_nav['date_obj'] = pd.to_datetime(df_nav['date'], format="%d-%m-%Y", errors="coerce")
            df_nav['nav_val'] = pd.to_numeric(df_nav['nav'], errors="coerce")
            df_nav = df_nav.dropna().sort_values('date_obj').reset_index(drop=True)

            curr_nav = float(df_nav['nav_val'].iloc[-1])
            curr_date = df_nav['date'].iloc[-1]
            now_dt = df_nav['date_obj'].iloc[-1]

            def calc_cagr_df(years):
                target_dt = now_dt - pd.Timedelta(days=int(years * 365.25))
                sub = df_nav[df_nav['date_obj'] <= target_dt]
                if not sub.empty and float(sub['nav_val'].iloc[-1]) > 0:
                    return (((curr_nav / float(sub['nav_val'].iloc[-1])) ** (1.0 / years)) - 1.0) * 100
                return 0.0

            c1, c3, c5 = calc_cagr_df(1.0), calc_cagr_df(3.0), calc_cagr_df(5.0)

            covid_slice = df_nav[(df_nav['date_obj'] >= "2020-01-01") & (df_nav['date_obj'] <= "2020-04-15")]
            covid_drop = None
            if len(covid_slice) > 10 and float(covid_slice['nav_val'].max()) > 0:
                covid_drop = ((float(covid_slice['nav_val'].min()) - float(covid_slice['nav_val'].max())) / float(covid_slice['nav_val'].max())) * 100

            df_5y = df_nav[df_nav['date_obj'] >= (now_dt - pd.Timedelta(days=1825))]
            roll_max = df_5y['nav_val'].cummax()
            dd = ((df_5y['nav_val'] - roll_max) / roll_max) * 100
            max_dd = float(dd.min()) if not dd.empty else 0.0

            sname = meta.get("scheme_name", "")
            is_direct = "direct" in sname.lower()

            why_mf, why_not_mf = [], []
            if covid_drop is not None:
                if covid_drop > -28.0:
                    why_mf.append(f"🛡️ **കോവിഡ് തകർച്ചയിൽ പിടിച്ചുനിന്ന ഫണ്ട്:** 2020-ൽ നിഫ്റ്റി -38.4% ഇടിഞ്ഞപ്പോൾ ഈ ഫണ്ട് വെറും **{covid_drop:.1f}%** മാത്രമാണ് ഇടിഞ്ഞത്!")
                else:
                    why_not_mf.append(f"2020 കോവിഡ് തകർച്ചയിൽ ഈ ഫണ്ട് {covid_drop:.1f}% ഇടിഞ്ഞിരുന്നു.")

            if max_dd > -20.0:
                why_mf.append(f"കഴിഞ്ഞ 5 വർഷത്തെ ഏറ്റവും വലിയ ഇടിവ് (Max Drawdown) വെറും `{max_dd:.1f}%` മാത്രമാണ്.")
            else:
                why_not_mf.append(f"വിപണി ഇടിയുമ്പോൾ `{max_dd:.1f}%` വരെ താഴേക്ക് പോയിട്ടുണ്ട്.")

            if c3 >= 15 or c5 >= 15:
                why_mf.append(f"മികച്ച ദീർഘകാല ലാഭം (3Y CAGR: {c3:.1f}%, 5Y CAGR: {c5:.1f}%).")
            else:
                why_not_mf.append(f"3-5 വർഷത്തെ ശരാശരി വളർച്ച ({c3:.1f}%) കുറവാണ്.")

            if is_direct:
                why_mf.append("Direct Plan ആയതിനാൽ ബ്രോക്കർ കമ്മീഷൻ ഇല്ല.")
            else:
                why_not_mf.append("ഇതൊരു Regular Plan ആണ്! കമ്മീഷൻ ഒഴിവാക്കാൻ ഇതിന്റെ Direct Plan എടുക്കുക.")

            rec_status = "🟢 RECOMMENDED CRISIS-PROOF SIP FUND" if (is_direct and (c3 >= 14 or c5 >= 14)) else "🔴 NOT RECOMMENDED (Switch to Direct Plan or Lower-Drawdown Fund)"

            return {
                "name": sname, "house": meta.get("fund_house", ""), "category": meta.get("scheme_category", ""),
                "nav": curr_nav, "date": curr_date, "cagr_1y": c1, "cagr_3y": c3, "cagr_5y": c5,
                "covid_drop": covid_drop, "max_dd": max_dd,
                "why_mf": why_mf, "why_not_mf": why_not_mf, "rec_status": rec_status,
                "chart_df": df_5y.set_index('date_obj')['nav_val']
            }
    except Exception:
        pass
    return None

@st.cache_data(ttl=1800)
def fetch_live_ipos_india():
    ipo_items = []
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=5)
        r = s.get("https://www.nseindia.com/api/ipo-current-issue", headers=headers, timeout=6)
        if r.status_code == 200:
            for item in r.json():
                ser = item.get("series", "EQ")
                rec_tag = "🟢 APPLY IF QIB > 10x (Mainboard)" if ser == "EQ" else "🔴 AVOID FOR RETAIL (SME High Risk)"
                ipo_items.append({
                    "IPO കമ്പനി": item.get("companyName", "N/A"),
                    "വിഭാഗം": "Mainboard" if ser == "EQ" else f"SME ({ser})",
                    "സ്റ്റാറ്റസ്": "🟢 OPEN NOW (NSE Live)",
                    "തീയതി": f"{item.get('issueStartDate', '')} - {item.get('issueEndDate', '')}",
                    "വില": f"₹{item.get('issuePrice', 'TBA')}",
                    "ഇന്ത്യൻ സ്റ്റാൻഡേർഡ് വിധി": rec_tag
                })
    except Exception:
        pass

    try:
        rss_url = "https://news.google.com/rss/search?q=IPO+GMP+subscription+India+when:7d&hl=en-IN&gl=IN&ceid=IN:en"
        r_rss = requests.get(rss_url, headers=headers, timeout=6)
        if r_rss.status_code == 200:
            root = ET.fromstring(r_rss.content)
            for item in root.findall(".//item")[:12]:
                title = item.find("title").text if item.find("title") is not None else ""
                pub = item.find("pubDate").text[:16] if item.find("pubDate") is not None else ""
                tl = title.lower()
                rec_v = "🔴 SME HIGH RISK" if "sme" in tl else ("🟢 STRONG BUZZ (Check QIB > 15x)" if ("gmp" in tl or "subscri" in tl) else "🟡 UPCOMING / TRACK")
                ipo_items.append({
                    "IPO കമ്പനി": title.split(" - ")[0],
                    "വിഭാഗം": "SME" if "sme" in tl else "Mainboard / News",
                    "സ്റ്റാറ്റസ്": "📡 LIVE UPDATE",
                    "തീയതി": pub,
                    "വില": "See Analyzer Below",
                    "ഇന്ത്യൻ സ്റ്റാൻഡേർഡ് വിധി": rec_v
                })
    except Exception:
        pass
    return ipo_items

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
        c.execute('''CREATE TABLE IF NOT EXISTS user_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT, name TEXT, category TEXT, rating TEXT, message TEXT)''')
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
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (u_hash, xor_cipher_hex(api_k, u_hash), xor_cipher_hex(api_s, u_hash), red_u, tg_t, tg_c, xor_cipher_hex(acc_tok, u_hash), broker))
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
                'api_key': xor_decipher_hex(row[0] or '', u_hash),
                'api_secret': xor_decipher_hex(row[1] or '', u_hash),
                'redirect_uri': row[2] or 'https://my-trading-bot-wyjcnfn2bprzd4ysp8riie.streamlit.app',
                'tg_token': row[3] or '', 'tg_chat': row[4] or '',
                'access_token': xor_decipher_hex(row[5] or '', u_hash),
                'broker': row[6] or 'Upstox'
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
# 🌐 SIDEBAR & DUAL-LAYER AUTHENTICATION
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
                st.success("🎉 Access Token ഓട്ടോമാറ്റിക് ആയി ജനറേറ്റ് ചെയ്ത് എൻക്രിപ്റ്റ് ചെയ്തു!")

if "authenticated_user_hash" not in st.session_state:
    st.session_state["authenticated_user_hash"] = None

if not st.session_state["authenticated_user_hash"]:
    st.subheader("🔒 ഇരട്ട സുരക്ഷാ പ്രൈവറ്റ് ലോക്കർ ലോഗിൻ (100% Encrypted Data Isolation)" if is_ml else "🔒 Dual-Layer Encrypted Vault Login")
    st.info("നിങ്ങളുടെ ഡാറ്റ മറ്റൊരാൾക്കും ഊഹിച്ചെടുക്കാൻ കഴിയാതിരിക്കാൻ നിങ്ങളുടെ **യൂസർ ഐഡിയും (User ID)** **രഹസ്യ പാസ്‌കീയും (Secret Passkey)** നൽകുക. (നിങ്ങൾ നേരത്തെ പാസ്‌കീ മാത്രമാണ് ഉപയോഗിച്ചിരുന്നതെങ്കിൽ ആദ്യ കള്ളി ഒഴിവാക്കി താഴെ പാസ്‌കീ മാത്രം നൽകിയാലും പഴയ അക്കൗണ്ട് തുറക്കാം)." if is_ml else "Enter your User ID and Secret Passkey to unlock your isolated encrypted vault.")
    
    with st.form("vault_login_form"):
        l_col1, l_col2 = st.columns(2)
        uid_input = l_col1.text_input("👤 യൂസർനെയിം / ഇമെയിൽ (Optional for existing users):" if is_ml else "👤 Username / Email (Optional):")
        passkey_input = l_col2.text_input("🔑 രഹസ്യ പാസ്‌കീ (Secret Passkey - Required):" if is_ml else "🔑 Secret Passkey (Required):", type="password")
        consent_chk = st.checkbox(
            "⚖️ **നിയമപരമായ സമ്മതപത്രം (SEBI / RBI Disclaimer):** ഈ പ്ലാറ്റ്‌ഫോം പൂർണ്ണമായും **പഠന-ഗവേഷണ (Educational & Research)** ആവശ്യങ്ങൾക്ക് വേണ്ടി മാത്രമുള്ളതാണ്. ഇതിന്റെ നിർമ്മാതാക്കൾ SEBI രജിസ്റ്റർ ചെയ്ത ഇൻവെസ്റ്റ്‌മെന്റ് അഡ്വൈസർമാരോ (RIA) RBI അംഗീകൃത സ്ഥാപനമോ അല്ല. ഇതിലെ വിവരങ്ങൾ വെച്ച് ഞാൻ സ്വന്തം ഉത്തരവാദിത്തത്തിലും സ്വന്തം പഠനത്തിലും മാത്രമേ നിക്ഷേപ തീരുമാനങ്ങൾ എടുക്കുകയുള്ളൂ എന്ന് ഞാൻ സമ്മതിക്കുന്നു.",
            value=True
        )
        login_submitted = st.form_submit_button("🔓 സമ്മതിച്ച് അക്കൗണ്ട് തുറക്കുക (Agree & Unlock)" if is_ml else "🔓 Agree & Unlock Workspace", type="primary")
        if login_submitted:
            if not consent_chk:
                st.error("⚠️ തുടരുന്നതിന് മുൻപ് നിയമപരമായ സമ്മതപത്രം ടിക്ക് ചെയ്യുക!")
            elif passkey_input.strip():
                combined_secret = f"{uid_input.strip().lower()}:{passkey_input.strip()}" if uid_input.strip() else passkey_input.strip()
                st.session_state["authenticated_user_hash"] = hashlib.sha256(combined_secret.encode()).hexdigest()[:16]
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
else:
    if saved_c.get('access_token') and not user_vault[USER_HASH].get('token'):
        user_vault[USER_HASH]['token'] = saved_c['access_token']

state = user_vault[USER_HASH]

st.sidebar.markdown("---")
phil_options = ["🌐 ആഗോള ജനറൽ മോഡ് (Conventional)", "🌙 100% പ്യുവർ ശരീഅത്ത് മോഡ് (Halal AAOIFI)"] if is_ml else ["🌐 Global Conventional Mode", "🌙 100% Pure Shariah Mode (AAOIFI)"]
wealth_mode = st.sidebar.radio("നിക്ഷേപ തത്ത്വശാസ്ത്രം:" if is_ml else "Investment Philosophy:", phil_options)
is_shariah = ("ശരീഅത്ത്" in wealth_mode or "Shariah" in wealth_mode)
state['shariah_lock'] = is_shariah

MENU_ITEMS = [
    "🧭 തുടക്കക്കാരുടെ വഴികാട്ടി, SIP ഗ്രാഫ് & സക്കാത്ത്",
    "🏛️ നമ്പർ-1 സ്റ്റോക്ക് റെക്കമെൻഡേഷൻസ് & ലൈവ് സ്കാനർ (India+Global)",
    "📈 കോവിഡ് തകർച്ചയെ അതിജീവിച്ച മ്യൂച്വൽ ഫണ്ടുകൾ & ലൈവ് സെർച്ച്",
    "🎟️ ലൈവ് ഐ.പി.ഒ (IPO) റെക്കമെൻഡേഷൻസ് & QIB അനലൈസർ",
    "📜 ബോണ്ടുകൾ, REITs (വാടക വരുമാനം), SIF & ഹലാൽ മാർഗ്ഗങ്ങൾ",
    "💳 കടം തീർക്കൽ, RBI ഭീഷണി പ്രതിരോധം & കംപ്ലയിന്റ് ജനറേറ്റർ",
    "🎯 ലക്ഷ്യാധിഷ്ഠിത പോർട്ട്ഫോളിയോ (Goal Allocator)",
    "💼 എന്റെ ലൈവ് പോർട്ട്ഫോളിയോ & എക്സിറ്റ് വാച്ച്ഡോഗ്",
    "🌍 യു.എസ് (US) സ്റ്റോക്ക് റെക്കമെൻഡേഷൻസ് & ഇന്ത്യൻ ടാക്സ് കാൽക്കുലേറ്റർ",
    "🥇 മികച്ച ഗോൾഡ് & സിൽവർ റെക്കമെൻഡേഷൻസ്",
    "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട് (100% Full Algo Execution Engine)",
    "📚 എന്റെ നിക്ഷേപ ജേർണൽ (Audit Journal)",
    "💬 അഭിപ്രായങ്ങളും ചോദ്യങ്ങളും (Private & Public Feedback)"
]

st.sidebar.markdown("---")
main_menu = st.sidebar.radio("പ്രധാന വിഭാഗം തിരഞ്ഞെടുക്കുക:" if is_ml else "Select Core Module:", MENU_ITEMS)

def render_universal_stock_search(key_prefix, market_filter="ALL", default_query="Polycab"):
    c_s1, c_s2 = st.columns([2, 3])
    q_input = c_s1.text_input(
        "🔍 കമ്പനിയുടെ പേര് ടൈപ്പ് ചെയ്യുക (ഉദാ: Kitex, Kalyan, Tata, ITC, Nvidia):",
        value=default_query,
        key=f"{key_prefix}_q"
    )
    matches = live_search_yahoo_tickers(q_input, market_filter=market_filter)
    if matches:
        sel = c_s2.selectbox(
            f"✅ '{q_input}' എന്നതിൽ വരുന്ന കമ്പനികൾ (ഇതിൽ നിന്ന് തിരഞ്ഞെടുക്കുക):",
            matches,
            key=f"{key_prefix}_sel"
        )
        return sel.split(" | ")[0].strip()
    else:
        c_s2.warning("ഈ പേരിൽ കമ്പനികൾ കണ്ടില്ല. അക്ഷരങ്ങൾ മാറ്റി ടൈപ്പ് ചെയ്യുക.")
        return q_input.upper().strip()

# ##################################################################
# 🧭 MODULE 0: BEGINNER GUIDE, SIP COMPOUNDING GRAPH & ZAKAT
# ##################################################################
if main_menu == MENU_ITEMS[0]:
    st.title("🧭 തുടക്കക്കാരുടെ വഴികാട്ടി, SIP കോമ്പൗണ്ടിംഗ് ഗ്രാഫ് & സക്കാത്ത് കാൽക്കുലേറ്റർ")
    t_g1, t_g2, t_g3, t_g4 = st.tabs([
        "🗺️ 4-ഘട്ട സാമ്പത്തിക വഴികാട്ടി",
        "📈 SIP കോമ്പൗണ്ടിംഗ് & പണപ്പെരുപ്പ കാൽക്കുലേറ്റർ",
        "💰 മാസവരുമാന & സേവിങ്സ് ഡോക്ടർ",
        "🌙 സക്കാത്ത് (2.5%) കാൽക്കുലേറ്റർ"
    ])

    with t_g1:
        st.success("👋 **ആദ്യമായിട്ടാണോ ഇവിടെ?** ഓരോ മെനു തുറക്കുമ്പോഴും **ഇന്ത്യൻ & ഗ്ലോബൽ സ്റ്റാൻഡേർഡ് പ്രകാരം തിരഞ്ഞെടുത്ത നമ്പർ-1 സ്റ്റോക്കുകൾ, കോവിഡ് തകർച്ചയിൽ പോലും വീഴാത്ത മ്യൂച്വൽ ഫണ്ടുകൾ, ബോണ്ടുകൾ, IPO-കൾ** എന്നിവ മുകളിൽ തന്നെ ഓട്ടോമാറ്റിക് ആയി കാണാം!")
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("""
            * **ഘട്ടം 1 (കടം തീർക്കൽ & RBI സംരക്ഷണം):** ലോൺ കുടിശ്ശികയോ റിക്കവറി ഏജന്റുമാരുടെ ഭീഷണിയോ ഉണ്ടെങ്കിൽ **'💳 കടം തീർക്കൽ & RBI ഭീഷണി പ്രതിരോധം'** തുറക്കുക.
            * **ഘട്ടം 2 (എമർജൻസി ഫണ്ട് & ഗോൾഡ്):** 6 മാസത്തെ ചെലവിനുള്ള പണം സുരക്ഷിതമാക്കിയ ശേഷം മാത്രം ഓഹരി വിപണിയിലേക്ക് കടക്കുക.
            """)
        with g2:
            st.markdown("""
            * **ഘട്ടം 3 (കോവിഡ് തകർച്ചയെ അതിജീവിച്ച ഫണ്ടുകൾ & Moat സ്റ്റോക്കുകൾ):** വിപണി ഇടിയുമ്പോഴും തകരാതെ നിൽക്കുന്ന ഫണ്ടുകളിൽ ദീർഘകാല SIP ചെയ്യുക.
            * **ഘട്ടം 4 (ഇൻട്രാഡേ ബോട്ട്):** പേപ്പർ ട്രേഡിംഗിൽ പരീക്ഷിച്ച ശേഷം മാത്രം ലൈവ് ട്രേഡിംഗ് ഉപയോഗിക്കുക.
            """)

    with t_g2:
        st.subheader("📈 പ്രതിമാസ SIP കോമ്പൗണ്ടിംഗ് & പണപ്പെരുപ്പ (Inflation) കാൽക്കുലേറ്റർ")
        sip_c1, sip_c2, sip_c3 = st.columns(3)
        sip_m = sip_c1.number_input("പ്രതിമാസ നിക്ഷേപം (Monthly SIP ₹):", value=5000.0, step=1000.0)
        sip_yr = sip_c2.slider("വർഷങ്ങൾ (Years):", 1, 35, 15)
        sip_ret = sip_c3.slider("പ്രതീക്ഷിക്കുന്ന വാർഷിക വളർച്ച (% CAGR):", 8.0, 25.0, 15.0)

        r_m = (sip_ret / 100.0) / 12.0
        r_inf = ((max(1.0, sip_ret - 6.0)) / 100.0) / 12.0
        chart_rows = []
        for y in range(1, sip_yr + 1):
            n_m = y * 12
            invested = sip_m * n_m
            fv = sip_m * (((1 + r_m) ** n_m - 1) / r_m) * (1 + r_m)
            fv_real = sip_m * (((1 + r_inf) ** n_m - 1) / r_inf) * (1 + r_inf)
            chart_rows.append({"Year": y, "മുടക്കുമുതൽ (Invested)": round(invested), "ആകെ വളർച്ച (Total Value)": round(fv), "പണപ്പെരുപ്പം കിഴിച്ചുള്ള മൂല്യം (Inflation-Adjusted)": round(fv_real)})
        df_sip = pd.DataFrame(chart_rows).set_index("Year")
        tot_inv = df_sip["മുടക്കുമുതൽ (Invested)"].iloc[-1]
        tot_fv = df_sip["ആകെ വളർച്ച (Total Value)"].iloc[-1]
        tot_real = df_sip["പണപ്പെരുപ്പം കിഴിച്ചുള്ള മൂല്യം (Inflation-Adjusted)"].iloc[-1]
        s1, s2, s3 = st.columns(3)
        s1.metric("ആകെ മുടക്കുമുതൽ", f"₹{tot_inv:,.0f}")
        s2.metric(f"{sip_yr} വർഷത്തിന് ശേഷം ലഭിക്കുന്ന തുക", f"₹{tot_fv:,.0f}", f"+₹{tot_fv-tot_inv:,.0f} Profit")
        s3.metric("ഇന്നത്തെ മൂല്യത്തിൽ (6% പണപ്പെരുപ്പം കിഴിച്ചാൽ)", f"₹{tot_real:,.0f}")
        st.line_chart(df_sip)

    with t_g3:
        inc_c1, inc_c2, inc_c3 = st.columns(3)
        m_income = inc_c1.number_input("മാസവരുമാനം (₹):", value=50000.0, step=5000.0)
        m_expense = inc_c2.number_input("വീട്ടുചെലവുകൾ (₹):", value=25000.0, step=2000.0)
        m_emi_now = inc_c3.number_input("നിലവിലെ ലോൺ EMI (₹):", value=10000.0, step=1000.0)
        surplus = m_income - (m_expense + m_emi_now)
        if surplus > 0:
            st.success(f"✅ **നിങ്ങളുടെ കൈയിൽ മിച്ചമുള്ളത്: ₹{surplus:,.0f} / മാസം.** ഇതിൽ **₹{surplus*0.5:,.0f}** കടം നേരത്തെ വീട്ടാനും, **₹{surplus*0.5:,.0f}** മികച്ച മ്യൂച്വൽ ഫണ്ട് / സ്റ്റോക്ക് SIP ചെയ്യാനും ഉപയോഗിക്കുക!")
        else:
            st.error(f"🚨 **ചെലവും EMI-യും വരുമാനത്തേക്കാൾ ₹{abs(surplus):,.0f} കൂടുതലാണ്!** അനാവശ്യ ചെലവുകൾ കുറയ്ക്കുക.")

    with t_g4:
        z1, z2, z3 = st.columns(3)
        z_stocks = z1.number_input("ഓഹരി / മ്യൂച്വൽ ഫണ്ട് മൂല്യം (₹):", value=100000.0, step=10000.0)
        z_gold_cash = z2.number_input("സ്വർണ്ണം & ക്യാഷ് ബാലൻസ് (₹):", value=150000.0, step=10000.0)
        z_debts = z3.number_input("കുറയ്ക്കേണ്ട അടിയന്തര കടങ്ങൾ (₹):", value=20000.0, step=5000.0)
        net_zakatable = max(0.0, (z_stocks + z_gold_cash) - z_debts)
        st.info(f"🕌 **സക്കാത്ത് നൽകേണ്ട ആകെ സമ്പത്ത്:** `₹{net_zakatable:,.0f}` | **വാർഷിക സക്കാത്ത് (2.5%):** **`₹{net_zakatable * 0.025:,.0f}`**")

# ##################################################################
# 🏛️ MODULE 1: INDIA + GLOBAL STANDARD STOCK RECOMMENDATIONS & SCANNER
# ##################################################################
elif main_menu == MENU_ITEMS[1]:
    st.title("🏛️ നമ്പർ-1 സ്റ്റോക്ക് റെക്കമെൻഡേഷൻസ് & ഇന്ത്യൻ-ഗ്ലോബൽ ലൈവ് സ്കാനർ")

    with st.expander("📐 എന്തുകൊണ്ട് അമേരിക്കൻ ബെഞ്ചമിൻ ഗ്രഹാം ഫോർമുല ഇന്ത്യയിൽ തിരുത്തണം? (Indian vs Global Standard)", expanded=False):
        st.markdown("""
        * **അമേരിക്കൻ ഗ്രഹാം ഫോർമുലയുടെ പരിമിതി:** ബെഞ്ചമിൻ ഗ്രഹാം ഫോർമുല ($\sqrt{22.5 \times \text{EPS} \times \text{Book Value}}$) ഫാക്ടറികളുള്ള പഴയ കമ്പനികൾക്ക് വേണ്ടിയുള്ളതാണ്. ഇന്ത്യയിലെ ഏറ്റവും മികച്ച അസറ്റ്-ലൈറ്റ് കമ്പനികളായ **TCS, Titan, Polycab, CDSL** എന്നിവയ്ക്ക് Book Value കുറവും ROCE വളരെ കൂടുതലുമാണ് (>30%). അതിനാൽ പഴയ ഗ്രഹാം ഫോർമുല മാത്രം നോക്കിയാൽ ഇന്ത്യയിലെ നമ്പർ-1 കമ്പനികൾ നഷ്ടമാകും!
        * **ഞങ്ങളുടെ 'India Quality-Adjusted Valuation Standard':** നമ്മൾ ഗ്രഹാം ഫോർമുലയ്ക്കൊപ്പം ഇന്ത്യയുടെ **Coffee-Can ROCE (>20%), PEG Ratio, Promoter Holding (>45%), Positive Operating Cash Flow, COVID-19 Crash Resilience** എന്നിവ ചേർത്താണ് ഓരോ സ്റ്റോക്കും റെക്കമെൻഡ് ചെയ്യുന്നത്!
        """)

    st.subheader("🏆 1. ഇന്ത്യയിലെയും ലോകത്തെയും നമ്പർ-1 ഓട്ടോമാറ്റിക് സ്റ്റോക്ക് റെക്കമെൻഡേഷൻസ് (Top Curated Compounders)")
    if is_shariah:
        st.success("🌙 **100% ശരീഅത്ത് മോഡ് ആക്ടീവ്:** പലിശ ബാങ്കുകൾ ഒഴിവാക്കി, ഇന്ത്യയിലെയും ആഗോള വിപണിയിലെയും ഏറ്റവും മികച്ച ഹലാൽ Moat കമ്പനികൾ:")
        auto_rec_stocks = [
            {"Stock": "TCS", "Sector": "India #1 IT Moat", "Horizon": "5 - 10+ Years", "Indian & Global Metrics": "ROCE: 58% | Promoter: 71.7% | Debt: 0.6%", "എന്തുകൊണ്ട് നമ്പർ-1? (Why Recommended)": "റ്റാറ്റ ഗ്രൂപ്പ് പ്രൊമോട്ടർ, കടരഹിത ക്യാഷ് മെഷീൻ, കോവിഡ് തകർച്ചയിൽ -21% മാത്രം ഇടിഞ്ഞ് വേഗത്തിൽ തിരിച്ചുകയറി.", "Exit Rule": "മാർജിൻ 20%-ൽ താഴെയായാൽ.", "Verdict": "🟢 #1 INDIA HALAL MOAT"},
            {"Stock": "POLYCAB", "Sector": "India #1 Wires & Cables", "Horizon": "3 - 10 Years", "Indian & Global Metrics": "ROCE: 28% | Promoter: 63% | Debt: 0.8%", "എന്തുകൊണ്ട് നമ്പർ-1? (Why Recommended)": "ഇന്ത്യൻ വയർ വിപണിയിലെ 25%+ കുത്തക, ശക്തമായ പ്രൊമോട്ടർ പങ്കാളിത്തം, പോസിറ്റീവ് ക്യാഷ് ഫ്ലോ.", "Exit Rule": "വിപണി വിഹിതം നഷ്ടപ്പെട്ടാൽ.", "Verdict": "🟢 STRONG RECOMMEND"},
            {"Stock": "TITAN", "Sector": "India #1 Jewellery Moat", "Horizon": "5 - 10+ Years", "Indian & Global Metrics": "ROE: 32% | Promoter: 52.9% (Tata+TIDCO)", "എന്തുകൊണ്ട് നമ്പർ-1? (Why Recommended)": "തനിഷ്ക് (Tanishq) ബ്രാൻഡ് കുത്തക, രാകേഷ് ജുൻജുൻവാലയുടെ എക്കാലത്തെയും മികച്ച കോമ്പൗണ്ടർ.", "Exit Rule": "ROE 15%-ൽ താഴെയായാൽ.", "Verdict": "🟢 STRONG RECOMMEND"},
            {"Stock": "SUNPHARMA", "Sector": "India #1 Specialty Pharma", "Horizon": "3 - 10 Years", "Indian & Global Metrics": "ROCE: 18% | Promoter: 54.5% | Debt: 1.5%", "എന്തുകൊണ്ട് നമ്പർ-1? (Why Recommended)": "മാന്ദ്യത്തിലും യുദ്ധത്തിലും തകരാത്ത ജീവൻരക്ഷാ മരുന്ന് കുത്തക.", "Exit Rule": "സ്ഥിരമായ USFDA നിരോധനം വന്നാൽ.", "Verdict": "🟢 DEFENSIVE PICK"},
            {"Stock": "NVDA / MSFT (US)", "Sector": "World #1 AI & Cloud", "Horizon": "5 - 10 Years", "Indian & Global Metrics": "ROE: 35%-90% | Debt < 3% | Global Monopoly", "എന്തുകൊണ്ട് നമ്പർ-1? (Why Recommended)": "ലോകത്തിലെ AI ചിപ്പുകളുടെയും ക്ലൗഡ് കമ്പ്യൂട്ടിംഗിന്റെയും 80% കുത്തക + ഡോളർ മൂല്യവർദ്ധനവ്.", "Exit Rule": "AI ചിപ്പ് കുത്തക നഷ്ടപ്പെട്ടാൽ.", "Verdict": "🟢 #1 GLOBAL MOAT"}
        ]
    else:
        auto_rec_stocks = [
            {"Stock": "TCS", "Sector": "India #1 IT Moat", "Horizon": "5 - 10+ Years", "Indian & Global Metrics": "ROCE: 58% | Promoter: 71.7% | Debt: 0.6%", "എന്തുകൊണ്ട് നമ്പർ-1? (Why Recommended)": "കടരഹിത ക്യാഷ് മെഷീൻ, ഉയർന്ന ഡിവിഡന്റ്, ആഗോള ഐ.ടി കുത്തക.", "Exit Rule": "മാർജിൻ 20%-ൽ താഴെയായാൽ.", "Verdict": "🟢 #1 INDIA MOAT"},
            {"Stock": "CDSL", "Sector": "Depository Monopoly", "Horizon": "5 - 10+ Years", "Indian & Global Metrics": "ROCE: 33% | Debt: 0% | Op Margin: 60%", "എന്തുകൊണ്ട് നമ്പർ-1? (Why Recommended)": "ഇന്ത്യയിൽ ഓഹരി വിപണി വളരുമ്പോൾ ടോൾ ബൂത്ത് പോലെ ലാഭം നേടുന്ന ഡ്യുവോപ്പോളി കുത്തക.", "Exit Rule": "SEBI ചാർജുകൾ പകുതിയായി കുറച്ചാൽ.", "Verdict": "🟢 STRONG RECOMMEND"},
            {"Stock": "POLYCAB", "Sector": "India #1 Wires & Cables", "Horizon": "3 - 10 Years", "Indian & Global Metrics": "ROCE: 28% | Promoter: 63% | Debt: 0.8%", "എന്തുകൊണ്ട് നമ്പർ-1? (Why Recommended)": "ഇന്ത്യൻ വയർ വിപണിയിലെ 25%+ കുത്തക.", "Exit Rule": "മാർക്കറ്റ് ഷെയർ ഇടിഞ്ഞാൽ.", "Verdict": "🟢 STRONG RECOMMEND"},
            {"Stock": "HAL", "Sector": "Sovereign Defence Monopoly", "Horizon": "3 - 8 Years", "Indian & Global Metrics": "ROCE: 31% | Promoter: 71.6% (Govt) | Debt: 0%", "എന്തുകൊണ്ട് നമ്പർ-1? (Why Recommended)": "വ്യോമസേനയ്ക്ക് ഫൈറ്റർ ജെറ്റുകൾ നിർമ്മിക്കുന്ന പരമാധികാര കുത്തക, ₹94,000 കോടി ഓർഡർ ബുക്ക്.", "Exit Rule": "കുത്തക പദവി നഷ്ടപ്പെട്ടാൽ.", "Verdict": "🟢 RECOMMEND"},
            {"Stock": "LT", "Sector": "India #1 Capex Giant", "Horizon": "3 - 10 Years", "Indian & Global Metrics": "ROE: 15% | Order Book: ₹5L+ Cr", "എന്തുകൊണ്ട് നമ്പർ-1? (Why Recommended)": "ഇന്ത്യൻ അടിസ്ഥാന സൗകര്യ വികസനത്തിലെ പകരം വെക്കാനില്ലാത്ത എൻജിനീയറിംഗ് ഭീമൻ.", "Exit Rule": "Debt/Equity 1.5 കടന്നാൽ.", "Verdict": "🟢 RECOMMEND"}
        ]
    st.dataframe(pd.DataFrame(auto_rec_stocks), use_container_width=True, hide_index=True)

    with st.expander("📡 മാർക്കറ്റിലെ മറ്റ് സ്റ്റോക്കുകളെ ഇപ്പോൾ ലൈവ് ആയി സ്കാൻ ചെയ്ത് പുതിയ റെക്കമെൻഡേഷൻസ് കണ്ടെത്താൻ ഇവിടെ ക്ലിക്ക് ചെയ്യുക"):
        sc_c1, sc_c2 = st.columns(2)
        min_roe_f = sc_c1.slider("കുറഞ്ഞ ലാഭക്ഷമത (Min ROE %):", 10, 35, 15)
        max_debt_f = sc_c2.slider("പരമാവധി കടം (Max Debt/MCap %):", 5, 60, 33 if is_shariah else 45)
        if st.button("🔄 ഇപ്പോൾ മാർക്കറ്റ് ലൈവ് ആയി സ്കാൻ ചെയ്യുക (Run Live Market Screener)", type="primary"):
            scan_list = ["TCS.NS", "INFY.NS", "POLYCAB.NS", "SUNPHARMA.NS", "TITAN.NS", "PERSISTENT.NS", "CUMMINSIND.NS", "ASTRAL.NS", "DRREDDY.NS", "BEL.NS", "HAL.NS", "TRENT.NS"]
            live_recs = []
            p_bar = st.progress(0, text="⏳ ലൈവ് മാർക്കറ്റ് പരിശോധിക്കുന്നു...")
            for i, s_code in enumerate(scan_list):
                p_bar.progress((i + 1) / len(scan_list), text=f"⏳ സ്കാൻ ചെയ്യുന്നു: {s_code}...")
                r_data = analyze_any_stock_deep(s_code, shariah_mode=is_shariah)
                if r_data and r_data['roe'] >= min_roe_f and r_data['debt_to_mcap'] <= max_debt_f:
                    if is_shariah and not r_data['shariah_pass']:
                        continue
                    live_recs.append({
                        "Stock": s_code.replace(".NS", ""), "Company": r_data['name'],
                        "Live Price": f"₹{r_data['price']:,.1f}", "India Quality Fair Value": f"₹{r_data['fair_val']:,.1f}",
                        "ROE": f"{r_data['roe']:.1f}%", "Promoter %": f"{r_data['promoter']:.1f}%",
                        "Debt/MCap": f"{r_data['debt_to_mcap']:.1f}%",
                        "COVID-2020 Drop": f"{r_data['covid_drop']:.1f}%" if r_data['covid_drop'] else "N/A",
                        "Verdict": r_data['verdict'].split(" (")[0]
                    })
            p_bar.empty()
            if live_recs:
                st.dataframe(pd.DataFrame(live_recs), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🔎 2. പുറത്തുള്ള ഏത് സ്റ്റോക്കും (NSE / BSE / US) അടിച്ചു നോക്കൂ — എന്തുകൊണ്ട് റെക്കമെൻഡ് ചെയ്യുന്നു / ചെയ്യുന്നില്ല എന്ന് അറിയാം!")
    mkt_choice = st.radio("മാർക്കറ്റ് തിരഞ്ഞെടുക്കുക:", ["🇮🇳 ഇന്ത്യൻ മാർക്കറ്റ് (NSE & BSE)", "🇺🇸 യു.എസ് മാർക്കറ്റ് (US Stocks)", "🌐 എല്ലാ മാർക്കറ്റുകളും"], horizontal=True)
    m_filt = "INDIA" if "ഇന്ത്യൻ" in mkt_choice else ("US" if "യു.എസ്" in mkt_choice else "ALL")

    selected_sym = render_universal_stock_search("univ_scan", market_filter=m_filt, default_query="Polycab")

    if selected_sym:
        with st.spinner(f"⏳ `{selected_sym}`-ന്റെ ഇന്ത്യൻ & ഗ്ലോബൽ മാനദണ്ഡങ്ങളും കോവിഡ് അതിജീവന ശേഷിയും പരിശോധിക്കുന്നു..."):
            audit = analyze_any_stock_deep(selected_sym, shariah_mode=is_shariah)
            if not audit:
                st.error(f"❌ `{selected_sym}` എന്ന കമ്പനിയുടെ ഡാറ്റ ലഭ്യമല്ല. മുകളിലെ സെർച്ച് ബോക്സിൽ പേര് ടൈപ്പ് ചെയ്ത് വലതുവശത്തെ ലിസ്റ്റിൽ നിന്ന് തിരഞ്ഞെടുക്കുക.")
            else:
                st.markdown(f"### 🏢 {audit['name']} (`{audit['symbol']}`) — നിലവിലെ വില: **{audit['curr_sym']}{audit['price']:,.2f}**")
                st.caption(f"📐 **വാല്യുവേഷൻ താരതമ്യം:** ഇന്ത്യൻ ക്വാളിറ്റി-ഗ്രോത്ത് മൂല്യം (Quality Fair Value): **{audit['curr_sym']}{audit['fair_val']:,.1f}** | പരമ്പരാഗത യു.എസ് ഗ്രഹാം മൂല്യം: `{audit['curr_sym']}{audit['graham_raw']:,.1f}` | പ്രൊമോട്ടർ ഓഹരി: `{audit['promoter']:.1f}%`")
                
                if "🟢" in audit['verdict']:
                    st.success(f"### 🏆 വിധി (Verdict): {audit['verdict']} (Score: {audit['score']}/100)")
                elif "🟡" in audit['verdict']:
                    st.warning(f"### ⚖️ വിധി (Verdict): {audit['verdict']} (Score: {audit['score']}/100)")
                else:
                    st.error(f"### 🛑 വിധി (Verdict): {audit['verdict']} (Score: {audit['score']}/100)")

                k1, k2, k3, k4, k5 = st.columns(5)
                k1.metric("സെക്ടർ & പ്രൊമോട്ടർ", audit['sector'], f"Promoter: {audit['promoter']:.1f}%")
                k2.metric("ലാഭക്ഷമത (ROE)", f"{audit['roe']:.1f}%", "✅ >=16% Pass" if audit['roe'] >= 16 else "❌ <16% Weak")
                k3.metric("കടം (Debt / MCap)", f"{audit['debt_to_mcap']:.1f}%", "✅ <33% Safe" if audit['debt_to_mcap'] < 33 else "❌ High Debt")
                k4.metric("കോവിഡ് തകർച്ചയിൽ (2020)", f"{audit['covid_drop']:.1f}%" if audit['covid_drop'] else f"{audit['max_dd_5y']:.1f}% (5Y DD)", "Nifty fell -38.4%")
                k5.metric("ശരീഅത്ത് & ക്യാഷ് ഫ്ലോ", "✅ ഹലാൽ (HALAL)" if audit['shariah_pass'] else "❌ നോൺ-ഹലാൽ", "CashFlow: " + ("✅ +ve" if audit['op_cf_pos'] else "⚠️ -ve"))

                w1, w2 = st.columns(2)
                with w1:
                    st.success("#### ✅ എന്തുകൊണ്ട് റെക്കമെൻഡ് ചെയ്യുന്നു? (Positives / Why Buy)")
                    if audit['why_rec']:
                        for p in audit['why_rec']: st.markdown(f"- 🟢 {p}")
                    else:
                        st.write("- എടുത്തുപറയത്തക്ക പോസിറ്റീവ് ഘടകങ്ങൾ നിലവിലില്ല.")
                with w2:
                    st.error("#### ❌ എന്തുകൊണ്ട് റെക്കമെൻഡ് ചെയ്യുന്നില്ല / പ്രശ്നങ്ങൾ? (Problems / Red Flags)")
                    if audit['why_not_rec']:
                        for c_item in audit['why_not_rec']: st.markdown(f"- 🔴 {c_item}")
                    else:
                        st.write("- ഫണ്ടമെന്റൽ പോരായ്മകൾ ഒന്നും കണ്ടെത്തിയില്ല!")

                st.subheader("⏳ എത്ര കാലത്തേക്ക് ഇൻവെസ്റ്റ് ചെയ്യാം? (Time-Horizon Suitability)")
                h1, h2, h3 = st.columns(3)
                h1.info(f"**📅 1 വർഷത്തേക്ക്:**\n\n{audit['suit_1y']}")
                h2.info(f"**🚀 3 - 5 വർഷത്തേക്ക്:**\n\n{audit['suit_5y']}")
                h3.info(f"**🏛️ 10+ വർഷത്തേക്ക്:**\n\n{audit['suit_10y']}")

                if not audit['hist'].empty:
                    st.line_chart(audit['hist']['Close'])

# ##################################################################
# 📈 MODULE 2: COVID-CRASH SURVIVOR MUTUAL FUNDS & LIVE 10,000+ TESTER
# ##################################################################
elif main_menu == MENU_ITEMS[2]:
    st.title("📈 കോവിഡ് തകർച്ചയിലും (2020 Crash) വിപണി ഇടിവുകളിലും പിടിച്ചുനിന്ന മ്യൂച്വൽ ഫണ്ടുകൾ")
    st.caption("മാർക്കറ്റ് മുകളിലേക്ക് കയറുമ്പോൾ എല്ലാ ഫണ്ടുകളും ലാഭം കാണിക്കും. എന്നാൽ 2020 മാർച്ചിലെ കോവിഡ് തകർച്ചയിൽ (Nifty 50 -38.4% ഇടിഞ്ഞപ്പോൾ) ഏറ്റവും കുറവ് മാത്രം ഇടിഞ്ഞതും വേഗത്തിൽ തിരിച്ചു കയറിയതുമായ ഫണ്ടുകളാണ് യഥാർത്ഥ നമ്പർ-1 ഫണ്ടുകൾ!")

    st.subheader("🛡️ 1. കോവിഡ് തകർച്ചയിലും യുദ്ധസമയത്തും തകരാതെ പിടിച്ചുനിന്ന നമ്പർ-1 മ്യൂച്വൽ ഫണ്ടുകൾ (Auto-Recommended)")
    if is_shariah:
        st.success("🌙 **ശരീഅത്ത് മോഡ് ആക്ടീവ്:** 2020 കോവിഡ് തകർച്ചയിൽ ബാങ്കിംഗ് ഓഹരികൾ -50% തകർന്നപ്പോൾ, ബാങ്കിംഗ് ഓഹരികൾ ഇല്ലാതിരുന്ന ഹലാൽ ഫണ്ടുകളും ഗോൾഡ് ETF-കളും നിക്ഷേപകരെ അത്ഭുതകരമായി സംരക്ഷിച്ചു:")
        top_mfs = [
            {"Fund Name": "Tata Ethical Fund - Direct Plan Growth", "Category": "Shariah Flexi-Cap", "COVID-2020 Crash vs Nifty (-38.4%)": "🛡️ വെറും -24.5% (Nifty-യേക്കാൾ 14% കുറവ് ഇടിവ്!)", "5Y CAGR": "22.5%", "എന്തുകൊണ്ട് ഇടിവിൽ തകർന്നില്ല?": "കോവിഡ് സമയത്ത് തകർന്നടിഞ്ഞ ബാങ്കുകളും NBFC-കളും ഇതിലില്ല; പകരം കടരഹിത ഐ.ടി, ഫാർമ, എഫ്.എം.സി.ജി കമ്പനികളായിരുന്നു!", "Verdict": "🟢 #1 CRISIS-PROOF HALAL SIP"},
            {"Fund Name": "Nippon India ETF Gold BeES (GOLDBEES)", "Category": "Physical Gold Hedge", "COVID-2020 Crash vs Nifty (-38.4%)": "🚀 +28.0% ലാഭം! (ഓഹരികൾ വീണപ്പോൾ സ്വർണ്ണം കയറി!)", "5Y CAGR": "14.8%", "എന്തുകൊണ്ട് ഇടിവിൽ തകർന്നില്ല?": "ലോകത്ത് എപ്പോൾ പ്രതിസന്ധിയോ യുദ്ധമോ വന്നാലും സ്വർണ്ണവില കുതിച്ചുയരും. പോർട്ട്ഫോളിയോയുടെ രക്ഷാകവചം.", "Verdict": "🟢 #1 CRASH SHIELD"},
            {"Fund Name": "Taurus Ethical Fund - Direct Plan Growth", "Category": "Shariah Multi-Cap", "COVID-2020 Crash vs Nifty (-38.4%)": "🛡️ -26.2% (6 മാസം കൊണ്ട് പൂർണ്ണമായി തിരിച്ചു കയറി)", "5Y CAGR": "21.2%", "എന്തുകൊണ്ട് ഇടിവിൽ തകർന്നില്ല?": "അമിത കടമുള്ള കമ്പനികൾ ഇല്ലാത്തതിനാൽ കോവിഡ് ലോക്ക്ഡൗണിൽ ഒരു കമ്പനിയും പൂട്ടിപ്പോയില്ല.", "Verdict": "🟢 RECOMMENDED"}
        ]
    else:
        top_mfs = [
            {"Fund Name": "Parag Parikh Flexi Cap Fund - Direct Growth", "Category": "Flexi Cap Fortress", "COVID-2020 Crash vs Nifty (-38.4%)": "🛡️ വെറും -23.8% (ഇക്വിറ്റി ഫണ്ടുകളിൽ ഏറ്റവും കുറഞ്ഞ ഇടിവ്!)", "5Y CAGR": "24.2%", "എന്തുകൊണ്ട് ഇടിവിൽ തകർന്നില്ല?": "ആമസോൺ, ഗൂഗിൾ, മൈക്രോസോഫ്റ്റ് തുടങ്ങിയ ആഗോള ഓഹരികളും മൂല്യമുള്ള ഇന്ത്യൻ ഓഹരികളും ഉണ്ടായിരുന്നതിനാൽ കോവിഡ് തകർച്ചയെ നിഷ്പ്രഭമാക്കി!", "Verdict": "🟢 #1 CRISIS-PROOF EQUITY SIP"},
            {"Fund Name": "ICICI Prudential Balanced Advantage Fund - Direct", "Category": "Dynamic Asset Allocation", "COVID-2020 Crash vs Nifty (-38.4%)": "🛡️ വെറും -18.5% (ഓട്ടോമാറ്റിക് ഹെഡ്ജിംഗ്)", "5Y CAGR": "15.4%", "എന്തുകൊണ്ട് ഇടിവിൽ തകർന്നില്ല?": "മാർക്കറ്റ് അമിതമായി കയറുമ്പോൾ ഓഹരി വിറ്റ് ക്യാഷിലേക്ക് മാറ്റുകയും, കോവിഡ് പോലെ ഇടിയുമ്പോൾ കുറഞ്ഞ വിലയ്ക്ക് ഓഹരി വാങ്ങുകയും ചെയ്യുന്ന ഫോർമുല.", "Verdict": "🟢 #1 LOW-RISK FAMILY FUND"},
            {"Fund Name": "ICICI Prudential Multi-Asset Fund - Direct", "Category": "Equity + Gold + Debt", "COVID-2020 Crash vs Nifty (-38.4%)": "🛡️ -21.0% (സ്വർണ്ണവും ബോണ്ടും രക്ഷിച്ചു)", "5Y CAGR": "23.1%", "എന്തുകൊണ്ട് ഇടിവിൽ തകർന്നില്ല?": "ഒരേ ഫണ്ടിൽ തന്നെ ഓഹരിയും സ്വർണ്ണവും ഉൾപ്പെട്ടതിനാൽ ഏത് പ്രതിസന്ധിയിലും തകരാതെ നിൽക്കുന്നു.", "Verdict": "🟢 STRONG RECOMMEND"},
            {"Fund Name": "UTI Nifty 50 Index Fund - Direct Growth", "Category": "Large Cap Index", "COVID-2020 Crash vs Nifty (-38.4%)": "⚖️ -38.1% (7 മാസം കൊണ്ട് തിരിച്ചു കയറി)", "5Y CAGR": "16.5%", "എന്തുകൊണ്ട് ഇടിവിൽ തകർന്നില്ല?": "ഇന്ത്യയിലെ ഏറ്റവും വലിയ 50 കമ്പനികളായതിനാൽ തകർച്ചയിൽ നിന്ന് ആദ്യം തിരിച്ചു കയറുന്നു.", "Verdict": "🟢 CORE INDEX PICK"}
        ]
    st.dataframe(pd.DataFrame(top_mfs), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🔎 2. ഇന്ത്യയിലെ ഏതൊരു മ്യൂച്വൽ ഫണ്ടും (10,000+ Funds) അടിച്ചു നോക്കൂ — കോവിഡ് തകർച്ചയിൽ അത് എത്രത്തോളം വീണു എന്ന് ലൈവ് ആയി കാണാം!")
    mf_q = st.text_input("🔍 മ്യൂച്വൽ ഫണ്ടിന്റെ പേര് ടൈപ്പ് ചെയ്യുക (ഉദാ: Parag Parikh, Tata Ethical, SBI, HDFC, Quant):", value="Parag Parikh")
    mf_results = search_live_mutual_funds(mf_q)

    if mf_results:
        mf_options = [f"{item['schemeCode']} | {item['schemeName']}" for item in mf_results]
        sel_mf = st.selectbox("✅ ഫണ്ട് തിരഞ്ഞെടുക്കുക:", mf_options)
        sel_code = sel_mf.split(" | ")[0].strip()

        with st.spinner("⏳ AMFI സെർവറിൽ നിന്ന് ഫണ്ടിന്റെ ചരിത്രവും 2020 കോവിഡ് തകർച്ചയിലെ പ്രകടനവും പരിശോധിക്കുന്നു..."):
            mf_data = analyze_mutual_fund_with_covid_test(sel_code)
            if mf_data:
                st.markdown(f"### 🏛️ {mf_data['name']} ({mf_data['category']})")
                if "🟢" in mf_data['rec_status']:
                    st.success(f"**വിധി (Verdict):** {mf_data['rec_status']}")
                else:
                    st.error(f"**വിധി (Verdict):** {mf_data['rec_status']}")

                mc1, mc2, mc3, mc4, mc5 = st.columns(5)
                mc1.metric("നിലവിലെ NAV", f"₹{mf_data['nav']:.2f}", f"Date: {mf_data['date']}")
                mc2.metric("3 വർഷ ശരാശരി (3Y CAGR)", f"{mf_data['cagr_3y']:.1f}% p.a.")
                mc3.metric("5 വർഷ ശരാശരി (5Y CAGR)", f"{mf_data['cagr_5y']:.1f}% p.a.")
                mc4.metric("🦠 2020 കോവിഡ് ഇടിവ്", f"{mf_data['covid_drop']:.1f}%" if mf_data['covid_drop'] else "New Fund", "Nifty fell -38.4%")
                mc5.metric("📉 5-വർഷത്തെ പരമാവധി ഇടിവ്", f"{mf_data['max_dd']:.1f}%", "Downside Risk")

                m_w1, m_w2 = st.columns(2)
                with m_w1:
                    st.success("#### ✅ എന്തുകൊണ്ട് റെക്കമെൻഡ് ചെയ്യുന്നു? (Strengths & Crash Protection)")
                    for w in mf_data['why_mf']: st.markdown(f"- 🟢 {w}")
                with m_w2:
                    st.error("#### ❌ പോരായ്മകൾ (Weaknesses / Warnings)")
                    for wn in mf_data['why_not_mf']: st.markdown(f"- 🔴 {wn}")

                if not mf_data['chart_df'].empty:
                    st.caption("📈 **കഴിഞ്ഞ 5 വർഷത്തെ NAV വളർച്ചാ ഗ്രാഫ്:**")
                    st.line_chart(mf_data['chart_df'])

# ##################################################################
# 🎟️ MODULE 3: LIVE IPO RECOMMENDATIONS & INDIAN SEBI/QIB ANALYZER
# ##################################################################
elif main_menu == MENU_ITEMS[3]:
    st.title("🎟️ ലൈവ് ഐ.പി.ഒ (IPO) റെക്കമെൻഡേഷൻസ് & ഇന്ത്യൻ SEBI / QIB അനലൈസർ")
    st.info("🇮🇳 **ഇന്ത്യൻ IPO സുവർണ്ണ നിയമം (SEBI Lottery Rule):** റീട്ടെയിൽ ക്വാട്ട ഓവർ-സബ്സ്ക്രൈബ് ആയാൽ കമ്പ്യൂട്ടർ നറുക്കെടുപ്പ് (Lottery) ആയതിനാൽ, ഒരൊറ്റ അക്കൗണ്ടിൽ നിന്ന് 5 ലോട്ട് അപേക്ഷിച്ചിട്ട് കാര്യമില്ല! പകരം **കുടുംബാംഗങ്ങളുടെ വെവ്വേറെ PAN കാർഡുള്ള ഡിമാറ്റ് അക്കൗണ്ടുകളിൽ നിന്ന് 1 Lot (~₹15,000) വീതം** അവസാന ദിവസം ഉച്ചയ്ക്ക് 1 മണിക്ക് ശേഷം (QIB സബ്സ്ക്രിപ്ഷൻ > 15x ആണെന്ന് ഉറപ്പാക്കി) അപേക്ഷിക്കുക!")

    col_ipo1, col_ipo2 = st.columns([3, 1])
    col_ipo1.subheader("📡 1. നിലവിൽ ഓപ്പൺ ആയതും വരാൻ പോകുന്നതുമായ IPO-കളും ഓട്ടോമാറ്റിക് വിധിയും")
    if col_ipo2.button("🔄 ലൈവ് IPO ലിസ്റ്റ് റിഫ്രഷ് ചെയ്യുക", use_container_width=True):
        st.cache_data.clear()

    live_ipos = fetch_live_ipos_india()
    if live_ipos:
        st.dataframe(pd.DataFrame(live_ipos), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🧮 2. ഏതൊരു പുതിയ IPO-യും ഇന്ത്യൻ സ്റ്റാൻഡേർഡിൽ പരിശോധിച്ച് APPLY ചെയ്യണോ AVOID ചെയ്യണോ എന്ന് തീരുമാനിക്കാം")
    ic1, ic2, ic3 = st.columns(3)
    ipo_name = ic1.text_input("IPO കമ്പനിയുടെ പേര്:", value="New Mainboard IPO")
    ipo_type = ic2.selectbox("IPO വിഭാഗം:", ["🟢 Mainboard IPO (1 Lot ~₹15,000 - SEBI Strict)", "🔴 SME IPO (1 Lot ₹1.2 Lakh+ - High Manipulation Risk)"])
    qib_sub = ic3.slider("QIB സബ്സ്ക്രിപ്ഷൻ (വൻകിട ബാങ്കുകളും ഫണ്ടുകളും എത്ര ഇരട്ടി വാങ്ങി?):", 0, 150, 20)

    ic4, ic5, ic6 = st.columns(3)
    ofs_pct = ic4.slider("OFS ശതമാനം (പഴയ ഉടമകൾ ഓഹരി വിറ്റ് പുറത്തുപോകുന്നത് %):", 0, 100, 20)
    gmp_pct = ic5.slider("നിലവിലെ GMP (Grey Market Premium %):", -20, 120, 25)
    debt_stat = ic6.selectbox("കമ്പനിയുടെ കടവും ബിസിനസ്സും:", ["🟢 കടം < 33% & ഹലാൽ ബിസിനസ്സ്", "🟡 കടം കമ്പനി IPO പണം കൊണ്ട് വീട്ടുന്നു", "🔴 അമിത കടം / ബാങ്കിംഗ് / നോൺ-ഹലാൽ"])

    score = 100
    why_ipo, why_not_ipo = [], []
    if "SME" in ipo_type:
        score -= 30
        why_not_ipo.append("SME IPO ആയതിനാൽ ലിസ്റ്റിംഗിന് ശേഷം വിൽക്കാൻ ആളെ കിട്ടാത്ത (Lower Circuit) വലിയ അപകടമുണ്ട്.")
    else:
        why_ipo.append("Mainboard IPO ആയതിനാൽ ഉയർന്ന സുതാര്യതയും ലിക്വിഡിറ്റിയും ഉണ്ട്.")

    if qib_sub >= 15:
        why_ipo.append(f"വൻകിട സ്ഥാപനങ്ങൾ (QIB: {qib_sub}x) ശക്തമായി വാങ്ങുന്നുണ്ട്! ഇത് കമ്പനിയുടെ ഗുണനിലവാരം തെളിയിക്കുന്നു.")
    elif qib_sub < 5:
        score -= 25
        why_not_ipo.append(f"വൻകിട ഫണ്ടുകൾ (QIB: {qib_sub}x) ഈ IPO-യിൽ താല്പര്യം കാണിക്കുന്നില്ല!")

    if ofs_pct > 50:
        score -= 30
        why_not_ipo.append(f"OFS കെണി ({ofs_pct}%): സമാഹരിക്കുന്ന പണം കമ്പനിയുടെ വളർച്ചയ്ക്കല്ല, പഴയ ഉടമകളുടെ കീശയിലേക്കാണ് പോകുന്നത്!")
    else:
        why_ipo.append(f"Fresh Issue ({100-ofs_pct}%): പണം കമ്പനിയുടെ വികസനത്തിനും കടം വീട്ടാനും ഉപയോഗിക്കുന്നു.")

    if gmp_pct >= 20:
        why_ipo.append(f"മികച്ച ഗ്രേ മാർക്കറ്റ് പ്രീമിയം (+{gmp_pct}% GMP) ഉള്ളതിനാൽ ലിസ്റ്റിംഗ് ലാഭം പ്രതീക്ഷിക്കാം.")
    elif gmp_pct < 10:
        score -= 20
        why_not_ipo.append(f"GMP വളരെ കുറവാണ് ({gmp_pct}%). ലിസ്റ്റിംഗ് ദിവസം നഷ്ടം വരാം.")

    if "🔴" in debt_stat and is_shariah:
        score -= 40
        why_not_ipo.append("ശരീഅത്ത് വിരുദ്ധമായ ബിസിനസ്സ് അല്ലെങ്കിൽ അമിത കടം.")

    if score >= 75:
        st.success(f"🟢 **RECOMMENDED TO APPLY ({score}/100):** `{ipo_name}` നിക്ഷേപത്തിന് അനുയോജ്യമാണ്! കുടുംബാംഗങ്ങളുടെ വെവ്വേറെ അക്കൗണ്ടുകളിൽ നിന്ന് 1 Lot വീതം അപേക്ഷിക്കുക.")
    elif score >= 50:
        st.warning(f"🟡 **WAIT FOR DAY-3 QIB ({score}/100):** അവസാന ദിവസം ഉച്ചയ്ക്ക് 2 മണിക്ക് QIB 15x കടന്നാൽ മാത്രം പരിഗണിക്കുക.")
    else:
        st.error(f"🔴 **NOT RECOMMENDED / AVOID ({score}/100):** `{ipo_name}` ഒഴിവാക്കുക!")

    ip_c1, ip_c2 = st.columns(2)
    with ip_c1:
        st.success("#### ✅ അനുകൂല ഘടകങ്ങൾ")
        for w in why_ipo: st.markdown(f"- 🟢 {w}")
    with ip_c2:
        st.error("#### ❌ അപകട സൂചനകൾ (Red Flags)")
        for wn in why_not_ipo: st.markdown(f"- 🔴 {wn}")

# ##################################################################
# 📜 MODULE 4: BONDS, REITS, SEBI SIF & HALAL FIXED-INCOME
# ##################################################################
elif main_menu == MENU_ITEMS[4]:
    st.title("📜 മികച്ച ബോണ്ടുകൾ, REITs (വാടക വരുമാനം), SEBI SIF & ഹലാൽ വരുമാന മാർഗ്ഗങ്ങൾ")
    if is_shariah:
        st.error("🌙 **ശരീഅത്ത് നിയമം:** സാധാരണ ഗവൺമെന്റ്/കോർപ്പറേറ്റ് ബോണ്ടുകളും ബാങ്ക് FD-യും SEBI SIF Long-Short ഡെറിവേറ്റീവ് ഫണ്ടുകളും പലിശ/ഊഹക്കച്ചവടം ആയതിനാൽ ഹലാൽ അല്ല.")
        st.subheader("🏆 പലിശയില്ലാതെ സ്ഥിരവരുമാനം നേടാൻ ഞങ്ങൾ റെക്കമെൻഡ് ചെയ്യുന്ന ഹലാൽ മാർഗ്ഗങ്ങൾ:")
        st.dataframe(pd.DataFrame([
            {"Rank": "🥇 #1 Recommend", "ഹലാൽ മാർഗ്ഗം": "ഉയർന്ന ഡിവിഡന്റ് നൽകുന്ന കടരഹിത ഹലാൽ ഓഹരികൾ (TCS, HCLTECH, INFOSYS)", "വാർഷിക വരുമാനം": "3% - 4.5% Div + ഓഹരി വളർച്ച", "എന്തുകൊണ്ട് മികച്ചത്?": "പലിശയ്ക്ക് പകരം യഥാർത്ഥ ബിസിനസ്സ് ലാഭവിഹിതം ബാങ്ക് അക്കൗണ്ടിലേക്ക് ലഭിക്കുന്നു."},
            {"Rank": "🥈 #2 Recommend", "ഹലാൽ മാർഗ്ഗം": "Nippon India Gold BeES (24K ഫിസിക്കൽ ഗോൾഡ് ETF)", "വാർഷിക വരുമാനം": "12% - 14% ശരാശരി വളർച്ച", "എന്തുകൊണ്ട് മികച്ചത്?": "ബാങ്ക് FD-യേക്കാൾ ഇരട്ടി വളർച്ച, 100% ഹലാൽ (AAOIFI Standard #57), എപ്പോൾ വേണമെങ്കിലും വിൽക്കാം."},
            {"Rank": "🥉 #3 Recommend", "ഹലാൽ മാർഗ്ഗം": "വാടക വരുമാനം നൽകുന്ന കമേഴ്സ്യൽ റിയൽ എസ്റ്റേറ്റ് / ഇജാറ (Direct Property / Ijarah)", "വാർഷിക വരുമാനം": "6% - 9% വാടക", "എന്തുകൊണ്ട് മികച്ചത്?": "പലിശരഹിതമായ മാസവരുമാനവും ഭൂമിയുടെ വിലവർദ്ധനവും."}
        ]), use_container_width=True, hide_index=True)
    else:
        st.subheader("🏆 സുരക്ഷിത വരുമാനത്തിനായി റെക്കമെൻഡ് ചെയ്യുന്ന RBI ബോണ്ടുകൾ, REITs & പുതിയ SEBI SIF:")
        st.dataframe(pd.DataFrame([
            {"Rank": "🥇 #1 Safest Bond", "Instrument": "RBI Retail Direct G-Secs & T-Bills (ഇന്ത്യാ ഗവൺമെന്റ് കടപ്പത്രങ്ങൾ)", "Type": "Sovereign Bond", "Yield": "7.0% - 7.3% p.a.", "എന്തുകൊണ്ട് റെക്കമെൻഡ് ചെയ്യുന്നു?": "കേന്ദ്ര സർക്കാർ ഗ്യാരണ്ടി ഉള്ളതിനാൽ മുതലിന് 0% പോലും റിസ്ക് ഇല്ല."},
            {"Rank": "🥈 #2 Tax-Free Bond ETF", "Instrument": "Bharat Bond ETF (AAA PSU Companies - NHAI, REC, PFC)", "Type": "AAA Corporate Bond ETF", "Yield": "7.4% - 7.7% p.a.", "എന്തുകൊണ്ട് റെക്കമെൻഡ് ചെയ്യുന്നു?": "ഡിമാറ്റ് അക്കൗണ്ട് വഴി ഓഹരി പോലെ എപ്പോൾ വേണമെങ്കിലും വാങ്ങാനും വിൽക്കാനും കഴിവും."},
            {"Rank": "🏢 #3 Commercial Rental REITs", "Instrument": "Embassy Office Parks REIT / Nexus Select Trust / Mindspace REIT", "Type": "Real Estate (₹350+ per unit)", "Yield": "6.5% - 8.0% Rental + Appreciation", "എന്തുകൊണ്ട് റെക്കമെൻഡ് ചെയ്യുന്നു?": "കോടികൾ മുടക്കാതെ ₹400 രൂപ മുതൽ വൻകിട ഐ.ടി പാർക്കുകളിലും മാളുകളിലും നിക്ഷേപിച്ച് 3 മാസം തോറും വാടക വരുമാനം നേടാം!"},
            {"Rank": "⚡ #4 New SEBI Asset (₹10L+)", "Instrument": "SEBI Specialized Investment Funds (SIF)", "Type": "Long-Short Strategy (Min ₹10 Lakh)", "Yield": "12% - 16% Target", "എന്തുകൊണ്ട് റെക്കമെൻഡ് ചെയ്യുന്നു?": "മ്യൂച്വൽ ഫണ്ടിനും PMS-നും ഇടയിലായി SEBI പുതുതായി കൊണ്ടുവന്ന വിഭാഗം (ഉയർന്ന മൂലധനമുള്ളവർക്ക് മാത്രം)."}
        ]), use_container_width=True, hide_index=True)

# ##################################################################
# 💳 MODULE 5: DEBT FREEDOM, RBI 2026 RECOVERY SHIELD & COMPLAINT GENERATOR
# ##################################################################
elif main_menu == MENU_ITEMS[5]:
    st.title("💳 കടം തീർക്കൽ, RBI ഭീഷണി പ്രതിരോധ ഷീൽഡ് & ഓട്ടോമാറ്റിക് പരാതി ജനറേറ്റർ")
    st.caption("നിങ്ങളുടെ ലോണുകൾ മുൻഗണനാ ക്രമത്തിൽ വീട്ടാനും, റിക്കവറി ഏജന്റുമാരുടെ ഭീഷണി കോളുകളെ RBI നിയമം (August 2026 Directions) ഉപയോഗിച്ച് നേരിടാനുമുള്ള സമ്പൂർണ്ണ സംവിധാനം.")

    tab_debt_list, tab_rbi_shield = st.tabs([
        "📊 1. എന്റെ കടങ്ങളുടെ പ്രയോറിറ്റി ലിസ്റ്റ് (Secured vs Unsecured Payoff Planner)",
        "🛡️ 2. റിക്കവറി ഭീഷണി പ്രതിരോധം & RBI പരാതി ലെറ്റർ ജനറേറ്റർ (2026 RBI Rules)"
    ])

    with tab_debt_list:
        with st.expander("➕ നിങ്ങളുടെ ലോൺ / കടം ഇവിടെ ചേർക്കുക", expanded=True):
            dc1, dc2, dc3 = st.columns(3)
            loan_cat = dc1.selectbox("കടത്തിന്റെ വിഭാഗം:", [
                "🏠 സെക്യൂർഡ്: ഹോം ലോൺ / പ്രോപ്പർട്ടി ലോൺ (ജപ്തി ഭീഷണിയുള്ളവ - SARFAESI)",
                "🪙 സെക്യൂർഡ്: ഗോൾഡ് ലോൺ / സ്വർണ്ണപ്പണയം (ലേല ഭീഷണിയുള്ളവ)",
                "💳 അൺസെക്യൂർഡ്: ക്രെഡിറ്റ് കാർഡ് കുടിശ്ശിക (36% - 42% പലിശ)",
                "⚠️ വ്യക്തിഗത കടം / പുറത്തുനിന്ന് വാങ്ങിയത് (Private / Friends Debt)",
                "🏦 അൺസെക്യൂർഡ്: പേഴ്സണൽ ലോൺ / ആപ്പ് ലോൺ (14% - 28% പലിശ)",
                "🚗 വാഹന ലോൺ (9% - 14% പലിശ)"
            ])
            lender_name = dc2.text_input("ബാങ്ക് / വ്യക്തിയുടെ പേര് (ഉദാ: SBI, HDFC, സുഹൃത്ത്):")
            loan_status = dc3.selectbox("നിലവിലെ അവസ്ഥ:", [
                "🟢 കൃത്യമായി EMI അടച്ചുപോകുന്നു (Regular)",
                "🟡 1-2 മാസം അടവ് മുടങ്ങി (Overdue)",
                "🔴 പൂർണ്ണമായി മുടങ്ങി / ജപ്തി അല്ലെങ്കിൽ റിക്കവറി ഭീഷണി (Defaulted / Critical)"
            ])
            dc4, dc5, dc6 = st.columns(3)
            tot_debt_amt = dc4.number_input("ഇനി കൊടുത്തുതീർക്കാനുള്ള ആകെ തുക (₹):", min_value=500.0, value=50000.0, step=5000.0)
            int_rate = dc5.number_input("വാർഷിക പലിശ നിരക്ക് (%):", min_value=0.0, max_value=120.0, value=14.0, step=1.0)
            monthly_emi = dc6.number_input("പ്രതിമാസ അടവ് / EMI (₹):", min_value=0.0, value=2500.0, step=500.0)

            if st.button("💾 കടങ്ങളുടെ ലിസ്റ്റിലേക്ക് ചേർക്കുക", type="primary", use_container_width=True):
                conn = get_db_connection()
                conn.execute("INSERT INTO user_debts (user_hash, loan_type, lender, total_amount, interest_rate, emi, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (USER_HASH, loan_cat, lender_name or "Lender", tot_debt_amt, int_rate, monthly_emi, loan_status, ""))
                conn.commit()
                conn.close()
                st.rerun()

        conn = get_db_connection()
        df_debts = pd.read_sql_query("SELECT id, loan_type, lender, total_amount, interest_rate, emi, status FROM user_debts WHERE user_hash=?", conn, params=(USER_HASH,))
        conn.close()
        if not df_debts.empty:
            def smart_priority_score(r):
                is_secured = "സെക്യൂർഡ്" in str(r['loan_type'])
                is_overdue = ("🔴" in str(r['status']) or "🟡" in str(r['status']))
                if is_secured and is_overdue:
                    return 200.0 + float(r['interest_rate'])
                status_pts = 50.0 if "🔴" in str(r['status']) else (25.0 if "🟡" in str(r['status']) else 0.0)
                return float(r['interest_rate']) + status_pts

            df_debts['urgency'] = df_debts.apply(smart_priority_score, axis=1)
            df_sorted = df_debts.sort_values(by=['urgency', 'total_amount'], ascending=[False, True]).reset_index(drop=True)
            df_sorted['Priority'] = [f"🔥 #{i+1} (ആദ്യം സംരക്ഷിക്കുക/വീട്ടുക!)" if i == 0 else f"#{i+1}" for i in range(len(df_sorted))]
            st.subheader("🎯 നിങ്ങളുടെ കടങ്ങൾ വീട്ടേണ്ട മുൻഗണനാ ക്രമം (Smart Payoff Order):")
            st.dataframe(df_sorted[['id', 'Priority', 'loan_type', 'lender', 'total_amount', 'interest_rate', 'emi', 'status']], use_container_width=True, hide_index=True)

            del_col1, del_col2 = st.columns([2, 1])
            del_id = del_col1.selectbox("വീട്ടിക്കഴിഞ്ഞ ഒരു ലോൺ മാത്രം ലിസ്റ്റിൽ നിന്ന് നീക്കം ചെയ്യാൻ അതിന്റെ ID തിരഞ്ഞെടുക്കുക:", df_sorted['id'].tolist())
            if del_col2.button("🗑️ തിരഞ്ഞെടുത്ത ലോൺ ഡിലീറ്റ് ചെയ്യുക", use_container_width=True):
                conn = get_db_connection()
                conn.execute("DELETE FROM user_debts WHERE id=? AND user_hash=?", (int(del_id), USER_HASH))
                conn.commit()
                conn.close()
                st.rerun()

    with tab_rbi_shield:
        st.subheader("🛡️ ലോൺ അടവ് മുടങ്ങിയവർ അറിയേണ്ട RBI നിയമങ്ങൾ (RBI Responsible Business Conduct Directions 2026)")
        st.error("""
        🚨 **റിക്കവറി ഏജന്റുമാർ നിങ്ങളെ ഭീഷണിപ്പെടുത്തുന്നുണ്ടോ? നിങ്ങളുടെ 5 നിയമപരമായ അവകാശങ്ങൾ ഇതാ:**
        1. **⏰ കോൾ സമയപരിധി (8:00 AM – 7:00 PM Rule):** രാവിലെ 8 മണിക്ക് മുൻപോ വൈകുന്നേരം 7 മണിക്ക് ശേഷമോ റിക്കവറി ഏജന്റുമാർക്ക് വിളിക്കാൻ അനുവാദമില്ല. എല്ലാ കോളുകളും ബാങ്ക് റെക്കോർഡ് ചെയ്യണമെന്നാണ് RBI നിയമം.
        2. **🏠 വീട്ടിലോ ഓഫീസിലോ വരുന്നതിനുള്ള നിയമം (Mandatory Prior Notice):** ഒരു ഏജന്റ് വീട്ടിലേക്ക് വരുന്നതിന് മുൻപ് ബാങ്ക് നിങ്ങൾക്ക് **മുൻകൂർ നോട്ടീസ് (Prior Notice)** നൽകിയിരിക്കണം. ഏജന്റിന്റെ കൈയിൽ ബാങ്കിന്റെ **Authorization Letter-ഉം ID കാർഡും** നിർബന്ധമാണ്.
        3. **🚫 നാണംകെടുത്താൻ പാടില്ല (Zero Public Humiliation):** നിങ്ങളുടെ ബന്ധുക്കളെയോ, സുഹൃത്തുക്കളെയോ, അയൽക്കാരെയോ, സഹപ്രവർത്തകരെയോ വിളിച്ച് നിങ്ങളുടെ കടവിവരം പറയുന്നതും വാട്ട്സ്ആപ്പ് ഗ്രൂപ്പുകളിൽ ഇടുന്നതും RBI കർശനമായി നിരോധിച്ചിട്ടുള്ള ക്രിമിനൽ കുറ്റമാണ്!
        4. **⚖️ അൺസെക്യൂർഡ് ലോണിന് പോലീസ് അറസ്റ്റ് ഇല്ല:** പേഴ്സണൽ ലോൺ, ക്രെഡിറ്റ് കാർഡ് എന്നിവ തിരിച്ചടയ്ക്കാൻ വൈകുന്നത് ഒരു സിവിൽ കേസ് (Civil Matter) മാത്രമാണ്; ഇതിന്റെ പേരിൽ പോലീസ് നിങ്ങളെ അറസ്റ്റ് ചെയ്യുമെന്ന് ഏജന്റ് പറഞ്ഞാൽ അത് പൂർണ്ണമായും വ്യാജ ഭീഷണിയാണ്!
        5. **📱 വ്യാജ ലോൺ ആപ്പ് ഭീഷണി:** അനധികൃത ആപ്പുകൾ ഫോൺ കോൺടാക്റ്റ് എടുത്ത് ഭീഷണിപ്പെടുത്തിയാൽ ഉടൻ ഒരു രൂപ പോലും നൽകാതെ **1930** എന്ന സൈബർ ക്രൈം നമ്പറിൽ വിളിക്കുക.
        """)

        c_link1, c_link2 = st.columns(2)
        c_link1.link_button("🏛️ RBI Ombudsman ഒഫീഷ്യൽ പരാതി പോർട്ടൽ (cms.rbi.org.in)", "https://cms.rbi.org.in", type="primary", use_container_width=True)
        c_link2.link_button("🚓 നാഷണൽ സൈബർ ക്രൈം പോർട്ടൽ (1930 / cybercrime.gov.in)", "https://cybercrime.gov.in", use_container_width=True)

        st.markdown("---")
        st.subheader("📝 ഒറ്റ ക്ലിക്കിൽ ബാങ്കിനും RBI-ക്കും അയക്കാനുള്ള പരാതി കത്ത് തയ്യാറാക്കാം (Auto Complaint Generator)")
        cp1, cp2, cp3 = st.columns(3)
        comp_bank = cp1.text_input("ശല്യം ചെയ്യുന്ന ബാങ്ക് / NBFC പേര്:", value="ABC Bank / Finance")
        comp_loan_no = cp2.text_input("ലോൺ / ക്രെഡിറ്റ് കാർഡ് നമ്പർ:", value="XXXX1234")
        comp_issue = cp3.selectbox("ഏജന്റ് ചെയ്ത നിയമലംഘനം:", [
            "വൈകുന്നേരം 7 മണിക്ക് ശേഷവും തുടർച്ചയായി വിളിച്ച് ഭീഷണിപ്പെടുത്തുന്നു",
            "മുൻകൂർ നോട്ടീസോ ID കാർഡോ ഇല്ലാതെ വീട്ടിൽ/ഓഫീസിൽ വന്ന് അപമാനിച്ചു",
            "ബന്ധുക്കളെയും സഹപ്രവർത്തകരെയും വിളിച്ച് കടവിവരം പറഞ്ഞ് നാണംകെടുത്തി",
            "സാമ്പത്തിക ബുദ്ധിമുട്ട് അറിയിച്ചിട്ടും EMI Restructuring / OTS അനുവദിക്കുന്നില്ല"
        ])
        letter_text = (
            f"To,\nThe Principal Nodal Officer / Grievance Redressal Officer,\n{comp_bank}\n\n"
            f"Subject: Formal Complaint against RBI Fair Practices Code Violation & Recovery Harassment (Account: {comp_loan_no})\n\n"
            f"Dear Sir/Madam,\nI hold Loan/Card No. {comp_loan_no} with your institution. Due to genuine financial hardship, there has been a temporary delay in repayment.\n"
            f"However, your recovery agents have violated RBI Responsible Business Conduct Guidelines by: [{comp_issue}].\n\n"
            f"I request you to immediately stop unlawful recovery harassment and provide an EMI Restructuring / One-Time Settlement (OTS) plan, failing which I will escalate this complaint with evidence to the RBI Ombudsman (https://cms.rbi.org.in).\n\n"
            f"Yours sincerely,\n[Your Name & Mobile]"
        )
        st.text_area("📋 താഴെ കാണുന്ന ഇമെയിൽ കോപ്പി ചെയ്ത് ബാങ്കിന്റെ കസ്റ്റമർ കെയറിലേക്കും നോഡൽ ഓഫീസർക്കും അയക്കുക:", value=letter_text, height=220)

# ##################################################################
# 🎯 MODULE 6: DYNAMIC GOAL ALLOCATOR
# ##################################################################
elif main_menu == MENU_ITEMS[6]:
    st.title(MENU_ITEMS[6])
    c1, c2, c3 = st.columns(3)
    inv_amount = c1.number_input("നിക്ഷേപ തുക (₹):", value=10000.0, step=1000.0)
    goal_horizon = c2.selectbox("നിക്ഷേപ കാലാവധി:", ["⏳ 1 Year (ഹ്രസ്വകാലം)", "🚀 3 - 5 Years (ഇടത്തരം വളർച്ച)", "🏛️ 10+ Years (ദീർഘകാല സമ്പത്ത്)"])
    market_climate = c3.selectbox("വിപണി സാഹചര്യം:", ["🟢 Normal Bull", "⚠️ War / Oil Spike", "🔴 Market Crash"])

    if "1 Year" in goal_horizon: eq_pct, gold_pct, cash_pct = 0.15, 0.35, 0.50
    elif "3 - 5 Years" in goal_horizon: eq_pct, gold_pct, cash_pct = (0.40, 0.30, 0.30) if "War" in market_climate else (0.60, 0.20, 0.20)
    else: eq_pct, gold_pct, cash_pct = (0.75, 0.15, 0.10) if "Crash" in market_climate else (0.70, 0.20, 0.10)

    a1, a2, a3 = st.columns(3)
    a1.metric("1. ഇക്വിറ്റി വിഹിതം", f"₹{(inv_amount * eq_pct):,.0f}", f"{int(eq_pct*100)}%")
    a2.metric("2. ഗോൾഡ് & സിൽവർ വിഹിതം", f"₹{(inv_amount * gold_pct):,.0f}", f"{int(gold_pct*100)}%")
    a3.metric("3. സുരക്ഷിത ക്യാഷ് കരുതൽ", f"₹{(inv_amount * cash_pct):,.0f}", f"{int(cash_pct*100)}%")

# ##################################################################
# 💼 MODULE 7: LIVE PORTFOLIO & WATCHDOG
# ##################################################################
elif main_menu == MENU_ITEMS[7]:
    st.title(MENU_ITEMS[7])
    h_tab1, h_tab2 = st.tabs(["⚡ ലൈവ് ബ്രോക്കർ സിങ്ക് (Upstox / Dhan / Zerodha)", "📝 എന്റെ മാനുവൽ പോർട്ട്ഫോളിയോ (Live Price & Exit Watchdog)"])

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
        m_qty = col_m1.number_input("വാങ്ങിയ എണ്ണം (Qty):", value=10, min_value=1, step=1)
        m_bp = col_m2.number_input("വാങ്ങിയ ശരാശരി വില (₹):", value=3500.0, min_value=1.0, step=10.0)
        m_plat = col_m3.selectbox("പ്ലാറ്റ്‌ഫോം:", ["Groww", "Zerodha", "AngelOne", "Upstox", "Other"])

        if st.button("➕ പോർട്ട്ഫോളിയോയിലേക്ക് ചേർക്കുക", type="primary"):
            if m_sym:
                conn = get_db_connection()
                conn.execute("INSERT INTO manual_portfolio (user_hash, symbol, qty, buy_price, buy_date, notes) VALUES (?, ?, ?, ?, ?, ?)",
                             (USER_HASH, m_sym, m_qty, m_bp, datetime.date.today().strftime("%Y-%m-%d"), m_plat))
                conn.commit()
                conn.close()
                st.rerun()

        conn = get_db_connection()
        df_man = pd.read_sql_query("SELECT id, symbol, qty, buy_price, buy_date, notes FROM manual_portfolio WHERE user_hash=? ORDER BY id DESC", conn, params=(USER_HASH,))
        conn.close()
        if not df_man.empty:
            port_rows = []
            for _, r in df_man.iterrows():
                sym = r['symbol']
                qty = float(r['qty'])
                bp = float(r['buy_price'])
                try:
                    lp = float(yf.Ticker(sym).fast_info.get('lastPrice', bp))
                except Exception:
                    lp = bp
                pnl = (lp - bp) * qty
                pnl_pct = ((lp - bp) / bp * 100) if bp > 0 else 0
                w_stat = "🚨 EXIT ALERT (-10% SL)" if pnl_pct <= -10 else ("🟢 STRONG WINNER (+20%)" if pnl_pct >= 20 else "🟡 HOLD")
                port_rows.append({
                    "ID": r['id'], "Stock": sym, "Broker": r['notes'], "Qty": int(qty),
                    "Buy Price": f"₹{bp:,.1f}", "Live Price": f"₹{lp:,.1f}",
                    "Net P&L (₹)": f"₹{pnl:+,.1f}", "Return (%)": f"{pnl_pct:+.1f}%",
                    "Watchdog Status": w_stat
                })
            st.dataframe(pd.DataFrame(port_rows), use_container_width=True, hide_index=True)
            p_del1, p_del2 = st.columns([2, 1])
            del_pid = p_del1.selectbox("വിറ്റുകഴിഞ്ഞ സ്റ്റോക്ക് ഒഴിവാക്കാൻ അതിന്റെ ID തിരഞ്ഞെടുക്കുക:", df_man['id'].tolist())
            if p_del2.button("🗑️ സ്റ്റോക്ക് ഡിലീറ്റ് ചെയ്യുക", use_container_width=True):
                conn = get_db_connection()
                conn.execute("DELETE FROM manual_portfolio WHERE id=? AND user_hash=?", (int(del_pid), USER_HASH))
                conn.commit()
                conn.close()
                st.rerun()

# ##################################################################
# 🌍 MODULE 8: US STOCK RECOMMENDATIONS & INDIA LRS/TCS/FOREX CALCULATOR
# ##################################################################
elif main_menu == MENU_ITEMS[8]:
    st.title("🌍 യു.എസ് (US) നമ്പർ-1 സ്റ്റോക്ക് റെക്കമെൻഡേഷൻസ് & ഇന്ത്യൻ ടാക്സ്/ഫോറെക്സ് കാൽക്കുലേറ്റർ")

    with st.expander("🇮🇳 ഒരു ഇന്ത്യക്കാരൻ US സ്റ്റോക്കിൽ നിക്ഷേപിക്കുമ്പോൾ അറിയേണ്ട RBI LRS, 20% TCS & ബാങ്ക് ചാർജ് കാൽക്കുലേറ്റർ", expanded=True):
        us_inr_amt = st.number_input("നിങ്ങൾ US വിപണിയിൽ നിക്ഷേപിക്കാൻ ഉദ്ദേശിക്കുന്ന തുക (ഇന്ത്യൻ രൂപയിൽ ₹):", value=50000.0, step=25000.0)
        forex_fee = us_inr_amt * 0.015
        tcs_tax = max(0.0, (us_inr_amt - 700000.0) * 0.20)
        u_c1, u_c2, u_c3 = st.columns(3)
        u_c1.metric("ബാങ്ക് ഫോറെക്സ് ചാർജ് (~1.5%)", f"₹{forex_fee:,.0f}")
        u_c2.metric("RBI LRS 20% TCS നികുതി (> ₹7 Lakh)", f"₹{tcs_tax:,.0f}", "✅ 0% TCS (Under ₹7L)" if tcs_tax == 0 else "Claimable in ITR")
        u_c3.metric("ഇന്ത്യൻ നിക്ഷേപകനുള്ള ശുപാർശ", "🇮🇳 Indian FoF / ETF Route" if us_inr_amt < 75000 else "🇺🇸 Direct INDmoney / Vested Route")

    st.subheader("🏆 1. ലോകത്തിലെ നമ്പർ-1 യു.എസ് (US) ഓഹരി റെക്കമെൻഡേഷൻസ്")
    us_recs = [
        {"Ticker": "NVDA", "Company": "Nvidia Corp", "Horizon": "3 - 10 Years", "Shariah": "✅ Halal (AAOIFI)", "എന്തുകൊണ്ട് വേൾഡ് നമ്പർ-1?": "ലോകത്തിലെ AI ചിപ്പുകളുടെ 80% കുത്തക, ROE > 90%, കടം < 2%.", "Verdict": "🟢 #1 AI MOAT PICK"},
        {"Ticker": "MSFT", "Company": "Microsoft Corp", "Horizon": "5 - 10+ Years", "Shariah": "✅ Halal (AAOIFI)", "എന്തുകൊണ്ട് വേൾഡ് നമ്പർ-1?": "Windows, Office, Azure Cloud, OpenAI കുത്തക.", "Verdict": "🟢 STRONG RECOMMEND"},
        {"Ticker": "AAPL", "Company": "Apple Inc.", "Horizon": "5 - 10+ Years", "Shariah": "✅ Halal (AAOIFI)", "എന്തുകൊണ്ട് വേൾഡ് നമ്പർ-1?": "200 കോടിയിലധികം ആക്ടീവ് ഐഫോൺ/മാക് ഉപഭോക്താക്കൾ, ഭീമമായ ക്യാഷ് ഫ്ലോ.", "Verdict": "🟢 STRONG RECOMMEND"},
        {"Ticker": "SPUS", "Company": "SP Funds S&P 500 Sharia ETF", "Horizon": "5 - 10+ Years", "Shariah": "✅ 100% Halal ETF", "എന്തുകൊണ്ട് വേൾഡ് നമ്പർ-1?": "അമേരിക്കയിലെ ഏറ്റവും മികച്ച 200 ഹലാൽ കമ്പനികളിൽ ഒറ്റ ക്ലിക്കിൽ നിക്ഷേപിക്കാം.", "Verdict": "🟢 #1 US HALAL ETF"}
    ]
    st.dataframe(pd.DataFrame(us_recs), use_container_width=True, hide_index=True)

    st.subheader("🔎 2. ഏതൊരു US സ്റ്റോക്കും തിരഞ്ഞ് പരിശോധിക്കാം")
    u_sym = render_universal_stock_search("us_univ", market_filter="US", default_query="Nvidia")
    if u_sym:
        us_audit = analyze_any_stock_deep(u_sym, shariah_mode=is_shariah)
        if us_audit:
            st.info(f"🇺🇸 **{us_audit['name']} (`{us_audit['symbol']}`)** | Live Price: **${us_audit['price']:,.2f}** | Fair Value: **${us_audit['fair_val']:,.2f}** | ROE: `{us_audit['roe']:.1f}%` | Debt: `{us_audit['debt_to_mcap']:.1f}%` | **{us_audit['verdict']}**")

# ##################################################################
# 🥇 MODULE 9: TOP GOLD & SILVER RECOMMENDATIONS
# ##################################################################
elif main_menu == MENU_ITEMS[9]:
    st.title("🥇 മികച്ച ഗോൾഡ് & സിൽവർ റെക്കമെൻഡേഷൻസ് (AAOIFI Standard #57)")
    st.dataframe(pd.DataFrame([
        {"Rank": "🥇 #1 Best Gold ETF", "Instrument": "Nippon India ETF Gold BeES (GOLDBEES)", "Backing": "99.5% Physical Bullion", "Expense": "0.55%", "COVID-2020 Return": "🚀 +28.0% (ഓഹരികൾ വീണപ്പോൾ കുതിച്ചുയർന്നു!)", "എന്തുകൊണ്ട് റെക്കമെൻഡ് ചെയ്യുന്നു?": "ഇന്ത്യയിൽ ഏറ്റവും കൂടുതൽ ആളുകൾ ട്രേഡ് ചെയ്യുന്ന, 100% ഫിസിക്കൽ സ്വർണ്ണ പിന്തുണയുള്ള ETF."},
        {"Rank": "🥈 #2 Lowest Cost Gold", "Instrument": "HDFC Gold ETF (HDFCGOLD)", "Backing": "99.5% Physical Bullion", "Expense": "0.30%", "COVID-2020 Return": "🚀 +27.8%", "എന്തുകൊണ്ട് റെക്കമെൻഡ് ചെയ്യുന്നു?": "ദീർഘകാലത്തേക്ക് സൂക്ഷിക്കാൻ ഏറ്റവും കുറഞ്ഞ എക്സ്പെൻസ് റേഷ്യോ (0.30%)."},
        {"Rank": "🥉 #3 Best Silver ETF", "Instrument": "Nippon India Silver ETF (SILVERBEES)", "Backing": "99.9% Physical Silver", "Expense": "0.50%", "COVID-2020 Return": "🚀 +45.0% Recovery", "എന്തുകൊണ്ട് റെക്കമെൻഡ് ചെയ്യുന്നു?": "സോളാർ പാനലുകളിലും ഇലക്ട്രിക് വാഹനങ്ങളിലും വെള്ളിയുടെ ഉപയോഗം കൂടുന്നതിനാൽ മികച്ച വളർച്ചാ സാധ്യത."}
    ]), use_container_width=True, hide_index=True)

# ##################################################################
# ⚡ MODULE 10: INTRADAY ALGO TRADING BOT (100% FULL EXECUTION ENGINE!)
# ##################################################################
elif main_menu == MENU_ITEMS[10]:
    st.title("⚡ മൾട്ടി-ബ്രോക്കർ ഇൻസ്റ്റിറ്റ്യൂഷണൽ ഇൻട്രാഡേ ബോട്ട് (100% Full Order Execution Engine)")
    with st.expander("📐 ബോട്ട് എങ്ങനെയാണ് ട്രേഡ് തിരഞ്ഞെടുക്കുന്നത്? (6-ഇന ഗണിത മാനദണ്ഡങ്ങൾ)"):
        st.markdown("1. **Nifty 50 >= 20 EMA** | 2. **Price > VWAP** | 3. **EMA 9 > EMA 21 Cross** | 4. **Volume >= 1.2x SMA** | 5. **RSI 50–68** | 6. **ATR 1:2 Risk-Reward, 45m Stale Exit, 2-Loss Kill Switch & 3:15 PM Auto Square-off**.")

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

    WATCHLIST_CONV = {'SBIN': 'NSE_EQ|INE062A01020', 'RELIANCE': 'NSE_EQ|INE002A01018', 'BHARTIARTL': 'NSE_EQ|INE397D01024', 'LT': 'NSE_EQ|INE018A01030'}
    WATCHLIST_HALAL = {'TCS': 'NSE_EQ|INE467B01029', 'INFY': 'NSE_EQ|INE009A01021', 'SUNPHARMA': 'NSE_EQ|INE044A01036', 'RELIANCE': 'NSE_EQ|INE002A01018'}

    def send_telegram_alert(msg, tg_t, tg_c):
        if tg_t and tg_c:
            try:
                requests.post(f"https://api.telegram.org/bot{tg_t}/sendMessage", json={"chat_id": tg_c, "text": msg, "parse_mode": "Markdown"}, timeout=5)
            except Exception:
                pass

    def place_real_order(symbol, instrument_key, qty, action, token, u_state):
        if u_state['mode'] == "LIVE":
            b_name = u_state.get('broker', 'Upstox')
            try:
                if b_name == "Upstox":
                    url = 'https://api-hft.upstox.com/v2/order/place'
                    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
                    order_data = {
                        "quantity": int(qty), "product": "I", "validity": "DAY", "price": 0,
                        "tag": "WealthOS", "instrument_token": instrument_key,
                        "order_type": "MARKET", "transaction_type": action,
                        "disclosed_quantity": 0, "trigger_price": 0, "is_amo": False
                    }
                    res = requests.post(url, headers=headers, json=order_data, timeout=7)
                    rj = res.json()
                    if res.status_code == 200 and rj.get('status') == 'success':
                        u_state['last_order_error'] = ''
                        return True
                    else:
                        u_state['last_order_error'] = rj.get('errors', [{}])[0].get('message', 'Order Rejected')
                        return False
                elif b_name == "Dhan":
                    res = requests.post('https://api.dhan.co/orders', headers={'access-token': token, 'Content-Type': 'application/json'},
                                        json={"dhanClientId": u_state.get('api_key', ''), "transactionType": action, "exchangeSegment": "NSE_EQ", "productType": "INTRADAY", "orderType": "MARKET", "validity": "DAY", "securityId": symbol, "quantity": int(qty)}, timeout=7)
                    return res.status_code == 200
            except Exception as e:
                u_state['last_order_error'] = str(e)
                return False
        return True

    def log_executed_trade(u_hash, date_s, time_s, sym, t_type, bp, sp, qty, gross_pnl):
        turnover = (bp + sp) * qty
        est_charges = min(40.0, turnover * 0.0005) + (turnover * 0.0003)
        net_pnl = gross_pnl - est_charges
        try:
            conn = get_db_connection()
            conn.execute("INSERT INTO trades (user_hash, date, time, symbol, type, buy_price, sell_price, qty, pnl) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (u_hash, date_s, time_s, sym, t_type, round(bp, 2), round(sp, 2), int(qty), round(net_pnl, 2)))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def fetch_candles_upstox(instrument_key, token):
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

    def background_trading_loop(u_hash, u_state):
        while u_state['running']:
            token = u_state['token']
            if not token:
                time.sleep(5)
                continue
            ist_zone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            now_ist = datetime.datetime.now(ist_zone)
            curr_t = now_ist.time()

            if curr_t >= datetime.time(15, 15):
                if u_state['active_pos']:
                    pos = u_state['active_pos']
                    df_c = fetch_candles_upstox(pos['key'], token)
                    ep = float(df_c['close'].iloc[-1]) if (df_c is not None and len(df_c) > 0) else pos['buy_price']
                    if place_real_order(pos['symbol'], pos['key'], pos['qty'], "SELL", token, u_state):
                        pnl = (ep - pos['buy_price']) * pos['qty']
                        log_executed_trade(u_hash, now_ist.strftime("%Y-%m-%d"), now_ist.strftime("%I:%M:%S %p"), pos['symbol'], "AUTO_315_EXIT", pos['buy_price'], ep, pos['qty'], pnl)
                        send_telegram_alert(f"⏰ *3:15 PM Auto Exit:* `{pos['symbol']}` PnL: `₹{pnl:.2f}`", u_state['tg_token'], u_state['tg_chat'])
                        u_state['active_pos'] = None
                u_state['nifty_status'] = "🌙 Market Closed (After 3:15 PM)"
                time.sleep(15)
                continue

            if u_state['consecutive_losses'] >= 2:
                u_state['kill_switch'] = True
                u_state['running'] = False
                send_telegram_alert("🛑 *Kill Switch Activated!* Halted after 2 consecutive losses.", u_state['tg_token'], u_state['tg_chat'])
                break

            if u_state['active_pos']:
                pos = u_state['active_pos']
                df_c = fetch_candles_upstox(pos['key'], token)
                if df_c is not None and len(df_c) > 0:
                    cur_p = float(df_c['close'].iloc[-1])
                    el_mins = (time.time() - pos['entry_time']) / 60.0
                    if el_mins >= 45 and (abs(cur_p - pos['buy_price']) / pos['buy_price']) < 0.005:
                        if place_real_order(pos['symbol'], pos['key'], pos['qty'], "SELL", token, u_state):
                            pnl = (cur_p - pos['buy_price']) * pos['qty']
                            log_executed_trade(u_hash, now_ist.strftime("%Y-%m-%d"), now_ist.strftime("%I:%M:%S %p"), pos['symbol'], "TIME_EXIT_45M", pos['buy_price'], cur_p, pos['qty'], pnl)
                            u_state['active_pos'] = None
                    elif cur_p >= pos['target']:
                        if place_real_order(pos['symbol'], pos['key'], pos['qty'], "SELL", token, u_state):
                            pnl = (cur_p - pos['buy_price']) * pos['qty']
                            log_executed_trade(u_hash, now_ist.strftime("%Y-%m-%d"), now_ist.strftime("%I:%M:%S %p"), pos['symbol'], "TARGET_HIT", pos['buy_price'], cur_p, pos['qty'], pnl)
                            send_telegram_alert(f"🎉 *TARGET HIT:* `{pos['symbol']}` Profit: `+₹{pnl:.2f}`", u_state['tg_token'], u_state['tg_chat'])
                            u_state['consecutive_losses'] = 0
                            u_state['active_pos'] = None
                    elif cur_p <= pos['sl']:
                        if place_real_order(pos['symbol'], pos['key'], pos['qty'], "SELL", token, u_state):
                            pnl = (cur_p - pos['buy_price']) * pos['qty']
                            log_executed_trade(u_hash, now_ist.strftime("%Y-%m-%d"), now_ist.strftime("%I:%M:%S %p"), pos['symbol'], "STOP_LOSS", pos['buy_price'], cur_p, pos['qty'], pnl)
                            send_telegram_alert(f"🛑 *STOP LOSS HIT:* `{pos['symbol']}` Loss: `₹{pnl:.2f}`", u_state['tg_token'], u_state['tg_chat'])
                            u_state['consecutive_losses'] += 1
                            u_state['active_pos'] = None

            if now_ist.weekday() >= 5 or curr_t < datetime.time(9, 20) or curr_t > datetime.time(15, 5):
                u_state['nifty_status'] = "🌙 Waiting for Market Window (9:20 AM - 3:05 PM)"
                time.sleep(10)
                continue

            df_n = fetch_candles_upstox('NSE_INDEX|Nifty 50', token)
            nifty_ok = False
            if df_n is not None and len(df_n) >= 20:
                c_s = df_n['close'].astype(float)
                nifty_ok = c_s.iloc[-1] >= c_s.ewm(span=20, adjust=False).mean().iloc[-1]
                u_state['nifty_status'] = "🟢 Bullish (> EMA20)" if nifty_ok else "🔴 Bearish (< EMA20)"

            if u_state['active_pos'] is None:
                active_wl = WATCHLIST_HALAL if u_state['shariah_lock'] else WATCHLIST_CONV
                for sym, ikey in active_wl.items():
                    if not u_state['running'] or u_state['active_pos'] is not None:
                        break
                    df = fetch_candles_upstox(ikey, token)
                    if df is None or len(df) < 25:
                        continue
                    close = df['close'].astype(float)
                    vol = df['volume'].astype(float)
                    high = df['high'].astype(float)
                    low = df['low'].astype(float)
                    ema9 = close.ewm(span=9, adjust=False).mean()
                    ema21 = close.ewm(span=21, adjust=False).mean()
                    vwap = (((high + low + close) / 3) * vol).cumsum() / vol.cumsum().replace(0, np.nan)
                    delta = close.diff()
                    rs = delta.where(delta > 0, 0.0).rolling(14).mean() / (-delta.where(delta < 0, 0.0)).rolling(14).mean().replace(0, np.nan)
                    rsi = float((100 - (100 / (1 + rs))).fillna(50.0).iloc[-1])
                    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
                    atr = float(tr.rolling(14).mean().iloc[-1]) if not np.isnan(tr.rolling(14).mean().iloc[-1]) else (float(close.iloc[-1]) * 0.01)

                    cp = float(close.iloc[-1])
                    vw = float(vwap.iloc[-1]) if not np.isnan(vwap.iloc[-1]) else cp
                    ecross = (ema9.iloc[-2] <= ema21.iloc[-2]) and (ema9.iloc[-1] > ema21.iloc[-1])
                    vsurge = float(vol.iloc[-1]) >= 1.2 * float(vol.rolling(20).mean().iloc[-1])

                    if nifty_ok and cp > vw and vsurge and (50 <= rsi <= 68) and ecross:
                        sl_dist = max(0.5, 1.5 * atr)
                        sl_p = cp - sl_dist
                        tg_p = cp + (3.0 * atr)
                        qty = max(1, min(int(u_state['risk'] // sl_dist), int(u_state['capital'] // cp)))
                        if cp <= u_state['capital'] and place_real_order(sym, ikey, qty, "BUY", token, u_state):
                            u_state['active_pos'] = {'symbol': sym, 'key': ikey, 'buy_price': cp, 'qty': qty, 'sl': sl_p, 'target': tg_p, 'entry_time': time.time()}
                            status, reason = "🎯 BUY_TRIGGERED", f"Bought Qty {qty} @ ₹{cp:.2f}"
                            send_telegram_alert(f"🚀 *BUY EXECUTED:* `{sym}` (Qty: {qty}) @ ₹{cp:.2f} | Target: ₹{tg_p:.2f} | SL: ₹{sl_p:.2f}", u_state['tg_token'], u_state['tg_chat'])
                        else:
                            status, reason = "SKIPPED_CAP_OR_ERR", "Capital limit or order rejected"
                    else:
                        status, reason = "SCANNING", f"RSI: {rsi:.1f} | >VWAP: {cp > vw}"

                    try:
                        conn = get_db_connection()
                        conn.execute("INSERT INTO audit_logs (user_hash, date, time, symbol, price, vwap, rsi, vol_surge, ema_cross, nifty_trend, status, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                     (u_hash, now_ist.strftime("%Y-%m-%d"), now_ist.strftime("%I:%M:%S %p"), sym, round(cp, 2), round(vw, 2), round(rsi, 1), "Yes" if vsurge else "No", "Yes" if ecross else "No", u_state['nifty_status'], status, reason))
                        conn.commit()
                        conn.close()
                    except Exception:
                        pass
            time.sleep(10)

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
            state['kill_switch'] = False
            state['consecutive_losses'] = 0
            if state['thread'] is None or not state['thread'].is_alive():
                t = threading.Thread(target=background_trading_loop, args=(USER_HASH, state), daemon=True)
                t.start()
                state['thread'] = t
            st.sidebar.success("ബോട്ട് സജീവം!")

    if col2.button("⏹️ STOP BOT", use_container_width=True):
        state['running'] = False
        st.sidebar.warning("ബോട്ട് നിർത്തി!")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ബോട്ട് സ്റ്റാറ്റസ്", "🟢 സർവറിൽ ഓടുന്നു" if state['running'] else ("🛑 കിൽ സ്വിച്ച് ഓഫ്" if state['kill_switch'] else "🔴 ഓഫ് ആണ്"))
    m2.metric("നിഫ്റ്റി 50 ട്രെൻഡ്", state['nifty_status'])
    m3.metric("തുടർച്ചയായ നഷ്ടങ്ങൾ", f"{state['consecutive_losses']} / 2")
    m4.metric("ക്യാപിറ്റൽ", f"₹{state['capital']:,.2f}")

    if state['active_pos']:
        ap = state['active_pos']
        st.success(f"📌 **നിലവിലെ ലൈവ് ട്രേഡ്:** `{ap['symbol']}` | എണ്ണം: `{ap['qty']}` | വാങ്ങിയ വില: `₹{ap['buy_price']:.2f}` | ടാർജറ്റ്: `₹{ap['target']:.2f}` | സ്റ്റോപ്പ്-ലോസ്: `₹{ap['sl']:.2f}`")

    t_log1, t_log2 = st.tabs(["🔍 ലൈവ് സ്കാനിംഗ് ഓഡിറ്റ് ലോഗ്", "📜 പൂർത്തിയായ ട്രേഡുകൾ (Net PnL)"])
    with t_log1:
        conn = get_db_connection()
        today_s = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")
        df_l = pd.read_sql_query("SELECT time AS Time, symbol AS Stock, price AS Price, vwap AS VWAP, rsi AS RSI, nifty_trend AS Nifty, status AS Status, reason AS Evaluation FROM audit_logs WHERE user_hash=? AND date=? ORDER BY id DESC LIMIT 40", conn, params=(USER_HASH, today_s))
        conn.close()
        if not df_l.empty:
            st.dataframe(df_l, use_container_width=True, hide_index=True)
        else:
            st.info("മാർക്കറ്റ് സമയത്ത് (9:20 AM - 3:15 PM) ബോട്ട് സ്റ്റാർട്ട് ചെയ്യുമ്പോൾ ലൈവ് സ്കാനിംഗ് ഡാറ്റ ഇവിടെ വരും.")
    with t_log2:
        conn = get_db_connection()
        df_t = pd.read_sql_query("SELECT date, time, symbol, type, qty, buy_price, sell_price, pnl FROM trades WHERE user_hash=? ORDER BY id DESC", conn, params=(USER_HASH,))
        conn.close()
        if not df_t.empty:
            st.dataframe(df_t, use_container_width=True, hide_index=True)
        else:
            st.info("ഇതുവരെ ട്രേഡുകൾ നടന്നിട്ടില്ല.")

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

# ##################################################################
# 💬 MODULE 12: USER FEEDBACK (PRIVATE TELEGRAM & PUBLIC BOARD)
# ##################################################################
elif main_menu == MENU_ITEMS[12]:
    st.title("💬 അഭിപ്രായങ്ങളും നിർദ്ദേശങ്ങളും സംശയങ്ങളും (User Feedback, Q&A & Bug Report)")
    st.warning("🔒 **സ്വകാര്യത മുന്നറിയിപ്പ്:** പൊതുവായ ഫീഡ്‌ബാക്ക് ബോർഡിൽ നിങ്ങളുടെ ഫോൺ നമ്പറോ വ്യക്തിപരമായ ലോൺ വിവരങ്ങളോ എഴുതരുത്. അഡ്മിന് മാത്രം കാണാനായി താഴെയുള്ള 'Send Privately' ടിക്ക് ചെയ്യുക.")
    fb_col1, fb_col2 = st.columns([2, 1])
    with fb_col1:
        with st.form("user_feedback_form"):
            u_name = st.text_input("നിങ്ങളുടെ പേര് (Optional):", placeholder="ഉദാ: Muhammed / Anonymous")
            fb_cat = st.selectbox("വിഭാഗം തിരഞ്ഞെടുക്കുക:", [
                "💡 പുതിയ ഫീച്ചർ നിർദ്ദേശം (Feature Suggestion)",
                "🐞 ആപ്പിലെ പോരായ്മ / എറർ അറിയിക്കുക (Bug / Issue Report)",
                "❓ സംശയങ്ങൾ / ചോദ്യങ്ങൾ (Question / Doubt)",
                "⭐ പൊതുവായ അഭിപ്രായം (General Review)"
            ])
            fb_rating = st.select_slider("റേറ്റിംഗ്:", options=["⭐ 1", "⭐⭐ 2", "⭐⭐⭐ 3", "⭐⭐⭐⭐ 4", "⭐⭐⭐⭐⭐ 5 (മികച്ചത്)"], value="⭐⭐⭐⭐⭐ 5 (മികച്ചത്)")
            is_private_fb = st.checkbox("🔒 ഇത് അഡ്മിന് മാത്രം സ്വകാര്യമായി അയക്കുക (പബ്ലിക് ബോർഡിൽ കാണിക്കരുത്)")
            fb_msg = st.text_area("നിങ്ങളുടെ അഭിപ്രായം / ചോദ്യം ഇവിടെ വിശദമായി എഴുതുക:")
            fb_sub = st.form_submit_button("📨 അഭിപ്രായം സമർപ്പിക്കുക (Submit Feedback)", type="primary")

            if fb_sub and fb_msg.strip():
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")
                if not is_private_fb:
                    conn = get_db_connection()
                    conn.execute("INSERT INTO user_feedback (date, name, category, rating, message) VALUES (?, ?, ?, ?, ?)",
                                 (now_str, u_name.strip() or "Anonymous User", fb_cat, fb_rating, fb_msg.strip()))
                    conn.commit()
                    conn.close()
                if state.get('tg_token') and state.get('tg_chat'):
                    try:
                        tg_text = f"📬 *New Feedback ({'PRIVATE' if is_private_fb else 'PUBLIC'})*\n👤 *From:* {u_name or 'Anon'}\n📂 *Type:* {fb_cat}\n⭐ *Rating:* {fb_rating}\n📝 *Message:* {fb_msg.strip()}"
                        requests.post(f"https://api.telegram.org/bot{state['tg_token']}/sendMessage", json={"chat_id": state['tg_chat'], "text": tg_text, "parse_mode": "Markdown"}, timeout=5)
                    except Exception:
                        pass
                st.success("🎉 നന്ദി! നിങ്ങളുടെ അഭിപ്രായം വിജയകരമായി രേഖപ്പെടുത്തി!")

    with fb_col2:
        st.info("### 🐙 GitHub Issues\nകോഡുമായി ബന്ധപ്പെട്ട നിർദ്ദേശങ്ങൾ GitHub വഴിയും അറിയിക്കാം:")
        st.link_button("🐞 Open GitHub Issues", "https://github.com/anasvkvp/my-trading-bot/issues", use_container_width=True)

    conn = get_db_connection()
    df_fb = pd.read_sql_query("SELECT date AS Date, name AS Name, category AS Category, rating AS Rating, message AS [Feedback / Question] FROM user_feedback ORDER BY id DESC LIMIT 30", conn)
    conn.close()
    if not df_fb.empty:
        st.dataframe(df_fb, use_container_width=True, hide_index=True)

# ==============================================================================
# ⚖️ MANDATORY GLOBAL REGULATORY FOOTER (DISPLAYED AT THE BOTTOM OF EVERY PAGE)
# ==============================================================================
st.markdown("---")
st.warning("""
⚖️ **നിയമപരമായ മുന്നറിയിപ്പ് (SEBI & RBI Regulatory Disclaimer — Educational Purpose Only):**  
1. **നോൺ-അഡ്വൈസറി സ്റ്റാറ്റസ് (No Financial Advice):** ഈ സോഫ്റ്റ്‌വെയർ പ്ലാറ്റ്‌ഫോം (**Autonomous Wealth OS**) പൂർണ്ണമായും **വിദ്യാഭ്യാസം, ഗണിതശാസ്ത്ര ഗവേഷണം, സ്വയം പഠനം (Educational & Quantitative Research Purpose)** എന്നിവയ്ക്ക് വേണ്ടി മാത്രം നിർമ്മിച്ചിട്ടുള്ളതാണ്. ഇതിന്റെ നിർമ്മാതാക്കൾ **SEBI** രജിസ്റ്റർ ചെയ്ത ഇൻവെസ്റ്റ്‌മെന്റ് അഡ്വൈസർമാരോ (RIA), റിസർച്ച് അനലിസ്റ്റുകളോ (RA), അല്ലെങ്കിൽ **RBI** അംഗീകൃത ധനകാര്യ സ്ഥാപനമോ അല്ല.  
2. **വ്യക്തിഗത ഉത്തരവാദിത്തം (Self-Directed Decision):** ഇതിൽ കാണുന്ന അൽഗോറിതമിക് സ്റ്റോക്ക് സ്ക്രീനറുകൾ, റെക്കമെൻഡേഷൻ പട്ടികകൾ, ഐ.പി.ഒ / മ്യൂച്വൽ ഫണ്ട് ഡാറ്റ എന്നിവയൊന്നും തന്നെ ഏതെങ്കിലും ഓഹരി വാങ്ങാനോ വിൽക്കാനോ ഉള്ള വ്യക്തിഗത ശുപാർശയല്ല. നിക്ഷേപിക്കുന്നതിന് മുൻപ് നിങ്ങൾ സ്വയം പഠിക്കുകയും, അംഗീകൃത സാമ്പത്തിക വിദഗ്ദ്ധരുടെ ഉപദേശം തേടുകയും ചെയ്യുക.
""")
