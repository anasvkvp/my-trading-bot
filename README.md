# 🏛️ Autonomous Wealth OS & Institutional Algo Trading Platform

[![Live Web App](https://img.shields.io/badge/🚀_Live_App-Open_in_Streamlit-FF4B4B?style=for-the-badge)](https://my-trading-bot-wyjcnfn2bprzd4ysp8riie.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Brokers](https://img.shields.io/badge/Brokers-Upstox_|_Dhan_|_Zerodha-0052CC?style=for-the-badge)](https://upstox.com)
[![Security](https://img.shields.io/badge/Privacy-SHA256_Multi--User_Vault-success?style=for-the-badge)](https://sqlite.org)
[![Compliance](https://img.shields.io/badge/AAOIFI-Shariah_Screening-009688?style=for-the-badge)](https://aaoifi.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

An institutional-grade, multi-user, multi-broker wealth management and algorithmic execution platform built in Python. Designed around the disciplined, 50-year capital-preservation principles of legends like Warren Buffett, Charlie Munger, and Howard Marks, the platform combines **high-probability tactical intraday execution** with **long-term macroeconomic generational wealth creation**.

🌐 **Live Cloud Deployment:** [Launch Autonomous Wealth OS](https://my-trading-bot-wyjcnfn2bprzd4ysp8riie.streamlit.app)  
🗣️ **Supported Languages:** English | മലയാളം (Malayalam) | हिन्दी (Hindi) | العربية (Arabic)

---

## 🌟 Key Architectural Pillars

| Module | Core Functionality | Primary Focus |
| :--- | :--- | :--- |
| **⚡ Multi-Broker Algo Engine** | 1-Click OAuth 2.0, Nifty Trend Guard, VWAP, EMA 9/21, ATR SL | Capital Preservation & Low Drawdown |
| **🔐 Private Multi-User Vault** | SHA-256 Passkey Isolation & Encrypted OAuth State Matching | 100% Data Privacy for Public Users |
| **🎯 Dynamic Goal Engine** | 1Y, 3-5Y, and 10+ Year Multi-Horizon Allocator | Macro Climate Sentinel & Crisis Sizing |
| **💼 All-Broker Watchdog** | Upstox, Dhan, Zerodha API Sync & Groww Portfolio Tracker | Real-time Thesis & Exit Monitoring |
| **🏛️ 50-Year Moat Vault** | Zero-Debt Monopolies & Pricing Power Leaders | Generational Compounders (Coffee Can) |
| **🌙 100% Halal Wealth** | Pure AAOIFI Screening, SPUS/HLAL, Shariah Watchlist Lock | Zero-Interest, Ethical Asset Allocation |

---

### 1. ⚡ Multi-Broker Institutional Intraday Algo Engine
* **Multi-Broker Execution:** Supports **Upstox API v2, DhanHQ, Zerodha Kite Connect, and Angel One**, alongside a zero-risk **Paper Trading Simulation Mode**.
* **1-Click Automatic OAuth 2.0 Token Generator:** Seamless browser authentication with encrypted `state` verification—no manual token copy-pasting required.
* **Nifty Trend Guard & Market Window Enforcement:** Validates Nifty 50 20-EMA alignment and restricts new entries strictly to the prime institutional window (**9:20 AM – 3:05 PM IST**).
* **Dynamic ATR Position Sizing & Capital Cap:** Volatility-adjusted 1:2 risk-to-reward sizing capped automatically against available account capital.
* **Consecutive Loss Circuit Breaker (Kill Switch):** Automatically halts execution after 2 consecutive stop-losses and dispatches instant **Telegram Bot Alerts**.
* **45-Minute Stale Momentum & 3:15 PM Auto Square-Off:** Eliminates non-trending decay and guarantees full liquidation prior to broker auto-square-off penalties.

---

### 2. 🔐 Multi-User Privacy & Multilingual Architecture
* **SHA-256 Encrypted Workspace Isolation:** Publicly accessible web app where each user unlocks their own isolated database vault and background trading thread using a secret Passkey.
* **Real-Time 4-Language Switcher:** Instant UI localization across **English, Malayalam (മലയാളം), Hindi (हिन्दी), and Arabic (العربية)**.

---

### 3. 🎯 Dynamic Goal & Macro Climate Sentinel
* **Time-Horizon Engine:** Flexible allocation models across **1-Year (Liquidity), 3-5 Year (Growth), and 10+ Year (Generational)** horizons.
* **Crisis Sentinel:** Dynamically shifts marginal capital allocations between Equities, Physical Gold ETFs, and Liquid Cash based on geopolitical tensions, crude oil spikes, and market crashes.

---

### 4. 💼 Multi-Broker Demat Holdings Sync & Exit Sentinel
* Integrates seamlessly with **Upstox, Dhan, and Zerodha** long-term demat holdings, plus manual tracking for **Groww** portfolios.
* Continuously evaluates held assets against institutional exit triggers and stop-loss thresholds.

---

### 5. 🌙 100% Zero-Compromise Shariah Engine
* Built strictly according to **AAOIFI Standards** (Standard #57 for Gold, financial threshold screens: Debt < 33%, Interest securities < 33%, Non-halal revenue < 5%).
* Master toggle automatically switches the intraday scanner to a **100% Shariah-Compliant Watchlist** (`TCS`, `INFY`, `SUNPHARMA`, `RELIANCE`), excluding conventional banking stocks.

---

### 6. 🌍 Global Markets & Live USD/INR Portfolio Tracker
* **INDmoney / Vested / Alpaca US Equity Tracker:** Track fractional US equities (`NVDA`, `MSFT`, `AAPL`, `SPUS`) with live Yahoo Finance USD pricing and real-time `USD/INR` currency appreciation calculations.

---

## 🛠️ Technology Stack

| Layer | Component | Description |
| :--- | :--- | :--- |
| **Frontend UI** | Streamlit (Cloud) | Multilingual, mobile-first Web App with session-based vault lock |
| **Backend Engine** | Python 3.10+ | Isolated multi-user background worker threads (`threading`) |
| **Persistence** | SQLite3 (WAL Mode) | Concurrent ACID database partitioned by `SHA-256` user hashes |
| **Broker & Alerts** | Upstox / Dhan / Telegram | OAuth 2.0 auto-token exchange & real-time Telegram execution alerts |
| **Market Data** | Upstox Feed & `yfinance` | Intraday 1-minute candles & live global USD/INR valuation |

---

## 🚀 Quickstart Guide (Cloud & Local Setup)

### Option A: Instant Cloud Access (No Installation Required)
1. Open the live web application: **[Autonomous Wealth OS on Streamlit](https://my-trading-bot-wyjcnfn2bprzd4ysp8riie.streamlit.app)**
2. Enter your personal **Secret Passkey** to create or unlock your private encrypted workspace.

### Option B: Local Installation

    git clone https://github.com/anasvkvp/my-trading-bot.git
    cd my-trading-bot
    pip install -r requirements.txt
    streamlit run app.py

The application will open automatically in your browser at `http://localhost:8501`.

---

## 🔒 Security & Privacy Architecture
* **Zero Credential Exposure:** API Keys, Access Tokens, and personal client data are never committed to this repository.
* **Cryptographic User Partitioning:** Every user's portfolio, trade history, and OAuth state are isolated via `SHA-256` passkey hashing.
* **Separation of Concerns:** The open-source repository contains pure algorithmic logic and financial formulas; your portfolio balances and private credentials remain strictly confidential.

---

## ⚖️ Regulatory & Legal Disclaimers (SEBI & Financial Disclosures)

> ⚠️ **IMPORTANT REGULATORY NOTICE:**  
> This software platform is developed strictly for **educational, research, and self-directed personal use**.

* **Non-Advisory Status:** The author and contributors are not SEBI-registered Investment Advisers (RIA) or Research Analysts (RA). None of the content, formulas, or curated lists constitute personal financial advice or a solicitation to buy or sell securities.
* **Market Risk:** Equities, derivatives, and algorithmic trading carry substantial capital risk. Past algorithmic backtest performances do not guarantee future live returns.
* **Self-Directed Execution:** All trading and investment executions initiated through broker APIs remain entirely at the discretion and sole responsibility of the individual account holder.
* **Shariah Verification:** While screening rules align with global AAOIFI guidelines, investors are advised to cross-verify compliance based on their individual scholarly guidance.

---

## 📄 License
This project is open-source and distributed under the **MIT License**.
