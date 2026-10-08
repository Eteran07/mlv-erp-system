import React, { useState, useEffect } from 'react';
import { Search, Play, Pause, RefreshCw, AlertCircle, Image as ImageIcon } from 'lucide-react';

export default function MultiAccountAction() {
  const [cuentas, setCuentas] = useState([]);
  const [selectedCuentas, setSelectedCuentas] = useState(new Set());
  const [sku, setSku] = useState('');
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [resultados, setResultados] = useState(null); // Array de resultados por cuenta

  useEffect(() => {
    fetch('/cuentas')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setCuentas(data);
          setSelectedCuentas(new Set(data.map(c => c.archivo))); // Seleccionar todas por defecto
        }
      })
      .catch(err => console.error("Error cargando cuentas:", err));
  }, []);

  const toggleCuenta = (archivo) => {
    const newSel = new Set(selectedCuentas);
    if (newSel.has(archivo)) newSel.delete(archivo);
    else newSel.add(archivo);
    setSelectedCuentas(newSel);
  };

  const toggleTodasCuentas = (e) => {
    if (e.target.checked) setSelectedCuentas(new Set(cuentas.map(c => c.archivo)));
    else setSelectedCuentas(new Set());
  };

  const buscarSKU = async (e) => {
    if (e) e.preventDefault();
    if (!sku.trim()) return alert("Ingresa un SKU para buscar");
    if (selectedCuentas.size === 0) return alert("Selecciona al menos una cuenta para buscar");

    setLoading(true);
    setResultados(null);
    try {
      // Necesitamos crear un endpoint que busque un SKU en múltiples cuentas.
      // O hacer peticiones individuales a cada cuenta desde el frontend usando el endpoint de publicaciones.
      
      const promises = Array.from(selectedCuentas).map(async (cuentaArchivo) => {
        const cuentaObj = cuentas.find(c => c.archivo === cuentaArchivo);
        try {
          const res = await fetch(`/api/manager/publicaciones?cuenta=${encodeURIComponent(cuentaArchivo)}&q=${encodeURIComponent(sku.trim())}`);
          const data = await res.json();
          return {
            cuenta: cuentaObj,
            items: data.items || [],
            error: data.error
          };
        } catch (err) {
          return { cuenta: cuentaObj, items: [], error: "Error de red" };
        }
      });

      const results = await Promise.all(promises);
      setResultados(results);

    } catch (error) {
      console.error("Error en la búsqueda masiva:", error);
    } finally {
      setLoading(false);
    }
  };

  const cambiarEstadoMasivo = async (estado) => {
    if (!resultados) return;
    
    // Recopilar todos los IDs encontrados
    const cuentasConItems = resultados.filter(r => r.items && r.items.length > 0);
    if (cuentasConItems.length === 0) return alert("No hay artículos encontrados para modificar.");

    let confirmMsg = estado === 'active' ? '¿Activar' : '¿Pausar';
    if (!window.confirm(`${confirmMsg} este SKU en las ${cuentasConItems.length} cuentas donde se encontró?`)) return;

    setActionLoading(true);
    try {
      // Hacemos un request por cada cuenta que tiene este item
      const promises = cuentasConItems.map(async (r) => {
        const ids = r.items.map(item => item.id);
        const res = await fetch('/api/manager/estado', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            cuenta: r.cuenta.archivo,
            ids: ids,
            estado: estado
          })
        });
        return await res.json();
      });

      const resAll = await Promise.all(promises);
      
      let totalExitos = 0;
      let totalErrores = 0;
      resAll.forEach(r => {
        if (!r.error) {
          totalExitos += (r.exitos || 0);
          totalErrores += (r.errores || 0);
        }
      });

      alert(`Operación masiva completada.\nÉxitos: ${totalExitos}\nErrores: ${totalErrores}`);
      buscarSKU(); // Recargar resultados
      
    } catch (err) {
      alert("Error ejecutando la acción masiva.");
    } finally {
      setActionLoading(false);
    }
  };

  const statusColors = {
    active: 'bg-green-100 text-green-700',
    paused: 'bg-amber-100 text-amber-700',
    closed: 'bg-slate-100 text-slate-700',
    under_review: 'bg-blue-100 text-blue-700',
    inactive: 'bg-red-100 text-red-700'
  };

  const statusTranslations = {
    active: 'Activa',
    paused: 'Pausada',
    closed: 'Finalizada',
    under_review: 'En Revisión',
    inactive: 'Inactiva'
  };

  return (
    <div className="flex flex-col h-full bg-slate-50 gap-6">
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        <h3 className="font-bold text-slate-800 mb-4 text-lg">1. Selecciona las Cuentas</h3>
        <div className="flex items-center gap-2 mb-3 pb-3 border-b border-slate-100">
          <input 
            type="checkbox" 
            id="chk-todas"
            className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4"
            checked={cuentas.length > 0 && selectedCuentas.size === cuentas.length}
            onChange={toggleTodasCuentas}
          />
          <label htmlFor="chk-todas" className="font-medium text-sm text-slate-700 cursor-pointer">Seleccionar Todas</label>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 max-h-48 overflow-y-auto">
          {cuentas.map(c => (
            <label key={c.archivo} className={`flex items-center gap-2 p-2 rounded border cursor-pointer transition-colors ${selectedCuentas.has(c.archivo) ? 'bg-blue-50 border-blue-200' : 'bg-white border-slate-200 hover:bg-slate-50'}`}>
              <input 
                type="checkbox" 
                className="rounded text-blue-600 focus:ring-blue-500"
                checked={selectedCuentas.has(c.archivo)}
                onChange={() => toggleCuenta(c.archivo)}
              />
              <span className="text-sm font-medium text-slate-700 truncate" title={c.nombre}>{c.nombre}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        <h3 className="font-bold text-slate-800 mb-4 text-lg">2. Buscar SKU (Búsqueda Masiva)</h3>
        <form onSubmit={buscarSKU} className="flex gap-4">
          <div className="relative flex-1 max-w-xl">
            <Search className="absolute left-3 top-2.5 text-slate-400" size={20} />
            <input 
              type="text" 
              placeholder="Ingresa el SKU a buscar en las cuentas seleccionadas..." 
              className="w-full border border-slate-300 rounded-lg pl-10 pr-4 py-2 text-slate-700 focus:ring-2 focus:ring-blue-500 outline-none"
              value={sku}
              onChange={(e) => setSku(e.target.value)}
              required
            />
          </div>
          <button 
            type="submit" 
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 py-2 rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            {loading ? <RefreshCw className="animate-spin" size={18} /> : <Search size={18} />}
            Buscar en {selectedCuentas.size} cuentas
          </button>
        </form>
      </div>

      {resultados && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 flex-1 overflow-hidden flex flex-col">
          <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
            <h3 className="font-bold text-slate-800">
              Resultados para: <span className="text-blue-600 font-mono">{sku}</span>
            </h3>
            
            <div className="flex gap-2">
              <button 
                disabled={actionLoading}
                onClick={() => cambiarEstadoMasivo('active')}
                className="bg-green-600 disabled:opacity-50 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
              >
                <Play size={16} /> Activar en todas
              </button>
              <button 
                disabled={actionLoading}
                onClick={() => cambiarEstadoMasivo('paused')}
                className="bg-amber-500 disabled:opacity-50 hover:bg-amber-600 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
              >
                <Pause size={16} /> Pausar en todas
              </button>
            </div>
          </div>

          <div className="overflow-x-auto flex-1 p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {resultados.map((res, index) => (
                <div key={index} className="border border-slate-200 rounded-lg overflow-hidden flex flex-col">
                  <div className="bg-slate-100 p-3 border-b border-slate-200 font-bold text-slate-700 flex justify-between items-center">
                    <span className="truncate pr-2">{res.cuenta.nombre}</span>
                    {res.items.length > 0 ? (
                      <span className="bg-green-100 text-green-700 text-xs px-2 py-1 rounded-full font-bold">Encontrado</span>
                    ) : (
                      <span className="bg-slate-200 text-slate-500 text-xs px-2 py-1 rounded-full font-bold">No existe</span>
                    )}
                  </div>
                  <div className="p-4 bg-white flex-1">
                    {res.error ? (
                      <div className="text-red-500 text-sm flex items-center gap-2"><AlertCircle size={16}/> {res.error}</div>
                    ) : res.items.length === 0 ? (
                      <div className="text-slate-400 text-sm italic">Este artículo no existe en esta cuenta.</div>
                    ) : (
                      <div className="flex flex-col gap-3">
                        {res.items.map(item => (
                          <div key={item.id} className="border border-blue-100 bg-blue-50/30 p-3 rounded text-sm flex flex-col gap-2">
                            <div className="flex gap-3">
                              {item.thumbnail ? (
                                <img src={item.thumbnail} alt={item.id} className="w-12 h-12 object-contain rounded border border-slate-200 bg-white shrink-0" />
                              ) : (
                                <div className="w-12 h-12 rounded border border-slate-200 bg-slate-100 shrink-0 flex items-center justify-center text-slate-300">
                                  <ImageIcon size={20} />
                                </div>
                              )}
                              <div className="flex-1 min-w-0">
                                <div className="font-semibold text-blue-700 mb-1 truncate">
                                  <a href={`https://articulo.mercadolibre.com.ve/${item.id}`} target="_blank" rel="noreferrer" className="hover:underline">
                                    {item.id}
                                  </a>
                                </div>
                                <div className="text-slate-800 font-medium line-clamp-2" title={item.title}>{item.title}</div>
                              </div>
                            </div>
                            <div className="flex justify-between items-center mt-auto pt-2 border-t border-blue-100">
                              <div className="font-bold text-slate-700">${item.price}</div>
                              <div className="text-xs text-slate-500">Stock: <span className="font-bold text-slate-700">{item.stock}</span></div>
                              <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${statusColors[item.status] || statusColors.closed}`}>
                                {statusTranslations[item.status] || item.status}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

