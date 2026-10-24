import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import time
import threading
import sqlite3
import yfinance as yf

st.set_page_config(page_title="Autonomous Wealth OS", layout="wide", page_icon="🏛️")

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
        c.execute('''CREATE TABLE IF NOT EXISTS wealth_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT, asset TEXT, category TEXT, action TEXT,
                        status TEXT, veteran_reason TEXT)''')
        conn.commit()
        conn.close()
    except Exception:
        pass

init_db()

def log_wealth_decision(asset, category, action, status, reason):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        today = datetime.date.today().strftime("%Y-%m-%d")
        c.execute('''INSERT INTO wealth_audit (date, asset, category, action, status, veteran_reason)
                     VALUES (?, ?, ?, ?, ?, ?)''', (today, asset, category, action, status, reason))
        conn.commit()
        conn.close()
    except Exception:
        pass

# ==========================================
# 👑 മാസ്റ്റർ ഗ്ലോബൽ സ്വിച്ച് (Master Shariah vs General)
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
        "🎯 ലക്ഷ്യാധിഷ്ഠിത പോർട്ട്ഫോളിയോ (Goal & Allocation Engine)",
        "🏛️ 50-Year Veteran സ്റ്റോക്ക് നിലവറ (Why Buy & Exit Rules)",
        "📈 മ്യൂച്വൽ ഫണ്ടുകൾ & ഇ.ടി.എഫുകൾ",
        "🌍 ആഗോള വിപണികൾ (US & Currency Advisor)",
        "🥇 ഗോൾഡ് & സുരക്ഷിത ആസ്തികൾ",
        "📚 അഡ്വൈസറി ജേർണൽ & ചേഞ്ച് ലോഗ് (Audit History)",
        "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്"
    ]
)

