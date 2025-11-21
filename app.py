import os
from flask import Flask, render_template, request, jsonify
import mercadopago
from dotenv import load_dotenv  # IMPORTA A FERRAMENTA DE SEGURANÇA

# CARREGA O COFRE (.ENV)
load_dotenv()

app = Flask(__name__)

# --- CONFIGURAÇÕES SEGURAS ---
# Agora o Python busca a chave no cofre. Se não achar, avisa.
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

if not MP_ACCESS_TOKEN:
    print("⚠️ AVISO: Token do Mercado Pago não encontrado no arquivo .env")

BASE_URL = os.getenv("SITE_URL", "http://localhost:5000")
sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# --- DADOS DOS PRODUTOS ---
PRODUTOS = [
    { "id": 101, "nome": "Blusa de Seda Bege", "preco_original": 259.90, "preco": 189.90, "imagem": 'blusa_seda.jpg', "descricao": "Blusa sofisticada.", "cores": ["#FFDAB9", "#C08081"], "vendidos": 432, "nota": 4.9, "peso": 0.3, "altura": 4, "largura": 12, "comprimento": 17 },
    { "id": 102, "nome": "Calça Pantalona Preta", "preco_original": 299.90, "preco": 229.00, "imagem": 'pantalona.jpg', "descricao": "Calça de corte amplo.", "cores": ["#3E3B3B", "#FFFFFF"], "vendidos": 128, "nota": 4.8, "peso": 0.5, "altura": 5, "largura": 20, "comprimento": 25 },
    { "id": 103, "nome": "Vestido Midi Estampado", "preco_original": 399.90, "preco": 299.90, "imagem": 'vestido_midi.jpg', "descricao": "Vestido midi exclusivo.", "cores": ["#C08081", "#E0FFFF"], "vendidos": 850, "nota": 5.0, "peso": 0.4, "altura": 5, "largura": 20, "comprimento": 20 },
    { "id": 104, "nome": "Saia Lápis Xadrez", "preco_original": 219.50, "preco": 165.50, "imagem": 'saia_lapis.jpg', "descricao": "Saia lápis clássica.", "cores": ["#3E3B3B", "#C08081"], "vendidos": 65, "nota": 4.7, "peso": 0.3, "altura": 4, "largura": 15, "comprimento": 20 },
]

@app.route('/')
def home():
    termo_busca = request.args.get('q')
    if termo_busca:
        produtos_exibidos = [p for p in PRODUTOS if termo_busca.lower() in p['nome'].lower()]
    else:
        produtos_exibidos = PRODUTOS
    return render_template('index.html', produtos=produtos_exibidos, busca_atual=termo_busca)

@app.route('/produto/<int:id_produto>')
def detalhes_produto(id_produto):
    produto_encontrado = next((item for item in PRODUTOS if item['id'] == id_produto), None)
    if produto_encontrado:
        return render_template('detalhes.html', produto=produto_encontrado)
    return "Produto não encontrado", 404

@app.route('/carrinho')
def carrinho():
    return render_template('carrinho.html')

@app.route('/favoritos')
def favoritos():
    return render_template('favoritos.html')

@app.route('/sucesso')
def sucesso():
    return render_template('sucesso.html')

# --- API FRETE MANUAL ---
@app.route('/api/calcular-frete', methods=['POST'])
def calcular_frete():
    data = request.get_json()
    cep_destino = data.get('cep', '').replace('-', '').replace('.', '')
    
    if not cep_destino or len(cep_destino) < 8:
        return jsonify({'erro': 'CEP inválido'}), 400

    opcoes = [
        {'servico': 'PAC (Normal)', 'preco': '25.90', 'prazo': '5 a 10 dias', 'obs': 'Entrega Econômica'},
        {'servico': 'SEDEX (Rápido)', 'preco': '48.50', 'prazo': '2 a 4 dias', 'obs': 'Mais Rápido'}
    ]

    # Regra de Retirada na Loja (Santana de Mangueira)
    if cep_destino == '58985000':
        opcoes.append({'servico': 'Retirada na Loja', 'preco': '0.00', 'prazo': 'Disponível hoje', 'obs': 'Grátis'})

    return jsonify(opcoes)

# --- ROTA DE PAGAMENTO ---
@app.route('/api/checkout-mp', methods=['POST'])
def criar_pagamento_mp():
    try:
        # Verificação de Segurança Extra: Se não tiver token, não deixa vender
        if not MP_ACCESS_TOKEN:
            return jsonify({'erro': 'Erro de configuração no servidor (Token ausente)'}), 500

        dados = request.get_json()
        carrinho = dados.get('carrinho', [])
        frete_valor = float(dados.get('frete', 0))
        
        if not carrinho:
            return jsonify({'erro': 'Carrinho vazio'}), 400

        itens_mp = []
        for item in carrinho:
            itens_mp.append({
                "id": str(item['id']),
                "title": item['nome'],
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": float(item['preco'])
            })
        
        if frete_valor > 0:
            itens_mp.append({
                "title": "Frete e Envio",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": frete_valor
            })

        preference_data = {
            "items": itens_mp,
            "back_urls": {
                "success": f"{BASE_URL}/sucesso",
                "failure": f"{BASE_URL}/carrinho",
                "pending": f"{BASE_URL}/carrinho"
            },
            "auto_return": "approved"
        }

        resposta = sdk.preference().create(preference_data)
        pagamento = resposta["response"]

        if resposta["status"] not in [200, 201]:
            print("ERRO MP:", pagamento)
            return jsonify({'erro': pagamento.get('message', 'Erro MP')}), 400

        return jsonify({'link_pagamento': pagamento['init_point']})

    except Exception as e:
        print("ERRO SERVIDOR:", e)
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    # Configuração segura de debug
    debug_mode = os.getenv("FLASK_DEBUG", "False") == "True"
    app.run(debug=debug_mode)