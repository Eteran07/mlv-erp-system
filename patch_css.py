import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_css = '''.item-row { transition: all 0.5s ease; opacity: 1; transform: translateX(0); }'''
new_css = '''.item-row { transition: all 0.5s ease; opacity: 1; transform: translateX(0); content-visibility: auto; contain-intrinsic-size: 200px; }'''

content = content.replace(old_css, new_css)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
