import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix handlePublish
pub_pattern = r"if \(!window\.confirm\(.Est.s seguro de publicar  art.culos\?.*\) return;"
pub_repl = r"if (!window.confirm(`¿Estás seguro de publicar ${selectedRows.size} artículos?`)) return;"
code = re.sub(pub_pattern, pub_repl, code)

# Fix applyBulkExposicion
exp_pattern = r"if \(!window\.confirm\(.*Aplicar exposici.n .* a  publicaciones\?.*\) return;"
exp_repl = r"if (!window.confirm(`¿Aplicar exposición '${bulkExposicion}' a ${selectedRows.size} publicaciones?`)) return;"
code = re.sub(exp_pattern, exp_repl, code)

# Fix applyBulkEnvio
env_pattern = r"if \(!window\.confirm\(.*Aplicar env.o .* a  publicaciones\?.*\) return;"
env_repl = r"if (!window.confirm(`¿Aplicar envío '${bulkEnvio}' a ${selectedRows.size} publicaciones?`)) return;"
code = re.sub(env_pattern, env_repl, code)

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched template literals")
