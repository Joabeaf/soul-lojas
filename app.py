from flask import Flask, jsonify, request, render_template_string, redirect, url_for
import sqlite3
import csv
import os
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configurações de Upload
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
        body { font-family: 'Segoe UI', sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f4f6f8; color: #333; }
        h1, .subtitle { text-align: center; }
        
        #main-map { height: 450px; width: 100%; border-radius: 12px; margin-bottom: 20px; border: 2px solid #ddd; z-index: 1; }
        
        /* BUSCA */
        .search-container { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 20px; background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .input-group { display: flex; gap: 5px; flex-grow: 1; max-width: 500px; }
        input { padding: 12px; width: 100%; border: 1px solid #ccc; border-radius: 6px; font-size: 16px; }
        button { padding: 12px 20px; cursor: pointer; background: #000; color: #fff; border: none; border-radius: 6px; font-weight: bold; white-space: nowrap; transition: background 0.2s; }
        button:hover { background: #333; }
        button.btn-cep { background: #007bff; }
        button.btn-cep:hover { background: #0056b3; }

        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 15px; }
        
        /* CARD */
        .card { 
            background: #fff; border-radius: 12px; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); 
            cursor: pointer; transition: transform 0.2s; 
            display: flex; align-items: center; 
            padding: 15px; gap: 15px; border: 1px solid #eee; position: relative;
        }
        .card:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); border-color: #000; }
        
        .card-img-box { 
            width: 60px; height: 60px; flex-shrink: 0; 
            border-radius: 50%; overflow: hidden; 
            background: #f0f0f0; display: flex; justify-content: center; align-items: center; border: 1px solid #ddd;
        }
        .card-img { width: 100%; height: 100%; object-fit: cover; }
        .card-initials { font-size: 1.2em; font-weight: bold; color: #555; text-transform: uppercase; }

        .card-content { flex-grow: 1; min-width: 0; }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px; }
        .card h3 { margin: 0; font-size: 1.1em; color: #000; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .badge { background: #eee; padding: 2px 6px; font-size: 0.7em; font-weight: bold; border-radius: 4px; color: #666; text-transform: uppercase; }
        .info-row { font-size: 0.9em; color: #666; }
        
        .distancia-badge {
            background: #e3f2fd; color: #0d47a1; font-weight: bold; font-size: 0.85em;
            padding: 4px 8px; border-radius: 4px; margin-top: 5px; display: inline-block;
        }

        /* MODAL */
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 9999; justify-content: center; align-items: center; }
        .modal-body { background: white; width: 95%; max-width: 1000px; height: 85vh; border-radius: 10px; display: flex; flex-direction: column; overflow: hidden; position: relative; }
        
        .modal-close { 
            position: absolute; top: 10px; right: 15px; 
            font-size: 30px; line-height: 1; cursor: pointer; 
            background: #fff; border: none; font-weight: bold; color: #333; 
            z-index: 20; padding: 5px; border-radius: 50%; width: 40px; height: 40px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .modal-close:hover { background: #f0f0f0; color: red; }
        
        .modal-header-area { padding: 30px 20px 15px 20px; background: #fafafa; border-bottom: 1px solid #eee; }
        .modal-title { margin: 0; font-size: 1.8em; padding-right: 40px; }
        .modal-code { font-weight: bold; color: #000; background: #FFC107; padding: 2px 8px; border-radius: 4px; font-size: 0.9em; display: inline-block; margin-top: 5px; }

        .modal-content-grid { display: grid; grid-template-columns: 55% 45%; flex-grow: 1; overflow: hidden; }
        @media (max-width: 768px) { .modal-content-grid { grid-template-columns: 1fr; overflow-y: auto; } }

        .col-info { padding: 20px; overflow-y: auto; background: #fff; }
        .modal-img-banner { width: 100%; height: 200px; object-fit: cover; border-radius: 8px; margin-bottom: 20px; border: 1px solid #eee; }
        
        .detail-item { margin-bottom: 15px; border-bottom: 1px solid #f5f5f5; padding-bottom: 5px; }
        .detail-label { font-weight: bold; color: #888; font-size: 0.75em; text-transform: uppercase; margin-bottom: 3px; }
        .detail-value { font-size: 0.95em; color: #333; line-height: 1.4; }

        .col-map { position: relative; height: 100%; background: #eee; border-left: 1px solid #ddd; }
        .modal-map { width: 100%; height: 100%; }

        .admin-link { display: block; text-align: right; margin-top: 20px; color: #aaa; text-decoration: none; }
        .loader { display: none; text-align: center; margin: 10px 0; color: #007bff; font-weight: bold; }
        .aviso-filtro { display:none; background: #fff3cd; color: #856404; padding: 10px; text-align: center; border-radius: 6px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <h1>Encontre uma Loja Soul</h1>
    <p class="subtitle">{{ qtd }} autorizadas cadastradas</p>
    
    <div id="main-map"></div>

    <div class="search-container">
        <div class="input-group">
            <input type="text" id="buscaInput" placeholder="Busque por Cidade, Estado ou Nome...">
            <button onclick="buscarTexto()">🔍 Buscar</button>
        </div>
        <div class="input-group" style="max-width: 280px;">
            <input type="text" id="cepInput" placeholder="Digite seu CEP">
            <button class="btn-cep" onclick="buscarCep()">📍 Lojas até 100km</button>
        </div>
    </div>
    
    <div id="aviso" class="aviso-filtro">Mostrando apenas lojas num raio de 100km do seu CEP.</div>
    <div id="loader" class="loader">Calculando rota e distâncias...</div>
    <div id="lista" class="grid"></div>
    
    <a href="/admin" class="admin-link">Area Administrativa</a>

    <div id="modalDetalhes" class="modal-overlay" onclick="fecharModal(event)">
        <div class="modal-body" onclick="event.stopPropagation()">
            <button class="modal-close" onclick="fecharModal()">×</button>
            
            <div class="modal-header-area">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <h2 class="modal-title" id="m_nome">Nome da Loja</h2>
                        <div id="m_codigo_area"></div>
                    </div>
                    <span class="badge" id="m_perfil" style="font-size: 0.9em; margin-top: 5px;">PERFIL</span>
                </div>
                <div id="m_local" style="color:#666; margin-top:5px;">Cidade - UF</div>
            </div>

            <div class="modal-content-grid">
                <div class="col-info">
                    <img id="m_foto" class="modal-img-banner" src="" style="display:none;">
                    <div class="detail-item"><div class="detail-label">Endereço</div><div class="detail-value" id="m_endereco"></div></div>
                    <div class="detail-item"><div class="detail-label">Contatos</div><div class="detail-value" id="m_contato"></div></div>
                    <div class="detail-item"><div class="detail-label">Horário de Atendimento</div><div class="detail-value" id="m_horario"></div></div>
                    <div class="detail-item"><div class="detail-label">Informações Internas</div><div class="detail-value" id="m_interno"></div></div>
                    <div class="detail-item" style="border:none;"><div class="detail-label">Ações Rápidas</div><div class="detail-value" id="m_links"></div></div>
                </div>
                <div class="col-map">
                    <div id="modal-map" class="modal-map"></div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var mainMap = L.map('main-map').setView([-14.2350, -51.9253], 4);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }).addTo(mainMap);
        var markersLayer = L.layerGroup().addTo(mainMap);
        var radiusCircle = null; // Círculo de 100km
        var modalMap = null;
        var allData = [];

        async function carregar() {
            // Carrega TODAS as lojas inicialmente
            let res = await fetch('/api/lojas');
            let dados = await res.json();
            allData = dados.lojas || []; 
            renderizar(allData);
            document.getElementById('aviso').style.display = 'none';
        }

        async function buscarCep() {
            let cep = document.getElementById('cepInput').value.replace(/\D/g, '');
            if (cep.length !== 8) { alert("Digite um CEP válido (8 números)"); return; }

            document.getElementById('loader').style.display = 'block';
            document.getElementById('lista').style.opacity = '0.5';

            try {
                // Chama a API que filtra por 100km
                let res = await fetch('/api/lojas?cep=' + cep);
                let resposta = await res.json();
                
                if(resposta.erro) {
                    alert(resposta.erro);
                } else {
                    // Atualiza a lista apenas com as lojas filtradas
                    let lojasFiltradas = resposta.lojas;
                    let centro = resposta.centro;

                    renderizar(lojasFiltradas);
                    
                    document.getElementById('aviso').style.display = 'block';
                    document.getElementById('aviso').innerText = `Encontramos ${lojasFiltradas.length} lojas num raio de 100km do CEP ${cep}.`;

                    // ZOOM NO ESTADO/REGIAO
                    if(centro) {
                        mainMap.setView([centro[0], centro[1]], 8); // Zoom 8 é bom para visualizar raio de 100km
                        
                        // Desenha círculo de 100km
                        if(radiusCircle) mainMap.removeLayer(radiusCircle);
                        radiusCircle = L.circle([centro[0], centro[1]], {
                            color: 'blue',
                            fillColor: '#blue',
                            fillOpacity: 0.1,
                            radius: 100000 // 100km em metros
                        }).addTo(mainMap);
                    }
                }
            } catch (e) {
                console.error(e);
                alert("Erro ao buscar CEP.");
            } finally {
                document.getElementById('loader').style.display = 'none';
                document.getElementById('lista').style.opacity = '1';
            }
        }

        function buscarTexto() {
            // Limpa o círculo de CEP se houver
            if(radiusCircle) { mainMap.removeLayer(radiusCircle); radiusCircle = null; }
            document.getElementById('aviso').style.display = 'none';

            let termo = document.getElementById('buscaInput').value.toLowerCase();
            
            // Se estiver vazio, recarrega tudo do backend para garantir
            if(!termo) { carregar(); return; }

            // Filtra localmente na lista atual (ou recarrega tudo se preferir)
            // Aqui vamos recarregar tudo para tirar o filtro de 100km se o usuário quiser buscar por nome
            fetch('/api/lojas').then(r => r.json()).then(d => {
                let todas = d.lojas;
                let filtrados = todas.filter(l => 
                    (l.nome + ' ' + l.municipio + ' ' + l.uf).toLowerCase().includes(termo)
                );
                renderizar(filtrados);
                // Se tiver resultado, foca no primeiro
                if(filtrados.length > 0 && filtrados[0].lat) {
                    mainMap.setView([filtrados[0].lat, filtrados[0].lon], 6);
                }
            });
        }

        function pegarIniciais(nome) {
            if(!nome) return "SL";
            let partes = nome.trim().split(" ");
            if (partes.length === 1) return partes[0].substring(0, 2).toUpperCase();
            return (partes[0][0] + partes[1][0]).toUpperCase();
        }

        function renderizar(lojas) {
            markersLayer.clearLayers();
            let html = '';
            
            if (!lojas || lojas.length === 0) html = '<p style="text-align:center; grid-column:1/-1;">Nenhuma loja encontrada nesta região.</p>';
            else {
                lojas.forEach(l => {
                    if(l.lat && l.lon) {
                        let m = L.marker([l.lat, l.lon]).bindPopup(`<b>${l.nome}</b>`);
                        m.on('click', () => abrirModal(l));
                        markersLayer.addLayer(m);
                    }

                    let imagemHtml = l.foto ? 
                        `<img src="/static/uploads/${l.foto}" class="card-img">` : 
                        `<div class="card-initials">${pegarIniciais(l.nome)}</div>`;
                    
                    let distHtml = l.distancia ? 
                        `<div class="distancia-badge">📍 A ${l.distancia} km de você</div>` : '';

                    html += `
                    <div class="card" onclick='abrirModal(${JSON.stringify(l)})'>
                        <div class="card-img-box">${imagemHtml}</div>
                        <div class="card-content">
                            <div class="card-header">
                                <h3>${l.nome}</h3>
                                <span class="badge">${l.perfil || 'Loja'}</span>
                            </div>
                            <div class="info-row">📍 ${l.municipio} - ${l.uf}</div>
                            ${distHtml}
                        </div>
                    </div>`;
                });
            }
            document.getElementById('lista').innerHTML = html;
        }

        function abrirModal(l) {
            document.getElementById('m_nome').innerText = l.nome;
            document.getElementById('m_perfil').innerText = l.perfil;
            document.getElementById('m_local').innerText = `${l.municipio} - ${l.uf}`;
            
            let codigoHtml = l.codigo ? `<span class="modal-code">CÓD: ${l.codigo}</span>` : '';
            document.getElementById('m_codigo_area').innerHTML = codigoHtml;
            document.getElementById('m_endereco').innerText = `${l.endereco}, ${l.numero} - ${l.bairro || ''} (CEP: ${l.cep || ''})`;
            
            let contatoHtml = "";
            if(l.telefone) contatoHtml += `Tel: ${l.telefone}<br>`;
            if(l.email) contatoHtml += `Email: ${l.email}<br>`;
            if(l.contato) contatoHtml += `Responsável: ${l.contato}`;
            document.getElementById('m_contato').innerHTML = contatoHtml || "-";

            let horaHtml = "";
            if(l.horario_seg_sex) horaHtml += `Seg-Sex: ${l.horario_seg_sex}<br>`;
            if(l.horario_sab) horaHtml += `Sáb: ${l.horario_sab}`;
            document.getElementById('m_horario').innerHTML = horaHtml || "-";

            document.getElementById('m_interno').innerText = `Vendedor: ${l.vendedor || '-'} | Time: ${l.time_soul || '-'}`;

            let linksHtml = "";
            if(l.telefone) linksHtml += `<a href="https://wa.me/55${l.telefone.replace(/\D/g,'')}" target="_blank" style="color:green; font-weight:bold; margin-right:15px; text-decoration:none;">📲 WhatsApp</a>`;
            if(l.instagram) linksHtml += `<a href="https://instagram.com/${l.instagram.replace('@','').replace('/','')}" target="_blank" style="color:#E1306C; font-weight:bold; text-decoration:none;">📸 Instagram</a>`;
            document.getElementById('m_links').innerHTML = linksHtml;

            let img = document.getElementById('m_foto');
            if(l.foto) { img.src = "/static/uploads/" + l.foto; img.style.display = "block"; } 
            else { img.style.display = "none"; }

            document.getElementById('modalDetalhes').style.display = 'flex';

            setTimeout(() => {
                if (!modalMap) {
                    modalMap = L.map('modal-map');
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }).addTo(modalMap);
                }
                if (l.lat && l.lon) {
                    modalMap.setView([l.lat, l.lon], 15);
                    modalMap.eachLayer((layer) => { if (layer instanceof L.Marker) modalMap.removeLayer(layer); });
                    L.marker([l.lat, l.lon]).addTo(modalMap);
                    modalMap.invalidateSize();
                } else {
                    modalMap.setView([-14.23, -51.92], 4);
                    modalMap.invalidateSize();
                }
            }, 200);
        }

        function fecharModal(e) {
            if(!e || e.target.id === 'modalDetalhes' || e.target.className === 'modal-close') {
                document.getElementById('modalDetalhes').style.display = 'none';
            }
        }
        
        document.getElementById("buscaInput").addEventListener("keypress", function(event) { if (event.key === "Enter") buscarTexto(); });
        document.getElementById("cepInput").addEventListener("keypress", function(event) { if (event.key === "Enter") buscarCep(); });

        carregar();
    </script>
</body>
</html>
"""

# --- HTML ADMIN (Mantido igual) ---
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
        
        #form-container { display: none; background: #f9f9f9; padding: 20px; border: 1px solid #ddd; margin-bottom: 20px; border-radius: 8px; }
        .form-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        .col-1 { grid-column: span 1; } .col-2 { grid-column: span 2; } .col-4 { grid-column: span 4; }
        input, select { padding: 8px; width: 100%; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        label { font-size: 0.8em; font-weight: bold; color: #555; }
        .section-title { grid-column: span 4; margin-top: 10px; border-bottom: 1px solid #ccc; font-weight: bold; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.85em; }
        th, td { padding: 8px; border-bottom: 1px solid #ddd; text-align: left; }
        
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
                <div class="col-4"><label>📸 Foto da Loja</label><input type="file" name="foto" accept="image/*"></div>

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
            <thead><tr><th>Cód</th><th>Loja</th><th>Local</th><th>Foto</th><th>Ações</th></tr></thead>
            <tbody>
                {% for loja in lojas %}
                <tr>
                    <td>{{ loja['codigo'] }}</td>
                    <td><b>{{ loja['nome'] }}</b><br><small>{{ loja['perfil'] }}</small></td>
                    <td>{{ loja['municipio'] }}-{{ loja['uf'] }}</td>
                    <td>{% if loja['foto'] %}✅{% else %}❌{% endif %}</td>
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
                
                <div class="col-2"><label>Código</label><input type="text" name="codigo" id="e_codigo"></div>
                <div class="col-2"><label>Nome</label><input type="text" name="nome" id="e_nome" required></div>
                <div class="col-4"><label>Trocar Foto</label><input type="file" name="foto" accept="image/*"></div>
                
                <div class="col-2"><label>Rua</label><input type="text" name="endereco" id="e_endereco"></div>
                <div class="col-1"><label>Num</label><input type="text" name="numero" id="e_numero"></div>
                <div class="col-1"><label>UF</label><input type="text" name="uf" id="e_uf"></div>
                <div class="col-2"><label>Cidade</label><input type="text" name="municipio" id="e_municipio"></div>
                <div class="col-2"><label>Bairro</label><input type="text" name="bairro" id="e_bairro"></div>
                
                <div class="col-2"><label>Telefone</label><input type="text" name="telefone" id="e_telefone"></div>
                <div class="col-2"><label>Vendedor</label><input type="text" name="vendedor" id="e_vendedor"></div>

                <input type="hidden" name="perfil" id="e_perfil">
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
    cep_busca = request.args.get('cep')
    conn = get_db()
    lojas = conn.execute('SELECT * FROM lojas').fetchall()
    conn.close()
    
    lista = [dict(ix) for ix in lojas]

    # FILTRO POR CEP E DISTÂNCIA
    if cep_busca:
        try:
            geolocator = Nominatim(user_agent="soul_cep")
            location = geolocator.geocode(f"{cep_busca}, Brazil")
            if location:
                user_coords = (location.latitude, location.longitude)
                lojas_proximas = []

                for l in lista:
                    if l['lat'] and l['lon']:
                        store_coords = (l['lat'], l['lon'])
                        dist = geodesic(user_coords, store_coords).km
                        if dist <= 100: # Filtro de 100 KM
                            l['distancia'] = round(dist, 1)
                            lojas_proximas.append(l)
                
                # Ordena da mais perto para a mais longe
                lojas_proximas.sort(key=lambda x: x['distancia'])
                
                return jsonify({
                    'centro': user_coords,
                    'lojas': lojas_proximas
                })
            else:
                return jsonify({'erro': 'CEP não encontrado no mapa.'})
        except Exception as e:
            print(e)
            return jsonify({'erro': 'Erro ao calcular rota.'})

    return jsonify({'lojas': lista})

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
    
    sql = '''UPDATE lojas SET codigo=?, nome=?, endereco=?, numero=?, bairro=?, municipio=?, uf=?, telefone=?, vendedor=?'''
    params = [f['codigo'], f['nome'], f['endereco'], f['numero'], f['bairro'], f['municipio'], f['uf'], f['telefone'], f['vendedor']]
    
    if lat and lon:
        sql += ", lat=?, lon=?"
        params.extend([lat, lon])
        
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
