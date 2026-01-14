from flask import Flask, jsonify, request, render_template_string
import csv
import os
from unicodedata import normalize

app = Flask(__name__)

# --- CONFIGURAÇÃO DO HTML ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rede Autorizada Soul</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background-color: #f4f6f8; color: #333; }
        h1 { text-align: center; color: #111; margin-bottom: 5px; }
        .subtitle { text-align: center; color: #666; margin-bottom: 30px; }
        .search-container { display: flex; gap: 10px; justify-content: center; margin-bottom: 30px; }
        input { padding: 12px 15px; width: 60%; border: 1px solid #ccc; border-radius: 6px; font-size: 16px; outline: none; }
        button { padding: 12px 25px; cursor: pointer; background: #000; color: #fff; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; }
        button:hover { background: #444; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
        .card { background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border-left: 5px solid #000; }
        .card h3 { margin: 0 0 10px 0; font-size: 1.2rem; color: #000; }
        .badge { background: #eee; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; color: #555; text-transform: uppercase; float: right; }
        .info-group { margin-bottom: 12px; font-size: 0.95rem; line-height: 1.5; }
        .info-group strong { display: block; font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
        .contact-links { margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap; }
        .btn-link { text-decoration: none; background: #f0f0f0; color: #333; padding: 6px 12px; border-radius: 4px; font-size: 0.85rem; font-weight: 600; }
        .btn-link.whatsapp { background: #25D366; color: #fff; }
        .btn-link.insta { background: #E1306C; color: #fff; }
        .error { text-align: center; padding: 20px; background: #fff; border-radius: 8px; color: #d9534f; grid-column: 1/-1; }
        .loading { text-align: center; color: #666; font-style: italic; grid-column: 1/-1; }
    </style>
</head>
<body>
    <h1>Encontre uma Loja Soul</h1>
    <p class="subtitle">{{ qtd }} autorizadas cadastradas</p>
    
    <div class="search-container">
        <input type="text" id="cidadeInput" placeholder="Digite Cidade ou Estado (ex: Itajaí, SP)...">
        <button onclick="buscar()">Buscar</button>
    </div>
    
    <div id="resultado" class="grid"></div>

    <script>
        document.getElementById("cidadeInput").addEventListener("keypress", function(event) {
            if (event.key === "Enter") { buscar(); }
        });

        async function buscar() {
            let termo = document.getElementById('cidadeInput').value;
            let btn = document.querySelector('button');
            let divRes = document.getElementById('resultado');
            
            if (!termo) { alert("Digite algo para buscar!"); return; }

            btn.innerText = 'Buscando...';
            btn.disabled = true;
            divRes.innerHTML = '<p class="loading">Carregando dados...</p>';
            
            try {
                let response = await fetch('/lojas?busca=' + termo);
                let dados = await response.json();
                
                let html = '';
                if(dados.length === 0) {
                    divRes.classList.remove('grid');
                    html = '<div class="error">Nenhuma loja encontrada para "'+termo+'".<br>Tente digitar apenas o nome da cidade ou a sigla do estado.</div>';
                } else {
                    divRes.classList.add('grid');
                    dados.forEach(item => {
                        let nome = item.nome || 'Loja Autorizada';
                        let perfil = item.perfil || 'Autorizada';
                        let cidade = item.municipio || '';
                        let uf = item.uf || '';
                        let endereco = item.endereço || '';
                        let num = item['numero/complemento'] || '';
                        let bairro = item.bairro || '';
                        let cep = item.cep || '';
                        let tel = item.telefone || '';
                        let contato = item.contato || '';
                        let email = item['e-mail'] || '';
                        let insta = item.instagram || '';
                        let sem = item['seg._a_sex.'] || '';
                        let sab = item['sábado'] || '';

                        html += `
                        <div class="card">
                            <span class="badge">${perfil}</span>
                            <h3>${nome}</h3>
                            
                            <div class="info-group">
                                <strong>Localização</strong>
                                ${cidade} - ${uf}<br>
                                ${endereco}, ${num}<br>
                                ${bairro} - CEP: ${cep}
                            </div>
                            
                            <div class="info-group">
                                <strong>Contato</strong>
                                ${contato ? `Falar com: ${contato}<br>` : ''}
                                ${tel} <br>
                                <span style="font-size: 0.85em; color: #666;">${email}</span>
                            </div>

                            ${ (sem || sab) ? `
                            <div class="info-group">
                                <strong>Horário</strong>
                                ${sem ? `Seg-Sex: ${sem}<br>` : ''}
                                ${sab ? `Sáb: ${sab}` : ''}
                            </div>` : ''}

                            <div class="contact-links">
                                ${tel ? `<a href="tel:${tel.replace(/[^0-9]/g, '')}" class="btn-link">Ligar</a>` : ''}
                                ${tel ? `<a href="https://wa.me/55${tel.replace(/[^0-9]/g, '')}" target="_blank" class="btn-link whatsapp">WhatsApp</a>` : ''}
                                ${insta ? `<a href="https://instagram.com/${insta.replace('@','').replace('/','')}" target="_blank" class="btn-link insta">Instagram</a>` : ''}
                            </div>
                        </div>`;
                    });
                }
                divRes.innerHTML = html;
            } catch (error) {
                console.error(error);
                divRes.innerHTML = '<p class="error">Ocorreu um erro ao buscar.</p>';
            } finally {
                btn.innerText = 'Buscar';
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""

# --- BACKEND (SERVIDOR PYTHON) ---

def remover_acentos(txt):
    if not txt: return ""
    # Esta função remove acentos para facilitar a busca
    return normalize('NFKD', str(txt)).encode('ASCII', 'ignore').decode('ASCII').lower()

def carregar_dados():
    lojas = []
    caminho = 'dados.csv'
    
    if not os.path.exists(caminho):
        return []

    try:
        try:
            arquivo = open(caminho, mode='r', encoding='utf-8-sig')
        except:
            arquivo = open(caminho, mode='r', encoding='latin-1')

        with arquivo as f:
            conteudo = f.read(2048)
            f.seek(0)
            delimitador = ';' if conteudo.count(';') > conteudo.count(',') else ','
            
            reader = csv.DictReader(f, delimiter=delimitador)
            
            for row in reader:
                item_limpo = {}
                for k, v in row.items():
                    if k:
                        chave = str(k).strip().lower().replace(' ', '_')
                        valor = str(v).strip() if v else ""
                        item_limpo[chave] = valor
                lojas.append(item_limpo)
                
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        
    return lojas

@app.route('/')
def home():
    dados = carregar_dados()
    return render_template_string(HTML_TEMPLATE, qtd=len(dados))

@app.route('/lojas')
def get_lojas():
    termo = request.args.get('busca', '').strip()
    todas = carregar_dados()
    
    if not termo:
        return jsonify(todas)
    
    termo_limpo = remover_acentos(termo)
    
    resultado = []
    for loja in todas:
        mun = remover_acentos(loja.get('municipio', ''))
        uf = remover_acentos(loja.get('uf', ''))
        nome = remover_acentos(loja.get('nome', ''))
        
        if (termo_limpo in mun) or (termo_limpo == uf) or (termo_limpo in nome):
            resultado.append(loja)
            
    return jsonify(resultado)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
