
README - BOT MEXC FUTUROS (LONG, LIMIT, TELEGRAM)

✅ O QUE O BOT FAZ:
- Recebe sinais RSI e entra automaticamente em LONG na MEXC Futures
- Envia ordens LIMIT com alavancagem 5x (configurável)
- Cria TP e SL como ordens LIMIT (não OCO)
- Cancela ordens não executadas após X minutos
- Envia alertas no Telegram

🛠 CONFIGURAÇÕES NO .ENV:
- MEXC_API_KEY=
- MEXC_API_SECRET=
- TELEGRAM_BOT_TOKEN=
- TELEGRAM_CHAT_ID=
- PERCENTUAL_CAPITAL=0.05
- TAKE_PROFIT=0.02
- STOP_LOSS=0.10
- TEMPO_CANCELAMENTO_MINUTOS=5

📁 COMO USAR:
1. Preencha o .env com suas chaves
2. Suba os arquivos no seu GitHub
3. Conecte o Railway ao seu repositório e faça deploy
4. Envie /start no Telegram para testar
