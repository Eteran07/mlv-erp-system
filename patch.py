import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('errores_historicos = cargar_errores_ia()', 'errores_historicos = cargar_errores_ia(cat_id)')
content = content.replace('guardar_error_ia(error_previo)', 'guardar_error_ia(error_previo, cat_id)')

old_req = '''        url_openrouter = "https://openrouter.ai/api/v1/chat/completions"
        res_or = requests.post(url_openrouter, headers=headers_or, json=payload_or, timeout=60)
        
        if res_or.status_code != 200:
            return {"error": f"Error API OpenRouter ({res_or.status_code})"}'''

new_req = '''        url_openrouter = "https://openrouter.ai/api/v1/chat/completions"
        
        max_reintentos = 3
        res_or = None
        for intento in range(max_reintentos):
            try:
                res_or = requests.post(url_openrouter, headers=headers_or, json=payload_or, timeout=60)
                if res_or.status_code == 200:
                    break
                elif res_or.status_code == 429:
                    import time
                    time.sleep((2 ** intento) + 1)
                else:
                    break
            except Exception:
                import time
                time.sleep((2 ** intento) + 1)

        if not res_or or res_or.status_code != 200:
            return {"error": f"Error API OpenRouter tras reintentos ({res_or.status_code if res_or else 'Timeout'})"}'''

content = content.replace(old_req, new_req)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
