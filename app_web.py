import os
import json
import requests
import pandas as pd
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from google import genai

load_dotenv()

app = FastAPI(title="ERP Mercado Libre - Panel Interactivo")

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
- Trabajamos con agentes de retención
- Enviamos a todo el País.
**************************************************************************************************
COMENTARIOS:
- Realice todas las preguntas necesarias Antes de ofertar.
- El equipo de ventas está a tu disposición para responder tus consultas.
- Horario: Lunes A Viernes de 8:30am A 5:30pm
"""

def obtener_token():
    try:
        with open("tokens_ml.json", "r") as archivo:
            return json.load(archivo).get("access_token")
    except FileNotFoundError:
        return None

def adivinar_categoria(titulo, headers):
    url = "https://api.mercadolibre.com/sites/MLV/domain_discovery/search"
    response = requests.get(url, headers=headers, params={"q": titulo})
    if response.status_code == 200 and len(response.json()) > 0:
        return response.json()[0].get("category_id")
    return "MLV-DESCONOCIDA"

def redactar_parrafo(titulo):
    if not USAR_IA:
        return "Producto garantizado de excelente rendimiento y máxima durabilidad."
    try:
        respuesta = cliente_ia.models.generate_content(
            model='gemini-2.0-flash',
            contents=f"Escribe un párrafo corto, persuasivo y técnico sobre el producto: '{titulo}'."
        )
        return respuesta.text.strip()
    except Exception:
        return "Producto garantizado de excelente rendimiento y máxima durabilidad."

# Interfaz HTML Interactiva
HTML_INTERFACE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ERP Mercado Libre - Previsualización y Control</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f2f5; margin: 0; padding: 30px; }
        .container { max-width: 1100px; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); margin: auto; }
        h1 { color: #1a1a1a; text-align: center; margin-bottom: 5px; }
        .subtitle { text-align: center; color: #666; margin-bottom: 25px; }
        .upload-section { display: flex; gap: 15px; margin-bottom: 25px; align-items: center; background: #f8f9fa; padding: 20px; border-radius: 8px; border: 1px solid #dee2e6; }
        input[type="file"] { padding: 8px; background: white; border: 1px solid #ccc; border-radius: 4px; flex-grow: 1; }
        button { background: #007bff; color: white; border: none; padding: 10px 20px; font-weight: bold; border-radius: 6px; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #0056b3; }
        .btn-success { background: #28a745; width: 100%; padding: 14px; font-size: 16px; margin-top: 20px; }
        .btn-success:hover { background: #218838; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }
        th, td { border: 1px solid #dee2e6; padding: 10px; text-align: left; }
        th { background-color: #343a40; color: white; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .log-box { background: #1e1e1e; color: #00ff66; padding: 15px; border-radius: 8px; font-family: monospace; height: 180px; overflow-y: auto; white-space: pre-wrap; font-size: 12px; margin-top: 20px; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 ERP Mercado Libre</h1>
        <div class="subtitle">Módulo de Control, Previsualización y Publicación Semiautomática</div>
        
        <div class="upload-section">
            <input type="file" id="file" name="file" accept=".xlsx">
            <button onclick="cargarInventario()">Cargar y Previsualizar</button>
        </div>

        <div id="tabla-container" class="hidden">
            <h3>Paso 2: Verifica los datos antes de publicar</h3>
            <p style="color: #666; font-size: 13px;">Desmarca los productos que no desees enviar.</p>
            <table>
                <thead>
                    <tr>
                        <th><input type="checkbox" id="select-all" checked onclick="toggleAll(this)"></th>
                        <th>Título</th>
                        <th>Precio ($)</th>
                        <th>Stock</th>
                        <th>Categoría ML</th>
                        <th>Marca / Modelo</th>
                    </tr>
                </thead>
                <tbody id="tabla-body"></tbody>
            </table>
            <button class="btn-success" onclick="ejecutarPublicacionSeleccionada()">🚀 Confirmar y Publicar Seleccionados</button>
        </div>

        <h3>Consola de Estado:</h3>
        <div id="resultados" class="log-box">Esperando carga de inventario...</div>
    </div>

    <script>
        let datosGlobales = [];

        async function cargarInventario() {
            const fileInput = document.getElementById('file');
            if (fileInput.files.length === 0) {
                alert('Por favor selecciona un archivo Excel primero.');
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            const consola = document.getElementById('resultados');
            consola.innerText = "⏳ Leyendo matriz, consultando categorías y preparando descripciones...";

            const response = await fetch('/previsualizar', { method: 'POST', body: formData });
            const resultado = await response.json();

            if (resultado.error) {
                consola.innerText = "❌ Error: " + resultado.error;
                return;
            }

            datosGlobales = resultado.productos;
            const tbody = document.getElementById('tabla-body');
            tbody.innerHTML = "";

            datosGlobales.forEach((prod, index) => {
                tbody.innerHTML += `
                    <tr>
                        <td><input type="checkbox" class="prod-check" data-index="${index}" checked></td>
                        <td><b>${prod.Titulo}</b></td>
                        <td>$${prod.Precio}</td>
                        <td>${prod.Stock}</td>
                        <td><code>${prod.Categoria_ID}</code></td>
                        <td>${prod.Marca} / ${prod.Modelo}</td>
                    </tr>
                `;
            });

            document.getElementById('tabla-container').classList.remove('hidden');
            consola.innerText = `✅ ¡Previsualización lista! Se cargaron ${datosGlobales.length} productos para tu revisión.`;
        }

        function toggleAll(source) {
            checkboxes = document.querySelectorAll('.prod-check');
            checkboxes.forEach(cb => cb.checked = source.checked);
        }

        async function ejecutarPublicacionSeleccionada() {
            const checks = document.querySelectorAll('.prod-check');
            const seleccionados = [];

            checks.forEach(cb => {
                if (cb.checked) {
                    seleccionados.push(datosGlobales[cb.dataset.index]);
                }
            });

            if (seleccionados.length === 0) {
                alert('No hay productos seleccionados para publicar.');
                return;
            }

            const consola = document.getElementById('resultados');
            consola.innerText = "🚀 Enviando lote seleccionado a Mercado Libre...";

            const response = await fetch('/publicar-lote', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(seleccionados)
            });

            const resultado = await response.json();
            consola.innerText = resultado.detalles.join('\\n');
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_INTERFACE

@app.post("/previsualizar")
async def previsualizar_excel(file: UploadFile = File(...)):
    temp_filename = f"temp_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        buffer.write(await file.read())

    token = obtener_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"} if token else {}

    try:
        df = pd.read_excel(temp_filename)
        # Limpiamos los nombres de las columnas para evitar errores de espacios invisibles
        df.columns = df.columns.str.strip()
    except Exception as e:
        return {"error": f"Error leyendo Excel: {str(e)}"}

    productos_procesados = []
    
    # Solo tomamos los primeros 100 productos por seguridad visual en pruebas
    for index, fila in df.head(100).iterrows():
        # Mapeo Inteligente: Busca el nombre oficial o el nombre de tu matriz "Maxiprint"
        titulo = str(fila.get('Titulo', fila.get('Producto', '')))
        if not titulo or titulo == 'nan':
            continue # Saltamos filas vacías
            
        precio = float(fila.get('Precio', fila.get('PRECIO  $', fila.get('PRECIO $', 0))))
        stock = int(fila.get('Stock', fila.get('Disponible', 0)))
        marca = str(fila.get('Marca', 'Generico'))
        modelo = str(fila.get('Modelo', fila.get('Codigo Zmart', 'Universal')))
        imagen_url = str(fila.get('Imagen', 'https://dummyimage.com/600x600/000/fff.jpg&text=FOTO'))
        
        cat_id = adivinar_categoria(titulo, headers) if token else "MLV-DESCONOCIDA"
        
        productos_procesados.append({
            "Titulo": titulo,
            "Precio": precio,
            "Stock": stock,
            "Marca": marca,
            "Modelo": modelo,
            "Imagen": imagen_url,
            "Categoria_ID": cat_id
        })

    if os.path.exists(temp_filename):
        os.remove(temp_filename)

    return {"productos": productos_procesados}

@app.post("/publicar-lote")
async def publicar_lote(productos: list[dict]):
    token = obtener_token()
    if not token:
        return {"detalles": ["❌ Error: Token de Mercado Libre no válido."]}

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    logs = []

    for prod in productos:
        titulo_original = prod['Titulo']
        # 🛡️ PROTECCIÓN: Cortamos el título a máximo 60 caracteres exactos
        titulo_ml = titulo_original[:60].strip()
        
        titulo_x3 = f"{titulo_original}\n{titulo_original}\n{titulo_original}\n"
        parrafo_dinamico = redactar_parrafo(titulo_original)
        descripcion_completa = f"{BLOQUE_SUPERIOR}\n{titulo_x3}\n{parrafo_dinamico}\n{BLOQUE_INFERIOR}"

        datos_publicacion = {
            "title": titulo_ml,  # Usamos el título recortado
            "category_id": prod['Categoria_ID'],
            "price": prod['Precio'],
            "currency_id": "USD",
            "available_quantity": prod['Stock'],
            "buying_mode": "buy_it_now",
            "condition": "new",
            "listing_type_id": "bronze", # Si este da error, el nuevo log te lo dirá
            "pictures": [{"source": prod['Imagen']}],
            "attributes": [
                {"id": "BRAND", "value_name": prod['Marca']},
                {"id": "MODEL", "value_name": prod['Modelo']}
            ]
        }

        respuesta = requests.post("https://api.mercadolibre.com/items", headers=headers, json=datos_publicacion)
        
        if respuesta.status_code == 201:
            item_data = respuesta.json()
            item_id = item_data.get('id')
            permalink = item_data.get('permalink')
            
            requests.post(f"https://api.mercadolibre.com/items/{item_id}/description", headers=headers, json={"text": descripcion_completa})
            logs.append(f"✅ ¡PUBLICADO! -> {permalink}")
        else:
            # 🔍 EXTRACCIÓN PROFUNDA DEL ERROR
            error_data = respuesta.json()
            causas = error_data.get('cause', [])
            
            if causas:
                # Extraemos el mensaje real de Mercado Libre (ej. "Title length must be less than 60")
                detalles = " | ".join([c.get('message', 'Error') for c in causas])
                logs.append(f"❌ Error en '{titulo_ml[:15]}...': {detalles}")
            else:
                logs.append(f"❌ Error en '{titulo_ml[:15]}...': {error_data.get('message', 'Desconocido')}")

    return {"detalles": logs}