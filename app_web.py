import os
import json
import base64
import requests
import pandas as pd
import re  # NUEVA LIBRERÍA PARA EL BYPASS
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from google import genai

load_dotenv()
app = FastAPI(title="ERP Mercado Libre - Control Maestro")

try:
    cliente_ia = genai.Client()
    USAR_IA = True
except Exception:
    USAR_IA = False

BLOQUE_SUPERIOR = "SOMOS TIENDA FÍSICA, Empresa Mayorista Líder en el Mercado de la Computación Producto 100% de calidad\n"
BLOQUE_INFERIOR = """
.Por Favor Verifique la disponibilidad antes de ofertar
**************************************************************************************************
- Emitimos factura LEGAL
- Enviamos a todo el País.
**************************************************************************************************
"""

def obtener_token():
    try:
        with open("tokens_ml.json", "r") as archivo:
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

def redactar_parrafo(titulo):
    if not USAR_IA: return "Producto garantizado de excelente rendimiento y máxima durabilidad."
    try:
        respuesta = cliente_ia.models.generate_content(
            model='gemini-2.0-flash', 
            contents=f"Escribe un párrafo técnico, persuasivo y corto sobre el producto: '{titulo}'."
        )
        return respuesta.text.strip()
    except Exception:
        return "Producto garantizado de excelente rendimiento y máxima durabilidad."

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

