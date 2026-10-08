import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

grouped_pattern = r'''  const groupedByCategory = \(\(\) => \{
    const g = \{\};
    \(previewData\?\.productos \|\| \[\]\)\.forEach\(\(p, idx\) => \{
      const cat = p\.CategoriaNombre \|\| 'Sin Categoria';
      if \(!g\[cat\]\) g\[cat\] = \[\];
      g\[cat\]\.push\(\{ p, idx \}\);
    \}\);
    return g;
  \}\)\(\);'''

grouped_repl = r'''  const filteredItems = (previewData?.productos || []).map((p, idx) => ({ p, idx })).filter(item => {
    if (hidePublished) {
       return !(item.p.EstadoPublicación || item.p["Estado Publicación"] || "").includes("Ya publicado");
    }
    return true;
  });
  const totalPages = Math.ceil(filteredItems.length / itemsPerPage) || 1;
  const paginatedItems = filteredItems.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const groupedByCategory = (() => {
    const g = {};
    paginatedItems.forEach(({ p, idx }) => {
      const cat = p.CategoriaNombre || 'Sin Categoria';
      if (!g[cat]) g[cat] = [];
      g[cat].push({ p, idx });
    });
    return g;
  })();'''
code = re.sub(grouped_pattern, grouped_repl, code)

# Now inject pagination controls above the tabs
tabs_pattern = r'''              \{\/\* Vista Tabs \+ Table \*\/\}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm">'''
tabs_repl = r'''              {/* Paginación y Filtros */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-3 flex flex-wrap justify-between items-center gap-4">
                <label className="flex items-center gap-2 text-sm font-medium text-slate-700 cursor-pointer">
                  <input type="checkbox" checked={hidePublished} onChange={e => { setHidePublished(e.target.checked); setCurrentPage(1); }} className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-4 h-4" />
                  Ocultar artículos "Ya publicado"
                </label>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 font-bold">Mostrar:</span>
                  <select value={itemsPerPage} onChange={e => { setItemsPerPage(Number(e.target.value)); setCurrentPage(1); }} className="text-xs border border-slate-200 rounded px-2 py-1 bg-white focus:outline-none">
                    <option value={10}>10 por página</option>
                    <option value={50}>50 por página</option>
                    <option value={100}>100 por página</option>
                    <option value={500}>500 por página</option>
                  </select>
                  <span className="text-slate-200 mx-1">|</span>
                  <button disabled={currentPage <= 1} onClick={() => setCurrentPage(p => p - 1)} className="px-3 py-1 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-600 rounded disabled:opacity-50 transition-colors">Anterior</button>
                  <span className="text-xs font-bold text-slate-700 w-24 text-center">Pág {currentPage} de {totalPages}</span>
                  <button disabled={currentPage >= totalPages} onClick={() => setCurrentPage(p => p + 1)} className="px-3 py-1 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-600 rounded disabled:opacity-50 transition-colors">Siguiente</button>
                </div>
              </div>

              {/* Vista Tabs + Table */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm">'''
code = code.replace(tabs_pattern, tabs_repl)

# Now fix 'lineal' map to use paginatedItems instead of previewData.productos
lineal_pattern = r'''\{previewData\.productos\.map\(\(p, idx\) => \('''
lineal_repl = r'''{paginatedItems.map(({ p, idx }) => ('''
code = code.replace(lineal_pattern, lineal_repl)

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched pagination")
