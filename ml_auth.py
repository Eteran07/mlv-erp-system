import os
import requests
from dotenv import load_dotenv

# Cargar credenciales del archivo .env
load_dotenv()
APP_ID = os.getenv("ML_APP_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")

# Forzamos tu URI real para evitar errores del archivo .env
REDIRECT_URI = "https://mlvsystem.com"

def obtener_autorizacion():
    print("=== PASO 1: AUTORIZACIÓN ===")
    url_auth = f"https://auth.mercadolibre.com.ve/authorization?response_type=code&client_id={APP_ID}&redirect_uri={REDIRECT_URI}"
    
    print("1. Abre tu navegador (recomendado en Incógnito).")
    print("2. Inicia sesión con la cuenta de Mercado Libre que quieres vincular.")
    print("3. Copia y pega el siguiente enlace en ese navegador:\n")
    print(f"{url_auth}\n")
    print("4. Mercado Libre te redirigirá a tu página web (https://mlvsystem.com).")
    print("5. Copia el código de la URL que está después de '?code=' (empieza con TG-).")
    
    codigo = input("\nPega el código TG- aquí y presiona Enter: ").strip()
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
        print("\n✅ ¡Conexión Exitosa con Mercado Libre!")
        
        # EL SISTEMA AHORA TE PREGUNTA EL NOMBRE PARA NO SOBREESCRIBIR
        nombre_archivo = input("¿Con qué nombre deseas guardar esta cuenta? (ej. token_ventas.json): ").strip()
        
        if not nombre_archivo.endswith(".json"):
            nombre_archivo += ".json"
            
        with open(nombre_archivo, "w") as f:
            f.write(response.text)
        print(f"✅ ¡ÉXITO TOTAL! Tokens guardados en el archivo '{nombre_archivo}'.")
    else:
        print("❌ Error al canjear el token:")
        print(response.json())

if __name__ == "__main__":
    codigo_auth = obtener_autorizacion()
    if codigo_auth:
        canjear_token(codigo_auth)