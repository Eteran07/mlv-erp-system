import re
with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = 'app = FastAPI(title="ERP Mercado Libre - Dashboard Definitivo", dependencies=[Depends(verify_auth)])'
replacement = '''app = FastAPI(title="ERP Mercado Libre - Dashboard Definitivo", dependencies=[Depends(verify_auth)])

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir solicitudes de React (ej: http://localhost:5173)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)'''

if target in content and 'CORSMiddleware' not in content:
    content = content.replace(target, replacement)
    with open('app_web.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("CORS added!")
else:
    print("Already added or not found")

