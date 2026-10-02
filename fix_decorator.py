import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

bad_code = '''@app.post("/api/autollenar-atributos-ia")

import time
from functools import lru_cache

@lru_cache(maxsize=128)
def obtener_atributos_categoria_ml_cached(cat_id):
    url_attr = f"{API_ML}/categories/{cat_id}/attributes"
    for i in range(3):
        try:
            res = requests.get(url_attr, timeout=10)
            if res.status_code == 200:
                return res.json()
        except:
            time.sleep(1)
    return None

def autollenar_atributos_ia('''

good_code = '''import time
from functools import lru_cache

@lru_cache(maxsize=128)
def obtener_atributos_categoria_ml_cached(cat_id):
    url_attr = f"{API_ML}/categories/{cat_id}/attributes"
    for i in range(3):
        try:
            res = requests.get(url_attr, timeout=10)
            if res.status_code == 200:
                return res.json()
        except:
            time.sleep(1)
    return None

@app.post("/api/autollenar-atributos-ia")
def autollenar_atributos_ia('''

content = content.replace(bad_code, good_code)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
