import os
from flask import Flask, render_template, request, jsonify
import requests
import mercadopago

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
# Token de Produção do Mercado Pago
MP_ACCESS_TOKEN = "APP_USR-2045481871192189-112010-1b7034c359c46bcc392d95626b6bfdb0-269196602"

# Token do Melhor Envio
TOKEN_MELHOR_ENVIO = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxIiwianRpIjoiZGUyNzExODI1NjZiYjhhYjFiYTI1OTgwY2U3YzZiN2U4NjJmN2I5MmEzMzNjMWE0ZjgwZDI4NmU2ZDEyMjVkNDFmNGYyNDhlNTk3Yjc2ZDgiLCJpYXQiOjE3NjM0OTQzMTUuMjYzNzk3LCJuYmYiOjE3NjM0OTQzMTUuMjYzNzk4LCJleHAiOjE3OTUwMzAzMTUuMjUwNTQ1LCJzdWIiOiJhMDYzN2ZhNi05NmI2LTQ3NzEtOWQxZi0wZGE4NzgxOTdkMWYiLCJzY29wZXMiOlsiY2FydC1yZWFkIiwiY2FydC13cml0ZSIsImNvbXBhbmllcy1yZWFkIiwiY291cG9ucy1yZWFkIiwiY291cG9ucy13cml0ZSIsIm5vdGlmaWNhdGlvbnMtcmVhZCIsIm9yZGVycy1yZWFkIiwicHJvZHVjdHMtcmVhZCIsInByb2R1Y3RzLWRlc3Ryb3kiLCJwcm9kdWN0cy13cml0ZSIsInB1cmNoYXNlcy1yZWFkIiwic2hpcHBpbmctY2FsY3VsYXRlIiwic2hpcHBpbmctY2FuY2VsIiwic2hpcHBpbmctY2hlY2tvdXQiLCJzaGlwcGluZy1jb21wYW5pZXMiLCJzaGlwcGluZy1nZW5lcmF0ZSIsInNoaXBwaW5nLXByZXZpZXciLCJzaGlwcGluZy1wcmludCIsInNoaXBwaW5nLXNoYXJlIiwic2hpcHBpbmctdHJhY2tpbmciLCJlY29tbWVyY2Utc2hpcHBpbmciLCJ0cmFuc2FjdGlvbnMtcmVhZCIsInVzZXJzLXJlYWQiLCJ1c2Vycy13cml0ZSIsIndlYmhvb2tzLXJlYWQiLCJ3ZWJob29rcy13cml0ZSIsIndlYmhvb2tzLWRlbGV0ZSIsInRkZWFsZXItd2ViaG9vayJdfQ.trKjLJ9rZZyrpRDEpDSzz-LdEFlrjiZRMNFOOP3MQO1RUmprD1y9cHIt0waCHrWXxLWmP8L_rYrYoWeYrIzovGhdMkCbsc68Pusl2eYR2cUjJMc_zS2om_SUDJbOyo2xNCliybQP5nithlVeuU3jX_0xDGm3snqcCE0zg9U1mt4inEOUVnUSZrTStKI82H2i8A7tAv4KRu0ZlpgUoxB44eNc9hWf9roe-38oqJUDYRHrTMPCKXJ4isteeUxUYfH1zegLaI5T9ydjUJEPHaXl-X4IcdC0Ea5dv1Xxz2IghH6VsdYpYYaJ7SR7APUTqEFoiKtwGE-n-752c3X6DQyF4JsBblIVP7SuUfiHPuSi-ayR9Bxr8EiYNsDGFR8C8yD7W7unBhFBHRxcs63nYSbjHdvLi2CFmNMAEs1j_Ps-o2uHHYlGn9a8GseZ_xXFrl3PM9wfvHemlinDgIQQvO2o4sG8svay4Tiqy-Ercm3RLJ0ueEEDff9S4LxBnacOqBDQ2rzoYt8Fo6KdLl3EWl3REnb4DBfMk0Ufp5s6vrxb7MjpmV29d86xCbeqS4H1Cj4e8RHz3NiTHKPdMlfCUbEvU61NWJHxLH_5CAyp5hpqNI4PCSlYG7oekSQoQ1kAAMdj9-ix-dmyibqXcdfWdrw9LzFOCO39O300tCp-fPz-fW4"
CEP_ORIGEM = "58985000"

# Define a URL base: Se tiver a variável de ambiente (Render), usa ela. Se não, usa localhost.
# IMPORTANTE: No Render, o link não pode ter a barra "/" no final.
BASE_URL = os.getenv("SITE_URL", "http://localhost:5000")

# Inicializa SDK
sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# --- DADOS DOS PRODUTOS ---
PRODUTOS = [
    { "id": 101, "nome": "Blusa de Seda Bege", "preco": 189.90, "imagem": 'blusa_seda.jpg', "descricao": "Blusa sofisticada em seda pura.", "cores": ["#FFDAB9", "#C08081"], "vendidos": 432, "nota": 4.9, "peso": 0.3, "altura": 4, "largura": 12, "comprimento": 17 },
    { "id": 102, "nome": "Calça Pantalona Preta", "preco": 229.00, "imagem": 'pantalona.jpg', "descricao": "Calça de corte amplo e elegante.", "cores": ["#3E3B3B", "#FFFFFF"], "vendidos": 128, "nota": 4.8, "peso": 0.5, "altura": 5, "largura": 20, "comprimento": 25 },
    { "id": 103, "nome": "Vestido Midi Estampado", "preco": 299.90, "imagem": 'vestido_midi.jpg', "descricao": "Vestido midi com estampa exclusiva.", "cores": ["#C08081", "#E0FFFF"], "vendidos": 850, "nota": 5.0, "peso": 0.4, "altura": 5, "largura": 20, "comprimento": 20 },
    { "id": 104, "nome": "Saia Lápis Xadrez", "preco": 165.50, "imagem": 'saia_lapis.jpg', "descricao": "Saia lápis clássica.", "cores": ["#3E3B3B", "#C08081"], "vendidos": 65, "nota": 4.7, "peso": 0.3, "altura": 4, "largura": 15, "comprimento": 20 },
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

        # Monta itens
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

        # Configuração da Preferência com URL DINÂMICA
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
            msg = pagamento.get('message', 'Erro ao criar preferência')
            return jsonify({'erro': msg}), 400

        return jsonify({'link_pagamento': pagamento['init_point']})

    except Exception as e:
        print("ERRO SERVIDOR:", e)
        return jsonify({'erro': str(e)}), 500


# --- API FRETE MELHOR ENVIO ---
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
        payload = {
            "from": {"postal_code": CEP_ORIGEM},
            "to": {"postal_code": cep_destino},
            "products": [{"id": "x", "width": 15, "height": 5, "length": 20, "weight": 0.3, "insurance_value": 50.0, "quantity": 1}]
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            dados_api = response.json()
            for frete in dados_api:
                if "error" not in frete and "price" in frete:
                    if "Correios" in frete.get('company', {}).get('name', ''):
                        opcoes.append({
                            'servico': frete['name'],
                            'preco': f"{float(frete['price']):.2f}",
                            'prazo': f"{frete['delivery_time']} dias",
                            'obs': frete['company']['name']
                        })
            return jsonify(opcoes)
        else:
            return jsonify(opcoes)

    except Exception as e:
        opcoes.append({'servico': 'PAC (Simulado)', 'preco': '25.90', 'prazo': '8 dias', 'obs': 'Correios'})
        return jsonify(opcoes)

if __name__ == '__main__':
    app.run(debug=True)