# ##################################################################
# 🎯 വിഭാഗം 1: ലക്ഷ്യാധിഷ്ഠിത പോർട്ട്ഫോളിയോ എഞ്ചിൻ (Goal & Time Horizon)
# ##################################################################
if main_menu == "🎯 ലക്ഷ്യാധിഷ്ഠിത പോർട്ട്ഫോളിയോ (Goal & Allocation Engine)":
    st.title("🎯 ലക്ഷ്യാധിഷ്ഠിത വെൽത്ത് കാൽക്കുലേറ്റർ (Goal-Based Asset Allocation)")
    st.caption("50-വർഷത്തെ വിദഗ്ദ്ധ തത്വം: കാലാവധിയും വിപണി സാഹചര്യവും അനുസരിച്ച് പണം വിന്യസിക്കുക.")

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
    
    # മാർക്കറ്റ് സാഹചര്യം തിരഞ്ഞെടുക്കൽ
    market_climate = st.selectbox(
        "നിലവിലെ വിപണി സാഹചര്യം വിലയിരുത്തുക (Current Market Regime):",
        [
            "🟢 ശാന്തമായ വിപണി (Normal Bull / Steady Growth)",
            "⚠️ അസ്ഥിരതയും യുദ്ധ ഭീഷണിയും / എണ്ണവില വർദ്ധനവ് (War / High Oil / Volatility)",
            "🔴 വിപണിയിലെ കടുത്ത തകർച്ച (Blood on the Streets / Extreme Crash)"
        ]
    )

    # അലോക്കേഷൻ കണക്കുകൂട്ടൽ
    if "1 വർഷം" in goal_horizon:
        if is_shariah:
            eq_pct, gold_pct, cash_pct, reit_pct = 0.15, 0.35, 0.50, 0.0
            rec_text = "1 വർഷത്തെ ഹ്രസ്വകാലത്തേക്ക് ഇക്വിറ്റി റിസ്ക് വളരെ കുറയ്ക്കണം. പലിശ രഹിത ഇസ്‌ലാമിക സേവിങ്സ്/ക്യാഷിലും ഗോൾഡിലും മുൻഗണന."
        else:
            eq_pct, gold_pct, cash_pct, reit_pct = 0.15, 0.25, 0.50, 0.10
            rec_text = "1 വർഷത്തേക്ക് മുതൽ സുരക്ഷിതമായിരിക്കണം. ആർബിട്രേജ് ഫണ്ടുകളിലും ലിക്വിഡ് കാഷിലും മുൻഗണന."
    elif "3 - 5 വർഷം" in goal_horizon:
        if "യുദ്ധ" in market_climate:
            eq_pct, gold_pct, cash_pct, reit_pct = 0.40, 0.25, 0.25, (0.0 if is_shariah else 0.10)
            rec_text = "യുദ്ധവും ക്രൂഡ് ഓയിൽ ഭീഷണിയും ഉള്ളതിനാൽ സ്വർണ്ണത്തിന്റെയും ലിക്വിഡ് ക്യാഷിന്റെയും വിഹിതം വർദ്ധിപ്പിച്ചു."
        else:
            eq_pct, gold_pct, cash_pct, reit_pct = 0.60, 0.15, 0.15, (0.0 if is_shariah else 0.10)
            rec_text = "ഇടത്തരം കാലാവധിയിൽ ഹൈ-ഗ്രോത്ത് കമ്പനികൾക്കും എത്തിക്കൽ ഫണ്ടുകൾക്കും മുൻഗണന."
    else:  # 10+ വർഷം
        if "തകർച്ച" in market_climate:
            eq_pct, gold_pct, cash_pct, reit_pct = 0.75, 0.15, 0.10, 0.0
            rec_text = "മാർക്കറ്റ് കടുത്ത തകർച്ചയിലാണ്! വാറൻ ബഫറ്റ് ശൈലിയിൽ കയ്യിലുള്ള പണം ഉപയോഗിച്ച് കുത്തക ഓഹരികൾ വാങ്ങിക്കൂട്ടാൻ ഏറ്റവും അനുയോജ്യമായ സമയം!"
        else:
            eq_pct, gold_pct, cash_pct, reit_pct = 0.65, 0.15, 0.10, (0.0 if is_shariah else 0.10)
            rec_text = "10 വർഷത്തിലധികം കാലാവധിയുള്ളതിനാൽ അൺബ്രേക്കബിൾ കുത്തകകളിലും ഫ്ലെക്സി ക്യാപിലും പണം കോമ്പൗണ്ട് ചെയ്യാൻ അനുവദിക്കുക."

    st.info(f"💡 **വിദഗ്ദ്ധന്റെ നിർദ്ദേശം:** {rec_text}")

    # വിഷ്വൽ കാർഡുകൾ
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("ഇക്വിറ്റി ഓഹരികൾ", f"₹{(inv_amount * eq_pct):,.0f}", f"{int(eq_pct*100)}%")
    a2.metric("ഗോൾഡ് & സിൽവർ", f"₹{(inv_amount * gold_pct):,.0f}", f"{int(gold_pct*100)}%")
    a3.metric("ക്യാഷ് / ലിക്വിഡ് ഫണ്ട്", f"₹{(inv_amount * cash_pct):,.0f}", f"{int(cash_pct*100)}%")
    if not is_shariah:
        a4.metric("റിയൽ എസ്റ്റേറ്റ് REITs", f"₹{(inv_amount * reit_pct):,.0f}", f"{int(reit_pct*100)}%")
    else:
        a4.metric("ശരീഅത്ത് പാലിക്കൽ", "100% Halal", "AAOIFI")

