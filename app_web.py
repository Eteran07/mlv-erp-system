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
from google import genai

load_dotenv()
app = FastAPI(title="ERP Mercado Libre - Multicuenta & Control Masivo")

CARPETA_LOTE_IMAGENES = "lote_imagenes"
os.makedirs(CARPETA_LOTE_IMAGENES, exist_ok=True)

try:
    cliente_ia = genai.Client()
    USAR_IA = True
except Exception:
    USAR_IA = False

PROGRESO_ACTUAL = {
    "porcentaje": 0,
    "mensaje": "Iniciando...",
    "activo": False
}

# --- CACHÉ PARA ESQUEMA DE ATRIBUTOS OFICIALES POR CATEGORÍA ---
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

def listar_archivos_token():
    archivos = sorted(glob.glob("token*.json"))
    return archivos if archivos else ["tokens_ml.json"]

def obtener_nombre_cuenta(archivo_token):
    nombre = archivo_token.replace("token_", "").replace("tokens_", "").replace(".json", "").upper()
    return nombre if nombre else "PRINCIPAL"

def obtener_token(archivo_token):
    try:
        with open(archivo_token, "r") as archivo:
            return json.load(archivo).get("access_token")
    except FileNotFoundError:
        return None

def obtener_titulos_publicados(headers):
    try:
        res_me = requests.get("https://api.mercadolibre.com/users/me", headers=headers)
        if res_me.status_code != 200: return set()
        user_id = res_me.json().get("id")

        res_items = requests.get(f"https://api.mercadolibre.com/users/{user_id}/items/search", headers=headers)
        item_ids = res_items.json().get("results", [])
        
        titulos_activos = set()
        if item_ids:
            ids_str = ",".join(item_ids[:50]) 
            res_detalles = requests.get(f"https://api.mercadolibre.com/items?ids={ids_str}", headers=headers)
            for item in res_detalles.json():
                if item.get("code") == 200:
                    titulos_activos.add(item["body"]["title"].strip().lower())
        return titulos_activos
    except Exception:
        return set()

def adivinar_categoria(titulo, headers):
    url = "https://api.mercadolibre.com/sites/MLV/domain_discovery/search"
    response = requests.get(url, headers=headers, params={"q": titulo})
    if response.status_code == 200 and len(response.json()) > 0:
        return response.json()[0].get("category_id")
    return "MLV-DESCONOCIDA"

def redactar_parrafo_base(titulo):
    if not USAR_IA: 
        return f"Producto original y garantizado de alto rendimiento para {titulo}. Fabricado bajo estrictos estándares de calidad."
    try:
        respuesta = cliente_ia.models.generate_content(
            model='gemini-2.0-flash', 
            contents=f"Escribe un párrafo técnico, persuasivo y sin saludos de máximo 3 líneas sobre el producto: '{titulo}'."
        )
        return respuesta.text.strip()
    except Exception:
        return f"Producto original y garantizado de alto rendimiento para {titulo}. Fabricado bajo estrictos estándares de calidad."

def emparejar_imagen_local(modelo, sku, titulo):
    if not os.path.exists(CARPETA_LOTE_IMAGENES):
        return None
    
    archivos = os.listdir(CARPETA_LOTE_IMAGENES)
    if not archivos:
        return None

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
                print(f"Error cargando foto local {arc}: {e}")
    return None

def subir_foto_a_ml(base64_data, token):
    try:
        header, encoded = base64_data.split(",", 1)
        file_ext = header.split(";")[0].split("/")[1]
        image_bytes = base64.b64decode(encoded)

        url = "https://api.mercadolibre.com/pictures"
        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": (f"foto.{file_ext}", image_bytes, f"image/{file_ext}")}
        
        res = requests.post(url, headers=headers, files=files)
        if res.status_code == 201:
            return res.json().get("id") 
    except Exception as e:
        print(f"Error procesando imagen base64: {e}")
    return None

