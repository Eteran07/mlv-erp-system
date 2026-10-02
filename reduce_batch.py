import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('const TAMANO_LOTE = 10;', 'const TAMANO_LOTE = 5;')
content = content.replace('lotes de 10', 'lotes de 5')

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
