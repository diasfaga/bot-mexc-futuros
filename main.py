
import requests
import hmac
import hashlib
import time
import json
from flask import Flask, request
import os
from dotenv import load_dotenv
import threading

load_dotenv()

API_KEY = os.getenv('MEXC_API_KEY')
API_SECRET = os.getenv('MEXC_API_SECRET')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

BASE_URL = 'https://contract.mexc.com'

ALAVANCAGEM = 5
PERCENTUAL_DO_SALDO = float(os.getenv('PERCENTUAL_CAPITAL', 0.05))
TAKE_PROFIT = float(os.getenv('TAKE_PROFIT', 0.02))
STOP_LOSS = float(os.getenv('STOP_LOSS', 0.10))
TEMPO_CANCELAMENTO = int(os.getenv('TEMPO_CANCELAMENTO_MINUTOS', 5))

app = Flask(__name__)

def enviar_mensagem(texto):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": texto}
    requests.post(url, json=payload)

def assinatura(params):
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    return hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def requisicao(endpoint, params=None, method='GET'):
    if params is None:
        params = {}
    params['timestamp'] = int(time.time() * 1000)
    params['apiKey'] = API_KEY
    params['signature'] = assinatura(params)

    headers = {'Content-Type': 'application/json'}
    url = f"{BASE_URL}{endpoint}"

    if method == 'GET':
        return requests.get(url, params=params, headers=headers).json()
    elif method == 'POST':
        return requests.post(url, json=params, headers=headers).json()
    elif method == 'DELETE':
        return requests.delete(url, params=params, headers=headers).json()

def buscar_preco_atual(symbol):
    url = f"https://contract.mexc.com/api/v1/contract/price/{symbol}"
    response = requests.get(url)
    if response.ok:
        return float(response.json()['data']['lastPrice'])
    return None

def buscar_saldo():
    resposta = requisicao('/api/v1/private/account/assets')
    for item in resposta.get('data', []):
        if item['currency'] == 'USDT':
            return float(item['availableBalance'])
    return None

def enviar_ordem_limit(symbol, quantidade, preco):
    params = {
        "symbol": symbol,
        "price": round(preco, 4),
        "vol": round(quantidade, 3),
        "side": 1,
        "type": 1,
        "openType": 2,
        "positionId": 0,
        "leverage": ALAVANCAGEM
    }
    return requisicao('/api/v1/private/order/submit', params, method='POST')

def criar_ordens_tp_sl(symbol, volume, preco_entrada):
    preco_tp = round(preco_entrada * (1 + TAKE_PROFIT), 4)
    preco_sl = round(preco_entrada * (1 - STOP_LOSS), 4)

    ordem_tp = {
        "symbol": symbol,
        "price": preco_tp,
        "vol": volume,
        "side": 2,
        "type": 1,
        "openType": 2,
        "positionId": 0,
        "leverage": ALAVANCAGEM
    }

    ordem_sl = {
        "symbol": symbol,
        "price": preco_sl,
        "vol": volume,
        "side": 2,
        "type": 1,
        "openType": 2,
        "positionId": 0,
        "leverage": ALAVANCAGEM
    }

    requisicao('/api/v1/private/order/submit', ordem_tp, method='POST')
    requisicao('/api/v1/private/order/submit', ordem_sl, method='POST')

    enviar_mensagem(f"🎯 TP em {preco_tp} | 🛡 SL em {preco_sl}")

def cancelar_ordem(orderId):
    return requisicao('/api/v1/private/order/cancel', {"orderId": orderId}, method='DELETE')

def monitorar_ordem(orderId, symbol, quantidade, preco_entrada):
    inicio = time.time()
    while True:
        if time.time() - inicio > TEMPO_CANCELAMENTO * 60:
            cancelar_ordem(orderId)
            enviar_mensagem("⏳ Ordem cancelada por tempo!")
            break
        time.sleep(10)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    if 'message' in update:
        texto = update['message'].get('text', '')
        if texto == '/start':
            enviar_mensagem("✅ Bot iniciado e pronto para operar!")
        elif texto == '/status':
            enviar_mensagem("📊 Bot ativo e monitorando sinais!")
    return {'ok': True}

@app.route('/')
def home():
    return '✅ Bot de Futuros MEXC Online!'

def loop_sinais():
    while True:
        symbol = "APT_USDT"  # Substitua por sua lógica de sinal real
        preco_atual = buscar_preco_atual(symbol)
        if preco_atual:
            saldo = buscar_saldo()
            if saldo:
                valor_usado = saldo * PERCENTUAL_DO_SALDO
                preco_entrada = round(preco_atual * 0.999, 4)
                quantidade = valor_usado / preco_entrada
                resposta = enviar_ordem_limit(symbol, quantidade, preco_entrada)
                if resposta.get('code') == 0:
                    orderId = resposta['data']['orderId']
                    enviar_mensagem(f"🚀 Ordem LIMIT enviada para {symbol} a {preco_entrada}")
                    threading.Thread(target=monitorar_ordem, args=(orderId, symbol, quantidade, preco_entrada)).start()
                    criar_ordens_tp_sl(symbol, quantidade, preco_entrada)
        time.sleep(300)

if __name__ == "__main__":
    threading.Thread(target=loop_sinais).start()
    app.run(host="0.0.0.0", port=8080)
