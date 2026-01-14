from flask import Flask, jsonify, request, render_template_string, redirect, url_for
import sqlite3
import csv
import os
from geopy.geocoders import Nominatim
from unicodedata import normalize

app = Flask(__name__)

# Configuração do Banco de Dados
DB_NAME = "lojas.db"

# HTML DO SITE (PÚBLICO)
HTML_PUBLICO = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rede Autorizada Soul</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { font-family: 'Segoe UI', sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f4f6f8; }
        h1, .subtitle { text-align: center; }
        #map { height: 400px; width: 100%; border-radius: 12px; margin-bottom: 20px; border: 2px solid #ddd; z-index: 1; }
        .search-box { display: flex; gap: 10px; justify-content: center; margin-bottom: 20px; }
        input { padding: 12px; width: 60%; border: 1px solid #ccc; border-radius: 6px; }
        button { padding: 12px 25px; cursor: pointer; background: #000; color: #fff; border: none; border-radius: 6px; font-weight: bold; }
        .admin-link { display: block; text-align: right; margin-top: 20px; color: #aaa; text-decoration: none; font-size: 0.8em; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #fff; padding: 20px; border-radius: 10px; border-left: 5px solid #000; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .badge { float: right; background: #eee; padding: 2px 8px; font-size: 0.8em; font-weight: bold; border-radius: 4px; }
        .contact-links { margin-top: 10px; display: flex; gap: 5px; }
        .btn-link { padding: 5px 10px; background: #eee; text-decoration: none; color: #333; border-radius: 4px; font-size: 0.85em; }
        .btn-link.whatsapp { background: #25D366; color: white; }
    </style>
</head>
<body>
    <h1>Encontre uma Loja Soul</h1>
    <p class="subtitle">{{ qtd }} autorizadas cadastradas</p>
    
    <div id="map"></div>

    <div class="search-box">
        <input type="text" id="buscaInput" placeholder="Busque por cidade, estado ou nome...">
        <button onclick="buscar()">Filtrar</button>
    </div>
    
    <div id="lista" class="grid"></div>
    
    <a href="/admin" class="admin-link">Area Administrativa</a>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([-14.2350, -51.9253], 4);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }).addTo(map);
        var markersLayer = L.layerGroup().addTo(map);
        var allData = [];

        async function carregar() {
            let res = await fetch('/api/lojas');
            allData = await res.json();
            renderizar(allData);
        }

        function renderizar(lojas) {
            markersLayer.clearLayers();
            let html = '';
            lojas.forEach(l => {
                // Adiciona no mapa se tiver lat/lon
                if(l.lat && l.lon) {
                    let m = L.marker([l.lat, l.lon]).bindPopup(`<b>${l.nome}</b><br>${l.municipio}-${l.uf}`);
                    markersLayer.addLayer(m);
                }
                // Adiciona na lista
                html += `
                <div class="card">
                    <span class="badge">${l.perfil}</span>
                    <h3>${l.nome}</h3>
                    <p>${l.municipio} - ${l.uf}</p>
                    <p style="font-size:0.9em; color:#666;">${l.endereco}, ${l.numero}</p>
                    <div class="contact-links">
                        ${l.telefone ? `<a href="https://wa.me/55${l.telefone.replace(/\D/g,'')}" class="btn-link whatsapp" target="_blank">WhatsApp</a>` : ''}
                    </div>
                </div>`;
            });
            document.getElementById('lista').innerHTML = html;
        }

        function buscar() {
            let termo = document.getElementById('buscaInput').value.toLowerCase();
            let filtrados = allData.filter(l => 
                (l.nome + ' ' + l.municipio + ' ' + l.uf).toLowerCase().includes(termo)
            );
            renderizar(filtrados);
        }
        
        carregar();
    </script>
</body>
</html>
"""

# HTML DO ADMIN (PRIVADO)
HTML_ADMIN = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin - Lojas Soul</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #eee; }
        .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { border-bottom: 2px solid #000; padding-bottom: 10px; }
        form { display: grid; gap: 10px; margin-bottom: 30px; background: #f9f9f9; padding: 15px; border-radius: 8px; }
        input, select { padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        button { padding: 10px; background: #000; color: white; border: none; cursor: pointer; border-radius: 4px; font-weight: bold; }
        button:hover { background: #333; }
        .msg { padding: 10px; background: #d4edda; color: #155724; border-radius: 4px; margin-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        .btn-del { background: #dc3545; padding: 5px 10px; font-size: 0.8em; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/">Voltar para o Site</a>
        <h2>Gerenciar Lojas</h2>
        
        {% if msg %} <div class="msg">{{ msg }}</div> {% endif %}

        <h3>Adicionar Nova Loja</h3>
        <p style="font-size: 0.9em; color: #666;">O sistema buscará a latitude/longitude automaticamente pelo endereço.</p>
        
        <form action="/admin/add" method="POST">
            <input type="text" name="nome" placeholder="Nome da Loja" required>
            <select name="perfil">
                <option value="Loja">Loja</option>
                <option value="Mecânico">Mecânico</option>
            </select>
            <input type="text" name="endereco" placeholder="Endereço (Rua)" required>
            <input type="text" name="numero" placeholder="Número" required>
            <input type="text" name="bairro" placeholder="Bairro">
            <input type="text" name="municipio" placeholder="Cidade" required>
            <input type="text" name="uf" placeholder="Estado (UF)" required maxlength="2">
            <input type="text" name="telefone" placeholder="Telefone/WhatsApp">
            <button type="submit">Cadastrar Loja</button>
        </form>

        <h3>Lojas Cadastradas ({{ total }})</h3>
        <table>
            <thead><tr><th>Nome</th><th>Cidade</th><th>Lat/Lon</th><th>Ação</th></tr></thead>
            <tbody>
                {% for loja in lojas %}
                <tr>
                    <td>{{ loja['nome'] }}</td>
                    <td>{{ loja['municipio'] }}-{{ loja['uf'] }}</td>
                    <td>
                        {% if loja['lat'] %} <span style="color:green">✔ OK</span>
                        {% else %} <span style="color:red">✖ Pendente</span> {% endif %}
                    </td>
                    <td>
                        <a href="/admin/delete/{{ loja['id'] }}" onclick="return confirm('Tem certeza?')" style="color:red">Excluir</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

# --- FUNÇÕES DO SISTEMA ---

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Cria a tabela se não existir
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS lojas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT, perfil TEXT, endereco TEXT, numero TEXT, bairro TEXT,
            municipio TEXT, uf TEXT, cep TEXT, telefone TEXT, 
            lat REAL, lon REAL
        )
    ''')
    
    # Se estiver vazia, tenta importar do CSV antigo
    count = conn.execute('SELECT count(*) FROM lojas').fetchone()[0]
    if count == 0 and os.path.exists('dados.csv'):
        print("Importando dados do CSV inicial...")
        try:
            with open('dados.csv', mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';') # Tenta ; primeiro
                if 'NOME' not in reader.fieldnames: # Se falhar, tenta ,
                    f.seek(0)
                    reader = csv.DictReader(f, delimiter=',')
                
                for row in reader:
                    # Mapeia colunas do CSV para o Banco
                    # Ajuste as chaves conforme seu CSV exato
                    nome = row.get('NOME') or row.get('nome')
                    if not nome: continue
                    
                    conn.execute('''
                        INSERT INTO lojas (nome, perfil, endereco, numero, bairro, municipio, uf, telefone)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        nome,
                        row.get('PERFIL') or row.get('perfil'),
                        row.get('ENDEREÇO') or row.get('endereço'),
                        row.get('NUMERO/COMPLEMENTO') or row.get('numero'),
                        row.get('BAIRRO') or row.get('bairro'),
                        row.get('MUNICIPIO') or row.get('municipio'),
                        row.get('UF') or row.get('uf'),
                        row.get('TELEFONE') or row.get('telefone')
                    ))
        except Exception as e:
            print(f"Erro na importação: {e}")
    
    conn.commit()
    conn.close()

# Roda a inicialização ao ligar o app
init_db()

# --- GEOLOCALIZAÇÃO ---
def geocode_address(address_str):
    try:
        geolocator = Nominatim(user_agent="soul_app_finder_v1")
        location = geolocator.geocode(address_str, timeout=10)
        if location:
            return location.latitude, location.longitude
    except:
        pass
    return None, None

# --- ROTAS ---

@app.route('/')
def home():
    conn = get_db()
    qtd = conn.execute('SELECT count(*) FROM lojas').fetchone()[0]
    conn.close()
    return render_template_string(HTML_PUBLICO, qtd=qtd)

@app.route('/api/lojas')
def api_lojas():
    conn = get_db()
    lojas = conn.execute('SELECT * FROM lojas').fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in lojas])

@app.route('/admin')
def admin():
    conn = get_db()
    lojas = conn.execute('SELECT * FROM lojas ORDER BY id DESC').fetchall()
    conn.close()
    return render_template_string(HTML_ADMIN, lojas=lojas, total=len(lojas))

@app.route('/admin/add', methods=['POST'])
def add_loja():
    nome = request.form['nome']
    municipio = request.form['municipio']
    uf = request.form['uf']
    endereco = request.form['endereco']
    numero = request.form['numero']
    
    # Monta endereço para o Google Maps/Nominatim achar
    full_address = f"{endereco}, {numero} - {municipio}, {uf}, Brazil"
    print(f"Buscando coordenadas para: {full_address}")
    
    # Busca Lat/Lon automaticamente
    lat, lon = geocode_address(full_address)
    
    conn = get_db()
    conn.execute('''
        INSERT INTO lojas (nome, perfil, endereco, numero, bairro, municipio, uf, telefone, lat, lon)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        nome, request.form['perfil'], endereco, numero, request.form['bairro'],
        municipio, uf, request.form['telefone'], lat, lon
    ))
    conn.commit()
    conn.close()
    
    msg = "Loja cadastrada com sucesso!"
    if not lat: msg += " (Mas não conseguimos achar a localização no mapa)"
    
    return render_template_string(HTML_ADMIN, msg=msg, lojas=get_db().execute('SELECT * FROM lojas ORDER BY id DESC').fetchall())

@app.route('/admin/delete/<int:id>')
def delete_loja(id):
    conn = get_db()
    conn.execute('DELETE FROM lojas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
