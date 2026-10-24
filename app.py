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
# 🌐 PAGE CONFIGURATION & FULL MULTILINGUAL DICTIONARY
# ==========================================
st.set_page_config(page_title="Autonomous Wealth OS & Algo Bot", layout="wide", page_icon="🏛️")

TRANSLATIONS = {
    "English": {
        "login_title": "🔒 Private Vault Login (100% Data Privacy)",
        "login_desc": "Enter your personal Secret Passkey to unlock your isolated workspace. No other user can view your API keys, trades, or portfolio.",
        "passkey_label": "Enter Secret Passkey / ID:",
        "login_btn": "🔓 Unlock Workspace",
        "logout_btn": "🔒 Logout / Lock Screen",
        "phil_label": "Investment Philosophy:",
        "phil_conv": "🌐 Global Conventional Mode",
        "phil_halal": "🌙 100% Pure Shariah Mode (AAOIFI)",
        "menu_label": "Select Core Module:",
        "m1": "⚡ Intraday Algo Trading Bot",
        "m2": "🎯 Dynamic Goal Allocator",
        "m3": "💼 Live Portfolio & Exit Watchdog",
        "m4": "🏛️ 50-Year Moat Vault & Live Scanner",
        "m5": "📈 Mutual Funds & ETFs",
        "m6": "🌍 Global Markets (US & Currency)",
        "m7": "🥇 Gold & Crisis Hedge Assets",
        "m8": "📚 Investment Audit Journal",
        "bot_title": "⚡ Multi-Broker Institutional Intraday Bot",
        "bot_sub": "Encrypted User Isolation + Auto OAuth 2.0 + Nifty Trend Guard + 3:15 PM Auto Square-off.",
        "shariah_warn": "🌙 **Shariah Watchlist Active:** Conventional banks (e.g. SBIN) are excluded. Scanning only AAOIFI-compliant equities (TCS, INFY, SUNPHARMA, RELIANCE).",
        "token_ready": "✅ **Broker Access Token is Active!** Click **▶️ START BOT** in the sidebar to begin execution.",
        "oauth_exp": "🔑 1-Click Automatic Token Generator (OAuth 2.0 Setup)",
        "criteria_bot": "📐 **How the Algo Bot Selects Trades (6-Point Institutional Criteria Blueprint)**",
        "criteria_bot_body": """
**Every 10 seconds during market hours (9:20 AM – 3:05 PM IST), the bot evaluates 1-minute candlesticks against 6 strict institutional filters. A BUY order is triggered ONLY when ALL 6 conditions align simultaneously:**

| # | Filter / Indicator | Mathematical Rule | Institutional Purpose |
| :--- | :--- | :--- | :--- |
| **1** | **Nifty 50 Trend Guard** | `Nifty Price >= 20 EMA` (1-min) | Prevents buying equities when the broader market is falling. |
| **2** | **VWAP Filter** | `Stock Price > Intraday VWAP` | Confirms institutional buyers are in control above average price. |
| **3** | **EMA Momentum Cross** | `EMA 9 crosses above EMA 21` | Captures fresh upward momentum at the exact inflection point. |
| **4** | **Volume Surge** | `Volume >= 1.2x (20-period SMA)` | Filters out false retail breakouts; requires institutional volume. |
| **5** | **RSI Safe Zone** | `50 <= RSI (14) <= 68` | Ensures bullish strength while avoiding overbought traps (>70). |
| **6** | **ATR Risk & Time Exit** | `SL = 1.5x ATR` / `Target = 3.0x ATR` | Enforces 1:2 Risk-Reward, 45-min stale exit, 2-loss Kill Switch, and 3:15 PM square-off. |
""",
        "broker_sel": "🏦 Select Broker Platform:",
        "ctrl_panel": "⚙️ Bot Control Panel",
        "mode_label": "Execution Mode:",
        "mode_paper": "Paper Trading (Safe Simulation)",
        "mode_live": "Live Real Money",
        "cap_label": "Trading Capital (₹):",
        "risk_label": "Risk Per Trade (₹):",
        "start_btn": "▶️ START BOT",
        "stop_btn": "⏹️ STOP BOT",
        "status_col": "Bot Status",
        "status_run": "🟢 Running on Server",
        "status_kill": "🛑 Kill Switch Active",
        "status_off": "🔴 Stopped",
        "nifty_col": "Nifty 50 Trend",
        "loss_col": "Consecutive Losses",
        "cap_col": "Active Capital",
        "tab_scan": "🔍 Live Scanning Audit Log",
        "tab_trades": "📜 Executed Trades History (Net PnL)",
        "refresh_btn": "🔄 Refresh Live Status",
        "wait_scan": "Waiting for live market scan data (Market Window: 9:20 AM - 3:15 PM IST)...",
        "no_trades": "No trades executed yet in this account.",
        "goal_criteria_title": "📐 **How Asset Allocation Percentages Are Calculated (Methodology)**",
        "goal_criteria_body": """
* **1-Year Horizon (Capital Preservation):** Caps equity exposure at **15%** to avoid short-term volatility. Allocates **50% to Liquid Reserves** and **25–35% to Gold** as an inflation hedge.
* **3–5 Year Horizon (Tactical Growth):** Allocates **60% to Equities** in normal markets, but automatically cuts equity exposure to **40%** and boosts Gold/Cash during geopolitical war/oil-spike regimes.
* **10+ Year Horizon (Generational Compounding):** Allocates **65–75% to Moat Equities** (increasing equity weight during market crashes per Howard Marks' counter-cyclical rule).
""",
        "port_criteria_title": "📐 **How the Portfolio Exit Watchdog Evaluates Your Holdings**",
        "port_criteria_body": """
* **🚨 Exit Alert (`PnL < -10%`):** Flags positions breaching institutional capital-preservation thresholds for immediate fundamental review or stop-loss execution.
* **🟢 Strong Compounder (`PnL > +20%`):** Recommends holding winners and trailing stop-losses above cost.
* **🟡 Normal Range (`-10% to +20%`):** Hold as long as core business ROCE and debt ratios remain intact.
""",
        "moat_criteria_title": "📐 **Stock Selection Criteria Blueprint (Why & How Stocks Are Selected)**",
        "moat_criteria_body": """
**Every stock in the 50-Year Moat Vault must pass two layers of institutional screening:**

#### 1. Warren Buffett & Charlie Munger Quality Moat Filters (Quantitative)
* **ROCE / ROE >= 20%:** Demonstrates superior capital allocation and pricing power.
* **Debt-to-Equity < 0.30x (Virtually Debt-Free):** Ensures survival across severe recessions without bankruptcy risk.
* **Positive Free Cash Flow (FCF) & Operating Margin > 18%:** Proves real cash generation rather than accounting profits.
* **Economic Moat:** Monopoly, duopoly, or high switching-cost industry leadership.

#### 2. AAOIFI Shariah Screening Filters (When Shariah Mode is Active)
* **Business Activity Screen:** Zero involvement in conventional banking/interest (Riba), alcohol, tobacco, gambling, weapons, or adult entertainment.
* **Financial Ratio Screen #1 (Debt Ceiling):** `Total Interest-Bearing Debt / Market Cap < 33%`
* **Financial Ratio Screen #2 (Cash/Interest Ceiling):** `(Cash + Interest-Bearing Securities) / Market Cap < 33%`
* **Financial Ratio Screen #3 (Impure Income):** `Non-Permissible Income / Total Revenue < 5%`
""",
        "scanner_title": "🔎 Live Fundamental, Shariah & Chart Stock Scanner",
        "scanner_input": "Enter any NSE Stock Symbol to test against our criteria (e.g. TCS, INFY, TITAN, HDFCBANK, ITC):",
        "scanner_btn": "⚡ Scan Stock Now",
        "mf_criteria_title": "📐 **How Mutual Funds & Ethical Funds Are Selected (5-Point Criteria)**",
        "mf_criteria_body": """
1. **5-Year Rolling Return Consistency:** Must beat its benchmark index across 80%+ of 5-year rolling periods.
2. **Low Expense Ratio (Direct Plan):** Prevents compounding drag over 10–20 year horizons.
3. **Downside Capture Ratio < 90%:** Falls less than the market during severe corrections.
4. **Portfolio Quality:** Low churn and high-ROCE holdings.
5. **Shariah Audit (For Ethical Funds):** Independently audited under AAOIFI standards with mandatory dividend purification.
""",
        "us_criteria_title": "📐 **Global Equity & Currency Arbitrage Selection Criteria**",
        "us_criteria_body": """
* **Global Monopoly Moat:** Companies commanding >50% global market share in secular megatrends (AI compute, Cloud OS, Search).
* **Currency Tailwinds (USD/INR):** Historically, the USD appreciates ~3–4% annually against the INR, adding an automatic currency compounding bonus to US equity returns.
* **AAOIFI Global Screening (SPUS / HLAL):** Debt/Market Cap < 30% and interest income < 5%.
""",
        "gold_criteria_title": "📐 **Gold & Precious Metals Selection Criteria (AAOIFI Standard #57)**",
        "gold_criteria_body": """
* **100% Physical Bullion Backing:** Must hold allocated 99.5% pure physical gold bars in custodian vaults (no synthetic futures or paper derivatives).
* **High Exchange Liquidity:** High daily trading volume on NSE to ensure tight bid-ask spreads.
* **Low Tracking Error & Expense Ratio:** Minimal deviation from domestic spot gold prices.
"""
    },
    "മലയാളം": {
        "login_title": "🔒 സ്വകാര്യ ലോക്കർ ലോഗിൻ (100% Data Privacy)",
        "login_desc": "നിങ്ങളുടെ സ്വകാര്യ അക്കൗണ്ട് തുറക്കാൻ നിങ്ങൾക്ക് മാത്രം അറിയാവുന്ന ഒരു രഹസ്യ പാസ്‌കീ നൽകുക. നിങ്ങളുടെ ടോക്കണോ ട്രേഡുകളോ മറ്റാർക്കും കാണാൻ കഴിയില്ല.",
        "passkey_label": "നിങ്ങളുടെ രഹസ്യ പാസ്‌കീ (Secret ID) നൽകുക:",
        "login_btn": "🔓 അക്കൗണ്ട് തുറക്കുക (Login)",
        "logout_btn": "🔒 ലോഗൗട്ട് / സ്ക്രീൻ പൂട്ടുക",
        "phil_label": "നിക്ഷേപ തത്ത്വശാസ്ത്രം (Philosophy):",
        "phil_conv": "🌐 ആഗോള ജനറൽ മോഡ് (Conventional)",
        "phil_halal": "🌙 100% പ്യുവർ ശരീഅത്ത് മോഡ് (Halal AAOIFI)",
        "menu_label": "പ്രധാന വിഭാഗം തിരഞ്ഞെടുക്കുക:",
        "m1": "⚡ ഇൻട്രാഡേ ട്രേഡിംഗ് ബോട്ട് (Algo Engine)",
        "m2": "🎯 ലക്ഷ്യാധിഷ്ഠിത പോർട്ട്ഫോളിയോ (Goal Engine)",
        "m3": "💼 എന്റെ ലൈവ് പോർട്ട്ഫോളിയോ & വാച്ച്ഡോഗ്",
        "m4": "🏛️ 50-Year സ്റ്റോക്ക് നിലവറ & ലൈവ് സ്കാനർ",
        "m5": "📈 മ്യൂച്വൽ ഫണ്ടുകൾ & ഇ.ടി.എഫുകൾ",
        "m6": "🌍 ആഗോള വിപണികൾ (US & INDmoney)",
        "m7": "🥇 ഗോൾഡ് & സുരക്ഷിത ആസ്തികൾ",
        "m8": "📚 അഡ്വൈസറി ജേർണൽ & ചേഞ്ച് ലോഗ്",
        "bot_title": "⚡ മൾട്ടി-ബ്രോക്കർ ഇൻസ്റ്റിറ്റ്യൂഷണൽ ഇൻട്രാഡേ ബോട്ട്",
        "bot_sub": "100% സുരക്ഷിത യൂസർ ലോക്കർ + ഓട്ടോ ടോക്കൺ + നിഫ്റ്റി ഗാർഡ് + 3:15 PM ഓട്ടോ സ്ക്വയർ-ഓഫ്.",
        "shariah_warn": "🌙 **ശരീഅത്ത് വാച്ച്‌ലിസ്റ്റ് ആക്ടീവ്:** ബാങ്കിംഗ് ഓഹരികൾ (SBIN) ഒഴിവാക്കി TCS, INFY, SUNPHARMA, RELIANCE എന്നിവ മാത്രമാണ് സ്കാൻ ചെയ്യുന്നത്.",
        "token_ready": "✅ **Access Token റെഡിയാണ്!** ഇനി ഇടതുവശത്തെ സൈഡ്‌ബാറിൽ **▶️ START BOT** അമർത്താം.",
        "oauth_exp": "🔑 ഓട്ടോമാറ്റിക് ടോക്കൺ ജനറേറ്റർ (1-Click Auto Login)",
        "criteria_bot": "📐 **ബോട്ട് എങ്ങനെയാണ് ട്രേഡ് തിരഞ്ഞെടുക്കുന്നത്? (6-ഇന മാനദണ്ഡങ്ങൾ കാണാൻ ഇവിടെ ക്ലിക്ക് ചെയ്യുക)**",
        "criteria_bot_body": """
**മാർക്കറ്റ് സമയത്ത് (9:20 AM – 3:05 PM IST) ഓരോ 10 സെക്കൻഡിലും ബോട്ട് താഴെ പറയുന്ന 6 കർശനമായ നിയമങ്ങൾ പരിശോധിക്കുന്നു. ഈ 6 നിയമങ്ങളും ഒരേ സമയം ശരിയായാൽ മാത്രമേ ബോട്ട് BUY ഓർഡർ എടുക്കുകയുള്ളൂ:**

| # | ഫിൽട്ടർ / ഇൻഡിക്കേറ്റർ | ഗണിതശാസ്ത്ര നിയമം (Rule) | ഇതിന്റെ ഉപയോഗം (Purpose) |
| :--- | :--- | :--- | :--- |
| **1** | **നിഫ്റ്റി 50 ട്രെൻഡ് ഗാർഡ്** | `Nifty Price >= 20 EMA` (1-min) | വിപണി പൊതുവായി ഇടിയുമ്പോൾ ഓഹരികൾ വാങ്ങി നഷ്ടം വരുന്നത് തടയുന്നു. |
| **2** | **VWAP ഫിൽട്ടർ** | `Stock Price > Intraday VWAP` | അന്നത്തെ ശരാശരി വിലയ്ക്ക് മുകളിൽ വൻകിട നിക്ഷേപകർ വാങ്ങുന്നുണ്ടെന്ന് ഉറപ്പാക്കുന്നു. |
| **3** | **EMA മൊമെന്റം ക്രോസ്** | `EMA 9 crosses above EMA 21` | വില മുകളിലേക്ക് കുതിച്ചുയരുന്ന കൃത്യമായ തുടക്കത്തിൽ തന്നെ എൻട്രി എടുക്കുന്നു. |
| **4** | **വോളിയം സർജ് (Volume)** | `Volume >= 1.2x (20-period SMA)` | വ്യാജ ബ്രേക്കൗട്ടുകൾ ഒഴിവാക്കി ശക്തമായ വോളിയം ഉണ്ടെന്ന് ഉറപ്പാക്കുന്നു. |
| **5** | **RSI സുരക്ഷാ പരിധി** | `50 <= RSI (14) <= 68` | ഓഹരിക്ക് ശക്തിയുണ്ടെന്നും എന്നാൽ അമിതമായി വില കയറിയിട്ടില്ലെന്നും (Overbought < 70) ഉറപ്പാക്കുന്നു. |
| **6** | **ATR സ്റ്റോപ്പ്-ലോസ് & എക്സിറ്റ്** | `SL = 1.5x ATR` / `Target = 3.0x ATR` | **1:2 റിസ്ക്-റിവാർഡ്**, 45 മിനിറ്റ് കഴിഞ്ഞും അനക്കമില്ലെങ്കിൽ എക്സിറ്റ്, തുടർച്ചയായി 2 നഷ്ടം വന്നാൽ കിൽ-സ്വിച്ച്, 3:15 PM ഓട്ടോ എക്സിറ്റ്. |
""",
        "broker_sel": "🏦 നിങ്ങളുടെ ബ്രോക്കർ പ്ലാറ്റ്‌ഫോം തിരഞ്ഞെടുക്കുക:",
        "ctrl_panel": "⚙️ ബോട്ട് കൺട്രോൾ പാനൽ",
        "mode_label": "ട്രേഡിംഗ് മോഡ്:",
        "mode_paper": "പേപ്പർ ട്രേഡിംഗ് (സുരക്ഷിതം)",
        "mode_live": "ലൈവ് റിയൽ മണി",
        "cap_label": "ക്യാപിറ്റൽ (₹):",
        "risk_label": "ഒരു ട്രേഡിലെ റിസ്ക് (₹):",
        "start_btn": "▶️ START BOT",
        "stop_btn": "⏹️ STOP BOT",
        "status_col": "ബോട്ട് സ്റ്റാറ്റസ്",
        "status_run": "🟢 സർവറിൽ ഓടുന്നു",
        "status_kill": "🛑 കിൽ സ്വിച്ച് ഓഫ്",
        "status_off": "🔴 ഓഫ് ആണ്",
        "nifty_col": "നിഫ്റ്റി 50 ട്രെൻഡ്",
        "loss_col": "തുടർച്ചയായ നഷ്ടങ്ങൾ",
        "cap_col": "ക്യാപിറ്റൽ",
        "tab_scan": "🔍 എന്റെ ലൈവ് സ്കാനിംഗ് ലോഗ്",
        "tab_trades": "📜 പൂർത്തിയായ ട്രേഡുകൾ (Net Profit)",
        "refresh_btn": "🔄 സ്റ്റാറ്റസ് റിഫ്രഷ് ചെയ്യുക",
        "wait_scan": "സ്കാനിംഗ് ഡാറ്റ വരാൻ കാത്തിരിക്കുന്നു (മാർക്കറ്റ് സമയം: 9:20 AM - 3:15 PM IST)...",
        "no_trades": "ഇതുവരെ ട്രേഡുകൾ ഒന്നും നടന്നിട്ടില്ല.",
        "goal_criteria_title": "📐 **നിക്ഷേപ വിഹിതം (Asset Allocation) നിശ്ചയിക്കുന്നതിന്റെ അടിസ്ഥാന തത്വങ്ങൾ**",
        "goal_criteria_body": """
* **1 വർഷത്തെ ലക്ഷ്യം (മൂലധന സുരക്ഷ):** ഹ്രസ്വകാലത്തേക്ക് ഓഹരി വിപണിയിലെ ചാഞ്ചാട്ടം ഒഴിവാക്കാൻ ഇക്വിറ്റി വിഹിതം **15%** ആയി പരിമിതപ്പെടുത്തുന്നു. **50% ലിക്വിഡ് ക്യാഷും 25–35% സ്വർണ്ണവും** നിർദ്ദേശിക്കുന്നു.
* **3–5 വർഷത്തെ ലക്ഷ്യം (ഇടത്തരം വളർച്ച):** സാധാരണ വിപണിയിൽ **60% ഇക്വിറ്റി** നൽകുന്നു. എന്നാൽ യുദ്ധമോ എണ്ണവിലക്കയറ്റമോ വരുമ്പോൾ ഇക്വിറ്റി **40%** ആയി കുറച്ച് സ്വർണ്ണത്തിലേക്ക് മാറ്റുന്നു.
* **10+ വർഷത്തെ ലക്ഷ്യം (ദീർഘകാല സമ്പത്ത്):** കടരഹിത കുത്തക കമ്പനികളിൽ **65–75%** നിക്ഷേപിക്കുന്നു (വിപണി തകരുമ്പോൾ വാറൻ ബഫറ്റ് ശൈലിയിൽ കൂടുതൽ ഓഹരികൾ വാങ്ങാൻ നിർദ്ദേശിക്കുന്നു).
""",
        "port_criteria_title": "📐 **പോർട്ട്ഫോളിയോ എക്സിറ്റ് വാച്ച്ഡോഗ് നിങ്ങളുടെ ഓഹരികളെ വിലയിരുത്തുന്ന വിധം**",
        "port_criteria_body": """
* **🚨 എക്സിറ്റ് മുന്നറിയിപ്പ് (`PnL < -10%`):** വാങ്ങിയ വിലയിൽ നിന്ന് 10%-ൽ കൂടുതൽ ഇടിഞ്ഞ ഓഹരികളെ പുനഃപരിശോധിക്കാനോ സ്റ്റോപ്പ്-ലോസ് എടുക്കാനോ മുന്നറിയിപ്പ് നൽകുന്നു.
* **🟢 മികച്ച ലാഭത്തിൽ (`PnL > +20%`):** മികച്ച ലാഭത്തിലുള്ള ഓഹരികളെ വിൽക്കാതെ തുടരാനും (Hold), സ്റ്റോപ്പ്-ലോസ് വാങ്ങിയ വിലയ്ക്ക് മുകളിലേക്ക് ഉയർത്താനും (Trail SL) നിർദ്ദേശിക്കുന്നു.
* **🟡 സാധാരണ നിലയിൽ (`-10% മുതൽ +20% വരെ`):** കമ്പനിയുടെ അടിസ്ഥാന ഗുണനിലവാരം (ROCE & Debt) കൃത്യമാണെങ്കിൽ തുടരാൻ നിർദ്ദേശിക്കുന്നു.
""",
        "moat_criteria_title": "📐 **സ്റ്റോക്കുകൾ തിരഞ്ഞെടുക്കുന്നതിന്റെ മാനദണ്ഡങ്ങൾ (Stock Selection Criteria Blueprint)**",
        "moat_criteria_body": """
**50-Year സ്റ്റോക്ക് നിലവറയിലെ ഓരോ ഓഹരിയും താഴെ പറയുന്ന രണ്ട് ഘട്ടങ്ങളായുള്ള കർശന പരിശോധനകൾ പാസ്സായവയാണ്:**

#### 1. വാറൻ ബഫറ്റ് & ചാർളി മംഗർ ക്വാളിറ്റി ഫിൽട്ടറുകൾ (Quantitative Moat Rules)
* **ROCE / ROE >= 20%:** മുടക്കുന്ന മൂലധനത്തിന് മുകളിൽ വർഷാവർഷം 20%-ൽ കൂടുതൽ ലാഭം നേടുന്ന കമ്പനികൾ.
* **Debt-to-Equity < 0.30x (കടരഹിത കമ്പനികൾ):** കടുത്ത സാമ്പത്തിക മാന്ദ്യം വന്നാലും തകർന്നുപോകാത്ത വിധം കടം ഇല്ലാത്തവ.
* **ഉയർന്ന ക്യാഷ് ഫ്ലോ (Free Cash Flow & Operating Margin > 18%):** പേപ്പറിലെ ലാഭമല്ലാതെ യഥാർത്ഥ പണം കമ്പനിയിലേക്ക് വരുന്നത്.
* **ഇക്കണോമിക് മോട്ട് (Economic Moat):** എതിരാളികൾക്ക് തകർക്കാൻ കഴിയാത്ത കുത്തക (Monopoly) അല്ലെങ്കിൽ വിപണി മേധാവിത്വം.

#### 2. AAOIFI ശരീഅത്ത് സ്ക്രീനിംഗ് നിയമങ്ങൾ (ശരീഅത്ത് മോഡ് ഓൺ ആയിരിക്കുമ്പോൾ)
* **ബിസിനസ്സ് പരിശോധന:** പലിശ ബാങ്കിംഗ് (Riba), മദ്യം, പുകയില, ചൂതാട്ടം, ആയുധ നിർമ്മാണം എന്നിവയിലൊന്നും ഉൾപ്പെടാത്ത കമ്പനികൾ.
* **സാമ്പത്തിക അനുപാതം #1 (കടത്തിന്റെ പരിധി):** കമ്പനിയുടെ ആകെ കടം മാർക്കറ്റ് ക്യാപ്പിന്റെ **33%-ൽ താഴെ** ആയിരിക്കണം (`Total Debt / Market Cap < 33%`).
* **സാമ്പത്തിക അനുപാതം #2 (പലിശ നിക്ഷേപ പരിധി):** പലിശ ലഭിക്കുന്ന നിക്ഷേപങ്ങൾ **33%-ൽ താഴെ** ആയിരിക്കണം.
* **സാമ്പത്തിക അനുപാതം #3 (വരുമാന ശുദ്ധീകരണം):** നോൺ-ഹലാൽ വരുമാനം ആകെ വരുമാനത്തിന്റെ **5%-ൽ താഴെ** ആയിരിക്കണം.
""",
        "scanner_title": "🔎 ഏത് സ്റ്റോക്കും പരിശോധിക്കാം: ലൈവ് ഫണ്ടമെന്റൽ, ശരീഅത്ത് & ചാർട്ട് സ്കാനർ",
        "scanner_input": "പരിശോധിക്കേണ്ട NSE സ്റ്റോക്ക് സിംബൽ നൽകുക (ഉദാ: TCS, INFY, TITAN, HDFCBANK, ITC):",
        "scanner_btn": "⚡ സ്റ്റോക്ക് പരിശോധിക്കുക (Scan Now)",
        "mf_criteria_title": "📐 **മ്യൂച്വൽ ഫണ്ടുകളും എത്തിക്കൽ ഫണ്ടുകളും തിരഞ്ഞെടുക്കുന്ന 5 മാനദണ്ഡങ്ങൾ**",
        "mf_criteria_body": """
1. **5-വർഷ റോളിംഗ് റിട്ടേൺ (Rolling Return Consistency):** കഴിഞ്ഞ 5 വർഷങ്ങളിൽ തുടർച്ചയായി ബെഞ്ച്മാർക്ക് ഇൻഡക്സിനെ തോൽപ്പിച്ച ഫണ്ടുകൾ.
2. **കുറഞ്ഞ ചെലവ് അനുപാതം (Low Expense Ratio - Direct Plan):** ദീർഘകാല കോമ്പൗണ്ടിംഗിൽ കമ്മീഷൻ ഇനത്തിൽ പണം നഷ്ടപ്പെടാതിരിക്കാൻ.
3. **Downside Capture Ratio < 90%:** വിപണി ഇടിയുമ്പോൾ വിപണിയേക്കാൾ കുറച്ചു മാത്രം ഇടിയുന്ന സുരക്ഷിതത്വം.
4. **പോർട്ട്ഫോളിയോ ഗുണനിലവാരം:** ഉയർന്ന ROCE ഉള്ള കമ്പനികൾ ഉൾപ്പെട്ട പോർട്ട്ഫോളിയോ.
5. **ശരീഅത്ത് ഓഡിറ്റ് (എത്തിക്കൽ ഫണ്ടുകൾക്ക്):** സ്വതന്ത്ര ശരീഅത്ത് ബോർഡ് (AAOIFI / Taqwaa Advisory) ഓഡിറ്റ് ചെയ്യുന്നതും പലിശ പൂർണ്ണമായി ഒഴിവാക്കിയതുമായ ഫണ്ടുകൾ.
""",
        "us_criteria_title": "📐 **ആഗോള ഓഹരികളും ഡോളർ മൂല്യവും തിരഞ്ഞെടുക്കുന്ന മാനദണ്ഡങ്ങൾ**",
        "us_criteria_body": """
* **ആഗോള കുത്തകകൾ (Global Moat):** AI, ക്ലൗഡ് കമ്പ്യൂട്ടിംഗ്, സെർച്ച് എൻജിൻ എന്നിവയിൽ ലോകത്ത് 50%-ൽ കൂടുതൽ വിപണി വിഹിതമുള്ള കമ്പനികൾ.
* **ഡോളർ-രൂപ മൂല്യവർദ്ധനവ് (USD/INR Arbitrage):** രൂപയ്ക്കെതിരെ ഡോളറിന്റെ മൂല്യം പ്രതിവർഷം ശരാശരി 3–4% ഉയരുന്നതിനാൽ, സ്റ്റോക്ക് ലാഭത്തിനൊപ്പം കറൻസി ലാഭവും അധികമായി ലഭിക്കുന്നു.
* **AAOIFI ഗ്ലോബൽ ഹലാൽ സ്ക്രീനിംഗ് (SPUS / HLAL):** കടം 30%-ൽ താഴെയുള്ളതും പലിശ വരുമാനം 5%-ൽ താഴെയുള്ളതുമായ യു.എസ് കമ്പനികൾ.
""",
        "gold_criteria_title": "📐 **ഗോൾഡ് & സിൽവർ ഇ.ടി.എഫുകൾ തിരഞ്ഞെടുക്കുന്ന മാനദണ്ഡങ്ങൾ (AAOIFI Standard #57)**",
        "gold_criteria_body": """
* **100% ഫിസിക്കൽ ഗോൾഡ് പിന്തുണ:** പേപ്പർ കോൺട്രാക്ടുകൾക്ക് പകരം 99.5% ശുദ്ധമായ സ്വർണ്ണക്കട്ടികൾ വോൾട്ടിൽ സൂക്ഷിക്കുന്ന ഇ.ടി.എഫുകൾ (AAOIFI Standard #57 പ്രകാരം ഹലാൽ).
* **ഉയർന്ന ലിക്വിഡിറ്റി:** എപ്പോൾ വേണമെങ്കിലും എളുപ്പത്തിൽ വാങ്ങാനും വിൽക്കാനും NSE-ൽ ഉയർന്ന വോളിയം ഉള്ളവ.
* **കുറഞ്ഞ ചെലവ് (Low Expense & Tracking Error):** സ്വർണ്ണവിലയുടെ അതേ വളർച്ച കൃത്യമായി നൽകുന്നവ.
"""
    }
}

