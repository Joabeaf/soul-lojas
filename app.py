from flask import Flask, jsonify, request, render_template_string, redirect, url_for
import sqlite3
import csv
import os
import json
import urllib.request
import time
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configurações de Upload
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DB_NAME = "lojas.db"

# --- HTML PÚBLICO (BUSCA ÚNICA + DESIGN TREK) ---
HTML_PUBLICO = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rede Autorizada Soul</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
        
        body { font-family: 'Inter', sans-serif; max-width: 1400px; margin: 0 auto; padding: 0; background: #fff; color: #111; }

        /* HEADER */
        header { padding: 40px 20px; text-align: center; border-bottom: 1px solid #eee; margin-bottom: 0; }
        h1 { text-transform: uppercase; letter-spacing: 2px; font-weight: 900; font-size: 2.5rem; margin: 0 0 10px 0; }
        .subtitle { color: #666; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }

        /* MAPA */
        #main-map { height: 500px; width: 100%; background: #f4f4f4; margin-bottom: 0; z-index: 1; border-bottom: 1px solid #000; }

        /* BUSCA ÚNICA E MODERNA */
        .search-section { background: #f9f9f9; padding: 30px 20px; border-bottom: 1px solid #ddd; }
        .search-wrapper { max-width: 800px; margin: 0 auto; display: flex; gap: 0; position: relative; }
        
        input { 
            width: 100%; padding: 18px; border: 1px solid #ccc; border-right: none;
            font-size: 16px; font-family: 'Inter', sans-serif; outline: none; border-radius: 0;
        }
        input:focus { border-color: #000; outline: 2px solid #000; z-index: 2; }
        
        button { 
            padding: 0 40px; cursor: pointer; background: #000; color: #fff; 
            border: 1px solid #000; font-weight: 800; text-transform: uppercase; 
            letter-spacing: 1px; font-size: 14px; white-space: nowrap; border-radius: 0;
        }
        button:hover { background: #333; border-color: #333; }

        /* STATUS E AVISOS */
        .loader { display: none; text-align: center; padding: 20px; font-weight: bold; text-transform: uppercase; font-size: 0.8rem; color: #000; }
        .aviso-filtro { display:none; background: #000; color: #fff; padding: 15px; text-align: center; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }

        /* GRID */
        .grid-container { padding: 40px 20px; background: #fff; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 30px; }

        /* CARD (DESIGN TREK) */
        .card { 
            background: #fff; border: 1px solid #e5e5e5; display: flex; flex-direction: column; 
            cursor: pointer; transition: all 0.2s ease; position: relative; border-radius: 0;
        }
        .card:hover { border-color: #000; box-shadow: 0 10px 30px rgba(0,0,0,0.08); transform: translateY(-2px); }

        .card-img-top { width: 100%; height: 180px; object-fit: cover; background: #f4f4f4; display: none; }
        .card-body { padding: 25px; display: flex; flex-direction: column; gap: 8px; flex-grow: 1; }
        
        .card-header { display: flex; justify-content: space-between; align-items: start; }
        .card h3 { margin: 0; font-size: 1.1rem; font-weight: 800; text-transform: uppercase; line-height: 1.2; }
        .badge { background: #000; color: #fff; padding: 3px 8px; font-size: 0.6rem; font-weight: 700; text-transform: uppercase; height: fit-content; }
        
        .info-row { font-size: 0.9rem; color: #555; }
        .distancia-badge { margin-top: auto; font-size: 0.75rem; font-weight: bold; color: #000; border-top: 1px solid #eee; padding-top: 10px; }

        /* MODAL */
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(255,255,255,0.95); z-index: 9999; justify-content: center; align-items: center; }
        .modal-body { background: white; width: 90%; max-width: 1100px; height: 85vh; border: 1px solid #ccc; display: flex; flex-direction: column; position: relative; box-shadow: 0 20px 50px rgba(0,0,0,0.2); }
        .modal-close { position: absolute; top: 20px; right: 20px; font-size: 40px; line-height: 0.5; cursor: pointer; background: transparent; border: none; color: #000; z-index: 50; padding: 10px; }
        
        .modal-content-grid { display: grid; grid-template-columns: 45% 55%; flex-grow: 1; overflow: hidden; }
        @media (max-width: 800px) { .modal-content-grid { grid-template-columns: 1fr; overflow-y: auto; } }

        .col-info { padding: 50px 40px; overflow-y: auto; background: #fff; display: flex; flex-direction: column; gap: 20px; }
        .col-map { position: relative; height: 100%; background: #eee; }
        .modal-map { width: 100%; height: 100%; }

        .modal-title-area { margin-bottom: 20px; padding-right: 40px; }
        .modal-title { font-size: 2rem; font-weight: 900; text-transform: uppercase; line-height: 1; margin: 0 0 10px 0; }
        .modal-meta { display: flex; gap: 10px; }
        .modal-badge-black { background: #000; color: #fff; padding: 5px 10px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }
        .modal-badge-outline { border: 1px solid #000; color: #000; padding: 5px 10px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }
        
        .modal-img-banner { width: 100%; height: 250px; object-fit: cover; margin-bottom: 10px; background: #eee; }
        
        .detail-block { margin-bottom: 15px; }
        .detail-label { font-size: 0.7rem; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
        .detail-text { font-size: 1rem; color: #000; line-height: 1.5; }
        .detail-text a { color: #000; text-decoration: underline; font-weight: bold; }

        .admin-link { display: block; text-align: center; padding: 20px; color: #ccc; text-decoration: none; font-size: 0.8rem; text-transform: uppercase; }
    </style>
</head>
<body>

    <header>
        <h1>Soul Cycles</h1>
        <div class="subtitle">Localizador de Lojas Autorizadas</div>
    </header>

    <div id="aviso" class="aviso-filtro"></div>
    <div id="loader" class="loader">Consultando GPS e Rotas...</div>

    <div id="main-map"></div>

    <div class="search-section">
        <div class="search-wrapper">
            <input type="text" id="buscaInput" placeholder="DIGITE O NOME, CIDADE OU CEP (Somente números)">
            <button onclick="realizarBusca()">BUSCAR</button>
        </div>
    </div>
    
    <div class="grid-container">
        <p class="subtitle" style="text-align: left; margin-bottom: 20px;">{{ qtd }} RESULTADOS ENCONTRADOS</p>
        <div id="lista" class="grid"></div>
    </div>
    
    <a href="/admin" class="admin-link">Area Administrativa</a>

    <div id="modalDetalhes" class="modal-overlay" onclick="fecharModal(event)">
        <div class="modal-body" onclick="event.stopPropagation()">
            <button class="modal-close" onclick="fecharModal()">×</button>
            <div class="modal-content-grid">
                <div class="col-info">
                    <div class="modal-title-area">
                        <h2 class="modal-title" id="m_nome"></h2>
                        <div class="modal-meta">
                            <span class="modal-badge-black" id="m_perfil"></span>
                            <span class="modal-badge-outline" id="m_codigo_area"></span>
                        </div>
                    </div>
                    <img id="m_foto" class="modal-img-banner" src="" style="display:none;">
                    <div class="detail-block"><div class="detail-label">Localização</div><div class="detail-text" id="m_endereco"></div><div class="detail-text" id="m_local"></div></div>
                    <div class="detail-block"><div class="detail-label">Contato</div><div class="detail-text" id="m_contato"></div></div>
                    <div class="detail-block"><div class="detail-label">Atendimento</div><div class="detail-text" id="m_horario"></div></div>
                    <div class="detail-block"><div class="detail-label">Links Rápidos</div><div class="detail-text" id="m_links"></div></div>
                    <div class="detail-block"><div class="detail-label">Info Interna</div><div class="detail-text" id="m_interno" style="font-size: 0.85rem; color: #666;"></div></div>
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
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '© OpenStreetMap contributors', subdomains: 'abcd', maxZoom: 20
        }).addTo(mainMap);

        var markersLayer = L.layerGroup().addTo(mainMap);
        var radiusCircle = null;
        var modalMap = null;
        var allData = [];

        async function carregar() {
            let res = await fetch('/api/lojas');
            let dados = await res.json();
            allData = dados.lojas || []; 
            renderizar(allData);
            document.getElementById('aviso').style.display = 'none';
        }

        // --- LÓGICA DE BUSCA UNIFICADA ---
        function realizarBusca() {
            let termo = document.getElementById('buscaInput').value.trim();
            if(!termo) { carregar(); return; }

            // Regex: Aceita CEP com ou sem traço (12345-678 ou 12345678)
            let cepLimpo = termo.replace(/\D/g, '');
            
            if(cepLimpo.length === 8) {
                // É um CEP
                buscarCep(cepLimpo);
            } else {
                // É texto normal
                buscarTexto(termo);
            }
        }

        async function buscarCep(cep) {
            document.getElementById('loader').style.display = 'block';
            document.getElementById('lista').style.opacity = '0.3';

            try {
                let res = await fetch('/api/lojas?cep=' + cep);
                let resposta = await res.json();
                
                if(resposta.erro) {
                    alert(resposta.erro);
                } else {
                    let lojasFiltradas = resposta.lojas;
                    let centro = resposta.centro;

                    renderizar(lojasFiltradas);
                    
                    document.getElementById('aviso').style.display = 'block';
                    if (lojasFiltradas.length > 0) {
                        document.getElementById('aviso').innerText = `ENCONTRADAS ${lojasFiltradas.length} LOJAS EM UM RAIO DE 100KM DE ${resposta.endereco_base}`;
                    } else {
                        document.getElementById('aviso').innerText = `NENHUMA LOJA PRÓXIMA A ${resposta.endereco_base}`;
                    }

                    if(centro) {
                        mainMap.setView([centro[0], centro[1]], 8);
                        if(radiusCircle) mainMap.removeLayer(radiusCircle);
                        radiusCircle = L.circle([centro[0], centro[1]], {
                            color: '#000', fillColor: '#000', fillOpacity: 0.05, weight: 1, radius: 100000
                        }).addTo(mainMap);
                        mainMap.fitBounds(radiusCircle.getBounds());
                    }
                }
            } catch (e) { console.error(e); } 
            finally {
                document.getElementById('loader').style.display = 'none';
                document.getElementById('lista').style.opacity = '1';
            }
        }

        function buscarTexto(termo) {
            if(radiusCircle) { mainMap.removeLayer(radiusCircle); radiusCircle = null; }
            document.getElementById('aviso').style.display = 'none';
            
            fetch('/api/lojas').then(r => r.json()).then(d => {
                let todas = d.lojas;
                let filtrados = todas.filter(l => (l.nome + ' ' + l.municipio + ' ' + l.uf).toLowerCase().includes(termo.toLowerCase()));
                renderizar(filtrados);
                if(filtrados.length > 0 && filtrados[0].lat) mainMap.setView([filtrados[0].lat, filtrados[0].lon], 10);
            });
        }

        function renderizar(lojas) {
            markersLayer.clearLayers();
            let html = '';
            if (!lojas || lojas.length === 0) html = '<p style="text-align:center; grid-column:1/-1; color:#999;">Nenhuma loja encontrada.</p>';
            else {
                lojas.forEach(l => {
                    if(l.lat && l.lon) {
                        let m = L.marker([l.lat, l.lon]).bindPopup(`<b>${l.nome}</b>`);
                        m.on('click', () => abrirModal(l));
                        markersLayer.addLayer(m);
                    }
                    let imgHtml = l.foto ? `<img src="/static/uploads/${l.foto}" class="card-img-top" style="display:block;">` : '';
                    let distHtml = l.distancia ? `<div class="distancia-badge">${l.distancia} KM DA SUA LOCALIZAÇÃO</div>` : '';
                    html += `
                    <div class="card" onclick='abrirModal(${JSON.stringify(l)})'>
                        ${imgHtml}
                        <div class="card-body">
                            <div class="card-header">
                                <h3>${l.nome}</h3>
                                <span class="badge">${l.perfil || 'LOJA'}</span>
                            </div>
                            <div class="info-row">${l.municipio} - ${l.uf}</div>
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
            document.getElementById('m_codigo_area').style.display = l.codigo ? 'inline-block' : 'none';
            if(l.codigo) document.getElementById('m_codigo_area').innerText = `COD: ${l.codigo}`;
            document.getElementById('m_endereco').innerText = `${l.endereco}, ${l.numero} - ${l.bairro || ''}`;
            
            let contatoHtml = "";
            if(l.telefone) contatoHtml += `${l.telefone}<br>`;
            if(l.email) contatoHtml += `${l.email}<br>`;
            if(l.contato) contatoHtml += `Resp: ${l.contato}`;
            document.getElementById('m_contato').innerHTML = contatoHtml || "-";

            let horaHtml = "";
            if(l.horario_seg_sex) horaHtml += `Seg-Sex: ${l.horario_seg_sex}<br>`;
            if(l.horario_sab) horaHtml += `Sáb: ${l.horario_sab}`;
            document.getElementById('m_horario').innerHTML = horaHtml || "-";

            document.getElementById('m_interno').innerText = `Vendedor: ${l.vendedor || '-'} | Time: ${l.time_soul || '-'}`;

            let linksHtml = "";
            if(l.telefone) linksHtml += `<a href="https://wa.me/55${l.telefone.replace(/\D/g,'')}" target="_blank">WHATSAPP</a> &nbsp;&nbsp; `;
            if(l.instagram) linksHtml += `<a href="https://instagram.com/${l.instagram.replace('@','').replace('/','')}" target="_blank">INSTAGRAM</a>`;
            document.getElementById('m_links').innerHTML = linksHtml;

            let img = document.getElementById('m_foto');
            if(l.foto) { img.src = "/static/uploads/" + l.foto; img.style.display = "block"; } else { img.style.display = "none"; }

            document.getElementById('modalDetalhes').style.display = 'flex';
            setTimeout(() => {
                if (!modalMap) {
                    modalMap = L.map('modal-map');
                    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', { subdomains: 'abcd', maxZoom: 20 }).addTo(modalMap);
                }
                if (l.lat && l.lon) {
                    modalMap.setView([l.lat, l.lon], 15);
                    modalMap.eachLayer((layer) => { if (layer instanceof L.Marker) modalMap.removeLayer(layer); });
                    var blackIcon = new L.Icon({
                        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/markers/marker-icon-2x-black.png',
                        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                        iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
                    });
                    L.marker([l.lat, l.lon], {icon: blackIcon}).addTo(modalMap);
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
        
        document.getElementById("buscaInput").addEventListener("keypress", function(event) { if (event.key === "Enter") realizarBusca(); });
        carregar();
    </script>
</body>
</html>
"""

# --- HTML ADMIN (ESTILO TREK - CORRIGIDO) ---
HTML_ADMIN = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin - Soul Cycles</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #eee; }
        .container { background: white; padding: 40px; border: 1px solid #ccc; }
        h2 { display: flex; justify-content: space-between; border-bottom: 2px solid #000; padding-bottom: 15px; margin-top:0; text-transform: uppercase; }
        
        .btn { padding: 10px 20px; border: none; cursor: pointer; font-weight: bold; text-decoration: none; color: white; background: #000; text-transform: uppercase; font-size: 0.8rem; }
        .btn:hover { background: #333; }
        .btn-danger { background: #dc3545; }
        .btn-warning { background: #ffc107; color: #000; }
        
        input, select { padding: 10px; width: 100%; border: 1px solid #ccc; box-sizing: border-box; margin-bottom: 5px; }
        label { font-size: 0.7rem; font-weight: bold; color: #666; text-transform: uppercase; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9rem; }
        th { background: #000; color: #fff; text-align: left; padding: 10px; text-transform: uppercase; font-size: 0.8rem; }
        td { padding: 10px; border-bottom: 1px solid #eee; }
        tr:hover { background: #f9f9f9; }

        /* Modal Admin */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 999; overflow-y: auto; }
        .modal-content { background: white; width: 90%; max-width: 800px; margin: 50px auto; padding: 30px; }
        .form-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }
        .col-1 { grid-column: span 1; } .col-2 { grid-column: span 2; } .col-4 { grid-column: span 4; }
        .section-title { grid-column: span 4; margin-top: 20px; border-bottom: 1px solid #eee; font-weight: bold; text-transform: uppercase; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" style="color:#666; text-decoration:none; font-size:0.8rem; text-transform:uppercase;">← Voltar ao Site</a>
        {% if msg %} <div style="background:#000; color:#fff; padding:10px; margin:10px 0; text-align:center;">{{ msg }}</div> {% endif %}
        
        <h2>Gerenciar Lojas <button onclick="toggleForm()" class="btn">Nova Loja</button></h2>

        <div id="modalAdd" class="modal">
            <div class="modal-content">
                <h3 style="text-transform:uppercase;">Nova Loja <button onclick="fecharAdd()" class="btn btn-danger" style="float:right">X</button></h3>
                <form action="/admin/add" method="POST" enctype="multipart/form-data" class="form-grid">
                    <div class="section-title">Dados</div>
                    <div class="col-2"><label>Nome</label><input type="text" name="nome" required></div>
                    <div class="col-1"><label>Perfil</label><select name="perfil"><option>Loja</option><option>Mecânico</option><option>Revenda</option></select></div>
                    <div class="col-1"><label>Código</label><input type="text" name="codigo"></div>
                    <div class="col-4"><label>Foto</label><input type="file" name="foto" accept="image/*"></div>
                    
                    <div class="section-title">Endereço</div>
                    <div class="col-2"><label>Rua</label><input type="text" name="endereco" required></div>
                    <div class="col-1"><label>Nº</label><input type="text" name="numero" required></div>
                    <div class="col-1"><label>Bairro</label><input type="text" name="bairro"></div>
                    <div class="col-2"><label>Cidade</label><input type="text" name="municipio" required></div>
                    <div class="col-1"><label>UF</label><input type="text" name="uf" required></div>
                    <div class="col-1"><label>CEP</label><input type="text" name="cep"></div>
                    
                    <div class="section-title">Extras</div>
                    <div class="col-2"><label>Telefone</label><input type="text" name="telefone"></div>
                    <div class="col-2"><label>Vendedor</label><input type="text" name="vendedor"></div>
                    <input type="hidden" name="cnpj"><input type="hidden" name="contato_nome">
                    
                    <div class="col-4" style="margin-top:10px"><button class="btn" style="width:100%">Salvar Cadastro</button></div>
                </form>
            </div>
        </div>

        <input type="text" id="busca" onkeyup="filtrar()" placeholder="PESQUISAR..." style="padding:15px; border:2px solid #000; margin-bottom:20px;">

        <table id="tabela">
            <thead><tr><th>Cód</th><th>Loja</th><th>Local</th><th>Foto</th><th>Ações</th></tr></thead>
            <tbody>
                {% for loja in lojas %}
                <tr>
                    <td>{{ loja['codigo'] }}</td>
                    <td><b>{{ loja['nome'] }}</b><br><small>{{ loja['perfil'] }}</small></td>
                    <td>{{ loja['municipio'] }}-{{ loja['uf'] }}</td>
                    <td>{% if loja['foto'] %}SIM{% else %}NÃO{% endif %}</td>
                    <td>
                        <button onclick='editar({{ loja | tojson }})' class="btn btn-warning">EDITAR</button>
                        <a href="/admin/delete/{{ loja['id'] }}" onclick="return confirm('Apagar?')" class="btn btn-danger">X</a>
                        {% if not loja['lat'] %} <a href="/admin/geo/{{ loja['id'] }}" class="btn">GPS</a> {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <div id="modalEdit" class="modal">
        <div class="modal-content">
            <h3 style="text-transform:uppercase;">Editar <button onclick="fechar()" class="btn btn-danger" style="float:right">X</button></h3>
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
        function toggleForm() { document.getElementById('modalAdd').style.display = 'block'; }
        function fecharAdd() { document.getElementById('modalAdd').style.display = 'none'; }
        function fechar() { document.getElementById('modalEdit').style.display = 'none'; }
        function editar(l) {
            document.getElementById('modalEdit').style.display = 'block';
            ['id','nome','endereco','numero','bairro','municipio','uf','telefone','vendedor',
             'perfil','codigo','cnpj','contato_nome','cep','email','instagram','horario_seg_sex','horario_sab','time_soul']
             .forEach(field => { if(document.getElementById('e_'+field)) document.getElementById('e_'+field).value = l[field] || ''; });
        }
        function filtrar() {
            let termo = document.getElementById('busca').value.toLowerCase();
            let trs = document.querySelectorAll('#tabela tbody tr');
            trs.forEach(tr => { tr.style.display = tr.innerText.toLowerCase().includes(termo) ? '' : 'none'; });
        }
    </script>
</body>
</html>
"""

# --- BACKEND (Python) ---
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

# --- FUNÇÃO GEOCODING ROBUSTA (COM RETRY) ---
def geocode_address(address_str):
    geolocator = Nominatim(user_agent="soul_cycles_unique_id_v20", timeout=10)
    
    # Tenta 3 vezes antes de desistir (Persistência)
    for attempt in range(3):
        try:
            location = geolocator.geocode(address_str)
            if location:
                return location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderUnavailable):
            time.sleep(2) # Espera 2 segundos antes de tentar de novo
            continue
        except Exception as e:
            print(f"Erro GPS Fatal: {e}")
            break
            
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

    if cep_busca:
        try:
            # 1. Busca endereço no ViaCEP
            url_viacep = f"https://viacep.com.br/ws/{cep_busca}/json/"
            req = urllib.request.Request(url_viacep, headers={'User-Agent': 'SoulApp/1.0'})
            
            with urllib.request.urlopen(req) as response:
                dados_cep = json.loads(response.read().decode())
                
                if 'erro' in dados_cep: return jsonify({'erro': 'CEP não encontrado.'})
                
                # 2. Busca coordenadas do endereço retornado (COM RETRY TBM)
                texto_busca = f"{dados_cep['logradouro']}, {dados_cep['localidade']} - {dados_cep['uf']}, Brazil"
                lat, lon = geocode_address(texto_busca) # Usa a função robusta
                
                if not lat:
                     texto_busca = f"{dados_cep['localidade']} - {dados_cep['uf']}, Brazil"
                     lat, lon = geocode_address(texto_busca)

                if lat:
                    user_coords = (lat, lon)
                    lojas_proximas = []

                    for l in lista:
                        if l['lat'] and l['lon']:
                            store_coords = (l['lat'], l['lon'])
                            dist = geodesic(user_coords, store_coords).km
                            if dist <= 100: 
                                l['distancia'] = round(dist, 1)
                                lojas_proximas.append(l)
                    
                    lojas_proximas.sort(key=lambda x: x['distancia'])
                    
                    return jsonify({
                        'centro': user_coords,
                        'endereco_base': f"{dados_cep['localidade']} - {dados_cep['uf']}",
                        'lojas': lojas_proximas
                    })
                else: return jsonify({'erro': 'Endereço do CEP não localizado no mapa.'})

        except Exception as e:
            print(f"Erro na busca: {e}")
            return jsonify({'erro': 'Erro ao processar busca.'})

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
    return redirect(url_for('admin', msg="Loja adicionada!"))

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
    msg = "Erro desconhecido"
    if l:
        full = f"{l['endereco']}, {l['numero']} - {l['municipio']}, {l['uf']}, Brazil"
        lat, lon = geocode_address(full)
        if lat:
            conn.execute('UPDATE lojas SET lat=?, lon=? WHERE id=?', (lat, lon, id))
            msg = "GPS Atualizado com sucesso!"
        else: msg = "Endereço não encontrado pelo GPS (Tentamos 3 vezes)."
        conn.commit()
    conn.close()
    return redirect(url_for('admin', msg=msg))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
