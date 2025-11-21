import os
from flask import Flask, render_template, request, jsonify
import requests
import mercadopago

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
# Token de Produção do Mercado Pago
MP_ACCESS_TOKEN = "APP_USR-2045481871192189-112010-1b7034c359c46bcc392d95626b6bfdb0-269196602"

# Token do Melhor Envio (Atualizado)
TOKEN_MELHOR_ENVIO = "rbermXVJIBsVCsmmG4SvYNamoN5i5Q96JlMs7XFf"
CEP_ORIGEM = "58985000"

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

# --- ROTA DE PAGAMENTO ---
@app.route('/api/checkout-mp', methods=['POST'])
def criar_pagamento_mp():
    try:
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
            }
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

# --- ROTA WEBHOOK ---
@app.route('/api/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if data.get("action") == "payment.created" or data.get("action") == "payment.updated" or data.get("type") == "payment":
            payment_id = data.get("data", {}).get("id")
            if payment_id:
                pagamento_info = sdk.payment().get(payment_id)
                if pagamento_info["status"] == 200:
                    status_atual = pagamento_info["response"]["status"]
                    valor_pago = pagamento_info["response"]["transaction_amount"]
                    print(f"🔔 WEBHOOK: Pagamento {payment_id} está: {status_atual} | Valor: {valor_pago}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print("Erro no Webhook:", e)
        return jsonify({"error": str(e)}), 500

# --- API FRETE MELHOR ENVIO (CORRIGIDA) ---
@app.route('/api/calcular-frete', methods=['POST'])
def calcular_frete():
    data = request.get_json()
    cep_destino = data.get('cep', '').replace('-', '').replace('.', '')
    
    if not cep_destino or len(cep_destino) != 8:
        return jsonify({'erro': 'CEP inválido'}), 400

    opcoes = [{'servico': 'Retirada na Loja', 'preco': '0.00', 'prazo': '1 dia útil', 'obs': 'Grátis'}]

    try:
        url = "https://melhorenvio.com.br/api/v2/me/shipment/calculate"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {TOKEN_MELHOR_ENVIO}',
            'User-Agent': 'Loja Confiance'
        }
        # Payload fixo para teste (ajustar conforme necessidade real dos produtos)
        payload = {
            "from": {"postal_code": CEP_ORIGEM},
            "to": {"postal_code": cep_destino},
            "products": [{"id": "x", "width": 15, "height": 5, "length": 20, "weight": 0.3, "insurance_value": 50.0, "quantity": 1}]
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # --- DEBUG NO TERMINAL ---
        if response.status_code != 200:
            print(f"❌ ERRO MELHOR ENVIO (Status {response.status_code}):")
            print(response.text)
        # -------------------------

        if response.status_code == 200:
            dados_api = response.json()
            for frete in dados_api:
                # Lógica corrigida para ser case-insensitive
                nome_empresa = frete.get('company', {}).get('name', '').lower()
                
                if "error" not in frete and "price" in frete and "correios" in nome_empresa:
                    opcoes.append({
                        'servico': frete['name'],
                        'preco': f"{float(frete['price']):.2f}",
                        'prazo': f"{frete['delivery_time']} dias",
                        'obs': frete['company']['name']
                    })
        
        return jsonify(opcoes)
        
    except Exception as e:
        print(f"❌ EXCEÇÃO AO CALCULAR FRETE: {str(e)}")
        # Fallback para não travar a venda
        opcoes.append({'servico': 'PAC (Simulado)', 'preco': '25.90', 'prazo': '8 dias', 'obs': 'Correios'})
        return jsonify(opcoes)

if __name__ == '__main__':
    app.run(debug=True)