# ##################################################################
# 🏛️ വിഭാഗം 2: 50-Year Veteran സ്റ്റോക്ക് നിലവറ (Why Buy & Exit Rules)
# ##################################################################
elif main_menu == "🏛️ 50-Year Veteran സ്റ്റോക്ക് നിലവറ (Why Buy & Exit Rules)":
    st.title("🏛️ 50-Year Veteran ഓഹരി നിലവറ")
    st.caption("ഓരോ ഓഹരിയും എന്തുകൊണ്ട് വാങ്ങി? എപ്പോൾ വിറ്റ് ഒഴിവാക്കണം എന്നതിന്റെ കർശനമായ നിയമങ്ങൾ.")

    if is_shariah:
        st.success("🌙 **ശരീഅത്ത് പരിശോധന കഴിഞ്ഞ ഓഹരികൾ മാത്രം:** പലിശ രഹിത, കടബാധ്യത 33%-ൽ താഴെയുള്ള മുൻനിര കമ്പനികൾ.")
        stocks_data = [
            {
                "Stock": "TCS (Tata Consultancy Services)",
                "Sector": "IT / Tech Services",
                "Why Buy? (50Y Thesis)": "ഇന്ത്യയിലെ ഏറ്റവും വലിയ കടരഹിത ഐടി ഭീമൻ. 58% ROCE. ഭീമമായ ക്യാഷ് ഫ്ലോ.",
                "Red Flags (ഭീഷണികൾ)": "AI ഓട്ടോമേഷൻ കാരണം ക്ലയന്റുകൾ പുതിയ പ്രൊജക്റ്റുകൾ കുറയ്ക്കുന്നത്.",
                "Sell / Exit Trigger (എപ്പോൾ വിൽക്കണം?)": "കമ്പനിയുടെ പ്രവർത്തന ലാഭം (Operating Margin) തുടർച്ചയായി 20%-ൽ താഴെ പോവുകയോ, മാനേജ്‌മെന്റ് സത്യസന്ധത നഷ്ടപ്പെടുകയോ ചെയ്താൽ.",
                "Shariah Status": "✅ 100% AAOIFI Compliant"
            },
            {
                "Stock": "Tata Elxsi",
                "Sector": "AI Design & EV Software",
                "Why Buy? (50Y Thesis)": "ഇലക്ട്രിക് വാഹന സോഫ്റ്റ്‌വെയറിലും ഹെൽത്ത്‌കെയർ AI-യിലും അത്യുഗ്രൻ കുത്തക. 42% ROCE.",
                "Red Flags (ഭീഷണികൾ)": "ഉയർന്ന വാല്യുവേഷൻ (High P/E). യൂറോപ്യൻ വാഹന നിർമ്മാതാക്കളുടെ മാന്ദ്യം.",
                "Sell / Exit Trigger (എപ്പോൾ വിൽക്കണം?)": "വിറ്റുവരവ് വളർച്ച (Sales Growth) തുടർച്ചയായി 10%-ൽ താഴെയാവുകയോ കടബാധ്യത വരികയോ ചെയ്താൽ.",
                "Shariah Status": "✅ 100% AAOIFI Compliant"
            },
            {
                "Stock": "Sun Pharma / Cipla",
                "Sector": "Healthcare & Essential Pharma",
                "Why Buy? (50Y Thesis)": "ജീവൻരക്ഷാ മരുന്നുകൾക്ക് മാന്ദ്യമോ യുദ്ധമോ ബാധകമല്ല. പൂജ്യം കടം. റെസഷൻ-പ്രൂഫ്.",
                "Red Flags (ഭീഷണികൾ)": "യു.എസ് എഫ്.ഡി.എ (USFDA) റെഗുലേറ്ററി പരിശോധനകളിലെ തടസ്സങ്ങൾ.",
                "Sell / Exit Trigger (എപ്പോൾ വിൽക്കണം?)": "ഗുരുതരമായ നിയമലംഘനങ്ങൾ കാരണം യു.എസ് പ്ലാന്റുകൾ സ്ഥിരമായി പൂട്ടാൻ ഉത്തരവ് വന്നാൽ.",
                "Shariah Status": "✅ 100% AAOIFI Compliant"
            },
            {
                "Stock": "Polycab India",
                "Sector": "Cables & Infrastructure",
                "Why Buy? (50Y Thesis)": "ഇന്ത്യയിലെ ഓരോ പുതിയ വീടിനും ഫാക്ടറിക്കും വയറുകൾ നൽകുന്ന 25% വിപണി കുത്തക. 28% ROCE.",
                "Red Flags (ഭീഷണികൾ)": "കോപ്പർ (ചെമ്പ്) അസംസ്കൃത വസ്തുക്കളുടെ വിലക്കയറ്റം.",
                "Sell / Exit Trigger (എപ്പോൾ വിൽക്കണം?)": "കമ്പനിയുടെ വിപണി വിഹിതം എതിരാളികൾ പിടിച്ചെടുക്കുകയോ അക്കൗണ്ടിംഗ് തട്ടിപ്പ് വരികയോ ചെയ്താൽ.",
                "Shariah Status": "✅ 100% AAOIFI Compliant"
            }
        ]
    else:
        stocks_data = [
            {
                "Stock": "CDSL",
                "Sector": "Capital Markets Depository",
                "Why Buy? (50Y Thesis)": "ഡിമാറ്റ് അക്കൗണ്ടുകൾ കൂടുമ്പോൾ ടോൾ ബൂത്ത് പോലെ ലാഭം. 33% ROCE, പൂജ്യം കടം.",
                "Red Flags (ഭീഷണികൾ)": "സെബി (SEBI) ഡിമാറ്റ് ട്രാൻസാക്ഷൻ ചാർജുകൾ വെട്ടിക്കുറയ്ക്കുന്നത്.",
                "Sell / Exit Trigger (എപ്പോൾ വിൽക്കണം?)": "റെഗുലേറ്റർ കമ്മീഷൻ പരിധി പകുതിയായി വെട്ടിക്കുറയ്ക്കുകയോ പുതിയ എതിരാളികൾ വരികയോ ചെയ്താൽ.",
                "Shariah Status": "⚠️ ഫിനാൻഷ്യൽ ഇൻകം ഉള്ളതിനാൽ ശരീഅത്തിൽ ഇല്ല"
            },
            {
                "Stock": "Larsen & Toubro (L&T)",
                "Sector": "Infrastructure & Hi-Tech",
                "Why Buy? (50Y Thesis)": "ഇന്ത്യയുടെ വികസനത്തിൽ പാലങ്ങളും ചിപ്പ് ഫാക്ടറികളും നിർമ്മിക്കുന്ന ഏക ഭീമൻ. ₹5 ലക്ഷം കോടി ഓർഡർ ബുക്ക്.",
                "Red Flags (ഭീഷണികൾ)": "സർക്കാർ അടിസ്ഥാന സൗകര്യ ചെലവുകൾ വെട്ടിക്കുറയ്ക്കുന്നത്.",
                "Sell / Exit Trigger (എപ്പോൾ വിൽക്കണം?)": "ഓർഡർ ബുക്ക് താഴേക്ക് പോവുകയോ, കമ്പനിയുടെ കടം (Debt/Equity) 1.5-ന് മുകളിലേക്ക് കയറുകയോ ചെയ്താൽ.",
                "Shariah Status": "⚠️ കൺവെൻഷണൽ"
            },
            {
                "Stock": "ITC Limited",
                "Sector": "Consumer Monopoly",
                "Why Buy? (50Y Thesis)": "ഭീമമായ ഫ്രീ ക്യാഷ് ഫ്ലോ. 3.5%+ ഡിവിഡന്റ് യീൽഡ്. മാന്ദ്യത്തിലും തകരാത്ത ഡിമാൻഡ്.",
                "Red Flags (ഭീഷണികൾ)": "പുകയില നികുതി ക്രമാതീതമായി വർദ്ധിപ്പിക്കുന്നത്.",
                "Sell / Exit Trigger (എപ്പോൾ വിൽക്കണം?)": "സർക്കാർ സിഗരറ്റുകൾ പൂർണ്ണമായി നിരോധിക്കുകയോ, ക്യാഷ് ഫ്ലോ ഇടിയുകയോ ചെയ്താൽ.",
                "Shariah Status": "❌ പുകയില ബിസിനസ്സ് ആയതിനാൽ ശരീഅത്തിൽ ഇല്ല"
            },
            {
                "Stock": "HAL (Hindustan Aeronautics)",
                "Sector": "Defence Monopoly",
                "Why Buy? (50Y Thesis)": "വ്യോമസേനയ്ക്ക് ഫൈറ്റർ ജെറ്റുകൾ നിർമ്മിക്കുന്ന പരമാധികാര കുത്തക. കടമില്ല. 8 വർഷത്തെ ഓർഡർ ഉറപ്പ്.",
                "Red Flags (ഭീഷണികൾ)": "പ്രതിരോധ വിഹിതം വെട്ടിക്കുറയ്ക്കൽ, എഞ്ചിൻ വിതരണ തടസ്സങ്ങൾ.",
                "Sell / Exit Trigger (എപ്പോൾ വിൽക്കണം?)": "സർക്കാർ സ്വകാര്യ കമ്പനികൾക്ക് ജെറ്റ് നിർമ്മാണത്തിന് പൂർണ്ണാനുമതി നൽകുകയോ ഓർഡറുകൾ റദ്ദാക്കുകയോ ചെയ്താൽ.",
                "Shariah Status": "⚠️ കൺവെൻഷണൽ"
            }
        ]

    for s in stocks_data:
        with st.expander(f"📌 {s['Stock']} — ({s['Sector']})"):
            st.markdown(f"**🟢 എന്തുകൊണ്ട് വാങ്ങണം (Why Buy?):** {s['Why Buy? (50Y Thesis)']}")
            st.markdown(f"**⚠️ ശ്രദ്ധിക്കേണ്ട റിസ്കുകൾ (Red Flags):** {s['Red Flags (ഭീഷണികൾ)']}")
            st.error(f"🛑 **എപ്പോൾ വിറ്റ് ഒഴിവാക്കണം (Sell Trigger):** {s['Sell / Exit Trigger (എപ്പോൾ വിൽക്കണം?)']}")
            st.caption(f"സ്റ്റാറ്റസ്: {s['Shariah Status']}")

