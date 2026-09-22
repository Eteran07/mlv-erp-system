import os
import glob
import json
import base64
import requests
import pandas as pd
import re
import time
import asyncio
import urllib.parse
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
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

# =================================================================
# BLINDAJE ANTI-PORTAPAPELES (EVITA ENLACES ROTOS MARKDOWN)
# =================================================================
DOM_ML = "mercado" + "libre.com"
API_ML = f"https://api.{DOM_ML}"
DOM_WA = "wa" + ".me"
API_WA = f"https://{DOM_WA}"

CARPETA_LOTE_IMAGENES = "lote_imagenes"
os.makedirs(CARPETA_LOTE_IMAGENES, exist_ok=True)

CARPETA_CATALOGOS = "catalogos_generados"
os.makedirs(CARPETA_CATALOGOS, exist_ok=True)

CARPETA_REPORTES = "reportes"
os.makedirs(CARPETA_REPORTES, exist_ok=True)

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
- Realice todas las preguntas necesarias Antes de ofertar.
- El equipo de ventas está a tu disposición para responder tus consultas.
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
        if not base64_data or not isinstance(base64_data, str) or not base64_data.startswith("data:image/"):
            return None
        header, encoded = base64_data.split(",", 1)
        file_ext = header.split(";")[0].split("/")[1]
        image_bytes = base64.b64decode(encoded)

        url = f"{API_ML}/pictures"
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": (f"foto.{file_ext}", image_bytes, f"image/{file_ext}")}
        
        res = requests.post(url, headers=headers, files=files, timeout=12)
        if res.status_code == 201:
            return res.json().get("id") 
    except Exception as e:
        print(f"Error procesando imagen base64: {e}")
    return None

def analizar_error_ml(respuesta):
    try:
        error_data = respuesta.json()
        causas = error_data.get('cause', [])
        if not causas and 'message' in error_data:
            causas = [{"message": error_data['message']}]
        
        msg_list = []
        for c in causas:
            msg = c.get('message', str(c)) if isinstance(c, dict) else str(c)
            
            if "500 pixeles" in msg or "500 pixels" in msg or "minimum size" in msg:
                msg_limpio = "📸 Error: Las fotos son muy pequeñas (Mínimo 500x500px)."
            elif "The provided unit is not valid" in msg or "The provided number is not valid" in msg:
                match = re.search(r'Attribute (.*?) with value', msg)
                attr = match.group(1) if match else "Un atributo"
                msg_limpio = f"📏 Falta unidad en '{attr}' (Debe incluir GB, pulgadas, Hz, etc)."
            elif "is not valid, item values" in msg:
                match = re.search(r'Attribute \[(.*?)\]', msg)
                attr = match.group(1) if match else "Un atributo"
                msg_limpio = f"❌ Valor no aceptado por ML en '{attr}' (Evita usar 'N/A' o 'No Aplica')."
            elif "is required and was omitted" in msg:
                match = re.search(r'Attribute (.*?) ', msg)
                attr = match.group(1) if match else "Un atributo"
                msg_limpio = f"⚠️ Falta atributo obligatorio: '{attr}'."
            else:
                msg_limpio = f"❌ {msg}"
            
            if msg_limpio not in msg_list:
                msg_list.append(msg_limpio)
        
        return " | ".join(msg_list)
    except Exception:
        return f"Error HTTP {respuesta.status_code}: Conexión rechazada por Mercado Libre."

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
            k_id_upper = str(k_id).strip().upper()
            if k_id_upper not in PROHIBIDOS and str(v_val).strip() != "":
                lista.append({"id": k_id_upper, "value_name": str(v_val).strip()})
    return lista

