import sys
import sqlite3
import json

ARCHIVO_MEMORIA_IA_DB = "memoria_ia.db"
ARCHIVO_MEMORIA = "memoria_erp.json"

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update inicializar_bd_ia
old_init = '''        cursor.execute(\'\'\'
            CREATE TABLE IF NOT EXISTS errores_ia ('''
new_init = '''        cursor.execute(\'\'\'
            CREATE TABLE IF NOT EXISTS memoria_erp (
                cuenta TEXT,
                tipo TEXT,
                valor TEXT,
                UNIQUE(cuenta, tipo, valor)
            )
        \'\'\')
        cursor.execute(\'\'\'
            CREATE TABLE IF NOT EXISTS errores_ia ('''

content = content.replace(old_init, new_init)

# 2. Replace cargar_memoria and guardar_en_memoria
old_mem = '''def cargar_memoria():
    if os.path.exists(ARCHIVO_MEMORIA):
        try:
            with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def guardar_en_memoria(cuenta, titulo, sku):
    mem = cargar_memoria()
    if cuenta not in mem:
        mem[cuenta] = {'titulos': [], 'skus': []}
    if titulo and titulo not in mem[cuenta]['titulos']:
        mem[cuenta]['titulos'].append(titulo)
    if sku and sku not in mem[cuenta]['skus']:
        mem[cuenta]['skus'].append(sku)
    with open(ARCHIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(mem, f, ensure_ascii=False, indent=4)'''

new_mem = '''def cargar_memoria():
    mem = {}
    with ia_memory_lock:
        try:
            conn = sqlite3.connect(ARCHIVO_MEMORIA_IA_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT cuenta, tipo, valor FROM memoria_erp")
            for cuenta, tipo, valor in cursor.fetchall():
                if cuenta not in mem:
                    mem[cuenta] = {'titulos': [], 'skus': []}
                mem[cuenta][tipo].append(valor)
            conn.close()
        except: pass
    return mem

def guardar_en_memoria(cuenta, titulo, sku):
    with ia_memory_lock:
        try:
            conn = sqlite3.connect(ARCHIVO_MEMORIA_IA_DB)
            cursor = conn.cursor()
            if titulo:
                cursor.execute("INSERT OR IGNORE INTO memoria_erp (cuenta, tipo, valor) VALUES (?, 'titulos', ?)", (cuenta, titulo))
            if sku:
                cursor.execute("INSERT OR IGNORE INTO memoria_erp (cuenta, tipo, valor) VALUES (?, 'skus', ?)", (cuenta, sku))
            conn.commit()
            conn.close()
        except: pass'''

content = content.replace(old_mem, new_mem)

# 3. Update the sync endpoint direct write
old_sync = '''    with open(ARCHIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(memoria, f, ensure_ascii=False, indent=4)'''

new_sync = '''    with ia_memory_lock:
        try:
            conn = sqlite3.connect(ARCHIVO_MEMORIA_IA_DB)
            cursor = conn.cursor()
            for n_c, datos_nuevos in memoria.items():
                for t in datos_nuevos.get("titulos", []):
                    cursor.execute("INSERT OR IGNORE INTO memoria_erp (cuenta, tipo, valor) VALUES (?, 'titulos', ?)", (n_c, t))
                for s in datos_nuevos.get("skus", []):
                    cursor.execute("INSERT OR IGNORE INTO memoria_erp (cuenta, tipo, valor) VALUES (?, 'skus', ?)", (n_c, s))
            conn.commit()
            conn.close()
        except Exception as e: print("Error sync db:", e)'''

content = content.replace(old_sync, new_sync)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
