import os
import glob
import json
import requests

def listar_archivos_token():
    archivos = sorted(glob.glob("token*.json"))
    return archivos if archivos else ["tokens_ml.json"]

def obtener_nombre_cuenta(archivo_token):
    nombre = archivo_token.replace("token_", "").replace("tokens_", "").replace(".json", "").upper()
    return nombre if nombre else "PRINCIPAL"

def renovar_y_guardar_token(archivo_token, datos_json):
    client_id = os.getenv("ML_APP_ID") or os.getenv("ML_CLIENT_ID")
    client_secret = os.getenv("ML_CLIENT_SECRET")
    refresh_token = datos_json.get("refresh_token")

    if not client_id or not client_secret:
        return datos_json.get("access_token"), "ERROR_ENV: Faltan credenciales en el .env"
    if not refresh_token:
        return datos_json.get("access_token"), "ERROR_JSON: El archivo JSON no tiene el campo 'refresh_token'."

    url_oauth = "https://api.mercadolibre.com/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        res = requests.post(url_oauth, data=payload, headers=headers)
        if res.status_code == 200:
            nuevos_datos = res.json()
            with open(archivo_token, "w") as f:
                json.dump(nuevos_datos, f, indent=4)
            return nuevos_datos.get("access_token"), "OK"
        else:
            return datos_json.get("access_token"), f"RECHAZO_ML ({res.status_code}): {res.text}"
    except Exception as e:
        return datos_json.get("access_token"), f"EXCEPCIÓN_RED: {str(e)}"

def obtener_token(archivo_token):
    try:
        if not os.path.exists(archivo_token):
            return None
        with open(archivo_token, "r") as archivo:
            datos = json.load(archivo)

        token = datos.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        res_check = requests.get("https://api.mercadolibre.com/users/me", headers=headers)

        if res_check.status_code != 200:
            nuevo_token, _ = renovar_y_guardar_token(archivo_token, datos)
            return nuevo_token
            
        return token
    except Exception as e:
        print(f"Error leyendo archivo de token {archivo_token}: {e}")
        return None

def obtener_titulos_publicados(headers):
    try:
        res_me = requests.get("https://api.mercadolibre.com/users/me", headers=headers)
        if res_me.status_code != 200: return set()
        user_id = res_me.json().get("id")

        res_items = requests.get(f"https://api.mercadolibre.com/users/{user_id}/items/search", headers=headers)
        item_ids = res_items.json().get("results", [])
        
        titulos_activos = set()
        if item_ids:
            ids_str = ",".join(item_ids[:50]) 
            res_detalles = requests.get(f"https://api.mercadolibre.com/items?ids={ids_str}", headers=headers)
            for item in res_detalles.json():
                if item.get("code") == 200:
                    titulos_activos.add(item["body"]["title"].strip().lower())
        return titulos_activos
    except Exception:
        return set()