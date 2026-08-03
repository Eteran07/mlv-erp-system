import os
import glob
import json
import base64
import requests
import pandas as pd
import re
import time
import asyncio
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

from token_manager import (
    listar_archivos_token, obtener_nombre_cuenta,
    obtener_token, obtener_titulos_publicados, renovar_y_guardar_token
)
from categorizador import (
    obtener_categorias_raices_mlv, adivinar_categoria_y_raiz,
    coincide_con_categoria_elegida
)
from excel_parser import procesar_excel_heuristico, obtener_encabezados_excel, obtener_vista_previa_excel

load_dotenv()
app = FastAPI(title="ERP Mercado Libre - Dashboard Definitivo")

CARPETA_LOTE_IMAGENES = "lote_imagenes"
os.makedirs(CARPETA_LOTE_IMAGENES, exist_ok=True)

PROGRESO_ACTUAL = {
    "porcentaje": 0,
    "mensaje": "Iniciando...",
    "activo": False
}

CACHE_ATRIBUTOS_CAT = {}

BLOQUE_SUPERIOR = "SOMOS TIENDA FÍSICA, Empresa Mayorista Líder en el Mercado de la Computación Producto 100% de calidad"

BLOQUE_INFERIOR = """
.Por Favor Verifique la disponibilidad antes de ofertar
Por Favor Verifique la disponibilidad antes de ofertar
Por Favor Verifique la disponibilidad antes de ofertar
**************************************************************************************************
- Emitimos factura LEGAL
- Trabajamos con agentes de retención
- Enviamos a todo el País.
**************************************************************************************************
COMENTARIOS:
- Realice todas las preguntas necesariasAntes de ofertar.
- El equipo de ventas de está a tu disposición para responder tus consultas.
- Te invitamos a que solo ofertes cuando estés seguro de realizar la compra.
- La disponibilidad y precio del producto publicado solo se garantiza por un lapso de 24hrs luego de haber solicitado la compra.
- Si presentas algún inconveniente durante el proceso de compras estaremos a tu completa disposición para atenderte y solventar la situación. Deseamos que tu compra con nosotros siempre genere una calificación positiva.
****************************************************************************************************
HORARIO DE TRABAJO
****************************************************
De Lunes A Viernes
De 8:30am A 5:30pm
"""

def actualizar_progreso(porcentaje: int, mensaje: str):
    PROGRESO_ACTUAL["porcentaje"] = porcentaje
    PROGRESO_ACTUAL["mensaje"] = mensaje
    PROGRESO_ACTUAL["activo"] = True