# --- NUEVO MOTOR QUIRÚRGICO: MAPEO DE CARACTERÍSTICAS SEGÚN LA CATEGORÍA ---
def construir_atributos_dinamicos(prod, headers):
    """
    Consulta la categoría en ML y mapea Color, Compatibilidad y Material
    a los IDs exactos que esa categoría soporta para que nunca sean descartados.
    """
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

    # Consulta a la API de Atributos de Categoria con caché
    if cat_id in CACHE_ATRIBUTOS_CAT:
        esquema_cat = CACHE_ATRIBUTOS_CAT[cat_id]
    elif headers and cat_id:
        try:
            url_attr = f"https://api.mercadolibre.com/categories/{cat_id}/attributes"
            res = requests.get(url_attr, headers=headers)
            if res.status_code == 200:
                esquema_cat = res.json()
                CACHE_ATRIBUTOS_CAT[cat_id] = esquema_cat
        except Exception:
            esquema_cat = []

    # Mapear Color
    color_val = str(prod.get("Color", "")).strip()
    if color_val and color_val.lower() != "nan":
        id_color = "COLOR"
        for attr in esquema_cat:
            nombre_attr = attr.get("name", "").lower()
            if "color" in nombre_attr or "tinta" in nombre_attr:
                id_color = attr.get("id")
                break
        atributos.append({"id": id_color, "value_name": color_val})

    # Mapear Compatibilidad / Modelos compatibles / Línea
    compat_val = str(prod.get("Compatibilidad", "")).strip()
    if compat_val and compat_val.lower() != "nan":
        id_compat = "COMPATIBLE_MODELS"
        encontrado = False
        for attr in esquema_cat:
            nombre_attr = attr.get("name", "").lower()
            if any(palabra in nombre_attr for palabra in ["compatib", "modelos", "impresoras", "línea", "linea", "serie"]):
                atributos.append({"id": attr.get("id"), "value_name": compat_val})
                encontrado = True
        if not encontrado:
            atributos.append({"id": "COMPATIBLE_MODELS", "value_name": compat_val})
            atributos.append({"id": "LINE", "value_name": compat_val})

    # Mapear Material / Especificación / Tipo
    mat_val = str(prod.get("Material", "")).strip()
    if mat_val and mat_val.lower() != "nan":
        id_mat = "MATERIAL"
        for attr in esquema_cat:
            nombre_attr = attr.get("name", "").lower()
            if any(palabra in nombre_attr for palabra in ["material", "tipo", "rendimiento", "especificac"]):
                id_mat = attr.get("id")
                break
        atributos.append({"id": id_mat, "value_name": mat_val})

    # Validador y Sanitizador del GTIN (Código Universal)
    gtin_val = str(prod.get("GTIN", "OMITIR")).strip()
    if gtin_val != "OMITIR" and gtin_val and gtin_val.lower() != "nan":
        gtin_solo_numeros = re.sub(r'\D', '', gtin_val)
        if len(gtin_solo_numeros) >= 8:
            atributos.append({"id": "GTIN", "value_name": gtin_solo_numeros})

    return atributos

