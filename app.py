from flask import Flask, jsonify, request, render_template_string, redirect, url_for, send_from_directory
import sqlite3
import csv
import os
from geopy.geocoders import Nominatim
from unicodedata import normalize
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configurações de Upload
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Garante que a pasta existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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
        body { font-family: 'Segoe UI', sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f4f6f8; }
        h1, .subtitle { text-align: center; }
        
        /* Mapa Principal */
        #main-map { height: 400px; width: 100%; border-radius: 12px; margin-bottom: 20px; border: 2px solid #ddd; z-index: 1; }
        
        /* Busca e Grid */
        .search-box { display: flex; gap: 10px; justify-content: center; margin-bottom: 20px; }
        input { padding: 12px; width: 60%; border: 1px solid #ccc; border-radius: 6px; }
        button { padding: 12px 25px; cursor: pointer; background: #000; color: #fff; border: none; border-radius: 6px; font-weight: bold; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        
        /* Card */
        .card { background: #fff; padding: 20px; border-radius: 10px; border-left: 5px solid #000; box-shadow: 0 2px 5px rgba(0,0,0,0.05); cursor: pointer; transition: transform 0.2s; }
        .card:hover { transform: translateY(-5px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .badge { float: right; background: #eee; padding: 2px 8px; font-size: 0.8em; font-weight: bold; border-radius: 4px; }
        .info-row { font-size: 0.9em; margin: 5px 0; color: #555; }
        .btn-ver-mais { display: block; width: 100%; text-align: center; background: #f0f0f0; padding: 8px; margin-top: 10px; border-radius: 4px; color: #333; font-weight: bold; }

        /* MODAL DE DETALHES */
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 9999; justify-content: center; align-items: center; }
        .modal-body { background: white; width: 90%; max-width: 900px; max-height: 90vh; overflow-y: auto; border-radius: 10px; padding: 0; display: flex; flex-direction: column; position: relative; }
        .modal-close { position: absolute; top: 15px; right: 20px; font-size: 24px; cursor: pointer; background: none; border: none; font-weight: bold; color: #333; z-index: 10; }
        
        .modal-content-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 20px; }
        @media (max-width: 700px) { .modal-content-grid { grid-template-columns: 1fr; } }

        .modal-img { width: 100%; height: 300px; object-fit: cover; border-radius: 8px; background: #eee; }
        .modal-map { width: 100%; height: 300px; border-radius: 8px; border: 1px solid #ddd; }
        
        .modal-header { padding: 20px; border-bottom: 1px solid #eee; background: #fafafa; }
        .modal-title { margin: 0; font-size: 1.8em; }
        .modal-subtitle { color: #666; margin-top: 5px; }

        .detail-item { margin-bottom: 10px; border-bottom: 1px solid #f9f9f9; padding-bottom: 5px; }
        .detail-label { font-weight: bold; color: #888; font-size: 0.8em; text-transform: uppercase; }
        .detail-value { font-size: 1em; color: #333; }
        
        .admin-link { display: block; text-align: right; margin-top: 20px; color: #aaa; text-decoration: none; }
    </style>
</head>
<body>
    <h1>Encontre uma Loja Soul</h1>
    <p class="subtitle">{{ qtd }} autorizadas cadastradas</p>
    
    <div id="main-map"></div>

    <div class="search-box">
        <input type="text" id="buscaInput" placeholder="Busque por cidade, estado ou nome...">
        <button onclick="buscar()">Filtrar</button>
    </div>
    
    <div id="lista" class="grid"></div>
    
    <a href="/admin" class="admin-link">Area Administrativa</a>

    <div id="modalDetalhes" class="modal-overlay" onclick="fecharModal(event)">
        <div class="modal-body" onclick="event.stopPropagation()">
            <button class="modal-close" onclick="fecharModal()">×</button>
            
            <div class="modal-header">
                <span class="badge" id="m_perfil"></span>
                <h2 class="modal-title" id="m_nome">Nome da Loja</h2>
                <div class="modal-subtitle" id="m_local">Cidade - UF</div>
            </div>

            <div class="modal-content-grid">
                <div>
                    <div class="detail-item"><div class="detail-label">Endereço</div><div class="detail-value" id="m_endereco"></div></div>
                    <div class="detail-item"><div class="detail-label">Contato</div><div class="detail-value" id="m_contato"></div></div>
                    <div class="detail-item"><div class="detail-label">Horários</div><div class="detail-value" id="m_horario"></div></div>
                    <div class="detail-item"><div class="detail-label">Vendedor / Time</div><div class="detail-value" id="m_interno"></div></div>
                    <div class="detail-item"><div class="detail-label">Links</div><div class="detail-value" id="m_links"></div></div>
                </div>

                <div>
                    <img id="m_foto" class="modal-img" src="" style="display:none;">
                    <div id="modal-map" class="modal-map"></div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        // Mapa Principal
        var mainMap = L.map('main-map').setView([-14.2350, -51.9253], 4);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }).addTo(mainMap);
        var markersLayer = L.layerGroup().addTo(mainMap);
        
        // Mapa do Modal (inicia depois)
        var modalMap = null;

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
                // Pino no mapa principal
                if(l.lat && l.lon) {
                    let m = L.marker([l.lat, l.lon]).bindPopup(`<b>${l.nome}</b>`);
                    m.on('click', () => abrirModal(l)); // Clicar no pino abre o modal
                    markersLayer.addLayer(m);
                }
                
                // Card na lista
                html += `
                <div class="card" onclick='abrirModal(${JSON.stringify(l)})'>
                    <span class="badge">${l.perfil || 'Loja'}</span>
                    <h3>${l.nome}</h3>
                    <div class="info-row">📍 ${l.municipio} - ${l.uf}</div>
                    <div class="info-row">📞 ${l.telefone || '-'}</div>
                    <div class="btn-ver-mais">Ver Detalhes Completos</div>
                </div>`;
            });
            document.getElementById('lista').innerHTML = html;
        }

        function abrirModal(l) {
            // Preenche textos
            document.getElementById('m_nome').innerText = l.nome;
            document.getElementById('m_perfil').innerText = l.perfil;
            document.getElementById('m_local').innerText = `${l.municipio} - ${l.uf}`;
            document.getElementById('m_endereco').innerText = `${l.endereco}, ${l.numero} - ${l.bairro || ''} (CEP: ${l.cep || ''})`;
            
            // Contato
            let contatoHtml = "";
            if(l.telefone) contatoHtml += `Tel: ${l.telefone}<br>`;
            if(l.email) contatoHtml += `Email: ${l.email}<br>`;
            if(l.contato) contatoHtml += `Resp: ${l.contato}`;
            document.getElementById('m_contato').innerHTML = contatoHtml || "-";

            // Horários
            let horaHtml = "";
            if(l.horario_seg_sex) horaHtml += `Seg-Sex: ${l.horario_seg_sex}<br>`;
            if(l.horario_sab) horaHtml += `Sáb: ${l.horario_sab}`;
            document.getElementById('m_horario').innerHTML = horaHtml || "-";

            // Dados Internos (Vendedor/Time)
            document.getElementById('m_interno').innerText = `Vendedor: ${l.vendedor || '-'} | Time: ${l.time_soul || '-'}`;

            // Links
            let linksHtml = "";
            if(l.telefone) linksHtml += `<a href="https://wa.me/55${l.telefone.replace(/\D/g,'')}" target="_blank" style="color:green; font-weight:bold;">WhatsApp</a> | `;
            if(l.instagram) linksHtml += `<a href="https://instagram.com/${l.instagram.replace('@','').replace('/','')}" target="_blank" style="color:#E1306C; font-weight:bold;">Instagram</a>`;
            document.getElementById('m_links').innerHTML = linksHtml;

            // Foto
            let img = document.getElementById('m_foto');
            if(l.foto) {
                img.src = "/static/uploads/" + l.foto;
                img.style.display = "block";
            } else {
                img.style.display = "none";
            }

            // Exibe o Modal
            document.getElementById('modalDetalhes').style.display = 'flex';

            // Configura o Mapa do Modal (com delay para renderizar correto)
            setTimeout(() => {
                if (!modalMap) {
                    modalMap = L.map('modal-map');
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }).addTo(modalMap);
                }
                
                if (l.lat && l.lon) {
                    modalMap.setView([l.lat, l.lon], 15); // Zoom bem perto
                    // Remove marcadores antigos do modal
                    modalMap.eachLayer((layer) => {
                        if (layer instanceof L.Marker) { modalMap.removeLayer(layer); }
                    });
                    L.marker([l.lat, l.lon]).addTo(modalMap);
                    modalMap.invalidateSize(); // Corrige bug gráfico
                } else {
                    modalMap.setView([-14.23, -51.92], 4);
                }
            }, 200);
        }

        function fecharModal(e) {
            if(!e || e.target.id === 'modalDetalhes' || e.target.className === 'modal-close') {
                document.getElementById('modalDetalhes').style.display = 'none';
            }
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

# --- HTML ADMIN ---
HTML_ADMIN = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin - Soul Cycles</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; max-width: 1100px; margin: 0 auto; padding: 20px; background: #eee; }
        .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { display: flex; justify-content: space-between; border-bottom: 2px solid #000; padding-bottom: 10px; }
        .btn { padding: 8px 15px; border: none; cursor: pointer; border-radius: 4px; font-weight: bold; text-decoration: none; color: white; background: #000; }
        .btn-danger { background: #dc3545; }
        .btn-warning { background: #ffc107; color: #000; }
        .btn-info { background: #17a2b8; }
        
        /* Modal e Form */
        #form-container { display: none; background: #f9f9f9; padding: 20px; border: 1px solid #ddd; margin-bottom: 20px; border-radius: 8px; }
        .form-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        .col-1 { grid-column: span 1; } .col-2 { grid-column: span 2; } .col-4 { grid-column: span 4; }
        input, select { padding: 8px; width: 100%; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        label { font-size: 0.8em; font-weight: bold; color: #555; }
        .section-title { grid-column: span 4; margin-top: 10px; border-bottom: 1px solid #ccc; font-weight: bold; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.85em; }
        th, td { padding: 8px; border-bottom: 1px solid #ddd; text-align: left; }
        
        /* Modal de Edição */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 999; overflow-y: auto; }
        .modal-content { background: white; width: 95%; max-width: 800px; margin: 30px auto; padding: 20px; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" style="color:#666; text-decoration:none;">← Voltar ao Site</a>
        
        {% if msg %} <div style="background:#d4edda; color:#155724; padding:10px; margin:10px 0; text-align:center;">{{ msg }}</div> {% endif %}

        <h2>Gerenciar Lojas <button onclick="toggleForm()" class="btn">➕ Nova Loja</button></h2>

        <div id="form-container">
            <h3>Nova Loja</h3>
            <form action="/admin/add" method="POST" enctype="multipart/form-data" class="form-grid">
                
                <div class="section-title">Dados & Foto</div>
                <div class="col-2"><label>Nome</label><input type="text" name="nome" required></div>
                <div class="col-1"><label>Perfil</label>
                    <select name="perfil"><option>Loja</option><option>Mecânico</option><option>Revenda</option></select>
                </div>
                <div class="col-1"><label>Código</label><input type="text" name="codigo"></div>
                
                <div class="col-4">
                    <label>📸 Foto da Loja</label>
                    <input type="file" name="foto" accept="image/*">
                </div>

                <div class="section-title">Localização</div>
                <div class="col-2"><label>Rua</label><input type="text" name="endereco" required></div>
                <div class="col-1"><label>Número</label><input type="text" name="numero" required></div>
                <div class="col-1"><label>Bairro</label><input type="text" name="bairro"></div>
                <div class="col-2"><label>Cidade</label><input type="text" name="municipio" required></div>
                <div class="col-1"><label>UF</label><input type="text" name="uf" required></div>
                <div class="col-1"><label>CEP</label><input type="text" name="cep"></div>

                <div class="section-title">Extras</div>
                <div class="col-2"><label>Telefone</label><input type="text" name="telefone"></div>
                <div class="col-2"><label>Vendedor</label><input type="text" name="vendedor"></div>
                
                <input type="hidden" name="cnpj" value=""><input type="hidden" name="contato_nome" value="">
                
                <div class="col-4" style="margin-top:10px"><button class="btn" style="width:100%">Salvar</button></div>
            </form>
        </div>

        <input type="text" id="busca" onkeyup="filtrar()" placeholder="🔍 Pesquisar..." style="width:100%; padding:10px; margin-bottom:10px;">

        <table id="tabela">
            <thead><tr><th>Loja</th><th>Local</th><th>Foto</th><th>Ações</th></tr></thead>
            <tbody>
                {% for loja in lojas %}
                <tr>
                    <td><b>{{ loja['nome'] }}</b><br><small>{{ loja['perfil'] }}</small></td>
                    <td>{{ loja['municipio'] }}-{{ loja['uf'] }}</td>
                    <td>
                        {% if loja['foto'] %} <a href="/static/uploads/{{ loja['foto'] }}" target="_blank">Ver Foto</a>
                        {% else %} - {% endif %}
                    </td>
                    <td>
                        <button onclick='editar({{ loja | tojson }})' class="btn btn-warning">✏️</button>
                        <a href="/admin/delete/{{ loja['id'] }}" onclick="return confirm('Apagar?')" class="btn btn-danger">🗑️</a>
                        {% if not loja['lat'] %} <a href="/admin/geo/{{ loja['id'] }}" class="btn btn-info">🌍</a> {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <div id="modalEdit" class="modal">
        <div class="modal-content">
            <h3>Editar <button onclick="fechar()" class="btn btn-danger" style="float:right">X</button></h3>
            <form action="/admin/update" method="POST" enctype="multipart/form-data" class="form-grid">
                <input type="hidden" name="id" id="e_id">
                
                <div class="col-4"><label>Nome</label><input type="text" name="nome" id="e_nome" required></div>
                
                <div class="col-4">
                    <label>Trocar Foto (Deixe em branco para manter a atual)</label>
                    <input type="file" name="foto" accept="image/*">
                </div>

                <div class="col-2"><label>Rua</label><input type="text" name="endereco" id="e_endereco"></div>
                <div class="col-1"><label>Num</label><input type="text" name="numero" id="e_numero"></div>
                <div class="col-1"><label>UF</label><input type="text" name="uf" id="e_uf"></div>
                <div class="col-2"><label>Cidade</label><input type="text" name="municipio" id="e_municipio"></div>
                <div class="col-2"><label>Bairro</label><input type="text" name="bairro" id="e_bairro"></div>
                
                <div class="col-2"><label>Telefone</label><input type="text" name="telefone" id="e_telefone"></div>
                <div class="col-2"><label>Vendedor</label><input type="text" name="vendedor" id="e_vendedor"></div>

                <input type="hidden" name="perfil" id="e_perfil"><input type="hidden" name="codigo" id="e_codigo">
                <input type="hidden" name="cnpj" id="e_cnpj"><input type="hidden" name="contato_nome" id="e_contato_nome">
                <input type="hidden" name="cep" id="e_cep"><input type="hidden" name="email" id="e_email">
                <input type="hidden" name="instagram" id="e_instagram"><input type="hidden" name="horario_seg_sex" id="e_horario_seg_sex">
                <input type="hidden" name="horario_sab" id="e_horario_sab"><input type="hidden" name="time_soul" id="e_time_soul">

                <div class="col-4" style="margin-top:10px"><button class="btn" style="width:100%">Salvar Alterações</button></div>
            </form>
        </div>
    </div>

    <script>
        function toggleForm() { document.getElementById('form-container').style.display = 'block'; }
        function fechar() { document.getElementById('modalEdit').style.display = 'none'; }
        function editar(l) {
            document.getElementById('modalEdit').style.display = 'block';
            // Preenche campos principais
            ['id','nome','endereco','numero','bairro','municipio','uf','telefone','vendedor',
             'perfil','codigo','cnpj','contato_nome','cep','email','instagram','horario_seg_sex','horario_sab','time_soul']
             .forEach(field => {
                 if(document.getElementById('e_'+field)) document.getElementById('e_'+field).value = l[field] || '';
             });
        }
        function filtrar() {
            let termo = document.getElementById('busca').value.toLowerCase();
            let trs = document.querySelectorAll('#tabela tbody tr');
            trs.forEach(tr => {
                tr.style.display = tr.innerText.toLowerCase().includes(termo) ? '' : 'none';
            });
        }
    </script>
</body>
</html>
"""

# --- BACKEND ---
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = get_db()
    # Adicionada coluna 'foto'
    conn.execute('''
        CREATE TABLE IF NOT EXISTS lojas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT, perfil TEXT, nome TEXT, cnpj TEXT, contato TEXT,
            telefone TEXT, endereco TEXT, numero TEXT, bairro TEXT,
            uf TEXT, municipio TEXT, cep TEXT,
            horario_seg_sex TEXT, horario_sab TEXT,
            instagram TEXT, email TEXT, time_soul TEXT, vendedor TEXT,
            lat REAL, lon REAL, foto TEXT
        )
    ''')
    
    # Importação Simples se vazio
    if conn.execute('SELECT count(*) FROM lojas').fetchone()[0] == 0 and os.path.exists('dados.csv'):
        try:
            with open('dados.csv', mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                if 'NOME' not in reader.fieldnames:
                     f.seek(0)
                     reader = csv.DictReader(f, delimiter=',')
                for row in reader:
                    r = {k.strip(): v for k, v in row.items() if k}
                    if not r.get('NOME'): continue
                    conn.execute('''
                        INSERT INTO lojas (codigo, perfil, nome, cnpj, contato, telefone, endereco, numero, bairro, uf, municipio, cep, horario_seg_sex, horario_sab, instagram, email, time_soul, vendedor)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ''', (
                        r.get('CODIGO'), r.get('PERFIL'), r.get('NOME'), r.get('CNPJ'), r.get('CONTATO'), r.get('TELEFONE'),
                        r.get('ENDEREÇO'), r.get('NUMERO/COMPLEMENTO'), r.get('BAIRRO'), r.get('UF'), r.get('MUNICIPIO'),
                        r.get('CEP'), r.get('SEG. A SEX.'), r.get('SÁBADO'), r.get('INSTAGRAM'), r.get('E-mail'),
                        r.get('Time'), r.get('Vendedor')
                    ))
        except: pass
    conn.commit()
    conn.close()

init_db()

def geocode_address(address_str):
    try:
        geolocator = Nominatim(user_agent="soul_v5")
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
    
    # Processamento da Imagem
    filename = None
    if 'foto' in request.files:
        file = request.files['foto']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{f['nome']}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    conn = get_db()
    conn.execute('''
        INSERT INTO lojas (codigo, perfil, nome, cnpj, contato, telefone, endereco, numero, bairro, municipio, uf, cep, vendedor, lat, lon, foto)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        f.get('codigo'), f.get('perfil'), f.get('nome'), f.get('cnpj'), f.get('contato_nome'), f.get('telefone'),
        f.get('endereco'), f.get('numero'), f.get('bairro'), f.get('municipio'), f.get('uf'), f.get('cep'), f.get('vendedor'),
        lat, lon, filename
    ))
    conn.commit()
    conn.close()
    return redirect(url_for('admin', msg="Loja adicionada com foto!"))

@app.route('/admin/update', methods=['POST'])
def update_loja():
    f = request.form
    id_loja = f['id']
    endereco_completo = f"{f['endereco']}, {f['numero']} - {f['municipio']}, {f['uf']}, Brazil"
    lat, lon = geocode_address(endereco_completo)
    
    # Update básico
    sql = '''UPDATE lojas SET nome=?, endereco=?, numero=?, bairro=?, municipio=?, uf=?, telefone=?, vendedor=?'''
    params = [f['nome'], f['endereco'], f['numero'], f['bairro'], f['municipio'], f['uf'], f['telefone'], f['vendedor']]
    
    # Se achou GPS, atualiza
    if lat and lon:
        sql += ", lat=?, lon=?"
        params.extend([lat, lon])
        
    # Se enviou nova foto, atualiza
    if 'foto' in request.files:
        file = request.files['foto']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{f['nome']}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            sql += ", foto=?"
            params.append(filename)

    sql += " WHERE id=?"
    params.append(id_loja)
    
    conn = get_db()
    conn.execute(sql, params)
    conn.commit()
    conn.close()
    return redirect(url_for('admin', msg="Atualizado!"))

@app.route('/admin/delete/<int:id>')
def delete_loja(id):
    conn = get_db()
    conn.execute('DELETE FROM lojas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin', msg="Removido."))

@app.route('/admin/geo/<int:id>')
def force_geo(id):
    # (Mantido igual ao anterior, código omitido para economizar espaço mas funcionalidade inclusa no Admin)
    conn = get_db()
    l = conn.execute('SELECT * FROM lojas WHERE id = ?', (id,)).fetchone()
    if l:
        full = f"{l['endereco']}, {l['numero']} - {l['municipio']}, {l['uf']}, Brazil"
        lat, lon = geocode_address(full)
        if lat:
            conn.execute('UPDATE lojas SET lat=?, lon=? WHERE id=?', (lat, lon, id))
            msg = "GPS Atualizado!"
        else: msg = "Endereço não encontrado."
        conn.commit()
    conn.close()
    return redirect(url_for('admin', msg=msg))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
