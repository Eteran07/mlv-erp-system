# -*- coding: utf-8 -*-
import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix runAIBulk
old_bulk = "fd.append('cat_id', p.Categoria_ID || '');"
new_bulk = "fd.append('cat_id', rd.cat_id ?? p.Categoria_ID || '');"
content = content.replace(old_bulk, new_bulk)

# Fix handlePublish
old_publish = """          return {
            ...p,
            idx:         originalIdx,
            Titulo:      rd.titulo      ?? p.Titulo,
            Precio:      rd.precio      ?? p.Precio,
            Stock:       rd.stock       ?? p.Stock,
            Exposicion:  rd.exposicion  ?? 'bronze',
            Envio:       rd.envio       ?? 'me2_free',
            DescripcionCustom: rd.descripcion ?? p.DescripcionCustom ?? '',
            AtributosDinamicos: rd.aiAtributos ?? p.AtributosDinamicos ?? {},
            ImagenesB64: ImagenesB64.length > 0 ? ImagenesB64 : (p.ImagenesB64 || [])
          };"""

new_publish = """          return {
            ...p,
            idx:         originalIdx,
            Titulo:      rd.titulo      ?? p.Titulo,
            Precio:      rd.precio      ?? p.Precio,
            Stock:       rd.stock       ?? p.Stock,
            Exposicion:  rd.exposicion  ?? 'bronze',
            Envio:       rd.envio       ?? 'me2_free',
            Categoria_ID: rd.cat_id     ?? p.Categoria_ID,
            CategoriaNombre: rd.cat_nombre ?? p.CategoriaNombre,
            DescripcionCustom: rd.descripcion ?? p.DescripcionCustom ?? '',
            AtributosDinamicos: rd.aiAtributos ?? p.AtributosDinamicos ?? {},
            ImagenesB64: ImagenesB64.length > 0 ? ImagenesB64 : (p.ImagenesB64 || [])
          };"""

content = content.replace(old_publish, new_publish)

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replaced handlePublish and runAIBulk")