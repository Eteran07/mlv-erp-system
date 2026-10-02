import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

helper_code = '''
def auto_reparar_imagen_ml(ruta_completa):
    if not HAS_PIL: return None
    try:
        cambiada = False
        with Image.open(ruta_completa) as img:
            w, h = img.size
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                cambiada = True
            
            if w < 500 or h < 500:
                ratio = max(500.0 / w, 500.0 / h)
                new_w = max(500, int(w * ratio))
                new_h = max(500, int(h * ratio))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                cambiada = True
            
            if cambiada:
                img.save(ruta_completa, "JPEG", quality=95)
                return f"Auto-corregida (Ahora {img.width}x{img.height}px)"
    except Exception as e:
        return f"Error en archivo de imagen: {str(e)}"
    return None

def emparejar_imagen_local('''

if 'def auto_reparar_imagen_ml' not in content:
    content = content.replace("def emparejar_imagen_local(", helper_code)

idx_start = content.find('if limpio_val and len(limpio_val) > 1 and (limpio_val == limpio_arc')
idx_end = content.find('except Exception as e:', idx_start)

if idx_start != -1 and idx_end != -1:
    old_match = content[idx_start:idx_end]
    new_match = '''if limpio_val and len(limpio_val) > 1 and (limpio_val == limpio_arc or limpio_val in limpio_arc or limpio_arc in limpio_val):
                ruta_completa = os.path.join(CARPETA_LOTE_IMAGENES, arc)
                alerta_auto = auto_reparar_imagen_ml(ruta_completa)
                
                try:
                    size_mb = os.path.getsize(ruta_completa) / (1024*1024)
                    if size_mb > 9.5:
                        alerta_auto = (alerta_auto or "") + " | ⚠️ Peligro: Imagen pesa casi 10MB (límite ML)."
                except: pass

                try:
                    with open(ruta_completa, "rb") as f:
                        raw_bytes = f.read()
                        data = base64.b64encode(raw_bytes).decode("utf-8")
                        mime = "image/jpeg" if ext in ["jpg", "jpeg"] else f"image/{ext}"
                        return f"data:{mime};base64,{data}", alerta_auto
                '''
    content = content.replace(old_match, new_match)

old_upload = '''            with open(ruta, "wb") as buffer:
                buffer.write(f.file.read())
            guardadas += 1'''

new_upload = '''            with open(ruta, "wb") as buffer:
                buffer.write(f.file.read())
            auto_reparar_imagen_ml(ruta)
            guardadas += 1'''

content = content.replace(old_upload, new_upload)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
