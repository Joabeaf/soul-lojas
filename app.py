from flask import Flask, jsonify, request
import csv
import os

app = Flask(__name__)

def carregar_dados():
    lojas = []
    # Verifica se o arquivo existe antes de tentar ler
    if not os.path.exists('dados.csv'):
        print("ERRO: O arquivo dados.csv não foi encontrado.")
        return []

    try:
        # Lê o arquivo CSV usando a biblioteca nativa do Python (super leve)
        with open('dados.csv', mode='r', encoding='utf-8-sig') as f:
            # O delimiter=';' ou ',' depende do seu Excel. 
            # O Python tenta adivinhar, mas se der erro, trocamos para delimiter=';'
            leitor = csv.DictReader(f) 
            
            for linha in leitor:
                # Limpeza: remove espaços das chaves e valores
                item_limpo = {}
                for k, v in linha.items():
                    chave = str(k).strip().lower().replace(' ', '_')
                    valor = str(v).strip()
                    item_limpo[chave] = valor
                lojas.append(item_limpo)
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        
    return lojas

@app.route('/')
def home():
    # Carrega os dados para ver se está funcionando
    dados = carregar_dados()
    qtd = len(dados)
    
    return f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1>Busca Soul</h1>
        <p>Status: <strong>{qtd} lojas carregadas.</strong></p>
        <hr>
        <p>Digite sua cidade:</p>
        <input type="text" id="cidadeInput" placeholder="Ex: Itajai">
        <button onclick="buscar()">Buscar</button>
        <div id="resultado" style="margin-top: 20px;"></div>
    </div>

    <script>
        async function buscar() {
            let cidade = document.getElementById('cidadeInput').value;
            let response = await fetch('/lojas?cidade=' + cidade);
            let dados = await response.json();
            
            let html = '';
            if(dados.length === 0) html = '<p>Nenhuma loja encontrada nesta cidade.</p>';
            
            dados.forEach(loja => {
                // Tenta encontrar o nome da loja em várias colunas possíveis
                let nome = loja.loja || loja.nome || loja.revenda || 'Loja Soul';
                let end = loja.endereço || loja.endereco || '';
                let num = loja.número || loja.numero || '';
                let tel = loja.telefone || loja.celular || '';
                let cid = loja.cidade || '';
                let est = loja.estado || loja.uf || '';

                html += `<div style="border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px;">
                    <h3>${nome}</h3>
                    <p><strong>Local:</strong> ${cid} - ${est}</p>
                    <p><strong>Endereço:</strong> ${end}, ${num}</p>
                    <p><strong>Contato:</strong> ${tel}</p>
                </div>`;
            });
            document.getElementById('resultado').innerHTML = html;
        }
    </script>
    """

@app.route('/lojas')
def get_lojas():
    cidade_busca = request.args.get('cidade', '').lower()
    todas = carregar_dados()
    
    if not cidade_busca:
        return jsonify(todas)
    
    # Filtro simples
    resultado = [
        loja for loja in todas 
        if cidade_busca in str(loja.get('cidade', '')).lower()
    ]
    return jsonify(resultado)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
