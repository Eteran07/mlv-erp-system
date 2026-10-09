# -*- coding: utf-8 -*-
import re

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscamos donde se añade un log de éxito en publicar_lote
# "logs_totales.append(f"✅ [{nombre_perfil}] ¡PUBLICADO! -> {url_publicacion}")" o similar
# Aca vemos: `logs_totales.append(f"✅ [{nombre_perfil}] ¡PUBLICADO! -> {permalink}")`
success_marker = """                    logs_totales.append(f"✅ [{nombre_perfil}] ¡PUBLICADO! -> {permalink}")
                    PROGRESO_ACTUAL["exitos"] += 1"""

new_success_code = """                    logs_totales.append(f"✅ [{nombre_perfil}] ¡PUBLICADO! -> {permalink}")
                    PROGRESO_ACTUAL["exitos"] += 1
                    
                    # Actualizar ULTIMO_REPORTE
                    global ULTIMO_REPORTE
                    if type(ULTIMO_REPORTE) is dict and "todos" in ULTIMO_REPORTE:
                        for row_data in ULTIMO_REPORTE["todos"]:
                            if str(row_data.get("SKU", "")) == str(sku):
                                row_data["Estado Publicación"] = f"Ya publicado"
"""

if success_marker in content:
    content = content.replace(success_marker, new_success_code)
    
    # Hay otro para Bypass Catálogo
    bypass_marker = """                            logs_totales.append(f"✅ [{nombre_perfil}] ¡PUBLICADO (Bypass Catálogo)! -> {permalink}")
                            PROGRESO_ACTUAL["exitos"] += 1"""
    
    new_bypass_code = """                            logs_totales.append(f"✅ [{nombre_perfil}] ¡PUBLICADO (Bypass Catálogo)! -> {permalink}")
                            PROGRESO_ACTUAL["exitos"] += 1
                            
                            # Actualizar ULTIMO_REPORTE
                            if type(ULTIMO_REPORTE) is dict and "todos" in ULTIMO_REPORTE:
                                for row_data in ULTIMO_REPORTE["todos"]:
                                    if str(row_data.get("SKU", "")) == str(sku):
                                        row_data["Estado Publicación"] = f"Ya publicado"
"""
    content = content.replace(bypass_marker, new_bypass_code)

    with open('app_web.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Replaced successfully')
else:
    print('Success marker not found')