import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

alert_pattern = r"alert\(.*Se emparejaron fotos para  art.culos\.\);"
alert_repl = r"alert(`✅ Se emparejaron fotos para ${actualizadas} artículos.`);"
code = re.sub(alert_pattern, alert_repl, code)

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched alert")
