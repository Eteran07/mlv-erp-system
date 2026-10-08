@echo off
echo Iniciando Servidor Backend (Python)...
start "Backend" cmd /c "venv\Scripts\uvicorn app_web:app --host 127.0.0.1 --port 8000"

echo Esperando a que el backend inicie...
timeout /t 3 /nobreak > nul

echo Iniciando Frontend (React Vite)...
cd frontend
start "Frontend" cmd /c "npm run dev"

echo.
echo Los servidores se han iniciado. Revisa las dos ventanas de terminal abiertas.
echo Puedes entrar a la aplicacion en tu navegador en: http://localhost:5174
pause
