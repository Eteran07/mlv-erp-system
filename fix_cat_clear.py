# -*- coding: utf-8 -*-
import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("onRowChange(manualCatSearch.idx, 'cat_nombre', `Cat Manual: ${c.name}`);", "onRowChange(manualCatSearch.idx, 'cat_nombre', `Cat Manual: ${c.name}`);\n                          const rData = rowData[manualCatSearch.idx] || {};\n                          if (rData.errorML && rData.errorML.includes('category_id')) {\n                              onRowChange(manualCatSearch.idx, 'errorML', null);\n                          }")

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Replaced")