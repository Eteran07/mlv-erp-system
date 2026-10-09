# -*- coding: utf-8 -*-
import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

bad_block = """  const handleAIErrors = () => {
    const errorIdxs = [...selectedRows].filter(idx => (rowData[idx] || {}).errorML);
    if (!errorIdxs.length) return customAlert('No hay articulos seleccionados con errores.');
    let errorIdxs = [...selectedRows].filter(idx => (rowData[idx] || {}).errorML);
    if (!errorIdxs.length) {
      errorIdxs = filteredItems.map(i => i.idx).filter(idx => (rowData[idx] || {}).errorML);
    }
    if (!errorIdxs.length) return customAlert('No hay articulos con errores en esta vista.');
    runAIBulk(errorIdxs);
  };"""

good_block = """  const handleAIErrors = () => {
    let errorIdxs = [...selectedRows].filter(idx => (rowData[idx] || {}).errorML);
    if (!errorIdxs.length) {
      errorIdxs = filteredItems.map(i => i.idx).filter(idx => (rowData[idx] || {}).errorML);
    }
    if (!errorIdxs.length) return customAlert('No hay articulos con errores en esta vista.');
    runAIBulk(errorIdxs);
  };"""

if bad_block in content:
    content = content.replace(bad_block, good_block)
    with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Replaced successfully')
else:
    print('Bad block not found')