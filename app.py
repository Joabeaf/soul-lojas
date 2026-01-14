from flask import Flask, jsonify, request
import os

app = Flask(__name__)

# --- DADOS DAS LOJAS (DENTRO DO CÓDIGO) ---
# Aqui eliminamos o erro de leitura de arquivo.
# Você pode adicionar quantas lojas quiser seguindo esse modelo.
LOJAS_DB = [
    {
        "loja": "Soul Cycles Itajaí",
        "cidade": "Itajai",
        "estado": "SC",
        "endereco": "Rua Exemplo",
        "numero": "100",
        "telefone": "(47) 9999-9999"
    },
    {
        "loja": "Bike Shop Balneário",
        "cidade": "Balneario Camboriu",
        "estado": "SC",
        "endereco": "Av Atlantica",
        "numero": "500",
        "telefone": "(47) 8888-8888"
    },
    {
        "loja": "Pedal São Paulo",
        "cidade": "Sao Paulo",
        "estado": "SP",
        "endereco": "Av Paulista",
        "numero": "1000",
        "telefone": "(11) 9999-9999"
    }
]
# ------------------------------------------

@app.route('/')
def home():
    return """
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1>Busca Soul (Modo Seguro)</h1>
        <p>Se você está vendo isso, o erro 500 sumiu!</p>
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
            if(dados.length === 0) html = '<p>Nenhuma loja encontrada.</p>';
            
            dados.forEach(loja => {
                html += `<div style="border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px;">
                    <h3>${loja.loja}</h3>
                    <p><strong>Local:</strong> ${loja.cidade} - ${loja.estado}</p>
                    <p><strong>Endereço:</strong> ${loja.endereco}, ${loja.numero}</p>
                    <p><strong>Telefone:</strong> ${loja.telefone}</p>
                </div>`;
            });
            document.getElementById('resultado').innerHTML = html;
        }
    </script>
    """

@app.route('/lojas')
def get_lojas():
    cidade_busca = request.args.get('cidade', '').lower()
    
    # Se não digitou nada, retorna tudo
    if not cidade_busca:
        return jsonify(LOJAS_DB)
    
    # Filtra a lista que está na memória
    resultado = [
        loja for loja in LOJAS_DB 
        if cidade_busca in loja['cidade'].lower()
    ]
    return jsonify(resultado)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
