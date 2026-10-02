import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''badgePrecio = \<div style="background:#fee2e2; border:1px solid #fca5a5; color:#b91c1c; padding:4px; font-size:10px; font-weight:bold; border-radius:4px; margin-top:4px;">\u26a0\ufe0f Precio Mínimo ()</div>\;'''
new = '''badgePrecio = <div style="background:#fee2e2; border:1px solid #fca5a5; color:#b91c1c; padding:4px; font-size:10px; font-weight:bold; border-radius:4px; margin-top:4px;">⚠️ Precio Mínimo ()</div>;'''

content = content.replace(old, new)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
