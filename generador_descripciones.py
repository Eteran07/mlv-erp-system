import os
import pandas as pd
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

BLOQUE_SUPERIOR = "SOMOS TIENDA FÍSICA, Empresa Mayorista Líder en el Mercado de la Computación Producto 100% de calidad\n"

BLOQUE_INFERIOR = """
.Por Favor Verifique la disponibilidad antes de ofertar
Por Favor Verifique la disponibilidad antes de ofertar
Por Favor Verifique la disponibilidad antes de ofertar
**************************************************************************************************
- Emitimos factura LEGAL
- Trabajamos con agentes de retención
- Enviamos a todo el País.
**************************************************************************************************
COMENTARIOS:
- Realice todas las preguntas necesarias Antes de ofertar.
- El equipo de ventas está a tu disposición para responder tus consultas.
- Te invitamos a que solo ofertes cuando estés seguro de realizar la compra.
- La disponibilidad y precio del producto publicado solo se garantiza por un lapso de 24hrs luego de haber solicitado la compra.
- Si presentas algún inconveniente durante el proceso de compras estaremos a tu completa disposición para atenderte y solventar la situación. Deseamos que tu compra con nosotros siempre genere una calificación positiva.
**************************************************************************************************
**HORARIO DE TRABAJO**
****************************************************
De Lunes A Viernes
De 8:30am A 5:30pm
"""

def redactar_con_ia(titulo):
    prompt = f"Eres un experto en ventas y tecnología. Redacta una descripción extensa, muy detallada, persuasiva y técnica sobre el producto: '{titulo}'. Agrega valor real explicando posibles casos de uso, beneficios, características técnicas destacadas y por qué es una excelente compra. No incluyas saludos. Genera un texto en prosa, bien estructurado, que demuestre conocimiento profundo del producto."
    
    headers_or = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:8080",
        "X-Title": "Generador de Descripciones ML",
        "Content-Type": "application/json"
    }
    
    payload_or = {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    
    try:
        url_openrouter = "https://openrouter.ai/api/v1/chat/completions"
        res = requests.post(url_openrouter, headers=headers_or, json=payload_or, timeout=60)
        
        if res.status_code == 200:
            datos = res.json()
            return datos["choices"][0]["message"]["content"].strip()
        else:
            print(f"Error de OpenRouter (Cod {res.status_code}): {res.text}")
            return "Excelente producto de alta calidad y rendimiento garantizado."
    except Exception as e:
        print(f"Error con la IA para {titulo}: {e}")
        return "Excelente producto de alta calidad y rendimiento garantizado."

def procesar_excel():
    print("=== ✨ INICIANDO GENERADOR DE DESCRIPCIONES ===")
    
    try:
        df = pd.read_excel("inventario.xlsx")
    except FileNotFoundError:
        print("❌ No se encontró inventario.xlsx")
        return

    descripciones_finales = []

    for index, fila in df.iterrows():
        titulo = str(fila['Titulo'])
        print(f"Redactando descripción para: {titulo}...")
        
        titulo_x3 = f"{titulo}\n{titulo}\n{titulo}\n"
        parrafo_ia = redactar_con_ia(titulo)
        
        descripcion_completa = f"{BLOQUE_SUPERIOR}\n{titulo_x3}\n{parrafo_ia}\n{BLOQUE_INFERIOR}"
        descripciones_finales.append(descripcion_completa)

    df['Descripcion_Lista'] = descripciones_finales
    df.to_excel("inventario_listo.xlsx", index=False)
    print("\n✅ ¡ÉXITO! Se generó el archivo 'inventario_listo.xlsx' con todas las descripciones armadas.")

if __name__ == "__main__":
    procesar_excel()