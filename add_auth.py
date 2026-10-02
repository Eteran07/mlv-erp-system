import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_import = "from fastapi import FastAPI, UploadFile, File, Form"
new_import = "from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status\nfrom fastapi.security import HTTPBasic, HTTPBasicCredentials\nimport secrets"

content = content.replace(old_import, new_import)

old_app = 'app = FastAPI(title="ERP Mercado Libre - Dashboard Definitivo")'
new_app = '''security = HTTPBasic()

def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    import os
    import secrets
    correct_username = secrets.compare_digest(credentials.username, os.getenv("ERP_USER", "admin"))
    correct_password = secrets.compare_digest(credentials.password, os.getenv("ERP_PASS", "12345"))
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials

app = FastAPI(title="ERP Mercado Libre - Dashboard Definitivo", dependencies=[Depends(verify_auth)])'''

content = content.replace(old_app, new_app)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