def obtener_diccionario_publicados_ml(headers):
    try:
        url_me = f"{API_ML}/users/me"
        res_me = requests.get(url_me, headers=headers)
        if res_me.status_code != 200: return {}
        user_id = res_me.json().get("id")

        url_search = f"{API_ML}/users/{user_id}/items/search"
        res_items = requests.get(url_search, headers=headers)
        item_ids = res_items.json().get("results", [])
        
        diccionario = {}
        if item_ids:
            for i in range(0, len(item_ids), 50):
                ids_str = ",".join(item_ids[i:i+50]) 
                url_items = f"{API_ML}/items?ids={ids_str}"
                res_detalles = requests.get(url_items, headers=headers)
                for item in res_detalles.json():
                    if item.get("code") == 200:
                        body = item.get("body", {})
                        title = body.get("title", "").strip().lower()
                        permalink = body.get("permalink", "")
                        if title and permalink:
                            diccionario[title] = permalink
        return diccionario
    except Exception:
        return {}

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
        table.data-table tbody tr.cat-header:hover { background: #cbd5e1; }
        table.data-table tbody tr.item-row:hover { background: #f1f5f9; }
        
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
            <li class="nav-item" onclick="mostrarSeccion('tab-catalogo', this)">
                <span>📑</span> <span class="nav-text">Generar Catálogo</span>
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
                    <button onclick="abrirModalCategorias()" style="width: 100%; padding: 14px; font-size: 15px; background: #0284c7; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">
                        🔍 Analizar Inventario y Generar Reporte
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
                    <div id="resumen-reporte-box" style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 20px; margin-bottom: 20px; display: none;">
                        <div id="texto-resumen-reporte" style="font-size: 14px; color: #166534; line-height: 1.6;"></div>
                    </div>

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
                        <button id="btn-bulk-ia" class="bulk-btn" onclick="autollenarLoteIA()" style="margin-left:8px; background:#2563eb;">🤖 Autollenar Fichas (IA DeepSeek)</button>
                    </div>

                    <table class="data-table" id="data-table">
                        <thead>
                            <tr>
                                <th style="width: 30px;" title="Seleccionar TODO el inventario">
                                    <input type="checkbox" checked onclick="toggleAll(this)">
                                </th>
                                <th style="width: 24%;">Título, Categoría & Estado por Cuenta</th>
                                <th style="width: 8%;">Precio $</th>
                                <th style="width: 6%;">Stock</th>
                                <th style="width: 16%;">Exposición & Envío</th>
                                <th style="width: 26%;">Ficha Técnica & Descripción Final</th>
                                <th style="width: 20%;">Gestor de Fotos Local</th>
                            </tr>
                        </thead>
                        <tbody id="tabla-body"></tbody>
                    </table>
                    <button onclick="ejecutarPublicacion()" style="background: #16a34a; width: 100%; margin-top: 25px; padding: 16px; font-size: 16px; font-weight:800; color: white; border: none; border-radius: 8px; cursor: pointer;">
                        🚀 Confirmar y Publicar Lote Seleccionado
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
                <button onclick="verificarTokens()" style="padding: 12px 25px; font-size: 15px; background: #0284c7; color: white; border: none; border-radius: 8px; cursor: pointer;">🔄 Probar Conexión y Renovar Tokens Ahora</button>
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
                    <button onclick="cargarGaleriaLocal()" style="background:#0284c7; padding:10px 18px; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">🔄 Actualizar Galería</button>
                </div>
                <div id="galeria-contenedor" class="gallery-grid"></div>
            </div>
        </div>

        <!-- PESTAÑA 5: CATÁLOGO DIGITAL -->
        <div id="tab-catalogo" class="section-view">
            <div class="container">
                <h1>📑 Generador de Catálogo Digital Premium</h1>
                <div class="subtitle">Escanea tu Excel, valida inventario y genera un catálogo agrupado por categorías de Mercado Libre con links directos de compra (WhatsApp y ML).</div>
                
                <div class="steps-grid">
                    <div class="step-card">
                        <span class="step-num">Paso 1</span>
                        <label>Cuenta ML (Para link de compra directa):</label>
                        <select id="cat-cuenta"></select>
                    </div>
                    <div class="step-card">
                        <span class="step-num">Paso 2</span>
                        <label>Archivo Excel Maestro:</label>
                        <input type="file" id="cat-file" accept=".xlsx, .csv" onchange="detectarHojasCat(this)">
                    </div>
                    <div class="step-card">
                        <span class="step-num">Paso 3</span>
                        <label>Hoja a Escanear:</label>
                        <select id="cat-hoja-select" onchange="cambiarHojaSeleccionadaCat()">
                            <option value="TODAS">📚 Todo el Libro (Todas las Hojas)</option>
                        </select>
                    </div>
                    <div class="step-card">
                        <span class="step-num">Paso 4</span>
                        <label>Rango de filas:</label>
                        <div style="display: flex; gap: 8px;">
                            <input type="number" id="cat-rango-inicio" value="1" placeholder="Desde" style="width: 50%;">
                            <input type="number" id="cat-rango-fin" value="100" placeholder="Hasta" style="width: 50%;">
                        </div>
                    </div>
                    <div class="step-card" style="grid-column: span 2;">
                        <span class="step-num">Datos de Empresa</span>
                        <div style="display: flex; gap: 8px;">
                            <div style="width: 50%;">
                                <label>Nombre de Empresa:</label>
                                <input type="text" id="cat-empresa" placeholder="Ej: Mi Tienda C.A.">
                            </div>
                            <div style="width: 50%;">
                                <label>WhatsApp de Ventas:</label>
                                <input type="text" id="cat-ws" placeholder="Ej: 04141234567">
                            </div>
                        </div>
                    </div>
                </div>

                <div id="cat-mapping-bar" class="mapping-bar">
                    <h4 style="margin: 0 0 5px 0; color: #0369a1; font-size: 15px; font-weight: 800;">🎯 Validar Columnas del Catálogo:</h4>
                    <span style="font-size: 13px; color: #0284c7; font-weight: 600;">Asegúrate de que el sistema identifique correctamente el título, SKU y precio para el catálogo.</span>
                    <div class="mapping-grid">
                        <div><label>Título:</label><select id="cat-map-tit"><option value="">-- Automático --</option></select></div>
                        <div><label>SKU / Código:</label><select id="cat-map-sku"><option value="">-- Automático --</option></select></div>
                        <div><label>Modelo:</label><select id="cat-map-mod"><option value="">-- Automático --</option></select></div>
                        <div><label>Precio:</label><select id="cat-map-pre"><option value="">-- Automático --</option></select></div>
                        <div><label>Stock (Opcional):</label><select id="cat-map-stk"><option value="">-- Automático --</option></select></div>
                    </div>

                    <div class="excel-preview-box">
                        <div class="excel-preview-header">
                            <span id="cat-excel-preview-title">📊 Vista Previa de Datos a Exportar</span>
                            <div id="cat-excel-preview-nav" class="excel-preview-nav" style="display:none;">
                                <button type="button" class="excel-nav-btn" onclick="cambiarHojaPreviewCat(-1)">⬅️ Anterior</button>
                                <span id="cat-excel-preview-counter" style="color:#0f172a; font-weight:bold;">Hoja 1 de 1</span>
                                <button type="button" class="excel-nav-btn" onclick="cambiarHojaPreviewCat(1)">Siguiente ➡️</button>
                            </div>
                        </div>
                        <div style="overflow-x: auto; max-height: 250px;">
                            <table class="excel-table-preview" id="cat-excel-preview-table">
                                <thead id="cat-excel-preview-thead"></thead>
                                <tbody id="cat-excel-preview-tbody"></tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div id="cat-loader-zona" class="loader-container">
                    <div class="spinner-wrapper">
                        <div class="spinner-circle"></div>
                        <div id="cat-spinner-percentage" class="spinner-percentage">0%</div>
                    </div>
                    <div id="cat-loader-mensaje" style="font-weight:800; color:#0f172a; font-size:16px;">Analizando inventario y cargando fotos...</div>
                </div>

                <button onclick="generarCatalogoERP(event)" style="background: #8b5cf6; width: 100%; margin-top: 10px; padding: 16px; font-size: 16px; font-weight:800; color:white; border:none; border-radius:8px; cursor:pointer;">
                    🪄 Generar Catálogo Oficial HTML
                </button>

                <div id="cat-resultado" class="log-box" style="display:none; text-align:center; padding:30px; height: auto;">
                    <h2 style="color:#4ade80; margin:0;">✅ ¡Catálogo Generado Exitosamente!</h2>
                    <p style="color:#cbd5e1; margin-top:10px;">El sistema agrupó los productos por categoría de ML e integró las fotos. Listo para enviar por WhatsApp o guardar como PDF.</p>
                    <p id="cat-ruta-txt" style="color:white; font-weight:bold; font-size:14px; background:#1e293b; padding:10px; border-radius:6px; word-break: break-all; margin-top: 15px;"></p>
                </div>
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
                <button onclick="cerrarModalCategorias()" style="background:#64748b; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold;">Cancelar</button>
                <button onclick="confirmarYCargarInventario()" style="background:#16a34a; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold;">
                    🚀 Confirmar y Analizar Inventario
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
                <button onclick="cerrarModalMasivo()" style="background:#64748b; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold;">Cancelar</button>
                <button onclick="aplicarAtributosMasivos()" style="background:#7e22ce; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold;">🚀 Aplicar a Todo el Lote</button>
            </div>
        </div>
    </div>

    <!-- MODAL INDIVIDUAL DINÁMICO CONDENSADO -->
    <div id="modal-atributos" class="modal-overlay">
        <div class="modal-box">
            <h3 style="margin-bottom: 5px;">🛠️ Ficha Técnica (Vista Condensada)</h3>
            <p style="font-size:12px; color:#64748b; margin-top:0; margin-bottom:15px;">Solo te mostramos las características que Mercado Libre exige (*). Las demás están ocultas para agilizar tu trabajo.</p>
            <input type="hidden" id="modal-idx">
            <div id="modal-attr-dinamicos" class="modal-grid">
                <div style="text-align:center; padding:20px; color:#64748b;">⏳ Cargando ficha técnica de Mercado Libre...</div>
            </div>
            <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:20px;">
                <button onclick="cerrarModal()" style="background:#64748b; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold;">Cancelar</button>
                <button onclick="guardarAtributosModal()" style="background:#0284c7; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold;">💾 Guardar Ficha Técnica</button>
            </div>
        </div>
    </div>

    <!-- MODAL VISTA PREVIA DESCRIPCION FINAL -->
    <div id="modal-ver-descripcion" class="modal-overlay">
        <div class="modal-box" style="width: 750px;">
            <h3 style="color:#0f172a; margin-bottom: 5px; border-bottom: 2px solid #475569;">👁️ Vista Previa de la Descripción</h3>
            <p style="font-size:12px; color:#64748b; margin-top:0;">Así se verá el texto final publicado en Mercado Libre, incluyendo la ficha técnica ensamblada por el ERP.</p>
            
            <div id="desc-preview-text" style="background:#f8fafc; padding:20px; border:1px solid #cbd5e1; border-radius:8px; height: 350px; overflow-y:auto; font-family: monospace; font-size:12px; white-space: pre-wrap; color:#1e293b;">
            </div>
            
            <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:20px;">
                <button onclick="document.getElementById('modal-ver-descripcion').style.display='none'" style="background:#64748b; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold;">Cerrar Vista Previa</button>
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

        let datosVistaPreviaCat = [];
        let indiceHojaPreviewCat = 0;

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
            
            const selectMaestro = document.getElementById('cuenta-select');
            const selectCat = document.getElementById('cat-cuenta');
            
            selectMaestro.innerHTML = "";
            selectCat.innerHTML = "";

            cuentas.forEach(c => {
                selectMaestro.innerHTML += `<option value="${c.archivo}">${c.nombre} (${c.archivo})</option>`;
                selectCat.innerHTML += `<option value="${c.archivo}">${c.nombre} (${c.archivo})</option>`;
            });
            
            if (cuentas.length > 1) {
                selectMaestro.innerHTML += `<option value="TODAS" style="font-weight:bold; color:#0369a1;">🚀 PUBLICAR EN TODAS (Inteligente)</option>`;
            }
        };

        // ==========================================
        // FUNCIONES MAESTRO DE LOTES
        // ==========================================
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

        // ==========================================
        // AGRUPADOR Y DOBLE CHECKBOX
        // ==========================================
        function toggleCatGrupo(clase) {
            document.querySelectorAll('.' + clase).forEach(el => {
                el.style.display = (el.style.display === 'none') ? 'table-row' : 'none';
            });
        }

        function toggleCategory(event, checkbox) {
            event.stopPropagation(); // Evitar que el clic cierre el acordeon
            const targetClass = checkbox.getAttribute('data-target');
            document.querySelectorAll('.' + targetClass + ' .prod-check').forEach(cb => {
                cb.checked = checkbox.checked;
            });
        }

        function toggleAll(source) {
            // Selecciona tanto los productos como los checks maestros de categoría
            document.querySelectorAll('.prod-check, .cat-header input[type="checkbox"]').forEach(cb => cb.checked = source.checked);
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
                        document.getElementById('desc-init-'+idx).value = descripcionesCSV[skuVal] || descripcionesCSV[titVal];
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
                if (colorVal) {
                    if (!atributosAdicionalesPorFila[idx]) atributosAdicionalesPorFila[idx] = {};
                    atributosAdicionalesPorFila[idx]["COLOR"] = colorVal;
                }
                if (compatVal) {
                    if (!atributosAdicionalesPorFila[idx]) atributosAdicionalesPorFila[idx] = {};
                    atributosAdicionalesPorFila[idx]["COMPATIBLE_MODELS"] = compatVal;
                }
                if (matVal) {
                    if (!atributosAdicionalesPorFila[idx]) atributosAdicionalesPorFila[idx] = {};
                    atributosAdicionalesPorFila[idx]["MATERIAL"] = matVal;
                }

                actualizarResumenAtributos(idx);
                count++;
            });

            cerrarModalMasivo();
            alert(`✅ Características aplicadas masivamente a ${count} artículos.`);
        }

        function obtenerValorGuardado(att, attrAdic, attrBase) {
            if (attrAdic[att.id] !== undefined) return attrAdic[att.id];
            for (const [k, val] of Object.entries(attrAdic)) {
                if (String(k).toUpperCase() === String(att.id).toUpperCase()) return val;
                if (String(k).toLowerCase() === String(att.name).toLowerCase()) return val;
            }
            const idNorm = String(att.id).toUpperCase();
            const nomNorm = String(att.name).toLowerCase();
            if ((idNorm === "COLOR" || nomNorm.includes("color")) && attrBase.color) return attrBase.color;
            if ((idNorm === "COMPATIBLE_MODELS" || idNorm === "LINE" || nomNorm.includes("compatib")) && attrBase.compatibilidad) return attrBase.compatibilidad;
            if ((idNorm === "MATERIAL" || nomNorm.includes("material")) && attrBase.material) return attrBase.material;
            return "";
        }

        // ==========================================
        // MODAL VISTA PREVIA DESCRIPCION FINAL
        // ==========================================
        function verDescripcion(idx) {
            const titulo = document.getElementById('tit-'+idx).value;
            const marca = document.getElementById('mar-'+idx).value || 'Genérico';
            const modelo = document.getElementById('mod-'+idx).value || 'Universal';
            const descCustom = document.getElementById('desc-init-'+idx).value;
            
            let bloqueTecnico = "========================================\\n";
            bloqueTecnico += "ESPECIFICACIONES TÉCNICAS Y CARACTERÍSTICAS\\n";
            bloqueTecnico += "========================================\\n";
            bloqueTecnico += `• MARCA: ${marca}\\n`;
            bloqueTecnico += `• MODELO: ${modelo}\\n`;
            
            const adic = atributosAdicionalesPorFila[idx] || {};
            for (const [k, v] of Object.entries(adic)) {
                let claveLimpia = k.replace(/_/g, ' ');
                bloqueTecnico += `• ${claveLimpia}: ${v}\\n`;
            }
            bloqueTecnico += "========================================\\n\\n";

            const BLOQUE_SUPERIOR = "SOMOS TIENDA FÍSICA, Empresa Mayorista Líder en el Mercado de la Computación Producto 100% de calidad";
            const BLOQUE_INFERIOR = ".\\nPor Favor Verifique la disponibilidad antes de ofertar\\nPor Favor Verifique la disponibilidad antes de ofertar\\nPor Favor Verifique la disponibilidad antes de ofertar\\n**************************************************************************************************\\n- Emitimos factura LEGAL\\n- Trabajamos con agentes de retención\\n- Enviamos a todo el País.\\n**************************************************************************************************\\nCOMENTARIOS:\\n- Realice todas las preguntas necesarias Antes de ofertar.\\n- El equipo de ventas está a tu disposición para responder tus consultas.\\n- Te invitamos a que solo ofertes cuando estés seguro de realizar la compra.\\n- La disponibilidad y precio del producto publicado solo se garantiza por un lapso de 24hrs luego de haber solicitado la compra.\\n- Si presentas algún inconveniente durante el proceso de compras estaremos a tu completa disposición para atenderte y solventar la situación. Deseamos que tu compra con nosotros siempre genere una calificación positiva.\\n****************************************************************************************************\\nHORARIO DE TRABAJO\\n****************************************************\\nDe Lunes A Viernes\\nDe 8:30am A 5:30pm";

            let descFinal = `${BLOQUE_SUPERIOR}\\n\\n`;
            descFinal += `${titulo}\\n${titulo}\\n${titulo}\\n\\n`;
            
            if (descCustom && descCustom.trim().length > 5) {
                descFinal += `${descCustom}\\n\\n`;
            }
            
            descFinal += bloqueTecnico;
            descFinal += BLOQUE_INFERIOR;

            document.getElementById('desc-preview-text').innerText = descFinal;
            document.getElementById('modal-ver-descripcion').style.display = 'flex';
        }

        // ==========================================
        // MODAL DE CARACTERISTICAS CONDENSADO
        // ==========================================
        async function abrirModal(idx) {
            document.getElementById('modal-idx').value = idx;
            document.getElementById('modal-atributos').style.display = 'flex';
            
            const contenedor = document.getElementById('modal-attr-dinamicos');
            contenedor.innerHTML = '<div style="text-align:center; padding:20px; color:#0284c7; font-weight:bold;">⏳ Consultado atributos requeridos en Mercado Libre...</div>';
            
            const catId = document.getElementById('cat-'+idx).value;
            const attrBase = atributosPorFila[idx] || {};
            const attrAdic = atributosAdicionalesPorFila[idx] || {};

            try {
                const res = await fetch(`/api/atributos-categoria/${catId}`);
                const listaAttrML = await res.json();

                let htmlContent = `
                    <div style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; background: #e0f2fe; padding: 12px; border-radius: 8px; border: 1px solid #7dd3fc;">
                        <span style="font-size: 13px; font-weight: 800; color: #0369a1;">🤖 Relleno Inteligente de Ficha Técnica</span>
                        <button type="button" onclick="ejecutarAutollenadoIA(${idx}, this)" style="background: #0284c7; font-size: 11px; padding: 6px 14px; color:white; border:none; border-radius:6px; cursor:pointer;">
                            ⚡ Autollenar con IA
                        </button>
                    </div>
                    <div class="modal-field">
                        <label>Marca: <span style="color:#ef4444; font-weight:bold;" title="Obligatorio">*</span></label>
                        <input type="text" id="m-mar" value="${attrBase.marca || ''}">
                    </div>
                    <div class="modal-field">
                        <label>Modelo: <span style="color:#ef4444; font-weight:bold;" title="Obligatorio">*</span></label>
                        <input type="text" id="m-mod" value="${attrBase.modelo || ''}">
                    </div>
                `;

                let htmlReq = "";
                let htmlOpt = "";
                let countOpt = 0;

                listaAttrML.forEach(att => {
                    const vGuardado = obtenerValorGuardado(att, attrAdic, attrBase);
                    let controlHTML = "";

                    if (att.values && att.values.length > 0) {
                        let optionsHTML = "";
                        att.values.forEach(valML => {
                            optionsHTML += `<option value="${valML.name}">`;
                        });

                        controlHTML = `
                            <input type="text" list="dl-${att.id}" id="m-txt-${att.id}" value="${vGuardado}" placeholder="Elige de la lista o escribe una opción libre...">
                            <datalist id="dl-${att.id}">
                                ${optionsHTML}
                            </datalist>
                        `;
                    } else {
                        controlHTML = `<input type="text" id="m-txt-${att.id}" value="${vGuardado}" placeholder="Ej: ${att.hint || 'Valor'}">`;
                    }

                    const isReq = att.required;
                    const asterisco = isReq ? '<span style="color:#ef4444; font-weight:bold;" title="Obligatorio">*</span>' : '';
                    
                    const bloqueHTML = `
                        <div class="modal-field">
                            <label>${att.name} ${asterisco} <span style="font-weight:normal; color:#64748b; font-size:10px;">(${att.value_type})</span></label>
                            ${controlHTML}
                        </div>
                    `;

                    if (isReq) {
                        htmlReq += bloqueHTML;
                    } else {
                        htmlOpt += bloqueHTML;
                        countOpt++;
                    }
                });

                htmlContent += htmlReq;

                if (countOpt > 0) {
                    htmlContent += `
                        <div style="margin-top: 15px; border-top: 1px dashed #cbd5e1; padding-top: 15px;">
                            <button type="button" onclick="document.getElementById('opt-attrs').style.display='flex'; this.style.display='none';" style="background: #f8fafc; color: #475569; border: 1px solid #cbd5e1; width: 100%; padding: 10px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: bold;">
                                + Mostrar ${countOpt} características opcionales (Avanzado)
                            </button>
                            <div id="opt-attrs" style="display: none; flex-direction: column; gap: 14px; margin-top: 10px;">
                                ${htmlOpt}
                            </div>
                        </div>
                    `;
                }

                contenedor.innerHTML = htmlContent;

            } catch(e) {
                contenedor.innerHTML = '<div style="color:red; padding:20px;">❌ Error conectando a los atributos oficiales de Mercado Libre.</div>';
            }
        }

        async function ejecutarAutollenadoIA(idx, btn) {
            const titVal = document.getElementById('tit-'+idx).value;
            const catId = document.getElementById('cat-'+idx).value;
            const skuVal = document.getElementById('sku-'+idx).value;

            const formData = new FormData();
            formData.append('titulo', titVal);
            formData.append('cat_id', catId);
            formData.append('sku', skuVal);

            const textOrig = btn.innerText;
            btn.innerText = "⏳ Analizando...";
            btn.disabled = true;

            try {
                const res = await fetch('/api/autollenar-atributos-ia', { method: 'POST', body: formData });
                const data = await res.json();

                if (data.atributos) {
                    if (!atributosAdicionalesPorFila[idx]) atributosAdicionalesPorFila[idx] = {};
                    
                    for (const [idAttr, valIA] of Object.entries(data.atributos)) {
                        const idUpper = String(idAttr).trim ? String(idAttr).trim().toUpperCase() : String(idAttr).toUpperCase();
                        atributosAdicionalesPorFila[idx][idUpper] = valIA;
                        
                        const inputCampo = document.getElementById(`m-txt-${idUpper}`);
                        if (inputCampo) {
                            inputCampo.value = valIA;
                            inputCampo.style.backgroundColor = "#dcfce7";
                        }
                    }

                    if (data.descripcion && data.descripcion.trim() !== "") {
                        document.getElementById('desc-init-'+idx).value = data.descripcion;
                        const badge = document.getElementById('desc-tag-'+idx);
                        badge.innerText = "✨ Desc. IA Generada";
                        badge.style.backgroundColor = "#fef08a";
                        badge.style.color = "#854d0e";
                    }

                    actualizarResumenAtributos(idx);
                } else if (data.error) {
                    alert("Error de IA: " + data.error);
                }
            } catch(e) {
                alert("No se pudieron autollenar algunos atributos.");
            } finally {
                btn.innerText = textOrig;
                btn.disabled = false;
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
                const idAttrML = inp.id.replace('m-txt-', '').toUpperCase();
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
                info += ` | ⚡ +${totalDinamicos} características agregadas`;
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
                    if (e.target.result && typeof e.target.result === 'string' && e.target.result.startsWith('data:image/')) {
                        imagenesPorFila[idx].push(e.target.result);
                        renderizarGaleriaFila(idx);
                    }
                };
                reader.readAsDataURL(file);
            }
        }

        function renderizarGaleriaFila(idx) {
            const previewArea = document.getElementById(`prev-${idx}`);
            previewArea.innerHTML = "";
            imagenesPorFila[idx] = (imagenesPorFila[idx] || []).filter(img => img && typeof img === 'string' && img.startsWith('data:image/'));
            imagenesPorFila[idx].forEach((b64, pos) => {
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
        
        function applyingExpo() {
            const expoVal = document.getElementById('bulk-exposicion').value;
            document.querySelectorAll('.select-exposicion').forEach(sel => sel.value = expoVal);
        }

        function aplicarExposicionMasiva() {
            const expoVal = document.getElementById('bulk-exposicion').value;
            document.querySelectorAll('.select-exposicion').forEach(sel => sel.value = expoVal);
        }

        function applyingEnv() {
            const envioVal = document.getElementById('bulk-envio').value;
            document.querySelectorAll('.select-envio').forEach(sel => sel.value = envioVal);
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

        // ==========================================
        // REPORTE DE AUDITORÍA Y CARGA DE INVENTARIO
        // ==========================================
        async function confirmarYCargarInventario() {
            cerrarModalCategorias();
            const idCatDefecto = document.getElementById('cat-seleccionada-id').value;
            const fileInput = document.getElementById('file-db');

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('cuenta', document.getElementById('cuenta-select').value);
            formData.append('hoja', document.getElementById('hoja-select').value);
            formData.append('inicio', document.getElementById('rango-inicio').value);
            formData.append('fin', document.getElementById('rango-fin').value);
            formData.append('categoria_filtro', idCatDefecto);
            formData.append('filtrar_duplicados', document.getElementById('filtar-duplicados').checked);

            formData.append('col_tit', document.getElementById('map-tit').value);
            formData.append('col_sku', document.getElementById('map-sku').value);
            formData.append('col_mod', document.getElementById('map-mod').value);
            formData.append('col_pre', document.getElementById('map-pre').value);
            formData.append('col_stk', document.getElementById('map-stk').value);

            document.getElementById('tabla-container').style.display = 'none';
            document.getElementById('resumen-reporte-box').style.display = 'none';
            document.getElementById('loader-zona').style.display = 'block';
            document.getElementById('spinner-percentage').innerText = "0%";
            document.getElementById('loader-mensaje').innerText = "Iniciando sincronización...";
            
            iniciarMonitoreoProgreso();
            
            const consola = document.getElementById('resultados');
            consola.innerText = `⏳ Sincronizando inventario con filtro: [${idCatDefecto}]...`;

            try {
                const response = await fetch('/previsualizar', { method: 'POST', body: formData });
                const resultado = await response.json();

                if (resultado.error) return consola.innerText = "❌ " + resultado.error;

                const tbody = document.getElementById('tabla-body');
                tbody.innerHTML = "";

                const agrupados = {};
                resultado.productos.forEach((prod, idx) => {
                    const cName = prod.CategoriaNombre || 'Sin Categoría';
                    if (!agrupados[cName]) agrupados[cName] = { id: prod.Categoria_ID, items: [] };
                    agrupados[cName].items.push({prod, idx});
                });

                for (const [catName, data] of Object.entries(agrupados)) {
                    const catIdClase = 'cat-grp-' + data.id.replace(/[^a-zA-Z0-9]/g, '');
                    
                    tbody.innerHTML += `
                        <tr class="cat-header" style="background: #e2e8f0; border-bottom: 2px solid #cbd5e1;">
                            <td style="padding: 12px; width: 30px;">
                                <input type="checkbox" checked title="Seleccionar toda la categoría" data-target="${catIdClase}" onclick="toggleCategory(event, this)">
                            </td>
                            <td colspan="6" onclick="toggleCatGrupo('${catIdClase}')" style="padding: 12px; font-size: 14px; cursor: pointer;">
                                <span style="font-size:16px;">📂</span> 
                                <b style="color: #0f172a;">${catName}</b> 
                                <span style="color: #64748b; font-size: 12px;">(${data.items.length} artículos) - Clic para expandir / contraer</span>
                            </td>
                        </tr>
                    `;

                    data.items.forEach(obj => {
                        const prod = obj.prod;
                        const idx = obj.idx;

                        imagenesPorFila[idx] = [];
                        if (prod.ImagenLocal && typeof prod.ImagenLocal === 'string' && prod.ImagenLocal.startsWith('data:image/')) {
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

                        // Formatear precio estricto a 2 decimales para la UI
                        const precioFormateado = parseFloat(prod.Precio || 0).toFixed(2);

                        tbody.innerHTML += `
                            <tr id="row-${idx}" class="item-row ${catIdClase}">
                                <td><input type="checkbox" class="prod-check" data-idx="${idx}" checked></td>
                                <td>
                                    <input type="text" id="tit-${idx}" value="${prod.Titulo}" maxlength="60" style="margin-bottom:4px; font-weight:bold;">
                                    <div class="cat-tag" title="ID: ${prod.Categoria_ID}">📌 ML: ${prod.CategoriaNombre}</div>
                                    <div id="desc-tag-${idx}" class="desc-tag">📋 Plantilla Oficial (Título x3)</div>
                                    <div style="font-size:11px; color:#64748b; margin-top:2px;">📁 Hoja: <b>${prod.Hoja}</b></div>
                                    <div style="margin-top:6px;">${badgesHTML}</div>
                                    <input type="hidden" id="cat-${idx}" value="${prod.Categoria_ID}">
                                    <input type="hidden" id="desc-init-${idx}" value="${prod.DescripcionCustom || ''}">
                                </td>
                                <td><input type="number" id="pre-${idx}" value="${precioFormateado}" step="0.01"></td>
                                <td><input type="number" id="stk-${idx}" value="${prod.Stock}"></td>
                                <td>
                                    <select id="expo-${idx}" class="select-exposicion attr-select" style="margin-bottom:5px; font-weight:bold;">
                                        <option value="bronze">Bronce / Estándar</option>
                                        <option value="gold_special">Clásica</option>
                                        <option value="gold_pro">Premium</option>
                                    </select>
                                    <select id="envio-${idx}" class="select-envio attr-select" style="font-size:11px; font-weight:bold;">
                                        <option value="me2_free">🟢 Envío Gratis</option>
                                        <option value="custom_free">🟢 Envío Gratis (Custom)</option>
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
                                    
                                    <button type="button" onclick="abrirModal(${idx})" style="background:#0284c7; width:100%; padding:6px; font-size:11px; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; margin-bottom: 4px;">
                                        ⚡ Llenar Ficha Técnica (Obligatorios)
                                    </button>
                                    <button type="button" onclick="verDescripcion(${idx})" style="background:#475569; width:100%; padding:6px; font-size:11px; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">
                                        👁️ Ver Descripción Final
                                    </button>
                                    
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
                }

                // PANEL DE REPORTE
                const repBox = document.getElementById('resumen-reporte-box');
                document.getElementById('texto-resumen-reporte').innerHTML = `
                    <b>📊 Reporte de Auditoría de Inventario:</b><br>
                    • Se escanearon <b>${resultado.total_leidos}</b> artículos en el rango de filas seleccionado.<br>
                    • <b>${resultado.total_aprobados}</b> artículos pasaron los filtros y están listos para ser publicados.<br>
                    • <b style="color:#b91c1c;">${resultado.total_omitidos}</b> artículos fueron ignorados (por duplicidad, falta de título, o porque no coinciden con la categoría).<br><br>
                    <a href="/api/descargar-reporte/${resultado.archivo_reporte}" target="_blank" style="background:#166534; color:white; padding:8px 16px; border-radius:6px; font-weight:bold; text-decoration:none; display:inline-block;">📥 Descargar Reporte Completo en Excel</a>
                `;
                repBox.style.display = 'block';
                document.getElementById('tabla-container').style.display = 'block';
                
                consola.innerHTML = `✅ Sincronización completa. Revisa el reporte arriba.`;
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

        async function ejecutarPublicacion() {
            // Limpiar errores previos visuales
            document.querySelectorAll('.item-row').forEach(row => {
                row.style.border = "";
                row.style.backgroundColor = "";
            });

            const seleccionados = [];
            document.querySelectorAll('.prod-check:checked').forEach(cb => {
                const idx = cb.dataset.idx;
                const attr = atributosPorFila[idx];
                const adic = atributosAdicionalesPorFila[idx] || {};
                const razonGtin = document.getElementById('gtin-razon-'+idx).value;
                let gtinFinal = (razonGtin === 'CUSTOM') ? document.getElementById('gtin-'+idx).value : 'OMITIR';

                // Forzar 2 decimales limpios antes de enviar
                let precioLimpio = parseFloat(document.getElementById('pre-'+idx).value || 0).toFixed(2);

                seleccionados.push({
                    "idx": idx,
                    "Titulo": document.getElementById('tit-'+idx).value,
                    "Precio": parseFloat(precioLimpio),
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

                if (resData.errores_idx && Object.keys(resData.errores_idx).length > 0) {
                    let fallos = 0;
                    for (const [idxError, errorMsg] of Object.entries(resData.errores_idx)) {
                        const fila = document.getElementById('row-' + idxError);
                        if(fila) {
                            fila.style.borderLeft = "6px solid #ef4444";
                            fila.style.backgroundColor = "#fef2f2";
                        }
                        
                        const resumenDiv = document.getElementById('resumen-attr-'+idxError);
                        resumenDiv.innerHTML = `
                            <div style="background:#fee2e2; border:1px solid #fca5a5; padding:6px; border-radius:6px; margin-top:6px;">
                                <span style="color:#b91c1c; font-weight:bold; font-size:11px;">❌ ${errorMsg}</span><br>
                                <button onclick="ejecutarAutollenadoIA(${idxError}, this)" style="background:#b91c1c; color:white; border:none; padding:4px 8px; border-radius:4px; font-size:10px; cursor:pointer; margin-top:6px; font-weight:bold;">
                                    🤖 Corregir Errores con IA
                                </button>
                            </div>
                        `;
                        fallos++;
                    }
                    alert(`Hubo errores con ${fallos} artículos. Han sido resaltados en color rojo en tu panel para que uses la corrección IA.`);
                } else {
                    alert("¡Todo el lote se publicó de forma perfecta sin errores!");
                }

            } catch(e) {
                consola.innerText = "❌ Error subiendo lote: " + e;
            } finally {
                if (intervaloProgreso) clearInterval(intervaloProgreso);
                setTimeout(() => { document.getElementById('loader-zona').style.display = 'none'; }, 500);
            }
        }

        // ==========================================
        // FUNCIONES CATÁLOGO (PREMIUM)
        // ==========================================
        async function detectarHojasCat(inputElement) {
            const file = inputElement.files[0];
            const selectHoja = document.getElementById('cat-hoja-select');
            if (!file) return;

            selectHoja.innerHTML = '<option value="TODAS">⏳ Detectando pestañas...</option>';
            const formData = new FormData();
            formData.append('file', file);

            try {
                const res = await fetch('/api/vista-previa-excel', { method: 'POST', body: formData });
                const data = await res.json();
                
                datosVistaPreviaCat = data.vistas || [];
                selectHoja.innerHTML = '<option value="TODAS">📚 Todo el Libro (Todas las Hojas)</option>';
                datosVistaPreviaCat.forEach(item => {
                    selectHoja.innerHTML += `<option value="${item.nombre}">📄 ${item.nombre}</option>`;
                });
                cambiarHojaSeleccionadaCat();
            } catch(e) {
                selectHoja.innerHTML = '<option value="TODAS">📚 Todo el Libro (Todas las Hojas)</option>';
            }
        }

        function cambiarHojaSeleccionadaCat() {
            const val = document.getElementById('cat-hoja-select').value;
            if (val === "TODAS") {
                indiceHojaPreviewCat = 0;
            } else {
                const idx = datosVistaPreviaCat.findIndex(item => item.nombre === val);
                indiceHojaPreviewCat = (idx >= 0) ? idx : 0;
            }
            renderizarVistaPreviaExcelCat(val === "TODAS");
            poblarSelectoresMapeoCat(indiceHojaPreviewCat);
        }

        function cambiarHojaPreviewCat(delta) {
            const total = datosVistaPreviaCat.length;
            if (total === 0) return;
            indiceHojaPreviewCat = (indiceHojaPreviewCat + delta + total) % total;
            renderizarVistaPreviaExcelCat(true);
            poblarSelectoresMapeoCat(indiceHojaPreviewCat);
        }

        function renderizarVistaPreviaExcelCat(esTodas) {
            if (!datosVistaPreviaCat.length) return;
            const vista = datosVistaPreviaCat[indiceHojaPreviewCat];
            const thead = document.getElementById('cat-excel-preview-thead');
            const tbody = document.getElementById('cat-excel-preview-tbody');
            const title = document.getElementById('cat-excel-preview-title');
            const nav = document.getElementById('cat-excel-preview-nav');
            const count = document.getElementById('cat-excel-preview-counter');
            
            title.innerHTML = `📊 Vista Previa de Datos a Exportar — <b>Hoja: ${vista.nombre}</b>`;
            if (esTodas && datosVistaPreviaCat.length > 1) {
                nav.style.display = 'flex';
                count.innerText = `Hoja ${indiceHojaPreviewCat + 1} de ${datosVistaPreviaCat.length}`;
            } else {
                nav.style.display = 'none';
            }

            thead.innerHTML = "";
            tbody.innerHTML = "";
            if (!vista.filas || !vista.filas.length) return;

            const f0 = vista.filas[0];
            let trH = "<tr><th>#</th>";
            f0.forEach((cell, i) => { trH += `<th>Col ${i+1}: ${cell}</th>`; });
            trH += "</tr>";
            thead.innerHTML = trH;

            for (let r = 1; r < Math.min(10, vista.filas.length); r++) {
                const fila = vista.filas[r];
                let trB = `<tr><td><b>Fila ${r}</b></td>`;
                f0.forEach((_, cIdx) => { trB += `<td>${fila[cIdx] || ""}</td>`; });
                trB += "</tr>";
                tbody.innerHTML += trB;
            }
            document.getElementById('cat-mapping-bar').style.display = 'block';
        }

        function poblarSelectoresMapeoCat(idxHoja) {
            if (!datosVistaPreviaCat[idxHoja] || !datosVistaPreviaCat[idxHoja].filas.length) return;
            const filas = datosVistaPreviaCat[idxHoja].filas;
            const palabrasClave = ["codigo", "código", "sku", "producto", "descripcion", "descripción", "precio", "marca", "categoria", "nombre", "stock", "modelo", "linea", "garantia", "pvp", "$"];
            let mejorFila = 0, maxCoincidencias = -1;
            
            for (let r = 0; r < Math.min(10, filas.length); r++) {
                let coincidencias = 0, celdasLlenas = 0;
                filas[r].forEach(celda => {
                    const txt = String(celda || "").toLowerCase().trim();
                    if (txt && txt !== "nan" && txt !== "undefined") {
                        celdasLlenas++;
                        if (palabrasClave.some(p => txt.includes(p))) coincidencias += 3;
                    }
                });
                const puntuacion = coincidencias + (celdasLlenas * 0.5);
                if (puntuacion > maxCoincidencias && celdasLlenas >= 2) {
                    maxCoincidencias = puntuacion; mejorFila = r;
                }
            }

            const fPpal = filas[mejorFila] || [];
            const fSig = (mejorFila + 1 < filas.length) ? (filas[mejorFila + 1] || []) : [];
            const totalCols = Math.max(fPpal.length, fSig.length);
            const selects = ['cat-map-tit', 'cat-map-sku', 'cat-map-mod', 'cat-map-pre', 'cat-map-stk'];
            
            selects.forEach(id => {
                const el = document.getElementById(id);
                if (!el) return;
                el.innerHTML = '<option value="">-- Automático --</option>';
                for (let c = 0; c < totalCols; c++) {
                    let nom1 = String(fPpal[c] || "").trim();
                    let nom2 = String(fSig[c] || "").trim();
                    if (nom1.toLowerCase() === "nan" || nom1.toLowerCase() === "undefined") nom1 = "";
                    if (nom2.toLowerCase() === "nan" || nom2.toLowerCase() === "undefined") nom2 = "";

                    let etiquetaCol = "", valorCol = "";
                    if (nom1 && nom2 && palabrasClave.some(p => nom2.toLowerCase().includes(p))) {
                        valorCol = `${nom1} ${nom2}`; etiquetaCol = `Col ${c + 1}: ${nom1} ${nom2}`;
                    } else if (nom1) {
                        valorCol = nom1; etiquetaCol = `Col ${c + 1}: ${nom1}`;
                    } else if (nom2) {
                        valorCol = nom2; etiquetaCol = `Col ${c + 1}: ${nom2}`;
                    } else {
                        valorCol = `Col_${c + 1}`; etiquetaCol = `Col ${c + 1} (Sin nombre)`;
                    }
                    el.innerHTML += `<option value="${valorCol}">${etiquetaCol}</option>`;
                }
            });
        }

        async function generarCatalogoERP(event) {
            const file = document.getElementById('cat-file').files[0];
            const empresa = document.getElementById('cat-empresa').value;
            const ws = document.getElementById('cat-ws').value;

            if (!file) return alert("Por favor sube el archivo Excel Maestro en el Paso 2.");
            if (!ws) return alert("El número de WhatsApp es obligatorio para que funcionen los botones de compra.");

            const btn = event.target;
            const textOriginal = btn.innerHTML;
            btn.innerHTML = '⏳ Escaneando Inventario, ML y Procesando Fotos...';
            btn.disabled = true;

            const fd = new FormData();
            fd.append('file', file);
            fd.append('cuenta', document.getElementById('cat-cuenta').value);
            fd.append('hoja', document.getElementById('cat-hoja-select').value);
            fd.append('inicio', document.getElementById('cat-rango-inicio').value);
            fd.append('fin', document.getElementById('cat-rango-fin').value);
            fd.append('nombre_empresa', empresa || 'Mi Empresa');
            fd.append('whatsapp', ws);
            
            fd.append('col_tit', document.getElementById('cat-map-tit').value);
            fd.append('col_sku', document.getElementById('cat-map-sku').value);
            fd.append('col_mod', document.getElementById('cat-map-mod').value);
            fd.append('col_pre', document.getElementById('cat-map-pre').value);
            fd.append('col_stk', document.getElementById('cat-map-stk').value);

            document.getElementById('cat-loader-zona').style.display = 'block';
            document.getElementById('cat-spinner-percentage').innerText = "0%";
            document.getElementById('cat-loader-mensaje').innerText = "Iniciando generación de catálogo...";
            
            if (intervaloProgreso) clearInterval(intervaloProgreso);
            intervaloProgreso = setInterval(async () => {
                try {
                    const res = await fetch('/estado-progreso');
                    const info = await res.json();
                    document.getElementById('cat-spinner-percentage').innerText = info.porcentaje + "%";
                    document.getElementById('cat-loader-mensaje').innerText = info.mensaje;
                    if (!info.activo && info.porcentaje >= 100) clearInterval(intervaloProgreso);
                } catch(e) {}
            }, 250);

            try {
                const res = await fetch('/api/generar-catalogo', { method: 'POST', body: fd });
                const data = await res.json();
                
                if (data.error) {
                    alert("Error: " + data.error);
                } else {
                    document.getElementById('cat-resultado').style.display = 'block';
                    document.getElementById('cat-ruta-txt').innerText = "📂 Localizado en: " + data.ruta;
                }
            } catch(e) {
                alert("Ocurrió un error de red al generar el catálogo.");
            } finally {
                btn.innerHTML = textOriginal;
                btn.disabled = false;
                if (intervaloProgreso) clearInterval(intervaloProgreso);
                document.getElementById('cat-loader-zona').style.display = 'none';
            }
        }

        async function autollenarLoteIA() {
            const checks = document.querySelectorAll('.prod-check:checked');
            if (!checks.length) return alert('No hay artículos seleccionados para analizar.');
            
            if (!confirm(`¿Iniciar análisis IA para ${checks.length} artículos? Generará fichas y descripciones comerciales.`)) return;

            const btn = document.getElementById('btn-bulk-ia');
            const textoOriginal = btn.innerHTML;
            btn.innerHTML = '⏳ Procesando Lote con IA...';
            btn.disabled = true;

            for (let i = 0; i < checks.length; i++) {
                const idx = checks[i].dataset.idx;
                const titVal = document.getElementById('tit-'+idx).value;
                const catId = document.getElementById('cat-'+idx).value;
                const skuVal = document.getElementById('sku-'+idx).value;
                const resumenDiv = document.getElementById('resumen-attr-'+idx);

                resumenDiv.innerHTML = "⏳ <b>DeepSeek analizando...</b>";
                
                const fd = new FormData();
                fd.append('titulo', titVal);
                fd.append('cat_id', catId);
                fd.append('sku', skuVal);

                try {
                    const res = await fetch('/api/autollenar-atributos-ia', { method: 'POST', body: fd });
                    const data = await res.json();

                    if (data.atributos) {
                        if (!atributosAdicionalesPorFila[idx]) atributosAdicionalesPorFila[idx] = {};
                        for (const [idAttr, valIA] of Object.entries(data.atributos)) {
                            const idUpper = String(idAttr).trim().toUpperCase();
                            atributosAdicionalesPorFila[idx][idUpper] = valIA;
                        }

                        if (data.descripcion && data.descripcion.trim() !== "") {
                            document.getElementById('desc-init-'+idx).value = data.descripcion;
                            const badge = document.getElementById('desc-tag-'+idx);
                            badge.innerText = "✨ Desc. IA Generada";
                            badge.style.backgroundColor = "#fef08a";
                            badge.style.color = "#854d0e";
                        }

                        actualizarResumenAtributos(idx);
                    } else if (data.error) {
                        resumenDiv.innerHTML = `❌ <span style="color:red;">Error: ${data.error}</span>`;
                    }
                } catch(e) {
                    resumenDiv.innerText = "❌ Fallo de red con la IA";
                }
                
                await new Promise(r => setTimeout(r, 800));
            }

            btn.innerHTML = textoOriginal;
            btn.disabled = false;
            alert("✅ ¡Autollenado masivo completado con éxito!");
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
def obtener_hojas_excel(file: UploadFile = File(...)):
    temp_filename = f"temp_sheets_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        buffer.write(file.file.read())
    
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
def endpoint_columnas_excel(file: UploadFile = File(...), hoja: str = Form("TODAS")):
    temp_filename = f"temp_cols_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        buffer.write(file.file.read())
    
    columnas = obtener_encabezados_excel(temp_filename, hoja_objetivo=hoja)
    time.sleep(0.1)
    if os.path.exists(temp_filename):
        try: os.remove(temp_filename)
        except PermissionError: pass
    return columnas

@app.post("/api/vista-previa-excel")
def endpoint_vista_previa_excel(file: UploadFile = File(...)):
    temp_filename = f"temp_preview_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        buffer.write(file.file.read())
    
    vistas = obtener_vista_previa_excel(temp_filename)
    time.sleep(0.1)
    if os.path.exists(temp_filename):
        try: os.remove(temp_filename)
        except PermissionError: pass
    return {"vistas": vistas}

@app.get("/api/atributos-categoria/{cat_id}")
def endpoint_atributos_categoria(cat_id: str):
    try:
        url = f"{API_ML}/categories/{cat_id}/attributes"
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            attrs = res.json()
            relevantes = []
            PROHIBIDOS = {"BRAND", "MODEL", "SELLER_SKU", "PART_NUMBER", "GTIN", "ITEM_CONDITION", "HAS_COMPATIBILITIES"}
            for att in attrs:
                aid = att.get("id")
                if aid not in PROHIBIDOS and not att.get("read_only", False):
                    es_requerido = att.get("tags", {}).get("required", False)
                    relevantes.append({
                        "id": aid,
                        "name": att.get("name"),
                        "value_type": att.get("value_type", "string"),
                        "hint": att.get("hint", ""),
                        "values": att.get("values", [])[:20],
                        "required": es_requerido
                    })
            relevantes.sort(key=lambda x: not x["required"])
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

@app.post("/api/autollenar-atributos-ia")
def autollenar_atributos_ia(
    titulo: str = Form(...),
    cat_id: str = Form(...),
    sku: str = Form("")
):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return {"error": "Falta configurar OPENROUTER_API_KEY en tu archivo .env"}

    try:
        url_attr = f"{API_ML}/categories/{cat_id}/attributes"
        res_ml = requests.get(url_attr, timeout=6)
        if res_ml.status_code != 200:
            return {"error": "No se pudieron obtener los atributos de Mercado Libre."}

        attrs_ml = res_ml.json()
        prohibidos = {"BRAND", "MODEL", "SELLER_SKU", "PART_NUMBER", "GTIN", "ITEM_CONDITION", "HAS_COMPATIBILITIES"}
        
        relevantes = []
        for a in attrs_ml:
            if a.get("id") not in prohibidos and not a.get("read_only", False):
                es_requerido = a.get("tags", {}).get("required", False)
                relevantes.append({
                    "id": a.get("id"),
                    "name": a.get("name"),
                    "required": es_requerido
                })

        if not relevantes:
            return {"atributos": {}, "descripcion": ""}

        lista_obligatorios = [f"- {a['id']} ({a['name']})" for a in relevantes if a["required"]]
        lista_opcionales = [f"- {a['id']} ({a['name']})" for a in relevantes if not a["required"]][:12]

        texto_oblig = "\n".join(lista_obligatorios) if lista_obligatorios else "Ninguno estrictamente obligatorio."
        texto_opcio = "\n".join(lista_opcionales) if lista_opcionales else "Ninguno adicional."

        prompt = f"""Eres un experto catalogador y redactor de ventas para Mercado Libre.
Dado el siguiente producto tecnológico/electrónico:
- Título: "{titulo}"
- SKU / Número de Parte: "{sku}"

Tu tarea es doble:
1. Redactar una DESCRIPCIÓN COMERCIAL atractiva, persuasiva y detallada (aprox. 2 párrafos) que resalte los beneficios y usos del producto.
2. Extraer, deducir o investigar los atributos técnicos de Mercado Libre basándote en el Título, SKU y la descripción que acabas de idear.

Atributos OBLIGATORIOS (DEBES incluirlos en el JSON):
{texto_oblig}

Atributos OPCIONALES (inclúyelos SOLO si tienes información exacta):
{texto_opcio}

Reglas estrictas e inquebrantables:
1. Responde SOLO con un JSON válido. NADA de texto adicional (sin etiquetas de código).
2. El JSON debe contener la clave exacta "DESCRIPCION_COMERCIAL".
3. Las demás claves deben ser EXACTAMENTE el ID del atributo técnico.
4. OBLIGATORIOS: ¡Nunca vacíos! Si no sabes el dato, usa valores como "Genérico", "Universal", o "Estándar". (Nunca "N/A").
5. OPCIONALES: Si no sabes la información de un opcional, SIMPLEMENTE NO LO INCLUYAS en el JSON.
6. REGLA DE ORO PARA MEDIDAS: Todo atributo que represente capacidad, tamaño, longitud o frecuencia (RAM, disco duro, pantalla, Hz, voltaje) DEBE INCLUIR LA UNIDAD DE MEDIDA (ej. "8 GB", "1 TB", "15.6 pulgadas", "144 Hz", "110V"). NUNCA uses "No Aplica" o números solos como "15.6" en estos campos numéricos. Si el atributo es obligatorio y no sabes el valor, inventa un valor estándar realista de la industria en lugar de omitirlo o poner texto inválido.
"""

        headers_or = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "http://localhost:8080",
            "X-Title": "MLV ERP System",
            "Content-Type": "application/json"
        }
        
        payload_or = {
            "model": "deepseek/deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }

        url_openrouter = "https://" + "openrouter.ai/api/v1/chat/completions"
        res_or = requests.post(url_openrouter, headers=headers_or, json=payload_or, timeout=15)
        
        if res_or.status_code != 200:
            return {"error": f"Error API OpenRouter ({res_or.status_code})"}

        raw_text = res_or.json()["choices"][0]["message"]["content"].strip()
        
        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text.replace("```", "").strip()

        datos_ia = json.loads(raw_text)

        descripcion_ia = datos_ia.pop("DESCRIPCION_COMERCIAL", "")

        ids_validos = {a["id"] for a in relevantes}
        atributos_finales = {}
        for k, v in datos_ia.items():
            k_upper = str(k).strip().upper()
            if k_upper in ids_validos and v and str(v).strip() != "":
                atributos_finales[k_upper] = str(v).strip()

        return {"atributos": atributos_finales, "descripcion": descripcion_ia}

    except Exception as e:
        return {"error": f"Fallo en IA: {str(e)}"}

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
            
            url_me = f"{API_ML}/users/me"
            res = requests.get(url_me, headers=headers)
            
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
def previsualizar_archivo(
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
    with open(temp_filename, "wb") as buffer: 
        buffer.write(file.file.read())

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

    token_ref = obtener_token(archivos_a_escanear[0]) if archivos_a_escanear else None
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
        if os.path.exists(temp_filename): os.remove(temp_filename)
        return {"error": f"Error heurístico leyendo el archivo: {str(e)}"}

    idx_inicio = max(0, inicio - 1)
    filas_rango = filas_procesadas[idx_inicio:fin]
    total_filas = len(filas_rango)

    productos_activos = []
    cache_categorias_adivinadas = {}
    
    reporte_filas = []
    aprobados_count = 0
    omitidos_count = 0

    for indice, item in enumerate(filas_rango):
        time.sleep(0.01)
        porcentaje_actual = int(20 + ((indice + 1) / max(1, total_filas)) * 75)
        
        titulo = str(item.get("Titulo", "")).strip()
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

        sku = item.get("SKU", "")
        modelo = item.get("Modelo", "")
        
        # Redondear el precio a 2 decimales limpios
        try:
            precio = round(float(item.get("Precio", 0)), 2)
        except Exception:
            precio = 0.0

        stock = item.get("Stock", 0)
        marca = item.get("Marca", "")
        cat_origen = item.get("CategoriaOrigen", "")
        nom_hoja = item.get("Hoja", "")

        if headers_ref and titulo:
            if titulo in cache_categorias_adivinadas:
                cat_id, cat_nombre = cache_categorias_adivinadas[titulo]
            else:
                cat_id, cat_nombre = adivinar_categoria_y_raiz(titulo, headers_ref)
                cache_categorias_adivinadas[titulo] = (cat_id, cat_nombre)
        else:
            cat_id, cat_nombre = "MLV-DESCONOCIDA", "Categoría General"

        motivo_estado = "✅ Aprobado (Listo para Publicar)"
        
        if not titulo or titulo == "nan":
            motivo_estado = "🚫 Omitido (Fila vacía o sin Título)"
        else:
            if filtrar_duplicados == "true":
                if cuenta == "TODAS" and existe_en_todas:
                    motivo_estado = "🚫 Omitido (Ya publicado en todas las cuentas)"
                elif cuenta != "TODAS" and existe_en_seleccionada:
                    motivo_estado = "🚫 Omitido (Ya publicado en la cuenta destino)"
            
            if motivo_estado.startswith("✅") and not coincide_con_categoria_elegida(titulo, cat_id, categoria_filtro):
                motivo_estado = f"🚫 Omitido (No coincide con la categoría filtro: {categoria_filtro})"

        reporte_filas.append({
            "Fila Excel": idx_inicio + indice + 2,
            "SKU": sku,
            "Título del Producto": titulo,
            "Categoría Detectada": cat_nombre,
            "Precio": precio,
            "Stock": stock,
            "Estado": motivo_estado
        })

        if "🚫" in motivo_estado:
            omitidos_count += 1
            continue

        aprobados_count += 1
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

    df_rep = pd.DataFrame(reporte_filas)
    nombre_rep = f"Reporte_Sincronizacion_{int(time.time())}.xlsx"
    ruta_rep = os.path.join(CARPETA_REPORTES, nombre_rep)
    df_rep.to_excel(ruta_rep, index=False)

    if os.path.exists(temp_filename): os.remove(temp_filename)
    actualizar_progreso(100, "¡Sincronización Finalizada!")
    PROGRESO_ACTUAL["activo"] = False
    
    return {
        "productos": sorted(productos_activos, key=lambda x: x["CategoriaNombre"]),
        "total_leidos": total_filas,
        "total_aprobados": aprobados_count,
        "total_omitidos": omitidos_count,
        "archivo_reporte": nombre_rep
    }

@app.get("/api/descargar-reporte/{nombre_archivo}")
def descargar_reporte(nombre_archivo: str):
    ruta = os.path.join(CARPETA_REPORTES, nombre_archivo)
    if os.path.exists(ruta):
        return FileResponse(ruta, filename=nombre_archivo)
    return {"error": "Archivo no encontrado"}

@app.post("/publicar-lote")
def publicar_lote(productos: list[dict], cuenta: str = "tokens_ml.json"):
    PROGRESO_ACTUAL["activo"] = True
    archivos_destino = listar_archivos_token() if cuenta == "TODAS" else [cuenta]
    logs_totales = []
    errores_interactivos = {}
    total_items = len(productos) * len(archivos_destino)
    procesados = 0

    for arch_token in archivos_destino:
        token = obtener_token(arch_token)
        nombre_perfil = obtener_nombre_cuenta(arch_token)
        
        if not token:
            logs_totales.append(f"❌ [{nombre_perfil}] Error: Token no válido.")
            continue

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        titulos_existentes_cuenta = set()
        try:
            titulos_existentes_cuenta = obtener_titulos_publicados(headers)
        except Exception:
            pass

        for prod in productos:
            time.sleep(0.01)
            procesados += 1
            porcentaje = int((procesados / max(1, total_items)) * 100)
            titulo_original = prod['Titulo'][:60].strip()
            idx_front = prod.get('idx', '')
            
            if titulo_original.lower() in titulos_existentes_cuenta:
                logs_totales.append(f"⏭️ [{nombre_perfil}] OMITIDO: '{titulo_original[:20]}...' ya existe en esta cuenta.")
                continue

            actualizar_progreso(porcentaje, f"[{nombre_perfil}] Publicando ({procesados}/{total_items}): {titulo_original[:25]}...")

            titulo_x3 = f"{titulo_original}\n{titulo_original}\n{titulo_original}\n"
            
            attr_adicionales = prod.get('AtributosDinamicos', {})
            bloque_tecnico = "========================================\n"
            bloque_tecnico += "ESPECIFICACIONES TÉCNICAS Y CARACTERÍSTICAS\n"
            bloque_tecnico += "========================================\n"
            bloque_tecnico += f"• MARCA: {prod.get('Marca', 'Genérico')}\n"
            bloque_tecnico += f"• MODELO: {prod.get('Modelo', 'Universal')}\n"
            for k, v in attr_adicionales.items():
                bloque_tecnico += f"• {k.replace('_', ' ')}: {v}\n"
            bloque_tecnico += "========================================\n\n"

            if prod.get('DescripcionCustom') and len(str(prod['DescripcionCustom']).strip()) > 5:
                cuerpo_desc = f"{prod['DescripcionCustom']}\n"
                descripcion_estructurada = f"{BLOQUE_SUPERIOR}\n\n{titulo_x3}\n{cuerpo_desc}\n{bloque_tecnico}{BLOQUE_INFERIOR}"
            else:
                descripcion_estructurada = f"{BLOQUE_SUPERIOR}\n\n{titulo_x3}\n{bloque_tecnico}{BLOQUE_INFERIOR}"

            payload_desc = {
                "plain_text": descripcion_estructurada,
                "text": descripcion_estructurada
            }

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

            # REDONDEO ESTRICTO A MÁXIMO 2 DECIMALES
            precio_final = round(float(prod['Precio']), 2)

            datos_publicacion = {
                "title": titulo_original,
                "category_id": prod['Categoria_ID'],
                "price": precio_final,
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

            try:
                url_items = f"{API_ML}/items"
                respuesta = requests.post(url_items, headers=headers, json=datos_publicacion, timeout=12)
                
                if respuesta.status_code == 201:
                    item_data = respuesta.json()
                    item_id = item_data.get('id')
                    permalink = item_data.get('permalink')
                    
                    time.sleep(0.5)
                    try:
                        url_desc = f"{API_ML}/items/{item_id}/description"
                        res_desc = requests.post(url_desc, headers=headers, json=payload_desc, timeout=10)
                        if res_desc.status_code not in [200, 201]:
                            requests.put(url_desc, headers=headers, json=payload_desc, timeout=10)
                    except Exception as e_desc:
                        print(f"Aviso - Descripción no subida a {item_id}: {e_desc}")

                    try:
                        url_put = f"{API_ML}/items/{item_id}"
                        requests.put(url_put, headers=headers, json={"shipping": shipping_payload, "attributes": atributos_payload}, timeout=10)
                    except Exception:
                        pass
                        
                    logs_totales.append(f"✅ [{nombre_perfil}] ¡PUBLICADO! -> {permalink}")
                else:
                    error_texto = respuesta.text
                    if "restrictions_coliving" in error_texto:
                        titulo_mascarado = re.sub(r'(?i)\b(canon|hp|epson|brother|samsung|apple|sony)\b', 'Compatible', titulo_original)
                        datos_publicacion["title"] = titulo_mascarado
                        
                        url_items = f"{API_ML}/items"
                        res_bypass = requests.post(url_items, headers=headers, json=datos_publicacion, timeout=12)
                        if res_bypass.status_code == 201:
                            item_data = res_bypass.json()
                            item_id = item_data.get('id')
                            permalink = item_data.get('permalink')
                            
                            time.sleep(0.5)
                            try:
                                url_desc = f"{API_ML}/items/{item_id}/description"
                                res_desc = requests.post(url_desc, headers=headers, json=payload_desc, timeout=10)
                                if res_desc.status_code not in [200, 201]:
                                    requests.put(url_desc, headers=headers, json=payload_desc, timeout=10)
                            except Exception:
                                pass

                            url_put = f"{API_ML}/items/{item_id}"
                            requests.put(url_put, headers=headers, json={"title": titulo_original}, timeout=10)
                            requests.put(url_put, headers=headers, json={"shipping": shipping_payload, "attributes": atributos_payload}, timeout=10)
                            logs_totales.append(f"✅ [{nombre_perfil}] ¡PUBLICADO (Bypass Catálogo)! -> {permalink}")
                        else:
                            detalles = analizar_error_ml(res_bypass)
                            logs_totales.append(f"❌ [{nombre_perfil}] Error '{titulo_original[:15]}...': {detalles}")
                            if idx_front: errores_interactivos[idx_front] = detalles
                    else:
                        detalles = analizar_error_ml(respuesta)
                        logs_totales.append(f"❌ [{nombre_perfil}] Error '{titulo_original[:15]}...': {detalles}")
                        if idx_front: errores_interactivos[idx_front] = detalles
            except Exception as e_req:
                logs_totales.append(f"❌ [{nombre_perfil}] Excepción de red/servidor enviando '{titulo_original[:15]}...': {str(e_req)}")
                if idx_front: errores_interactivos[idx_front] = "Problema de conexión con el servidor ML."

    actualizar_progreso(100, "¡Lote Completado!")
    PROGRESO_ACTUAL["activo"] = False
    return {"detalles": logs_totales, "errores_idx": errores_interactivos}

@app.post("/api/generar-catalogo")
def generar_catalogo_endpoint(
    file: UploadFile = File(...),
    cuenta: str = Form(...),
    hoja: str = Form("TODAS"),
    inicio: int = Form(1),
    fin: int = Form(100),
    whatsapp: str = Form(...),
    nombre_empresa: str = Form("Mi Empresa"),
    col_tit: str = Form(""),
    col_sku: str = Form(""),
    col_mod: str = Form(""),
    col_pre: str = Form(""),
    col_stk: str = Form("")
):
    actualizar_progreso(10, "Cargando Excel...")
    temp_filename = f"temp_catalogo_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        buffer.write(file.file.read())
        
    mapa_manual = {
        "tit": col_tit if col_tit else None, "sku": col_sku if col_sku else None,
        "mod": col_mod if col_mod else None, "pre": col_pre if col_pre else None,
        "stk": col_stk if col_stk else None
    }

    try:
        filas_procesadas = procesar_excel_heuristico(temp_filename, hoja_objetivo=hoja, mapa_manual=mapa_manual)
    except Exception as e:
        if os.path.exists(temp_filename): os.remove(temp_filename)
        return {"error": f"Error leyendo Excel: {str(e)}"}
    
    if os.path.exists(temp_filename): os.remove(temp_filename)

    idx_inicio = max(0, inicio - 1)
    filas_rango = filas_procesadas[idx_inicio:fin]
    
    actualizar_progreso(30, f"Consultando productos de la cuenta en Mercado Libre...")
    token = obtener_token(cuenta)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"} if token else {}
    enlaces_ml = obtener_diccionario_publicados_ml(headers) if token else {}

    token_ref = obtener_token(listar_archivos_token()[0]) if listar_archivos_token() else None
    headers_ref = {"Authorization": f"Bearer {token_ref}", "Content-Type": "application/json"} if token_ref else {}
    cache_cat = {}

    productos_por_categoria = {}
    total_filas = len(filas_rango)
    
    for indice, p in enumerate(filas_rango):
        time.sleep(0.01)
        porcentaje_actual = int(30 + ((indice + 1) / max(1, total_filas)) * 60)
        actualizar_progreso(porcentaje_actual, f"[{indice+1}/{total_filas}] Vinculando fotos e info: {p.get('Titulo', '')[:20]}...")

        titulo = str(p.get("Titulo", "")).strip()
        if not titulo or titulo.lower() == "nan": continue

        if titulo in cache_cat:
            cat_nombre = cache_cat[titulo]
        else:
            if headers_ref:
                _, cat_nombre = adivinar_categoria_y_raiz(titulo, headers_ref)
            else:
                cat_nombre = "Categoría General"
            cache_cat[titulo] = cat_nombre

        if cat_nombre not in productos_por_categoria:
            productos_por_categoria[cat_nombre] = []
        
        productos_por_categoria[cat_nombre].append(p)

    actualizar_progreso(95, "Ensamblando diseño del catálogo HTML...")

    base_ws = "https://" + "wa.me/"
    num_telefono = "".join(filter(str.isdigit, whatsapp))
    if not num_telefono.startswith("58"):
        num_telefono = "58" + num_telefono.lstrip("0")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Catálogo Oficial - {nombre_empresa}</title>
        <style>
            :root {{ --primary: #0f172a; --accent: #0284c7; --bg: #f8fafc; --text: #334155; }}
            body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 0; }}
            header {{ background: var(--primary); color: white; padding: 40px 20px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-bottom: 5px solid var(--accent); }}
            header h1 {{ margin: 0; font-size: 38px; font-weight: 900; letter-spacing: -0.5px; }}
            header p {{ margin: 10px 0 0 0; color: #cbd5e1; font-size: 16px; font-weight: 500; }}
            .container {{ max-width: 1250px; margin: 40px auto; padding: 0 20px; }}
            
            .category-title {{ border-bottom: 3px solid #e2e8f0; padding-bottom: 10px; margin: 50px 0 25px 0; color: var(--primary); font-size: 24px; font-weight: 800; display: flex; align-items: center; gap: 10px; }}
            
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 30px; }}
            .card {{ background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; transition: all 0.3s ease; display: flex; flex-direction: column; position: relative; }}
            .card:hover {{ transform: translateY(-8px); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); border-color: #bae6fd; }}
            
            .stock-badge {{ position: absolute; top: 15px; right: 15px; background: rgba(15, 23, 42, 0.85); color: white; padding: 6px 12px; border-radius: 20px; font-size: 11px; font-weight: 800; backdrop-filter: blur(4px); z-index: 10; border: 1px solid rgba(255,255,255,0.2); }}
            
            .img-container {{ height: 240px; background: #ffffff; display: flex; justify-content: center; align-items: center; overflow: hidden; position: relative; border-bottom: 1px solid #f1f5f9; padding: 20px; }}
            .img-container img {{ max-width: 100%; max-height: 100%; object-fit: contain; transition: transform 0.3s ease; }}
            .card:hover .img-container img {{ transform: scale(1.05); }}
            .no-img {{ color: #cbd5e1; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; padding: 40px; border: 2px dashed #e2e8f0; border-radius: 12px; }}
            
            .card-body {{ padding: 25px; flex-grow: 1; display: flex; flex-direction: column; }}
            .sku-badge {{ font-size: 11px; font-weight: 800; background: #e0f2fe; color: #0369a1; padding: 5px 10px; border-radius: 6px; display: inline-block; margin-bottom: 12px; width: fit-content; text-transform: uppercase; letter-spacing: 0.5px; }}
            .title {{ font-size: 17px; font-weight: 800; color: var(--primary); margin: 0 0 15px 0; line-height: 1.4; }}
            
            .price-wrap {{ background: #f8fafc; padding: 15px; border-radius: 10px; margin-top: auto; border: 1px solid #e2e8f0; display: flex; flex-direction: column; gap: 12px; }}
            .price {{ font-size: 24px; font-weight: 900; color: #16a34a; text-align: center; }}
            
            .btn-group {{ display: flex; flex-direction: column; gap: 8px; }}
            .btn {{ text-decoration: none; padding: 12px; border-radius: 8px; font-weight: 800; font-size: 13px; text-align: center; transition: 0.2s; text-transform: uppercase; letter-spacing: 0.5px; display: block; }}
            .btn-ws {{ background: #25D366; color: white; }}
            .btn-ws:hover {{ background: #1da851; box-shadow: 0 4px 12px rgba(37,211,102,0.2); }}
            .btn-ml {{ background: #ffe600; color: #2d3277; border: 1px solid #facc15; }}
            .btn-ml:hover {{ background: #facc15; box-shadow: 0 4px 12px rgba(255,230,0,0.3); }}
            
            footer {{ text-align: center; padding: 40px 20px; color: #94a3b8; font-size: 14px; margin-top: 60px; background: white; border-top: 1px solid #e2e8f0; }}
            
            @media print {{
                .btn-group {{ display: none !important; }}
                body {{ background: white; }}
                .card {{ break-inside: avoid; box-shadow: none; border: 1px solid #e2e8f0; margin-bottom: 15px; }}
                .grid {{ grid-template-columns: repeat(3, 1fr); gap: 15px; }}
                .category-title {{ margin-top: 20px; }}
                .price-wrap {{ padding: 10px; background: transparent; border: none; border-top: 1px solid #e2e8f0; border-radius: 0; }}
            }}
        </style>
    </head>
    <body>
        <header>
            <h1>{nombre_empresa}</h1>
            <p>Catálogo Oficial Autorizado | Actualizado: {datetime.now().strftime('%d/%m/%Y')}</p>
        </header>
        <div class="container">
    """

    productos_validos = 0

    for cat_nombre, items in productos_por_categoria.items():
        html_content += f'<h2 class="category-title">📂 {cat_nombre}</h2>\n<div class="grid">\n'
        
        for p in items:
            titulo = str(p.get("Titulo", "")).strip()
            precio = round(float(p.get("Precio", 0)), 2)
            sku = str(p.get("SKU", "N/A")).strip()
            stock = p.get("Stock", 0)
            modelo = str(p.get("Modelo", "Universal")).strip()
            
            img_b64 = emparejar_imagen_local(modelo, sku, titulo)
            img_html = f'<img src="{img_b64}">' if img_b64 else '<div class="no-img">Imagen No Disponible</div>'

            msg_ws = f"Hola {nombre_empresa}, me interesa el producto:\n*{titulo}*\n(SKU: {sku})\nPrecio: ${precio:.2f}\n¿Tienen disponibilidad?"
            link_ws = f"{API_WA}/{num_telefono}?text={urllib.parse.quote(msg_ws)}"

            link_ml = enlaces_ml.get(titulo.lower())
            ml_btn_html = f'<a href="{link_ml}" target="_blank" class="btn btn-ml">🛍️ Comprar en ML</a>' if link_ml else ""

            html_content += f"""
                    <div class="card">
                        <div class="stock-badge">Stock: {stock} u.</div>
                        <div class="img-container">
                            {img_html}
                        </div>
                        <div class="card-body">
                            <span class="sku-badge">SKU: {sku}</span>
                            <h3 class="title">{titulo}</h3>
                            
                            <div class="price-wrap">
                                <div class="price">${precio:.2f}</div>
                                <div class="btn-group">
                                    <a href="{link_ws}" target="_blank" class="btn btn-ws">💬 WhatsApp</a>
                                    {ml_btn_html}
                                </div>
                            </div>
                        </div>
                    </div>
            """
            productos_validos += 1
        html_content += '</div>\n'

    html_content += """
        </div>
        <footer>
            Generado automáticamente por el motor ERP &copy; 2026
        </footer>
    </body>
    </html>
    """

    actualizar_progreso(100, "¡Catálogo generado!")
    PROGRESO_ACTUAL["activo"] = False

    if productos_validos == 0:
        return {"error": "No se detectaron productos válidos en el rango seleccionado."}

    nombre_archivo = f"Catalogo_{nombre_empresa.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    ruta_guardado = os.path.join(CARPETA_CATALOGOS, nombre_archivo)
    
    with open(ruta_guardado, "w", encoding="utf-8") as f:
        f.write(html_content)

    return {
        "success": True, 
        "mensaje": f"Se generó el catálogo con {productos_validos} productos.",
        "ruta": ruta_guardado
    }