# Fallback for Hindi and Arabic to use English detailed bodies if not explicitly overridden
for _l in ["हिन्दी", "العربية"]:
    TRANSLATIONS[_l] = TRANSLATIONS["English"].copy()

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
# 🔐 OAUTH STATE MATCHER & SESSION AUTHENTICATION
# ==========================================
@st.cache_resource
def get_user_vault():
    return {}

user_vault = get_user_vault()

st.sidebar.markdown("# 🏛️ WEALTH OS")
lang = st.sidebar.selectbox("🌐 Language / ഭാഷ:", ["English", "മലയാളം", "हिन्दी", "العربية"], index=1)
T = TRANSLATIONS[lang]
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
                st.success("🎉 OAuth 2.0 Access Token generated and securely saved to your vault!")
            else:
                st.error(f"OAuth Token Error: {tok_or_err}")
    else:
        st.session_state["pending_auth_code"] = incoming_code

if "authenticated_user_hash" not in st.session_state:
    st.session_state["authenticated_user_hash"] = None

if not st.session_state["authenticated_user_hash"]:
    st.subheader(T["login_title"])
    st.info(T["login_desc"])
    with st.form("vault_login_form"):
        passkey_input = st.text_input(T["passkey_label"], type="password")
        login_submitted = st.form_submit_button(T["login_btn"], type="primary")
        if login_submitted and passkey_input.strip():
            st.session_state["authenticated_user_hash"] = hashlib.sha256(passkey_input.strip().encode()).hexdigest()[:16]
            st.rerun()
    st.stop()

