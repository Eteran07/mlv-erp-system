import sys
import re

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

header_addition = '''
CARPETA_TEMP = "temp_archivos"
if not os.path.exists(CARPETA_TEMP):
    os.makedirs(CARPETA_TEMP)

def limpiar_carpeta_temp():
    for f in os.listdir(CARPETA_TEMP):
        try: os.remove(os.path.join(CARPETA_TEMP, f))
        except: pass
limpiar_carpeta_temp()
'''

if 'CARPETA_TEMP = "temp_archivos"' not in content:
    # Insert after CARPETA_CATALOGOS
    content = content.replace(
        'CARPETA_CATALOGOS = "catalogos_generados"', 
        'CARPETA_CATALOGOS = "catalogos_generados"\n' + header_addition
    )

content = re.sub(r'temp_filename = f"temp_sheets_(.*)"', r'temp_filename = os.path.join(CARPETA_TEMP, f"temp_sheets_\1")', content)
content = re.sub(r'temp_filename = f"temp_cols_(.*)"', r'temp_filename = os.path.join(CARPETA_TEMP, f"temp_cols_\1")', content)
content = re.sub(r'temp_filename = f"temp_preview_(.*)"', r'temp_filename = os.path.join(CARPETA_TEMP, f"temp_preview_\1")', content)
content = re.sub(r'temp_filename = f"temp_(.*)"', r'temp_filename = os.path.join(CARPETA_TEMP, f"temp_\1")', content)
content = re.sub(r'temp_filename = f"temp_catalogo_(.*)"', r'temp_filename = os.path.join(CARPETA_TEMP, f"temp_catalogo_\1")', content)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