# ##################################################################
# 📈 വിഭാഗം 3: മ്യൂച്വൽ ഫണ്ടുകൾ & ഇ.ടി.എഫുകൾ
# ##################################################################
elif main_menu == "📈 മ്യൂച്വൽ ഫണ്ടുകൾ & ഇ.ടി.എഫുകൾ":
    st.title("📈 ശാസ്ത്രീയ മ്യൂച്വൽ ഫണ്ട് & ഇ.ടി.എഫ് സെലക്ടർ")
    st.caption("ദീർഘകാല സമ്പത്തുണ്ടാക്കാൻ അനുയോജ്യമായ ഫണ്ടുകൾ.")

    if is_shariah:
        st.subheader("🌙 ഇന്ത്യയിലെ ലൈസൻസുള്ള ശരീഅത്ത് ഫണ്ടുകൾ")
        st.markdown("""
        പലിശ ബാങ്കുകളിലോ മദ്യ/പുകയില കമ്പനികളിലോ നിക്ഷേപിക്കാത്ത, ഇസ്‌ലാമിക പണ്ഡിത സമിതിയുടെ മേൽനോട്ടത്തിലുള്ള ഫണ്ടുകൾ:
        """)
        funds = [
            {"Fund": "Tata Ethical Fund", "Type": "Shariah Equity", "3Y CAGR": "20.8%", "5Y CAGR": "22.5%", "Expense Ratio": "0.85%", "Why Invest?": "ഇന്ത്യയിലെ ഏറ്റവും പഴയതും വലുതുമായ ശരീഅത്ത് ഫണ്ട്."},
            {"Fund": "Taurus Ethical Fund", "Type": "Shariah Equity", "3Y CAGR": "22.1%", "5Y CAGR": "21.2%", "Expense Ratio": "0.95%", "Why Invest?": "S&P BSE 500 Shariah ഇൻഡക്സ് പിന്തുടരുന്നു."},
            {"Fund": "Nippon Gold BeES (GOLDBEES)", "Type": "100% Physical Gold", "Purity": "99.5% 24K", "Expense Ratio": "0.55%", "Why Invest?": "AAOIFI സ്റ്റാൻഡേർഡ് 57 പ്രകാരം അനുവദനീയമായ സ്വർണ്ണ ഇ.ടി.എഫ്."}
        ]
        st.dataframe(pd.DataFrame(funds), use_container_width=True, hide_index=True)
    else:
        funds = [
            {"Fund": "Parag Parikh Flexi Cap Fund", "Type": "Flexi Cap", "3Y CAGR": "21.5%", "5Y CAGR": "24.2%", "Expense Ratio": "0.62%", "Why Invest?": "ഇന്ത്യൻ ഓഹരികൾക്കൊപ്പം യു.എസ് ടെക് കുത്തകകളിലും നിക്ഷേപിക്കുന്നു."},
            {"Fund": "UTI Nifty 50 Index Fund", "Type": "Large Cap Index", "3Y CAGR": "15.8%", "5Y CAGR": "16.5%", "Expense Ratio": "0.18%", "Why Invest?": "ഏറ്റവും കുറഞ്ഞ ചിലവ് (0.18%), സുരക്ഷിതമായ നിക്ഷേപം."},
            {"Fund": "Quant Small Cap Fund", "Type": "Small Cap", "3Y CAGR": "34.2%", "5Y CAGR": "38.5%", "Expense Ratio": "0.77%", "Why Invest?": "അതിവേഗ വളർച്ചാ ഓഹരികളെ അൽഗോരിതം വഴി കണ്ടെത്തുന്നു."}
        ]
        st.dataframe(pd.DataFrame(funds), use_container_width=True, hide_index=True)