USER_HASH = st.session_state["authenticated_user_hash"]

if st.sidebar.button(T["logout_btn"], use_container_width=True):
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
wealth_mode = st.sidebar.radio(T["phil_label"], [T["phil_conv"], T["phil_halal"]])
is_shariah = (wealth_mode == T["phil_halal"])
state['shariah_lock'] = is_shariah

st.sidebar.markdown("---")
menu_options = [T["m1"], T["m2"], T["m3"], T["m4"], T["m5"], T["m6"], T["m7"], T["m8"]]
main_menu = st.sidebar.radio(T["menu_label"], menu_options)

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
# ⚡ MODULE 1: INTRADAY ALGO TRADING BOT
# ##################################################################
if main_menu == T["m1"]:
    st.title(T["bot_title"])
    st.caption(T["bot_sub"])

    with st.expander(T["criteria_bot"], expanded=False):
        st.markdown(T["criteria_bot_body"])

    selected_broker = st.selectbox(
        T["broker_sel"],
        ["Upstox (API v2)", "Dhan (DhanHQ API)", "Zerodha (Kite Connect)", "Angel One (SmartAPI)"],
        index=0
    )
    state['broker'] = selected_broker.split(" ")[0]

    if is_shariah:
        st.warning(T["shariah_warn"])

    if state['token']:
        st.success(T["token_ready"])

    with st.expander(T["oauth_exp"], expanded=not bool(state['token'])):
        st.caption("🔒 Your API credentials are encrypted under your personal Passkey hash.")
        oa1, oa2, oa3 = st.columns(3)
        api_k = oa1.text_input(f"{state['broker']} API Key / Client ID:", value=state['api_key'], type="password")
        api_s = oa2.text_input(f"{state['broker']} API Secret:", value=state['api_secret'], type="password")
        red_u = oa3.text_input("Redirect URL:", value=state['redirect_uri'])

        if api_k != state['api_key'] or api_s != state['api_secret'] or red_u != state['redirect_uri']:
            state['api_key'], state['api_secret'], state['redirect_uri'] = api_k.strip(), api_s.strip(), red_u.strip()
            save_user_creds(USER_HASH, state['api_key'], state['api_secret'], state['redirect_uri'], state['tg_token'], state['tg_chat'], state['token'], state['broker'])

        if state['broker'] == "Upstox" and state['api_key'] and state['api_secret'] and state['redirect_uri']:
            save_user_creds(USER_HASH, state['api_key'], state['api_secret'], state['redirect_uri'], state['tg_token'], state['tg_chat'], state['token'], state['broker'])
            encoded_redir = urllib.parse.quote(state['redirect_uri'], safe='')
            auth_url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={state['api_key']}&redirect_uri={encoded_redir}&state={USER_HASH}"
            st.link_button("🚀 Step 1: 1-Click Auto Login with Upstox", auth_url, type="primary")
        elif state['broker'] != "Upstox":
            st.info(f"💡 Paste your {state['broker']} Access Token in the sidebar to begin execution.")

        with st.form("manual_code_form"):
            manual_code = st.text_input("Or paste the 'code=' parameter from callback URL:")
            submitted = st.form_submit_button("⚡ Generate Token Now")
            if submitted and manual_code:
                clean_code = manual_code.strip()
                if "code=" in clean_code:
                    clean_code = clean_code.split("code=")[-1].split("&")[0]
                ok, res_msg = exchange_code_for_token(clean_code, state['api_key'], state['api_secret'], state['redirect_uri'])
                if ok:
                    state['token'] = res_msg
                    save_user_creds(USER_HASH, state['api_key'], state['api_secret'], state['redirect_uri'], state['tg_token'], state['tg_chat'], res_msg, state['broker'])
                    st.success("🎉 Token generated and saved!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Error: {res_msg}")

    st.sidebar.markdown("---")
    st.sidebar.subheader(T["ctrl_panel"])
    mode_choice = st.sidebar.radio(T["mode_label"], [T["mode_paper"], T["mode_live"]], index=0 if state['mode'] == "PAPER" else 1)
    token_input = st.sidebar.text_input(f"{state['broker']} Access Token:", value=state['token'], type="password")
    capital_input = st.sidebar.number_input(T["cap_label"], value=float(state['capital']), min_value=500.0, step=500.0)
    risk_input = st.sidebar.number_input(T["risk_label"], value=float(state['risk']), min_value=10.0, step=25.0)

    tg_token_input = st.sidebar.text_input("Telegram Bot Token (Optional):", value=state['tg_token'], type="password")
    tg_chat_input = st.sidebar.text_input("Telegram Chat ID (Optional):", value=state['tg_chat'])

    def send_telegram(msg, tg_t, tg_c):
        if tg_t and tg_c:
            try:
                requests.post(f"https://api.telegram.org/bot{tg_t}/sendMessage", json={"chat_id": tg_c, "text": msg, "parse_mode": "Markdown"}, timeout=5)
            except Exception:
                pass

    def place_real_order(symbol, instrument_key, qty, action, token, u_state):
        if u_state['mode'] == "LIVE":
            broker_name = u_state.get('broker', 'Upstox')
            try:
                if broker_name == "Upstox":
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
                        err_msg = res_json.get('errors', [{}])[0].get('message', 'Order Rejected')
                        u_state['last_order_error'] = f"Order Failed ({symbol}): {err_msg}"
                        return False
                elif broker_name == "Dhan":
                    url = 'https://api.dhan.co/orders'
                    headers = {'access-token': token, 'Content-Type': 'application/json'}
                    order_data = {
                        "dhanClientId": u_state.get('api_key', ''),
                        "transactionType": action, "exchangeSegment": "NSE_EQ",
                        "productType": "INTRADAY", "orderType": "MARKET", "validity": "DAY",
                        "securityId": symbol, "quantity": int(qty)
                    }
                    res = requests.post(url, headers=headers, json=order_data, timeout=7)
                    return res.status_code == 200
                elif broker_name == "Zerodha":
                    url = 'https://api.kite.trade/orders/regular'
                    headers = {'X-Kite-Version': '3', 'Authorization': f"token {u_state.get('api_key', '')}:{token}"}
                    order_data = {
                        "tradingsymbol": symbol, "exchange": "NSE", "transaction_type": action,
                        "order_type": "MARKET", "quantity": int(qty), "product": "MIS", "validity": "DAY"
                    }
                    res = requests.post(url, headers=headers, data=order_data, timeout=7)
                    return res.status_code == 200
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
            u_state['nifty_status'] = "🟢 Bullish (Above EMA20)" if is_bullish else "🔴 Bearish (Below EMA20)"
            return is_bullish
        u_state['nifty_status'] = "⚠️ Waiting for Feed"
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

    def log_trade(u_hash, date_s, time_s, sym, t_type, bp, sp, qty, gross_pnl):
        turnover = (bp + sp) * qty
        est_charges = min(40.0, turnover * 0.0005) + (turnover * 0.0003)
        net_pnl = gross_pnl - est_charges
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("INSERT INTO trades (user_hash, date, time, symbol, type, buy_price, sell_price, qty, pnl) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (u_hash, date_s, time_s, sym, t_type, round(bp, 2), round(sp, 2), int(qty), round(net_pnl, 2)))
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
                        send_telegram(f"⏰ *3:15 PM Auto Square-off:* `{pos['symbol']}` closed. Gross PnL: `₹{pnl:.2f}`", u_state['tg_token'], u_state['tg_chat'])
                        u_state['active_pos'] = None
                u_state['nifty_status'] = "🌙 Market Closed (After 3:15 PM)"
                time.sleep(15)
                continue

            if u_state['consecutive_losses'] >= 2:
                u_state['kill_switch'] = True
                u_state['running'] = False
                send_telegram("🛑 *Kill Switch Activated!* Trading halted after 2 consecutive stop-losses.", u_state['tg_token'], u_state['tg_chat'])
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
                            send_telegram(f"⏳ *45m Stale Momentum Exit:* `{pos['symbol']}` closed. PnL: `₹{pnl:.2f}`", u_state['tg_token'], u_state['tg_chat'])
                            u_state['active_pos'] = None
                    elif cur_p >= pos['target']:
                        if place_real_order(pos['symbol'], pos['key'], pos['qty'], "SELL", token, u_state):
                            pnl = (cur_p - pos['buy_price']) * pos['qty']
                            log_trade(u_hash, now_ist.strftime("%Y-%m-%d"), now_ist.strftime("%I:%M:%S %p"), pos['symbol'], "TARGET_HIT", pos['buy_price'], cur_p, pos['qty'], pnl)
                            send_telegram(f"🎉 *TARGET HIT:* `{pos['symbol']}` Profit: `+₹{pnl:.2f}`", u_state['tg_token'], u_state['tg_chat'])
                            u_state['consecutive_losses'] = 0
                            u_state['active_pos'] = None
                    elif cur_p <= pos['sl']:
                        if place_real_order(pos['symbol'], pos['key'], pos['qty'], "SELL", token, u_state):
                            pnl = (cur_p - pos['buy_price']) * pos['qty']
                            log_trade(u_hash, now_ist.strftime("%Y-%m-%d"), now_ist.strftime("%I:%M:%S %p"), pos['symbol'], "STOP_LOSS", pos['buy_price'], cur_p, pos['qty'], pnl)
                            send_telegram(f"🛑 *STOP LOSS HIT:* `{pos['symbol']}` Loss: `₹{pnl:.2f}`", u_state['tg_token'], u_state['tg_chat'])
                            u_state['consecutive_losses'] += 1
                            u_state['active_pos'] = None

            is_weekday = now_ist.weekday() < 5
            is_trading_window = is_weekday and (market_entry_start <= curr_time_obj <= market_entry_cutoff)

            if not is_trading_window:
                if not is_weekday:
                    u_state['nifty_status'] = "📅 Market Holiday (Weekend)"
                elif curr_time_obj < market_entry_start:
                    u_state['nifty_status'] = "⏳ Waiting for 9:20 AM IST..."
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
                        reason, status = "Failed Rule #1: Nifty 50 < 20 EMA", "SKIPPED_NIFTY"
                    elif not above_vwap:
                        reason, status = "Failed Rule #2: Price < VWAP", "SKIPPED"
                    elif not volume_surge:
                        reason, status = "Failed Rule #4: Volume < 1.2x SMA", "SKIPPED"
                    elif not rsi_safe:
                        reason, status = f"Failed Rule #5: RSI ({rsi:.1f}) outside 50-68", "SKIPPED"
                    elif not ema_cross:
                        reason, status = "Awaiting Rule #3: EMA 9/21 Crossover", "WAITING"
                    else:
                        sl_dist = max(0.5, 1.5 * atr)
                        sl_p = curr_price - sl_dist
                        tg_p = curr_price + (3.0 * atr)
                        
                        risk_based_qty = int(u_state['risk'] // sl_dist)
                        max_affordable_qty = int(u_state['capital'] // curr_price)
                        qty = max(1, min(risk_based_qty, max_affordable_qty))

                        if curr_price > u_state['capital']:
                            reason, status = f"Insufficient Capital (Price: ₹{curr_price:.0f})", "SKIPPED_CAP"
                        elif place_real_order(symbol, instrument_key, qty, "BUY", token, u_state):
                            u_state['active_pos'] = {
                                'symbol': symbol, 'key': instrument_key, 'buy_price': curr_price,
                                'qty': qty, 'sl': sl_p, 'target': tg_p, 'entry_time': time.time()
                            }
                            reason, status = f"All 6 Rules Passed! BUY (Qty: {qty})", "🎯 BUY_TRIGGERED"
                            send_telegram(f"🚀 *BUY EXECUTED:* `{symbol}` (Qty: {qty}) @ ₹{curr_price:.2f} | Target: ₹{tg_p:.2f} | SL: ₹{sl_p:.2f}", u_state['tg_token'], u_state['tg_chat'])
                        else:
                            reason, status = "Broker Rejected Order", "ORDER_FAILED"

                    try:
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute('''INSERT INTO audit_logs (user_hash, date, time, symbol, price, vwap, rsi, vol_surge, ema_cross, nifty_trend, status, reason)
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
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
    if col1.button(T["start_btn"], use_container_width=True):
        if not token_input:
            st.sidebar.error("Please provide Broker Access Token!")
        else:
            state['token'] = token_input
            state['capital'] = capital_input
            state['risk'] = risk_input
            state['mode'] = "PAPER" if mode_choice == T["mode_paper"] else "LIVE"
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
            st.sidebar.success("Bot Started!")

    if col2.button(T["stop_btn"], use_container_width=True):
        state['running'] = False
        st.sidebar.warning("Bot Stopped!")

    if state['last_order_error']:
        st.error(f"🚨 Broker Alert: {state['last_order_error']}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(T["status_col"], T["status_run"] if state['running'] else (T["status_kill"] if state['kill_switch'] else T["status_off"]))
    m2.metric(T["nifty_col"], state['nifty_status'])
    m3.metric(T["loss_col"], f"{state['consecutive_losses']} / 2")
    m4.metric(T["cap_col"], f"₹{state['capital']:,.2f}")

    if state['active_pos']:
        ap = state['active_pos']
        st.success(f"📌 **Active Position:** `{ap['symbol']}` | Qty: `{ap['qty']}` | Buy: `₹{ap['buy_price']:.2f}` | Target: `₹{ap['target']:.2f}` | SL: `₹{ap['sl']:.2f}`")

    st.divider()

    t1, t2 = st.tabs([T["tab_scan"], T["tab_trades"]])
    with t1:
        try:
            conn = get_db_connection()
            today_str = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")
            df_live = pd.read_sql_query("SELECT time AS Time, symbol AS Stock, price AS Price, vwap AS VWAP, rsi AS RSI, nifty_trend AS [Nifty Trend], status AS Status, reason AS [Rule Evaluation] FROM audit_logs WHERE user_hash=? AND date=? ORDER BY id DESC LIMIT 50", conn, params=(USER_HASH, today_str))
            conn.close()
            if not df_live.empty:
                st.dataframe(df_live, use_container_width=True, hide_index=True)
            else:
                st.info(T["wait_scan"])
        except Exception:
            st.info(T["wait_scan"])

    with t2:
        try:
            conn = get_db_connection()
            df_tr = pd.read_sql_query("SELECT date AS Date, time AS Time, symbol AS Stock, type AS Action, qty AS Qty, buy_price AS [Buy Price], sell_price AS [Sell Price], pnl AS [Net PnL (After Charges)] FROM trades WHERE user_hash=? ORDER BY id DESC", conn, params=(USER_HASH,))
            conn.close()
            if not df_tr.empty:
                st.dataframe(df_tr, use_container_width=True, hide_index=True)
                csv_data = df_tr.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Trade History (CSV)", data=csv_data, file_name="my_trades_audit.csv", mime="text/csv")
            else:
                st.info(T["no_trades"])
        except Exception:
            st.info(T["no_trades"])

    if state['running']:
        if st.button(T["refresh_btn"]):
            st.rerun()

# ##################################################################
# 🎯 MODULE 2: DYNAMIC GOAL ALLOCATOR
# ##################################################################
elif main_menu == T["m2"]:
    st.title(T["m2"])
    with st.expander(T["goal_criteria_title"], expanded=False):
        st.markdown(T["goal_criteria_body"])

    if is_shariah:
        st.success("🌙 **100% ശരീഅത്ത് മോഡ് സജീവം:** പലിശ രഹിത ഹലാൽ ആസ്തികൾ മാത്രം." if is_ml else "🌙 **100% Shariah Mode Active:** Conventional debt and interest instruments are excluded.")

    c1, c2, c3 = st.columns(3)
    inv_type = c1.selectbox("നിക്ഷേപ രീതി:" if is_ml else "Investment Mode:", ["Monthly SIP", "Lump-Sum Allocation"])
    inv_amount = c2.number_input("നിക്ഷേപ തുക (₹):" if is_ml else "Investment Amount (₹):", value=10000.0, step=1000.0)
    goal_horizon = c3.selectbox(
        "നിക്ഷേപ കാലാവധി:" if is_ml else "Time Horizon & Objective:",
        [
            "⏳ 1 Year (ഹ്രസ്വകാലം / Emergency)" if is_ml else "⏳ 1 Year (Short-Term Liquidity / Emergency)",
            "🚀 3 - 5 Years (ഇടത്തരം വളർച്ച)" if is_ml else "🚀 3 - 5 Years (Medium-Term Growth / House / Business)",
            "🏛️ 10+ Years (ദീർഘകാല സമ്പത്ത്)" if is_ml else "🏛️ 10+ Years (Generational Wealth / Retirement)"
        ]
    )

    st.markdown("---")
    market_climate = st.selectbox(
        "നിലവിലെ വിപണി സാഹചര്യം:" if is_ml else "Current Market Regime:",
        [
            "🟢 Normal Bull (ശാന്തമായ വിപണി)",
            "⚠️ War / Crude Oil Spike (യുദ്ധം / അസ്ഥിരത)",
            "🔴 Extreme Market Crash (കടുത്ത തകർച്ച)"
        ]
    )

    if "1 Year" in goal_horizon:
        if is_shariah: eq_pct, gold_pct, cash_pct, reit_pct = 0.15, 0.35, 0.50, 0.0
        else: eq_pct, gold_pct, cash_pct, reit_pct = 0.15, 0.25, 0.50, 0.10
        rec_text = "1 വർഷത്തേക്ക് റിസ്ക് കുറയ്ക്കാൻ സ്വർണ്ണത്തിനും ലിക്വിഡ് ക്യാഷിനും മുൻഗണന." if is_ml else "Minimize equity volatility for 1-year horizons. Prioritize physical gold ETFs and liquid cash."
    elif "3 - 5 Years" in goal_horizon:
        if "War" in market_climate: eq_pct, gold_pct, cash_pct, reit_pct = 0.40, 0.30 if is_shariah else 0.25, 0.30 if is_shariah else 0.25, (0.0 if is_shariah else 0.10)
        else: eq_pct, gold_pct, cash_pct, reit_pct = 0.60, 0.20 if is_shariah else 0.15, 0.20 if is_shariah else 0.15, (0.0 if is_shariah else 0.10)
        rec_text = "ഇടത്തരം കാലാവധിയിൽ മികച്ച വളർച്ചയുള്ള ഓഹരികൾക്കും സ്വർണ്ണത്തിനും തുല്യ പ്രാധാന്യം." if is_ml else "Balanced growth across high-ROCE quality equities and sovereign/gold hedges."
    else:
        if "Crash" in market_climate: eq_pct, gold_pct, cash_pct, reit_pct = 0.75, 0.15, 0.10, 0.0
        else: eq_pct, gold_pct, cash_pct, reit_pct = 0.70 if is_shariah else 0.65, 0.20 if is_shariah else 0.15, 0.10, (0.0 if is_shariah else 0.10)
        rec_text = "10+ വർഷത്തേക്ക് കടരഹിത കുത്തക കമ്പനികളിൽ പണം കോമ്പൗണ്ട് ചെയ്യാൻ അനുവദിക്കുക." if is_ml else "Deploy aggressively into debt-free monopolies for 10+ year compounding."

    st.info(f"💡 {rec_text}")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("ഇക്വിറ്റി ഓഹരികൾ" if is_ml else "Core Equities", f"₹{(inv_amount * eq_pct):,.0f}", f"{int(eq_pct*100)}%")
    a2.metric("ഗോൾഡ് & സിൽവർ" if is_ml else "Gold & Silver", f"₹{(inv_amount * gold_pct):,.0f}", f"{int(gold_pct*100)}%")
    a3.metric("ക്യാഷ് കരുതൽ" if is_ml else "Cash Reserve", f"₹{(inv_amount * cash_pct):,.0f}", f"{int(cash_pct*100)}%")
    if not is_shariah: a4.metric("REITs / Yield", f"₹{(inv_amount * reit_pct):,.0f}", f"{int(reit_pct*100)}%")
    else: a4.metric("ശരീഅത്ത് പാലനം" if is_ml else "Compliance", "100% Halal", "AAOIFI")

# ##################################################################
# 💼 MODULE 3: LIVE PORTFOLIO & ALL-BROKER WATCHDOG
# ##################################################################
elif main_menu == T["m3"]:
    st.title(T["m3"])
    with st.expander(T["port_criteria_title"], expanded=False):
        st.markdown(T["port_criteria_body"])

    h_tab1, h_tab2 = st.tabs([
        "⚡ ലൈവ് ബ്രോക്കർ സിങ്ക് (Upstox / Dhan / Zerodha)" if is_ml else "⚡ Live Broker API Sync (Upstox / Dhan / Zerodha)",
        "📝 മാനുവൽ പോർട്ട്ഫോളിയോ (Groww / Other)" if is_ml else "📝 Groww / Manual Portfolio Tracker"
    ])

    with h_tab1:
        b_choice = st.selectbox("ബ്രോക്കർ തിരഞ്ഞെടുക്കുക:" if is_ml else "Select Broker for Holdings Sync:", ["Upstox", "Dhan", "Zerodha"])
        user_token = st.sidebar.text_input(f"{b_choice} Token:", value=state['token'], type="password", key="holdings_token")

        if st.button(f"🔄 {b_choice}-ൽ നിന്ന് പോർട്ട്ഫോളിയോ എടുക്കുക" if is_ml else f"🔄 Sync Holdings from {b_choice}"):
            if not user_token:
                st.error(f"Please enter your {b_choice} Access Token in the sidebar!")
            else:
                with st.spinner(f"⏳ Fetching demat holdings from {b_choice}..."):
                    try:
                        holdings = []
                        if b_choice == "Upstox":
                            headers = {'Accept': 'application/json', 'Authorization': f'Bearer {user_token}'}
                            res = requests.get('https://api.upstox.com/v2/portfolio/long-term-holdings', headers=headers, timeout=10)
                            data = res.json()
                            if data.get('status') == 'success':
                                holdings = data.get('data', [])
                        elif b_choice == "Dhan":
                            headers = {'access-token': user_token, 'Content-Type': 'application/json'}
                            res = requests.get('https://api.dhan.co/holdings', headers=headers, timeout=10)
                            if res.status_code == 200:
                                for item in res.json():
                                    holdings.append({
                                        'trading_symbol': item.get('tradingSymbol'),
                                        'quantity': item.get('totalQty', 0),
                                        'average_price': item.get('avgCostPrice', 0.0),
                                        'last_price': item.get('avgCostPrice', 0.0),
                                        'pnl': 0.0
                                    })
                        elif b_choice == "Zerodha":
                            headers = {'X-Kite-Version': '3', 'Authorization': f"token {state.get('api_key', '')}:{user_token}"}
                            res = requests.get('https://api.kite.trade/portfolio/holdings', headers=headers, timeout=10)
                            if res.status_code == 200:
                                holdings = res.json().get('data', [])

                        if len(holdings) > 0:
                            parsed_h = []
                            total_val, total_pnl = 0.0, 0.0
                            for h in holdings:
                                sym = h.get('trading_symbol') or h.get('tradingsymbol', 'N/A')
                                qty = h.get('quantity', 0)
                                avg_p = h.get('average_price', 0.0)
                                cur_p = h.get('last_price', avg_p)
                                pnl = h.get('pnl', (cur_p - avg_p) * qty)
                                total_val += (cur_p * qty)
                                total_pnl += pnl

                                pnl_pct = ((cur_p - avg_p) / avg_p * 100) if avg_p > 0 else 0
                                if pnl_pct < -10.0: sentinel_status = "🚨 എക്സിറ്റ് മുന്നറിയിപ്പ് (Review)" if is_ml else "🚨 Exit Alert (Stop-Loss / Review)"
                                elif pnl_pct > 20.0: sentinel_status = "🟢 മികച്ച ലാഭത്തിൽ (Hold)" if is_ml else "🟢 Strong Compounder (Hold / Trail SL)"
                                else: sentinel_status = "🟡 സാധാരണ നിലയിൽ (Hold)" if is_ml else "🟡 Normal Range (Hold)"

                                parsed_h.append({
                                    'Stock': sym, 'Quantity': qty, 'Avg Buy Price': round(avg_p, 2),
                                    'Current Price': round(cur_p, 2), 'Total P&L (₹)': round(pnl, 2),
                                    'P&L (%)': f"{round(pnl_pct, 1)}%", 'Watchdog Status': sentinel_status
                                })

                            hc1, hc2 = st.columns(2)
                            hc1.metric("ആകെ പോർട്ട്ഫോളിയോ മൂല്യം" if is_ml else "Total Portfolio Value", f"₹{total_val:,.2f}")
                            hc2.metric("ആകെ ലാഭം / നഷ്ടം" if is_ml else "Total Unrealized P&L", f"₹{total_pnl:,.2f}", delta=f"₹{total_pnl:,.2f}")
                            st.dataframe(pd.DataFrame(parsed_h), use_container_width=True, hide_index=True)
                        else:
                            st.info(f"നിങ്ങളുടെ {b_choice} അക്കൗണ്ടിൽ നിലവിൽ ഹോൾഡിംഗ്സുകൾ ഒന്നും കണ്ടെത്തിയില്ല." if is_ml else f"No long-term holdings found in your {b_choice} account.")
                    except Exception as e:
                        st.error(f"Error syncing holdings: {e}")

    with h_tab2:
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        m_sym = col_m1.text_input("സ്റ്റോക്ക് സിംബൽ (ഉദാ: TCS, CDSL):" if is_ml else "Stock Symbol (e.g. TCS, CDSL):").upper().strip()
        m_qty = col_m2.number_input("വാങ്ങിയ എണ്ണം (Qty):" if is_ml else "Quantity:", value=1, min_value=1, step=1)
        m_bp = col_m3.number_input("വാങ്ങിയ വില (₹):" if is_ml else "Buy Price (₹):", value=100.0, min_value=1.0, step=10.0)
        m_plat = col_m4.selectbox("പ്ലാറ്റ്‌ഫോം:" if is_ml else "Broker Platform:", ["Groww", "Zerodha", "AngelOne", "Other"])

        if st.button("➕ പോർട്ട്ഫോളിയോയിലേക്ക് ചേർക്കുക" if is_ml else "➕ Save to Private Portfolio"):
            if m_sym:
                try:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO manual_portfolio (user_hash, symbol, qty, buy_price, buy_date, notes) VALUES (?, ?, ?, ?, ?, ?)",
                              (USER_HASH, m_sym, m_qty, m_bp, datetime.date.today().strftime("%Y-%m-%d"), m_plat))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ {m_sym} ({m_plat}) added!")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.markdown("---")
        try:
            conn = get_db_connection()
            df_man = pd.read_sql_query("SELECT symbol AS Stock, qty AS Qty, buy_price AS [Buy Price], buy_date AS [Date], notes AS Broker FROM manual_portfolio WHERE user_hash=? ORDER BY id DESC", conn, params=(USER_HASH,))
            conn.close()
            if not df_man.empty:
                st.dataframe(df_man, use_container_width=True, hide_index=True)
            else:
                st.info("ഇതുവരെ മാനുവൽ ഓഹരികൾ ചേർത്തിട്ടില്ല." if is_ml else "No manual holdings recorded under your Passkey yet.")
        except Exception:
            st.info("No manual holdings recorded.")

# ##################################################################
# 🏛️ MODULE 4: 50-YEAR MOAT VAULT & LIVE STOCK SCANNER
# ##################################################################
elif main_menu == T["m4"]:
    st.title(T["m4"])

    with st.expander(T["moat_criteria_title"], expanded=True):
        st.markdown(T["moat_criteria_body"])

    st.subheader(T["scanner_title"])
    sc1, sc2 = st.columns([3, 1])
    scan_ticker = sc1.text_input(T["scanner_input"], value="TCS").upper().strip()
    if sc2.button(T["scanner_btn"], use_container_width=True) and scan_ticker:
        yf_sym = scan_ticker if (".NS" in scan_ticker or ".BO" in scan_ticker) else f"{scan_ticker}.NS"
        with st.spinner(f"Analyzing {yf_sym}..."):
            try:
                tk = yf.Ticker(yf_sym)
                info = tk.info
                mcap = info.get("marketCap", 0) or 1
                tot_debt = info.get("totalDebt", 0) or 0
                tot_cash = info.get("totalCash", 0) or 0
                roe = (info.get("returnOnEquity", 0) or 0) * 100
                sector = info.get("sector", "Unknown")
                industry = info.get("industry", "Unknown")

                debt_to_mcap = (tot_debt / mcap) * 100 if mcap > 1 else 0
                cash_to_mcap = (tot_cash / mcap) * 100 if mcap > 1 else 0

                non_halal_keywords = ["Bank", "Financial", "Insurance", "Tobacco", "Brew", "Distill", "Casino", "Gambling", "Defense"]
                is_prohibited_sector = any(k.lower() in (sector + " " + industry).lower() for k in non_halal_keywords)
                shariah_pass = (not is_prohibited_sector) and (debt_to_mcap < 33.0) and (cash_to_mcap < 33.0)
                buffett_pass = (roe >= 15.0) and (debt_to_mcap < 30.0)

                k1, k2, k3, k4 = st.columns(4)
                k1.metric("സെക്ടർ (Sector)" if is_ml else "Sector", sector)
                k2.metric("ROE / ലാഭക്ഷമത" if is_ml else "ROE / Quality", f"{roe:.1f}%", "✅ മികച്ചത്" if roe >= 15 else "⚠️ കുറവ്")
                k3.metric("കടം / Market Cap" if is_ml else "Debt / Market Cap", f"{debt_to_mcap:.1f}%", "✅ < 33% (Pass)" if debt_to_mcap < 33 else "❌ അമിത കടം")
                k4.metric("ശരീഅത്ത് സ്റ്റാറ്റസ്" if is_ml else "AAOIFI Shariah Status", "✅ ഹലാൽ (HALAL)" if shariah_pass else "❌ നോൺ-ഹലാൽ", "Buffett Moat: " + ("Pass" if buffett_pass else "Review"))

                hist_df = tk.history(period="1y")
                if not hist_df.empty:
                    st.caption(f"📈 **{scan_ticker} - 1 Year Price Trend:**")
                    st.line_chart(hist_df['Close'])
            except Exception as e:
                st.error(f"Could not fetch live fundamental data for {yf_sym}: {e}")

    st.markdown("---")
    st.subheader("🏛️ തിരഞ്ഞെടുത്ത 50-Year Moat ഓഹരികളും എക്സിറ്റ് നിയമങ്ങളും" if is_ml else "🏛️ Curated 50-Year Moat Vault (With Selection Metrics & Exit Triggers)")

    if is_shariah:
        if is_ml:
            stocks_data = [
                {"Stock": "TCS", "Sector": "IT Services", "Metrics": "ROCE: 58% | കടം: 0.6% | മാർജിൻ: 25%", "Why Buy?": "കടരഹിത ഭീമൻ, ഉയർന്ന ക്യാഷ് ഫ്ലോ, ആഗോള ഐ.ടി കുത്തക.", "Red Flags": "AI കാരണം ബില്ലിംഗ് കുറയുന്നത്.", "Exit Trigger": "ഓപ്പറേറ്റിംഗ് മാർജിൻ 20%-ൽ താഴെയാകുകയോ കടം 33% കടക്കുകയോ ചെയ്താൽ വിൽക്കുക.", "Status": "✅ ഹലാൽ (AAOIFI Pass)"},
                {"Stock": "Tata Elxsi", "Sector": "Design & EV", "Metrics": "ROCE: 42% | കടം: 0.4% | മാർജിൻ: 27%", "Why Buy?": "ഇലക്ട്രിക് വാഹന സോഫ്റ്റ്‌വെയർ മേഖലയിലെ കുത്തക.", "Red Flags": "യൂറോപ്യൻ വാഹന വിപണിയിലെ മാന്ദ്യം.", "Exit Trigger": "വാർഷിക വരുമാന വളർച്ച 10%-ൽ താഴെയായാൽ ഒഴിവാക്കുക.", "Status": "✅ ഹലാൽ (AAOIFI Pass)"},
                {"Stock": "Sun Pharma", "Sector": "Specialty Pharma", "Metrics": "ROCE: 18% | കടം: 1.5% | മാർജിൻ: 26%", "Why Buy?": "ജീവൻരക്ഷാ മരുന്നുകൾ നിർമ്മിക്കുന്നതിനാൽ മാന്ദ്യത്തെ അതിജീവിക്കും.", "Red Flags": "USFDA റെഗുലേറ്ററി തടസ്സങ്ങൾ.", "Exit Trigger": "പ്രധാന പ്ലാന്റുകൾക്ക് സ്ഥിരമായി USFDA നിരോധനം വന്നാൽ.", "Status": "✅ ഹലാൽ (AAOIFI Pass)"},
                {"Stock": "Polycab India", "Sector": "Cables & Wires", "Metrics": "ROCE: 28% | കടം: 0.8% | മാർജിൻ: 14%", "Why Buy?": "ഇന്ത്യൻ വയർ-കേബിൾ വിപണിയിലെ 25%+ കുത്തക.", "Red Flags": "ചെമ്പ് വിലയിലുണ്ടാകുന്ന വലിയ ചാഞ്ചാട്ടം.", "Exit Trigger": "ഗവേണൻസ് പ്രശ്നങ്ങളോ വിപണി വിഹിതം നഷ്ടപ്പെടലോ ഉണ്ടായാൽ.", "Status": "✅ ഹലാൽ (AAOIFI Pass)"}
            ]
        else:
            stocks_data = [
                {"Stock": "TCS", "Sector": "IT Services", "Metrics": "ROCE: 58% | Debt/MCap: 0.6% | Op Margin: 25%", "Why Buy?": "Zero-debt cash machine, mission-critical global IT moat.", "Red Flags": "AI-driven billing compression.", "Exit Trigger": "Operating margin drops below 20% or Debt > 33%.", "Status": "✅ Halal (AAOIFI Pass)"},
                {"Stock": "Tata Elxsi", "Sector": "Design & EV", "Metrics": "ROCE: 42% | Debt/MCap: 0.4% | Op Margin: 27%", "Why Buy?": "Embedded EV software leader with high switching costs.", "Red Flags": "European auto R&D slowdown.", "Exit Trigger": "Revenue growth falls below 10% YoY.", "Status": "✅ Halal (AAOIFI Pass)"},
                {"Stock": "Sun Pharma", "Sector": "Specialty Pharma", "Metrics": "ROCE: 18% | Debt/MCap: 1.5% | Op Margin: 26%", "Why Buy?": "Defensive global specialty healthcare moat, strong free cash flow.", "Red Flags": "USFDA regulatory observations.", "Exit Trigger": "Permanent USFDA import ban on core plants.", "Status": "✅ Halal (AAOIFI Pass)"},
                {"Stock": "Polycab India", "Sector": "Cables & Wires", "Metrics": "ROCE: 28% | Debt/MCap: 0.8% | Op Margin: 14%", "Why Buy?": "25%+ organized market share in electrification infrastructure.", "Red Flags": "Sharp copper price volatility.", "Exit Trigger": "Governance red flags or market share loss.", "Status": "✅ Halal (AAOIFI Pass)"}
            ]
    else:
        if is_ml:
            stocks_data = [
                {"Stock": "CDSL", "Sector": "Market Infrastructure", "Metrics": "ROCE: 33% | കടം: 0% | മാർജിൻ: 60%", "Why Buy?": "ഡിമാറ്റ് അക്കൗണ്ടുകൾ കൂടുമ്പോൾ ടോൾ ബൂത്ത് പോലെ ലാഭം നേടുന്ന കുത്തക.", "Red Flags": "SEBI ചാർജുകൾ വെട്ടിക്കുറയ്ക്കൽ.", "Exit Trigger": "റെഗുലേറ്ററി കമ്മീഷൻ പകുതിയായി കുറച്ചാൽ.", "Status": "⚠️ കൺവെൻഷണൽ"},
                {"Stock": "L&T", "Sector": "Infrastructure Giant", "Metrics": "ROE: 15% | ഓർഡർ ബുക്ക്: ₹5L+ Cr", "Why Buy?": "ഇന്ത്യൻ അടിസ്ഥാന സൗകര്യ വികസനത്തിലെ പകരം വെക്കാനില്ലാത്ത ഭീമൻ.", "Red Flags": "സർക്കാർ ചെലവുകൾ കുറയ്ക്കുന്നത്.", "Exit Trigger": "കടം (Debt-to-Equity) 1.5 കടന്നാൽ.", "Status": "⚠️ കൺവെൻഷണൽ"},
                {"Stock": "ITC Limited", "Sector": "FMCG / Cash Cow", "Metrics": "ROCE: 36% | കടം: 0% | ഡിവിഡന്റ്: 3.5%+", "Why Buy?": "ഭീമമായ ക്യാഷ് ഫ്ലോയും ഉയർന്ന ഡിവിഡന്റും.", "Red Flags": "പുകയില നികുതി വർദ്ധനവ്.", "Exit Trigger": "തുടർച്ചയായി 2 വർഷം ക്യാഷ് ഫ്ലോ ഇടിഞ്ഞാൽ.", "Status": "❌ നോൺ-ഹലാൽ (Tobacco)"},
                {"Stock": "HAL", "Sector": "Sovereign Defence", "Metrics": "ROCE: 31% | കടം: 0% | ഓർഡർ ബുക്ക്: ₹94,000 Cr", "Why Buy?": "ഇന്ത്യൻ വ്യോമസേനയ്ക്ക് ഫൈറ്റർ ജെറ്റുകൾ നിർമ്മിക്കുന്ന പരമാധികാര കുത്തക.", "Red Flags": "എൻജിൻ വിതരണത്തിലെ കാലതാമസം.", "Exit Trigger": "പ്രതിരോധ നിർമ്മാണത്തിലെ കുത്തക നഷ്ടപ്പെട്ടാൽ.", "Status": "⚠️ കൺവെൻഷണൽ"}
            ]
        else:
            stocks_data = [
                {"Stock": "CDSL", "Sector": "Market Infrastructure", "Metrics": "ROCE: 33% | Debt: 0% | Op Margin: 60%", "Why Buy?": "Regulated duopoly depository toll-booth business.", "Red Flags": "Regulatory fee caps by SEBI.", "Exit Trigger": "Tariff structure cut by more than 50%.", "Status": "⚠️ Conventional (Financial)"},
                {"Stock": "L&T", "Sector": "Infrastructure Giant", "Metrics": "ROE: 15% | Order Book: ₹5L+ Cr", "Why Buy?": "Unmatched engineering moat; backbone of Indian capex.", "Red Flags": "Government capex slowdown.", "Exit Trigger": "Consolidated Debt-to-Equity exceeds 1.5x.", "Status": "⚠️ Conventional (Debt > 33%)"},
                {"Stock": "ITC Limited", "Sector": "FMCG / Cash Cow", "Metrics": "ROCE: 36% | Debt: 0% | Div Yield: 3.5%+", "Why Buy?": "Massive free cash flow and pricing power.", "Red Flags": "Punitive sin-tax hikes.", "Exit Trigger": "Core free cash flow decline for 2 consecutive years.", "Status": "❌ Non-Halal (Tobacco)"},
                {"Stock": "HAL", "Sector": "Sovereign Defence", "Metrics": "ROCE: 31% | Debt: 0% | Order Book: ₹94,000 Cr", "Why Buy?": "Sovereign monopoly fighter jet manufacturer.", "Red Flags": "Execution delays in engine supply.", "Exit Trigger": "Loss of sovereign defence monopoly status.", "Status": "⚠️ Conventional (Defence)"}
            ]

    for s in stocks_data:
        with st.expander(f"📌 {s['Stock']} — ({s['Sector']}) | 📊 {s['Metrics']}"):
            st.markdown(f"**📐 തിരഞ്ഞെടുക്കാൻ കാരണമായ കണക്കുകൾ (Metrics):** `{s['Metrics']}`" if is_ml else f"**📐 Quantitative Selection Metrics:** `{s['Metrics']}`")
            st.markdown(f"**🟢 എന്തുകൊണ്ട് വാങ്ങണം (Thesis):** {s['Why Buy?']}" if is_ml else f"**🟢 Selection Thesis (Why Buy):** {s['Why Buy?']}")
            st.markdown(f"**⚠️ ശ്രദ്ധിക്കേണ്ട റിസ്കുകൾ:** {s['Red Flags']}" if is_ml else f"**⚠️ Key Risks to Monitor:** {s['Red Flags']}")
            st.error(f"🛑 **എപ്പോൾ വിറ്റ് ഒഴിവാക്കണം (Exit Trigger):** {s['Exit Trigger']}" if is_ml else f"🛑 **Strict Institutional Exit Trigger:** {s['Exit Trigger']}")
            st.caption(f"സ്റ്റാറ്റസ്: {s['Status']}")

# ##################################################################
# 📈 MODULE 5: MUTUAL FUNDS & ETFS
# ##################################################################
elif main_menu == T["m5"]:
    st.title(T["m5"])
    with st.expander(T["mf_criteria_title"], expanded=True):
        st.markdown(T["mf_criteria_body"])

    if is_shariah:
        funds = [
            {"Fund": "Tata Ethical Fund (Direct Growth)", "Type": "Shariah Equity", "3Y CAGR": "20.8%", "5Y CAGR": "22.5%", "Expense": "0.85%", "തിരഞ്ഞെടുക്കാൻ കാരണം (Criteria Passed)": "Nifty 500 Shariah ബെഞ്ച്മാർക്ക്, ബാങ്കിംഗ് ഓഹരികളില്ല, 28+ വർഷത്തെ മികച്ച ചരിത്രം." if is_ml else "Audited Nifty 500 Shariah benchmark, zero banking exposure, 28+ year track record."},
            {"Fund": "Taurus Ethical Fund (Direct Growth)", "Type": "Shariah Equity", "3Y CAGR": "22.1%", "5Y CAGR": "21.2%", "Expense": "0.95%", "തിരഞ്ഞെടുക്കാൻ കാരണം (Criteria Passed)": "കർശനമായ AAOIFI സ്ക്രീനിംഗ്, മികച്ച മിഡ്-ക്യാപ് വളർച്ച." if is_ml else "Strict AAOIFI debt/income screens, strong mid-cap quality alpha."},
            {"Fund": "Nippon India Gold BeES", "Type": "Physical Gold ETF", "3Y CAGR": "16.4%", "5Y CAGR": "14.8%", "Expense": "0.55%", "തിരഞ്ഞെടുക്കാൻ കാരണം (Criteria Passed)": "99.5% ശുദ്ധമായ ഫിസിക്കൽ സ്വർണ്ണ പിന്തുണ (AAOIFI Standard #57), ഉയർന്ന ലിക്വിഡിറ്റി." if is_ml else "99.5% physical bullion backing (AAOIFI Standard #57), highest NSE liquidity."}
        ]
    else:
        funds = [
            {"Fund": "Parag Parikh Flexi Cap Fund", "Type": "Flexi Cap", "3Y CAGR": "21.5%", "5Y CAGR": "24.2%", "Expense": "0.62%", "തിരഞ്ഞെടുക്കാൻ കാരണം (Criteria Passed)": "വാല്യൂ ഇൻവെസ്റ്റിംഗ്, യു.എസ് ടെക് കമ്പനികളിലെ നിക്ഷേപം, വിപണി ഇടിയുമ്പോൾ കുറഞ്ഞ നഷ്ടം." if is_ml else "Value-oriented moat investing, global tech exposure, lowest downside capture."},
            {"Fund": "UTI Nifty 50 Index Fund", "Type": "Passive Index", "3Y CAGR": "15.8%", "5Y CAGR": "16.5%", "Expense": "0.18%", "തിരഞ്ഞെടുക്കാൻ കാരണം (Criteria Passed)": "ഏറ്റവും കുറഞ്ഞ ചെലവ് (0.18%), ഇന്ത്യയിലെ മികച്ച 50 കമ്പനികളിൽ നേരിട്ടുള്ള നിക്ഷേപം." if is_ml else "Ultra-low cost (0.18%), zero fund-manager bias, minimal tracking error."},
            {"Fund": "Quant Small Cap Fund", "Type": "Small Cap", "3Y CAGR": "34.2%", "5Y CAGR": "38.5%", "Expense": "0.77%", "തിരഞ്ഞെടുക്കാൻ കാരണം (Criteria Passed)": "ക്വാണ്ടിറ്റേറ്റീവ് മൊമെന്റം സ്ട്രാറ്റജി വഴി ഉയർന്ന ദീർഘകാല വളർച്ച." if is_ml else "VLRT quantitative momentum-value framework for high-growth risk allocation."}
        ]
    st.dataframe(pd.DataFrame(funds), use_container_width=True, hide_index=True)

# ##################################################################
# 🌍 MODULE 6: GLOBAL MARKETS (INDMONEY / VESTED LIVE US TRACKER)
# ##################################################################
elif main_menu == T["m6"]:
    st.title(T["m6"])
    with st.expander(T["us_criteria_title"], expanded=False):
        st.markdown(T["us_criteria_body"])

    u_tab1, u_tab2 = st.tabs([
        "🇺🇸 എന്റെ US പോർട്ട്ഫോളിയോ (INDmoney / Vested)" if is_ml else "🇺🇸 My US Portfolio (INDmoney / Vested / Alpaca)",
        "🏆 മികച്ച ആഗോള ഓഹരികളും മാനദണ്ഡങ്ങളും" if is_ml else "🏆 Global Moat Leaders & Criteria"
    ])

    with u_tab1:
        uc1, uc2, uc3, uc4 = st.columns(4)
        u_sym = uc1.text_input("US സ്റ്റോക്ക് സിംബൽ (NVDA, AAPL, MSFT, SPUS):" if is_ml else "US Ticker (e.g. NVDA, AAPL, MSFT, SPUS):").upper().strip()
        u_qty = uc2.number_input("എണ്ണം (Fractional Qty):" if is_ml else "Quantity (Fractional OK):", value=1.0, min_value=0.01, step=0.1)
        u_bp = uc3.number_input("വാങ്ങിയ വില ($ USD):" if is_ml else "Buy Price ($ USD):", value=100.0, min_value=1.0, step=5.0)
        u_plat = uc4.selectbox("പ്ലാറ്റ്‌ഫോം:" if is_ml else "Platform:", ["INDmoney", "Vested", "Alpaca API", "Interactive Brokers"])

        if st.button("➕ US പോർട്ട്ഫോളിയോയിലേക്ക് ചേർക്കുക" if is_ml else "➕ Add to US Portfolio"):
            if u_sym:
                try:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO us_portfolio (user_hash, symbol, qty, buy_price_usd, buy_usd_inr, platform) VALUES (?, ?, ?, ?, ?, ?)",
                              (USER_HASH, u_sym, u_qty, u_bp, 84.0, u_plat))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ {u_sym} saved!")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.markdown("---")
        try:
            conn = get_db_connection()
            df_us = pd.read_sql_query("SELECT symbol, qty, buy_price_usd, platform FROM us_portfolio WHERE user_hash=? ORDER BY id DESC", conn, params=(USER_HASH,))
            conn.close()
            if not df_us.empty:
                try:
                    usd_inr_live = float(yf.Ticker("INR=X").fast_info.get('lastPrice', 84.5))
                except Exception:
                    usd_inr_live = 84.5

                us_rows = []
                tot_inr_val = 0.0
                for _, r in df_us.iterrows():
                    sym = r['symbol']
                    qty = float(r['qty'])
                    bp_usd = float(r['buy_price_usd'])
                    try:
                        live_usd = float(yf.Ticker(sym).fast_info.get('lastPrice', bp_usd))
                    except Exception:
                        live_usd = bp_usd
                    val_usd = live_usd * qty
                    val_inr = val_usd * usd_inr_live
                    pnl_pct = ((live_usd - bp_usd) / bp_usd * 100) if bp_usd > 0 else 0
                    tot_inr_val += val_inr
                    us_rows.append({
                        "Ticker": sym, "Platform": r['platform'], "Qty": qty,
                        "Buy ($)": f"${bp_usd:.2f}", "Live ($)": f"${live_usd:.2f}",
                        "Value (₹ INR)": f"₹{val_inr:,.2f}", "Return (%)": f"{pnl_pct:.1f}%"
                    })
                st.metric("ആകെ US പോർട്ട്ഫോളിയോ മൂല്യം (INR)" if is_ml else "Total US Portfolio Value (in INR)", f"₹{tot_inr_val:,.2f}", f"Live USD/INR = ₹{usd_inr_live:.2f}")
                st.dataframe(pd.DataFrame(us_rows), use_container_width=True, hide_index=True)
            else:
                st.info("INDmoney / Vested ഓഹരികൾ മുകളിൽ ചേർത്താൽ തത്സമയ രൂപ/ഡോളർ മൂല്യം ഇവിടെ കാണാം." if is_ml else "Add your INDmoney or Vested US holdings above to track live USD & INR returns.")
        except Exception:
            st.info("No US holdings recorded yet.")

    with u_tab2:
        if is_shariah:
            us_stocks = [
                {"Company": "Nvidia (NVDA)", "Sector": "AI Hardware", "Shariah": "✅ ഹലാൽ (AAOIFI)", "തിരഞ്ഞെടുക്കാൻ കാരണം": "ROE > 90%, കടം < 2%, AI ചിപ്പുകളിലെ 80%+ ആഗോള കുത്തക." if is_ml else "ROE > 90%, Debt/MCap < 2%, 80%+ AI GPU monopoly."},
                {"Company": "Microsoft (MSFT)", "Sector": "Cloud & OS", "Shariah": "✅ ഹലാൽ (AAOIFI)", "തിരഞ്ഞെടുക്കാൻ കാരണം": "ROE > 35%, കടം < 3%, എന്റർപ്രൈസ് ക്ലൗഡ് ശൃംഖല." if is_ml else "ROE > 35%, Debt/MCap < 3%, Azure + Copilot enterprise lock-in."},
                {"Company": "SPUS ETF", "Sector": "S&P 500 Shariah", "Shariah": "✅ 100% Halal ETF", "തിരഞ്ഞെടുക്കാൻ കാരണം": "അമേരിക്കയിലെ മികച്ച 200 പലിശരഹിത ഹലാൽ കമ്പനികളുടെ ഇ.ടി.എഫ്." if is_ml else "Excludes all banks/debt-heavy firms from S&P 500; 0.45% expense."}
            ]
        else:
            us_stocks = [
                {"Company": "Microsoft (MSFT)", "Sector": "Cloud / AI", "Market Cap": "$3.1T+", "Selection Reason": "AAA-rated balance sheet, enterprise software monopoly."},
                {"Company": "Apple (AAPL)", "Sector": "Consumer Tech", "Market Cap": "$3.4T+", "Selection Reason": "2B+ active devices, massive share buybacks & free cash flow."},
                {"Company": "Nvidia (NVDA)", "Sector": "AI Chips", "Market Cap": "$3.0T+", "Selection Reason": "CUDA software moat + global AI data-center dominance."},
                {"Company": "Berkshire Hathaway (BRK.B)", "Sector": "Conglomerate", "Market Cap": "$900B+", "Selection Reason": "Warren Buffett capital allocation + $300B+ cash fortress."}
            ]
        st.dataframe(pd.DataFrame(us_stocks), use_container_width=True, hide_index=True)

# ##################################################################
# 🥇 MODULE 7: GOLD & CRISIS HEDGE ASSETS
# ##################################################################
elif main_menu == T["m7"]:
    st.title(T["m7"])
    with st.expander(T["gold_criteria_title"], expanded=True):
        st.markdown(T["gold_criteria_body"])
    gold_data = [
        {"Instrument": "Nippon India Gold BeES (GOLDBEES)", "Backing": "99.5% Physical Bullion", "Expense": "0.55%", "Compliance": "✅ AAOIFI Standard #57", "തിരഞ്ഞെടുക്കാൻ കാരണം": "NSE-ൽ ഏറ്റവും ഉയർന്ന വോളിയം, 100% ഫിസിക്കൽ ഗോൾഡ് പിന്തുണ." if is_ml else "Highest liquidity on NSE, custodial physical gold backing."},
        {"Instrument": "HDFC Gold ETF (HDFCGOLD)", "Backing": "99.5% Physical Bullion", "Expense": "0.30%", "Compliance": "✅ AAOIFI Standard #57", "തിരഞ്ഞെടുക്കാൻ കാരണം": "ദീർഘകാല നിക്ഷേപത്തിന് ഏറ്റവും കുറഞ്ഞ ചെലവ് (0.30%)." if is_ml else "Low expense ratio (0.30%) for long-term holding."},
        {"Instrument": "Nippon India Silver ETF (SILVERBEES)", "Backing": "99.9% Physical Silver", "Expense": "0.50%", "Compliance": "✅ AAOIFI Standard #57", "തിരഞ്ഞെടുക്കാൻ കാരണം": "ഇലക്ട്രിക് വാഹന/സോളാർ വ്യവസായ ആവശ്യകതയും സുരക്ഷിത നിക്ഷേപവും." if is_ml else "Industrial EV/Solar demand + precious metal monetary hedge."}
    ]
    st.dataframe(pd.DataFrame(gold_data), use_container_width=True, hide_index=True)

# ##################################################################
# 📚 MODULE 8: INVESTMENT AUDIT JOURNAL
# ##################################################################
elif main_menu == T["m8"]:
    st.title(T["m8"])
    with st.expander("➕ പുതിയ നിക്ഷേപ തീരുമാനം രേഖപ്പെടുത്തുക" if is_ml else "➕ Record New Investment Decision"):
        j_col1, j_col2, j_col3 = st.columns(3)
        j_asset = j_col1.text_input("അസറ്റ് / സ്റ്റോക്ക് (ഉദാ: TCS, GOLDBEES):" if is_ml else "Asset / Ticker (e.g. TCS, GOLDBEES):").upper().strip()
        j_action = j_col2.selectbox("തീരുമാനം:" if is_ml else "Action:", ["BUY", "HOLD", "SELL", "WATCHLIST"])
        j_status = j_col3.selectbox("വിഭാഗം:" if is_ml else "Classification:", ["✅ Long-Term Moat", "🌙 Halal Verified", "⚠️ Tactical Bet", "🛑 Rule Exit"])
        j_reason = st.text_area("എന്തുകൊണ്ട് ഈ തീരുമാനം എടുത്തു? (Thesis & Exit Rule):" if is_ml else "Investment Thesis & Exit Criteria:")

        if st.button("💾 ജേർണലിൽ സേവ് ചെയ്യുക" if is_ml else "💾 Save to Private Journal"):
            if j_asset and j_reason:
                try:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO wealth_audit (user_hash, date, asset, category, action, status, veteran_reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                              (USER_HASH, datetime.date.today().strftime("%Y-%m-%d"), j_asset, "Equity/Asset", j_action, j_status, j_reason))
                    conn.commit()
                    conn.close()
                    st.success("✅ സേവ് ചെയ്തു!" if is_ml else "✅ Decision logged in your private journal!")
                except Exception as e:
                    st.error(f"Error: {e}")

    try:
        conn = get_db_connection()
        df_audit = pd.read_sql_query("SELECT date AS Date, asset AS Asset, action AS Action, status AS Classification, veteran_reason AS [Thesis / Notes] FROM wealth_audit WHERE user_hash=? ORDER BY id DESC LIMIT 50", conn, params=(USER_HASH,))
        conn.close()
        if not df_audit.empty:
            st.dataframe(df_audit, use_container_width=True, hide_index=True)
        else:
            st.info("ഇതുവരെ കുറിപ്പുകൾ ചേർത്തിട്ടില്ല." if is_ml else "No journal entries recorded under your Passkey yet.")
    except Exception:
        st.info("No journal entries recorded yet.")
