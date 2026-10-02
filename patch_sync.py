import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_loop = '''        if item_ids:
            for i in range(0, total_items, 20):
                # 🟢 Calculamos y enviamos el porcentaje de extracción de SKUs
                pct = int((i / total_items) * 100)
                actualizar_progreso(pct, f"[{nombre_perfil}] Extrayendo SKUs y Variaciones: {i} de {total_items}...")
                
                ids_str = ",".join(item_ids[i:i+20]) 
                url_items = f"{API_ML}/items?ids={ids_str}"
                res_detalles = requests.get(url_items, headers=headers)
                
                if res_detalles.status_code == 200:
                    res_json = res_detalles.json()'''

new_loop = '''        if item_ids:
            import concurrent.futures
            chunks = [item_ids[i:i+20] for i in range(0, total_items, 20)]
            completados = 0
            
            def fetch_detalles(ids_chunk):
                ids_str = ",".join(ids_chunk)
                url_items = f"{API_ML}/items?ids={ids_str}"
                try:
                    res = requests.get(url_items, headers=headers, timeout=10)
                    if res.status_code == 200:
                        return res.json()
                except: pass
                return []

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                for res_json in executor.map(fetch_detalles, chunks):
                    completados += 20
                    pct = int((completados / total_items) * 100)
                    actualizar_progreso(pct, f"[{nombre_perfil}] Extrayendo SKUs y Variaciones: {min(completados, total_items)} de {total_items}...")
                    if res_json:'''

# There is a problem, python is very strict about indentation. Let's make sure it matches.
content = content.replace(old_loop, new_loop)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
