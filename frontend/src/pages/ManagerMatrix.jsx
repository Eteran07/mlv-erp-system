import React, { useState, useEffect } from 'react';
import { Search, Filter, Play, Pause, Trash2, RefreshCw, AlertCircle, Image as ImageIcon, Save } from 'lucide-react';

export default function ManagerMatrix() {
  const [cuentas, setCuentas] = useState([]);
  const [cuentaActiva, setCuentaActiva] = useState('');
  const [items, setItems] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [query, setQuery] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('todas');
  const [selectedItems, setSelectedItems] = useState(new Set());
  const [actionLoading, setActionLoading] = useState(false);
  const [editedItems, setEditedItems] = useState({});

  // Cargar cuentas al inicio
  useEffect(() => {
    fetch('/cuentas')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setCuentas(data);
          if (data.length > 0) setCuentaActiva(data[0].archivo);
        } else {
          console.error("Respuesta inesperada al cargar cuentas:", data);
          if (data.detail === "Credenciales invalidas" || data.detail === "Not authenticated") {
            alert("Por favor, inicia sesión en la aplicación. La página se recargará.");
            window.location.reload();
          }
        }
      })
      .catch(err => console.error("Error cargando cuentas:", err));
  }, []);

  // Cargar publicaciones cuando cambian los filtros
  useEffect(() => {
    if (!cuentaActiva) return;
    cargarPublicaciones();
  }, [cuentaActiva, offset, filtroEstado]);

  const cargarPublicaciones = async () => {
    setLoading(true);
    setSelectedItems(new Set()); // Limpiar selección al recargar
    setEditedItems({}); // Limpiar ediciones al recargar
    try {
      const qParams = new URLSearchParams({
        cuenta: cuentaActiva,
        offset: offset,
        q: query,
        filtro_estado: filtroEstado
      });
      const res = await fetch(`/api/manager/publicaciones?${qParams.toString()}`);
      const data = await res.json();
      
      if (data.error) {
        alert(data.error);
        setItems([]);
        setTotalItems(0);
      } else {
        setItems(data.items || []);
        setTotalItems(data.total || 0);
      }
    } catch (error) {
      console.error("Error cargando publicaciones:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setOffset(0);
    cargarPublicaciones();
  };

  const toggleSelection = (id) => {
    const newSel = new Set(selectedItems);
    if (newSel.has(id)) newSel.delete(id);
    else newSel.add(id);
    setSelectedItems(newSel);
  };

  const toggleAll = (e) => {
    if (e.target.checked) {
      setSelectedItems(new Set(items.map(i => i.id)));
    } else {
      setSelectedItems(new Set());
    }
  };

  const cambiarEstado = async (estado) => {
    if (selectedItems.size === 0) return alert("Selecciona al menos una publicación.");
    
    let confirmMsg = estado === 'active' ? '¿Activar' : (estado === 'paused' ? '¿Pausar' : '¿Eliminar');
    if (!window.confirm(`${confirmMsg} ${selectedItems.size} publicaciones?`)) return;

    setActionLoading(true);
    try {
      const res = await fetch('/api/manager/estado', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cuenta: cuentaActiva,
          ids: Array.from(selectedItems),
          estado: estado
        })
      });
      const data = await res.json();
      if (data.error) {
        alert(data.error);
      } else {
        alert(`Operación completada.\nÉxitos: ${data.exitos}\nErrores: ${data.errores}`);
        cargarPublicaciones();
      }
    } catch (e) {
      alert("Error de red al cambiar estado.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleEditChange = (id, field, value) => {
    setEditedItems(prev => ({
      ...prev,
      [id]: {
        ...(prev[id] || {}),
        [field]: value
      }
    }));
  };

  const guardarCambios = async () => {
    const itemsToUpdate = Object.entries(editedItems).map(([id, changes]) => ({
      id,
      ...changes
    }));
    
    if (itemsToUpdate.length === 0) return;
    
    setActionLoading(true);
    try {
      const res = await fetch('/api/manager/actualizar-items', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cuenta: cuentaActiva,
          items: itemsToUpdate
        })
      });
      const data = await res.json();
      if (data.error) {
        alert(data.error);
      } else {
        let msg = `Cambios guardados.\nÉxitos: ${data.exitos}\nErrores: ${data.errores}`;
        if (data.detalles && data.detalles.length) msg += `\nDetalles:\n${data.detalles.join('\n')}`;
        alert(msg);
        setEditedItems({});
        cargarPublicaciones();
      }
    } catch (error) {
      alert("Error al guardar los cambios.");
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
    <div className="flex flex-col h-full bg-slate-50">
      {/* Header Actions */}
      <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 mb-6 flex flex-wrap gap-4 items-center justify-between">
        
        <div className="flex gap-4 items-center">
          <div className="flex flex-col">
            <label className="text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider">Cuenta</label>
            <select 
              className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-slate-50 min-w-[200px]"
              value={cuentaActiva}
              onChange={(e) => { setCuentaActiva(e.target.value); setOffset(0); }}
            >
              {cuentas.map(c => (
                <option key={c.archivo} value={c.archivo}>{c.nombre}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col">
            <label className="text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider">Estado</label>
            <select 
              className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-slate-50"
              value={filtroEstado}
              onChange={(e) => { setFiltroEstado(e.target.value); setOffset(0); }}
            >
              <option value="todas">Todas (Activas y Pausadas)</option>
              <option value="activas">Solo Activas</option>
              <option value="pausadas">Solo Pausadas</option>
              <option value="infracciones">Con Infracciones</option>
            </select>
          </div>
        </div>

        <form onSubmit={handleSearch} className="flex gap-2 items-end">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 text-slate-400" size={16} />
            <input 
              type="text" 
              placeholder="Buscar SKU, Título o ID..." 
              className="border border-slate-300 rounded-lg pl-9 pr-4 py-2 text-sm w-72 focus:ring-2 focus:ring-blue-500 outline-none"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
            Buscar
          </button>
        </form>

      </div>

      {/* Bulk Actions */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex gap-2">
          <button 
            disabled={selectedItems.size === 0 || actionLoading}
            onClick={() => cambiarEstado('active')}
            className="bg-green-600 disabled:opacity-50 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
          >
            <Play size={16} /> Activar Seleccionados ({selectedItems.size})
          </button>
          <button 
            disabled={selectedItems.size === 0 || actionLoading}
            onClick={() => cambiarEstado('paused')}
            className="bg-amber-500 disabled:opacity-50 hover:bg-amber-600 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
          >
            <Pause size={16} /> Pausar Seleccionados ({selectedItems.size})
          </button>
          <button 
            disabled={selectedItems.size === 0 || actionLoading}
            onClick={() => cambiarEstado('deleted')}
            className="bg-red-500 disabled:opacity-50 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
          >
            <Trash2 size={16} /> Eliminar
          </button>

          {Object.keys(editedItems).length > 0 && (
            <button 
              disabled={actionLoading}
              onClick={guardarCambios}
              className="bg-blue-600 disabled:opacity-50 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors ml-4"
            >
              <Save size={16} /> Guardar {Object.keys(editedItems).length} Cambios
            </button>
          )}
        </div>
        
        <div className="text-sm font-medium text-slate-600">
          Total: {totalItems} publicaciones
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 flex-1 overflow-hidden flex flex-col">
        <div className="overflow-x-auto flex-1 max-h-[60vh]">
          <table className="w-full text-left border-collapse">
            <thead className="bg-slate-100 text-slate-600 text-xs uppercase sticky top-0 z-10 shadow-sm">
              <tr>
                <th className="p-3 w-12 text-center border-b border-slate-200">
                  <input type="checkbox" onChange={toggleAll} checked={items.length > 0 && selectedItems.size === items.length} className="rounded text-blue-600 focus:ring-blue-500" />
                </th>
                <th className="p-3 border-b border-slate-200 font-semibold w-24">ID MLV</th>
                <th className="p-3 border-b border-slate-200 font-semibold w-32">SKU</th>
                <th className="p-3 border-b border-slate-200 font-semibold">Título</th>
                <th className="p-3 border-b border-slate-200 font-semibold w-24 text-right">Precio</th>
                <th className="p-3 border-b border-slate-200 font-semibold w-20 text-center">Stock</th>
                <th className="p-3 border-b border-slate-200 font-semibold w-28 text-center">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {loading ? (
                <tr>
                  <td colSpan="7" className="p-12 text-center text-slate-400">
                    <RefreshCw className="animate-spin mx-auto mb-2" size={24} />
                    Cargando publicaciones...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan="7" className="p-12 text-center text-slate-400">
                    No se encontraron publicaciones.
                  </td>
                </tr>
              ) : (
                items.map(item => (
                  <tr key={item.id} className="hover:bg-blue-50/50 transition-colors">
                    <td className="p-3 text-center">
                      <input 
                        type="checkbox" 
                        className="rounded text-blue-600 focus:ring-blue-500" 
                        checked={selectedItems.has(item.id)}
                        onChange={() => toggleSelection(item.id)}
                      />
                    </td>
                    <td className="p-3 font-medium text-blue-600">
                      <a href={`https://articulo.mercadolibre.com.ve/${item.id}`} target="_blank" rel="noreferrer" className="hover:underline">
                        {item.id}
                      </a>
                    </td>
                    <td className="p-3 text-slate-600 font-mono text-xs">{item.sku}</td>
                    <td className="p-3">
                      <div className="flex items-center gap-3">
                        {item.thumbnail ? (
                          <img src={item.thumbnail} alt={item.id} className="w-10 h-10 object-contain rounded border border-slate-200 bg-white shrink-0" />
                        ) : (
                          <div className="w-10 h-10 rounded border border-slate-200 bg-slate-100 shrink-0 flex items-center justify-center text-slate-300">
                            <ImageIcon size={16} />
                          </div>
                        )}
                        <div className="font-medium text-slate-800">
                          {item.title}
                          {item.infraccion_razon && (
                            <div className="text-xs text-red-600 flex items-center gap-1 mt-1 font-normal bg-red-50 p-1 rounded">
                              <AlertCircle size={12} /> {item.infraccion_razon}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="p-3">
                      <div className="flex justify-end items-center gap-1">
                        <span className="text-slate-400 text-xs">$</span>
                        <input 
                          type="number"
                          className="w-24 border border-slate-300 rounded px-2 py-1 text-right text-sm font-semibold text-slate-700 focus:ring-2 focus:ring-blue-500 outline-none"
                          value={editedItems[item.id]?.price !== undefined ? editedItems[item.id].price : item.price}
                          onChange={(e) => handleEditChange(item.id, 'price', e.target.value)}
                        />
                      </div>
                    </td>
                    <td className="p-3 text-center">
                      <input 
                        type="number"
                        className={`w-16 border rounded px-2 py-1 text-center text-sm font-bold focus:ring-2 focus:ring-blue-500 outline-none mx-auto block ${
                          (editedItems[item.id]?.stock ?? item.stock) > 0 ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'
                        }`}
                        value={editedItems[item.id]?.stock !== undefined ? editedItems[item.id].stock : item.stock}
                        onChange={(e) => handleEditChange(item.id, 'stock', e.target.value)}
                      />
                    </td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[item.status] || statusColors.closed}`}>
                        {statusTranslations[item.status] || item.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {/* Pagination Footer */}
        <div className="bg-slate-50 border-t border-slate-200 p-3 flex justify-between items-center text-sm">
          <div className="text-slate-500">
            Mostrando {items.length > 0 ? offset + 1 : 0} - {Math.min(offset + 50, totalItems)} de {totalItems}
          </div>
          <div className="flex gap-2">
            <button 
              disabled={offset === 0 || loading}
              onClick={() => setOffset(Math.max(0, offset - 50))}
              className="px-3 py-1 border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-50 transition-colors bg-white font-medium shadow-sm"
            >
              Anterior
            </button>
            <button 
              disabled={offset + 50 >= totalItems || loading}
              onClick={() => setOffset(offset + 50)}
              className="px-3 py-1 border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-50 transition-colors bg-white font-medium shadow-sm"
            >
              Siguiente
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

