import os
import time
import hmac
import hashlib
import requests
import pandas as pd
from flask import Flask, request
from datetime import datetime
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("MEXC_API_KEY")
SECRET_KEY = os.getenv("MEXC_SECRET_KEY")
RISK_PERCENT = float(os.getenv("RISK_PERCENT", 0.05))
TP_PERCENT = float(os.getenv("TP_PERCENT", 0.01))
SL_PERCENT = float(os.getenv("SL_PERCENT", 0.03))
CANCEL_MINUTES = int(os.getenv("CANCEL_MINUTES", 5))

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
SYMBOLS = ['ALTUSDT', 'SAGAUSDT', 'ACEUSDT']

app = Flask(__name__)
bot_ativo = False

def telegram(text):
    try:
        requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"Erro enviando Telegram: {e}")

def assinar(params):
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()
    return f"{query}&signature={signature}"

def enviar_ordem_limit(symbol, side, quantity, price):
    url = "https://api.mexc.com/api/v1/private/order/submit"
    timestamp = int(time.time() * 1000)
    params = {
        "symbol": symbol,
        "price": str(price),
        "vol": str(quantity),
        "side": side,
        "type": "1",
        "open_type": "1",
        "leverage": "5",
        "position_id": "0",
        "external_oid": f"bot_{timestamp}",
        "stop_loss_price": "",
        "take_profit_price": "",
        "timestamp": timestamp
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "ApiKey": API_KEY
    }
    signed = assinar(params)
    response = requests.post(url, headers=headers, data=signed)
    return response.json()

def buscar_preco(symbol):
    try:
        url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=1m&limit=2"
        df = pd.DataFrame(requests.get(url).json())
        df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume'] + list(range(6, len(df.columns)))
        df['close'] = df['close'].astype(float)
        return df['close'].iloc[-1]
    except Exception as e:
        telegram(f"Erro buscar_preco {symbol}: {e}")
        return None

def calcular_rsi(symbol, interval='5m'):
    try:
        url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=100"
        df = pd.DataFrame(requests.get(url).json())
        df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume'] + list(range(6, len(df.columns)))
        df['close'] = df['close'].astype(float)
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    except Exception as e:
        telegram(f"Erro calcular_rsi {symbol}: {e}")
        return None

def buscar_saldo():
    try:
        url = "https://api.mexc.com/api/v1/private/account/assets"
        params = {"timestamp": int(time.time() * 1000)}
        signed = assinar(params)
        headers = {"ApiKey": API_KEY}
        response = requests.get(url, headers=headers, params=signed)
        ativos = response.json()['data']
        usdt = next((a for a in ativos if a['currency'] == 'USDT'), None)
        return float(usdt['available_balance']) if usdt else 0.0
    except Exception as e:
        telegram(f"Erro buscar_saldo: {e}")
        return 0.0

def processar_sinal(symbol):
    preco = buscar_preco(symbol)
    rsi = calcular_rsi(symbol)
    if preco is None or rsi is None:
        telegram(f"Erro analisando {symbol}: Preço ou RSI inválido")
        return
    if rsi <= 30:
        saldo = buscar_saldo()
        valor = saldo * RISK_PERCENT
        qtd = round((valor * 5) / preco, 3)
        tp = round(preco * (1 + TP_PERCENT), 6)
        sl = round(preco * (1 - SL_PERCENT), 6)
        resp = enviar_ordem_limit(symbol, "1", qtd, preco)
        mensagem = (
            f"🟢 COMPRA: {symbol} [5m] | RSI: {rsi:.2f}\n"
            f"💰 Preço: {preco}\n"
            f"🎯 TP: {tp} | 🛑 SL: {sl}\n"
            f"📦 Quantidade: {qtd}\n"
            f"📋 Ordem: {resp}"
        )
        telegram(mensagem)

def iniciar_bot():
    while True:
        for symbol in SYMBOLS:
            try:
                processar_sinal(symbol)
            except Exception as e:
                telegram(f"Erro processando {symbol}: {e}")
        time.sleep(300)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    global bot_ativo
    update = request.get_json()
    if "message" in update:
        texto = update["message"].get("text", "")
        if texto == "/start":
            telegram("✅ Bot iniciado! Monitorando Altcoins.")
            if not bot_ativo:
                bot_ativo = True
                threading.Thread(target=iniciar_bot).start()
        elif texto == "/status":
            status = "🟢 ATIVO" if bot_ativo else "🔴 INATIVO"
            telegram(f"📊 Status do bot: {status}")
    return {"ok": True}

@app.route("/")
def home():
    return "Bot MEXC ativo! 🚀"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
