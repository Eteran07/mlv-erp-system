import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_endpoint = '''@app.get("/api/galeria-local")
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
    return lista_fotos'''

new_endpoint = '''from fastapi.responses import FileResponse
from fastapi import HTTPException
import urllib.parse

@app.get("/api/imagen-local/{nombre}")
def endpoint_imagen_local(nombre: str):
    nombre_limpio = urllib.parse.unquote(nombre)
    ruta = os.path.join(CARPETA_LOTE_IMAGENES, nombre_limpio)
    if os.path.exists(ruta):
        return FileResponse(ruta)
    raise HTTPException(status_code=404, detail="Imagen no encontrada")

@app.get("/api/galeria-local")
def endpoint_galeria_local():
    if not os.path.exists(CARPETA_LOTE_IMAGENES):
        return []
    
    lista_fotos = []
    for arc in sorted(os.listdir(CARPETA_LOTE_IMAGENES)):
        ext = arc.rsplit(".", 1)[-1].lower()
        if ext in ["jpg", "jpeg", "png", "webp"]:
            lista_fotos.append({"nombre": arc})
    return lista_fotos'''

content = content.replace(old_endpoint, new_endpoint)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
