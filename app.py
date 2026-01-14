from flask import Flask, jsonify, request
import pandas as pd
import os

app = Flask(__name__)

# Configuração
# Se seu arquivo tiver outro nome, mude APENAS AQUI em baixo:
NOME_DO_ARQUIVO = 'dados.xlsx' 

try:
    # Agora usamos read_excel e especificamos a engine openpyxl
    df = pd.read_excel(NOME_DO_ARQUIVO, engine='openpyxl')
    
    # Limpeza: remove espaços e deixa tudo minúsculo no cabeçalho
    df.columns = [str(c).strip().replace(' ', '_').lower() for c in df.columns]
    
    # Converte tudo para texto (string) para evitar erros com números/CEPs
    df = df.astype(str)
    
    # Remove linhas que estejam vazias (acontece muito em Excel)
    df = df.dropna(how='all')
    
except Exception as e:
    print(f"ERRO CRÍTICO AO LER EXCEL: {e}")
    df = pd.DataFrame()

@app.route('/')
def home():
    return """
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1>Busca Soul (Versão Excel)</h1>
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
            if(dados.length === 0) html = '<p>Nada encontrado.</p>';
            
            dados.forEach(loja => {
                // Tenta pegar o nome da loja, ou usa um padrão
                let nome = loja.loja || loja.nome_fantasia || 'Loja Soul';
                
                html += `<div style="border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px;">
                    <h3>${nome}</h3>
                    <p><strong>Cidade:</strong> ${loja.cidade} - ${loja.estado}</p>
                    <p><strong>Endereço:</strong> ${loja.endereço || ''}, ${loja.número || ''}</p>
                    <p><strong>Telefone:</strong> ${loja.telefone || ''}</p>
                </div>`;
            });
            document.getElementById('resultado').innerHTML = html;
        }
    </script>
    """

@app.route('/lojas')
def get_lojas():
    cidade_busca = request.args.get('cidade')
    
    if df.empty:
        return jsonify([])

    if cidade_busca:
        # Filtra onde a cidade contém o texto (insensível a maiúsculas)
        # O 'nan' é para ignorar células vazias
        resultado = df[df['cidade'].str.contains(cidade_busca, case=False, na=False)]
    else:
        resultado = df
        
    return jsonify(resultado.to_dict(orient='records'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
