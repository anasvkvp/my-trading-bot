# 🏛️ Autonomous Wealth OS & Institutional Algo Trading Platform

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Broker API](https://img.shields.io/badge/Upstox-API_v2-0052CC?style=for-the-badge)](https://upstox.com)
[![Database](https://img.shields.io/badge/SQLite3-Embedded-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Compliance](https://img.shields.io/badge/AAOIFI-Shariah_Screening-009688?style=for-the-badge)](https://aaoifi.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

An institutional-grade, multi-asset wealth management and algorithmic execution platform built in Python. Designed around the disciplined, 50-year capital-preservation principles of legends like Warren Buffett, Charlie Munger, and Howard Marks, the platform combines **high-probability tactical intraday execution** with **long-term macroeconomic generational wealth creation**.

---

## 🌟 Key Architectural Pillars

| Module | Core Functionality | Primary Focus |
| :--- | :--- | :--- |
| **⚡ Intraday Algo Engine** | Nifty Trend Guard, VWAP, Supertrend, ATR Stop-Loss | Capital Preservation & Low Drawdown |
| **🎯 Dynamic Goal Engine** | 1Y, 3-5Y, and 10+ Year Multi-Horizon Allocator | Macro Climate Sentinel & Crisis Sizing |
| **💼 Live Demat Watchdog** | Broker API Holdings Sync & Automated Sell Triggers | Real-time Thesis & Governance Monitoring |
| **🏛️ 50-Year Moat Vault** | Zero-Debt Monopolies & Pricing Power Leaders | Generational Compounders (Coffee Can) |
| **🌙 100% Halal Wealth** | Pure AAOIFI Screening, SPUS/HLAL, Shariah Funds | Zero-Interest, Ethical Asset Allocation |

---

### 1. ⚡ Institutional Intraday Algo Engine
* **Nifty Trend Guard:** Validates market directional alignment before initiating individual equity long positions.
* **Volume Surge & VWAP Filters:** Eliminates false breakouts and market noise.
* **Dynamic ATR Stop-Loss & Target:** Volatility-adjusted 1:2 risk-to-reward parameters.
* **Consecutive Loss Circuit Breaker (Kill Switch):** Automatically shuts down execution after 2 consecutive stops to protect capital.
* **45-Minute Stale Momentum Exit:** Auto-liquidates flat, non-trending trades at cost to prevent end-of-day decay.
* **3:15 PM Penalty Enforcement:** Guaranteed square-off prior to broker auto-square-off penalties.

---

### 2. 🎯 Dynamic Goal & Macro Climate Sentinel
* **Time-Horizon Engine:** Flexible allocation models across **1-Year (Tactical), 3-5 Year (Growth), and 10+ Year (Generational)** horizons.
* **Crisis Sentinel:** Dynamically shifts marginal capital allocations between Equities, Gold, and Liquid Cash based on geopolitical tensions, crude oil spikes, and market regimes.

---

### 3. 💼 Live Demat Holdings Sync & Exit Sentinel
* Integrates seamlessly with broker portfolios via Upstox API v2 (`/v2/portfolio/long-term-holdings`).
* Continuously evaluates held assets against institutional sell triggers:
  * Fundamental thesis breakdown
  * Promoter integrity & governance alerts
  * Capital allocation decay / Debt-to-equity breaches
  * Severe technical breakdown (200-day EMA violations)

---

### 4. 🌙 100% Zero-Compromise Shariah Engine
* Built strictly according to **AAOIFI Standards** (Standard #57 for Gold, financial threshold screens: Debt < 33%, Interest securities < 33%, Non-halal revenue < 5%).
* Master toggle enables an immediate system-wide lock eliminating conventional banking, interest-bearing instruments, and non-permissible equities.
* Features dedicated research on **Nifty Shariah leaders, Global Halal Titans (SPUS/HLAL), and Tata Ethical Fund**.

---

### 5. 🌍 Global Wealth & Currency Arbitrage Hub
* Curated research on the **Magnificent 7 & Berkshire Hathaway**.
* **Dual Currency Appreciation Calculator:** Demonstrates how USD appreciation against INR historically compounds foreign equity returns.
* Direct vs. Feeder Route Guidance (Zero-fee INR Feeder ETFs vs. Direct LRS routes).

---

## 🛠️ Technology Stack

| Layer | Component | Description |
| :--- | :--- | :--- |
| **Frontend UI** | Streamlit | Responsive, mobile-first Web App with live updates |
| **Backend Engine** | Python 3.10+ | Multi-threaded background execution worker (`threading`) |
| **Persistence** | SQLite3 | Embedded ACID database for trades, audit logs, and manual demat sync |
| **Broker Integration** | Upstox API v2 | Real-time candles, quotes, and portfolio sync via OAuth 2.0 |
| **Market Data** | Yahoo Finance (`yfinance`) | 5-year historical backtesting and fundamental data retrieval |

---

## 🚀 Quickstart Guide (Local Setup)

### Prerequisites
* Python 3.10 or higher installed with `PATH` enabled.
* An active Upstox Developer Account (for live API access).

### Execution Commands

```bash
git clone https://github.com/anasvkvp/my-trading-bot.git
cd my-trading-bot
pip install -r requirements.txt
streamlit run app.py
```
The application will open automatically in your browser at http://localhost:8501.
🔒 Security & Privacy Architecture
Zero Credential Persistence: API Keys, Access Tokens, and personal client data are never committed to this repository.
Ephemeral In-Memory Handling: Runtime tokens reside strictly within temporary server RAM sessions and communicate via encrypted HTTPS protocols.
Separation of Concerns: The open-source code represents pure algorithmic logic and financial formulas; your portfolio balances and private credentials remain strictly confidential.
⚖️ Regulatory & Legal Disclaimers (SEBI & Financial Disclosures)
⚠️ IMPORTANT REGULATORY NOTICE:
This software platform is developed strictly for educational, research, and self-directed personal use.
Non-Advisory Status: The author and contributors are not SEBI-registered Investment Advisers (RIA) or Research Analysts (RA). None of the content, formulas, or curated lists constitute personal financial advice or a solicitation to buy or sell securities.
Market Risk: Equities, derivatives, and algorithmic trading carry substantial capital risk. Past algorithmic backtest performances do not guarantee future live returns.
Self-Directed Execution: All trading and investment executions initiated through broker APIs remain entirely at the discretion and sole responsibility of the individual account holder.
Shariah Verification: While screening rules align with global AAOIFI guidelines, investors are advised to cross-verify compliance based on their individual scholarly guidance.
📄 License
This project is open-source and distributed under the MIT License.