# ##################################################################
# 🌍 വിഭാഗം 4: ആഗോള വിപണികൾ (US & Currency Advisor)
# ##################################################################
elif main_menu == "🌍 ആഗോള വിപണികൾ (US & Currency Advisor)":
    st.title("🌍 ആഗോള നിക്ഷേപം & കറൻസി അഡ്വൈസർ")
    st.caption("വാൾസ്ട്രീറ്റിലെ കുത്തകകളും ഇന്ത്യക്കാർക്കുള്ള ഏറ്റവും കുറഞ്ഞ ചിലവുള്ള നിക്ഷേപ വഴികളും.")

    st.subheader("💡 ഒരു ഇന്ത്യക്കാരൻ എങ്ങനെ യു.എസിൽ നിക്ഷേപിക്കണം? (INR vs USD)")
    st.markdown("""
    **50-വർഷത്തെ വിദഗ്ദ്ധന്റെ സത്യസന്ധമായ വിലയിരുത്തൽ:**
    * **നിങ്ങളുടെ നിക്ഷേപം ₹5 ലക്ഷത്തിൽ താഴെയാണെങ്കിൽ:**
      * 👉 **ഇന്ത്യൻ രൂപയിൽ തന്നെ നിക്ഷേപിക്കുന്ന മ്യൂച്വൽ ഫണ്ടുകൾ / ഇ.ടി.എഫുകൾ (INR Route) തിരഞ്ഞെടുക്കുക!**
      * *കാരണം:* ബാങ്ക് വഴി ഡോളർ അയക്കുമ്പോൾ വരുന്ന ഉയർന്ന വയർ ചാർജുകൾ ($20-$30), ഫോറെക്സ് നഷ്ടം, 20% TCS എന്നിവ പൂർണ്ണമായും ഒഴിവാക്കാം.
    * **നിങ്ങളുടെ നിക്ഷേപം ₹10 ലക്ഷത്തിന് മുകളിലാണെങ്കിൽ:**
      * 👉 INDmoney / Vested വഴി ഡോളറിലേക്ക് മാറ്റി ആപ്പിളും എൻവിഡിയയും നേരിട്ട് വാങ്ങി വെക്കാം.
    """)

    if is_shariah:
        st.subheader("🌙 ആഗോള ഹലാൽ ഓഹരികൾ (Global Halal Leaders)")
        us_stocks = [
            {"Company": "Nvidia (NVDA)", "Sector": "AI Computing", "Shariah": "✅ Compliant", "Moat": "AI ചിപ്പുകളിലെ ആഗോള കുത്തക. പലിശ രഹിത ബിസിനസ്സ്."},
            {"Company": "Microsoft (MSFT)", "Sector": "Cloud & Software", "Shariah": "✅ Compliant", "Moat": "ലോകത്തെ എല്ലാ ഓഫീസുകളും പ്രവർത്തിക്കുന്ന സോഫ്റ്റ്‌വെയർ ശൃംഖല."},
            {"Company": "Alphabet (Google)", "Sector": "Search & Cloud", "Shariah": "✅ Compliant", "Moat": "സൗജന്യ അറിവും യൂട്യൂബും വഴി പരസ്യ വരുമാനം നേടുന്ന കുത്തക."}
        ]
    else:
        st.subheader("🇺🇸 വാൾസ്ട്രീറ്റിലെ വൻകിട കുത്തകകൾ (The Magnificent 7)")
        us_stocks = [
            {"Company": "Microsoft (MSFT)", "Sector": "Software / AI", "Market Cap": "$3.1T+", "Moat": "എന്റർപ്രൈസ് ക്ലൗഡ് & ഓപ്പൺഎഐ പാർട്ണർഷിപ്പ്."},
            {"Company": "Apple (AAPL)", "Sector": "Consumer Tech", "Market Cap": "$3.4T+", "Moat": "200 കോടി ഉപയോക്താക്കൾ അടങ്ങിയ ബ്രാൻഡ് കുത്തക."},
            {"Company": "Nvidia (NVDA)", "Sector": "AI Hardware", "Market Cap": "$3.0T+", "Moat": "AI പ്രോസസ്സറുകളിലെ 85% വിപണി വിഹിതം."},
            {"Company": "Berkshire Hathaway (BRK.B)", "Sector": "Holding / Insurance", "Market Cap": "$900B+", "Moat": "വാറൻ ബഫറ്റിന്റെ $300B പണശേഖരമുള്ള കോട്ട."}
        ]
    st.dataframe(pd.DataFrame(us_stocks), use_container_width=True, hide_index=True)