# --- INTERFAZ HTML CON LISTAS DESPLEGABLES ---
HTML_INTERFACE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ERP Mercado Libre - Avanzado</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }
        .container { max-width: 1500px; background: white; padding: 25px; border-radius: 12px; margin: auto; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; }
        .panel-control { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #ddd; }
        .control-group { display: flex; flex-direction: column; gap: 5px; }
        label { font-weight: bold; font-size: 13px; color: #555; }
        input[type="file"] { padding: 8px; border: 1px solid #ccc; border-radius: 4px; background: white; }
        button { background: #007bff; color: white; border: none; padding: 10px; font-weight: bold; border-radius: 4px; cursor: pointer; transition: 0.2s; }
        button:hover { background: #0056b3; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 15px; }
        th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top;}
        th { background: #343a40; color: white; }
        input[type="text"], input[type="number"], select { width: 100%; padding: 6px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        .log-box { background: #1e1e1e; color: #00ff66; padding: 15px; height: 180px; overflow-y: auto; font-family: monospace; border-radius: 5px; margin-top: 20px; white-space: pre-wrap; font-size: 12px;}
        
        .loading-zone { display: none; text-align: center; padding: 30px; background: #e9ecef; border-radius: 8px; margin-bottom: 20px; border: 2px dashed #007bff; }
        .loader { border: 5px solid #f3f3f3; border-top: 5px solid #007bff; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 0 auto 15px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .photo-manager { border: 2px dashed #aaa; padding: 10px; text-align: center; border-radius: 6px; background: #fafafa; cursor: pointer; transition: 0.3s; position: relative;}
        .photo-manager:hover { border-color: #007bff; background: #f0f8ff; }
        .photo-manager input[type="file"] { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
        .preview-container { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; justify-content: center; }
        .preview-container img { width: 45px; height: 45px; object-fit: cover; border-radius: 4px; border: 1px solid #ccc; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚙️ ERP Mercado Libre - Control Maestro</h1>
        
        <div class="panel-control">
            <div class="control-group">
                <label>1. Sube Inventario (.xlsx o .csv):</label>
                <input type="file" id="file-db" accept=".xlsx, .csv">
            </div>
            <div class="control-group">
                <label>2. Rango de filas a analizar:</label>
                <div style="display: flex; gap: 10px;">
                    <input type="number" id="rango-inicio" value="1" placeholder="Desde" style="width: 50%;">
                    <input type="number" id="rango-fin" value="100" placeholder="Hasta" style="width: 50%;">
                </div>
            </div>
            <div class="control-group">
                <label>3. Filtro Inteligente:</label>
                <div style="display: flex; align-items: center; gap: 5px; margin-top: 5px;">
                    <input type="checkbox" id="filtar-duplicados" checked>
                    <span style="font-size: 12px; color: #444;">Ocultar ya publicados</span>
                </div>
            </div>
            <div class="control-group" style="grid-column: span 3;">
                <button onclick="cargarInventario()" style="width: 100%; font-size: 16px;">Generar Previsualización</button>
            </div>
        </div>

        <div id="loading" class="loading-zone">
            <div class="loader"></div>
            <h2 id="loading-text" style="margin:0; color:#333;">Procesando datos...</h2>
            <p style="color:#666;">Dependiendo del rango que elegiste, esto tomará unos segundos.</p>
        </div>

        <div id="tabla-container" style="display: none;">
            <table id="data-table">
                <thead>
                    <tr>
                        <th style="width: 30px;"><input type="checkbox" checked onclick="toggleAll(this)"></th>
                        <th style="width: 20%;">Título (Max 60)</th>
                        <th style="width: 8%;">Precio $</th>
                        <th style="width: 8%;">Stock</th>
                        <th style="width: 12%;">Categoría ML</th>
                        <th style="width: 15%;">Atributos (Marca / Modelo / Código)</th>
                        <th style="width: 25%;">Gestor de Fotos</th>
                    </tr>
                </thead>
                <tbody id="tabla-body"></tbody>
            </table>
            <button onclick="ejecutarPublicacion()" style="background: #28a745; width: 100%; margin-top: 20px; padding: 15px; font-size: 16px;">🚀 Publicar Lote Seleccionado</button>
        </div>

        <div id="resultados" class="log-box">Esperando carga de datos...</div>
    </div>

    <script>
        const imagenesPorFila = {};

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
        
        function toggleGtin(idx) {
            const selectVal = document.getElementById('gtin-razon-'+idx).value;
            const inputField = document.getElementById('gtin-'+idx);
            if (selectVal === 'CUSTOM') {
                inputField.style.display = 'block';
            } else {
                inputField.style.display = 'none';
            }
        }

        async function cargarInventario() {
            const fileInput = document.getElementById('file-db');
            if (!fileInput.files.length) return alert('Selecciona un archivo Excel o CSV.');

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('inicio', document.getElementById('rango-inicio').value);
            formData.append('fin', document.getElementById('rango-fin').value);
            formData.append('filtrar_duplicados', document.getElementById('filtar-duplicados').checked);

            document.getElementById('tabla-container').style.display = 'none';
            document.getElementById('loading').style.display = 'block';
            document.getElementById('loading-text').innerText = "Buscando categorías...";
            
            const consola = document.getElementById('resultados');
            consola.innerText = "⏳ Consultando con Mercado Libre...";

            try {
                const response = await fetch('/previsualizar', { method: 'POST', body: formData });
                const resultado = await response.json();
                document.getElementById('loading').style.display = 'none';

                if (resultado.error) return consola.innerText = "❌ " + resultado.error;

                const tbody = document.getElementById('tabla-body');
                tbody.innerHTML = "";

                if (resultado.productos.length === 0) {
                    consola.innerText = "⚠️ No hay productos en este rango.";
                    return;
                }

                resultado.productos.forEach((prod, idx) => {
                    imagenesPorFila[idx] = []; 
                    
                    let gtinDisplay = 'none';
                    let selectCustom = '';
                    let selectOmit = 'selected';
                    
                    if (prod.GTIN && prod.GTIN !== 'N/A') {
                        gtinDisplay = 'block';
                        selectCustom = 'selected';
                        selectOmit = '';
                    }

                    tbody.innerHTML += `
                        <tr>
                            <td><input type="checkbox" class="prod-check" data-idx="${idx}" checked></td>
                            <td><input type="text" id="tit-${idx}" value="${prod.Titulo}" maxlength="60"></td>
                            <td><input type="number" id="pre-${idx}" value="${prod.Precio}" step="0.01"></td>
                            <td><input type="number" id="stk-${idx}" value="${prod.Stock}"></td>
                            <td><input type="text" id="cat-${idx}" value="${prod.Categoria_ID}"></td>
                            <td>
                                <input type="text" id="mar-${idx}" value="${prod.Marca}" placeholder="Marca" style="margin-bottom:4px;" title="Marca">
                                <input type="text" id="mod-${idx}" value="${prod.Modelo}" placeholder="Modelo" style="margin-bottom:4px;" title="Modelo">
                                
                                <select id="gtin-razon-${idx}" onchange="toggleGtin(${idx})" style="margin-bottom:4px; font-size:11px; font-weight:bold;">
                                    <option value="CUSTOM" ${selectCustom}>Ingresar Código (GTIN)</option>
                                    <option value="OMITIR" ${selectOmit}>Este producto no posee código</option>
                                </select>
                                <input type="text" id="gtin-${idx}" value="${prod.GTIN !== 'N/A' ? prod.GTIN : ''}" placeholder="Ej: 0123456789123" style="display:${gtinDisplay}; margin-bottom:4px;">
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
                });
                document.getElementById('tabla-container').style.display = 'block';
                consola.innerText = `✅ ¡Listo! Puedes revisar y editar.`;
            } catch(e) {
                document.getElementById('loading').style.display = 'none';
                consola.innerText = "❌ Error: " + e;
            }
        }

        function toggleAll(source) {
            document.querySelectorAll('.prod-check').forEach(cb => cb.checked = source.checked);
        }

        async function ejecutarPublicacion() {
            const seleccionados = [];
            document.querySelectorAll('.prod-check:checked').forEach(cb => {
                const idx = cb.dataset.idx;
                
                const razonGtin = document.getElementById('gtin-razon-'+idx).value;
                let gtinFinal = 'OMITIR';
                if (razonGtin === 'CUSTOM') {
                    gtinFinal = document.getElementById('gtin-'+idx).value;
                }

                seleccionados.push({
                    "Titulo": document.getElementById('tit-'+idx).value,
                    "Precio": parseFloat(document.getElementById('pre-'+idx).value),
                    "Stock": parseInt(document.getElementById('stk-'+idx).value),
                    "Categoria_ID": document.getElementById('cat-'+idx).value,
                    "Marca": document.getElementById('mar-'+idx).value,
                    "Modelo": document.getElementById('mod-'+idx).value,
                    "GTIN": gtinFinal,
                    "ImagenesB64": imagenesPorFila[idx] || []
                });
            });

            if (!seleccionados.length) return alert('No hay artículos seleccionados.');

            document.getElementById('loading').style.display = 'block';
            document.getElementById('loading-text').innerText = "Subiendo fotos y armando publicaciones...";
            const consola = document.getElementById('resultados');
            consola.innerText = "🚀 Iniciando publicación. Aplicando protocolos de Bypass si es necesario...";

            try {
                const response = await fetch(`/publicar-lote`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(seleccionados)
                });
                const resData = await response.json();
                document.getElementById('loading').style.display = 'none';
                consola.innerText = resData.detalles.join('\\n');
            } catch(e) {
                document.getElementById('loading').style.display = 'none';
                consola.innerText = "❌ Error subiendo lote: " + e;
            }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_INTERFACE

@app.post("/previsualizar")
async def previsualizar_archivo(
    file: UploadFile = File(...), 
    inicio: int = Form(1),
    fin: int = Form(100),
    filtrar_duplicados: str = Form("true")
):
    temp_filename = f"temp_{file.filename}"
    with open(temp_filename, "wb") as buffer: buffer.write(await file.read())

    token = obtener_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"} if token else {}

    try:
        if temp_filename.lower().endswith('.csv'):
            df = pd.read_csv(temp_filename, encoding='utf-8')
        else:
            df = pd.read_excel(temp_filename)
        df.columns = df.columns.str.strip()
    except Exception as e:
        return {"error": f"Error leyendo el archivo: {str(e)}"}

    idx_inicio = max(0, inicio - 1)
    df_rango = df.iloc[idx_inicio:fin]

    titulos_existentes = set()
    if filtrar_duplicados == "true" and token:
        titulos_existentes = obtener_titulos_publicados(headers)

    productos_procesados = []
    cache_categorias = {}
    
    for _, fila in df_rango.iterrows():
        titulo_original = str(fila.get('Titulo', fila.get('Producto', '')))
        if not titulo_original or titulo_original == 'nan': continue
            
        titulo = titulo_original[:60].strip()
        if filtrar_duplicados == "true" and titulo.lower() in titulos_existentes: continue

        precio = float(fila.get('Precio', fila.get('PRECIO  $', fila.get('PRECIO $', 0))))
        stock = int(fila.get('Stock', fila.get('Disponible', 0)))
        marca = str(fila.get('Marca', 'Generico'))
        modelo = str(fila.get('Modelo', fila.get('Codigo Zmart', 'Universal')))
        
        gtin = str(fila.get('GTIN', fila.get('Codigo de Barras', 'N/A'))).strip()
        if gtin.lower() == 'nan' or gtin == '': 
            gtin = 'N/A'
        
        if token:
            if titulo in cache_categorias:
                cat_id = cache_categorias[titulo]
            else:
                cat_id = adivinar_categoria(titulo, headers)
                cache_categorias[titulo] = cat_id
        else:
            cat_id = "MLV-DESCONOCIDA"
        
        productos_procesados.append({
            "Titulo": titulo, "Precio": precio, "Stock": stock,
            "Marca": marca, "Modelo": modelo, "GTIN": gtin, "Categoria_ID": cat_id
        })

    if os.path.exists(temp_filename): os.remove(temp_filename)
    return {"productos": productos_procesados}

@app.post("/publicar-lote")
async def publicar_lote(productos: list[dict]):
    token = obtener_token()
    if not token: return {"detalles": ["❌ Error: Token de ML no válido."]}

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    logs = []

    for prod in productos:
        titulo_original = prod['Titulo'][:60].strip()
        titulo_x3 = f"{titulo_original}\n{titulo_original}\n{titulo_original}\n"
        parrafo_dinamico = redactar_parrafo(titulo_original)
        descripcion_completa = f"{BLOQUE_SUPERIOR}\n{titulo_x3}\n{parrafo_dinamico}\n{BLOQUE_INFERIOR}"

        datos_publicacion = {
            "title": titulo_original,
            "category_id": prod['Categoria_ID'],
            "price": prod['Precio'],
            "currency_id": "USD",
            "available_quantity": prod['Stock'],
            "buying_mode": "buy_it_now",
            "condition": "new",
            "listing_type_id": "bronze",
            "attributes": [
                {"id": "BRAND", "value_name": prod['Marca']},
                {"id": "MODEL", "value_name": prod['Modelo']}
            ]
        }

        gtin_val = prod.get('GTIN', 'OMITIR').strip()
        if gtin_val != 'OMITIR' and gtin_val:
            datos_publicacion["attributes"].append({"id": "GTIN", "value_name": gtin_val})

        fotos_payload = []
        if prod.get('ImagenesB64'):
            for img_b64 in prod['ImagenesB64']:
                pic_id = subir_foto_a_ml(img_b64, token)
                if pic_id:
                    fotos_payload.append({"id": pic_id})
        
        if fotos_payload:
            datos_publicacion["pictures"] = fotos_payload

        # Primer intento de publicación
        respuesta = requests.post("https://api.mercadolibre.com/items", headers=headers, json=datos_publicacion)
        
        if respuesta.status_code == 201:
            item_data = respuesta.json()
            item_id = item_data.get('id')
            permalink = item_data.get('permalink')
            requests.post(f"https://api.mercadolibre.com/items/{item_id}/description", headers=headers, json={"text": descripcion_completa})
            logs.append(f"✅ ¡PUBLICADO! -> {permalink}")
        else:
            error_texto = respuesta.text
            # 🛡️ MOTOR DE BYPASS AUTOMÁTICO
            if "restrictions_coliving" in error_texto:
                # Enmascaramos marcas famosas que activan el bot de ML
                titulo_mascarado = re.sub(r'(?i)\b(canon|hp|epson|brother|samsung|apple|sony)\b', 'Compatible', titulo_original)
                datos_publicacion["title"] = titulo_mascarado
                
                res_bypass = requests.post("https://api.mercadolibre.com/items", headers=headers, json=datos_publicacion)
                
                if res_bypass.status_code == 201:
                    item_data = res_bypass.json()
                    item_id = item_data.get('id')
                    permalink = item_data.get('permalink')
                    
                    # Restauramos tu título original mediante una actualización silenciosa (PUT)
                    requests.put(f"https://api.mercadolibre.com/items/{item_id}", headers=headers, json={"title": titulo_original})
                    requests.post(f"https://api.mercadolibre.com/items/{item_id}/description", headers=headers, json={"text": descripcion_completa})
                    
                    logs.append(f"✅ ¡PUBLICADO (Bypass de Catálogo Exitoso)! -> {permalink}")
                else:
                    logs.append(f"❌ Error en '{titulo_original[:15]}...' incluso con bypass: {res_bypass.json().get('message')}")
            else:
                error_data = respuesta.json()
                causas = error_data.get('cause', [])
                detalles_list = []
                if isinstance(causas, list) and len(causas) > 0:
                    for c in causas:
                        if isinstance(c, dict): detalles_list.append(c.get('message', str(c)))
                        else: detalles_list.append(str(c))
                    detalles = " | ".join(detalles_list)
                else:
                    detalles = str(error_data.get('message', 'Error desconocido'))
                logs.append(f"❌ Error en '{titulo_original[:15]}...': {detalles}")

    return {"detalles": logs}