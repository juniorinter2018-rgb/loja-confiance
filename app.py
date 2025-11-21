import os
import requests
from flask import Flask, render_template, request, jsonify
import mercadopago

app = Flask(__name__)

# --- CONFIGURAÇÕES DO MERCADO PAGO ---
# (Seu token de produção do MP)
MP_ACCESS_TOKEN = "APP_USR-2045481871192189-112010-1b7034c359c46bcc392d95626b6bfdb0-269196602"

# --- CONFIGURAÇÕES MELHOR ENVIO (PRODUÇÃO) ---
# URL Oficial (Sem Sandbox)
MELHOR_ENVIO_URL = "https://melhorenvio.com.br" 

# SEU TOKEN DE ACESSO
MELHOR_ENVIO_TOKEN = "rbermXVJIBsVCsmmG4SvYNamoN5i5Q96JlMs7XFf"

# DADOS DA LOJA (NECESSÁRIOS PARA A API)
CEP_ORIGEM = "58000000"  # Substitua pelo CEP real de onde sai a mercadoria (Ex: João Pessoa)
EMAIL_LOJA = "contato@lojacofiance.com.br" # Email técnico responsável pela integração

BASE_URL = os.getenv("SITE_URL", "http://localhost:5000")
sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# --- DADOS DOS PRODUTOS (SIMULANDO BANCO DE DADOS) ---
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

# --- INTEGRAÇÃO MELHOR ENVIO (CÁLCULO DE FRETE REAL) ---
@app.route('/api/calcular-frete', methods=['POST'])
def calcular_frete():
    try:
        data = request.get_json()
        cep_destino = data.get('cep', '').replace('-', '').replace('.', '')
        carrinho_cliente = data.get('carrinho', [])

        if not cep_destino or len(cep_destino) != 8:
            return jsonify({'erro': 'CEP inválido'}), 400
        
        if not carrinho_cliente:
            return jsonify([]) # Carrinho vazio

        # Montar payload para o Melhor Envio
        produtos_payload = []
        valor_seguro_total = 0

        for item_c in carrinho_cliente:
            # Pega dados reais do produto (peso/dimensões) pelo ID
            prod_db = next((p for p in PRODUTOS if p['id'] == int(item_c['id'])), None)
            
            if prod_db:
                produtos_payload.append({
                    "id": str(prod_db['id']),
                    "width": prod_db['largura'],
                    "height": prod_db['altura'],
                    "length": prod_db['comprimento'],
                    "weight": prod_db['peso'],
                    "insurance_value": prod_db['preco'],
                    "quantity": 1 
                })
                valor_seguro_total += prod_db['preco']

        payload = {
            "from": { "postal_code": CEP_ORIGEM },
            "to": { "postal_code": cep_destino },
            "products": produtos_payload,
            "options": {
                "receipt": False, 
                "own_hand": False, 
                "insurance_value": valor_seguro_total
            }
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MELHOR_ENVIO_TOKEN}",
            "User-Agent": EMAIL_LOJA
        }

        # Requisição para API OFICIAL
        response = requests.post(f"{MELHOR_ENVIO_URL}/api/v2/me/shipment/calculate", json=payload, headers=headers, timeout=15)
        
        if response.status_code != 200:
            # Se der erro (ex: token expirado), mostramos no console
            print(f"ERRO MELHOR ENVIO ({response.status_code}):", response.text)
            return jsonify([]) 

        opcoes_frete = []
        dados_api = response.json()

        # Filtrar transportadoras
        for oferta in dados_api:
            if "price" in oferta and "delivery_time" in oferta:
                if oferta.get("error"): continue

                nome_servico = f"{oferta['company']['name']} {oferta['name']}"
                
                opcoes_frete.append({
                    'servico': nome_servico,
                    'preco': oferta['price'],
                    'prazo': f"{oferta['delivery_time']} dias úteis",
                    'obs': 'Rastreado',
                    'id_servico': oferta['id']
                })

        # Ordenar: mais barato primeiro
        opcoes_frete.sort(key=lambda x: float(x['preco']))

        return jsonify(opcoes_frete)

    except Exception as e:
        print("ERRO SERVIDOR FRETE:", e)
        return jsonify({'erro': str(e)}), 500


# --- CHECKOUT (MERCADO PAGO) ---
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
            },
            "auto_return": "approved"
        }

        resposta = sdk.preference().create(preference_data)
        pagamento = resposta["response"]

        if resposta["status"] not in [200, 201]:
            return jsonify({'erro': pagamento.get('message', 'Erro MP')}), 400

        return jsonify({'link_pagamento': pagamento['init_point']})

    except Exception as e:
        print("ERRO SERVIDOR:", e)
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)