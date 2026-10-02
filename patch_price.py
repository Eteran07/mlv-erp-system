import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_price_code = '''const precioFormateado = parseFloat(prod.Precio || 0).toFixed(2);'''

new_price_code = '''const precioFloat = parseFloat(prod.Precio || 0);
const precioFormateado = precioFloat.toFixed(2);
let badgePrecio = "";
if (precioFloat > 0 && precioFloat < 2.0) {
    badgePrecio = \<div style="background:#fee2e2; border:1px solid #fca5a5; color:#b91c1c; padding:4px; font-size:10px; font-weight:bold; border-radius:4px; margin-top:4px;">⚠️ Precio Mínimo ()</div>\;
}'''

content = content.replace(old_price_code, new_price_code)

old_html = '''<td><input type="number" id="pre-" value="" step="0.01"></td>'''
new_html = '''<td>
                                    <input type="number" id="pre-" value="" step="0.01">
                                    
                                </td>'''

content = content.replace(old_html, new_html)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
