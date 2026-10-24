import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import time
import threading
import yfinance as yf

st.set_page_config(page_title="Upstox Algo Bot & Backtester", layout="wide", page_icon="📈")

st.title("🤖 Upstox അൽഗോരിതം ട്രേഡിങ് ബോട്ട്")
st.caption("ക്ലൗഡിൽ തത്സമയം പ്രവർത്തിക്കുന്ന ലൈവ് ബോട്ടും 5 വർഷത്തെ ബാക്ക്ടെസ്റ്ററും.")

WATCHLIST = {
    'SBIN': 'NSE_EQ|INE062A01020',
    'RELIANCE': 'NSE_EQ|INE002A01018',
    'BHARTIARTL': 'NSE_EQ|INE397D01024',
    'LT': 'NSE_EQ|INE018A01030'
}

# ബാക്ക്ടെസ്റ്റ് ചെയ്യാനുള്ള 20 പ്രമുഖ ഓഹരികൾ
BACKTEST_STOCKS = [
    'SBIN.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'AXISBANK.NS', 'KOTAKBANK.NS', 'BAJFINANCE.NS',
    'TCS.NS', 'INFY.NS', 'HCLTECH.NS', 'WIPRO.NS',
    'M&M.NS', 'MARUTI.NS',
    'RELIANCE.NS', 'NTPC.NS', 'POWERGRID.NS', 'ONGC.NS',
    'LT.NS', 'TATASTEEL.NS', 'BHARTIARTL.NS', 'ITC.NS'
]

@st.cache_resource
def get_global_state():
    return {
        'running': False, 'logs': [], 'trades': [], 'pnl': 0.0,
        'token': '', 'capital': 5000.0, 'risk': 100.0, 'mode': 'പേപ്പർ ട്രേഡിംഗ്',
        'tg_token': '', 'tg_chat': '', 'thread': None
    }

state = get_global_state()

# സൈഡ്‌ബാർ
st.sidebar.header("⚙️ കൺട്രോൾ പാനൽ")
mode_input = st.sidebar.radio("ട്രേഡിംഗ് മോഡ്:", ["പേപ്പർ ട്രേഡിംഗ്", "ലൈവ് റിയൽ മണി"], index=0 if state['mode']=="പേപ്പർ ട്രേഡിംഗ്" else 1)
token_input = st.sidebar.text_input("Upstox Access Token:", value=state['token'], type="password")
capital_input = st.sidebar.number_input("ക്യാപിറ്റൽ (₹):", value=float(state['capital']), step=500.0)
risk_input = st.sidebar.number_input("ഒരു ട്രേഡിലെ റിസ്ക് (₹):", value=float(state['risk']), step=25.0)

tg_token_input = st.sidebar.text_input("Telegram Bot Token (Optional):", value=state['tg_token'], type="password")
tg_chat_input = st.sidebar.text_input("Telegram Chat ID (Optional):", value=state['tg_chat'])

# ബാക്ക്ഗ്രൗണ്ട് ലൂപ്പ് ഫംഗ്ഷനുകൾ
def send_telegram(msg, tg_t, tg_c):
    if tg_t and tg_c:
        try:
            requests.post(f"https://api.telegram.org/bot{tg_t}/sendMessage", json={"chat_id": tg_c, "text": msg, "parse_mode": "Markdown"}, timeout=5)
        except Exception:
            pass

