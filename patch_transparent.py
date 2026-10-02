import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

helper_code = '''def auto_reparar_imagen_ml(ruta_completa):
    if not HAS_PIL: return None
    try:
        cambiada = False
        with Image.open(ruta_completa) as img:
            # 1. Manejo de transparencia a fondo blanco
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                if img.mode == "P":
                    img = img.convert("RGBA")
                fondo_blanco = Image.new("RGB", img.size, (255, 255, 255))
                try:
                    fondo_blanco.paste(img, mask=img.split()[3] if img.mode == "RGBA" else img.split()[1])
                except:
                    fondo_blanco.paste(img)
                img = fondo_blanco
                cambiada = True
            elif img.mode != "RGB":
                img = img.convert("RGB")
                cambiada = True

            # 2. Asegurar tamano minimo 500x500 y formato cuadrado si es muy pequena
            w, h = img.size
            if w < 500 or h < 500:
                lado_lienzo = max(500, w, h)
                lienzo = Image.new("RGB", (lado_lienzo, lado_lienzo), (255, 255, 255))
                
                ratio = lado_lienzo / max(w, h)
                new_w = int(w * ratio)
                new_h = int(h * ratio)
                img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                offset_x = (lado_lienzo - new_w) // 2
                offset_y = (lado_lienzo - new_h) // 2
                lienzo.paste(img_resized, (offset_x, offset_y))
                
                img = lienzo
                cambiada = True

            if cambiada:
                ext = ruta_completa.rsplit(".", 1)[-1].lower()
                formato = "PNG" if ext == "png" else ("WEBP" if ext == "webp" else "JPEG")
                img.save(ruta_completa, formato, quality=95)
                return f"Auto-corregida (Fondo blanco, {img.width}x{img.height}px)"
    except Exception as e:
        return f"Error en archivo de imagen: {str(e)}"
    return None'''

# Buscamos y reemplazamos la funcion entera
idx_start = content.find('def auto_reparar_imagen_ml')
idx_end = content.find('def emparejar_imagen_local')

if idx_start != -1 and idx_end != -1:
    old_func = content[idx_start:idx_end].strip()
    content = content.replace(old_func, helper_code.strip())

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
