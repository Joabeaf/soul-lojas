from flask import Flask, jsonify, request
import pandas as pd
import os

app = Flask(__name__)

# Lê o CSV assim que o site liga
# Certifique-se que o arquivo no GitHub se chama 'dados.csv'
try:
    df = pd.read_csv('dados.csv')
    # Limpeza básica nos nomes das colunas
    df.columns = [c.strip().replace(' ', '_').lower() for c in df.columns]
except Exception as e:
    df = pd.DataFrame() # Cria vazio se der erro
    print(f"Erro ao ler CSV: {e}")

@app.route('/')
def home():
    return """
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1>Busca de Revendas Soul</h1>
        <p>Digite sua cidade para encontrar uma loja:</p>
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
            if(dados.length === 0) html = '<p>Nenhuma loja encontrada.</p>';
            
            dados.forEach(loja => {
                html += `<div style="border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px;">
                    <h3>${loja.loja || 'Loja'}</h3>
                    <p><strong>Cidade:</strong> ${loja.cidade} - ${loja.estado}</p>
                    <p><strong>Endereço:</strong> ${loja.endereço}, ${loja.número}</p>
                    <p><strong>Telefone:</strong> ${loja.telefone}</p>
                </div>`;
            });
            document.getElementById('resultado').innerHTML = html;
        }
    </script>
    """

@app.route('/lojas')
def get_lojas():
    cidade = request.args.get('cidade')
    
    if df.empty:
        return jsonify([])

    if cidade:
        # Filtra onde a cidade contém o texto digitado (insensível a maiúsculas)
        resultado = df[df['cidade'].str.contains(cidade, case=False, na=False)]
    else:
        resultado = df
        
    return jsonify(resultado.to_dict(orient='records'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