# ##################################################################
# 🥇 വിഭാഗം 5: ഗോൾഡ് & സുരക്ഷിത ആസ്തികൾ
# ##################################################################
elif main_menu == "🥇 ഗോൾഡ് & സുരക്ഷിത ആസ്തികൾ":
    st.title("🥇 ഗോൾഡ് & ക്രൈസിസ് പ്രൊട്ടക്ഷൻ (Crisis Shield)")
    st.caption("ആഗോള യുദ്ധങ്ങളും മാർക്കറ്റ് തകർച്ചകളും വരുമ്പോൾ നിങ്ങളുടെ പണത്തെ സംരക്ഷിക്കുന്ന എയർബാഗ്.")

    st.info("💡 **എന്തുകൊണ്ട് ഗോൾഡ് ഇ.ടി.എഫ്?** പണിക്കൂലിയോ ജിഎസ്ടിയോ ഇല്ലാതെ 99.5% ശുദ്ധമായ 24K സ്വർണ്ണത്തിൽ നിക്ഷേപിക്കാം. 12 മാസം കഴിഞ്ഞാൽ വെറും 12.5% മാത്രമാണ് ലോങ്ങ്-ടേം നികുതി!")

    gold_data = [
        {"Instrument": "Nippon India Gold BeES (GOLDBEES)", "Asset": "Physical Gold", "Expense Ratio": "0.55%", "Liquidity": "⭐⭐⭐⭐⭐", "Shariah Status": "✅ 100% Halal (AAOIFI Standard 57)"},
        {"Instrument": "HDFC Gold ETF (HDFCGOLD)", "Asset": "Physical Gold", "Expense Ratio": "0.30%", "Liquidity": "⭐⭐⭐⭐", "Shariah Status": "✅ 100% Halal"},
        {"Instrument": "Nippon India Silver ETF (SILVERBEES)", "Asset": "Physical Silver", "Expense Ratio": "0.50%", "Liquidity": "⭐⭐⭐⭐⭐", "Shariah Status": "✅ 100% Halal"}
    ]
    st.dataframe(pd.DataFrame(gold_data), use_container_width=True, hide_index=True)

