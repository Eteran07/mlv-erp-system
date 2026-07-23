import json
import requests
import os

def obtener_token():
    try:
        with open("tokens_ml.json", "r") as archivo:
            return json.load(archivo).get("access_token")
    except FileNotFoundError:
        print("❌ No se encontró el token.")
        return None

def subir_imagen_local(ruta_imagen):
    print("=== 📸 INICIANDO CARGA DE IMAGEN ===")
    
    token = obtener_token()
    if not token: return
    
    url = "https://api.mercadolibre.com/pictures/items"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }

    if not os.path.exists(ruta_imagen):
        print(f"❌ No se encontró la imagen: {ruta_imagen}")
        return

    print(f"Subiendo '{ruta_imagen}' a los servidores de Mercado Libre...")

    with open(ruta_imagen, "rb") as archivo_imagen:
        archivos = {"file": archivo_imagen}
        respuesta = requests.post(url, headers=headers, files=archivos)

    if respuesta.status_code == 201 or respuesta.status_code == 200:
        datos = respuesta.json()
        id_imagen = datos.get("id")
        print("✅ ¡IMAGEN SUBIDA CON ÉXITO!")
        print("-" * 40)
        print(f"👉 ID de Mercado Libre: {id_imagen}")
        print("-" * 40)
        print("Este ID es el que usaremos en el publicador final.")
    else:
        print(f"❌ Error al subir la imagen. Código de estado HTTP: {respuesta.status_code}")
        # Red de seguridad: Intentamos leer JSON, si falla, leemos el texto crudo.
        try:
            print(respuesta.json())
        except requests.exceptions.JSONDecodeError:
            print("El servidor no devolvió un JSON. Respuesta cruda del servidor:")
            print(respuesta.text)

if __name__ == "__main__":
    subir_imagen_local("prueba.jpg")