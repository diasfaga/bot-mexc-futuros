from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# Dados falsos (mock)
data = {
    'saldo': {
        'USDT': 1000.00,
        'futuros': 750.00,
        'margem': 500.00
    },
    'posicoes': [
        {'par': 'BTC/USDT', 'lado': 'LONG', 'quantidade': 0.01, 'pnl': '+5%'},
        {'par': 'ETH/USDT', 'lado': 'SHORT', 'quantidade': 0.5, 'pnl': '-2%'},
    ],
    'logs': [
        'Análise: BTC/USDT rompeu resistência',
        'Sinal: ETH/USDT abaixo da média de 50',
    ]
}

# Página principal com saldo e posições
@app.route('/')
def home():
    return render_template_string('''
    <h1>Painel Trader MEXC</h1>
    <h2>Saldo</h2>
    <ul>
        <li>USDT: {{ saldo['USDT'] }}</li>
        <li>Futuros: {{ saldo['futuros'] }}</li>
        <li>Margem: {{ saldo['margem'] }}</li>
    </ul>
    
    <h2>Posições Abertas</h2>
    <ul>
    {% for p in posicoes %}
        <li>{{ p['par'] }} - {{ p['lado'] }} - {{ p['quantidade'] }} - PnL: {{ p['pnl'] }}</li>
    {% endfor %}
    </ul>

    <h2>Logs / Sinais</h2>
    <ul>
    {% for log in logs %}
        <li>{{ log }}</li>
    {% endfor %}
    </ul>

    <p><em>Versão demo com dados fictícios.</em></p>
    ''', saldo=data['saldo'], posicoes=data['posicoes'], logs=data['logs'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
