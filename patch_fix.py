import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

pattern = r"if \(!window\.confirm\(.*Buscar e intentar emparejar.*art.*culos seleccionados\?.*\) return;"
repl = r"if (!window.confirm(`¿Buscar e intentar emparejar imágenes locales para ${selectedRows.size} artículos seleccionados?`)) return;"

code = re.sub(pattern, repl, code)

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
