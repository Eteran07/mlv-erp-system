import re

with open('app_web.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix GET /api/ventas/mensajes/{pack_id} to handle 'null' or 'undefined'
get_pattern = r'(@app\.get\("/api/ventas/mensajes/\{pack_id\}"\)\s*def api_ventas_mensajes_get\(pack_id: str, cuenta: str, user_id: str\):)'
get_replacement = r'\1\n    if pack_id in ["null", "undefined", ""]: return {"mensajes": []}'
code = re.sub(get_pattern, get_replacement, code)

# Fix POST /api/ventas/mensajes/{pack_id} to use Request
post_pattern = r'@app\.post\("/api/ventas/mensajes/\{pack_id\}"\)\s*def api_ventas_mensajes_post\(pack_id: str, payload: dict\):'
post_replacement = r'''from fastapi import Request
@app.post("/api/ventas/mensajes/{pack_id}")
async def api_ventas_mensajes_post(pack_id: str, request: Request):
    payload = await request.json()'''
code = re.sub(post_pattern, post_replacement, code)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched app_web.py")
