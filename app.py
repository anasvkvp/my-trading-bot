import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import time

# ==========================================
# 📱 മൊബൈൽ ഫ്രണ്ട്‌ലി പേജ് സെറ്റിംഗ്സ്
# ==========================================
st.set_page_config(page_title="Upstox Algo Bot", layout="wide", page_icon="📈")

st.title("🤖 Upstox അൽഗോരിതം ട്രേഡിങ് ബോട്ട്")
st.caption("കമ്പ്യൂട്ടർ ആവശ്യമില്ലാതെ ക്ലൗഡിൽ പ്രവർത്തിക്കുന്ന പൂർണ്ണ ഓട്ടോമാറ്റിക് സിസ്റ്റം.")

# 🎯 5 വർഷത്തെ ബാക്ക്ടെസ്റ്റിൽ വിജയിച്ച മികച്ച ഓഹരികൾ
WATCHLIST = {
    'SBIN': 'NSE_EQ|INE062A01020',
    'RELIANCE': 'NSE_EQ|INE002A01018',
    'BHARTIARTL': 'NSE_EQ|INE397D01024',
    'LT': 'NSE_EQ|INE018A01030'
}

# ==========================================
# ⚙️ സൈഡ്‌ബാർ - നിയന്ത്രണങ്ങൾ (Settings)
# ==========================================
st.sidebar.header("⚙️ കൺട്രോൾ പാനൽ")
mode = st.sidebar.radio("ട്രേഡിംഗ് മോഡ്:", ["പേപ്പർ ട്രേഡിംഗ് (സുരക്ഷിതം)", "ലൈവ് റിയൽ മണി"])
token_input = st.sidebar.text_input("Upstox Access Token നൽകുക:", type="password")
capital = st.sidebar.number_input("ക്യാപിറ്റൽ (₹):", value=5000.0, step=500.0)
max_risk = st.sidebar.number_input("ഒരു ട്രേഡിലെ പരമാവധി റിസ്ക് (₹):", value=100.0, step=25.0)

telegram_token = st.sidebar.text_input("Telegram Bot Token (Optional):", type="password")
telegram_chat_id = st.sidebar.text_input("Telegram Chat ID (Optional):")

# സെഷൻ സ്റ്റേറ്റ് തയ്യാറാക്കുന്നു
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'trades' not in st.session_state:
    st.session_state.trades = []
if 'daily_pnl' not in st.session_state:
    st.session_state.daily_pnl = 0.0

# ബട്ടണുകൾ
col_btn1, col_btn2 = st.sidebar.columns(2)
if col_btn1.button("▶️ START BOT", use_container_width=True):
    if not token_input:
        st.sidebar.error("ദയവായി Access Token നൽകുക!")
    else:
        st.session_state.bot_running = True
        st.sidebar.success("ബോട്ട് ഓൺ ആയി!")

if col_btn2.button("⏹️ STOP BOT", use_container_width=True):
    st.session_state.bot_running = False
    st.sidebar.warning("ബോട്ട് ഓഫ് ചെയ്തു!")

# ==========================================
# 📊 സംഗ്രഹ കാർഡുകൾ (Metric Dashboard)
# ==========================================
c1, c2, c3, c4 = st.columns(4)
status_text = "🟢 പ്രവർത്തിക്കുന്നു (Running)" if st.session_state.bot_running else "🔴 ഓഫ് ആണ് (Stopped)"
c1.metric("ബോട്ട് സ്റ്റാറ്റസ്", status_text)
c2.metric("ഇന്നത്തെ ലാഭം / നഷ്ടം", f"₹{st.session_state.daily_pnl:.2f}")
c3.metric("എടുത്ത ട്രേഡുകൾ", len(st.session_state.trades))
c4.metric("ക്യാപിറ്റൽ", f"₹{capital:.2f}")

st.divider()

# ==========================================
# 🔍 ഫംഗ്ഷനുകൾ (API & Data)
# ==========================================
def send_telegram(msg):
    if telegram_token and telegram_chat_id:
        try:
            url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            requests.post(url, json={"chat_id": telegram_chat_id, "text": msg, "parse_mode": "Markdown"}, timeout=5)
        except Exception:
            pass

def fetch_candles(instrument_key):
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token_input}'}
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
    
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean()
    
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    return df

# ==========================================
# 📋 ടാബുകൾ: സ്കാനർ ലോഗും ട്രേഡ് ഹിസ്റ്ററിയും
# ==========================================
tab1, tab2 = st.tabs(["🔍 തത്സമയ സ്കാനിംഗ് & ഫിൽട്ടർ ലോഗ്", "📜 എടുത്ത ട്രേഡുകൾ"])

with tab1:
    if st.session_state.logs:
        df_logs = pd.DataFrame(st.session_state.logs)
        st.dataframe(df_logs.iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("ബോട്ട് 'START' ചെയ്യുമ്പോൾ ഓരോ ഓഹരിയും സ്കാൻ ചെയ്ത വിവരങ്ങൾ ഇവിടെ തത്സമയം വരും.")

with tab2:
    if st.session_state.trades:
        df_tr = pd.DataFrame(st.session_state.trades)
        st.dataframe(df_tr.iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("ഇതുവരെ ട്രേഡുകൾ ഒന്നും നടന്നിട്ടില്ല.")

# ==========================================
# 🚀 ലൈവ് സ്കാനിംഗ് ലൂപ്പ്
# ==========================================
if st.session_state.bot_running and token_input:
    for symbol, instrument_key in WATCHLIST.items():
        df = fetch_candles(instrument_key)
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

        curr_time = datetime.datetime.now().strftime("%H:%M:%S")

        # തീരുമാനം രേഖപ്പെടുത്തുന്നു
        if not above_vwap:
            reason = "VWAP-ക്ക് താഴെയാണ് (Bearish)"
            status = "SKIPPED"
        elif not volume_surge:
            reason = "വോളിയം കുറവാണ് (No Surge)"
            status = "SKIPPED"
        elif not rsi_safe:
            reason = f"RSI അനുകൂലമല്ല ({rsi:.1f})"
            status = "SKIPPED"
        elif not ema_cross:
            reason = "EMA ക്രോസ് ആയിട്ടില്ല"
            status = "WAITING"
        else:
            reason = "എല്ലാ ഫിൽട്ടറുകളും വിജയിച്ചു!"
            status = "🎯 BUY TRIGGERED"
            send_telegram(f"🚀 *BUY സിഗ്നൽ വന്നിരിക്കുന്നു:* `{symbol}` @ ₹{curr_price:.2f}")

        # ലോഗിൽ ചേർക്കുന്നു (പരമാവധി 50 ലോഗുകൾ സൂക്ഷിക്കുന്നു)
        st.session_state.logs.append({
            'Time': curr_time, 'Stock': symbol, 'Price': round(curr_price, 2),
            'VWAP': round(vwap, 2), 'RSI': round(rsi, 1), 'Status': status, 'Reason': reason
        })
        if len(st.session_state.logs) > 50:
            st.session_state.logs.pop(0)

    time.sleep(5)
    st.rerun()
