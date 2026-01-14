from flask import Flask, jsonify, request, render_template_string, redirect, url_for
import sqlite3
import csv
import os
from geopy.geocoders import Nominatim
from unicodedata import normalize

app = Flask(__name__)

DB_NAME = "lojas.db"

# --- HTML DO SITE (PÚBLICO) ---
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
                if(l.lat && l.lon) {
                    let m = L.marker([l.lat, l.lon]).bindPopup(`<b>${l.nome}</b><br>${l.municipio}-${l.uf}`);
                    markersLayer.addLayer(m);
                }
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

# --- HTML DO ADMIN (PRIVADO) ---
HTML_ADMIN = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin - Lojas Soul</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #eee; }
        .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #000; padding-bottom: 10px; }
        
        /* Botões */
        .btn { padding: 8px 15px; border: none; cursor: pointer; border-radius: 4px; font-weight: bold; text-decoration: none; display: inline-block; font-size: 0.9em; }
        .btn-primary { background: #000; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-warning { background: #ffc107; color: #000; }
        .btn-info { background: #17a2b8; color: white; }
        .btn-sm { padding: 5px 10px; font-size: 0.8em; }

        /* Formulário */
        #form-container { display: none; background: #f9f9f9; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #ddd; }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        input, select { padding: 10px; border: 1px solid #ddd; border-radius: 4px; width: 100%; box-sizing: border-box; }
        .full-width { grid-column: span 2; }
        
        /* Barra de Pesquisa Admin */
        .search-admin { margin: 20px 0; }
        .search-admin input { width: 100%; padding: 12px; font-size: 16px; border: 2px solid #ddd; }

        /* Tabela */
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9em; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
        tr:hover { background-color: #f1f1f1; }
        
        .msg { padding: 15px; background: #d4edda; color: #155724; border-radius: 4px; margin-bottom: 20px; text-align: center; }

        /* Modal de Edição */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 999; }
        .modal-content { background: white; width: 90%; max-width: 600px; margin: 50px auto; padding: 20px; border-radius: 8px; }
        .modal-header { display: flex; justify-content: space-between; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" style="text-decoration: none; color: #666;">← Voltar para o Site</a>
        
        {% if msg %} <div class="msg">{{ msg }}</div> {% endif %}

        <h2>
            Gerenciar Lojas 
            <button onclick="toggleForm()" class="btn btn-primary">➕ Nova Loja</button>
        </h2>

        <div id="form-container">
            <h3>Adicionar Nova Loja</h3>
            <form action="/admin/add" method="POST" class="form-grid">
                <input type="text" name="nome" placeholder="Nome da Loja" required class="full-width">
                <select name="perfil">
                    <option value="Loja">Loja</option>
                    <option value="Mecânico">Mecânico</option>
                    <option value="Revenda">Revenda</option>
                </select>
                <input type="text" name="telefone" placeholder="Telefone/WhatsApp">
                <input type="text" name="municipio" placeholder="Cidade" required>
                <input type="text" name="uf" placeholder="UF" required maxlength="2">
                <input type="text" name="endereco" placeholder="Endereço (Rua)" required>
                <input type="text" name="numero" placeholder="Número" required>
                <input type="text" name="bairro" placeholder="Bairro" class="full-width">
                <button type="submit" class="btn btn-primary full-width">Salvar Loja</button>
            </form>
        </div>

        <div class="search-admin">
            <input type="text" id="adminSearch" onkeyup="filterTable()" placeholder="🔍 Pesquisar na lista (Nome, Cidade, UF)...">
        </div>

        <table id="lojasTable">
            <thead>
                <tr>
                    <th>Nome</th>
                    <th>Cidade/UF</th>
                    <th>GPS</th>
                    <th>Ações</th>
                </tr>
            </thead>
            <tbody>
                {% for loja in lojas %}
                <tr>
                    <td><strong>{{ loja['nome'] }}</strong><br><small>{{ loja['perfil'] }}</small></td>
                    <td>{{ loja['municipio'] }} - {{ loja['uf'] }}</td>
                    <td>
                        {% if loja['lat'] %} 
                            <span style="color:green">✔ OK</span>
                        {% else %} 
                            <span style="color:red">✖ Pendente</span>
                            <a href="/admin/geo/{{ loja['id'] }}" class="btn btn-info btn-sm" title="Tentar achar coordenada">🌍 Buscar GPS</a>
                        {% endif %}
                    </td>
                    <td>
                        <button onclick='abrirEditar({{ loja | tojson }})' class="btn btn-warning btn-sm">✏️ Editar</button>
                        <a href="/admin/delete/{{ loja['id'] }}" onclick="return confirm('Tem certeza que deseja apagar?')" class="btn btn-danger btn-sm">🗑️</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <div id="editModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Editar Loja</h3>
                <button onclick="closeModal()" class="btn btn-danger btn-sm">X</button>
            </div>
            <form action="/admin/update" method="POST" class="form-grid">
                <input type="hidden" name="id" id="edit_id">
                <input type="text" name="nome" id="edit_nome" placeholder="Nome" class="full-width" required>
                <select name="perfil" id="edit_perfil">
                    <option value="Loja">Loja</option>
                    <option value="Mecânico">Mecânico</option>
                    <option value="Revenda">Revenda</option>
                </select>
                <input type="text" name="telefone" id="edit_telefone" placeholder="Telefone">
                <input type="text" name="municipio" id="edit_municipio" placeholder="Cidade" required>
                <input type="text" name="uf" id="edit_uf" placeholder="UF" required>
                <input type="text" name="endereco" id="edit_endereco" placeholder="Endereço" required>
                <input type="text" name="numero" id="edit_numero" placeholder="Número">
                <input type="text" name="bairro" id="edit_bairro" placeholder="Bairro" class="full-width">
                <button type="submit" class="btn btn-primary full-width">Salvar Alterações</button>
            </form>
        </div>
    </div>

    <script>
        function toggleForm() {
            var x = document.getElementById("form-container");
            x.style.display = x.style.display === "none" || x.style.display === "" ? "block" : "none";
        }

        function filterTable() {
            var input, filter, table, tr, td, i, txtValue;
            input = document.getElementById("adminSearch");
            filter = input.value.toUpperCase();
            table = document.getElementById("lojasTable");
            tr = table.getElementsByTagName("tr");
            for (i = 0; i < tr.length; i++) {
                // Procura na coluna Nome (0) e Cidade (1)
                td0 = tr[i].getElementsByTagName("td")[0];
                td1 = tr[i].getElementsByTagName("td")[1];
                if (td0 || td1) {
                    txtValue = (td0.textContent || td0.innerText) + " " + (td1.textContent || td1.innerText);
                    if (txtValue.toUpperCase().indexOf(filter) > -1) {
                        tr[i].style.display = "";
                    } else {
                        tr[i].style.display = "none";
                    }
                }       
            }
        }

        function abrirEditar(loja) {
            document.getElementById('edit_id').value = loja.id;
            document.getElementById('edit_nome').value = loja.nome;
            document.getElementById('edit_perfil').value = loja.perfil;
            document.getElementById('edit_telefone').value = loja.telefone;
            document.getElementById('edit_municipio').value = loja.municipio;
            document.getElementById('edit_uf').value = loja.uf;
            document.getElementById('edit_endereco').value = loja.endereco;
            document.getElementById('edit_numero').value = loja.numero;
            document.getElementById('edit_bairro').value = loja.bairro;
            document.getElementById('editModal').style.display = 'block';
        }

        function closeModal() {
            document.getElementById('editModal').style.display = 'none';
        }

        // Fecha o modal se clicar fora dele
        window.onclick = function(event) {
            if (event.target == document.getElementById('editModal')) {
                closeModal();
            }
        }
    </script>
</body>
</html>
"""

# --- FUNÇÕES E BANCO DE DADOS ---

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS lojas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT, perfil TEXT, endereco TEXT, numero TEXT, bairro TEXT,
            municipio TEXT, uf TEXT, cep TEXT, telefone TEXT, 
            lat REAL, lon REAL
        )
    ''')
    
    # Importa CSV apenas se o banco estiver vazio
    if conn.execute('SELECT count(*) FROM lojas').fetchone()[0] == 0 and os.path.exists('dados.csv'):
        try:
            with open('dados.csv', mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                if 'NOME' not in reader.fieldnames:
                     f.seek(0)
                     reader = csv.DictReader(f, delimiter=',')
                
                for row in reader:
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
            print(f"Erro importação: {e}")
    conn.commit()
    conn.close()

init_db()

def geocode_address(address_str):
    try:
        geolocator = Nominatim(user_agent="soul_finder_v2")
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
    return render_template_string(HTML_ADMIN, lojas=[dict(ix) for ix in lojas], msg=request.args.get('msg'))

@app.route('/admin/add', methods=['POST'])
def add_loja():
    nome = request.form['nome']
    endereco = f"{request.form['endereco']}, {request.form['numero']} - {request.form['municipio']}, {request.form['uf']}, Brazil"
    lat, lon = geocode_address(endereco)
    
    conn = get_db()
    conn.execute('''
        INSERT INTO lojas (nome, perfil, endereco, numero, bairro, municipio, uf, telefone, lat, lon)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        nome, request.form['perfil'], request.form['endereco'], request.form['numero'], request.form['bairro'],
        request.form['municipio'], request.form['uf'], request.form['telefone'], lat, lon
    ))
    conn.commit()
    conn.close()
    return redirect(url_for('admin', msg="Loja adicionada!"))

@app.route('/admin/update', methods=['POST'])
def update_loja():
    # Atualiza os dados da loja
    id_loja = request.form['id']
    endereco_completo = f"{request.form['endereco']}, {request.form['numero']} - {request.form['municipio']}, {request.form['uf']}, Brazil"
    
    # Tenta buscar nova coordenada sempre que edita
    lat, lon = geocode_address(endereco_completo)
    
    conn = get_db()
    # Se achou coordenada nova, atualiza tudo. Se não, mantem a antiga (ou null)
    if lat and lon:
        conn.execute('''
            UPDATE lojas SET nome=?, perfil=?, endereco=?, numero=?, bairro=?, municipio=?, uf=?, telefone=?, lat=?, lon=?
            WHERE id=?
        ''', (request.form['nome'], request.form['perfil'], request.form['endereco'], request.form['numero'], 
              request.form['bairro'], request.form['municipio'], request.form['uf'], request.form['telefone'], lat, lon, id_loja))
    else:
         conn.execute('''
            UPDATE lojas SET nome=?, perfil=?, endereco=?, numero=?, bairro=?, municipio=?, uf=?, telefone=?
            WHERE id=?
        ''', (request.form['nome'], request.form['perfil'], request.form['endereco'], request.form['numero'], 
              request.form['bairro'], request.form['municipio'], request.form['uf'], request.form['telefone'], id_loja))
         
    conn.commit()
    conn.close()
    return redirect(url_for('admin', msg="Loja atualizada com sucesso!"))

@app.route('/admin/geo/<int:id>')
def force_geo(id):
    conn = get_db()
    loja = conn.execute('SELECT * FROM lojas WHERE id = ?', (id,)).fetchone()
    
    if loja:
        full_address = f"{loja['endereco']}, {loja['numero']} - {loja['municipio']}, {loja['uf']}, Brazil"
        lat, lon = geocode_address(full_address)
        if lat:
            conn.execute('UPDATE lojas SET lat=?, lon=? WHERE id=?', (lat, lon, id))
            msg = "Coordenada encontrada e atualizada!"
        else:
            msg = "Não conseguimos achar esse endereço no mapa. Verifique se a rua e cidade estão corretos."
        conn.commit()
    else:
        msg = "Loja não encontrada."
        
    conn.close()
    return redirect(url_for('admin', msg=msg))

@app.route('/admin/delete/<int:id>')
def delete_loja(id):
    conn = get_db()
    conn.execute('DELETE FROM lojas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin', msg="Loja removida."))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