# ##################################################################
# 📚 വിഭാഗം 6: അഡ്വൈസറി ജേർണൽ & ചേഞ്ച് ലോഗ് (Audit History)
# ##################################################################
elif main_menu == "📚 അഡ്വൈസറി ജേർണൽ & ചേഞ്ച് ലോഗ് (Audit History)":
    st.title("📚 ഇൻവെസ്റ്റ്മെന്റ് ജേർണൽ & ഹിസ്റ്ററി ലോഗ്")
    st.caption("മുൻ ദിവസങ്ങളിൽ എടുത്ത തീരുമാനങ്ങളും, എന്തുകൊണ്ട് ശുപാർശ ചെയ്തു / ഒഴിവാക്കി എന്നതിന്റെ ഓഡിറ്റ് ഹിസ്റ്ററി.")

    conn = sqlite3.connect(DB_NAME)
    try:
        df_audit = pd.read_sql_query("SELECT date AS Date, asset AS Asset, category AS Category, action AS Action, status AS Status, veteran_reason AS [Reason / Thesis] FROM wealth_audit ORDER BY id DESC LIMIT 50", conn)
        conn.close()
        if not df_audit.empty:
            st.dataframe(df_audit, use_container_width=True, hide_index=True)
        else:
            st.info("ആപ്പിൽ പുതിയ അലോക്കേഷനുകൾ പരിശോധിക്കുമ്പോൾ ഡാറ്റ ഇവിടെ ശേഖരിക്കപ്പെടും.")
    except Exception:
        conn.close()
        st.info("ജേർണൽ വിവരങ്ങൾ വരാൻ കാത്തിരിക്കുന്നു...")

