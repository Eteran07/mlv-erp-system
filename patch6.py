import re
with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f: code = f.read()
code = code.replace('if (!window.confirm("¿Estás seguro de generar la previsualización con estos ajustes?")) return;', '')
with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f: f.write(code)
