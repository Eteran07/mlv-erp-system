import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the dictionary iteration
old_code = '''    res_det = requests.get(f"https://api.mercadolibre.com/items?ids={ids_str}&attributes=id,title,price,seller_custom_field,status,health", headers=headers)
    
    resultados = []
    for it in res_det.json():
        if it.get("code") == 200:'''

new_code = '''    res_det = requests.get(f"https://api.mercadolibre.com/items?ids={ids_str}&attributes=id,title,price,seller_custom_field,status,health", headers=headers)
    
    data = res_det.json()
    if isinstance(data, dict) and "error" in data:
        return {"error": f"Error de ML: {data.get('message', str(data))}"}
        
    resultados = []
    for it in data:
        if isinstance(it, dict) and it.get("code") == 200:'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('app_web.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed")
else:
    print("Old code not found. Searching for partial match.")
