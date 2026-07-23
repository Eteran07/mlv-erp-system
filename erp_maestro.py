import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv
from google import genai

# Cargar variables de entorno
load_dotenv()

# Configuración de Gemini (con manejo de respaldo si la red regional bloquea la IA)
try:
    cliente_ia = genai.Client()
    USAR_IA = True
except Exception:
    USAR_IA = False

# ==========================================
# PLANTILLAS DE DESCRIPCIÓN ESTÁNDAR
# ==========================================
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
De Lunes A Virenes
De 8:30am A 5:30pm
"""

def obtener_token():
    try:
        with open("tokens_ml.json", "r") as archivo:
            return json.load(archivo).get("access_token")
    except FileNotFoundError:
        print("❌ No se encontró el archivo tokens_ml.json.")
        return None

def adivinar_categoria(titulo, headers):
    url = "https://api.mercadolibre.com/sites/MLV/domain_discovery/search"
    response = requests.get(url, headers=headers, params={"q": titulo})
    if response.status_code == 200 and len(response.json()) > 0:
        return response.json()[0].get("category_id")
    return None

def redactar_parrafo(titulo):
    """Genera el párrafo intermedio con IA o usa texto de respaldo optimizado."""
    if not USAR_IA:
        return "Producto garantizado de excelente rendimiento y máxima durabilidad para exigencia profesional."
    
    prompt = f"Escribe un solo párrafo corto (máximo 4 líneas), persuasivo y técnico, sobre el producto: '{titulo}'. No incluyas saludos, ni viñetas, solo el texto puro."
    try:
        respuesta = cliente_ia.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        return respuesta.text.strip()
    except Exception:
        return "Producto garantizado de excelente rendimiento y máxima durabilidad para exigencia profesional."

def ejecutar_erp():
    print("=== 🚀 INICIANDO SISTEMA ERP - PUBLICADOR MASIVO ===")
    
    token = obtener_token()
    if not token: 
        print("❌ Autenticación fallida. Revisa tus tokens.")
        return
        
    headers = {
        "Authorization": f"Bearer {token}", 
        "Content-Type": "application/json"
    }

    try:
        df = pd.read_excel("inventario.xlsx")
        print(f"✅ Inventario cargado con éxito. Total de productos: {len(df)}\n")
    except Exception as e:
        print(f"❌ Error leyendo el archivo 'inventario.xlsx': {e}")
        return

    for index, fila in df.iterrows():
        titulo = str(fila['Titulo'])
        precio = float(fila['Precio'])
        stock = int(fila['Stock'])
        
        # 🛡️ Validación defensiva: Si faltan columnas en el Excel, se asignan valores por defecto
        marca = str(fila['Marca']) if 'Marca' in df.columns else 'Generico'
        modelo = str(fila['Modelo']) if 'Modelo' in df.columns else 'Universal'
        imagen_url = str(fila['Imagen']) if 'Imagen' in df.columns else 'https://dummyimage.com/600x600/000/fff.jpg&text=FOTO'

        print(f"--------------------------------------------------")
        print(f"📦 Procesando: {titulo}")
        
        # 1. Búsqueda inteligente de categoría
        categoria_id = adivinar_categoria(titulo, headers)
        if not categoria_id:
            print(f"⚠️ No se pudo determinar la categoría para: {titulo}. Saltando...")
            continue
        print(f"👉 Categoría asignada: {categoria_id}")

        # 2. Construcción de la descripción estructurada
        titulo_x3 = f"{titulo}\n{titulo}\n{titulo}\n"
        parrafo_dinamico = redactar_parrafo(titulo)
        descripcion_completa = f"{BLOQUE_SUPERIOR}\n{titulo_x3}\n{parrafo_dinamico}\n{BLOQUE_INFERIOR}"

        # 3. Paquete base para Mercado Libre
        datos_publicacion = {
            "title": titulo,
            "category_id": categoria_id,
            "price": precio,
            "currency_id": "USD", 
            "available_quantity": stock,
            "buying_mode": "buy_it_now",
            "condition": "new",
            "listing_type_id": "bronze", 
            "pictures": [{"source": imagen_url}],
            "attributes": [
                {"id": "BRAND", "value_name": marca},
                {"id": "MODEL", "value_name": modelo}
            ]
        }

        # 4. Enviar solicitud de publicación
        respuesta = requests.post("https://api.mercadolibre.com/items", headers=headers, json=datos_publicacion)

        if respuesta.status_code == 201:
            item_ml = respuesta.json()
            item_id = item_ml.get('id')
            
            # 5. Inyectar la descripción formateada
            url_desc = f"https://api.mercadolibre.com/items/{item_id}/description"
            resp_desc = requests.post(url_desc, headers=headers, json={"text": descripcion_completa})
            
            if resp_desc.status_code in [200, 201]:
                print(f"✅ ¡PUBLICADO Y DESCRIPCIÓN APLICADA CON ÉXITO!")
                print(f"🔗 Link: {item_ml.get('permalink')}")
            else:
                print(f"⚠️ Publicado base con ID {item_id}, pero hubo un detalle con la descripción.")
        else:
            print(f"❌ Error al publicar la ficha:")
            print(respuesta.json())

    print("\n=== ✨ PROCESO MASIVO FINALIZADO ===")

if __name__ == "__main__":
    ejecutar_erp()