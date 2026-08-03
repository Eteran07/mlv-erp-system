import os
import base64
import requests
import re
import time
import asyncio
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

# Importación de nuestros propios módulos limpios
from token_manager import (
    listar_archivos_token, obtener_nombre_cuenta,
    obtener_token, obtener_titulos_publicados, renovar_y_guardar_token
)
from categorizador import (
    obtener_categorias_raices_mlv, adivinar_categoria_y_raiz,
    coincide_con_categoria_elegida
)
from excel_parser import procesar_excel_heuristico

load_dotenv()
app = FastAPI(title="ERP Mercado Libre - Dashboard & Categorizador")

CARPETA_LOTE_IMAGENES = "lote_imagenes"
os.makedirs(CARPETA_LOTE_IMAGENES, exist_ok=True)

PROGRESO_ACTUAL = {
    "porcentaje": 0,
    "mensaje": "Iniciando...",
    "activo": False
}

CACHE_ATRIBUTOS_CAT = {}
BLOQUE_SUPERIOR = "SOMOS TIENDA FÍSICA, Empresa Mayorista Líder en el Mercado de la Computación Producto 100% de calidad\n"
BLOQUE_INFERIOR = """
.Por Favor Verifique la disponibilidad antes de ofertar
**************************************************************************************************
- Emitimos factura LEGAL
- Enviamos a todo el País.
**************************************************************************************************
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

def construir_atributos_dinamicos(prod, headers):
    atributos = [
        {"id": "BRAND", "value_name": prod.get("Marca", "Generico")},
        {"id": "MODEL", "value_name": prod.get("Modelo", "Universal")}
    ]

    sku = str(prod.get("SKU", "")).strip()
    if sku and sku.lower() != "nan":
        atributos.append({"id": "SELLER_SKU", "value_name": sku})
        atributos.append({"id": "PART_NUMBER", "value_name": sku})

    cat_id = prod.get("Categoria_ID")
    esquema_cat = []

    if cat_id in CACHE_ATRIBUTOS_CAT:
        esquema_cat = CACHE_ATRIBUTOS_CAT[cat_id]
    elif headers and cat_id:
        try:
            url_attr = f"https://api.mercadolibre.com/categories/{cat_id}/attributes"
            res = requests.get(url_attr, headers=headers, timeout=5)
            if res.status_code == 200:
                esquema_cat = res.json()
                CACHE_ATRIBUTOS_CAT[cat_id] = esquema_cat
        except Exception:
            esquema_cat = []

    color_val = str(prod.get("Color", "")).strip()
    if color_val and color_val.lower() != "nan":
        id_color = "COLOR"
        for attr in esquema_cat:
            nombre_attr = attr.get("name", "").lower()
            if "color" in nombre_attr or "tinta" in nombre_attr:
                id_color = attr.get("id")
                break
        atributos.append({"id": id_color, "value_name": color_val})

    PROHIBIDOS_COMPAT = {"HAS_COMPATIBILITIES", "COMPATIBILITIES", "ITEM_CONDITION", "GTIN", "BRAND", "MODEL", "SELLER_SKU", "PART_NUMBER"}
    compat_val = str(prod.get("Compatibilidad", "")).strip()
    if compat_val and compat_val.lower() != "nan":
        id_elegido = None
        for attr in esquema_cat:
            aid = attr.get("id", "")
            aname = attr.get("name", "").lower()
            if aid in PROHIBIDOS_COMPAT or attr.get("read_only") == True:
                continue
            if aid in ["COMPATIBLE_MODELS", "LINE", "SERIES", "COMPATIBLE_PRINTERS", "COMPATIBLE_BRANDS"]:
                id_elegido = aid
                break
            elif any(p in aname for p in ["compatib", "modelos compatibles", "impresoras", "línea", "linea"]):
                id_elegido = aid
                break
        if not id_elegido:
            id_elegido = "COMPATIBLE_MODELS"
        atributos.append({"id": id_elegido, "value_name": compat_val})

    mat_val = str(prod.get("Material", "")).strip()
    if mat_val and mat_val.lower() != "nan":
        id_mat = "MATERIAL"
        for attr in esquema_cat:
            nombre_attr = attr.get("name", "").lower()
            if any(palabra in nombre_attr for palabra in ["material", "tipo", "rendimiento", "especificac"]):
                id_mat = attr.get("id")
                break
        atributos.append({"id": id_mat, "value_name": mat_val})

    gtin_val = str(prod.get("GTIN", "OMITIR")).strip()
    if gtin_val != "OMITIR" and gtin_val and gtin_val.lower() != "nan":
        gtin_solo_numeros = re.sub(r'\D', '', gtin_val)
        if len(gtin_solo_numeros) >= 8:
            atributos.append({"id": "GTIN", "value_name": gtin_solo_numeros})

    return atributos

# --- INTERFAZ WEB BLINDADA (CARGA PROGRESIVA Y TOKENS REPARADOS) ---
HTML_INTERFACE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ERP Mercado Libre - Dashboard & Categorizador</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #f1f5f9; margin: 0; display: flex; min-height: 100vh; }
        .sidebar { width: 260px; background: #0f172a; color: white; transition: width 0.3s; display: flex; flex-direction: column; flex-shrink: 0; }
        .sidebar.collapsed { width: 65px; }
        .sidebar-header { padding: 20px 15px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #1e293b; }
        .logo-text { font-weight: bold; font-size: 16px; white-space: nowrap; overflow: hidden; }
        .sidebar.collapsed .logo-text { display: none; }
        .toggle-btn { background: #1e293b; color: white; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; }
        
        .nav-menu { list-style: none; padding: 10px 0; margin: 0; }
        .nav-item { padding: 14px 18px; display: flex; align-items: center; gap: 12px; cursor: pointer; transition: 0.2s; color: #94a3b8; font-size: 14px; font-weight: bold; }
        .nav-item:hover, .nav-item.active { background: #1e293b; color: #38bdf8; border-left: 4px solid #38bdf8; }
        .sidebar.collapsed .nav-text { display: none; }
        
        .main-content { flex-grow: 1; padding: 25px; overflow-x: auto; }
        .section-view { display: none; }
        .section-view.active { display: block; }
        
        .container { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        h1 { color: #1e293b; margin-top: 0; font-size: 24px; }
        .subtitle { color: #64748b; font-size: 14px; margin-bottom: 20px; }
        
        .panel-control { display: grid; grid-template-columns: 1.1fr 1fr 1fr 1fr 1.1fr; gap: 12px; background: #f8fafc; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e2e8f0; }
        .control-group { display: flex; flex-direction: column; gap: 5px; }
        label { font-weight: bold; font-size: 13px; color: #334155; }
        input[type="file"], select { padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px; background: white; font-size: 13px; }
        button { background: #0284c7; color: white; border: none; padding: 11px; font-weight: bold; border-radius: 4px; cursor: pointer; transition: 0.2s; }
        button:hover { background: #0369a1; }
        
        /* PANTALLA DE CARGA SIEMPRE VISIBLE CUANDO ACTIVA */
        .loader-container { display: none; text-align: center; padding: 40px; background: #f8fafc; border-radius: 12px; margin: 20px 0; border: 2px dashed #0284c7; }
        .spinner-wrapper { position: relative; width: 80px; height: 80px; margin: 0 auto 15px auto; }
        .spinner-circle { box-sizing: border-box; width: 100%; height: 100%; border: 8px solid #e2e8f0; border-top-color: #0284c7; border-radius: 50%; animation: spin 1s linear infinite; }
        .spinner-percentage { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 16px; color: #0284c7; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .bulk-toolbar { display: flex; flex-wrap: wrap; gap: 12px; background: #e0f2fe; padding: 12px 18px; border-radius: 6px; margin-bottom: 15px; align-items: center; border: 1px solid #bae6fd; }
        .bulk-select { padding: 6px; font-size: 12px; border-radius: 4px; border: 1px solid #7dd3fc; }
        .bulk-btn { background: #0284c7; color: white; border: none; padding: 7px 14px; font-size: 12px; border-radius: 4px; cursor: pointer; font-weight: bold; }
        
        table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }
        th, td { border: 1px solid #e2e8f0; padding: 8px; vertical-align: top;}
        th { background: #1e293b; color: white; }
        
        .account-badge { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; margin-top: 4px; margin-right: 4px; }
        .badge-libre { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
        .badge-existe { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
        
        .log-box { background: #0f172a; color: #4ade80; padding: 15px; height: 250px; overflow-y: auto; font-family: monospace; border-radius: 5px; margin-top: 20px; white-space: pre-wrap; font-size: 12px;}
        
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.65); z-index: 2000; justify-content: center; align-items: center; }
        .modal-box { background: white; padding: 28px; border-radius: 12px; width: 680px; max-width: 95%; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        .modal-box h3 { margin-top: 0; color: #0f172a; border-bottom: 2px solid #0284c7; padding-bottom: 10px; }
        .category-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; max-height: 380px; overflow-y: auto; margin: 15px 0; padding-right: 5px; }
        .category-item { border: 1px solid #cbd5e1; padding: 12px; border-radius: 6px; cursor: pointer; transition: 0.2s; font-size: 13px; font-weight: bold; color: #334155; display: flex; align-items: center; gap: 8px; }
        .category-item:hover { background: #f0f9ff; border-color: #0284c7; color: #0284c7; }
        .category-item.selected { background: #e0f2fe; border-color: #0284c7; color: #0369a1; box-shadow: 0 0 0 2px #0284c7; }
        
        .photo-manager { border: 2px dashed #aaa; padding: 8px; text-align: center; border-radius: 6px; background: #fafafa; cursor: pointer; position: relative;}
        .photo-manager input[type="file"] { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
        .preview-container { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; justify-content: center; }
        .preview-container img { width: 42px; height: 42px; object-fit: cover; border-radius: 4px; border: 1px solid #ccc; }
        .attr-summary { font-size: 11px; color: #334155; background: #f1f5f9; padding: 5px; border-radius: 4px; margin-top: 5px; border-left: 3px solid #0284c7; }
    </style>
</head>
<body>
    <!-- SIDEBAR -->
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
                <span>🔑</span> <span class="nav-text">Estado de Cuentas & Tokens</span>
            </li>
            <li class="nav-item" onclick="mostrarSeccion('tab-csv', this)">
                <span>📄</span> <span class="nav-text">Carga de Descripciones CSV</span>
            </li>
        </ul>
    </div>

    <!-- MAIN CONTENT -->
    <div class="main-content">
        <!-- PESTAÑA 1: MAESTRO -->
        <div id="tab-maestro" class="section-view active">
            <div class="container">
                <h1>📦 Panel Maestro de Sincronización y Publicación</h1>
                <div class="subtitle">Detección Dinámica de Hojas, Selector Oficial de Categorías MLV y Carga en Vivo</div>
                
                <div class="panel-control">
                    <div class="control-group">
                        <label>1. Cuenta / Modo Destino:</label>
                        <select id="cuenta-select"></select>
                    </div>
                    <div class="control-group">
                        <label>2. Inventario (.xlsx / .csv):</label>
                        <input type="file" id="file-db" accept=".xlsx, .csv" onchange="detectarHojasExcel(this)">
                    </div>
                    <div class="control-group">
                        <label>3. Pestaña / Hoja a Escanear:</label>
                        <select id="hoja-select">
                            <option value="TODAS">📚 Todo el Libro (Todas las Hojas)</option>
                        </select>
                    </div>
                    <div class="control-group">
                        <label>4. Rango de filas:</label>
                        <div style="display: flex; gap: 8px;">
                            <input type="number" id="rango-inicio" value="1" placeholder="Desde">
                            <input type="number" id="rango-fin" value="100" placeholder="Hasta">
                        </div>
                    </div>
                    <div class="control-group">
                        <label>5. Filtro Duplicados:</label>
                        <div style="display: flex; align-items: center; gap: 5px; margin-top: 6px;">
                            <input type="checkbox" id="filtar-duplicados" checked>
                            <span style="font-size: 12px; color: #444;">Ocultar YA EXISTENTES</span>
                        </div>
                    </div>
                    <!-- BOTONES RESTAURADOS: SINCRONIZAR + VERIFICAR TOKENS DIRECTAMENTE EN TAB 1 -->
                    <div class="control-group" style="grid-column: span 3;">
                        <button onclick="abrirModalCategorias()" style="width: 100%; font-size: 15px; background: #0284c7;">
                            🔍 1. Sincronizar y Elegir Categoría ML
                        </button>
                    </div>
                    <div class="control-group" style="grid-column: span 2;">
                        <button onclick="verificarTokens()" style="width: 100%; font-size: 15px; background: #475569;">
                            🔑 Probar Tokens Ahora
                        </button>
                    </div>
                </div>

                <!-- PANTALLA DE CARGA PROGRESIVA -->
                <div id="loader-zona" class="loader-container">
                    <div class="spinner-wrapper">
                        <div class="spinner-circle"></div>
                        <div id="spinner-percentage" class="spinner-percentage">0%</div>
                    </div>
                    <div id="loader-mensaje" style="font-weight:bold; color:#1e293b; font-size:16px;">Analizando inventario...</div>
                </div>

                <div id="tabla-container" style="display: none;">
                    <div class="bulk-toolbar">
                        <span>⚡ Edición Masiva:</span>
                        <select id="bulk-exposicion" class="bulk-select">
                            <option value="bronze">Exposición: Bronce / Estándar</option>
                            <option value="gold_special">Exposición: Clásica</option>
                            <option value="gold_pro">Exposición: Premium</option>
                        </select>
                        <button class="bulk-btn" onclick="aplicarExposicionMasiva()">Aplicar Exposición</button>
                        
                        <select id="bulk-envio" class="bulk-select" style="margin-left:5px;">
                            <option value="me2_free">🟢 Mercado Envíos - Envío Gratis</option>
                            <option value="custom_free">🟢 Envío Gratis Nacional (Custom)</option>
                            <option value="me2_buyer">🔵 Mercado Envíos - Cobro en Destino</option>
                            <option value="not_specified">⚪ Acordar con el Vendedor</option>
                        </select>
                        <button class="bulk-btn" onclick="aplicarEnvioMasivo()">Aplicar Envío</button>

                        <button class="bulk-btn" onclick="abrirModalMasivo()" style="background:#7e22ce; margin-left:10px;">⚡ Llenar Características Lote</button>
                    </div>

                    <table id="data-table">
                        <thead>
                            <tr>
                                <th style="width: 30px;"><input type="checkbox" checked onclick="toggleAll(this)"></th>
                                <th style="width: 22%;">Título, Categoría & Estado por Cuenta</th>
                                <th style="width: 7%;">Precio $</th>
                                <th style="width: 6%;">Stock</th>
                                <th style="width: 16%;">Exposición & Envío</th>
                                <th style="width: 27%;">Ficha Técnica (Marca / Modelo / SKU / GTIN)</th>
                                <th style="width: 22%;">Gestor de Fotos Local</th>
                            </tr>
                        </thead>
                        <tbody id="tabla-body"></tbody>
                    </table>
                    <button onclick="ejecutarPublicacion()" style="background: #16a34a; width: 100%; margin-top: 20px; padding: 16px; font-size: 16px;">🚀 Confirmar y Publicar Lote (Inteligente: Salta lo repetido)</button>
                </div>

                <div id="resultados" class="log-box">Esperando carga de archivo y sincronización...</div>
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
                <label style="background: #16a34a; color: white; padding: 12px 20px; border-radius: 4px; cursor: pointer; font-weight: bold; display: inline-block;">
                    <span>📂 Seleccionar Archivo CSV de Descripciones</span>
                    <input type="file" accept=".csv" style="display:none;" onchange="cargarDescripcionesCSV(this)">
                </label>
                <p id="csv-status" style="font-weight:bold; color:#16a34a; margin-top:15px;"></p>
            </div>
        </div>
    </div>

    <!-- MODAL EMERGENTE DE CATEGORÍAS MLV -->
    <div id="modal-categoria-mlv" class="modal-overlay">
        <div class="modal-box">
            <h3>🏷️ Selecciona una Categoría Oficial de Mercado Libre</h3>
            <p style="font-size:13px; color:#64748b; margin-bottom:10px;">
                Filtra tu rango de filas por un rubro oficial para mayor precisión, o elige cargar absolutamente todo el inventario:
            </p>
            <div id="lista-categorias-ml" class="category-grid"></div>
            <input type="hidden" id="cat-seleccionada-id" value="TODAS">
            <div style="display:flex; justify-content:flex-end; gap:12px; margin-top:20px; border-top:1px solid #e2e8f0; padding-top:15px;">
                <button onclick="cerrarModalCategorias()" style="background:#64748b;">Cancelar</button>
                <button onclick="confirmarYCargarInventario()" style="background:#16a34a; padding:10px 20px;">
                    🚀 2. Confirmar y Cargar Tabla de Publicación
                </button>
            </div>
        </div>
    </div>

    <!-- MODAL MASIVO -->
    <div id="modal-bulk-atributos" class="modal-overlay">
        <div class="modal-box">
            <h3 style="color:#7e22ce;">⚡ Llenado Masivo de Características</h3>
            <div class="modal-grid">
                <div><label>Marca:</label><input type="text" id="bm-mar"></div>
                <div><label>Color:</label><input type="text" id="bm-color"></div>
                <div><label>Compatibilidad:</label><input type="text" id="bm-compat"></div>
                <div><label>Material:</label><input type="text" id="bm-mat"></div>
            </div>
            <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:20px;">
                <button onclick="cerrarModalMasivo()" style="background:#64748b;">Cancelar</button>
                <button onclick="aplicarAtributosMasivos()" style="background:#7e22ce;">🚀 Aplicar a Todo</button>
            </div>
        </div>
    </div>

    <!-- MODAL INDIVIDUAL -->
    <div id="modal-atributos" class="modal-overlay">
        <div class="modal-box">
            <h3>🛠️ Editar Características del Producto</h3>
            <input type="hidden" id="modal-idx">
            <div class="modal-grid">
                <div><label>Marca:</label><input type="text" id="m-mar"></div>
                <div><label>Modelo:</label><input type="text" id="m-mod"></div>
                <div><label>Color:</label><input type="text" id="m-color"></div>
                <div><label>Compatibilidad:</label><input type="text" id="m-compat"></div>
                <div style="grid-column: span 2;"><label>Material / Especificación:</label><input type="text" id="m-mat"></div>
            </div>
            <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:20px;">
                <button onclick="cerrarModal()" style="background:#64748b;">Cancelar</button>
                <button onclick="guardarAtributosModal()">💾 Guardar Cambios</button>
            </div>
        </div>
    </div>

    <script>
        const imagenesPorFila = {};
        const atributosPorFila = {};
        const descripcionesCSV = {};
        let intervaloProgreso = null;

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
                select.innerHTML += `<option value="TODAS" style="font-weight:bold; color:#0369a1;">🚀 PUBLICAR EN TODAS SIMULTÁNEAMENTE</option>`;
            }
        };

        // --- DETECCIÓN DINÁMICA DE HOJAS AL SELECCIONAR EL EXCEL ---
        async function detectarHojasExcel(inputElement) {
            const file = inputElement.files[0];
            const selectHoja = document.getElementById('hoja-select');
            if (!file) return;

            selectHoja.innerHTML = '<option value="TODAS">⏳ Detectando pestañas del archivo...</option>';
            const formData = new FormData();
            formData.append('file', file);

            try {
                const res = await fetch('/api/hojas-excel', { method: 'POST', body: formData });
                const data = await res.json();
                
                selectHoja.innerHTML = '<option value="TODAS">📚 Todo el Libro (Todas las Hojas)</option>';
                data.hojas.forEach(nombreHoja => {
                    selectHoja.innerHTML += `<option value="${nombreHoja}">📄 ${nombreHoja}</option>`;
                });
            } catch(e) {
                selectHoja.innerHTML = '<option value="TODAS">📚 Todo el Libro (Todas las Hojas)</option>';
            }
        }

        // --- SALIDA INMEDIATA EN TABLA 1 AL PROBAR TOKENS ---
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

        // --- PANTALLA DE CARGA SIEMPRE VISIBLE SIN RACE CONDITIONS ---
        function iniciarMonitoreoProgreso() {
            document.getElementById('loader-zona').style.display = 'block';
            if (intervaloProgreso) clearInterval(intervaloProgreso);
            
            intervaloProgreso = setInterval(async () => {
                try {
                    const res = await fetch('/estado-progreso');
                    const info = await res.json();
                    document.getElementById('spinner-percentage').innerText = info.porcentaje + "%";
                    document.getElementById('loader-mensaje').innerText = info.mensaje;
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

        function abrirModal(idx) {
            const attr = atributosPorFila[idx];
            document.getElementById('modal-idx').value = idx;
            document.getElementById('m-mar').value = attr.marca || '';
            document.getElementById('m-mod').value = attr.modelo || '';
            document.getElementById('m-color').value = attr.color || '';
            document.getElementById('m-compat').value = attr.compatibilidad || '';
            document.getElementById('m-mat').value = attr.material || '';
            document.getElementById('modal-atributos').style.display = 'flex';
        }

        function cerrarModal() {
            document.getElementById('modal-atributos').style.display = 'none';
        }

        function guardarAtributosModal() {
            const idx = document.getElementById('modal-idx').value;
            atributosPorFila[idx].marca = document.getElementById('m-mar').value;
            atributosPorFila[idx].modelo = document.getElementById('m-mod').value;
            atributosPorFila[idx].color = document.getElementById('m-color').value;
            atributosPorFila[idx].compatibilidad = document.getElementById('m-compat').value;
            atributosPorFila[idx].material = document.getElementById('m-mat').value;
            
            document.getElementById('mar-'+idx).value = atributosPorFila[idx].marca;
            document.getElementById('mod-'+idx).value = atributosPorFila[idx].modelo;
            actualizarResumenAtributos(idx);
            cerrarModal();
        }

        function actualizarResumenAtributos(idx) {
            const attr = atributosPorFila[idx];
            let info = `🏷️ ${attr.marca || 'Generico'} / ${attr.modelo || 'Universal'}`;
            if (attr.color) info += ` | 🎨 ${attr.color}`;
            if (attr.compatibilidad) info += ` | 🔧 ${attr.compatibilidad}`;
            document.getElementById('resumen-attr-'+idx).innerText = info;
        }

        function procesarArchivos(inputElement, idx) {
            const files = inputElement.files;
            const previewArea = document.getElementById(`prev-${idx}`);
            if (!imagenesPorFila[idx]) imagenesPorFila[idx] = [];

            for (let file of files) {
                if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
                    alert(`El archivo ${file.name} no es válido. Solo JPG, PNG o WEBP.`);
                    continue;
                }
                const reader = new FileReader();
                reader.onload = (e) => {
                    const base64Data = e.target.result;
                    imagenesPorFila[idx].push(base64Data);
                    const img = document.createElement('img');
                    img.src = base64Data;
                    previewArea.appendChild(img);
                };
                reader.readAsDataURL(file);
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

            // OCULTAR TABLA Y ENCENDER LA PANTALLA DE CARGA AL 100% VISIBLE
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
                    let imgHtmlPreview = "";
                    if (prod.ImagenLocal) {
                        imagenesPorFila[idx].push(prod.ImagenLocal);
                        imgHtmlPreview = `<img src="${prod.ImagenLocal}" title="Foto local">`;
                    }
                    
                    atributosPorFila[idx] = {
                        marca: prod.Marca,
                        modelo: prod.Modelo,
                        color: prod.Color,
                        compatibilidad: prod.Compatibilidad,
                        material: prod.Material
                    };

                    let gtinDisplay = (prod.GTIN && prod.GTIN !== 'N/A' && prod.GTIN !== 'OMITIR') ? 'block' : 'none';
                    let selectCustom = (prod.GTIN && prod.GTIN !== 'N/A' && prod.GTIN !== 'OMITIR') ? 'selected' : '';
                    let selectOmit = (prod.GTIN && prod.GTIN !== 'N/A' && prod.GTIN !== 'OMITIR') ? '' : 'selected';

                    let resumenInit = `🏷️ ${prod.Marca} / ${prod.Modelo}`;
                    if (prod.Color) resumenInit += ` | 🎨 ${prod.Color}`;
                    if (prod.Compatibilidad) resumenInit += ` | 🔧 ${prod.Compatibilidad}`;

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
                                <button onclick="abrirModal(${idx})" style="background:#0284c7; width:100%; padding:4px; font-size:11px;">🛠️ Ver / Editar + Características</button>
                                <div id="resumen-attr-${idx}" class="attr-summary">${resumenInit}</div>
                            </td>
                            <td>
                                <div class="photo-manager">
                                    <span>📸 Clic o Arrastra fotos aquí</span>
                                    <input type="file" accept="image/jpeg, image/png, image/webp" multiple onchange="procesarArchivos(this, ${idx})">
                                </div>
                                <div id="prev-${idx}" class="preview-container">${imgHtmlPreview}</div>
                            </td>
                        </tr>
                    `;
                });

                document.getElementById('tabla-container').style.display = 'block';
                consola.innerText = `✅ ¡Sincronización completa! ${resultado.productos.length} artículos listos.`;
            } catch(e) {
                consola.innerText = "❌ Error en sincronización: " + e;
            } finally {
                // APAGADO SEGURO Y EXPLÍCITO DEL LOADER SÓLO AL TERMINAR
                if (intervaloProgreso) clearInterval(intervaloProgreso);
                setTimeout(() => { document.getElementById('loader-zona').style.display = 'none'; }, 500);
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
                    "Color": attr.color,
                    "Compatibilidad": attr.compatibilidad,
                    "Material": attr.material,
                    "DescripcionCustom": document.getElementById('desc-init-'+idx).value,
                    "ImagenesB64": imagenesPorFila[idx] || []
                });
            });

            if (!seleccionados.length) return alert('No hay artículos seleccionados.');
            const cuentaSel = document.getElementById('cuenta-select').value;
            const nomCuenta = document.getElementById('cuenta-select').options[document.getElementById('cuenta-select').selectedIndex].text;

            if (!confirm(`¿Confirmas publicar ${seleccionados.length} artículos en: ${nomCuenta}?`)) return;

            // LOADER PROGRESIVO DE PUBLICACIÓN
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
            res = requests.get("https://api.mercadolibre.com/users/me", headers=headers, timeout=5)
            if res.status_code == 200:
                nick = res.json().get("nickname", "Desconocido")
                logs.append(f"✅ [{nombre}] Conexión Activa (Usuario: {nick})")
            else:
                logs.append(f"⚠️ [{nombre}] Token vencido. Intentando auto-renovación...")
                nuevo_token, estado = renovar_y_guardar_token(arch, datos)
                if estado == "OK":
                    logs.append(f"🔄 [{nombre}] ¡Renovado con Éxito!")
                else:
                    logs.append(f"❌ [{nombre}] Falló renovación: {estado}")
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
    filtrar_duplicados: str = Form("true")
):
    actualizar_progreso(5, "Cargando archivo en memoria...")
    PROGRESO_ACTUAL["activo"] = True
    temp_filename = f"temp_{file.filename}"
    with open(temp_filename, "wb") as buffer: buffer.write(await file.read())

    archivos_a_escanear = listar_archivos_token()
    titulos_por_cuenta = {}

    actualizar_progreso(15, "Analizando inventarios activos por cuenta...")
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

    try:
        filas_procesadas = procesar_excel_heuristico(temp_filename, hoja_objetivo=hoja)
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
        modelo = sku
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
            cuerpo_desc = prod['DescripcionCustom'] if prod.get('DescripcionCustom') else redactar_parrafo_base(titulo_original)
            
            bloque_ficha = f"""
