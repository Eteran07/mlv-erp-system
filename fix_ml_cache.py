import sys
import re

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add lru_cache for ML categories
helper = '''
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

def autollenar_atributos_ia(
'''

content = content.replace("def autollenar_atributos_ia(\n", helper)

old_ml_call = '''        url_attr = f"{API_ML}/categories/{cat_id}/attributes"
        res_ml = requests.get(url_attr, timeout=6)
        if res_ml.status_code != 200:
            return {"error": "No se pudieron obtener los atributos de Mercado Libre."}

        attrs_ml = res_ml.json()'''

new_ml_call = '''        attrs_ml = obtener_atributos_categoria_ml_cached(cat_id)
        if not attrs_ml:
            return {"error": "No se pudieron obtener los atributos de Mercado Libre tras reintentos."}'''

content = content.replace(old_ml_call, new_ml_call)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
