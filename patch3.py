import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# We need to find the map over previewData.productos
# Usually it looks like: previewData.productos.map((p, i) =>
productos_map_pattern = r'\{previewData\.productos\.map\(\(p, i\) => \('
productos_map_repl = r'''{(() => {
                    let itemsToRender = previewData.productos.map((p, i) => ({ p, idx: i }));
                    if (hidePublished) {
                      itemsToRender = itemsToRender.filter(({ p }) => !(p.EstadoPublicación || p["Estado Publicación"] || "").includes("Ya publicado"));
                    }
                    const totalPages = Math.ceil(itemsToRender.length / itemsPerPage);
                    const paginated = itemsToRender.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);
                    
                    return (
                      <>
                        <div className="flex justify-between items-center bg-white p-3 rounded-xl border border-slate-200 shadow-sm mb-3">
                          <label className="flex items-center gap-2 text-sm font-medium text-slate-700 cursor-pointer">
                            <input type="checkbox" checked={hidePublished} onChange={e => { setHidePublished(e.target.checked); setCurrentPage(1); }} className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-4 h-4" />
                            Ocultar artículos ya publicados
                          </label>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-500">Mostrar:</span>
                            <select value={itemsPerPage} onChange={e => { setItemsPerPage(Number(e.target.value)); setCurrentPage(1); }} className="text-xs border-slate-200 rounded p-1">
                              <option value={10}>10</option>
                              <option value={50}>50</option>
                              <option value={100}>100</option>
                              <option value={500}>500</option>
                            </select>
                            <span className="text-slate-300 mx-2">|</span>
                            <button disabled={currentPage <= 1} onClick={() => setCurrentPage(p => p - 1)} className="px-2 py-1 text-xs bg-slate-100 hover:bg-slate-200 rounded disabled:opacity-50">Anterior</button>
                            <span className="text-xs font-medium text-slate-600">Pág {currentPage} de {totalPages || 1}</span>
                            <button disabled={currentPage >= totalPages} onClick={() => setCurrentPage(p => p + 1)} className="px-2 py-1 text-xs bg-slate-100 hover:bg-slate-200 rounded disabled:opacity-50">Siguiente</button>
                          </div>
                        </div>
                        {paginated.map(({ p, idx: i }) => ('''

code = code.replace(productos_map_pattern, productos_map_repl)

# We need to close the paginated map parenthesis
# Look for the closing of the map function
end_map_pattern = r'''          \)\)}
                </div>
              </div>
            \)}
  
            \{\/\* STEP 4'''
end_map_repl = r'''          ))}
                        {paginated.length === 0 && <div className="p-8 text-center text-slate-500 bg-white rounded-xl border border-slate-200">No hay artículos para mostrar.</div>}
                      </>
                    );
                  })()}
                </div>
              </div>
            )}
  
            {/* STEP 4'''
code = code.replace(end_map_pattern, end_map_repl)

# Let's fix the viewMode logic because there might be two maps (one for 'categorias' and one for 'lineal')
# Let's check how many times "previewData.productos.map" appears.
