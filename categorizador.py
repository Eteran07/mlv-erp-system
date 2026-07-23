import json
import requests

def predecir_categorias():
    print("===🤖 ANALIZANDO CATEGORÍAS EN MLV ===\n")
    
    # 1. Leer tu llave maestra
    try:
        with open("tokens_ml.json", "r") as archivo:
            tokens = json.load(archivo)
    except FileNotFoundError:
        print("❌ No se encontró el archivo tokens_ml.json")
        return

    access_token = tokens.get("access_token")
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    mis_productos = [
        "Toner Maxiprint Compatible Xerox B205/B210/B215 106R04348",
        "cartucho 712",
        "laptop dell 128 gb 4 gb de ram",
        "mouse inalambrico"
    ]

    for producto in mis_productos:
        # 2. Endpoint actualizado a 'domain_discovery'
        url = "https://api.mercadolibre.com/sites/MLV/domain_discovery/search"
        params = {"q": producto}
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            datos = response.json()
            
            # 3. Mercado Libre devuelve una lista, tomamos la opción [0] (la mejor predicción)
            if len(datos) > 0:
                mejor_prediccion = datos[0]
                categoria_id = mejor_prediccion.get("category_id")
                categoria_nombre = mejor_prediccion.get("category_name")
                
                print(f"📦 Producto: {producto}")
                print(f"👉 ID Categoría: {categoria_id} ({categoria_nombre})")
                print("-" * 50)
            else:
                print(f"⚠️ No se encontró ninguna categoría para: {producto}")
                
        else:
            print(f"❌ Error analizando: {producto}")
            print(f"Detalle del error: {response.text}")

if __name__ == "__main__":
    predecir_categorias()