def fetch_candles(instrument_key, token):
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token}'}
    url = f"https://api.upstox.com/v2/historical-candle/intraday/{instrument_key}/1minute"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if data.get('status') == 'success' and 'candles' in data['data']:
            df = pd.DataFrame(data['data']['candles'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
            return df.iloc[::-1].reset_index(drop=True)
    except Exception:
        pass
    return None

def calculate_indicators(df):
    close = df['close'].astype(float)
    volume = df['volume'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    
    df['EMA_Fast'] = close.ewm(span=9, adjust=False).mean()
    df['EMA_Slow'] = close.ewm(span=21, adjust=False).mean()
    df['Vol_SMA'] = volume.rolling(window=20).mean()
    typical_price = (high + low + close) / 3
    df['VWAP'] = (typical_price * volume).cumsum() / volume.cumsum()
    df['RSI'] = 100 - (100 / (1 + (close.diff().where(close.diff() > 0, 0).rolling(14).mean() / (-close.diff().where(close.diff() < 0, 0)).rolling(14).mean())))
    return df

def background_trading_loop():
    while state['running']:
        token = state['token']
        if not token:
            time.sleep(5)
            continue

        for symbol, instrument_key in WATCHLIST.items():
            if not state['running']:
                break
            df = fetch_candles(instrument_key, token)
            if df is None or len(df) < 30:
                continue

            df = calculate_indicators(df)
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            curr_price = float(curr['close'])
            curr_vol = float(curr['volume'])
            vol_avg = float(curr['Vol_SMA']) if not np.isnan(curr['Vol_SMA']) else 0
            vwap = float(curr['VWAP'])
            rsi = float(curr['RSI'])

            ema_cross = (prev['EMA_Fast'] <= prev['EMA_Slow']) and (curr['EMA_Fast'] > curr['EMA_Slow'])
            rsi_safe = 50 <= rsi <= 68
            above_vwap = curr_price > vwap
            volume_surge = curr_vol >= (1.2 * vol_avg) if vol_avg > 0 else True

            ist_zone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            curr_time = datetime.datetime.now(ist_zone).strftime("%I:%M:%S %p")

            if not above_vwap:
                reason, status = "VWAP-ക്ക് താഴെയാണ് (Bearish)", "SKIPPED"
            elif not volume_surge:
                reason, status = "വോളിയം കുറവാണ് (No Surge)", "SKIPPED"
            elif not rsi_safe:
                reason, status = f"RSI അനുകൂലമല്ല ({rsi:.1f})", "SKIPPED"
            elif not ema_cross:
                reason, status = "EMA ക്രോസ് ആയിട്ടില്ല", "WAITING"
            else:
                reason, status = "എല്ലാ ഫിൽട്ടറുകളും വിജയിച്ചു!", "🎯 BUY TRIGGERED"
                send_telegram(f"🚀 *BUY സിഗ്നൽ:* `{symbol}` @ ₹{curr_price:.2f}", state['tg_token'], state['tg_chat'])

            state['logs'].append({
                'Time': curr_time, 'Stock': symbol, 'Price': round(curr_price, 2),
                'VWAP': round(vwap, 2), 'RSI': round(rsi, 1), 'Status': status, 'Reason': reason
            })
            if len(state['logs']) > 50:
                state['logs'].pop(0)

        time.sleep(10)

# ബട്ടണുകൾ
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
        state['running'] = True

        if state['thread'] is None or not state['thread'].is_alive():
            t = threading.Thread(target=background_trading_loop, daemon=True)
            t.start()
            state['thread'] = t
        st.sidebar.success("ബാക്ക്ഗ്രൗണ്ട് ബോട്ട് ആരംഭിച്ചു!")

if col2.button("⏹️ STOP BOT", use_container_width=True):
    state['running'] = False
    st.sidebar.warning("ബോട്ട് ഓഫ് ചെയ്തു!")

# വിഷ്വൽ കാർഡുകൾ
m1, m2, m3, m4 = st.columns(4)
m1.metric("ബോട്ട് സ്റ്റാറ്റസ്", "🟢 ബാക്ക്ഗ്രൗണ്ടിൽ ഓടുന്നു" if state['running'] else "🔴 ഓഫ് ആണ്")
m2.metric("ഇന്നത്തെ ലാഭം / നഷ്ടം", f"₹{state['pnl']:.2f}")
m3.metric("എടുത്ത ട്രേഡുകൾ", len(state['trades']))
m4.metric("ക്യാപിറ്റൽ", f"₹{state['capital']:.2f}")

st.divider()

# 3 പ്രധാന ടാബുകൾ
tab1, tab2, tab3 = st.tabs(["🔍 ലൈവ് സ്കാനിംഗ് ലോഗ്", "📜 ട്രേഡുകൾ", "📊 20 സ്റ്റോക്ക് മെഗാ ബാക്ക്ടെസ്റ്റ്"])

with tab1:
    if state['logs']:
        st.dataframe(pd.DataFrame(state['logs']).iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("ബോട്ട് ബാക്ക്ഗ്രൗണ്ടിൽ സ്കാൻ ചെയ്യാൻ കാത്തിരിക്കുന്നു...")

with tab2:
    if state['trades']:
        st.dataframe(pd.DataFrame(state['trades']).iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("ഇതുവരെ ട്രേഡുകൾ ഒന്നും നടന്നിട്ടില്ല.")

# ==========================================
# 📊 ടാബ് 3: മെഗാ ബാക്ക്ടെസ്റ്റ് ഫീച്ചർ
# ==========================================
with tab3:
    st.subheader("📈 20 പ്രമുഖ നിഫ്റ്റി ഓഹരികളുടെ 5 വർഷത്തെ പെർഫോമൻസ്")
    st.caption("ബ്രോക്കറേജും നികുതികളും കുറച്ച ശേഷം ഏറ്റവും കൂടുതൽ ലാഭം തരുന്ന സ്റ്റോക്കുകളെ ഇവിടെ കണ്ടെത്താം.")

    if st.button("🚀 5 വർഷത്തെ മെഗാ ബാക്ക്ടെസ്റ്റ് റൺ ചെയ്യുക"):
        with st.spinner("⏳ 20 ഓഹരികളുടെ 5 വർഷത്തെ ഡാറ്റ പരിശോധിച്ച് റാങ്ക് ചെയ്യുന്നു... ദയവായി കാത്തിരിക്കൂ..."):
            bt_results = []
            
            def calculate_charges(buy_val, sell_val):
                turnover = buy_val + sell_val
                brokerage = min(20.0, buy_val * 0.0005) + min(20.0, sell_val * 0.0005)
                stt = sell_val * 0.00025
                exchange_charges = turnover * 0.0000345
                sebi_charges = turnover * 0.000001
                stamp_duty = buy_val * 0.00003
                gst = 0.18 * (brokerage + exchange_charges + sebi_charges)
                return brokerage + stt + exchange_charges + sebi_charges + stamp_duty + gst

            def calculate_supertrend(high, low, close, period=10, multiplier=3):
                tr = np.max(np.vstack([high[1:] - low[1:], np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])]), axis=0)
                tr = np.insert(tr, 0, high[0] - low[0])
                atr = pd.Series(tr).rolling(window=period).mean().to_numpy().flatten()
                hl2 = (high + low) / 2
                upperband = hl2 + (multiplier * atr)
                lowerband = hl2 - (multiplier * atr)
                direction = np.ones(len(close))
                for i in range(period, len(close)):
                    if float(close[i-1]) > float(upperband[i-1]):
                        direction[i] = 1
                    elif float(close[i-1]) < float(lowerband[i-1]):
                        direction[i] = -1
                    else:
                        direction[i] = direction[i-1]
                        if direction[i] == 1 and lowerband[i] < lowerband[i-1]:
                            lowerband[i] = lowerband[i-1]
                        if direction[i] == -1 and upperband[i] > upperband[i-1]:
                            upperband[i] = upperband[i-1]
                return direction, atr

            for sym in BACKTEST_STOCKS:
                try:
                    df_b = yf.download(sym, period="5y", interval="1d", auto_adjust=True, progress=False)
                    if df_b.empty or len(df_b) < 60:
                        continue
                    close_b = df_b['Close'].to_numpy(dtype=float).flatten()
                    high_b = df_b['High'].to_numpy(dtype=float).flatten()
                    low_b = df_b['Low'].to_numpy(dtype=float).flatten()
                    
                    ema_50_b = pd.Series(close_b).ewm(span=50, adjust=False).mean().to_numpy().flatten()
                    direction_b, atr_b = calculate_supertrend(high_b, low_b, close_b)
                    
                    cap = 5000.0
                    peak = 5000.0
                    max_dd = 0.0
                    wins, losses = 0, 0
                    win_sum, loss_sum = 0.0, 0.0
                    in_p, bp, sl, tg, qty = False, 0, 0, 0, 0
                    trailed = False

                    for i in range(50, len(close_b)):
                        cp = float(close_b[i])
                        c_atr = float(atr_b[i]) if not np.isnan(atr_b[i]) else (cp * 0.02)
                        
                        if not in_p:
                            if (direction_b[i-1] == -1 and direction_b[i] == 1) and (cp > ema_50_b[i]):
                                in_p = True
                                bp = cp
                                qty = max(1, int(cap // bp))
                                sl = bp - (1.5 * c_atr)
                                tg = bp + (3.0 * c_atr)
                                trailed = False
                                continue
                        if in_p:
                            done, sp = False, 0
                            if not trailed and cp >= (bp + (1.5 * c_atr)):
                                sl = bp
                                trailed = True
                            if cp >= tg:
                                sp, done, wins = tg, True, wins + 1
                            elif cp <= sl:
                                sp, done, losses = sl, True, losses + 1

                            if done:
                                net = ((sp - bp) * qty) - calculate_charges(bp * qty, sp * qty)
                                cap += net
                                if net > 0: win_sum += net
                                else: loss_sum += abs(net)
                                if cap > peak: peak = cap
                                dd = (peak - cap) / peak * 100
                                if dd > max_dd: max_dd = dd
                                in_p = False

                    tot = wins + losses
                    if tot > 0:
                        pf = round(win_sum / loss_sum, 2) if loss_sum > 0 else 99.0
                        bt_results.append({
                            'Stock': sym.replace('.NS', ''),
                            'Trades': tot, 'Wins': wins, 'Losses': losses,
                            'Win Rate (%)': round((wins/tot)*100, 1),
                            'Profit Factor': pf,
                            'Max Drawdown (%)': round(max_dd, 1),
                            'Net Profit (₹)': round(cap - 5000.0, 2),
                            'Final Capital (₹)': round(cap, 2)
                        })
                except Exception:
                    continue

            if bt_results:
                res_df = pd.DataFrame(bt_results).sort_values(by=['Net Profit (₹)', 'Win Rate (%)'], ascending=[False, False])
                st.success("✅ 20 ഓഹരികളുടെ മെഗാ ബാക്ക്ടെസ്റ്റ് പൂർത്തിയായി! റാങ്ക് ലിസ്റ്റ് താഴെ കാണാം:")
                st.dataframe(res_df, use_container_width=True, hide_index=True)
            else:
                st.error("ഡാറ്റ ലഭിച്ചില്ല. ദയവായി വീണ്ടും ശ്രമിക്കുക.")

# ഓട്ടോ അപ്‌ഡേറ്റ്
if state['running']:
    time.sleep(5)
    st.rerun()
