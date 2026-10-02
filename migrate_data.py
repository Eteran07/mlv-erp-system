import json
import sqlite3
import os

ARCHIVO_MEMORIA_IA_DB = "memoria_ia.db"
ARCHIVO_MEMORIA = "memoria_erp.json"

if os.path.exists(ARCHIVO_MEMORIA):
    with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f:
        mem = json.load(f)
        
    conn = sqlite3.connect(ARCHIVO_MEMORIA_IA_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memoria_erp (
            cuenta TEXT,
            tipo TEXT,
            valor TEXT,
            UNIQUE(cuenta, tipo, valor)
        )
    ''')
    
    for cuenta, datos in mem.items():
        for t in datos.get("titulos", []):
            cursor.execute("INSERT OR IGNORE INTO memoria_erp (cuenta, tipo, valor) VALUES (?, 'titulos', ?)", (cuenta, t))
        for s in datos.get("skus", []):
            cursor.execute("INSERT OR IGNORE INTO memoria_erp (cuenta, tipo, valor) VALUES (?, 'skus', ?)", (cuenta, s))
            
    conn.commit()
    conn.close()
    
    # Rename to keep a backup
    os.rename(ARCHIVO_MEMORIA, ARCHIVO_MEMORIA + ".backup")
    print("Migrated JSON to SQLite successfully!")
