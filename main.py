import os
import time
import hmac
import hashlib
import threading
import requests
import pandas as pd
from datetime import datetime
from flask import Flask, request

app = Flask(__name__)

# Variáveis de ambiente
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MEXC_API_KEY = os.getenv("MEXC_API_KEY")
MEXC_SECRET_KEY = os.getenv("MEXC_SECRET_KEY")
TP_PERCENT = float(os.getenv("TP_PERCENT", "0.01"))        # 1%
SL_PERCENT = float(os.getenv("SL_PERCENT", "0.10"))        # 10%
RISK_PERCENT = float(os.getenv("RISK_PERCENT", "0.10"))    # 10%
CANCEL_MINUTES = int(os.getenv("CANCEL_MINUTES", "5"))

symbols = [
    'SAGAUSDT', 'ACEUSDT', 'PORTALUSDT', 'HIFIUSDT', 'ALTUSDT', 'ONIUSDT',
    'IMXUSDT', 'FLOKIUSDT', 'MAGICUSDT', 'DYDXUSDT', 'RNDRUSDT'
]

def send_message(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, json=payload)
    except:
        pass

def signature(payload, secret_key):
    query = '&'.join([f"{k}={v}" for k, v in sorted(payload.items())])
    return hmac.new(secret_key.encode(), query.encode(), hashlib.sha256).hexdigest()

def buscar_candles(symbol, interval, limit=100):
    url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url)
        df = pd.DataFrame(response.json())
        df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume'] + list(range(6, len(df.columns)))
        df['close'] = df['close'].astype(float)
        return df
    except:
        return None

def calcular_rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def criar_ordem_limit(symbol, qty, entry_price):
    endpoint = "https://api.mexc.com/api/v1/private/order/place"
    ts = str(int(time.time() * 1000))
    order_data = {
        "symbol": symbol,
        "price": entry_price,
        "vol": qty,
        "side": 1,  # Buy
        "type": 1,  # Limit
        "open_type": "cross",
        "positionId": 0,
        "leverage": 5,
        "externalOid": f"oid_{ts}",
        "timestamp": ts
    }
    order_data["sign"] = signature(order_data, MEXC_SECRET_KEY)
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "ApiKey": MEXC_API_KEY
    }
    response = requests.post(endpoint, data=order_data, headers=headers)
    return response.json()

def criar_ordem_oco(symbol, qty, entry_price):
    tp_price = round(entry_price * (1 + TP_PERCENT), 6)
    sl_price = round(entry_price * (1 - SL_PERCENT), 6)
    send_message(f"🎯 Criando TP: {tp_price} | 🛑 SL: {sl_price}")
    # MEXC não tem OCO nativo em futuros, vamos simular com duas ordens LIMIT

    # TP
    criar_ordem_limit(symbol, qty, tp_price)

    # SL
    criar_ordem_limit(symbol, qty, sl_price)

def obter_saldo_usdt():
    endpoint = "https://api.mexc.com/api/v1/private/account/assets"
    ts = str(int(time.time() * 1000))
    payload = {
        "timestamp": ts
    }
    payload["sign"] = signature(payload, MEXC_SECRET_KEY)
    headers = {"ApiKey": MEXC_API_KEY}
    try:
        r = requests.get(endpoint, params=payload, headers=headers)
        data = r.json()
        for coin in data.get("data", []):
            if coin["currency"] == "USDT":
                return float(coin["availableBalance"])
    except:
        return 0

def analisar_symbol(symbol):
    for timeframe in ['5m', '15m']:
        df = buscar_candles(symbol, timeframe)
        if df is not None and not df.empty:
            rsi = calcular_rsi(df).iloc[-1]
            preco = df['close'].iloc[-1]

            if rsi <= 30:
                send_message(f"🟢 COMPRA: {symbol} [{timeframe}] | RSI: {rsi:.2f} | Preço: {preco}")
                emitir_alerta_sonoro()
                enviar_ordem(symbol, preco)

def emitir_alerta_sonoro():
    try:
        import winsound
        winsound.Beep(1000, 300)
    except:
        pass

def enviar_ordem(symbol, preco_entrada):
    saldo = obter_saldo_usdt()
    valor_total = saldo * RISK_PERCENT
    qty = round((valor_total * 5) / preco_entrada, 2)
    resultado = criar_ordem_limit(symbol, qty, preco_entrada)
    send_message(f"📥 Ordem enviada: {symbol} | Qtd: {qty} | Preço: {preco_entrada}")

    # Cria TP e SL após 2s
    time.sleep(2)
    criar_ordem_oco(symbol, qty, preco_entrada)

def loop_sinais():
    while True:
        for symbol in symbols:
            try:
                analisar_symbol(symbol)
            except Exception as e:
                send_message(f"Erro analisando {symbol}: {e}")
        time.sleep(300)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data:
        texto = data["message"].get("text", "")
        if texto == "/start":
            send_message("✅ Bot iniciado! Monitorando Altcoins 🚀")
        elif texto == "/status":
            send_message("📡 Bot rodando e aguardando sinais!")
    return {"ok": True}

@app.route("/")
def index():
    return "Bot de Futuros MEXC - Online 🚀"

if __name__ == "__main__":
    threading.Thread(target=loop_sinais).start()
    app.run(host="0.0.0.0", port=8080)
