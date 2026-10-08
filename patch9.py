import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add handleRefreshImages function
handle_refresh = r'''  const applyBulkEnvio = \(\) => \{'''
handle_refresh_repl = r'''  const handleRefreshImages = async () => {
    if (!window.confirm(¿Buscar e intentar emparejar imágenes locales para  artículos seleccionados?)) return;
    
    // Create payload
    const peticiones = [];
    selectedRows.forEach(idx => {
      const p = previewData.productos[idx];
      const rd = rowData[idx] || {};
      peticiones.push({
        idx,
        sku: rd.sku ?? p.SKU,
        modelo: rd.modelo ?? p.Modelo,
        titulo: rd.titulo ?? p.Titulo
      });
    });

    try {
      const res = await fetch('/api/refrescar-fotos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(peticiones)
      });
      const resultados = await res.json();
      
      let actualizadas = 0;
      setRowData(prev => {
        const next = { ...prev };
        resultados.forEach(item => {
          if (item.b64) {
            next[item.idx] = { ...next[item.idx], localImages: [item.b64] };
            actualizadas++;
          }
        });
        return next;
      });
      alert(✅ Se emparejaron fotos para  artículos.);
    } catch (e) {
      alert('❌ Error al intentar refrescar fotos.');
    }
  };

  const applyBulkEnvio = () => {'''
code = re.sub(handle_refresh, handle_refresh_repl, code)

# 2. Add the button to the UI
btn_pattern = r'''<button onClick=\{applyBulkEnvio\} className="text-xs px-3 py-1\.5 rounded-lg bg-cyan-600 hover:bg-cyan-700 text-white font-semibold transition-colors flex items-center gap-1">
                  <Zap size=\{11\}\/> Aplicar Envio
                </button>
                <span className="text-slate-200">\|<\/span>'''
btn_repl = r'''<button onClick={applyBulkEnvio} className="text-xs px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-700 text-white font-semibold transition-colors flex items-center gap-1">
                  <Zap size={11}/> Aplicar Envio
                </button>
                <span className="text-slate-200">|</span>
                <button onClick={handleRefreshImages} className="text-xs px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold transition-colors flex items-center gap-1">
                  <Camera size={11}/> Refrescar Fotos Locales
                </button>
                <span className="text-slate-200">|</span>'''
code = re.sub(btn_pattern, btn_repl, code)

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched handleRefreshImages")
