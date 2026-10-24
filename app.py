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
        c.execute('''CREATE TABLE IF NOT EXISTS wealth_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT, asset TEXT, category TEXT, action TEXT,
                        status TEXT, veteran_reason TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS manual_portfolio (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT, qty REAL, buy_price REAL, buy_date TEXT, notes TEXT)''')
        conn.commit()
        conn.close()
    except Exception:
        pass

init_db()

# ==========================================
# 👑 മാസ്റ്റർ ഗ്ലോബൽ സ്വിച്ച്
# ==========================================
st.sidebar.markdown("# 🏛️ WEALTH OS")
wealth_mode = st.sidebar.radio(
    "നിക്ഷേപ തത്ത്വശാസ്ത്രം (Philosophy):",
    ["🌐 ആഗോള ജനറൽ മോഡ് (Global Conventional)", "🌙 100% പ്യുവർ ശരീഅത്ത് മോഡ് (Pure Halal AAOIFI)"]
)
is_shariah = "ശരീഅത്ത്" in wealth_mode

st.sidebar.markdown("---")
main_menu = st.sidebar.radio(
    "പ്രധാന വിഭാഗം തിരഞ്ഞെടുക്കുക:",
    [
        "🎯 ലക്ഷ്യാധിഷ്ഠിത പോർട്ട്ഫോളിയോ (Goal Engine)",
        "💼 എന്റെ ലൈവ് പോർട്ട്ഫോളിയോ & എക്സിറ്റ് വാച്ച്ഡോഗ്",
        "🏛️ 50-Year Veteran സ്റ്റോക്ക് നിലവറ (Why Buy & Exit Rules)",
        "📈 മ്യൂച്വൽ ഫണ്ടുകൾ & ഇ.ടി.എഫുകൾ",
        "🌍 ആഗോള വിപണികൾ (US & Currency Advisor)",
        "🥇 ഗോൾഡ് & സുരക്ഷിത ആസ്തികൾ",
        "📚 അഡ്വൈസറി ജേർണൽ & ചേഞ്ച് ലോഗ്",
        "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്"
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
# 🎯 വിഭാഗം 1: ലക്ഷ്യാധിഷ്ഠിത പോർട്ട്ഫോളിയോ എഞ്ചിൻ
# ##################################################################
if main_menu == "🎯 ലക്ഷ്യാധിഷ്ഠിത പോർട്ട്ഫോളിയോ (Goal Engine)":
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
        if "യുദ്ധ" in market_climate: eq_pct, gold_pct, cash_pct, reit_pct = 0.40, 0.25, 0.25, (0.0 if is_shariah else 0.10)
        else: eq_pct, gold_pct, cash_pct, reit_pct = 0.60, 0.15, 0.15, (0.0 if is_shariah else 0.10)
        rec_text = "ഇടത്തരം കാലാവധിയിൽ ഹൈ-ഗ്രോത്ത് കമ്പനികൾക്കും എത്തിക്കൽ ഫണ്ടുകൾക്കും മുൻഗണന."
    else:
        if "തകർച്ച" in market_climate: eq_pct, gold_pct, cash_pct, reit_pct = 0.75, 0.15, 0.10, 0.0
        else: eq_pct, gold_pct, cash_pct, reit_pct = 0.65, 0.15, 0.10, (0.0 if is_shariah else 0.10)
        rec_text = "ദീർഘകാലത്തേക്ക് അൺബ്രേക്കബിൾ കുത്തകകളിൽ പണം കോമ്പൗണ്ട് ചെയ്യാൻ അനുവദിക്കുക."

    st.info(f"💡 **വിദഗ്ദ്ധന്റെ നിർദ്ദേശം:** {rec_text}")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("ഇക്വിറ്റി ഓഹരികൾ", f"₹{(inv_amount * eq_pct):,.0f}", f"{int(eq_pct*100)}%")
    a2.metric("ഗോൾഡ് & സിൽവർ", f"₹{(inv_amount * gold_pct):,.0f}", f"{int(gold_pct*100)}%")
    a3.metric("ക്യാഷ് / സേവിങ്സ്", f"₹{(inv_amount * cash_pct):,.0f}", f"{int(cash_pct*100)}%")
    if not is_shariah: a4.metric("റിയൽ എസ്റ്റേറ്റ് REITs", f"₹{(inv_amount * reit_pct):,.0f}", f"{int(reit_pct*100)}%")
    else: a4.metric("ശരീഅത്ത് പാലിക്കൽ", "100% Halal", "AAOIFI")

# ##################################################################
# 💼 വിഭാഗം 2: എന്റെ ലൈവ് പോർട്ട്ഫോളിയോ & എക്സിറ്റ് വാച്ച്ഡോഗ് (NEW!)
# ##################################################################
elif main_menu == "💼 എന്റെ ലൈവ് പോർട്ട്ഫോളിയോ & എക്സിറ്റ് വാച്ച്ഡോഗ്":
    st.title("💼 എന്റെ പോർട്ട്ഫോളിയോ & എക്സിറ്റ് വാച്ച്ഡോഗ് (Live Holdings Sentinel)")
    st.caption("നിങ്ങൾ വാങ്ങിയ ഓഹരികൾ ബ്രോക്കറിൽ നിന്ന് തനിയെ കണ്ടെത്തി, എക്സിറ്റ് സിഗ്നലുകൾ തത്സമയം നിരീക്ഷിക്കുന്ന സംവിധാനം.")

    h_tab1, h_tab2 = st.tabs(["⚡ Upstox ലൈവ് ഹോൾഡിംഗ്സ് (Auto Sync)", "📝 മാനുവൽ പോർട്ട്ഫോളിയോ (Groww / Zerodha)"])

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

                                    # എക്സിറ്റ് ഹെൽത്ത് ചെക്ക്
                                    pnl_pct = ((cur_p - avg_p) / avg_p * 100) if avg_p > 0 else 0
                                    if pnl_pct < -10.0:
                                        sentinel_status = "🚨 എക്സിറ്റ് മുന്നറിയിപ്പ് (Stop-Loss / Review)"
                                    elif pnl_pct > 20.0:
                                        sentinel_status = "🟢 മികച്ച ലാഭത്തിൽ (Hold / Trail SL)"
                                    else:
                                        sentinel_status = "🟡 സാധാരണ നിലയിൽ (Hold)"

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
                            st.warning(f"Upstox കണക്റ്റിവിറ്റിയിൽ തടസ്സം: {data.get('errors', 'ടോക്കൺ കാലാവധി കഴിഞ്ഞിരിക്കാം.')}")
                    except Exception as e:
                        st.error(f"ഡാറ്റ ലഭിക്കുന്നതിൽ തടസ്സം: {e}")

    with h_tab2:
        st.subheader("📝 മറ്റ് ആപ്പുകളിൽ വാങ്ങിയ ഓഹരികൾ രേഖപ്പെടുത്തുക (Groww, Zerodha, etc.)")
        col_m1, col_m2, col_m3 = st.columns(3)
        m_sym = col_m1.text_input("സ്റ്റോക്ക് സിംബൽ (ഉദാ: CDSL, TCS):").upper()
        m_qty = col_m2.number_input("വാങ്ങിയ എണ്ണം (Qty):", value=1, step=1)
        m_bp = col_m3.number_input("വാങ്ങിയ വില (₹):", value=100.0, step=10.0)

        if st.button("➕ എന്റെ പോർട്ട്ഫോളിയോയിലേക്ക് ചേർക്കുക"):
            if m_sym:
                try:
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("INSERT INTO manual_portfolio (symbol, qty, buy_price, buy_date, notes) VALUES (?, ?, ?, ?, ?)",
                              (m_sym, m_qty, m_bp, datetime.date.today().strftime("%Y-%m-%d"), "Manual Entry"))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ {m_sym} പോർട്ട്ഫോളിയോയിൽ ചേർത്തു!")
                except Exception as e:
                    st.error(f"സേവ് ചെയ്യുന്നതിൽ തടസ്സം: {e}")

        st.markdown("---")
        st.caption("നിങ്ങൾ മാനുവലായി ചേർത്ത ഓഹരികൾ:")
        try:
            conn = sqlite3.connect(DB_NAME)
            df_man = pd.read_sql_query("SELECT symbol AS Stock, qty AS Qty, buy_price AS [Buy Price], buy_date AS [Bought Date] FROM manual_portfolio ORDER BY id DESC", conn)
            conn.close()
            if not df_man.empty:
                st.dataframe(df_man, use_container_width=True, hide_index=True)
            else:
                st.info("ഇതുവരെ മാനുവൽ ഓഹരികൾ ഒന്നും ചേർത്തിട്ടില്ല.")
        except Exception:
            st.info("ഡാറ്റ ലഭ്യമായിട്ടില്ല.")

# ##################################################################
# 🏛️ വിഭാഗം 3: 50-Year Veteran സ്റ്റോക്ക് നിലവറ
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
# 📈 വിഭാഗം 4: മ്യൂച്വൽ ഫണ്ടുകൾ & ഇ.ടി.എഫുകൾ
# ##################################################################
elif main_menu == "📈 മ്യൂച്വൽ ഫണ്ടുകൾ & ഇ.ടി.എഫുകൾ":
    st.title("📈 മ്യൂച്വൽ ഫണ്ട് & ഇ.ടി.എഫ് സെലക്ടർ")
    if is_shariah:
        funds = [
            {"Fund": "Tata Ethical Fund", "Type": "Shariah Equity", "3Y CAGR": "20.8%", "5Y CAGR": "22.5%", "Expense": "0.85%"},
            {"Fund": "Taurus Ethical Fund", "Type": "Shariah Equity", "3Y CAGR": "22.1%", "5Y CAGR": "21.2%", "Expense": "0.95%"},
            {"Fund": "Nippon Gold BeES", "Type": "Physical Gold", "Purity": "99.5% 24K", "Expense": "0.55%"}
        ]
    else:
        funds = [
            {"Fund": "Parag Parikh Flexi Cap Fund", "Type": "Flexi Cap", "3Y CAGR": "21.5%", "5Y CAGR": "24.2%", "Expense": "0.62%"},
            {"Fund": "UTI Nifty 50 Index Fund", "Type": "Index", "3Y CAGR": "15.8%", "5Y CAGR": "16.5%", "Expense": "0.18%"},
            {"Fund": "Quant Small Cap Fund", "Type": "Small Cap", "3Y CAGR": "34.2%", "5Y CAGR": "38.5%", "Expense": "0.77%"}
        ]
    st.dataframe(pd.DataFrame(funds), use_container_width=True, hide_index=True)

# ##################################################################
# 🌍 വിഭാഗം 5: ആഗോള വിപണികൾ (US & Currency Advisor)
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
# 🥇 വിഭാഗം 6: ഗോൾഡ് & സുരക്ഷിത ആസ്തികൾ
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
# 📚 വിഭാഗം 7: അഡ്വൈസറി ജേർണൽ & ചേഞ്ച് ലോഗ്
# ##################################################################
elif main_menu == "📚 അഡ്വൈസറി ജേർണൽ & ചേഞ്ച് ലോഗ്":
    st.title("📚 ഇൻവെസ്റ്റ്മെന്റ് ജേർണൽ & ചേഞ്ച് ലോഗ്")
    try:
        conn = sqlite3.connect(DB_NAME)
        df_audit = pd.read_sql_query("SELECT date AS Date, asset AS Asset, action AS Action, status AS Status, veteran_reason AS [Reason / Thesis] FROM wealth_audit ORDER BY id DESC LIMIT 50", conn)
        conn.close()
        if not df_audit.empty: st.dataframe(df_audit, use_container_width=True, hide_index=True)
        else: st.info("തീരുമാനങ്ങൾ ഇവിടെ ഓഡിറ്റ് ആയി രേഖപ്പെടുത്തും.")
    except Exception: st.info("ഡാറ്റ വരാൻ കാത്തിരിക്കുന്നു...")

# ##################################################################
# ⚡ വിഭാഗം 8: ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്
# ##################################################################
elif main_menu == "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്":
    st.title("⚡ Upstox ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്")
    if is_shariah:
        st.error("⚠️ **ശരീഅത്ത് മുന്നറിയിപ്പ്:** ഇൻട്രാഡേ ലിവറേജ് ട്രേഡിംഗും F&O-യും ഇസ്‌ലാമിക പണ്ഡിതന്മാർ വിലക്കിയിട്ടുള്ളതാണ്. ശരീഅത്ത് നിക്ഷേപകർ ദീർഘകാല ഡെലിവറി ഇക്വിറ്റിയും എത്തിക്കൽ ഫണ്ടുകളും മാത്രം തിരഞ്ഞെടുക്കുക.")
    else:
        st.info("ഇൻട്രാഡേ ബോട്ട് ബാക്ക്ഗ്രൗണ്ടിൽ നിരീക്ഷണത്തിലാണ്.")