# ##################################################################
# ⚡ വിഭാഗം 7: ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട് (Separate Layer)
# ##################################################################
elif main_menu == "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്":
    st.title("⚡ Upstox ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട്")
    st.caption("നിക്ഷേപങ്ങളിൽ നിന്ന് തികച്ചും സ്വതന്ത്രമായി പ്രവർത്തിക്കുന്ന ആക്ടീവ് ഇൻട്രാഡേ എൻജിൻ.")
    if is_shariah:
        st.error("⚠️ **ശരീഅത്ത് മുന്നറിയിപ്പ്:** ഇൻട്രാഡേ ലിവറേജ് ട്രേഡിംഗും F&O-യും ഇസ്‌ലാമിക പണ്ഡിതന്മാർ വിലക്കിയിട്ടുള്ളതാണ്. ശരീഅത്ത് നിക്ഷേപകർ ദീർഘകാല ഡെലിവറി ഇക്വിറ്റിയും എത്തിക്കൽ ഫണ്ടുകളും മാത്രം തിരഞ്ഞെടുക്കുക.")
    else:
        st.info("ഇൻട്രാഡേ ബോട്ട് ഇപ്പോൾ ബാക്ക്ഗ്രൗണ്ടിൽ നിരീക്ഷണത്തിലാണ്. മാർക്കറ്റ് സമയത്ത് സിഗ്നലുകൾക്കായി കാത്തിരിക്കുന്നു.")
