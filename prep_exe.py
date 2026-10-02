import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

footer = '''
if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading
    import time

    def open_browser():
        time.sleep(2)
        webbrowser.open("http://127.0.0.1:8080")
        
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Ejecutar FastAPI directamente
    uvicorn.run(app, host="127.0.0.1", port=8080)
'''

if 'if __name__ == "__main__":' not in content:
    with open('app_web.py', 'a', encoding='utf-8') as f:
        f.write("\n" + footer)
        print("Added main block!")
