import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''        max_reintentos = 3
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


new_block = '''        max_reintentos = 6
        res_or = None
        for intento in range(max_reintentos):
            try:
                res_or = requests.post(url_openrouter, headers=headers_or, json=payload_or, timeout=90)
                if res_or.status_code == 200:
                    break
                elif res_or.status_code in [400, 401, 403]:
                    break
                else:
                    import time
                    time.sleep((2 ** intento) + 2)
            except Exception:
                import time
                time.sleep((2 ** intento) + 2)

        if not res_or or res_or.status_code != 200:
            return {"error": f"Fallo persistente IA tras {max_reintentos} intentos. Causa: ({res_or.status_code if res_or else 'Red / Timeout'})"}'''

content = content.replace(old_block, new_block)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
