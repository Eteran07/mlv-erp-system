# -*- coding: utf-8 -*-
import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("fd.append('cat_id', rd.cat_id ?? p.Categoria_ID || '');", "fd.append('cat_id', (rd.cat_id ?? p.Categoria_ID) || '');")

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed parens")