import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace the category cards with a select dropdown
cat_pattern = r'''              <div className="p-6 overflow-y-auto flex-1 bg-slate-50">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">.*?</div>
              </div>'''
              
cat_repl = r'''              <div className="p-6 overflow-y-auto flex-1 bg-slate-50">
                <label className="block text-sm font-bold text-slate-700 mb-2">Filtrar por Categoría:</label>
                <select className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-blue-500" value={config.categoria_filtro} onChange={e => setConfig(c => ({ ...c, categoria_filtro: e.target.value }))}>
                  <option value="TODAS">TODAS LAS CATEGORÍAS (Sin filtro)</option>
                  {categorias.map(cat => (
                    <option key={cat.id} value={cat.id}>{cat.name} ({cat.id})</option>
                  ))}
                </select>
                <p className="text-xs text-slate-500 mt-2">
                  Si seleccionas una categoría específica, solo se previsualizarán los productos que MercadoLibre clasifique dentro de ella.
                </p>
              </div>'''

code = re.sub(cat_pattern, cat_repl, code, flags=re.DOTALL)

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched category modal to use select")
