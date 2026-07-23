import os
import requests
from dotenv import load_dotenv

# Cargar credenciales del archivo .env
load_dotenv()
APP_ID = os.getenv("ML_APP_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ML_REDIRECT_URI")

def obtener_autorizacion():
    print("=== PASO 1: AUTORIZACIÓN ===")
    url_auth = f"https://auth.mercadolibre.com.ve/authorization?response_type=code&client_id={APP_ID}&redirect_uri={REDIRECT_URI}"
    print("1. Haz Ctrl + Clic en este enlace e inicia sesión con la cuenta de ML Venezuela:\n")
    print(f"{url_auth}\n")
    print("2. La página final dará error de conexión (es el plan). Copia el código de la URL que está después de 'code='.")
    
    codigo = input("\nPega el código aquí y presiona Enter: ").strip()
    return codigo

def canjear_token(codigo):
    print("\n=== PASO 2: CANJEANDO TOKEN ===")
    url = "https://api.mercadolibre.com/oauth/token"
    headers = {
        "accept": "application/json", 
        "content-type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "client_id": APP_ID,
        "client_secret": CLIENT_SECRET,
        "code": codigo,
        "redirect_uri": REDIRECT_URI
    }

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        with open("tokens_ml.json", "w") as f:
            f.write(response.text)
        print("✅ ¡ÉXITO TOTAL! Tokens guardados en el archivo 'tokens_ml.json'.")
    else:
        print("❌ Error al canjear el token:")
        print(response.json())

if __name__ == "__main__":
    codigo_auth = obtener_autorizacion()
    if codigo_auth:
        canjear_token(codigo_auth)