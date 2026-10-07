import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''    # Obtener detalles
    ids_str = ",".join(item_ids)
    res_det = requests.get(f"https://api.mercadolibre.com/items?ids={ids_str}&attributes=id,title,price,seller_custom_field,status,health", headers=headers)
    
    data = res_det.json()
    if isinstance(data, dict) and "error" in data:
        return {"error": f"Error de ML: {data.get('message', str(data))}"}
        
    resultados = []
    for it in data:
        if isinstance(it, dict) and it.get("code") == 200:
            body = it["body"]
            resultados.append({
                "id": body.get("id"),
                "title": body.get("title"),
                "price": body.get("price"),
                "sku": body.get("seller_custom_field", "N/A"),
                "status": body.get("status"),
                "health": body.get("health", 1)
            })
    return resultados'''

new_code = '''    # Obtener detalles en bloques de 20 (Lmite estricto de Mercado Libre)
    resultados = []
    
    # Dividir item_ids en sublistas de 20
    for i in range(0, len(item_ids), 20):
        bloque = item_ids[i:i+20]
        ids_str = ",".join(bloque)
        
        res_det = requests.get(f"https://api.mercadolibre.com/items?ids={ids_str}&attributes=id,title,price,seller_custom_field,status,health", headers=headers)
        data = res_det.json()
        
        if isinstance(data, dict) and "error" in data:
            return {"error": f"Error de ML: {data.get('message', str(data))}"}
            
        for it in data:
            if isinstance(it, dict) and it.get("code") == 200:
                body = it["body"]
                
                # Por seguridad, si el SKU no existe, lo marcamos como "N/A"
                sku_str = body.get("seller_custom_field", "N/A")
                if not sku_str: sku_str = "N/A"
                
                resultados.append({
                    "id": body.get("id"),
                    "title": body.get("title"),
                    "price": body.get("price"),
                    "sku": sku_str,
                    "status": body.get("status"),
                    "health": body.get("health", 1)
                })
                
    return resultados'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('app_web.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed chunking")
else:
    print("Chunking block not found")
