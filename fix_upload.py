import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

import_old = "from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status"
import_new = "from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status\nfrom typing import List"

content = content.replace(import_old, import_new)

endpoint = '''
@app.post("/api/subir-lote-imagenes")
def api_subir_lote_imagenes(files: List[UploadFile] = File(...)):
    if not os.path.exists(CARPETA_LOTE_IMAGENES):
        os.makedirs(CARPETA_LOTE_IMAGENES)
    guardadas = 0
    for f in files:
        if f.filename:
            ruta = os.path.join(CARPETA_LOTE_IMAGENES, f.filename)
            with open(ruta, "wb") as buffer:
                buffer.write(f.file.read())
            guardadas += 1
    return {"mensaje": f"Se subieron {guardadas} imágenes exitosamente al servidor."}

@app.get("/api/galeria-local")'''

content = content.replace('\n@app.get("/api/galeria-local")', endpoint)

html_old = '''                    <button onclick="cargarGaleriaLocal()" style="background:#0284c7; padding:10px 18px; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">🔄 Actualizar Galería</button>
                </div>
                <div id="galeria-contenedor" class="gallery-grid"></div>'''

html_new = '''                    <div style="display: flex; gap: 10px;">
                        <input type="file" id="input-subir-lote" multiple accept="image/*" style="display:none;" onchange="subirLoteImagenesServidor(this)">
                        <button onclick="document.getElementById('input-subir-lote').click()" style="background:#10b981; padding:10px 18px; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">📤 Subir Imágenes al Servidor</button>
                        <button onclick="cargarGaleriaLocal()" style="background:#0284c7; padding:10px 18px; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">🔄 Actualizar Galería</button>
                    </div>
                </div>
                <div id="galeria-contenedor" class="gallery-grid"></div>'''

content = content.replace(html_old, html_new)

js_old = '''        async function cargarGaleriaLocal() {'''
js_new = '''        async function subirLoteImagenesServidor(inputElem) {
            if(!inputElem.files || inputElem.files.length === 0) return;
            const cont = document.getElementById('galeria-contenedor');
            cont.innerHTML = "<div style='grid-column: 1 / -1; text-align: center; padding: 20px;'>Subiendo " + inputElem.files.length + " imágenes al servidor... Por favor espera.</div>";
            const fd = new FormData();
            for(let i=0; i<inputElem.files.length; i++){
                fd.append("files", inputElem.files[i]);
            }
            try {
                const res = await fetch('/api/subir-lote-imagenes', { method: 'POST', body: fd });
                const data = await res.json();
                alert(data.mensaje);
                inputElem.value = "";
                cargarGaleriaLocal();
            } catch(e) {
                alert("Error al subir las imágenes.");
            }
        }

        async function cargarGaleriaLocal() {'''

content = content.replace(js_old, js_new)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
