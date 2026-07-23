import os
import pandas as pd
from google import genai
from dotenv import load_dotenv

load_dotenv()
cliente_ia = genai.Client()

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
    prompt = f"Escribe un solo párrafo corto (máximo 4 líneas), persuasivo y técnico, sobre el producto: '{titulo}'. No incluyas saludos, ni viñetas, solo el texto puro."
    
    try:
        # ¡ACTUALIZADO AL MODELO MÁS RECIENTE!
        respuesta = cliente_ia.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        return respuesta.text.strip()
    except Exception as e:
        print(f"Error con la IA para {titulo}: {e}")
        return "Excelente producto de alta calidad y rendimiento garantizado."

def procesar_excel():
    print("=== 🤖 INICIANDO GENERADOR DE DESCRIPCIONES ===")
    
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