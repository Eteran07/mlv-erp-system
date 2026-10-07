import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# First, remove the misplaced endpoint
idx_bad_start = content.find('@app.post("/api/ia/analizar-infracciones")')
if idx_bad_start != -1:
    idx_bad_end = content.find('def verify_auth', idx_bad_start)
    if idx_bad_end != -1:
        content = content[:idx_bad_start] + content[idx_bad_end:]

# Now, insert the endpoint at the bottom, just before if __name__ == '__main__':
new_endpoint = '''
@app.post("/api/ia/analizar-infracciones")
def api_ia_analizar_infracciones(payload: dict):
    import os
    import requests
    import json
    
    cuenta = payload.get("cuenta")
    items = payload.get("items", [])
    
    if not items: return {"error": "No hay ítems para analizar"}
    
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key: return {"error": "API Key de OpenRouter no configurada en .env"}
    
    prompt = "Eres un asistente experto en Mercado Libre. Analiza las siguientes publicaciones que tienen infracciones. Para cada una, sugiere una corrección. Si el problema es 'Duplicada' o 'Igual a otra', cambia el título ligeramente (por ejemplo agregando un adjetivo, usando un sinónimo, o un código al final) y modifica el precio un 1% para que el algoritmo de Mercado Libre no la marque como duplicada. Devuelve tu respuesta EXACTAMENTE en este formato JSON (sin texto adicional, sin formato markdown, solo el JSON):\\n"
    prompt += "{\\n  \\"log\\": \\"Explicación breve de lo que hiciste.\\",\\n  \\"sugerencias\\": [\\n    { \\"id\\": \\"MLV...\\", \\"nuevo_titulo\\": \\"Nuevo Titulo...\\", \\"nuevo_precio\\": 100.0 }\\n  ]\\n}\\n\\n"
    prompt += "Publicaciones a reparar:\\n"
    
    for it in items:
        prompt += f"- ID: {it.get('id')}\\n  Título Actual: {it.get('title')}\\n  Precio Actual: {it.get('price')}\\n  Infracción: {it.get('infraccion')}\\n\\n"
        
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek/deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}
            }
        )
        if response.status_code != 200:
            return {"error": f"Error de OpenRouter: {response.status_code} - {response.text}"}
            
        ai_msg = response.json()["choices"][0]["message"]["content"]
        
        if ai_msg.startswith("`json"): ai_msg = ai_msg[7:]
        if ai_msg.startswith("`"): ai_msg = ai_msg[3:]
        if ai_msg.endswith("`"): ai_msg = ai_msg[:-3]
        
        parsed = json.loads(ai_msg)
        return parsed
        
    except Exception as e:
        return {"error": f"Error en la IA: {str(e)}"}
'''

idx_main = content.find('if __name__ == "__main__":')
if idx_main != -1:
    content = content[:idx_main] + new_endpoint + "\n" + content[idx_main:]
    with open('app_web.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("ENDPOINT AI MOVED AND FIXED TO DEEPSEEK")
else:
    print("NOT FOUND")
