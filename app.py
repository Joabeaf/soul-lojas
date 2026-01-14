from flask import Flask, jsonify, request
import csv
import os

app = Flask(__name__)

def carregar_dados():
    lojas = []
    caminho_arquivo = 'dados.csv'
    
    if not os.path.exists(caminho_arquivo):
        print("ALERTA: Arquivo dados.csv não encontrado.")
        return []

    try:
        # Tenta ler com encoding UTF-8 (padrão) ou Latin-1 (comum no Excel Brasil)
        try:
            arquivo = open(caminho_arquivo, mode='r', encoding='utf-8-sig')
        except:
            arquivo = open(caminho_arquivo, mode='r', encoding='latin-1')

        with arquivo as f:
            # O Excel as vezes usa ponto-e-virgula, as vezes virgula. Vamos testar.
            amostra = f.read(1024)
            f.seek(0)
            delimitador = ';' if ';' in amostra else ','
            
            reader = csv.DictReader(f, delimiter=delimitador)
            
            for row in reader:
                # Limpa os dados para evitar erros de chaves (Ex: "Cidade " vira "cidade")
                loja_limpa = {}
                for k, v in row.items():
                    if k: # Só processa se a coluna tiver nome
                        chave = str(k).strip().lower().replace(' ', '_')
                        valor = str(v).strip() if v else ""
                        loja_limpa[chave] = valor
                lojas.append(loja_limpa)
                
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        
    return lojas

@app.route('/')
def home():
    dados = carregar_dados()
    qtd = len(dados)
    
    return f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #333;">Encontre uma Loja Soul</h1>
        <p>Temos <strong>{qtd}</strong> parceiros cadastrados.</p>
        
        <div style="display: flex; gap: 10px; margin-bottom: 20px;">
            <input type="text" id="cidadeInput" placeholder="Digite sua cidade..." style="padding: 10px; width: 100%;">
            <button onclick="buscar()" style="padding: 10px 20px; cursor: pointer; background: #000; color: #fff; border: none;">Buscar</button>
        </div>
        
        <div id="resultado"></div>
    </div>

    <script>
        async function buscar() {
            let cidade = document.getElementById('cidadeInput').value;
            let btn = document.querySelector('button');
            btn.innerText = 'Buscando...';
            
            let response = await fetch('/lojas?cidade=' + cidade);
            let dados = await response.json();
            
            let html = '';
            if(dados.length === 0) html = '<p style="color: red">Nenhuma loja encontrada nesta cidade.</p>';
            
            dados.forEach(loja => {
                // Tenta achar os campos independente do nome exato no Excel
                let nome = loja.loja || loja.nome_fantasia || loja.nome || 'Loja Autorizada';
                let end = loja.endereço || loja.endereco || '';
                let num = loja.número || loja.numero || '';
                let bairro = loja.bairro || '';
                let tel = loja.telefone || loja.celular || loja.contato || '';
                let cidade = loja.cidade || '';
                let uf = loja.estado || loja.uf || '';

                html += `<div style="border: 1px solid #ddd; padding: 15px; margin-bottom: 10px; border-radius: 8px; background: #f9f9f9;">
                    <h3 style="margin: 0 0 10px 0;">${nome}</h3>
                    <p style="margin: 5px 0;">📍 <strong>${cidade} - ${uf}</strong></p>
                    <p style="margin: 5px 0;">🏠 ${end}, ${num} - ${bairro}</p>
                    <p style="margin: 5px 0;">📞 <a href="tel:${tel}">${tel}</a></p>
                </div>`;
            });
            
            document.getElementById('resultado').innerHTML = html;
            btn.innerText = 'Buscar';
        }
    </script>
    """

@app.route('/lojas')
def get_lojas():
    cidade_busca = request.args.get('cidade', '').strip().lower()
    todas = carregar_dados()
    
    if not cidade_busca:
        return jsonify(todas)
    
    resultado = [
        loja for loja in todas 
        if cidade_busca in str(loja.get('cidade', '')).lower()
    ]
    return jsonify(resultado)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
