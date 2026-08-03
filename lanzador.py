import time
import threading
import uvicorn
import webview
from app_web import app

def iniciar_servidor():
    # Inicia FastAPI en el puerto 8000 en segundo plano
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

if __name__ == "__main__":
    # 1. Arrancar el servidor en un hilo separado
    hilo_servidor = threading.Thread(target=iniciar_servidor, daemon=True)
    hilo_servidor.start()
    
    # 2. Esperar medio segundo para que el servidor esté listo
    time.sleep(0.5)
    
    # 3. Abrir la ventana nativa de la aplicación
    ventana = webview.create_window(
        title="🚀 MLV ERP SYSTEM - Control Maestro",
        url="http://127.0.0.1:8000",
        width=1366,
        height=768,
        min_size=(1024, 600)
    )
    
    # 4. Iniciar la interfaz gráfica
    webview.start()