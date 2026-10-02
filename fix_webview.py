import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_main = '''if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading
    import time

    def open_browser():
        time.sleep(2)
        webbrowser.open("http://127.0.0.1:8080")
        
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Ejecutar FastAPI directamente
    uvicorn.run(app, host="127.0.0.1", port=8080)'''

new_main = '''if __name__ == "__main__":
    import uvicorn
    import threading
    import webview
    import time

    def run_server():
        # Ejecuta el servidor web en silencio (critical) para no crashear la app en modo noconsole
        uvicorn.run(app, host="127.0.0.1", port=8080, log_level="critical")

    t = threading.Thread(target=run_server)
    t.daemon = True
    t.start()

    # Le damos 1 segundo al servidor para encender
    time.sleep(1)

    # Creamos una ventana de aplicacion nativa de Windows
    webview.create_window("ERP Mercado Libre - MLV", "http://127.0.0.1:8080", width=1200, height=800)
    webview.start()
'''

content = content.replace(old_main, new_main)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
