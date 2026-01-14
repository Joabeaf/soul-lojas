from flask import Flask, jsonify, request, render_template_string, redirect, url_for
import sqlite3
import csv
import os
from geopy.geocoders import Nominatim
from unicodedata import normalize

app = Flask(__name__)

DB_NAME = "lojas.db"

# --- HTML PÚBLICO (SITE) ---
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
        .contact-links { margin-top: 10px; display: flex; gap: 5px; flex-wrap: wrap;}
        .btn-link { padding: 5px 10px; background: #eee; text-decoration: none; color: #333; border-radius: 4px; font-size: 0.85em; }
        .btn-link.whatsapp { background: #25D366; color: white; }
        .btn-link.insta { background: #E1306C; color: white; }
        .info-row { font-size: 0.9em; margin: 5px 0; color: #555; }
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
                
                // Formatação do Card
                html += `
                <div class="card">
                    <span class="badge">${l.perfil || 'Loja'}</span>
                    <h3>${l.nome}</h3>
                    <div class="info-row">📍 ${l.municipio} - ${l.uf}</div>
                    <div class="info-row">🏠 ${l.endereco}, ${l.numero} - ${l.bairro || ''}</div>
                    
                    ${l.horario_seg_sex ? `<div class="info-row">🕒 Seg-Sex: ${l.horario_seg_sex}</div>` : ''}
                    ${l.horario_sab ? `<div class="info-row">🕒 Sáb: ${l.horario_sab}</div>` : ''}
                    
                    <div class="contact-links">
                        ${l.telefone ? `<a href="https://wa.me/55${l.telefone.replace(/\D/g,'')}" class="btn-link whatsapp" target="_blank">WhatsApp</a>` : ''}
                        ${l.instagram ? `<a href="https://instagram.com/${l.instagram.replace('@','').replace('/','')}" class="btn-link insta" target="_blank">Instagram</a>` : ''}
                        ${l.telefone ? `<a href="tel:${l.telefone.replace(/\D/g,'')}" class="btn-link">📞 Ligar</a>` : ''}
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

# --- HTML DO ADMIN ---
HTML_ADMIN = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin - Completo</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; max-width: 1100px; margin: 0 auto; padding: 20px; background: #eee; }
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
        .form-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        .col-1 { grid-column: span 1; }
        .col-2 { grid-column: span 2; }
        .col-3 { grid-column: span 3; }
        .col-4 { grid-column: span 4; }
        
        input, select { padding: 10px; border: 1px solid #ddd; border-radius: 4px; width: 100%; box-sizing: border-box; }
        label { display: block; font-size: 0.8em; font-weight: bold; margin-bottom: 2px; color: #555; }
        
        .section-title { grid-column: span 4; font-size: 1.1em; border-bottom: 1px solid #ccc; margin-top: 15px; padding-bottom: 5px; color: #333; }

        /* Tabela */
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.85em; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
        tr:hover { background-color: #f1f1f1; }
        
        .msg { padding: 15px; background: #d4edda; color: #155724; border-radius: 4px; margin-bottom: 20px; text-align: center; }

        /* Modal */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 999; overflow-y: auto; }
        .modal-content { background: white; width: 95%; max-width: 800px; margin: 30px auto; padding: 20px; border-radius: 8px; }
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
                
                <div class="section-title">Dados Principais</div>
                <div class="col-1"><label>Código</label><input type="text" name="codigo"></div>
                <div class="col-1"><label>Perfil</label>
                    <select name="perfil">
                        <option value="Loja">Loja</option>
                        <option value="Mecânico">Mecânico</option>
                        <option value="Revenda">Revenda</option>
                    </select>
                </div>
                <div class="col-2"><label>Nome Fantasia</label><input type="text" name="nome" required></div>
                <div class="col-2"><label>CNPJ</label><input type="text" name="cnpj"></div>
                <div class="col-2"><label>Contato (Pessoa)</label><input type="text" name="contato_nome"></div>

                <div class="section-title">Endereço</div>
                <div class="col-1"><label>CEP</label><input type="text" name="cep"></div>
                <div class="col-2"><label>Logradouro</label><input type="text" name="endereco" required></div>
                <div class="col-1"><label>Número</label><input type="text" name="numero" required></div>
                <div class="col-2"><label>Bairro</label><input type="text" name="bairro"></div>
                <div class="col-1"><label>Cidade</label><input type="text" name="municipio" required></div>
                <div class="col-1"><label>UF</label><input type="text" name="uf" required maxlength="2"></div>

                <div class="section-title">Contatos e Horários</div>
                <div class="col-2"><label>Telefone/Whats</label><input type="text" name="telefone"></div>
                <div class="col-2"><label>E-mail</label><input type="text" name="email"></div>
                <div class="col-2"><label>Instagram</label><input type="text" name="instagram"></div>
                <div class="col-2"><label>Vendedor Resp.</label><input type="text" name="vendedor"></div>
                <div class="col-2"><label>Horário Seg-Sex</label><input type="text" name="horario_seg_sex"></div>
                <div class="col-2"><label>Horário Sábado</label><input type="text" name="horario_sab"></div>
                <div class="col-4"><label>Time Soul</label><input type="text" name="time_soul"></div>

                <div class="col-4" style="margin-top:15px">
                    <button type="submit" class="btn btn-primary" style="width:100%">Salvar Cadastro Completo</button>
                </div>
            </form>
        </div>

        <input type="text" id="adminSearch" onkeyup="filterTable()" placeholder="🔍 Pesquisar na lista..." style="margin: 20px 0; padding: 12px;">

        <table id="lojasTable">
            <thead>
                <tr>
                    <th>Cod</th>
                    <th>Nome / CNPJ</th>
                    <th>Local</th>
                    <th>Contato</th>
                    <th>Ações</th>
                </tr>
            </thead>
            <tbody>
                {% for loja in lojas %}
                <tr>
                    <td>{{ loja['codigo'] }}</td>
                    <td><strong>{{ loja['nome'] }}</strong><br><small>{{ loja['cnpj'] }}</small></td>
                    <td>{{ loja['municipio'] }}-{{ loja['uf'] }}<br><small>{{ loja['bairro'] }}</small></td>
                    <td>{{ loja['telefone'] }}<br><small>{{ loja['email'] }}</small></td>
                    <td>
                        <button onclick='abrirEditar({{ loja | tojson }})' class="btn btn-warning btn-sm">✏️</button>
                        <a href="/admin/delete/{{ loja['id'] }}" onclick="return confirm('Apagar?')" class="btn btn-danger btn-sm">🗑️</a>
                        {% if not loja['lat'] %}
                        <a href="/admin/geo/{{ loja['id'] }}" class="btn btn-info btn-sm" title="Buscar GPS">🌍</a>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <div id="editModal" class="modal">
        <div class="modal-content">
            <div style="display:flex; justify-content:space-between;">
                <h3>Editar Loja</h3>
                <button onclick="closeModal()" class="btn btn-danger btn-sm">X</button>
            </div>
            <form action="/admin/update" method="POST" class="form-grid">
                <input type="hidden" name="id" id="e_id">
                
                <div class="section-title">Dados Principais</div>
                <div class="col-1"><label>Código</label><input type="text" name="codigo" id="e_codigo"></div>
                <div class="col-1"><label>Perfil</label>
                    <select name="perfil" id="e_perfil">
                        <option value="Loja">Loja</option>
                        <option value="Mecânico">Mecânico</option>
                        <option value="Revenda">Revenda</option>
                    </select>
                </div>
                <div class="col-2"><label>Nome</label><input type="text" name="nome" id="e_nome" required></div>
                <div class="col-2"><label>CNPJ</label><input type="text" name="cnpj" id="e_cnpj"></div>
                <div class="col-2"><label>Contato</label><input type="text" name="contato_nome" id="e_contato_nome"></div>

                <div class="section-title">Endereço</div>
                <div class="col-1"><label>CEP</label><input type="text" name="cep" id="e_cep"></div>
                <div class="col-2"><label>Rua</label><input type="text" name="endereco" id="e_endereco" required></div>
                <div class="col-1"><label>Num</label><input type="text" name="numero" id="e_numero" required></div>
                <div class="col-2"><label>Bairro</label><input type="text" name="bairro" id="e_bairro"></div>
                <div class="col-1"><label>Cidade</label><input type="text" name="municipio" id="e_municipio" required></div>
                <div class="col-1"><label>UF</label><input type="text" name="uf" id="e_uf" required></div>

                <div class="section-title">Outros</div>
                <div class="col-2"><label>Tel</label><input type="text" name="telefone" id="e_telefone"></div>
                <div class="col-2"><label>Email</label><input type="text" name="email" id="e_email"></div>
                <div class="col-2"><label>Insta</label><input type="text" name="instagram" id="e_instagram"></div>
                <div class="col-2"><label>Vendedor</label><input type="text" name="vendedor" id="e_vendedor"></div>
                <div class="col-2"><label>Hor. Seg-Sex</label><input type="text" name="horario_seg_sex" id="e_horario_seg_sex"></div>
                <div class="col-2"><label>Hor. Sab</label><input type="text" name="horario_sab" id="e_horario_sab"></div>
                <div class="col-4"><label>Time</label><input type="text" name="time_soul" id="e_time_soul"></div>

                <div class="col-4" style="margin-top:15px">
                    <button type="submit" class="btn btn-primary" style="width:100%">Salvar Alterações</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        function toggleForm() {
            var x = document.getElementById("form-container");
            x.style.display = x.style.display === "none" || x.style.display === "" ? "block" : "none";
        }
        function filterTable() {
            var input = document.getElementById("adminSearch");
            var filter = input.value.toUpperCase();
            var table = document.getElementById("lojasTable");
            var tr = table.getElementsByTagName("tr");
            for (i = 0; i < tr.length; i++) {
                var tdText = tr[i].innerText;
                if (tdText) {
                    tr[i].style.display = tdText.toUpperCase().indexOf(filter) > -1 ? "" : "none";
                }       
            }
        }
        function abrirEditar(l) {
            document.getElementById('e_id').value = l.id;
            document.getElementById('e_codigo').value = l.codigo || '';
            document.getElementById('e_perfil').value = l.perfil || 'Loja';
            document.getElementById('e_nome').value = l.nome || '';
            document.getElementById('e_cnpj').value = l.cnpj || '';
            document.getElementById('e_contato_nome').value = l.contato || '';
            document.getElementById('e_cep').value = l.cep || '';
            document.getElementById('e_endereco').value = l.endereco || '';
            document.getElementById('e_numero').value = l.numero || '';
            document.getElementById('e_bairro').value = l.bairro || '';
            document.getElementById('e_municipio').value = l.municipio || '';
            document.getElementById('e_uf').value = l.uf || '';
            document.getElementById('e_telefone').value = l.telefone || '';
            document.getElementById('e_email').value = l.email || '';
            document.getElementById('e_instagram').value = l.instagram || '';
            document.getElementById('e_vendedor').value = l.vendedor || '';
            document.getElementById('e_horario_seg_sex').value = l.horario_seg_sex || '';
            document.getElementById('e_horario_sab').value = l.horario_sab || '';
            document.getElementById('e_time_soul').value = l.time_soul || '';
            
            document.getElementById('editModal').style.display = 'block';
        }
        function closeModal() { document.getElementById('editModal').style.display = 'none'; }
        window.onclick = function(e) { if (e.target == document.getElementById('editModal')) closeModal(); }
    </script>
</body>
</html>
"""

# --- BACKEND ---
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    # Cria a tabela com TODAS as colunas solicitadas
    conn.execute('''
        CREATE TABLE IF NOT EXISTS lojas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT, perfil TEXT, nome TEXT, cnpj TEXT, contato TEXT,
            telefone TEXT, endereco TEXT, numero TEXT, bairro TEXT,
            uf TEXT, municipio TEXT, cep TEXT,
            horario_seg_sex TEXT, horario_sab TEXT,
            instagram TEXT, email TEXT, time_soul TEXT, vendedor TEXT,
            lat REAL, lon REAL
        )
    ''')
    
    # Importação do CSV
    if conn.execute('SELECT count(*) FROM lojas').fetchone()[0] == 0 and os.path.exists('dados.csv'):
        try:
            with open('dados.csv', mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                if 'NOME' not in reader.fieldnames:
                     f.seek(0)
                     reader = csv.DictReader(f, delimiter=',')
                
                for row in reader:
                    # Normaliza as chaves (remove espaços e poe minusculo)
                    r = {k.strip(): v for k, v in row.items() if k}
                    
                    # Se não tiver nome, pula
                    if not r.get('NOME'): continue
                    
                    conn.execute('''
                        INSERT INTO lojas (
                            codigo, perfil, nome, cnpj, contato, telefone,
                            endereco, numero, bairro, uf, municipio, cep,
                            horario_seg_sex, horario_sab, instagram, email,
                            time_soul, vendedor
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ''', (
                        r.get('CODIGO'), r.get('PERFIL'), r.get('NOME'), r.get('CNPJ'), r.get('CONTATO'),
                        r.get('TELEFONE'), r.get('ENDEREÇO'), r.get('NUMERO/COMPLEMENTO'),
                        r.get('BAIRRO'), r.get('UF'), r.get('MUNICIPIO'), r.get('CEP'),
                        r.get('SEG. A SEX.'), r.get('SÁBADO'), r.get('INSTAGRAM'),
                        r.get('E-mail'), r.get('Time'), r.get('Vendedor')
                    ))
        except Exception as e:
            print(f"Erro na importação: {e}")
    conn.commit()
    conn.close()

init_db()

def geocode_address(address_str):
    try:
        geolocator = Nominatim(user_agent="soul_sys_v3")
        location = geolocator.geocode(address_str, timeout=10)
        if location: return location.latitude, location.longitude
    except: pass
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
    f = request.form
    endereco_completo = f"{f['endereco']}, {f['numero']} - {f['municipio']}, {f['uf']}, Brazil"
    lat, lon = geocode_address(endereco_completo)
    
    conn = get_db()
    conn.execute('''
        INSERT INTO lojas (
            codigo, perfil, nome, cnpj, contato, telefone, endereco, numero, bairro,
            municipio, uf, cep, horario_seg_sex, horario_sab, instagram, email,
            time_soul, vendedor, lat, lon
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        f['codigo'], f['perfil'], f['nome'], f['cnpj'], f['contato_nome'], f['telefone'],
        f['endereco'], f['numero'], f['bairro'], f['municipio'], f['uf'], f['cep'],
        f['horario_seg_sex'], f['horario_sab'], f['instagram'], f['email'],
        f['time_soul'], f['vendedor'], lat, lon
    ))
    conn.commit()
    conn.close()
    return redirect(url_for('admin', msg="Loja cadastrada com sucesso!"))

@app.route('/admin/update', methods=['POST'])
def update_loja():
    f = request.form
    id_loja = f['id']
    endereco_completo = f"{f['endereco']}, {f['numero']} - {f['municipio']}, {f['uf']}, Brazil"
    lat, lon = geocode_address(endereco_completo)
    
    conn = get_db()
    # Se achou GPS novo, atualiza tudo. Se não, mantem o GPS antigo.
    sql_base = '''
        UPDATE lojas SET 
        codigo=?, perfil=?, nome=?, cnpj=?, contato=?, telefone=?, endereco=?, numero=?, bairro=?,
        municipio=?, uf=?, cep=?, horario_seg_sex=?, horario_sab=?, instagram=?, email=?,
        time_soul=?, vendedor=?
    '''
    params = [
        f['codigo'], f['perfil'], f['nome'], f['cnpj'], f['contato_nome'], f['telefone'],
        f['endereco'], f['numero'], f['bairro'], f['municipio'], f['uf'], f['cep'],
        f['horario_seg_sex'], f['horario_sab'], f['instagram'], f['email'],
        f['time_soul'], f['vendedor']
    ]
    
    if lat and lon:
        conn.execute(sql_base + ', lat=?, lon=? WHERE id=?', (*params, lat, lon, id_loja))
    else:
        conn.execute(sql_base + ' WHERE id=?', (*params, id_loja))
         
    conn.commit()
    conn.close()
    return redirect(url_for('admin', msg="Atualizado com sucesso!"))

@app.route('/admin/geo/<int:id>')
def force_geo(id):
    conn = get_db()
    l = conn.execute('SELECT * FROM lojas WHERE id = ?', (id,)).fetchone()
    if l:
        full = f"{l['endereco']}, {l['numero']} - {l['municipio']}, {l['uf']}, Brazil"
        lat, lon = geocode_address(full)
        if lat:
            conn.execute('UPDATE lojas SET lat=?, lon=? WHERE id=?', (lat, lon, id))
            msg = "GPS Atualizado!"
        else:
            msg = "Endereço não encontrado no mapa."
        conn.commit()
    else: msg = "Erro."
    conn.close()
    return redirect(url_for('admin', msg=msg))

@app.route('/admin/delete/<int:id>')
def delete_loja(id):
    conn = get_db()
    conn.execute('DELETE FROM lojas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin', msg="Removido."))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