def emparejar_imagen_local(modelo, sku, titulo):
    if not os.path.exists(CARPETA_LOTE_IMAGENES):
        return None
    archivos = os.listdir(CARPETA_LOTE_IMAGENES)
    if not archivos:
        return None

    for val in [str(sku).strip(), str(modelo).strip()]:
        if not val or val.lower() in ["nan", "universal", "generico", ""]:
            continue
        nombre_exacto = re.sub(r'[\\/*?:"<>|]', '', val).upper()
        for ext in [".JPG", ".JPEG", ".PNG", ".WEBP"]:
            archivo_esperado = nombre_exacto + ext
            for arc in archivos:
                if arc.upper() == archivo_esperado:
                    ruta_completa = os.path.join(CARPETA_LOTE_IMAGENES, arc)
                    try:
                        with open(ruta_completa, "rb") as f:
                            data = base64.b64encode(f.read()).decode("utf-8")
                            mime = "image/jpeg" if ext in [".JPG", ".JPEG"] else f"image/{ext[1:].lower()}"
                            return f"data:{mime};base64,{data}"
                    except Exception as e:
                        print(f"Error cargando foto local exacta {arc}: {e}")

    def limpiar_texto(t):
        return re.sub(r'[\s\-_\.]+', '', str(t)).lower()

    m_limpio = limpiar_texto(modelo)
    s_limpio = limpiar_texto(sku)

    for arc in archivos:
        nombre_base = limpiar_texto(arc.rsplit(".", 1)[0])
        if (m_limpio and len(m_limpio) > 2 and (m_limpio == nombre_base or m_limpio in nombre_base)) or \
           (s_limpio and len(s_limpio) > 2 and (s_limpio == nombre_base or s_limpio in nombre_base)):
            ruta_completa = os.path.join(CARPETA_LOTE_IMAGENES, arc)
            try:
                with open(ruta_completa, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                    ext = arc.rsplit(".", 1)[-1].lower()
                    mime = "image/jpeg" if ext in ["jpg", "jpeg"] else f"image/{ext}"
                    return f"data:{mime};base64,{data}"
            except Exception as e:
                print(f"Error cargando foto local flexible {arc}: {e}")
    return None

def subir_foto_a_ml(base64_data, token):
    try:
        header, encoded = base64_data.split(",", 1)
        file_ext = header.split(";")[0].split("/")[1]
        image_bytes = base64.b64decode(encoded)

        url = "https://api.mercadolibre.com/pictures"
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": (f"foto.{file_ext}", image_bytes, f"image/{file_ext}")}
        
        res = requests.post(url, headers=headers, files=files, timeout=10)
        if res.status_code == 201:
            return res.json().get("id") 
    except Exception as e:
        print(f"Error procesando imagen base64: {e}")
    return None

def construir_atributos_dinamicos_dict(prod, attr_adicionales, headers):
    lista = [
        {"id": "BRAND", "value_name": prod.get("Marca", "Generico")},
        {"id": "MODEL", "value_name": prod.get("Modelo", "Universal")}
    ]

    sku = str(prod.get("SKU", "")).strip()
    if sku and sku.lower() != "nan":
        lista.append({"id": "SELLER_SKU", "value_name": sku})
        lista.append({"id": "PART_NUMBER", "value_name": sku})

    gtin_val = str(prod.get("GTIN", "OMITIR")).strip()
    if gtin_val != "OMITIR" and gtin_val and gtin_val.lower() != "nan":
        gtin_solo_numeros = re.sub(r'\D', '', gtin_val)
        if len(gtin_solo_numeros) >= 8:
            lista.append({"id": "GTIN", "value_name": gtin_solo_numeros})

    PROHIBIDOS = {"BRAND", "MODEL", "SELLER_SKU", "PART_NUMBER", "GTIN", "ITEM_CONDITION", "HAS_COMPATIBILITIES"}
    if attr_adicionales and isinstance(attr_adicionales, dict):
        for k_id, v_val in attr_adicionales.items():
            if k_id not in PROHIBIDOS and str(v_val).strip() != "":
                lista.append({"id": k_id, "value_name": str(v_val).strip()})

    return lista

HTML_INTERFACE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ERP Mercado Libre - Dashboard Definitivo</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #f8fafc; margin: 0; display: flex; min-height: 100vh; color: #1e293b; }
        
        .sidebar { width: 260px; background: linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%); color: white; transition: width 0.3s; display: flex; flex-direction: column; flex-shrink: 0; border-right: 1px solid #312e81; }
        .sidebar.collapsed { width: 65px; }
        .sidebar-header { padding: 22px 15px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .logo-text { font-weight: 800; font-size: 16px; white-space: nowrap; overflow: hidden; color: #38bdf8; text-shadow: 0 0 10px rgba(56,189,248,0.3); }
        .sidebar.collapsed .logo-text { display: none; }
        .toggle-btn { background: rgba(255,255,255,0.1); color: white; border: none; padding: 6px 10px; border-radius: 6px; cursor: pointer; transition: 0.2s; }
        .toggle-btn:hover { background: rgba(255,255,255,0.2); }
        
        .nav-menu { list-style: none; padding: 15px 0; margin: 0; }
        .nav-item { padding: 15px 20px; display: flex; align-items: center; gap: 14px; cursor: pointer; transition: 0.2s; color: #cbd5e1; font-size: 14px; font-weight: 600; border-left: 4px solid transparent; }
        .nav-item:hover { background: rgba(255,255,255,0.05); color: #fff; }
        .nav-item.active { background: rgba(56,189,248,0.15); color: #38bdf8; border-left-color: #38bdf8; }
        .sidebar.collapsed .nav-text { display: none; }
        
        .main-content { flex-grow: 1; padding: 30px; overflow-x: auto; }
        .section-view { display: none; }
        .section-view.active { display: block; }
        .container { background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); border: 1px solid #e2e8f0; }
        h1 { color: #0f172a; margin-top: 0; font-size: 26px; font-weight: 800; }
        .subtitle { color: #475569; font-size: 14px; margin-bottom: 25px; }
        
        .steps-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 25px; }
        .step-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; transition: 0.2s; position: relative; overflow: hidden; }
        .step-card:hover { border-color: #0284c7; box-shadow: 0 4px 12px rgba(2,132,199,0.08); }
        .step-num { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; color: #0284c7; margin-bottom: 6px; display: block; }
        .step-card label { font-weight: 700; font-size: 13px; color: #1e293b; display: block; margin-bottom: 8px; }
        
        input[type="file"], select, input[type="number"], input[type="text"] { width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; background: white; font-size: 13px; color: #0f172a; transition: 0.2s; }
        input:focus, select:focus { border-color: #0284c7; outline: none; box-shadow: 0 0 0 3px rgba(2,132,199,0.15); }
        
        button { background: #0284c7; color: white; border: none; padding: 12px 18px; font-weight: 700; border-radius: 8px; cursor: pointer; transition: 0.2s; font-size: 14px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; }
        button:hover { background: #0369a1; transform: translateY(-1px); }
        button:active { transform: translateY(0); }
        
        .mapping-bar { display: none; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border: 1px solid #bae6fd; padding: 20px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(2,132,199,0.05); }
        .mapping-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-top: 15px; }
        .mapping-grid label { font-size: 12px; font-weight: 700; color: #0369a1; margin-bottom: 4px; display: block; }
        
        .excel-preview-box { margin-top: 18px; background: #fff; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; }
        .excel-preview-header { background: #f1f5f9; padding: 10px 15px; font-size: 13px; font-weight: 700; color: #0f172a; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; }
        .excel-preview-nav { display: flex; gap: 8px; align-items: center; }
        .excel-nav-btn { background: #0284c7; color: white; border: none; padding: 5px 12px; border-radius: 6px; font-size: 11px; cursor: pointer; font-weight: 700; }
        .excel-nav-btn:disabled { background: #94a3b8; cursor: default; }
        .excel-table-preview { width: 100%; border-collapse: collapse; font-size: 11px; }
        .excel-table-preview th, .excel-table-preview td { border: 1px solid #e2e8f0; padding: 6px 10px; text-align: left; }
        .excel-table-preview th { background: #eff6ff; color: #1d4ed8; font-weight: 700; }
        
        .loader-container { display: none; text-align: center; padding: 50px; background: #f8fafc; border-radius: 16px; margin: 20px 0; border: 2px dashed #38bdf8; }
        .spinner-wrapper { position: relative; width: 80px; height: 80px; margin: 0 auto 15px auto; }
        .spinner-circle { box-sizing: border-box; width: 100%; height: 100%; border: 8px solid #e2e8f0; border-top-color: #0284c7; border-radius: 50%; animation: spin 1s linear infinite; }
        .spinner-percentage { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 16px; color: #0284c7; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .bulk-toolbar { display: flex; flex-wrap: wrap; gap: 12px; background: #f8fafc; padding: 16px; border-radius: 12px; margin-bottom: 20px; align-items: center; border: 1px solid #e2e8f0; }
        .bulk-select { padding: 8px 12px; font-size: 13px; border-radius: 6px; border: 1px solid #cbd5e1; background: white; }
        .bulk-btn { background: #7e22ce; color: white; border: none; padding: 8px 16px; font-size: 12px; border-radius: 6px; cursor: pointer; font-weight: 700; }
        .bulk-btn:hover { background: #6b21a8; }
        
        table.data-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 12px; margin-top: 10px; border-radius: 10px; overflow: hidden; border: 1px solid #e2e8f0; }
        table.data-table th, table.data-table td { padding: 12px 10px; vertical-align: top; border-bottom: 1px solid #e2e8f0; }
        table.data-table th { background: #0f172a; color: white; font-weight: 700; text-align: left; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; }
        table.data-table tbody tr:nth-child(even) { background: #f8fafc; }
        table.data-table tbody tr:hover { background: #f1f5f9; }
        
        .account-badge { display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; margin-top: 6px; margin-right: 4px; }
        .badge-libre { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
        .badge-existe { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
        
        .cat-tag { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; background: #e0f2fe; color: #0369a1; margin-top: 4px; }
        .desc-tag { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; background: #dcfce7; color: #15803d; margin-top: 4px; }
        .attr-summary { font-size: 11px; color: #334155; background: #f1f5f9; padding: 8px 10px; border-radius: 6px; margin-top: 6px; border-left: 3px solid #0284c7; font-weight: 600; }
        
        .log-box { background: #0f172a; color: #4ade80; padding: 20px; height: 260px; overflow-y: auto; font-family: 'Consolas', monospace; border-radius: 10px; margin-top: 25px; white-space: pre-wrap; font-size: 12px; line-height: 1.5; border: 1px solid #334155; }
        
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15,23,42,0.75); z-index: 2000; justify-content: center; align-items: center; backdrop-filter: blur(4px); }
        .modal-box { background: white; padding: 32px; border-radius: 16px; width: 680px; max-width: 95%; box-shadow: 0 20px 50px rgba(0,0,0,0.3); border: 1px solid #e2e8f0; }
        .modal-box h3 { margin-top: 0; color: #0f172a; border-bottom: 2px solid #0284c7; padding-bottom: 12px; font-size: 18px; font-weight: 800; }
        
        .modal-grid { display: flex; flex-direction: column; gap: 14px; margin-top: 15px; max-height: 420px; overflow-y: auto; padding-right: 8px; }
        .modal-field { display: flex; flex-direction: column; gap: 6px; }
        .modal-field label { font-size: 12px; font-weight: 700; color: #334155; }
        
        .category-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; max-height: 380px; overflow-y: auto; margin: 15px 0; padding-right: 5px; }
        .category-item { border: 1px solid #cbd5e1; padding: 14px; border-radius: 10px; cursor: pointer; transition: 0.2s; font-size: 13px; font-weight: 700; color: #334155; display: flex; align-items: center; gap: 10px; background: #f8fafc; }
        .category-item:hover { background: #eff6ff; border-color: #0284c7; color: #0284c7; }
        .category-item.selected { background: #e0f2fe; border-color: #0284c7; color: #0369a1; box-shadow: 0 0 0 2px #0284c7; }
        
        .photo-manager { border: 2px dashed #94a3b8; padding: 12px; text-align: center; border-radius: 8px; background: #f8fafc; cursor: pointer; position: relative; transition: 0.2s; font-weight: 600; color: #475569; }
        .photo-manager:hover { border-color: #0284c7; background: #eff6ff; color: #0284c7; }
        .photo-manager input[type="file"] { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
        .preview-container { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; justify-content: center; }
        .thumb-wrap { position: relative; display: inline-block; }
        .thumb-wrap img { width: 48px; height: 48px; object-fit: cover; border-radius: 6px; border: 1px solid #cbd5e1; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .del-photo-btn { position: absolute; top: -6px; right: -6px; background: #ef4444; color: white; border: none; border-radius: 50%; width: 20px; height: 20px; font-size: 11px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: bold; }
        
        .gallery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 16px; margin-top: 20px; }
        .gallery-item { background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.03); }
        .gallery-item img { width: 100%; height: 110px; object-fit: contain; border-radius: 6px; background: #f8fafc; }
        .gallery-item span { display: block; font-size: 11px; font-weight: 700; color: #334155; margin-top: 8px; word-break: break-all; }
    </style>
</head>
<body>
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <span class="logo-text">🚀 MLV ERP SYSTEM</span>
            <button class="toggle-btn" onclick="toggleSidebar()">☰</button>
        </div>
        <ul class="nav-menu">
            <li class="nav-item active" onclick="mostrarSeccion('tab-maestro', this)">
                <span>📦</span> <span class="nav-text">Sincronización & Lotes</span>
            </li>
            <li class="nav-item" onclick="mostrarSeccion('tab-tokens', this)">
                <span>🔑</span> <span class="nav-text">Cuentas & Tokens</span>
            </li>
            <li class="nav-item" onclick="mostrarSeccion('tab-csv', this)">
                <span>📄</span> <span class="nav-text">Descripciones CSV</span>
            </li>
            <li class="nav-item" onclick="mostrarSeccion('tab-galeria', this); cargarGaleriaLocal();">
                <span>🖼️</span> <span class="nav-text">Galería Local (lote_imagenes)</span>
            </li>
        </ul>
    </div>

    <div class="main-content">
        <!-- PESTAÑA 1: MAESTRO -->
        <div id="tab-maestro" class="section-view active">
            <div class="container">
                <h1>📦 Panel Maestro de Sincronización y Publicación</h1>
                <div class="subtitle">Selector Oficial MLV, Mapeo Manual Visual y Filtro Anti-Basura Estricto</div>
                
                <div class="steps-grid">
                    <div class="step-card">
                        <span class="step-num">Paso 1</span>
                        <label>Cuenta / Perfil ML:</label>
                        <select id="cuenta-select"></select>
                    </div>
                    <div class="step-card">
                        <span class="step-num">Paso 2</span>
                        <label>Inventario (.xlsx / .csv):</label>
                        <input type="file" id="file-db" accept=".xlsx, .csv" onchange="detectarHojasYVistaPrevia(this)">
                    </div>
                    <div class="step-card">
                        <span class="step-num">Paso 3</span>
                        <label>Hoja a Escanear:</label>
                        <select id="hoja-select" onchange="cambiarHojaSeleccionada()">
                            <option value="TODAS">📚 Todo el Libro (Todas las Hojas)</option>
                        </select>
                    </div>
                    <div class="step-card">
                        <span class="step-num">Paso 4</span>
                        <label>Rango de filas:</label>
                        <div style="display: flex; gap: 8px;">
                            <input type="number" id="rango-inicio" value="1" placeholder="Desde" style="width: 50%;">
                            <input type="number" id="rango-fin" value="100" placeholder="Hasta" style="width: 50%;">
                        </div>
                    </div>
                    <div class="step-card">
                        <span class="step-num">Paso 5</span>
                        <label>Ocultar Publicados:</label>
                        <div style="display: flex; align-items: center; gap: 8px; margin-top: 10px;">
                            <input type="checkbox" id="filtar-duplicados" checked style="width: auto;">
                            <span style="font-size: 12px; font-weight: 600; color: #475569;">Solo mostrar Libres</span>
                        </div>
                    </div>
                </div>

                <div style="margin-bottom: 25px;">
                    <button onclick="abrirModalCategorias()" style="width: 100%; padding: 14px; font-size: 15px; background: #0284c7;">
                        🔍 Sincronizar y Elegir Categoría Oficial ML
                    </button>
                </div>

                <!-- MAPEO MANUAL Y VISTA PREVIA VISUAL DEL EXCEL -->
                <div id="mapping-bar" class="mapping-bar">
                    <h4 style="margin: 0 0 5px 0; color: #0369a1; font-size: 15px; font-weight: 800;">🎯 Mapeo Manual de Columnas y Vista Previa en Vivo:</h4>
                    <span style="font-size: 13px; color: #0284c7; font-weight: 600;">Selecciona las columnas de tu Excel o deja "-- Automático --" para que la heurística las detecte. Verifica en la tabla inferior qué contiene cada celda:</span>
                    <div class="mapping-grid">
                        <div><label>Título:</label><select id="map-tit"><option value="">-- Automático --</option></select></div>
                        <div><label>SKU / Código:</label><select id="map-sku"><option value="">-- Automático --</option></select></div>
                        <div><label>Modelo:</label><select id="map-mod"><option value="">-- Automático --</option></select></div>
                        <div><label>Precio:</label><select id="map-pre"><option value="">-- Automático --</option></select></div>
                        <div><label>Stock:</label><select id="map-stk"><option value="">-- Automático --</option></select></div>
                    </div>

                    <div id="excel-preview-box" class="excel-preview-box">
                        <div class="excel-preview-header">
                            <span id="excel-preview-title">📊 Vista Previa del Excel</span>
                            <div id="excel-preview-nav" class="excel-preview-nav" style="display:none;">
                                <button type="button" class="excel-nav-btn" onclick="cambiarHojaPreview(-1)">⬅️ Hoja Anterior</button>
                                <span id="excel-preview-counter" style="color:#0f172a; font-weight:bold;">Hoja 1 de 1</span>
                                <button type="button" class="excel-nav-btn" onclick="cambiarHojaPreview(1)">Siguiente Hoja ➡️</button>
                            </div>
                        </div>
                        <div style="overflow-x: auto; max-height: 250px;">
                            <table class="excel-table-preview" id="excel-preview-table">
                                <thead id="excel-preview-thead"></thead>
                                <tbody id="excel-preview-tbody"></tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div id="loader-zona" class="loader-container">
                    <div class="spinner-wrapper">
                        <div class="spinner-circle"></div>
                        <div id="spinner-percentage" class="spinner-percentage">0%</div>
                    </div>
                    <div id="loader-mensaje" style="font-weight:800; color:#0f172a; font-size:16px;">Analizando inventario...</div>
                </div>

                <div id="tabla-container" style="display: none;">
                    <div class="bulk-toolbar">
                        <span style="font-weight: 800; color: #0f172a;">⚡ ACCIONES MASIVAS:</span>
                        <select id="bulk-exposicion" class="bulk-select">
                            <option value="bronze">Exposición: Bronce / Estándar</option>
                            <option value="gold_special">Exposición: Clásica</option>
                            <option value="gold_pro">Exposición: Premium</option>
                        </select>
                        <button class="bulk-btn" onclick="aplicarExposicionMasiva()">Aplicar Exposición</button>
                        
                        <select id="bulk-envio" class="bulk-select" style="margin-left:8px;">
                            <option value="me2_free">🟢 Mercado Envíos - Envío Gratis</option>
                            <option value="custom_free">🟢 Envío Gratis Nacional (Custom)</option>
                            <option value="me2_buyer">🔵 Mercado Envíos - Cobro en Destino</option>
                            <option value="not_specified">⚪ Acordar con el Vendedor</option>
                        </select>
                        <button class="bulk-btn" onclick="aplicarEnvioMasivo()">Aplicar Envío</button>

                        <button class="bulk-btn" onclick="abrirModalMasivo()" style="margin-left:auto; background:#7e22ce;">⚡ Llenar Características Lote</button>
                    </div>

                    <table class="data-table" id="data-table">
                        <thead>
                            <tr>
                                <th style="width: 30px;"><input type="checkbox" checked onclick="toggleAll(this)"></th>
                                <th style="width: 24%;">Título, Categoría & Estado por Cuenta</th>
                                <th style="width: 8%;">Precio $</th>
                                <th style="width: 6%;">Stock</th>
                                <th style="width: 16%;">Exposición & Envío</th>
                                <th style="width: 26%;">Ficha Técnica (Marca / Modelo / SKU / GTIN)</th>
                                <th style="width: 20%;">Gestor de Fotos Local</th>
                            </tr>
                        </thead>
                        <tbody id="tabla-body"></tbody>
                    </table>
                    <button onclick="ejecutarPublicacion()" style="background: #16a34a; width: 100%; margin-top: 25px; padding: 16px; font-size: 16px; font-weight:800;">
                        🚀 Confirmar y Publicar Lote (Inteligente: Salta lo repetido)
                    </button>
                </div>

                <div id="resultados" class="log-box">Esperando sincronización de inventario...</div>
            </div>
        </div>

        <!-- PESTAÑA 2: TOKENS -->
        <div id="tab-tokens" class="section-view">
            <div class="container">
                <h1>🔑 Estado y Diagnóstico en Vivo de Cuentas</h1>
                <div class="subtitle">Prueba la conexión y la renovación automática de tokens sin salir de tu panel</div>
                <button onclick="verificarTokens()" style="padding: 12px 25px; font-size: 15px;">🔄 Probar Conexión y Renovar Tokens Ahora</button>
                <div id="log-tokens" class="log-box" style="height: 350px;">Presiona el botón para verificar la salud de los tokens...</div>
            </div>
        </div>

        <!-- PESTAÑA 3: CSV DESCRIPCIONES -->
        <div id="tab-csv" class="section-view">
            <div class="container">
                <h1>📄 Asignación Masiva de Descripciones (.CSV)</h1>
                <div class="subtitle">Carga un archivo CSV que relacione tu SKU con una descripción personalizada para el lote</div>
                <div style="background: #f8fafc; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px;">
                    <p style="font-weight:bold; margin-top:0;">Formato requerido en el archivo CSV:</p>
                    <code style="background:#e2e8f0; padding:5px 10px; border-radius:4px; display:block; margin-bottom:10px;">SKU,Descripcion Personalizada</code>
                    <code style="background:#e2e8f0; padding:5px 10px; border-radius:4px; display:block;">MXP-GI11C,Botella de tinta cian original alta resolución para cartuchos...</code>
                </div>
                <label style="background: #16a34a; color: white; padding: 12px 20px; border-radius: 8px; cursor: pointer; font-weight: 700; display: inline-block;">
                    <span>📂 Seleccionar Archivo CSV de Descripciones</span>
                    <input type="file" accept=".csv" style="display:none;" onchange="cargarDescripcionesCSV(this)">
                </label>
                <p id="csv-status" style="font-weight:700; color:#16a34a; margin-top:15px;"></p>
            </div>
        </div>

        <!-- PESTAÑA 4: GALERÍA LOCAL DE IMÁGENES -->
        <div id="tab-galeria" class="section-view">
            <div class="container">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h1 style="margin:0;">🖼️ Galería Local de Imágenes (Carpeta: lote_imagenes)</h1>
                        <div class="subtitle" style="margin-bottom:0;">Verifica visualmente en tiempo real todas las fotos que el sistema tiene listas para emparejar</div>
                    </div>
                    <button onclick="cargarGaleriaLocal()" style="background:#0284c7; padding:10px 18px;">🔄 Actualizar Galería</button>
                </div>
                <div id="galeria-contenedor" class="gallery-grid"></div>
            </div>
        </div>
    </div>

    <!-- MODAL EMERGENTE DE CATEGORÍAS MLV -->
    <div id="modal-categoria-mlv" class="modal-overlay">
        <div class="modal-box">
            <h3>🏷️ Selecciona una Categoría Oficial de Mercado Libre</h3>
            <p style="font-size:13px; color:#475569; margin-bottom:10px;">
                Filtra tu rango de filas por un rubro oficial para mayor precisión, o elige cargar absolutamente todo el inventario:
            </p>
            <div id="lista-categorias-ml" class="category-grid"></div>
            <input type="hidden" id="cat-seleccionada-id" value="TODAS">
            <div style="display:flex; justify-content:flex-end; gap:12px; margin-top:20px; border-top:1px solid #e2e8f0; padding-top:15px;">
                <button onclick="cerrarModalCategorias()" style="background:#64748b;">Cancelar</button>
                <button onclick="confirmarYCargarInventario()" style="background:#16a34a; padding:10px 20px;">
                    🚀 Confirmar y Cargar Tabla de Publicación
                </button>
            </div>
        </div>
    </div>

    <!-- MODAL MASIVO -->
    <div id="modal-bulk-atributos" class="modal-overlay">
        <div class="modal-box">
            <h3 style="color:#7e22ce;">⚡ Llenado Masivo de Características</h3>
            <p style="font-size:12px; color:#475569;">Los atributos que llenes aquí se aplicarán a todos los artículos marcados con check.</p>
            <div class="modal-grid">
                <div class="modal-field"><label>Marca (Común para el lote):</label><input type="text" id="bm-mar" placeholder="Ej: MAXIPRINT"></div>
                <div class="modal-field"><label>Color (Común para el lote):</label><input type="text" id="bm-color" placeholder="Ej: Negro / Cian"></div>
                <div class="modal-field"><label>Compatibilidad / Rendimiento:</label><input type="text" id="bm-compat" placeholder="Ej: Canon G1100"></div>
                <div class="modal-field"><label>Material / Especificación:</label><input type="text" id="bm-mat" placeholder="Ej: Original"></div>
            </div>
            <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:20px;">
                <button onclick="cerrarModalMasivo()" style="background:#64748b;">Cancelar</button>
                <button onclick="aplicarAtributosMasivos()" style="background:#7e22ce;">🚀 Aplicar a Todo el Lote</button>
            </div>
        </div>
    </div>

    <!-- MODAL INDIVIDUAL DINÁMICO (CON LISTAS SUGERIDAS DE MLV) -->
    <div id="modal-atributos" class="modal-overlay">
        <div class="modal-box">
            <h3>🛠️ Editar Características Oficiales de Mercado Libre</h3>
            <input type="hidden" id="modal-idx">
            <div id="modal-attr-dinamicos" class="modal-grid">
                <div style="text-align:center; padding:20px; color:#64748b;">⏳ Cargando ficha técnica de Mercado Libre...</div>
            </div>
            <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:20px;">
                <button onclick="cerrarModal()" style="background:#64748b;">Cancelar</button>
                <button onclick="guardarAtributosModal()" style="background:#0284c7;">💾 Guardar Ficha Técnica</button>
            </div>
        </div>
    </div>

    <script>
        const imagenesPorFila = {};
        const atributosPorFila = {};
        const atributosAdicionalesPorFila = {};
        const descripcionesCSV = {};
        let intervaloProgreso = null;
        
        let datosVistaPrevia = [];
        let indiceHojaPreview = 0;

        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('collapsed');
        }

        function mostrarSeccion(idSeccion, el) {
            document.querySelectorAll('.section-view').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            document.getElementById(idSeccion).classList.add('active');
            if (el) el.classList.add('active');
        }

        window.onload = async () => {
            const res = await fetch('/cuentas');
            const cuentas = await res.json();
            const select = document.getElementById('cuenta-select');
            select.innerHTML = "";
            cuentas.forEach(c => {
                select.innerHTML += `<option value="${c.archivo}">${c.nombre} (${c.archivo})</option>`;
            });
            if (cuentas.length > 1) {
                select.innerHTML += `<option value="TODAS" style="font-weight:bold; color:#0369a1;">🚀 PUBLICAR EN TODAS (Inteligente: Salta donde ya exista)</option>`;
            }
        };

        // DETECCIÓN DE HOJAS, COLUMNAS Y VISTA PREVIA VISUAL INTELIGENTE
        async function detectarHojasYVistaPrevia(inputElement) {
            const file = inputElement.files[0];
            const selectHoja = document.getElementById('hoja-select');
            if (!file) return;

            selectHoja.innerHTML = '<option value="TODAS">⏳ Detectando pestañas...</option>';
            const formData = new FormData();
            formData.append('file', file);

            try {
                const res = await fetch('/api/vista-previa-excel', { method: 'POST', body: formData });
                const data = await res.json();
                
                datosVistaPrevia = data.vistas || [];
                selectHoja.innerHTML = '<option value="TODAS">📚 Todo el Libro (Todas las Hojas)</option>';
                datosVistaPrevia.forEach(item => {
                    selectHoja.innerHTML += `<option value="${item.nombre}">📄 ${item.nombre}</option>`;
                });
                
                cambiarHojaSeleccionada();
            } catch(e) {
                selectHoja.innerHTML = '<option value="TODAS">📚 Todo el Libro (Todas las Hojas)</option>';
            }
        }

        function cambiarHojaSeleccionada() {
            const val = document.getElementById('hoja-select').value;
            if (val === "TODAS") {
                indiceHojaPreview = 0;
            } else {
                const idx = datosVistaPrevia.findIndex(item => item.nombre === val);
                indiceHojaPreview = (idx >= 0) ? idx : 0;
            }
            renderizarVistaPreviaExcel(val === "TODAS");
            poblarSelectoresMapeo(indiceHojaPreview);
        }

        function cambiarHojaPreview(delta) {
            const total = datosVistaPrevia.length;
            if (total === 0) return;
            indiceHojaPreview = (indiceHojaPreview + delta + total) % total;
            renderizarVistaPreviaExcel(true);
            poblarSelectoresMapeo(indiceHojaPreview);
        }

        function renderizarVistaPreviaExcel(esTodas) {
            if (!datosVistaPrevia.length) return;
            const vista = datosVistaPrevia[indiceHojaPreview];
            const thead = document.getElementById('excel-preview-thead');
            const tbody = document.getElementById('excel-preview-tbody');
            const title = document.getElementById('excel-preview-title');
            const nav = document.getElementById('excel-preview-nav');
            const count = document.getElementById('excel-preview-counter');
            
            title.innerHTML = `📊 Vista Previa del Excel — <b>Hoja: ${vista.nombre}</b>`;
            if (esTodas && datosVistaPrevia.length > 1) {
                nav.style.display = 'flex';
                count.innerText = `Hoja ${indiceHojaPreview + 1} de ${datosVistaPrevia.length}`;
            } else {
                nav.style.display = 'none';
            }

            thead.innerHTML = "";
            tbody.innerHTML = "";
            if (!vista.filas || !vista.filas.length) return;

            const f0 = vista.filas[0];
            let trH = "<tr><th>#</th>";
            f0.forEach((cell, i) => {
                trH += `<th>Col ${i+1}: ${cell}</th>`;
            });
            trH += "</tr>";
            thead.innerHTML = trH;

            for (let r = 1; r < Math.min(10, vista.filas.length); r++) {
                const fila = vista.filas[r];
                let trB = `<tr><td><b>Fila ${r}</b></td>`;
                f0.forEach((_, cIdx) => {
                    trB += `<td>${fila[cIdx] || ""}</td>`;
                });
                trB += "</tr>";
                tbody.innerHTML += trB;
            }

            document.getElementById('mapping-bar').style.display = 'block';
        }

        // ESCÁNER QUE BUSCA LA FILA REAL DE ENCABEZADOS Y MUESTRA TODAS LAS COLUMNAS
        function poblarSelectoresMapeo(idxHoja) {
            if (!datosVistaPrevia[idxHoja] || !datosVistaPrevia[idxHoja].filas.length) return;
            const filas = datosVistaPrevia[idxHoja].filas;
            
            const palabrasClave = ["codigo", "código", "sku", "producto", "descripcion", "descripción", "precio", "marca", "categoria", "nombre", "stock", "modelo", "linea", "garantia", "pvp", "$"];
            
            let mejorFila = 0;
            let maxCoincidencias = -1;
            
            for (let r = 0; r < Math.min(10, filas.length); r++) {
                let coincidencias = 0;
                let celdasLlenas = 0;
                filas[r].forEach(celda => {
                    const txt = String(celda || "").toLowerCase().trim();
                    if (txt && txt !== "nan" && txt !== "undefined") {
                        celdasLlenas++;
                        if (palabrasClave.some(p => txt.includes(p))) {
                            coincidencias += 3;
                        }
                    }
                });
                const puntuacion = coincidencias + (celdasLlenas * 0.5);
                if (puntuacion > maxCoincidencias && celdasLlenas >= 2) {
                    maxCoincidencias = puntuacion;
                    mejorFila = r;
                }
            }

            const fPpal = filas[mejorFila] || [];
            const fSig = (mejorFila + 1 < filas.length) ? (filas[mejorFila + 1] || []) : [];
            const totalCols = Math.max(fPpal.length, fSig.length);

            const selects = ['map-tit', 'map-sku', 'map-mod', 'map-pre', 'map-stk'];
            
            selects.forEach(id => {
                const el = document.getElementById(id);
                if (!el) return;
                el.innerHTML = '<option value="">-- Automático --</option>';
                for (let c = 0; c < totalCols; c++) {
                    let nom1 = String(fPpal[c] || "").trim();
                    let nom2 = String(fSig[c] || "").trim();
                    if (nom1.toLowerCase() === "nan" || nom1.toLowerCase() === "undefined") nom1 = "";
                    if (nom2.toLowerCase() === "nan" || nom2.toLowerCase() === "undefined") nom2 = "";

                    let etiquetaCol = "";
                    let valorCol = "";
                    if (nom1 && nom2 && palabrasClave.some(p => nom2.toLowerCase().includes(p))) {
                        valorCol = `${nom1} ${nom2}`;
                        etiquetaCol = `Col ${c + 1}: ${nom1} ${nom2}`;
                    } else if (nom1) {
                        valorCol = nom1;
                        etiquetaCol = `Col ${c + 1}: ${nom1}`;
                    } else if (nom2) {
                        valorCol = nom2;
                        etiquetaCol = `Col ${c + 1}: ${nom2}`;
                    } else {
                        valorCol = `Col_${c + 1}`;
                        etiquetaCol = `Col ${c + 1} (Sin nombre)`;
                    }

                    el.innerHTML += `<option value="${valorCol}">${etiquetaCol}</option>`;
                }
            });
        }

        async function verificarTokens() {
            const consolaMain = document.getElementById('resultados');
            const consolaTokens = document.getElementById('log-tokens');
            if (consolaMain) consolaMain.innerText = "⏳ Probando conexión y vigencia de tokens en vivo con Mercado Libre...";
            if (consolaTokens) consolaTokens.innerText = "⏳ Probando conexión y vigencia de tokens en vivo con Mercado Libre...";
            try {
                const res = await fetch('/verificar-tokens');
                const data = await res.json();
                const textoLog = data.logs.join('\\n');
                if (consolaMain) consolaMain.innerText = textoLog;
                if (consolaTokens) consolaTokens.innerText = textoLog;
            } catch(e) {
                const errorMsg = "❌ Error al verificar tokens: " + e;
                if (consolaMain) consolaMain.innerText = errorMsg;
                if (consolaTokens) consolaTokens.innerText = errorMsg;
            }
        }

        function iniciarMonitoreoProgreso() {
            document.getElementById('loader-zona').style.display = 'block';
            if (intervaloProgreso) clearInterval(intervaloProgreso);
            
            intervaloProgreso = setInterval(async () => {
                try {
                    const res = await fetch('/estado-progreso');
                    const info = await res.json();
                    document.getElementById('spinner-percentage').innerText = info.porcentaje + "%";
                    document.getElementById('loader-mensaje').innerText = info.mensaje;

                    if (!info.activo && info.porcentaje >= 100) {
                        clearInterval(intervaloProgreso);
                        setTimeout(() => { document.getElementById('loader-zona').style.display = 'none'; }, 800);
                    }
                } catch(e) {}
            }, 250);
        }

        function cargarDescripcionesCSV(input) {
            const file = input.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function(e) {
                const text = e.target.result;
                const lineas = text.split('\\n');
                let matchCount = 0;

                for (let i = 1; i < lineas.length; i++) {
                    const l = lineas[i].split(',');
                    if (l.length >= 2) {
                        const clave = l[0].trim().toLowerCase();
                        const desc = l.slice(1).join(',').replace(/["']/g, '').trim();
                        if (clave && desc) descripcionesCSV[clave] = desc;
                    }
                }

                document.querySelectorAll('.prod-check').forEach(cb => {
                    const idx = cb.dataset.idx;
                    const skuVal = (document.getElementById('sku-'+idx).value || '').toLowerCase();
                    const titVal = (document.getElementById('tit-'+idx).value || '').toLowerCase();

                    if (descripcionesCSV[skuVal] || descripcionesCSV[titVal]) {
                        matchCount++;
                        document.getElementById('desc-tag-'+idx).innerText = "📄 Desc. CSV Asignada";
                    }
                });

                document.getElementById('csv-status').innerText = `✅ Se asignaron descripciones personalizadas a ${matchCount} artículos en memoria.`;
                alert(`✅ Archivo CSV procesado con éxito.`);
            };
            reader.readAsText(file);
        }

        function toggleGtin(idx) {
            const selectVal = document.getElementById('gtin-razon-'+idx).value;
            const inputField = document.getElementById('gtin-'+idx);
            inputField.style.display = (selectVal === 'CUSTOM') ? 'block' : 'none';
        }

        function abrirModalMasivo() {
            document.getElementById('modal-bulk-atributos').style.display = 'flex';
        }

        function cerrarModalMasivo() {
            document.getElementById('modal-bulk-atributos').style.display = 'none';
        }

        function aplicarAtributosMasivos() {
            const marVal = document.getElementById('bm-mar').value.trim();
            const colorVal = document.getElementById('bm-color').value.trim();
            const compatVal = document.getElementById('bm-compat').value.trim();
            const matVal = document.getElementById('bm-mat').value.trim();
            let count = 0;

            document.querySelectorAll('.prod-check:checked').forEach(cb => {
                const idx = cb.dataset.idx;
                if (marVal) {
                    atributosPorFila[idx].marca = marVal;
                    document.getElementById('mar-'+idx).value = marVal;
                }
                if (colorVal) atributosPorFila[idx].color = colorVal;
                if (compatVal) atributosPorFila[idx].compatibilidad = compatVal;
                if (matVal) atributosPorFila[idx].material = matVal;

                actualizarResumenAtributos(idx);
                count++;
            });

            cerrarModalMasivo();
            alert(`✅ Características aplicadas masivamente a ${count} artículos.`);
        }

        async function abrirModal(idx) {
            document.getElementById('modal-idx').value = idx;
            document.getElementById('modal-atributos').style.display = 'flex';
            
            const contenedor = document.getElementById('modal-attr-dinamicos');
            contenedor.innerHTML = '<div style="text-align:center; padding:20px; color:#0284c7; font-weight:bold;">⏳ Consultado atributos en vivo para esta categoría en Mercado Libre...</div>';
            
            const catId = document.getElementById('cat-'+idx).value;
            const attrBase = atributosPorFila[idx] || {};
            const attrAdic = atributosAdicionalesPorFila[idx] || {};

            try {
                const res = await fetch(`/api/atributos-categoria/${catId}`);
                const listaAttrML = await res.json();

                contenedor.innerHTML = "";

                contenedor.innerHTML += `
                    <div class="modal-field">
                        <label>Marca:</label>
                        <input type="text" id="m-mar" value="${attrBase.marca || ''}">
                    </div>
                    <div class="modal-field">
                        <label>Modelo:</label>
                        <input type="text" id="m-mod" value="${attrBase.modelo || ''}">
                    </div>
                `;

                listaAttrML.forEach(att => {
                    const vGuardado = attrAdic[att.id] || "";
                    let controlHTML = "";

                    if (att.values && att.values.length > 0) {
                        let optionsHTML = `<option value="">-- Elige una opción sugerida o escribe arriba --</option>`;
                        att.values.forEach(valML => {
                            const sel = (vGuardado.toLowerCase() === valML.name.toLowerCase()) ? "selected" : "";
                            optionsHTML += `<option value="${valML.name}" ${sel}>${valML.name}</option>`;
                        });

                        controlHTML = `
                            <div style="display:flex; gap:6px;">
                                <select id="m-attr-${att.id}" onchange="document.getElementById('m-txt-${att.id}').value = this.value;" style="flex:1;">
                                    ${optionsHTML}
                                </select>
                                <input type="text" id="m-txt-${att.id}" value="${vGuardado}" placeholder="O escribe aquí" style="flex:1;">
                            </div>
                        `;
                    } else {
                        controlHTML = `<input type="text" id="m-txt-${att.id}" value="${vGuardado}" placeholder="Ej: ${att.hint || 'Valor'}">`;
                    }

                    contenedor.innerHTML += `
                        <div class="modal-field">
                            <label>${att.name} <span style="font-weight:normal; color:#64748b; font-size:10px;">(${att.value_type})</span></label>
                            ${controlHTML}
                        </div>
                    `;
                });
            } catch(e) {
                contenedor.innerHTML = '<div style="color:red; padding:20px;">❌ Error conectando a los atributos oficiales de Mercado Libre.</div>';
            }
        }

        function cerrarModal() {
            document.getElementById('modal-atributos').style.display = 'none';
        }

        function guardarAtributosModal() {
            const idx = document.getElementById('modal-idx').value;
            
            atributosPorFila[idx].marca = document.getElementById('m-mar').value;
            atributosPorFila[idx].modelo = document.getElementById('m-mod').value;
            
            document.getElementById('mar-'+idx).value = atributosPorFila[idx].marca;
            document.getElementById('mod-'+idx).value = atributosPorFila[idx].modelo;

            if (!atributosAdicionalesPorFila[idx]) atributosAdicionalesPorFila[idx] = {};
            
            const contenedor = document.getElementById('modal-attr-dinamicos');
            contenedor.querySelectorAll('input[id^="m-txt-"]').forEach(inp => {
                const idAttrML = inp.id.replace('m-txt-', '');
                if (inp.value.trim() !== "") {
                    atributosAdicionalesPorFila[idx][idAttrML] = inp.value.trim();
                } else {
                    delete atributosAdicionalesPorFila[idx][idAttrML];
                }
            });

            actualizarResumenAtributos(idx);
            cerrarModal();
        }

        function actualizarResumenAtributos(idx) {
            const attr = atributosPorFila[idx] || {};
            const adic = atributosAdicionalesPorFila[idx] || {};
            let info = `🏷️ ${attr.marca || 'Generico'} / ${attr.modelo || 'Universal'}`;
            const totalDinamicos = Object.keys(adic).length;
            if (totalDinamicos > 0) {
                info += ` | ⚡ +${totalDinamicos} características oficiales MLV`;
            }
            document.getElementById('resumen-attr-'+idx).innerText = info;
        }

        function procesarArchivos(inputElement, idx) {
            const files = inputElement.files;
            if (!imagenesPorFila[idx]) imagenesPorFila[idx] = [];

            for (let file of files) {
                if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
                    alert(`El archivo ${file.name} no es válido. Solo JPG, PNG o WEBP.`);
                    continue;
                }
                const reader = new FileReader();
                reader.onload = (e) => {
                    imagenesPorFila[idx].push(e.target.result);
                    renderizarGaleriaFila(idx);
                };
                reader.readAsDataURL(file);
            }
        }

        function renderizarGaleriaFila(idx) {
            const previewArea = document.getElementById(`prev-${idx}`);
            previewArea.innerHTML = "";
            (imagenesPorFila[idx] || []).forEach((b64, pos) => {
                previewArea.innerHTML += `
                    <div class="thumb-wrap">
                        <img src="${b64}">
                        <button class="del-photo-btn" onclick="eliminarFotoFila(${idx}, ${pos})" title="Eliminar foto">✕</button>
                    </div>
                `;
            });
        }

        function eliminarFotoFila(idx, pos) {
            if (imagenesPorFila[idx]) {
                imagenesPorFila[idx].splice(pos, 1);
                renderizarGaleriaFila(idx);
            }
        }
        
        function aplicarExposicionMasiva() {
            const expoVal = document.getElementById('bulk-exposicion').value;
            document.querySelectorAll('.select-exposicion').forEach(sel => sel.value = expoVal);
        }

        function aplicarEnvioMasivo() {
            const envioVal = document.getElementById('bulk-envio').value;
            document.querySelectorAll('.select-envio').forEach(sel => sel.value = envioVal);
        }

        async function abrirModalCategorias() {
            const fileInput = document.getElementById('file-db');
            if (!fileInput.files.length) return alert('Selecciona primero un archivo Excel o CSV.');

            const modal = document.getElementById('modal-categoria-mlv');
            const grid = document.getElementById('lista-categorias-ml');
            grid.innerHTML = "⏳ Cargando categorías oficiales desde Mercado Libre...";
            modal.style.display = 'flex';

            try {
                const res = await fetch('/api/categorias-mlv');
                const catList = await res.json();
                
                grid.innerHTML = `
                    <div class="category-item selected" onclick="seleccionarCategoria('TODAS', this)" style="grid-column: span 2; background:#e0f2fe; border-color:#0284c7;">
                        🌐 <b>CARGAR TODO EL INVENTARIO</b> (Sin filtro de categoría)
                    </div>
                `;

                catList.forEach(c => {
                    grid.innerHTML += `
                        <div class="category-item" onclick="seleccionarCategoria('${c.id}', this)">
                            📌 ${c.name} <span style="font-size:10px; color:#64748b;">(${c.id})</span>
                        </div>
                    `;
                });
            } catch(e) {
                grid.innerHTML = "❌ Error conectando a la API de categorías MLV.";
            }
        }

        function seleccionarCategoria(idCat, elemento) {
            document.querySelectorAll('.category-item').forEach(el => el.classList.remove('selected'));
            elemento.classList.add('selected');
            document.getElementById('cat-seleccionada-id').value = idCat;
        }

        function cerrarModalCategorias() {
            document.getElementById('modal-categoria-mlv').style.display = 'none';
        }

        async function confirmarYCargarInventario() {
            cerrarModalCategorias();
            const idCat = document.getElementById('cat-seleccionada-id').value;
            const fileInput = document.getElementById('file-db');

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('cuenta', document.getElementById('cuenta-select').value);
            formData.append('hoja', document.getElementById('hoja-select').value);
            formData.append('inicio', document.getElementById('rango-inicio').value);
            formData.append('fin', document.getElementById('rango-fin').value);
            formData.append('categoria_filtro', idCat);
            formData.append('filtrar_duplicados', document.getElementById('filtar-duplicados').checked);

            formData.append('col_tit', document.getElementById('map-tit').value);
            formData.append('col_sku', document.getElementById('map-sku').value);
            formData.append('col_mod', document.getElementById('map-mod').value);
            formData.append('col_pre', document.getElementById('map-pre').value);
            formData.append('col_stk', document.getElementById('map-stk').value);

            document.getElementById('tabla-container').style.display = 'none';
            document.getElementById('loader-zona').style.display = 'block';
            document.getElementById('spinner-percentage').innerText = "0%";
            document.getElementById('loader-mensaje').innerText = "Iniciando sincronización...";
            
            iniciarMonitoreoProgreso();
            
            const consola = document.getElementById('resultados');
            consola.innerText = `⏳ Sincronizando inventario con filtro: [${idCat}]...`;

            try {
                const response = await fetch('/previsualizar', { method: 'POST', body: formData });
                const resultado = await response.json();

                if (resultado.error) return consola.innerText = "❌ " + resultado.error;

                const tbody = document.getElementById('tabla-body');
                tbody.innerHTML = "";

                resultado.productos.forEach((prod, idx) => {
                    imagenesPorFila[idx] = [];
                    if (prod.ImagenLocal) {
                        imagenesPorFila[idx].push(prod.ImagenLocal);
                    }
                    
                    atributosPorFila[idx] = {
                        marca: prod.Marca,
                        modelo: prod.Modelo,
                        color: "",
                        compatibilidad: "",
                        material: ""
                    };
                    atributosAdicionalesPorFila[idx] = {};

                    let gtinDisplay = (prod.GTIN && prod.GTIN !== 'N/A' && prod.GTIN !== 'OMITIR') ? 'block' : 'none';
                    let selectCustom = (prod.GTIN && prod.GTIN !== 'N/A' && prod.GTIN !== 'OMITIR') ? 'selected' : '';
                    let selectOmit = (prod.GTIN && prod.GTIN !== 'N/A' && prod.GTIN !== 'OMITIR') ? '' : 'selected';

                    let resumenInit = `🏷️ ${prod.Marca} / ${prod.Modelo}`;

                    let badgesHTML = "";
                    for (const [nomCuenta, est] of Object.entries(prod.EstadoCuentas)) {
                        badgesHTML += (est === "EXISTE") 
                            ? `<span class="account-badge badge-existe">${nomCuenta}: Ya Publicado</span>`
                            : `<span class="account-badge badge-libre">${nomCuenta}: Libre</span>`;
                    }

                    tbody.innerHTML += `
                        <tr>
                            <td><input type="checkbox" class="prod-check" data-idx="${idx}" checked></td>
                            <td>
                                <input type="text" id="tit-${idx}" value="${prod.Titulo}" maxlength="60" style="margin-bottom:4px; font-weight:bold;">
                                <div class="cat-tag" title="ID: ${prod.Categoria_ID}">📌 ML: ${prod.CategoriaNombre}</div>
                                <div id="desc-tag-${idx}" class="desc-tag">📋 Plantilla Oficial (Título x3)</div>
                                <div style="font-size:11px; color:#64748b; margin-top:2px;">📁 Hoja: <b>${prod.Hoja}</b> (${prod.CategoriaOrigen})</div>
                                <div style="margin-top:6px;">${badgesHTML}</div>
                                <input type="hidden" id="cat-${idx}" value="${prod.Categoria_ID}">
                                <input type="hidden" id="desc-init-${idx}" value="${prod.DescripcionCustom || ''}">
                            </td>
                            <td><input type="number" id="pre-${idx}" value="${prod.Precio}" step="0.01"></td>
                            <td><input type="number" id="stk-${idx}" value="${prod.Stock}"></td>
                            <td>
                                <select id="expo-${idx}" class="select-exposicion attr-select" style="margin-bottom:5px; font-weight:bold;">
                                    <option value="bronze">Bronce / Estándar</option>
                                    <option value="gold_special">Clásica</option>
                                    <option value="gold_pro">Premium</option>
                                </select>
                                <select id="envio-${idx}" class="select-envio attr-select" style="font-size:11px; font-weight:bold;">
                                    <option value="me2_free">🟢 Envío Gratis</option>
                                    <option value="custom_free">🟢 Envío Gratis Nacional (Custom)</option>
                                    <option value="me2_buyer">🔵 Cobro en Destino</option>
                                    <option value="not_specified">⚪ Acordar con Vendedor</option>
                                </select>
                            </td>
                            <td>
                                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:4px; margin-bottom:4px;">
                                    <input type="text" id="mar-${idx}" value="${prod.Marca}" placeholder="Marca">
                                    <input type="text" id="mod-${idx}" value="${prod.Modelo}" placeholder="Modelo">
                                </div>
                                <input type="text" id="sku-${idx}" value="${prod.SKU}" placeholder="SKU" style="margin-bottom:4px;">
                                <select id="gtin-razon-${idx}" class="attr-select" onchange="toggleGtin(${idx})" style="margin-bottom:4px; font-size:11px; font-weight:bold;">
                                    <option value="CUSTOM" ${selectCustom}>Ingresar Código (GTIN)</option>
                                    <option value="OMITIR" ${selectOmit}>Este producto no posee código</option>
                                </select>
                                <input type="text" id="gtin-${idx}" value="${prod.GTIN !== 'N/A' ? prod.GTIN : ''}" style="display:${gtinDisplay}; margin-bottom:4px;">
                                <button onclick="abrirModal(${idx})" style="background:#0284c7; width:100%; padding:4px; font-size:11px;">🛠️ Ver / Editar + Características Oficiales MLV</button>
                                <div id="resumen-attr-${idx}" class="attr-summary">${resumenInit}</div>
                            </td>
                            <td>
                                <div class="photo-manager">
                                    <span>📸 Clic o Arrastra fotos aquí</span>
                                    <input type="file" accept="image/jpeg, image/png, image/webp" multiple onchange="procesarArchivos(this, ${idx})">
                                </div>
                                <div id="prev-${idx}" class="preview-container"></div>
                            </td>
                        </tr>
                    `;
                    
                    renderizarGaleriaFila(idx);
                });

                document.getElementById('tabla-container').style.display = 'block';
                consola.innerText = `✅ ¡Sincronización completa! ${resultado.productos.length} artículos listos.`;
            } catch(e) {
                consola.innerText = "❌ Error en sincronización: " + e;
            } finally {
                if (intervaloProgreso) clearInterval(intervaloProgreso);
                setTimeout(() => { document.getElementById('loader-zona').style.display = 'none'; }, 500);
            }
        }

        async function cargarGaleriaLocal() {
            const cont = document.getElementById('galeria-contenedor');
            cont.innerHTML = "<div style='color:#64748b;'>⏳ Leyendo archivos desde la carpeta lote_imagenes...</div>";
            try {
                const res = await fetch('/api/galeria-local');
                const imgs = await res.json();
                if (!imgs.length) {
                    cont.innerHTML = "<div style='color:#64748b;'>No se encontraron imágenes JPG, PNG o WEBP en la carpeta <b>lote_imagenes</b>.</div>";
                    return;
                }
                cont.innerHTML = "";
                imgs.forEach(item => {
                    cont.innerHTML += `
                        <div class="gallery-item">
                            <img src="${item.b64}">
                            <span>${item.nombre}</span>
                        </div>
                    `;
                });
            } catch(e) {
                cont.innerHTML = "<div style='color:red;'>❌ Error cargando galería local.</div>";
            }
        }

        function toggleAll(source) {
            document.querySelectorAll('.prod-check').forEach(cb => cb.checked = source.checked);
        }

        async function ejecutarPublicacion() {
            const seleccionados = [];
            document.querySelectorAll('.prod-check:checked').forEach(cb => {
                const idx = cb.dataset.idx;
                const attr = atributosPorFila[idx];
                const adic = atributosAdicionalesPorFila[idx] || {};
                const razonGtin = document.getElementById('gtin-razon-'+idx).value;
                let gtinFinal = (razonGtin === 'CUSTOM') ? document.getElementById('gtin-'+idx).value : 'OMITIR';

                seleccionados.push({
                    "Titulo": document.getElementById('tit-'+idx).value,
                    "Precio": parseFloat(document.getElementById('pre-'+idx).value),
                    "Stock": parseInt(document.getElementById('stk-'+idx).value),
                    "Categoria_ID": document.getElementById('cat-'+idx).value,
                    "Exposicion": document.getElementById('expo-'+idx).value,
                    "Envio": document.getElementById('envio-'+idx).value,
                    "Marca": document.getElementById('mar-'+idx).value,
                    "Modelo": document.getElementById('mod-'+idx).value,
                    "SKU": document.getElementById('sku-'+idx).value,
                    "GTIN": gtinFinal,
                    "AtributosDinamicos": adic,
                    "DescripcionCustom": document.getElementById('desc-init-'+idx).value,
                    "ImagenesB64": imagenesPorFila[idx] || []
                });
            });

            if (!seleccionados.length) return alert('No hay artículos seleccionados.');
            const cuentaSel = document.getElementById('cuenta-select').value;
            const nomCuenta = document.getElementById('cuenta-select').options[document.getElementById('cuenta-select').selectedIndex].text;

            if (!confirm(`¿Confirmas publicar ${seleccionados.length} artículos en: ${nomCuenta}?`)) return;

            document.getElementById('loader-zona').style.display = 'block';
            document.getElementById('spinner-percentage').innerText = "0%";
            document.getElementById('loader-mensaje').innerText = "Iniciando publicación en lote...";
            iniciarMonitoreoProgreso();

            const consola = document.getElementById('resultados');
            consola.innerText = `🚀 Publicando lote...`;

            try {
                const response = await fetch(`/publicar-lote?cuenta=${cuentaSel}`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(seleccionados)
                });
                const resData = await response.json();
                consola.innerText = resData.detalles.join('\\n');
            } catch(e) {
                consola.innerText = "❌ Error subiendo lote: " + e;
            } finally {
                if (intervaloProgreso) clearInterval(intervaloProgreso);
                setTimeout(() => { document.getElementById('loader-zona').style.display = 'none'; }, 500);
            }
        }
    </script>
</body>
</html>
"""

@app.get("/estado-progreso")
def obtener_estado_progreso():
    return PROGRESO_ACTUAL

@app.get("/cuentas")
def obtener_cuentas():
    archivos = listar_archivos_token()
    return [{"archivo": a, "nombre": obtener_nombre_cuenta(a)} for a in archivos]

@app.get("/api/categorias-mlv")
def endpoint_categorias_mlv():
    return obtener_categorias_raices_mlv()

@app.post("/api/hojas-excel")
async def obtener_hojas_excel(file: UploadFile = File(...)):
    temp_filename = f"temp_sheets_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        buffer.write(await file.read())
    
    hojas = []
    try:
        if temp_filename.lower().endswith(".csv"):
            hojas = ["CSV (Hoja Única)"]
        else:
            with pd.ExcelFile(temp_filename) as xls:
                hojas = xls.sheet_names
    except Exception:
        hojas = ["Hoja 1"]
    finally:
        time.sleep(0.1)
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except PermissionError:
                pass
    return {"hojas": hojas}

@app.post("/api/columnas-excel")
async def endpoint_columnas_excel(file: UploadFile = File(...), hoja: str = Form("TODAS")):
    temp_filename = f"temp_cols_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        buffer.write(await file.read())
    
    columnas = obtener_encabezados_excel(temp_filename, hoja_objetivo=hoja)
    time.sleep(0.1)
    if os.path.exists(temp_filename):
        try: os.remove(temp_filename)
        except PermissionError: pass
    return columnas

@app.post("/api/vista-previa-excel")
async def endpoint_vista_previa_excel(file: UploadFile = File(...)):
    temp_filename = f"temp_preview_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        buffer.write(await file.read())
    
    vistas = obtener_vista_previa_excel(temp_filename)
    time.sleep(0.1)
    if os.path.exists(temp_filename):
        try: os.remove(temp_filename)
        except PermissionError: pass
    return {"vistas": vistas}

@app.get("/api/atributos-categoria/{cat_id}")
def endpoint_atributos_categoria(cat_id: str):
    try:
        url = f"https://api.mercadolibre.com/categories/{cat_id}/attributes"
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            attrs = res.json()
            relevantes = []
            PROHIBIDOS = {"BRAND", "MODEL", "SELLER_SKU", "PART_NUMBER", "GTIN", "ITEM_CONDITION", "HAS_COMPATIBILITIES"}
            for att in attrs:
                aid = att.get("id")
                if aid not in PROHIBIDOS and not att.get("read_only", False):
                    relevantes.append({
                        "id": aid,
                        "name": att.get("name"),
                        "value_type": att.get("value_type", "string"),
                        "hint": att.get("hint", ""),
                        "values": att.get("values", [])[:20]
                    })
            return relevantes
    except Exception:
        pass
    return []

@app.get("/api/galeria-local")
def endpoint_galeria_local():
    if not os.path.exists(CARPETA_LOTE_IMAGENES):
        return []
    
    lista_fotos = []
    for arc in sorted(os.listdir(CARPETA_LOTE_IMAGENES)):
        ext = arc.rsplit(".", 1)[-1].lower()
        if ext in ["jpg", "jpeg", "png", "webp"]:
            ruta = os.path.join(CARPETA_LOTE_IMAGENES, arc)
            try:
                with open(ruta, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                    mime = "image/jpeg" if ext in ["jpg", "jpeg"] else f"image/{ext}"
                    lista_fotos.append({
                        "nombre": arc,
                        "b64": f"data:{mime};base64,{data}"
                    })
            except Exception:
                continue
    return lista_fotos

@app.get("/verificar-tokens")
def verificar_tokens_endpoint():
    archivos = listar_archivos_token()
    logs = []
    for arch in archivos:
        nombre = obtener_nombre_cuenta(arch)
        try:
            with open(arch, "r") as f:
                datos = json.load(f)
            token = datos.get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            res = requests.get("https://api.mercadolibre.com/users/me", headers=headers)
            if res.status_code == 200:
                user_info = res.json()
                nick = user_info.get("nickname", "Desconocido")
                logs.append(f"✅ [{nombre}] Conexión Activa (Usuario: {nick} - ID: {user_info.get('id')})")
            else:
                logs.append(f"⚠️ [{nombre}] Token expirado o inválido. Renovando...")
                nuevo_token, estado = renovar_y_guardar_token(arch, datos)
                if estado == "OK":
                    logs.append(f"🔄 [{nombre}] ¡Renovación Exitosa!")
                else:
                    logs.append(f"❌ [{nombre}] No se pudo renovar -> {estado}")
        except Exception as e:
            logs.append(f"❌ [{nombre}] Error leyendo token: {e}")
    return {"logs": logs}

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_INTERFACE

@app.post("/previsualizar")
async def previsualizar_archivo(
    file: UploadFile = File(...), 
    cuenta: str = Form(...),
    hoja: str = Form("TODAS"),
    inicio: int = Form(1),
    fin: int = Form(100),
    categoria_filtro: str = Form("TODAS"),
    filtrar_duplicados: str = Form("true"),
    col_tit: str = Form(""),
    col_sku: str = Form(""),
    col_mod: str = Form(""),
    col_pre: str = Form(""),
    col_stk: str = Form("")
):
    actualizar_progreso(5, "Cargando archivo en memoria...")
    PROGRESO_ACTUAL["activo"] = True
    temp_filename = f"temp_{file.filename}"
    with open(temp_filename, "wb") as buffer: buffer.write(await file.read())

    archivos_a_escanear = listar_archivos_token()
    titulos_por_cuenta = {}

    actualizar_progreso(15, "Analizando inventarios activos de cada cuenta en Mercado Libre...")
    for arch in archivos_a_escanear:
        token = obtener_token(arch)
        nombre_c = obtener_nombre_cuenta(arch)
        if token:
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            titulos_por_cuenta[nombre_c] = obtener_titulos_publicados(headers)
        else:
            titulos_por_cuenta[nombre_c] = set()

    token_ref = obtener_token(archivos_a_escanear[0])
    headers_ref = {"Authorization": f"Bearer {token_ref}", "Content-Type": "application/json"} if token_ref else {}

    mapa_manual = {
        "tit": col_tit if col_tit else None,
        "sku": col_sku if col_sku else None,
        "mod": col_mod if col_mod else None,
        "pre": col_pre if col_pre else None,
        "stk": col_stk if col_stk else None
    }

    try:
        filas_procesadas = procesar_excel_heuristico(temp_filename, hoja_objetivo=hoja, mapa_manual=mapa_manual)
    except Exception as e:
        PROGRESO_ACTUAL["activo"] = False
        return {"error": f"Error heurístico leyendo el archivo: {str(e)}"}

    idx_inicio = max(0, inicio - 1)
    filas_rango = filas_procesadas[idx_inicio:fin]
    total_filas = len(filas_rango)

    productos_activos = []
    cache_categorias_adivinadas = {}
    
    for indice, item in enumerate(filas_rango):
        await asyncio.sleep(0.01)
        porcentaje_actual = int(20 + ((indice + 1) / max(1, total_filas)) * 75)
        
        titulo = item["Titulo"]
        titulo_norm = titulo.lower()

        estado_cuentas = {}
        existe_en_todas = True
        existe_en_seleccionada = False
        nombre_seleccionada = obtener_nombre_cuenta(cuenta) if cuenta != "TODAS" else "TODAS"

        for nom_c, set_tits in titulos_por_cuenta.items():
            if titulo_norm in set_tits:
                estado_cuentas[nom_c] = "EXISTE"
                if nom_c == nombre_seleccionada:
                    existe_en_seleccionada = True
            else:
                estado_cuentas[nom_c] = "LIBRE"
                existe_en_todas = False

        if filtrar_duplicados == "true":
            if cuenta == "TODAS" and existe_en_todas:
                continue
            elif cuenta != "TODAS" and existe_en_seleccionada:
                continue

        sku = item["SKU"]
        modelo = item["Modelo"]
        precio = item["Precio"]
        stock = item["Stock"]
        marca = item["Marca"]
        cat_origen = item["CategoriaOrigen"]
        nom_hoja = item["Hoja"]

        if token_ref:
            if titulo in cache_categorias_adivinadas:
                cat_id, cat_nombre = cache_categorias_adivinadas[titulo]
            else:
                cat_id, cat_nombre = adivinar_categoria_y_raiz(titulo, headers_ref)
                cache_categorias_adivinadas[titulo] = (cat_id, cat_nombre)
        else:
            cat_id, cat_nombre = "MLV-DESCONOCIDA", "Categoría General"

        if not coincide_con_categoria_elegida(titulo, cat_id, categoria_filtro):
            continue

        actualizar_progreso(porcentaje_actual, f"[{indice+1}/{total_filas}] Sincronizando: {titulo[:25]}...")
            
        imagen_emparejada = emparejar_imagen_local(modelo, sku, titulo)
        
        productos_activos.append({
            "Titulo": titulo, "Precio": precio, "Stock": stock,
            "Marca": marca, "Modelo": modelo, "SKU": sku, 
            "Color": "", "Compatibilidad": "", "Material": "",
            "DescripcionCustom": "", "GTIN": "N/A",
            "Categoria_ID": cat_id, "CategoriaNombre": cat_nombre,
            "ImagenLocal": imagen_emparejada, "EstadoCuentas": estado_cuentas,
            "Hoja": nom_hoja, "CategoriaOrigen": cat_origen
        })

    if os.path.exists(temp_filename): os.remove(temp_filename)
    actualizar_progreso(100, "¡Sincronización Finalizada!")
    PROGRESO_ACTUAL["activo"] = False
    
    return {"productos": sorted(productos_activos, key=lambda x: x["Categoria_ID"])}

@app.post("/publicar-lote")
async def publicar_lote(productos: list[dict], cuenta: str = "tokens_ml.json"):
    PROGRESO_ACTUAL["activo"] = True
    archivos_destino = listar_archivos_token() if cuenta == "TODAS" else [cuenta]
    logs_totales = []
    total_items = len(productos) * len(archivos_destino)
    procesados = 0

    for arch_token in archivos_destino:
        token = obtener_token(arch_token)
        nombre_perfil = obtener_nombre_cuenta(arch_token)
        
        if not token:
            logs_totales.append(f"❌ [{nombre_perfil}] Error: Token no válido.")
            continue

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        titulos_existentes_cuenta = obtener_titulos_publicados(headers)

        for prod in productos:
            await asyncio.sleep(0.01)
            procesados += 1
            porcentaje = int((procesados / max(1, total_items)) * 100)
            titulo_original = prod['Titulo'][:60].strip()
            
            if titulo_original.lower() in titulos_existentes_cuenta:
                logs_totales.append(f"⏭️ [{nombre_perfil}] OMITIDO: '{titulo_original[:20]}...' ya existe en esta cuenta.")
                continue

            actualizar_progreso(porcentaje, f"[{nombre_perfil}] Publicando ({procesados}/{total_items}): {titulo_original[:25]}...")

            titulo_x3 = f"{titulo_original}\n{titulo_original}\n{titulo_original}\n"
            if prod.get('DescripcionCustom') and len(str(prod['DescripcionCustom']).strip()) > 5:
                cuerpo_desc = f"{prod['DescripcionCustom']}\n"
                descripcion_estructurada = f"{BLOQUE_SUPERIOR}\n\n{titulo_x3}\n{cuerpo_desc}\n{BLOQUE_INFERIOR}"
            else:
                descripcion_estructurada = f"{BLOQUE_SUPERIOR}\n\n{titulo_x3}\n{BLOQUE_INFERIOR}"

            payload_desc = {
                "plain_text": descripcion_estructurada,
                "text": descripcion_estructurada
            }

            attr_adicionales = prod.get('AtributosDinamicos', {})
            atributos_payload = construir_atributos_dinamicos_dict(prod, attr_adicionales, headers)

            modo_envio = prod.get('Envio', 'not_specified')
            if modo_envio == "me2_free" or "free" in str(modo_envio).lower() or "gratis" in str(modo_envio).lower():
                shipping_payload = {"mode": "me2", "local_pick_up": True, "free_shipping": True}
            elif modo_envio == "custom_free":
                shipping_payload = {"mode": "custom", "free_shipping": True, "costs": [{"description": "Envío Gratis a Nivel Nacional", "cost": 0}]}
            elif modo_envio == "me2_buyer":
                shipping_payload = {"mode": "me2", "local_pick_up": True, "free_shipping": False}
            else:
                shipping_payload = {"mode": "me2", "local_pick_up": True, "free_shipping": True}

            datos_publicacion = {
                "title": titulo_original,
                "category_id": prod['Categoria_ID'],
                "price": prod['Precio'],
                "currency_id": "USD",
                "available_quantity": prod['Stock'],
                "buying_mode": "buy_it_now",
                "condition": "new",
                "listing_type_id": prod.get('Exposicion', 'bronze'),
                "attributes": atributos_payload,
                "shipping": shipping_payload
            }

            fotos_payload = []
            if prod.get('ImagenesB64'):
                for img_b64 in prod['ImagenesB64']:
                    pic_id = subir_foto_a_ml(img_b64, token)
                    if pic_id:
                        fotos_payload.append({"id": pic_id})
            if fotos_payload:
                datos_publicacion["pictures"] = fotos_payload

            respuesta = requests.post("https://api.mercadolibre.com/items", headers=headers, json=datos_publicacion, timeout=12)
            
            if respuesta.status_code == 201:
                item_data = respuesta.json()
                item_id = item_data.get('id')
                permalink = item_data.get('permalink')
                
                await asyncio.sleep(0.5)
                res_desc = requests.post(f"https://api.mercadolibre.com/items/{item_id}/description", headers=headers, json=payload_desc, timeout=10)
                if res_desc.status_code not in [200, 201]:
                    requests.put(f"https://api.mercadolibre.com/items/{item_id}/description", headers=headers, json=payload_desc, timeout=10)

                requests.put(f"https://api.mercadolibre.com/items/{item_id}", headers=headers, json={"shipping": shipping_payload, "attributes": atributos_payload}, timeout=10)
                logs_totales.append(f"✅ [{nombre_perfil}] ¡PUBLICADO! -> {permalink}")
            else:
                error_texto = respuesta.text
                if "restrictions_coliving" in error_texto:
                    titulo_mascarado = re.sub(r'(?i)\b(canon|hp|epson|brother|samsung|apple|sony)\b', 'Compatible', titulo_original)
                    datos_publicacion["title"] = titulo_mascarado
                    res_bypass = requests.post("https://api.mercadolibre.com/items", headers=headers, json=datos_publicacion, timeout=12)
                    if res_bypass.status_code == 201:
                        item_data = res_bypass.json()
                        item_id = item_data.get('id')
                        permalink = item_data.get('permalink')
                        
                        await asyncio.sleep(0.5)
                        res_desc = requests.post(f"https://api.mercadolibre.com/items/{item_id}/description", headers=headers, json=payload_desc, timeout=10)
                        if res_desc.status_code not in [200, 201]:
                            requests.put(f"https://api.mercadolibre.com/items/{item_id}/description", headers=headers, json=payload_desc, timeout=10)

                        requests.put(f"https://api.mercadolibre.com/items/{item_id}", headers=headers, json={"title": titulo_original}, timeout=10)
                        requests.put(f"https://api.mercadolibre.com/items/{item_id}", headers=headers, json={"shipping": shipping_payload, "attributes": atributos_payload}, timeout=10)
                        logs_totales.append(f"✅ [{nombre_perfil}] ¡PUBLICADO (Bypass Catálogo)! -> {permalink}")
                    else:
                        error_data = res_bypass.json()
                        causas = error_data.get('cause', [])
                        detalles = " | ".join([c.get('message', str(c)) if isinstance(c, dict) else str(c) for c in causas]) if (isinstance(causas, list) and len(causas) > 0) else str(error_data.get('message', 'Error ML'))
                        logs_totales.append(f"❌ [{nombre_perfil}] Error '{titulo_original[:15]}...': {detalles}")
                else:
                    error_data = respuesta.json()
                    causas = error_data.get('cause', [])
                    detalles = " | ".join([c.get('message', str(c)) if isinstance(c, dict) else str(c) for c in causas]) if (isinstance(causas, list) and len(causas) > 0) else str(error_data.get('message', 'Error ML'))
                    logs_totales.append(f"❌ [{nombre_perfil}] Error '{titulo_original[:15]}...': {detalles}")

    actualizar_progreso(100, "¡Lote Completado!")
    PROGRESO_ACTUAL["activo"] = False
    return {"detalles": logs_totales}