==================================================================
FICHA TÉCNICA DEL PRODUCTO:
- MARCA: {prod['Marca']}
- MODELO: {prod['Modelo']}
- NRO. DE PARTE / SKU: {prod.get('SKU', 'N/A')}
- COLOR / ESPECIFICACIÓN: {prod.get('Color', 'N/A')}
- COMPATIBILIDAD / LÍNEA: {prod.get('Compatibilidad', 'N/A')}
- MATERIAL / TIPO: {prod.get('Material', 'N/A')}
==================================================================
"""
            descripcion_estructurada = f"{BLOQUE_SUPERIOR}\n{titulo_x3}\n{bloque_ficha}\n{cuerpo_desc}\n{BLOQUE_INFERIOR}"
            atributos_payload = construir_atributos_dinamicos(prod, headers)

            modo_envio = prod.get('Envio', 'not_specified')
            if modo_envio == "me2_free":
                shipping_payload = {"mode": "me2", "local_pick_up": True, "free_shipping": True}
            elif modo_envio == "custom_free":
                shipping_payload = {"mode": "custom", "free_shipping": True, "costs": [{"description": "Envío Gratis a Nivel Nacional", "cost": 0}]}
            elif modo_envio == "me2_buyer":
                shipping_payload = {"mode": "me2", "local_pick_up": True, "free_shipping": False}
            else:
                shipping_payload = {"mode": "not_specified", "local_pick_up": True}

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
                requests.post(f"https://api.mercadolibre.com/items/{item_id}/description", headers=headers, json={"text": descripcion_estructurada}, timeout=10)
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
                        requests.put(f"https://api.mercadolibre.com/items/{item_id}", headers=headers, json={"title": titulo_original}, timeout=10)
                        requests.post(f"https://api.mercadolibre.com/items/{item_id}/description", headers=headers, json={"text": descripcion_estructurada}, timeout=10)
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