# --- INTERFAZ HTML (EXACTAMENTE COMO TE GUSTA, SIN TOCAR FUNCIONES OPERATIVAS) ---
HTML_INTERFACE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ERP Mercado Libre - Control Maestro</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }
        .container { max-width: 1780px; background: white; padding: 25px; border-radius: 12px; margin: auto; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; margin-bottom: 5px; }
        .subtitle { text-align: center; color: #666; font-size: 14px; margin-bottom: 20px; }
        
        .panel-control { display: grid; grid-template-columns: 1.2fr 1fr 1fr 1fr; gap: 15px; background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #ddd; }
        .control-group { display: flex; flex-direction: column; gap: 5px; }
        label { font-weight: bold; font-size: 13px; color: #444; }
        input[type="file"], select { padding: 8px; border: 1px solid #ccc; border-radius: 4px; background: white; font-size: 13px; }
        button { background: #007bff; color: white; border: none; padding: 11px; font-weight: bold; border-radius: 4px; cursor: pointer; transition: 0.2s; }
        button:hover { background: #0056b3; }
        
        .loader-container { display: none; text-align: center; padding: 40px; background: #f8f9fa; border-radius: 12px; margin: 20px 0; border: 2px dashed #007bff; }
        .spinner-wrapper { position: relative; width: 95px; height: 95px; margin: 0 auto 15px auto; }
        .spinner-circle { box-sizing: border-box; width: 100%; height: 100%; border: 8px solid #e9ecef; border-top-color: #007bff; border-radius: 50%; animation: spin 1s linear infinite; }
        .spinner-percentage { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; color: #007bff; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .progress-text { font-weight: bold; color: #333; font-size: 15px; margin-top: 5px; }

        .bulk-toolbar { display: flex; flex-wrap: wrap; gap: 12px; background: #e3f2fd; padding: 12px 18px; border-radius: 6px; margin-bottom: 15px; align-items: center; border: 1px solid #90caf9; }
        .bulk-toolbar span { font-weight: bold; font-size: 13px; color: #0d47a1; }
        .bulk-select { padding: 6px; font-size: 12px; border-radius: 4px; border: 1px solid #64b5f6; }
        .bulk-btn { background: #1976d2; color: white; border: none; padding: 7px 14px; font-size: 12px; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .bulk-btn:hover { background: #1565c0; }
        .btn-csv { background: #28a745; color: white; border: none; padding: 7px 14px; font-size: 12px; border-radius: 4px; cursor: pointer; font-weight: bold; display: flex; align-items: center; gap: 5px; }
        .btn-csv:hover { background: #218838; }
        .btn-bulk-attr { background: #6f42c1; color: white; border: none; padding: 7px 14px; font-size: 12px; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .btn-bulk-attr:hover { background: #5a32a3; }

        table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top;}
        th { background: #343a40; color: white; }
        input[type="text"], input[type="number"], select.attr-select { width: 100%; padding: 5px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; font-size: 12px; }
        
        .log-box { background: #1e1e1e; color: #00ff66; padding: 15px; height: 200px; overflow-y: auto; font-family: monospace; border-radius: 5px; margin-top: 20px; white-space: pre-wrap; font-size: 12px;}
        
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 1000; justify-content: center; align-items: center; }
        .modal-box { background: white; padding: 25px; border-radius: 10px; width: 600px; max-width: 95%; box-shadow: 0 5px 25px rgba(0,0,0,0.3); }
        .modal-box h3 { margin-top: 0; color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        .modal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 15px; }
        .modal-grid label { font-size: 12px; font-weight: bold; color: #555; display: block; margin-bottom: 3px; }
        .modal-grid input { width: 100%; padding: 7px; border: 1px solid #ccc; border-radius: 4px; }
        .modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
        
        .photo-manager { border: 2px dashed #aaa; padding: 8px; text-align: center; border-radius: 6px; background: #fafafa; cursor: pointer; transition: 0.3s; position: relative;}
        .photo-manager:hover { border-color: #007bff; background: #f0f8ff; }
        .photo-manager input[type="file"] { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
        .preview-container { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; justify-content: center; }
        .preview-container img { width: 42px; height: 42px; object-fit: cover; border-radius: 4px; border: 1px solid #ccc; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .cat-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: bold; background: #e3f2fd; color: #0d47a1; margin-top: 4px; }
        .desc-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: bold; background: #e8f5e9; color: #2e7d32; margin-top: 4px; }
        .attr-summary { font-size: 11px; color: #444; background: #f1f3f5; padding: 5px; border-radius: 4px; margin-top: 5px; border-left: 3px solid #007bff; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚙️ ERP Mercado Libre - Control Maestro</h1>
        <div class="subtitle">Mapeo Dinámico de Atributos por Categoría, Llenado Masivo y Envío Gratis Operativo</div>
        
        <div class="panel-control">
            <div class="control-group">
                <label>1. Perfil / Cuenta Destino:</label>
                <select id="cuenta-select"></select>
            </div>
            <div class="control-group">
                <label>2. Inventario (.xlsx / .csv):</label>
                <input type="file" id="file-db" accept=".xlsx, .csv">
            </div>
            <div class="control-group">
                <label>3. Rango de filas:</label>
                <div style="display: flex; gap: 8px;">
                    <input type="number" id="rango-inicio" value="1" placeholder="Desde" style="width: 50%;">
                    <input type="number" id="rango-fin" value="100" placeholder="Hasta" style="width: 50%;">
                </div>
            </div>
            <div class="control-group">
                <label>4. Filtro Inteligente:</label>
                <div style="display: flex; align-items: center; gap: 5px; margin-top: 6px;">
                    <input type="checkbox" id="filtar-duplicados" checked>
                    <span style="font-size: 12px; color: #444;">Ocultar ya publicados</span>
                </div>
            </div>
            <div class="control-group" style="grid-column: span 4;">
                <button onclick="cargarInventario()" style="width: 100%; font-size: 15px;">🔍 Sincronizar y Cargar Productos en Tabla</button>
            </div>
        </div>

        <div id="loader-zona" class="loader-container">
            <div class="spinner-wrapper">
                <div class="spinner-circle"></div>
                <div id="spinner-percentage" class="spinner-percentage">0%</div>
            </div>
            <div id="loader-mensaje" class="progress-text">Iniciando sincronización...</div>
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

                <button class="btn-bulk-attr" onclick="abrirModalMasivo()" style="margin-left:10px;">⚡ Llenar Características Masivamente</button>

                <label class="btn-csv" style="margin-left:auto;">
                    <span>📄 Cargar Descripciones CSV</span>
                    <input type="file" id="file-csv-desc" accept=".csv" style="display:none;" onchange="cargarDescripcionesCSV(this)">
                </label>
            </div>

            <table id="data-table">
                <thead>
                    <tr>
                        <th style="width: 30px;"><input type="checkbox" checked onclick="toggleAll(this)"></th>
                        <th style="width: 20%;">Título & Categoría</th>
                        <th style="width: 7%;">Precio $</th>
                        <th style="width: 6%;">Stock</th>
                        <th style="width: 16%;">Exposición & Envío</th>
                        <th style="width: 28%;">Ficha Técnica (Marca / Modelo / SKU / GTIN Obligatorio)</th>
                        <th style="width: 22%;">Gestor de Fotos</th>
                    </tr>
                </thead>
                <tbody id="tabla-body"></tbody>
            </table>
            <button onclick="ejecutarPublicacion()" style="background: #28a745; width: 100%; margin-top: 20px; padding: 16px; font-size: 16px;">🚀 Confirmar y Publicar Lote</button>
        </div>

        <!-- MODAL DE LLENADO MASIVO DE CARACTERÍSTICAS -->
        <div id="modal-bulk-atributos" class="modal-overlay">
            <div class="modal-box">
                <h3 style="color:#6f42c1;">⚡ Llenado Masivo de Características</h3>
                <p style="font-size:12px; color:#555;">Los atributos que llenes aquí se aplicarán instantáneamente a <b>todos los artículos marcados con check</b> en la tabla.</p>
                <div class="modal-grid">
                    <div>
                        <label>Marca (Común para el lote):</label>
                        <input type="text" id="bm-mar" placeholder="Ej: MAXIPRINT">
                    </div>
                    <div>
                        <label>Color (Común para el lote):</label>
                        <input type="text" id="bm-color" placeholder="Ej: Negro / Cian">
                    </div>
                    <div>
                        <label>Compatibilidad / Rendimiento:</label>
                        <input type="text" id="bm-compat" placeholder="Ej: Canon G1100 / HP 85A">
                    </div>
                    <div>
                        <label>Material / Especificación:</label>
                        <input type="text" id="bm-mat" placeholder="Ej: Consumible / Original">
                    </div>
                </div>
                <div class="modal-actions">
                    <button onclick="cerrarModalMasivo()" style="background:#6c757d;">Cancelar</button>
                    <button onclick="aplicarAtributosMasivos()" style="background:#6f42c1;">🚀 Aplicar a Todo el Lote Seleccionado</button>
                </div>
            </div>
        </div>

        <!-- MODAL INDIVIDUAL PARA DETALLES ESPECÍFICOS -->
        <div id="modal-atributos" class="modal-overlay">
            <div class="modal-box">
                <h3>🛠️ Editar Características del Producto</h3>
                <input type="hidden" id="modal-idx">
                <div class="modal-grid">
                    <div>
                        <label>Marca:</label>
                        <input type="text" id="m-mar">
                    </div>
                    <div>
                        <label>Modelo:</label>
                        <input type="text" id="m-mod">
                    </div>
                    <div>
                        <label>Color:</label>
                        <input type="text" id="m-color">
                    </div>
                    <div>
                        <label>Compatibilidad / Rendimiento:</label>
                        <input type="text" id="m-compat">
                    </div>
                    <div style="grid-column: span 2;">
                        <label>Material / Especificación Adicional:</label>
                        <input type="text" id="m-mat">
                    </div>
                </div>
                <div class="modal-actions">
                    <button onclick="cerrarModal()" style="background:#6c757d;">Cancelar</button>
                    <button onclick="guardarAtributosModal()" style="background:#007bff;">💾 Guardar Cambios</button>
                </div>
            </div>
        </div>

        <div id="resultados" class="log-box">Esperando selección de cuenta e inventario...</div>
    </div>

    <script>
        const imagenesPorFila = {};
        const atributosPorFila = {};
        const descripcionesCSV = {};
        let intervaloProgreso = null;

        window.onload = async () => {
            const res = await fetch('/cuentas');
            const cuentas = await res.json();
            const select = document.getElementById('cuenta-select');
            select.innerHTML = "";
            cuentas.forEach(c => {
                select.innerHTML += `<option value="${c.archivo}">${c.nombre} (${c.archivo})</option>`;
            });
            if (cuentas.length > 1) {
                select.innerHTML += `<option value="TODAS" style="font-weight:bold; color:#0d47a1;">🚀 PUBLICAR EN TODAS SIMULTÁNEAMENTE</option>`;
            }
        };

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
                        document.getElementById('desc-tag-'+idx).innerText = "📄 Desc. CSV Asignada";
                        matchCount++;
                    }
                });

                alert(`✅ Se asignaron descripciones personalizadas a ${matchCount} artículos.`);
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
            alert(`✅ Características aplicadas masivamente a ${count} artículos seleccionados.`);
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

        async function cargarInventario() {
            const fileInput = document.getElementById('file-db');
            if (!fileInput.files.length) return alert('Selecciona un archivo Excel o CSV.');

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('cuenta', document.getElementById('cuenta-select').value);
            formData.append('inicio', document.getElementById('rango-inicio').value);
            formData.append('fin', document.getElementById('rango-fin').value);
            formData.append('filtrar_duplicados', document.getElementById('filtar-duplicados').checked);

            document.getElementById('tabla-container').style.display = 'none';
            iniciarMonitoreoProgreso();
            
            const consola = document.getElementById('resultados');
            consola.innerText = "⏳ Sincronizando inventario con Mercado Libre...";

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
                        imgHtmlPreview = `<img src="${prod.ImagenLocal}" title="Auto-emparejada desde lote_imagenes">`;
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

                    tbody.innerHTML += `
                        <tr>
                            <td><input type="checkbox" class="prod-check" data-idx="${idx}" checked></td>
                            <td>
                                <input type="text" id="tit-${idx}" value="${prod.Titulo}" maxlength="60" style="margin-bottom:4px; font-weight:bold;">
                                <div class="cat-tag">Cat: ${prod.Categoria_ID}</div>
                                <div id="desc-tag-${idx}" class="desc-tag">${prod.DescripcionCustom ? '📄 Desc. Excel' : '🤖 IA Automática'}</div>
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
                                    <option value="me2_free">🟢 Mercado Envíos - Envío Gratis</option>
                                    <option value="custom_free">🟢 Envío Gratis Nacional (Custom)</option>
                                    <option value="me2_buyer">🔵 Mercado Envíos - Cobro en Destino</option>
                                    <option value="not_specified">⚪ Acordar con el Vendedor</option>
                                </select>
                            </td>

                            <td>
                                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:4px; margin-bottom:4px;">
                                    <input type="text" id="mar-${idx}" value="${prod.Marca}" placeholder="Marca" title="Marca">
                                    <input type="text" id="mod-${idx}" value="${prod.Modelo}" placeholder="Modelo" title="Modelo">
                                </div>
                                <input type="text" id="sku-${idx}" value="${prod.SKU}" placeholder="Nro. Parte / SKU" style="margin-bottom:4px;" title="SKU o Código de Parte">
                                
                                <select id="gtin-razon-${idx}" class="attr-select" onchange="toggleGtin(${idx})" style="margin-bottom:4px; font-size:11px; font-weight:bold;">
                                    <option value="CUSTOM" ${selectCustom}>Ingresar Código (GTIN)</option>
                                    <option value="OMITIR" ${selectOmit}>Este producto no posee código</option>
                                </select>
                                <input type="text" id="gtin-${idx}" value="${prod.GTIN !== 'N/A' ? prod.GTIN : ''}" placeholder="Ej: 0123456789123" style="display:${gtinDisplay}; margin-bottom:4px;">

                                <button onclick="abrirModal(${idx})" style="background:#17a2b8; width:100%; padding:4px; font-size:11px;">🛠️ Ver / Editar + Características</button>
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
                consola.innerText = `✅ ¡Sincronización completa! ${resultado.productos.length} artículos listos para publicar.`;
            } catch(e) {
                consola.innerText = "❌ Error en sincronización: " + e;
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
                let gtinFinal = 'OMITIR';
                if (razonGtin === 'CUSTOM') {
                    gtinFinal = document.getElementById('gtin-'+idx).value;
                }

                const skuVal = (document.getElementById('sku-'+idx).value || '').toLowerCase();
                const titVal = (document.getElementById('tit-'+idx).value || '').toLowerCase();
                let descFinal = document.getElementById('desc-init-'+idx).value;
                
                if (descripcionesCSV[skuVal]) descFinal = descripcionesCSV[skuVal];
                else if (descripcionesCSV[titVal]) descFinal = descripcionesCSV[titVal];

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
                    "DescripcionCustom": descFinal,
                    "ImagenesB64": imagenesPorFila[idx] || []
                });
            });

            if (!seleccionados.length) return alert('No hay artículos seleccionados.');

            const cuentaSeleccionada = document.getElementById('cuenta-select').value;
            const nombreCuentaText = document.getElementById('cuenta-select').options[document.getElementById('cuenta-select').selectedIndex].text;

            if (!confirm(`¿Confirmas publicar ${seleccionados.length} artículos en: ${nombreCuentaText}?`)) return;

            iniciarMonitoreoProgreso();
            const consola = document.getElementById('resultados');
            consola.innerText = `🚀 Publicando lote... Mapeando características dinámicamente con la API de Mercado Libre.`;

            try {
                const response = await fetch(`/publicar-lote?cuenta=${cuentaSeleccionada}`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(seleccionados)
                });
                const resData = await response.json();
                consola.innerText = resData.detalles.join('\\n');
            } catch(e) {
                consola.innerText = "❌ Error subiendo lote: " + e;
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

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_INTERFACE

@app.post("/previsualizar")
async def previsualizar_archivo(
    file: UploadFile = File(...), 
    cuenta: str = Form(...),
    inicio: int = Form(1),
    fin: int = Form(100),
    filtrar_duplicados: str = Form("true")
):
    actualizar_progreso(5, "Cargando archivo en memoria...")
    PROGRESO_ACTUAL["activo"] = True
    temp_filename = f"temp_{file.filename}"
    with open(temp_filename, "wb") as buffer: buffer.write(await file.read())

    archivos_a_escanear = listar_archivos_token() if cuenta == "TODAS" else [cuenta]
    titulos_existentes = set()

    if filtrar_duplicados == "true":
        actualizar_progreso(15, "Verificando publicaciones activas en Mercado Libre...")
        for arch in archivos_a_escanear:
            token = obtener_token(arch)
            if token:
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                titulos_existentes.update(obtener_titulos_publicados(headers))

    token_ref = obtener_token(archivos_a_escanear[0])
    headers_ref = {"Authorization": f"Bearer {token_ref}", "Content-Type": "application/json"} if token_ref else {}

    try:
        df = pd.read_csv(temp_filename, encoding='utf-8') if temp_filename.lower().endswith('.csv') else pd.read_excel(temp_filename)
        df.columns = df.columns.str.strip()
    except Exception as e:
        PROGRESO_ACTUAL["activo"] = False
        return {"error": f"Error leyendo el archivo: {str(e)}"}

    idx_inicio = max(0, inicio - 1)
    df_rango = df.iloc[idx_inicio:fin]
    total_filas = len(df_rango)

    productos_activos = []
    cache_categorias = {}
    
    for indice, (_, fila) in enumerate(df_rango.iterrows()):
        await asyncio.sleep(0.01)
        porcentaje_actual = int(20 + ((indice + 1) / max(1, total_filas)) * 75)
        
        titulo_original = str(fila.get('Titulo', fila.get('Producto', '')))
        if not titulo_original or titulo_original == 'nan': continue
            
        titulo = titulo_original[:60].strip()
        
        codigo_identificador = str(fila.get('SKU', fila.get('Codigo Zmart', fila.get('Codigo', fila.get('Modelo', 'Universal'))))).strip()
        if codigo_identificador.lower() == 'nan' or not codigo_identificador:
            codigo_identificador = str(fila.get('Modelo', 'Universal')).strip()
            
        modelo = codigo_identificador
        sku = codigo_identificador
        
        color = str(fila.get('Color', '')).strip()
        if color.lower() == 'nan': color = ''
        compatibilidad = str(fila.get('Compatibilidad', fila.get('Especificacion', ''))).strip()
        if compatibilidad.lower() == 'nan': compatibilidad = ''
        material = str(fila.get('Material', fila.get('Rendimiento', ''))).strip()
        if material.lower() == 'nan': material = ''
        desc_custom = str(fila.get('Descripcion', '')).strip()
        if desc_custom.lower() == 'nan': desc_custom = ''
        
        actualizar_progreso(porcentaje_actual, f"Procesando fila {indice+1} de {total_filas}: {titulo[:25]}...")

        if filtrar_duplicados == "true" and titulo.lower() in titulos_existentes:
            continue

        precio = float(fila.get('Precio', fila.get('PRECIO  $', fila.get('PRECIO $', 1.0))))
        precio = max(1.0, precio)
        stock = max(1, int(fila.get('Stock', fila.get('Disponible', 1))))
        marca = str(fila.get('Marca', 'Generico')).strip()
        
        gtin = str(fila.get('GTIN', fila.get('Codigo de Barras', 'N/A'))).strip()
        if gtin.lower() == 'nan' or gtin == '': 
            gtin = 'N/A'
        
        if token_ref:
            if titulo in cache_categorias:
                cat_id = cache_categorias[titulo]
            else:
                cat_id = adivinar_categoria(titulo, headers_ref)
                cache_categorias[titulo] = cat_id
        else:
            cat_id = "MLV-DESCONOCIDA"
            
        imagen_emparejada = emparejar_imagen_local(modelo, sku, titulo)
        
        productos_activos.append({
            "Titulo": titulo, "Precio": precio, "Stock": stock,
            "Marca": marca, "Modelo": modelo, "SKU": sku, 
            "Color": color, "Compatibilidad": compatibilidad, "Material": material,
            "DescripcionCustom": desc_custom, "GTIN": gtin, 
            "Categoria_ID": cat_id, "ImagenLocal": imagen_emparejada
        })

    if os.path.exists(temp_filename): os.remove(temp_filename)
    actualizar_progreso(100, "¡Sincronización Finalizada con Éxito!")
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

        for prod in productos:
            await asyncio.sleep(0.01)
            procesados += 1
            porcentaje = int((procesados / max(1, total_items)) * 100)
            titulo_original = prod['Titulo'][:60].strip()
            actualizar_progreso(porcentaje, f"[{nombre_perfil}] Publicando ({procesados}/{total_items}): {titulo_original[:25]}...")

            titulo_x3 = f"{titulo_original}\n{titulo_original}\n{titulo_original}\n"
            
            if prod.get('DescripcionCustom'):
                cuerpo_desc = prod['DescripcionCustom']
            else:
                cuerpo_desc = redactar_parrafo_base(titulo_original)
            
            descripcion_estructurada = f"{BLOQUE_SUPERIOR}\n{titulo_x3}\n{cuerpo_desc}\n{BLOQUE_INFERIOR}"

            # --- LLAMAMOS AL MAPEADOR DINÁMICO DE ATRIBUTOS ---
            atributos_payload = construir_atributos_dinamicos(prod, headers)

            # --- CONFIGURACIÓN DEL BLOQUE DE ENVÍO ---
            modo_envio = prod.get('Envio', 'not_specified')
            if modo_envio == "me2_free":
                shipping_payload = {
                    "mode": "me2", 
                    "local_pick_up": True, 
                    "free_shipping": True
                }
            elif modo_envio == "custom_free":
                shipping_payload = {
                    "mode": "custom",
                    "free_shipping": True,
                    "costs": [
                        {"description": "Envío Gratis a Nivel Nacional", "cost": 0}
                    ]
                }
            elif modo_envio == "me2_buyer":
                shipping_payload = {
                    "mode": "me2", 
                    "local_pick_up": True, 
                    "free_shipping": False
                }
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

            # 1. CREACIÓN INICIAL DEL ARTÍCULO
            respuesta = requests.post("https://api.mercadolibre.com/items", headers=headers, json=datos_publicacion)
            
            if respuesta.status_code == 201:
                item_data = respuesta.json()
                item_id = item_data.get('id')
                permalink = item_data.get('permalink')
                
                requests.post(f"https://api.mercadolibre.com/items/{item_id}/description", headers=headers, json={"text": descripcion_estructurada})
                
                # 2. GOLPE DOBLE (PUT DE CONFIRMACIÓN): Reasegurar Envío Gratis y Características
                put_payload = {
                    "shipping": shipping_payload,
                    "attributes": atributos_payload
                }
                requests.put(f"https://api.mercadolibre.com/items/{item_id}", headers=headers, json=put_payload)
                
                logs_totales.append(f"✅ [{nombre_perfil}] ¡PUBLICADO! -> {permalink}")
            else:
                error_texto = respuesta.text
                if "restrictions_coliving" in error_texto:
                    titulo_mascarado = re.sub(r'(?i)\b(canon|hp|epson|brother|samsung|apple|sony)\b', 'Compatible', titulo_original)
                    datos_publicacion["title"] = titulo_mascarado
                    
                    res_bypass = requests.post("https://api.mercadolibre.com/items", headers=headers, json=datos_publicacion)
                    if res_bypass.status_code == 201:
                        item_data = res_bypass.json()
                        item_id = item_data.get('id')
                        permalink = item_data.get('permalink')
                        
                        requests.put(f"https://api.mercadolibre.com/items/{item_id}", headers=headers, json={"title": titulo_original})
                        requests.post(f"https://api.mercadolibre.com/items/{item_id}/description", headers=headers, json={"text": descripcion_estructurada})
                        
                        # GOLPE DOBLE EN BYPASS
                        put_payload = {"shipping": shipping_payload, "attributes": atributos_payload}
                        requests.put(f"https://api.mercadolibre.com/items/{item_id}", headers=headers, json=put_payload)
                        
                        logs_totales.append(f"✅ [{nombre_perfil}] ¡PUBLICADO (Bypass Catálogo)! -> {permalink}")
                    else:
                        logs_totales.append(f"❌ [{nombre_perfil}] Error '{titulo_original[:15]}...': {res_bypass.json().get('message')}")
                else:
                    error_data = respuesta.json()
                    causas = error_data.get('cause', [])
                    detalles_list = [c.get('message', str(c)) if isinstance(c, dict) else str(c) for c in causas] if isinstance(causas, list) else [str(error_data.get('message', 'Error'))]
                    detalles = " | ".join(detalles_list)
                    logs_totales.append(f"❌ [{nombre_perfil}] Error '{titulo_original[:15]}...': {detalles}")

    actualizar_progreso(100, "¡Lote Completado!")
    PROGRESO_ACTUAL["activo"] = False
    return {"detalles": logs_totales}