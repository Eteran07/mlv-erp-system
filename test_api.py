import json
import requests

def probar_conexion():
    print("=== LEYENDO TOKEN Y CONECTANDO A LA API ===")
    
    # 1. Leer tu llave maestra
    try:
        with open("tokens_ml.json", "r") as archivo:
            tokens = json.load(archivo)
    except FileNotFoundError:
        print("❌ No se encontró el archivo tokens_ml.json")
        return

    access_token = tokens.get("access_token")

    # 2. Preparar la credencial para Mercado Libre
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # 3. Hacer la consulta al servidor de Mercado Libre
    url = "https://api.mercadolibre.com/users/me"
    
    response = requests.get(url, headers=headers)

    # 4. Mostrar los resultados
    if response.status_code == 200:
        datos = response.json()
        print("\n✅ ¡CONEXIÓN 100% EXITOSA!")
        print("-" * 30)
        print(f"ID de Vendedor : {datos.get('id')}")
        print(f"Nickname       : {datos.get('nickname')}")
        print(f"País           : {datos.get('site_id')}")
        print(f"Email          : {datos.get('email')}")
        print("-" * 30)
        print("\n¡Tu ERP ya tiene acceso total a esta cuenta!")
    else:
        print("\n❌ Ups, algo falló con la API:")
        print(response.json())

if __name__ == "__main__":
    probar_conexion()