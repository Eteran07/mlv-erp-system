import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Add better error handling to handleFileChange
old_catch = r"\} catch \{ alert\('Error leyendo archivo'\); \}"
new_catch = r"} catch (e) { console.error('Error cargando archivo', e); alert('Error leyendo el archivo. Revisa que el backend esté corriendo y no haya errores de formato.'); }"
code = code.replace(old_catch, new_catch)

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched handleFileChange error handling")
