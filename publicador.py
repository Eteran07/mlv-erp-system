import json
import requests
import pandas as pd

def obtener_token():
    try:
        with open("tokens_ml.json", "r") as archivo:
            tokens = json.load(archivo)
            return tokens.get("access_token")
    except FileNotFoundError:
        print("❌ No se encontró el token.")
        return None

def adivinar_categoria(titulo, headers):
    url = "https://api.mercadolibre.com/sites/MLV/domain_discovery/search"
    response = requests.get(url, headers=headers, params={"q": titulo})
    if response.status_code == 200 and len(response.json()) > 0:
        return response.json()[0].get("category_id")
    return None

def publicar_desde_excel():
    print("=== 🚀 INICIANDO PUBLICADOR MASIVO ===")
    
    token = obtener_token()
    if not token: return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        df = pd.read_excel("inventario.xlsx")
        print("✅ Excel cargado correctamente.\n")
    except Exception as e:
        print(f"❌ Error leyendo el Excel: {e}")
        return

    for index, fila in df.iterrows():
        titulo = str(fila['Titulo'])
        precio = float(fila['Precio'])
        stock = int(fila['Stock'])
        # Ignoraremos temporalmente la imagen del Excel para evitar el error de ML
        # imagen_url = str(fila['Imagen'])

        print(f"Preparando: {titulo}")
        
        categoria_id = adivinar_categoria(titulo, headers)
        if not categoria_id:
            print(f"⚠️ No se pudo adivinar la categoría para {titulo}. Saltando...\n")
            continue

        # 4. El Nuevo Paquete de Datos (Ajustado a las reglas de ML)
        datos_publicacion = {
            "title": titulo,
            "category_id": categoria_id,
            "price": precio,
            "currency_id": "USD", 
            "available_quantity": stock,
            "buying_mode": "buy_it_now",
            "condition": "new",
            "listing_type_id": "bronze", # Cambiado de 'free' a 'bronze' (Clásica)
            "pictures": [
                # Usamos una imagen de marcador de posición segura para la prueba
                {"source": "https://dummyimage.com/600x600/000/fff.jpg&text=FOTO+DE+PRUEBA"} 
            ],
            "attributes": [
                # Atributos OBLIGATORIOS inyectados directamente
                {"id": "BRAND", "value_name": "Maxiprint"},
                {"id": "MODEL", "value_name": "B205"}
            ]
        }

        url_post = "https://api.mercadolibre.com/items"
        respuesta = requests.post(url_post, headers=headers, json=datos_publicacion)

        if respuesta.status_code == 201:
            item_ml = respuesta.json()
            print(f"✅ ¡PUBLICADO CON ÉXITO!")
            print(f"👉 Link: {item_ml.get('permalink')}\n")
        else:
            print(f"❌ Error al publicar:")
            print(respuesta.json(), "\n")

if __name__ == "__main__":
    publicar_desde_excel()