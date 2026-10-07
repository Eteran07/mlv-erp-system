import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregamos el endpoint para servir la imagen cruda (en lugar de b64)
endpoint_imagen = '''
from fastapi.responses import FileResponse

@app.get("/api/imagen-local/{nombre}")
def endpoint_imagen_local(nombre: str):
    ruta = os.path.join(CARPETA_LOTE_IMAGENES, nombre)
    if os.path.exists(ruta):
        return FileResponse(ruta)
    raise HTTPException(status_code=404, detail="Imagen no encontrada")

@app.get("/api/galeria-local")'''

content = content.replace('\n@app.get("/api/galeria-local")', endpoint_imagen)

# 2. Actualizamos el Javascript para usar el nuevo endpoint
js_old = '''                        <div class="gallery-item">
                            <img src="">
                            <span></span>
                        </div>'''

js_new = '''                        <div class="gallery-item">
                            <img src="/api/imagen-local/" loading="lazy">
                            <span></span>
                        </div>'''

content = content.replace(js_old, js_new)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
