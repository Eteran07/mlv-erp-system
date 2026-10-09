import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  FileSpreadsheet, Upload, Settings2, Eye, Play,
  CheckCircle2, AlertCircle, Loader2, ArrowRight, Database, Table,
  Rows3, LayoutGrid, Bot, Camera, Zap, Image,
  ChevronDown, ChevronUp, Star, ZoomIn
} from 'lucide-react';

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
//  Constants
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const EXPOSURE_OPTS = [
  { value: 'bronze',       label: 'Bronce / Estandar' },
  { value: 'gold_special', label: 'Clasica' },
  { value: 'gold_pro',     label: 'Premium' },
];
const SHIPPING_OPTS = [
  { value: 'me2_free',     label: 'Mercado Envios - Gratis' },
  { value: 'custom_free',  label: 'Envio Gratis Nacional (Custom)' },
  { value: 'me2_buyer',    label: 'Mercado Envios - Cobro en Destino' },
  { value: 'not_specified',label: 'Acordar con el Vendedor' },
];

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
//  ProductRow - una fila expandible con todos los campos
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function ProductRow({ p, idx, selected, onToggle, rowData, onRowChange, onAIFill, onOpenCatSearch, onDiscard }) {
  const [expanded, setExpanded] = useState(false);
  const [showDesc, setShowDesc] = useState(false);
  const [iaLoading, setIaLoading] = useState(false);
  const [showAttrModal, setShowAttrModal] = useState(false);

  const [iaStatus, setIaStatus] = useState(null); // null | 'ok' | 'error'
  const fileRef = useRef();

  const handleAI = async () => {
    setIaLoading(true);
    setIaStatus(null);
    const fd = new FormData();
    fd.append('titulo', rowData.titulo ?? p.Titulo);
    fd.append('cat_id', (rowData.cat_id ?? p.Categoria_ID) || '');
    fd.append('sku', rowData.sku ?? p.SKU ?? '');
    if (rowData.errorML) fd.append('error_previo', rowData.errorML);
    try {
      const res = await fetch('/api/autollenar-atributos-ia', { method: 'POST', body: fd });
      const data = await res.json();
      if (data.atributos || data.descripcion) {
        onAIFill(idx, data, p.DescripcionFinal || '');
        setIaStatus('ok');
        if (rowData.errorML) onRowChange(idx, 'errorML', null);
      } else {
        setIaStatus('error');
      }
    } catch {
      setIaStatus('error');
    } finally {
      setIaLoading(false);
    }
  };

  const handleImages = (e) => {
    const files = Array.from(e.target.files);
    const previews = files.map(f => URL.createObjectURL(f));
    onRowChange(idx, 'localImages', [...(rowData.localImages || []), ...previews]);
    onRowChange(idx, 'imageFiles',  [...(rowData.imageFiles  || []), ...files]);
  };

  const removeImage = (imgIdx) => {
    const imgs = [...(rowData.localImages || [])];
    const fls  = [...(rowData.imageFiles  || [])];
    imgs.splice(imgIdx, 1);
    fls.splice(imgIdx, 1);
    onRowChange(idx, 'localImages', imgs);
    onRowChange(idx, 'imageFiles', fls);
  };

  const precioVal = rowData.precio ?? p.Precio;
  const precioBajo = parseFloat(precioVal) > 0 && parseFloat(precioVal) < 2.0;

  return (
    <div className={`border-b transition-all ${selected ? 'bg-white' : 'bg-slate-50 opacity-60'}`}>
      {/* Header row */}
      <div className="flex items-center gap-4 p-4">
        {/* Checkbox */}
        <input
          type="checkbox" checked={selected} onChange={() => onToggle(idx)}
          className="mt-1 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer w-4 h-4 shrink-0"
        />

        {/* Fila # */}
        <span className="text-slate-400 font-mono text-xs mt-1.5 w-5 shrink-0">{p.FilaExcel}</span>

        {/* Titulo editable inline */}
        <div className="flex-1 min-w-0">
          <input
            type="text"
            value={rowData.titulo ?? p.Titulo}
            onChange={e => onRowChange(idx, 'titulo', e.target.value)}
            maxLength={60}
            className="w-full font-bold text-slate-800 text-base bg-transparent border-b border-transparent hover:border-slate-300 focus:border-blue-400 focus:outline-none pb-0.5 transition-colors"
          />
          <div className="flex flex-wrap gap-1 mt-1 items-center">
            <span 
              className="text-[10px] bg-blue-50 text-blue-700 px-2 py-0.5 rounded font-bold cursor-pointer hover:bg-blue-100 border border-blue-200 transition-colors flex items-center gap-1"
              onClick={() => onOpenCatSearch(idx)}
              title="Click para buscar y cambiar categoria manualmente"
            >
              🏷️ {rowData.cat_nombre ?? p.CategoriaNombre ?? 'Sin categoria'} {rowData.cat_id ? `(${rowData.cat_id})` : ''} <span className="opacity-70">(Cambiar)</span>
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              SKU: {p.SKU || 'N/A'} | Mod: {p.Modelo || 'N/A'}
            </span>
            {p.AlertaImagen && (
              <span className="text-[10px] text-amber-600 flex items-center gap-0.5">
                <AlertCircle size={9}/> {p.AlertaImagen}
              </span>
            )}
            {iaStatus === 'ok'    && <span className="text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-bold">IA Completado</span>}
            {iaStatus === 'error' && <span className="text-[10px] bg-red-100 text-red-700 px-1.5 py-0.5 rounded font-bold">Error IA</span>}
          </div>
          {rowData.errorML && (
            <div className="mt-2 text-[11px] bg-red-50 text-red-600 p-2 rounded border border-red-200 flex items-start gap-2">
              <AlertCircle size={14} className="shrink-0 mt-0.5"/>
              <div className="flex-1">
                <strong>Error de Publicación:</strong> {rowData.errorML}
              </div>
              <button onClick={handleAI} disabled={iaLoading} className="bg-red-100 hover:bg-red-200 text-red-700 px-2 py-1 rounded font-bold shrink-0">
                {iaLoading ? 'Corrigiendo...' : 'Corregir con IA'}
              </button>
            </div>
          )}
        </div>

        {/* Precio */}
        <div className="shrink-0">
          <label className="block text-[9px] uppercase text-slate-400 font-bold mb-0.5">Precio</label>
          <input
            type="number" step="0.01"
            value={precioVal}
            onChange={e => onRowChange(idx, 'precio', e.target.value)}
            className={`w-24 text-right text-sm font-bold border rounded px-2 py-0.5 bg-white focus:outline-none ${precioBajo ? 'border-red-400 text-red-600 focus:border-red-500' : 'border-slate-200 text-emerald-600 focus:border-emerald-400'}`}
          />
          {precioBajo && <div className="text-[9px] text-red-500 mt-0.5 font-bold">Min $2.00</div>}
        </div>

        {/* Stock */}
        <div className="shrink-0">
          <label className="block text-[9px] uppercase text-slate-400 font-bold mb-0.5">Stock</label>
          <input
            type="number"
            value={rowData.stock ?? p.Stock}
            onChange={e => onRowChange(idx, 'stock', e.target.value)}
            className="w-16 text-right text-sm font-bold text-slate-700 border border-slate-200 rounded px-2 py-0.5 bg-white focus:border-blue-400 focus:outline-none"
          />
        </div>

        {/* Exposicion / Envio */}
        <div className="flex flex-col gap-1 shrink-0 min-w-[145px]">
          <select
            value={rowData.exposicion ?? 'bronze'}
            onChange={e => onRowChange(idx, 'exposicion', e.target.value)}
            className="text-[11px] border border-slate-200 rounded px-1.5 py-0.5 bg-white focus:outline-none font-bold text-slate-700"
          >
            {EXPOSURE_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select
            value={rowData.envio ?? 'me2_free'}
            onChange={e => onRowChange(idx, 'envio', e.target.value)}
            className="text-[10px] border border-slate-200 rounded px-1.5 py-0.5 bg-white focus:outline-none text-slate-700"
          >
            {SHIPPING_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        {/* Badges cuentas */}
        <div className="flex gap-1 flex-wrap shrink-0 min-w-[250px]">
          {Object.entries(p.EstadoCuentas || {}).map(([c_name, status]) => (
            <span key={c_name} title={c_name} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${status === 'EXISTE' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>
              {c_name.substring(0, 4).toUpperCase()}: {status === 'EXISTE' ? 'Publicado' : 'No'}
            </span>
          ))}
        </div>

        {/* Acciones rapidas */}
        <div className="flex gap-1 shrink-0">
          <button onClick={() => onDiscard && onDiscard(idx)} title="Descartar este producto de la carga"
            className="p-1.5 rounded-lg bg-red-50 text-red-600 hover:bg-red-100 transition-colors font-bold text-xs flex items-center justify-center min-w-[28px]">
            &times;
          </button>
          <button onClick={handleAI} disabled={iaLoading} title="Generar ficha con IA DeepSeek"
            className="p-1.5 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 disabled:opacity-50 transition-colors">
            {iaLoading ? <Loader2 size={14} className="animate-spin"/> : <Bot size={14}/>}
          </button>
          <button onClick={() => fileRef.current?.click()} title="Adjuntar imagenes"
            className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600 hover:bg-emerald-100 transition-colors">
            <Camera size={14}/>
          </button>
          <button onClick={() => setExpanded(v => !v)} title="Ver descripcion y detalles"
            className="p-1.5 rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors">
            {expanded ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
          </button>
        </div>
        <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" multiple className="hidden" onChange={handleImages}/>
      </div>

      {/* Panel expandido: descripcion + imagenes + atributos IA */}
      {expanded && (
        <div className="border-t border-slate-100 p-4 bg-slate-50 flex flex-col gap-4">
          {/* Descripcion */}
          <div>
            <div className="flex items-center gap-3 mb-2">
              <label className="block text-xs font-bold text-slate-600">Descripción Comercial (Plantilla Completa)</label>
              <button 
                onClick={() => setShowDesc(true)} 
                className="text-[11px] bg-[#4b5e72] text-white px-3 py-1.5 rounded font-bold hover:bg-[#34495e] flex items-center gap-1 shadow-sm"
              >
                <Eye size={12} /> Ver Descripción Final
              </button>
            </div>
            
            {showDesc && (
              <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-200">
                  <div className="p-4 border-b border-slate-200 flex items-center gap-2">
                    <Eye size={20} className="text-slate-700" />
                    <h3 className="font-black text-lg text-slate-800 tracking-tight">Vista Previa de la Descripción</h3>
                  </div>
                  <div className="p-4 bg-slate-50 flex-1 overflow-y-auto">
                    <p className="text-sm text-slate-500 mb-3">Así se verá el texto final publicado en Mercado Libre, incluyendo la ficha técnica ensamblada por el ERP.</p>
                    <textarea
                      rows={20}
                      value={rowData.descripcion ?? p.DescripcionFinal ?? ''}
                      onChange={e => onRowChange(idx, 'descripcion', e.target.value)}
                      placeholder="La IA puede generar esta descripcion automaticamente. Tambien puedes editarla manualmente."
                      className="w-full border border-slate-300 rounded-lg p-4 text-sm focus:border-blue-500 focus:outline-none bg-white font-mono shadow-inner resize-none"
                    />
                  </div>
                  <div className="p-4 border-t border-slate-200 flex justify-end bg-slate-100 rounded-b-xl">
                    <button 
                      onClick={() => setShowDesc(false)} 
                      className="px-6 py-2 bg-[#6b7c93] text-white font-bold rounded-lg hover:bg-[#52637a] shadow-sm transition-colors"
                    >
                      Cerrar Vista Previa
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Imagenes */}
          <div>
            <label className="block text-xs font-bold text-slate-600 mb-1">Imagenes del Producto</label>
            {(rowData.localImages || []).length === 0 ? (
              <div
                onClick={() => fileRef.current?.click()}
                className="border-2 border-dashed border-slate-300 rounded-lg h-28 flex flex-col items-center justify-center text-slate-400 text-xs cursor-pointer hover:border-blue-400 hover:text-blue-500 transition-colors"
              >
                <Image size={22} className="mb-1"/>
                Clic o arrastra fotos aqui
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {(rowData.localImages || []).map((src, i) => (
                  <div key={i} className="relative group">
                    <img src={src} alt="" className="w-16 h-16 object-cover rounded-lg border border-slate-200 shadow-sm"/>
                    <button
                      onClick={() => removeImage(i)}
                      className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white rounded-full text-[10px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity leading-none"
                    >x</button>
                  </div>
                ))}
                <div
                  onClick={() => fileRef.current?.click()}
                  className="w-16 h-16 border-2 border-dashed border-slate-300 rounded-lg flex items-center justify-center text-slate-400 cursor-pointer hover:border-blue-400 hover:text-blue-500 transition-colors text-xl"
                >+</div>
              </div>
            )}
          </div>

          {/* Atributos IA */}
          <div className="col-span-2 mt-2">
            <div className="flex items-center gap-3 mb-2">
              <label className="block text-xs font-bold text-slate-600">Ficha Tecnica / Atributos (IA o Manual)</label>
              <button onClick={() => setShowAttrModal(true)} className="text-[10px] bg-blue-100 text-blue-700 px-2 py-1 rounded font-bold hover:bg-blue-200">Editar Manualmente</button>
            </div>
            {rowData.aiAtributos && Object.keys(rowData.aiAtributos).length > 0 && (
            <div className="col-span-2">
              <label className="block text-xs font-bold text-slate-600 mb-1">Atributos Tecnicos (generados por IA)</label>
              <div className="flex flex-wrap gap-2">
                {Object.entries(rowData.aiAtributos).map(([k, v]) => (
                  <span key={k} className="text-[10px] bg-blue-50 border border-blue-200 text-blue-700 px-2 py-0.5 rounded-full font-mono">
                    {k}: <b>{String(v)}</b>
                  </span>
                ))}
              </div>
            </div>
          )}
          </div>
        </div>
      )}

      <AttributesModal
        isOpen={showAttrModal}
        onClose={() => setShowAttrModal(false)}
        catId={rowData.cat_id ?? p.Categoria_ID}
        titulo={p.Titulo}
        rowData={rowData}
        p={p}
        onSave={(vals) => {
           onRowChange(idx, 'aiAtributos', vals);
           setShowAttrModal(false);
        }}
      />
    </div>
  );
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  Main ExcelSync Component
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

function AttributesModal({ isOpen, onClose, catId, titulo, rowData, p, onSave }) {
  const [attrs, setAttrs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [localVals, setLocalVals] = useState(rowData?.aiAtributos || {});

  useEffect(() => {
    if (!isOpen) return;
    
    const init = { ...(rowData?.aiAtributos || {}) };
    if (!init.BRAND && p?.Marca) init.BRAND = p.Marca;
    if (!init.MODEL && p?.Modelo) init.MODEL = p.Modelo;
    
    setLocalVals(init);
    setLoading(true);
    fetch(`/api/atributos-categoria/${catId}`)
      .then(r => r.json())
      .then(d => { 
        setAttrs(d); 
        setLocalVals(init);
        setLoading(false); 
      })
      .catch(() => setLoading(false));
  }, [isOpen, catId, rowData, p]);

  const renderField = (a) => {
    const val = localVals[a.id] || '';
    if (a.value_type === "number_unit" && a.allowed_units && a.allowed_units.length > 0) {
      const currentUnit = a.allowed_units.find(u => val.endsWith(u)) || a.allowed_units[0];
      const num = val.replace(currentUnit, '').trim();
      return (
        <div className="flex gap-2">
          <input type="number" step="any" value={num} onChange={e => setLocalVals({...localVals, [a.id]: `${e.target.value} ${currentUnit}`.trim()})} className="flex-1 border border-slate-300 rounded-lg p-2 text-sm focus:border-blue-500 outline-none" placeholder={a.hint || ''} />
          <select value={currentUnit} onChange={e => setLocalVals({...localVals, [a.id]: `${num} ${e.target.value}`.trim()})} className="w-24 border border-slate-300 rounded-lg p-2 text-sm bg-white focus:border-blue-500 outline-none">
            {a.allowed_units.map(u => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
      );
    }
    if (a.values && a.values.length > 0) {
      return (
        <select value={val} onChange={e => setLocalVals({...localVals, [a.id]: e.target.value})} className="w-full border border-slate-300 rounded-lg p-2 text-sm bg-white focus:border-blue-500 outline-none">
          <option value="">Seleccione...</option>
          {a.values.map(v => <option key={v.id} value={v.name}>{v.name}</option>)}
        </select>
      );
    }
    return (
      <input type="text" value={val} onChange={e => setLocalVals({...localVals, [a.id]: e.target.value})} className="w-full border border-slate-300 rounded-lg p-2 text-sm focus:border-blue-500 outline-none" placeholder={a.hint || ''} />
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col animate-in zoom-in-95 duration-200">
        <div className="p-4 border-b border-slate-200 flex justify-between items-center">
          <h3 className="font-bold text-lg text-slate-800">Ficha Tecnica: {titulo}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 font-bold">&times;</button>
        </div>
        <div className="p-4 overflow-y-auto flex-1">
          {loading ? (
            <div className="flex justify-center p-8"><Loader2 className="animate-spin text-blue-500" size={32}/></div>
          ) : attrs.length === 0 ? (
            <div className="text-slate-500 text-center p-8">No hay atributos para esta categoria.</div>
          ) : (
            <div className="space-y-6">
              {attrs.filter(a => a.required).length > 0 && (
                <div>
                  <h4 className="text-sm font-black text-slate-800 uppercase tracking-wide mb-3 border-b border-slate-200 pb-1">Atributos Obligatorios</h4>
                  <div className="space-y-4">
                    {attrs.filter(a => a.required).map(a => (
                      <div key={a.id}>
                        <label className="block text-sm font-bold text-slate-700 mb-1">{a.name} <span className="text-red-500">*</span></label>
                        {renderField(a)}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {attrs.filter(a => !a.required).length > 0 && (
                <div>
                  <h4 className="text-sm font-black text-slate-500 uppercase tracking-wide mb-3 border-b border-slate-200 pb-1">Atributos Opcionales</h4>
                  <div className="space-y-4">
                    {attrs.filter(a => !a.required).map(a => (
                      <div key={a.id}>
                        <label className="block text-sm font-bold text-slate-600 mb-1">{a.name}</label>
                        {renderField(a)}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        <div className="p-4 border-t border-slate-200 flex justify-end gap-3 bg-slate-50 rounded-b-xl">
          <button onClick={onClose} className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-200 rounded-lg">Cancelar</button>
          <button onClick={() => { onSave(localVals); onClose(); }} className="px-6 py-2 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700">Guardar Ficha</button>
        </div>
      </div>
    </div>
  );
}

export default function ExcelSync() {
  const [dialog, setDialog] = useState({ isOpen: false, type: 'alert', message: '', onConfirm: null, onCancel: null });
  const [zoomLevel, setZoomLevel] = useState(100);
  const [toasts, setToasts] = useState([]);
  
  const customAlert = (message, type = 'success') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };
  const customConfirm = (message, onConfirmCallback) => setDialog({ isOpen: true, type: 'confirm', message, onConfirm: () => { setDialog({ isOpen: false, type: 'alert', message: '', onConfirm: null, onCancel: null }); if (onConfirmCallback) onConfirmCallback(); }, onCancel: () => setDialog({ isOpen: false, type: 'alert', message: '', onConfirm: null, onCancel: null }) });

  const [cuentas, setCuentas] = useState([]);
  const [cuentasActivas, setCuentasActivas] = useState(['TODAS']);

  // Step 1
  const [file, setFile] = useState(null);
  const [hojas, setHojas] = useState([]);
  const [columnas, setColumnas] = useState([]);
  const [hojaActiva, setHojaActiva] = useState('TODAS');
  const [loadingFile, setLoadingFile] = useState(false);
  const [rawPreview, setRawPreview] = useState([]);

  // Step 2
  const [filterMode, setFilterMode] = useState('all');
  const [config, setConfig] = useState({
    inicio: 1, fin: 100, cantidad_limite: 10,
    categoria_filtro: 'TODAS',
    filtrar_duplicados: 'true',
    verificar_todas: 'false',
  });
  const [mapping, setMapping] = useState({ col_tit: '', col_sku: '', col_mod: '', col_pre: '', col_stk: '' });

  // Step 3
  const [previewData, setPreviewData] = useState(null);
  const [selectedRows, setSelectedRows] = useState(new Set());
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [manualCatSearch, setManualCatSearch] = useState({ isOpen: false, idx: null, query: '', results: [], loading: false });
  const [globalCatSearch, setGlobalCatSearch] = useState({ query: '', results: [], loading: false });
  const [viewMode, setViewMode] = useState('categorias');
  const [rowData, setRowData] = useState({});
  const [currentPage, setCurrentPage] = useState(1);
  const [showPublished, setShowPublished] = useState(false);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [foldedCategories, setFoldedCategories] = useState(new Set());
  const [discardedItems, setDiscardedItems] = useState(new Set());

  const [iaAllLoading, setIaAllLoading] = useState(false);
  const [iaProgress, setIaProgress] = useState({ done: 0, total: 0 });
  const [bulkExposicion, setBulkExposicion] = useState('bronze');
  const [bulkEnvio, setBulkEnvio] = useState('me2_free');

  // Step 4
  const [isPublishing, setIsPublishing] = useState(false);
  const [progress, setProgress] = useState(null);
  const [publishResult, setPublishResult] = useState(null);
  const [activeTaskName, setActiveTaskName] = useState('');

  const [categorias, setCategorias] = useState([]);
  const [step, setStep] = useState(1);

  useEffect(() => {
    fetch('/cuentas').then(r => r.json()).then(d => { if (Array.isArray(d)) setCuentas(d); });
    fetch('/api/categorias-mlv').then(r => r.json()).then(d => {
      if (d.categorias) setCategorias(d.categorias);
      else if (Array.isArray(d)) setCategorias(d);
    });
  }, []);

  const startProgressTracking = () => {
    const iv = setInterval(async () => {
      try {
        const d = await fetch('/estado-progreso').then(r => r.json());
        setProgress(d);
      } catch {}
    }, 1000);
    return iv;
  };

  const onRowChange = useCallback((idx, field, value) => {
    setRowData(prev => ({ ...prev, [idx]: { ...(prev[idx] || {}), [field]: value } }));
    if (field === 'exposicion') {
      customAlert(`Exposicion actualizada a ${value === 'silver' ? 'Premium' : 'Clásica'} (Fila ${idx + 1})`);
    } else if (field === 'envio') {
      customAlert(`Envío actualizado a ${value === 'me2_free' ? 'Gratis' : value === 'me2' ? 'Cobro en Destino' : 'Acordar'} (Fila ${idx + 1})`);
    }
  }, []);

  const onAIFill = useCallback((idx, data, initialDesc = '') => {
    setRowData(prev => {
      let baseDesc = prev[idx]?.descripcion;
      if (baseDesc === undefined) {
        baseDesc = initialDesc;
      }
      const existingDesc = baseDesc || '';
      
      let newDesc = existingDesc;
      if (data.descripcion) {
         if (newDesc.includes('CARACTERISTICAS TECNICAS')) {
            newDesc = newDesc.replace('========================================\nCARACTERISTICAS TECNICAS\n========================================\n\n', '========================================\nCARACTERISTICAS TECNICAS\n========================================\n\n' + data.descripcion + '\n\n');
         } else {
            newDesc = (newDesc.trim() ? newDesc + '\n\n' : '') + data.descripcion;
         }
      }
      return {
        ...prev,
        [idx]: {
          ...(prev[idx] || {}),
          descripcion: newDesc,
          aiAtributos: data.atributos || {},
        },
      };
    });
  }, []);

  // Bulk apply
  const applyBulkExposicion = () => {
    if (selectedRows.size === 0) return customAlert('Seleccione al menos un producto.');
    setRowData(prev => {
      const next = { ...prev };
      selectedRows.forEach(i => { next[i] = { ...(next[i] || {}), exposicion: bulkExposicion }; });
      return next;
    });
    customAlert(`Exposicion aplicada a ${selectedRows.size} productos.`);
  };

  const handleRefreshImages = async (isSilent = false, specificIdxs = null, specificData = null) => {
    const silent = typeof isSilent === 'boolean' ? isSilent : false;
    const idxsToProcess = specificIdxs || Array.from(selectedRows);
    const dToUse = specificData || previewData || { productos: [] };
    const executeRefresh = async () => {
    const peticiones = [];
    idxsToProcess.forEach(idx => {
      const prods = dToUse?.productos || [];
      const p = prods[idx];
      if (!p) return;
      const rd = rowData[idx] || {};
      peticiones.push({ idx, sku: rd.sku ?? p.SKU, modelo: rd.modelo ?? p.Modelo, titulo: rd.titulo ?? p.Titulo });
    });

    try {
      const res = await fetch('/api/refrescar-fotos', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(peticiones) });
      const d = await res.json();
      const resultados = d.resultados || [];
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

      if (!silent) customAlert(`Imagenes actualizadas: ${actualizadas}`);
    } catch {
      if (!silent) customAlert('Error refrescando imagenes');
    }
    };
    if(!silent) customConfirm(`ÂBuscar e intentar emparejar imagenes locales para ${idxsToProcess.length} articulos?`, executeRefresh);
    else executeRefresh();
  };

  const applyBulkEnvio = () => {
    if (selectedRows.size === 0) return customAlert('Seleccione al menos un producto.');
    setRowData(prev => {
      const next = { ...prev };
      selectedRows.forEach(i => { next[i] = { ...(next[i] || {}), envio: bulkEnvio }; });
      return next;
    });
    customAlert(`Forma de envio aplicada a ${selectedRows.size} productos.`);
  };
  const toggleCurrentPage = () => {
    const pageIndices = paginatedItems.map(i => i.idx);
    const allOnPageSelected = pageIndices.every(idx => selectedRows.has(idx));
    
    const newSet = new Set(selectedRows);
    if (allOnPageSelected) {
      pageIndices.forEach(idx => newSet.delete(idx));
    } else {
      pageIndices.forEach(idx => newSet.add(idx));
    }
    setSelectedRows(newSet);
  };
  
  const toggleAll = () => {
    const allIndices = filteredItems.map(i => i.idx);
    setSelectedRows(selectedRows.size === allIndices.length ? new Set() : new Set(allIndices));
  };
  
  const [rangeStart, setRangeStart] = useState(1);
  const [rangeEnd, setRangeEnd] = useState(10);
  const selectRange = () => {
    const newSet = new Set(selectedRows);
    filteredItems.forEach((item, index) => {
      const pos = index + 1; // 1-based
      if (pos >= rangeStart && pos <= rangeEnd) {
        newSet.add(item.idx);
      }
    });
    setSelectedRows(newSet);
    customAlert(`Seleccionados del ${rangeStart} al ${rangeEnd}`);
  };

  // IA masiva
  const runAIBulk = async (idxs) => {
    const items = previewData?.productos || [];
    const validIdxs = idxs.filter(i => items[i]);
    if (!validIdxs.length) return;
    customConfirm(`Generar fichas IA para ${validIdxs.length} articulos? Se procesarn en lotes de 10.`, async () => {
      setIaAllLoading(true);
      setIaProgress({ done: 0, total: validIdxs.length });
      const BATCH = 3;
      for (let i = 0; i < validIdxs.length; i += BATCH) {
        const chunk = validIdxs.slice(i, i + BATCH);
        await Promise.all(chunk.map(async (idx) => {
          const p = items[idx];
          const rd = rowData[idx] || {};
          const fd = new FormData();
          fd.append('titulo', rd.titulo ?? p.Titulo);
          fd.append('cat_id', (rd.cat_id ?? p.Categoria_ID) || '');
          fd.append('sku', rd.sku ?? p.SKU ?? '');
          if (rd.errorML) fd.append('error_previo', rd.errorML);
          try {
            const res = await fetch('/api/autollenar-atributos-ia', { method: 'POST', body: fd });
            const data = await res.json();
            if (data.atributos || data.descripcion) {
               onAIFill(idx, data, p.DescripcionFinal || '');
               if (rd.errorML) onRowChange(idx, 'errorML', null);
            }
          } catch {}
          setIaProgress(prev => ({ ...prev, done: prev.done + 1 }));
        }));
        if (i + BATCH < validIdxs.length) await new Promise(r => setTimeout(r, 3000));
      }
      setIaAllLoading(false);
      customAlert('Autollenado IA completado!');
    });
  };

  const handleAIAll = () => runAIBulk([...selectedRows]);
  
  const handleAIErrors = () => {
    let errorIdxs = [...selectedRows].filter(idx => (rowData[idx] || {}).errorML);
    if (!errorIdxs.length) {
      errorIdxs = filteredItems.map(i => i.idx).filter(idx => (rowData[idx] || {}).errorML);
    }
    if (!errorIdxs.length) return customAlert('No hay articulos con errores en esta vista.');
    runAIBulk(errorIdxs);
  };

  const handleSyncMemory = async () => {
    customConfirm('ÂSincronizar memoria de cuentas con MercadoLibre? Esto puede tomar un momento.', async () => {
      setIsPublishing(true); setStep(4);
      setActiveTaskName('Sincronizando Memoria ML...'); setPublishResult(null);
      const fd = new FormData(); fd.append('cuenta', cuentasActivas.includes('TODAS') ? 'TODAS' : cuentasActivas.join(','));
      const iv = startProgressTracking();
      try {
        const d = await fetch('/api/sincronizar-memoria-ml', { method: 'POST', body: fd }).then(r => r.json());
        setPublishResult(d);
        customAlert('Memoria sincronizada exitosamente.');
      } catch { customAlert('Error sincronizando memoria'); }
      finally { setIsPublishing(false); clearInterval(iv); }
    });
  };

  const handleFileChange = async (e) => {
    const f = e.target.files[0]; if (!f) return;
    setFile(f); setLoadingFile(true); setHojas([]); setColumnas([]); setRawPreview([]);
    const fd = new FormData(); fd.append('file', f);
    try {
      const dHojas = await fetch('/api/hojas-excel', { method: 'POST', body: fd }).then(r => r.json());
      setHojas(dHojas.hojas || []);
      const hojaDefault = dHojas.hojas?.[0] || 'TODAS';
      setHojaActiva(hojaDefault);
      fd.append('hoja', hojaDefault);
      const dCols = await fetch('/api/columnas-excel', { method: 'POST', body: fd }).then(r => r.json());
      setColumnas(dCols || []);
      const dRaw = await fetch('/api/vista-previa-excel', { method: 'POST', body: fd }).then(r => r.json());
      setRawPreview(dRaw.vistas || []);
      const findCol = (kw) => (dCols || []).find(c => kw.some(k => c.toLowerCase().includes(k))) || '';
      setMapping({
        col_tit: findCol(['titulo', 'nombre', 'title', 'descrip']),
        col_sku: findCol(['sku', 'codigo', 'cod']),
        col_mod: findCol(['modelo', 'model']),
        col_pre: findCol(['precio', 'price', 'costo']),
        col_stk: findCol(['stock', 'cant', 'inventario']),
      });
      setStep(2);
    } catch { customAlert('Error leyendo archivo'); }
    finally { setLoadingFile(false); }
  };

  const loadColumnsForSheet = async (hojaName) => {
    if (!file) return;
    setHojaActiva(hojaName);
    const fd = new FormData(); fd.append('file', file); fd.append('hoja', hojaName);
    try {
      const d = await fetch('/api/columnas-excel', { method: 'POST', body: fd }).then(r => r.json());
      setColumnas(d || []);
    } catch {}
  };

  const handlePreview = async () => {
    customConfirm('ÂEstas seguro de generar la vista previa del lote?', async () => {
    setShowCategoryModal(false); setLoadingPreview(true); setPreviewData(null); setRowData({});
    
    setIsPublishing(true); setStep(4);
    setActiveTaskName('Generando Vista Previa...'); setPublishResult(null);

    const fd = new FormData();
    fd.append('file', file); fd.append('cuenta', cuentasActivas.includes('TODAS') ? 'TODAS' : cuentasActivas.join(',')); fd.append('hoja', hojaActiva);
    fd.append('inicio', filterMode === 'range' ? config.inicio : 1);
    fd.append('fin',    filterMode === 'range' ? config.fin    : 99999);
    fd.append('cantidad_limite', filterMode === 'limit' ? config.cantidad_limite : 0);
    fd.append('categoria_filtro', config.categoria_filtro);
    fd.append('filtrar_duplicados', config.filtrar_duplicados);
    fd.append('verificar_todas', config.verificar_todas);
    fd.append('col_tit', mapping.col_tit); fd.append('col_sku', mapping.col_sku);
    fd.append('col_mod', mapping.col_mod); fd.append('col_pre', mapping.col_pre);
    fd.append('col_stk', mapping.col_stk);

    const iv = startProgressTracking();
    try {
      const d = await fetch('/previsualizar', { method: 'POST', body: fd }).then(r => r.json());
      setPreviewData(d);
      
      const initialRowData = {};
      const newSelected = new Set();
      const BLOQUE_SUPERIOR = `SOMOS TIENDA FÍSICA, Empresa Mayorista Líder en el Mercado de la Computación Producto 100% de calidad`;
      const BLOQUE_INFERIOR = `.
Por Favor Verifique la disponibilidad antes de ofertar
Por Favor Verifique la disponibilidad antes de ofertar
Por Favor Verifique la disponibilidad antes de ofertar
**************************************************************************************************
- Emitimos factura LEGAL
- Trabajamos con agentes de retención
- Enviamos a todo el País.
**************************************************************************************************
COMENTARIOS:
- Realice todas las preguntas necesarias Antes de ofertar.
- El equipo de ventas esta a tu disposicion para responder tus consultas.
- Te invitamos a que solo ofertes cuando estes seguro de realizar la compra.
- La disponibilidad y precio del producto publicado solo se garantiza por un lapso de 24hrs luego de haber solicitado la compra.
- Si presentas algun inconveniente durante el proceso de compras estaremos a tu completa disposicion para atenderte y solventar la situacion. Deseamos que tu compra con nosotros siempre genere una calificacion positiva.
****************************************************************************************************
HORARIO DE TRABAJO
****************************************************
De Lunes A Viernes
De 8:30am A 5:30pm`;

      (d.productos || []).forEach((p, i) => {
        const itemRowData = { ...rowData[i] };
        if (p.ImagenLocal) {
          itemRowData.localImages = [p.ImagenLocal];
        }
        
        // Auto-fill template
        let titulo = p.Titulo || 'Sin Título';
        let descFinal = `${BLOQUE_SUPERIOR}\n\n${titulo}\n${titulo}\n${titulo}\n\n`;
        const custom = p.DescripcionCustom || '';
        if (custom && custom.trim().length > 0) {
            descFinal += `${custom}\n\n`;
        }
        descFinal += `========================================\nCARACTERISTICAS TECNICAS\n========================================\n\n`;
        descFinal += `========================================\n\n${BLOQUE_INFERIOR}`;
        
        itemRowData.descripcion = descFinal;
        initialRowData[i] = itemRowData;

        // by default select if not 'Ya publicado'
        if (!(p.EstadoPublicacion || p["Estado Publicacion"] || "").includes("Ya publicado")) {
           newSelected.add(i);
        }
      });
      setRowData(initialRowData);
      setSelectedRows(newSelected);
      setStep(3);
      setCurrentPage(1);
      // Auto sync images after slight delay
      setTimeout(() => handleRefreshImages(true, Array.from(newSelected), d), 500);
    } catch { 
      customAlert('Error generando vista previa'); 
      setStep(2); 
    }
    finally { 
      setLoadingPreview(false); 
      setIsPublishing(false); 
      clearInterval(iv); 
    }
    });
  };

  const handlePublish = async () => {
    if (!previewData?.productos?.length) return;
    customConfirm(`Publicar ${selectedRows.size} articulos en MercadoLibre?`, async () => {
    setIsPublishing(true); setStep(4);
    setActiveTaskName('Publicando Lote en MercadoLibre...'); setPublishResult(null);
    const fileToBase64 = (file) => new Promise((resolve) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => resolve(null);
    });

    const productosFinales = await Promise.all(Array.from(selectedRows).map(async originalIdx => {
        const p = previewData.productos[originalIdx];
        const rd = rowData[originalIdx] || {};

        let ImagenesB64 = [];
        if (rd.localImages) {
           for (let i = 0; i < rd.localImages.length; i++) {
               const img = rd.localImages[i];
               if (img.startsWith('data:image')) {
                   ImagenesB64.push(img);
               } else if (rd.imageFiles && rd.imageFiles[i]) {
                   const b64 = await fileToBase64(rd.imageFiles[i]);
                   if (b64) ImagenesB64.push(b64);
               }
           }
        }

        return {
          ...p,
          idx:         originalIdx,
          Categoria_ID: rd.cat_id ?? p.Categoria_ID,
          Titulo:      rd.titulo      ?? p.Titulo,
          Precio:      rd.precio      ?? p.Precio,
          Stock:       rd.stock       ?? p.Stock,
          Exposicion:  rd.exposicion  ?? 'bronze',
          Envio:       rd.envio       ?? 'me2_free',
          DescripcionCustom: rd.descripcion ?? p.DescripcionCustom ?? '',
          AtributosDinamicos: rd.aiAtributos ?? p.AtributosDinamicos ?? {},
          ImagenesB64: ImagenesB64.length > 0 ? ImagenesB64 : (p.ImagenesB64 || [])
        };
      }));
    const iv = startProgressTracking();
    try {
      const d = await fetch(`/publicar-lote?cuenta=${encodeURIComponent(cuentasActivas.includes('TODAS') ? 'TODAS' : cuentasActivas.join(','))}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(productosFinales),
      }).then(r => r.json());
      setPublishResult(d);
    } catch { customAlert('Error publicando lote'); }
    finally { setIsPublishing(false); clearInterval(iv); }
    });
  };

  const handleReturnToStep3 = () => {
    if (publishResult && publishResult.errores_idx) {
      // Remover los que se publicaron con exito de selectedRows
      const failedIndices = Object.keys(publishResult.errores_idx).map(Number);
      const newSelected = new Set(failedIndices);
      
      // Update previewData to mark successful ones so they are hidden
      setPreviewData(prev => {
        if (!prev || !prev.productos) return prev;
        const newProductos = [...prev.productos];
        const successfulIndices = Array.from(selectedRows).filter(idx => !failedIndices.includes(Number(idx)));
        successfulIndices.forEach(idx => {
           newProductos[idx] = { ...newProductos[idx], publishedSuccessfully: true };
        });
        return { ...prev, productos: newProductos };
      });

      setSelectedRows(newSelected);
      
      // Inject error messages into rowData so they can be sent to AI next time
      const newRowData = { ...rowData };
      failedIndices.forEach(idx => {
         newRowData[idx] = { ...newRowData[idx], errorML: publishResult.errores_idx[idx] };
      });
      setRowData(newRowData);
    }
    setPublishResult(null);
    setStep(3);
  };

  // Computed helpers
  const activeRawSheet = rawPreview.find(s => s.nombre === hojaActiva) || rawPreview[0];
  const rawRows   = activeRawSheet?.filas || [];
  const rawHeaders = rawRows[0] || [];
  const rawDataRows = rawRows.slice(1, 11);

  const filteredItems = (previewData?.productos || []).map((p, idx) => ({ p, idx })).filter(item => {
    if (discardedItems.has(item.idx)) return false;
    if (item.p.publishedSuccessfully) return false;
    if (!showPublished && item.p.EstadoCuentas) {
       if (cuentasActivas.includes('TODAS')) {
           const allExist = Object.values(item.p.EstadoCuentas).every(s => s === 'EXISTE');
           if (allExist) return false;
       } else {
           const selectedNames = cuentas.filter(c => cuentasActivas.includes(c.archivo)).map(c => c.nombre);
           if (selectedNames.length > 0) {
              const allExistInSelected = selectedNames.every(name => item.p.EstadoCuentas[name] === 'EXISTE');
              if (allExistInSelected) return false;
           }
       }
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
  })();

  const toggleCategory = (items) => {
    const allSel = items.every(it => selectedRows.has(it.idx));
    const next = new Set(selectedRows);
    items.forEach(it => allSel ? next.delete(it.idx) : next.add(it.idx));
    setSelectedRows(next);
  };

  const toggleOne = (i) => {
    const next = new Set(selectedRows);
    next.has(i) ? next.delete(i) : next.add(i);
    setSelectedRows(next);
  };

  // â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
  //  RENDER
  // â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
  return (
    <div className="flex h-full bg-slate-50 flex-col overflow-hidden relative" style={{ zoom: zoomLevel / 100 }}>

      {/* Category Modal */}
      {showCategoryModal && (
        <div className="fixed inset-0 bg-slate-900/50 z-[999] flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl overflow-hidden flex flex-col">
            <div className="p-5 border-b border-slate-200">
              <h3 className="font-black text-xl text-slate-800 flex items-center gap-2">
                🏷️ Selecciona Categoría Filtro
              </h3>
            </div>
            <div className="p-6 bg-slate-50 flex-1 overflow-y-auto">
              <p className="text-slate-500 mb-6 text-sm">Filtra tu rango de filas por un rubro oficial para mayor precisión, o elige cargar absolutamente todo el inventario:</p>
              
              <button 
                onClick={() => setConfig(c => ({ ...c, categoria_filtro: 'TODAS' }))}
                className={`w-full py-4 px-6 rounded-lg font-bold text-sm text-left border-2 flex items-center mb-4 transition-all ${config.categoria_filtro === 'TODAS' ? 'border-[#0284c7] bg-[#e0f2fe] text-[#0284c7]' : 'border-slate-300 bg-white hover:border-[#0284c7] hover:text-[#0284c7]'}`}
              >
                🌐 CARGAR TODO EL INVENTARIO <span className="font-normal opacity-70 ml-2">(Sin filtro de categoría)</span>
              </button>

              <div className="mb-4">
                <input 
                  type="text" 
                  value={globalCatSearch.query}
                  onChange={(e) => setGlobalCatSearch({ ...globalCatSearch, query: e.target.value })}
                  placeholder="🔍 Buscar categoría por título (Ej: Laptops)... Presiona Enter"
                  className="w-full p-3 border border-slate-300 rounded focus:border-[#0284c7] outline-none font-medium"
                  onKeyDown={async (e) => {
                    if (e.key === 'Enter' && globalCatSearch.query.trim()) {
                      setGlobalCatSearch(prev => ({ ...prev, loading: true, results: [] }));
                      try {
                        const res = await fetch(`/api/buscar-categorias-mlv?q=${encodeURIComponent(globalCatSearch.query.trim())}`);
                        if (res.ok) {
                          const data = await res.json();
                          setGlobalCatSearch(prev => ({ ...prev, loading: false, results: data }));
                        } else {
                          setGlobalCatSearch(prev => ({ ...prev, loading: false }));
                        }
                      } catch {
                        setGlobalCatSearch(prev => ({ ...prev, loading: false }));
                      }
                    }
                  }}
                />
              </div>

              {globalCatSearch.loading ? (
                <div className="text-center py-4 text-slate-500 font-bold"><Loader2 size={24} className="animate-spin mx-auto mb-2"/> Buscando categorías...</div>
              ) : globalCatSearch.results.length > 0 ? (
                <div className="grid grid-cols-2 gap-4">
                  {globalCatSearch.results.map(cat => (
                    <button
                      key={cat.id}
                      onClick={() => setConfig(c => ({ ...c, categoria_filtro: cat.id }))}
                      className={`py-3 px-4 rounded-lg font-bold text-sm text-left border-2 flex items-center transition-all ${config.categoria_filtro === cat.id ? 'border-[#0284c7] bg-[#e0f2fe] text-[#0284c7]' : 'border-slate-200 bg-white hover:border-[#0284c7] hover:text-[#0284c7]'}`}
                    >
                      🔍 {cat.name} <span className="font-normal opacity-60 ml-2">({cat.id})</span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  {categorias.map(cat => (
                    <button
                      key={cat.id}
                      onClick={() => setConfig(c => ({ ...c, categoria_filtro: cat.id }))}
                      className={`py-4 px-4 rounded-lg font-bold text-sm text-left border-2 flex items-center transition-all ${config.categoria_filtro === cat.id ? 'border-[#0284c7] bg-[#e0f2fe] text-[#0284c7]' : 'border-slate-200 bg-white hover:border-[#0284c7] hover:text-[#0284c7]'}`}
                    >
                      📌 {cat.name} <span className="font-normal opacity-60 ml-2">({cat.id})</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="p-5 border-t border-slate-200 bg-white flex justify-center gap-4">
              <button onClick={() => setShowCategoryModal(false)} className="px-6 py-2.5 bg-slate-500 hover:bg-slate-600 text-white font-bold rounded-lg shadow-sm">
                Cancelar
              </button>
              <button onClick={() => { setShowCategoryModal(false); }} className="px-6 py-2.5 bg-[#16a34a] hover:bg-[#15803d] text-white font-bold rounded-lg shadow-sm flex items-center gap-2">
                🚀 Confirmar y Analizar Inventario
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manual Category Search Modal */}
      {manualCatSearch.isOpen && (
        <div className="fixed inset-0 bg-slate-900/60 z-[999] flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between">
              <h3 className="font-black text-lg text-slate-800 flex items-center gap-2">
                ✏️ Cambiar Categoría
              </h3>
              <button onClick={() => setManualCatSearch({ ...manualCatSearch, isOpen: false })} className="text-slate-400 hover:text-slate-600">
                x
              </button>
            </div>
            <div className="p-4 bg-slate-50 border-b border-slate-200">
              <div className="flex gap-2">
                <input 
                  type="text" 
                  value={manualCatSearch.query}
                  onChange={(e) => setManualCatSearch({ ...manualCatSearch, query: e.target.value })}
                  placeholder="Ej: Laptops, Discos Duros, MLV1234"
                  className="flex-1 p-2 border border-slate-300 rounded focus:border-[#0284c7] outline-none"
                  onKeyDown={async (e) => {
                    if (e.key === 'Enter' && manualCatSearch.query.trim()) {
                      setManualCatSearch(prev => ({ ...prev, loading: true, results: [] }));
                      try {
                        const res = await fetch(`/api/buscar-categorias-mlv?q=${encodeURIComponent(manualCatSearch.query.trim())}`);
                        const data = await res.json();
                        setManualCatSearch(prev => ({ ...prev, loading: false, results: data }));
                      } catch {
                        setManualCatSearch(prev => ({ ...prev, loading: false }));
                      }
                    }
                  }}
                />
                <button 
                  onClick={async () => {
                    if (!manualCatSearch.query.trim()) return;
                    setManualCatSearch(prev => ({ ...prev, loading: true, results: [] }));
                    try {
                      const res = await fetch(`/api/buscar-categorias-mlv?q=${encodeURIComponent(manualCatSearch.query.trim())}`);
                      const data = await res.json();
                      setManualCatSearch(prev => ({ ...prev, loading: false, results: data }));
                    } catch {
                      setManualCatSearch(prev => ({ ...prev, loading: false }));
                    }
                  }}
                  className="px-4 py-2 bg-[#0284c7] hover:bg-[#0369a1] text-white rounded font-bold"
                >
                  Buscar
                </button>
              </div>
            </div>
            <div className="flex-1 max-h-[50vh] overflow-y-auto bg-white p-2">
              {manualCatSearch.loading ? (
                <div className="p-4 text-center text-slate-500 font-bold">Buscando...</div>
              ) : manualCatSearch.results.length === 0 && manualCatSearch.query ? (
                <div className="p-4 text-center text-slate-500 text-sm">Presiona Enter o Buscar. Si no aparece, prueba otras palabras.</div>
              ) : (
                <div className="flex flex-col">
                  {manualCatSearch.results.map((c) => (
                    <button 
                      key={c.id}
                      onClick={() => {
                        onRowChange(manualCatSearch.idx, 'cat_id', c.id);
                        onRowChange(manualCatSearch.idx, 'cat_nombre', `Cat Manual: ${c.name}`);
                          const rData = rowData[manualCatSearch.idx] || {};
                          if (rData.errorML && rData.errorML.includes('category_id')) {
                              onRowChange(manualCatSearch.idx, 'errorML', null);
                          }
                        setManualCatSearch({ isOpen: false, idx: null, query: '', results: [], loading: false });
                      }}
                      className="p-3 text-left hover:bg-slate-50 border-b border-slate-100 last:border-0 flex items-center justify-between group"
                    >
                      <span className="text-sm font-medium text-slate-700">{c.name}</span>
                      <span className="text-xs font-mono text-slate-400 group-hover:text-[#0284c7]">{c.id}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Header Steps */}
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center shrink-0">
        <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
          <FileSpreadsheet className="text-emerald-600"/> Sincronizador Excel a MercadoLibre
          <div className="flex items-center gap-2 ml-4 bg-slate-100 rounded-lg p-1">
            <button onClick={() => setZoomLevel(z => Math.max(50, z - 10))} className="p-1 hover:bg-slate-200 rounded text-slate-600" title="Disminuir tamao">-</button>
            <span className="text-xs font-mono w-10 text-center text-slate-500">{zoomLevel}%</span>
            <button onClick={() => setZoomLevel(z => Math.min(200, z + 10))} className="p-1 hover:bg-slate-200 rounded text-slate-600" title="Aumentar tamao">+</button>
          </div>
        </h1>
        <div className="flex items-center gap-4 text-sm font-medium">
          {[['1','Archivo'],['2','Configuracion'],['3','Previsualizacion']].map(([n, label], i) => (
            <React.Fragment key={n}>
              {i > 0 && <ArrowRight size={14} className="text-slate-300"/>}
              <div className={`flex items-center gap-2 ${step >= +n ? 'text-emerald-600' : 'text-slate-400'}`}>
                <span className={`w-6 h-6 flex items-center justify-center rounded-full text-xs text-white ${step >= +n ? 'bg-emerald-600' : 'bg-slate-300'}`}>{n}</span>
                {label}
              </div>
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className={`flex-1 overflow-y-auto ${step === 3 ? 'p-0 bg-white' : 'p-6'}`}>
        <div className={`space-y-4 ${step === 3 ? 'w-full' : 'max-w-6xl mx-auto'}`}>

          {/* STEPS 1 & 2 */}
          {step <= 2 && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <div className="flex justify-between items-center border-b pb-4 mb-4">
                <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                  <Upload size={18}/> Cargar Archivo y Cuenta
                </h2>
                <button onClick={handleSyncMemory} className="flex items-center gap-2 bg-blue-50 text-blue-700 hover:bg-blue-100 px-4 py-2 rounded-lg text-sm font-semibold transition-colors">
                  <Database size={16}/> Sincronizar Memoria ML
                </button>
              </div>

              <div className="grid grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Cuenta de MercadoLibre</label>
                  <div className="w-full border border-slate-300 rounded-lg p-2 max-h-32 overflow-y-auto bg-white flex flex-col gap-1">
                    <label className="flex items-center gap-2 text-sm cursor-pointer hover:bg-slate-50 p-1 rounded">
                      <input type="checkbox" checked={cuentasActivas.includes('TODAS')} onChange={(e) => {
                         if (e.target.checked) setCuentasActivas(['TODAS']);
                         else setCuentasActivas([]);
                      }} className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500" /> MULTICUENTA (Todas)
                    </label>
                    {cuentas.map(c => (
                      <label key={c.archivo} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-slate-50 p-1 rounded">
                        <input type="checkbox" checked={cuentasActivas.includes(c.archivo)} onChange={(e) => {
                          let newArr = [...cuentasActivas].filter(x => x !== 'TODAS');
                          if (e.target.checked) newArr.push(c.archivo);
                          else newArr = newArr.filter(x => x !== c.archivo);
                          if (newArr.length === 0) newArr = ['TODAS'];
                          setCuentasActivas(newArr);
                        }} className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500" /> {c.nombre}
                      </label>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Archivo Excel (.xlsx, .csv)</label>
                  <input type="file" accept=".xlsx,.xls,.csv"
                    className="w-full border border-slate-300 rounded-lg px-3 py-1.5 outline-none focus:border-emerald-500 text-sm file:mr-4 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:bg-emerald-50 file:text-emerald-700 cursor-pointer"
                    onChange={handleFileChange} disabled={loadingFile}
                  />
                </div>
              </div>

              {/* Raw Preview */}
              {rawRows.length > 0 && (
                <div className="mt-2 mb-6 border border-slate-200 rounded-lg overflow-hidden">
                  <div className="bg-slate-100 px-4 py-2 text-xs font-semibold text-slate-600 flex items-center gap-2 border-b border-slate-200">
                    <Table size={14}/> Vista previa del Excel - {activeRawSheet?.nombre} (Primeras filas)
                  </div>
                  <div className="overflow-x-auto max-h-[220px]">
                    <table className="w-full text-left text-xs whitespace-nowrap">
                      <thead className="bg-slate-50 text-slate-500 sticky top-0 shadow-sm z-10">
                        <tr>{rawHeaders.map((col, k) => <th key={k} className="px-3 py-2 border-b border-r border-slate-200 font-semibold">{col}</th>)}</tr>
                      </thead>
                      <tbody>
                        {rawDataRows.map((row, i) => (
                          <tr key={i} className="hover:bg-slate-50">
                            {row.map((val, j) => <td key={j} className="px-3 py-1.5 border-b border-r border-slate-100 text-slate-700">{String(val).substring(0, 45)}</td>)}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Step 2 Config */}
              {step === 2 && (
                <div className="mt-8 animate-in fade-in slide-in-from-bottom-4 duration-300">
                  <h2 className="text-lg font-bold text-slate-800 mb-4 border-b pb-2 flex items-center gap-2">
                    <Settings2 size={18}/> Mapeo y Configuraciones
                  </h2>
                  <div className="grid grid-cols-3 gap-6">
                    <div className="col-span-1 space-y-5">
                      <div>
                        <label className="block text-xs font-semibold text-slate-600 mb-1">Hoja de Trabajo</label>
                        <select className="w-full border border-slate-300 rounded px-3 py-2 text-sm bg-white" value={hojaActiva} onChange={e => loadColumnsForSheet(e.target.value)}>
                          <option value="TODAS">Procesar TODAS las Hojas</option>
                          {hojas.map(h => <option key={h} value={h}>{h}</option>)}
                        </select>
                      </div>
                      <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-3">
                        <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 cursor-pointer">
                          <input type="radio" name="filterMode" checked={filterMode === 'range'} onChange={() => setFilterMode('range')} className="text-emerald-600 focus:ring-emerald-500"/>
                          Procesar Rango de Filas
                        </label>
                        <div className={`grid grid-cols-2 gap-2 transition-opacity ${filterMode !== 'range' ? 'opacity-50 pointer-events-none' : ''}`}>
                          <div>
                            <label className="block text-[10px] uppercase font-bold text-slate-500 mb-1">Inicio</label>
                            <input type="number" className="w-full border border-slate-300 rounded px-2 py-1 text-sm bg-white" value={config.inicio} onChange={e => setConfig(c => ({ ...c, inicio: e.target.value }))}/>
                          </div>
                          <div>
                            <label className="block text-[10px] uppercase font-bold text-slate-500 mb-1">Fin</label>
                            <input type="number" className="w-full border border-slate-300 rounded px-2 py-1 text-sm bg-white" value={config.fin} onChange={e => setConfig(c => ({ ...c, fin: e.target.value }))}/>
                          </div>
                        </div>
                        <hr className="border-slate-200"/>
                        <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 cursor-pointer">
                          <input type="radio" name="filterMode" checked={filterMode === 'limit'} onChange={() => setFilterMode('limit')} className="text-emerald-600 focus:ring-emerald-500"/>
                          Procesar por Limite
                        </label>
                        <div className={`transition-opacity ${filterMode !== 'limit' ? 'opacity-50 pointer-events-none' : ''}`}>
                          <label className="block text-[10px] uppercase font-bold text-slate-500 mb-1">Cantidad Maxima</label>
                          <input type="number" className="w-full border border-slate-300 rounded px-2 py-1 text-sm bg-white" value={config.cantidad_limite} onChange={e => setConfig(c => ({ ...c, cantidad_limite: e.target.value }))}/>
                        </div>
                      </div>
                      <div className="space-y-2 pt-2">
                        <label className="flex items-center gap-2 text-sm cursor-pointer hover:text-emerald-700">
                          <input type="checkbox" checked={config.filtrar_duplicados === 'true'} onChange={e => setConfig(c => ({ ...c, filtrar_duplicados: e.target.checked ? 'true' : 'false' }))} className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"/>
                          Omitir articulos ya publicados en ML (Recomendado)
                        </label>
                        <label className={`flex items-center gap-2 text-sm cursor-pointer hover:text-emerald-700 ${cuentasActivas.includes('TODAS') ? 'opacity-50 pointer-events-none' : ''}`}>
                          <input type="checkbox" checked={config.verificar_todas === 'true'} onChange={e => setConfig(c => ({ ...c, verificar_todas: e.target.checked ? 'true' : 'false' }))} className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"/>
                          Solo omitir si existe en TODAS
                        </label>
                      </div>
                    </div>
                    <div className="col-span-2 bg-slate-50 p-5 rounded-xl border border-slate-200 shadow-inner">
                      <h3 className="font-semibold text-slate-700 mb-4 text-sm flex items-center gap-2"><Table size={16}/> Mapeo de Columnas del Excel</h3>
                      <div className="grid grid-cols-2 gap-4">
                        {Object.keys(mapping).map(key => {
                          const labels = { col_tit: 'Titulo del Producto *', col_sku: 'Codigo / SKU', col_mod: 'Modelo', col_pre: 'Precio *', col_stk: 'Stock / Cantidad *' };
                          return (
                            <div key={key}>
                              <label className="block text-xs font-semibold text-slate-600 mb-1">{labels[key]}</label>
                              <select className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm outline-none focus:border-emerald-500 bg-white"
                                value={mapping[key]} onChange={e => setMapping(m => ({ ...m, [key]: e.target.value }))}>
                                <option value="">-- No Usar --</option>
                                {columnas.map(c => <option key={c} value={c}>{c}</option>)}
                              </select>
                            </div>
                          );
                        })}
                      </div>

                      <div className="border-t border-slate-200 mt-6 pt-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <label className="block text-xs font-semibold text-slate-600 mb-1">Filtrar por Categoria en MercadoLibre</label>
                            <span className="text-sm font-bold text-slate-800">{config.categoria_filtro === 'TODAS' ? 'CARGAR TODO EL INVENTARIO' : (categorias.find(c => c.id === config.categoria_filtro)?.name || config.categoria_filtro)}</span>
                          </div>
                          <button onClick={() => setShowCategoryModal(true)} className="bg-slate-200 hover:bg-slate-300 text-slate-700 px-4 py-2 rounded font-bold text-xs">
                            Cambiar Categoría
                          </button>
                        </div>
                      </div>

                      <div className="mt-8 flex justify-end">
                        <button
                          onClick={handlePreview}
                          disabled={loadingPreview || !mapping.col_tit}
                          className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white px-6 py-2 rounded-lg font-bold flex items-center gap-2 shadow transition-all"
                        >
                          {loadingPreview ? <Loader2 className="animate-spin" size={18}/> : <Eye size={18}/>}
                          Generar Previsualizacion
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 3: Full-featured Preview */}
          {step === 3 && previewData && (
            <div className="animate-in fade-in zoom-in-95 duration-300 space-y-3">

              {/* Stats Bar */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <button onClick={() => setStep(2)} className="text-slate-400 hover:text-slate-700 text-sm font-medium flex items-center gap-1 transition-colors">
                    &larr; Volver
                  </button>
                  <span className="text-slate-300">|</span>
                  <h2 className="font-bold text-slate-800 text-base">Vista Previa del Lote</h2>
                </div>
                <div className="flex gap-2 text-sm font-medium flex-wrap">
                  <span className="text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-full">{previewData.total_aprobados} Aprobados</span>
                  <span className="text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1 rounded-full">{previewData.total_omitidos} Omitidos</span>
                  <span className="text-blue-700 bg-blue-50 border border-blue-200 px-3 py-1 rounded-full">{previewData.total_leidos} Leidos</span>
                  <span className="text-slate-600 bg-slate-100 border border-slate-200 px-3 py-1 rounded-full">{selectedRows.size} Seleccionados</span>
                  {previewData.archivo_reporte && (
                    <a href={`/api/descargar-reporte/${previewData.archivo_reporte}`} target="_blank" rel="noreferrer" className="bg-green-600 hover:bg-green-700 text-white px-4 py-1 rounded-full text-sm font-bold shadow-sm transition-colors flex items-center gap-1.5 ml-2">
                      <FileSpreadsheet size={16}/> Reporte Excel
                    </a>
                  )}
                </div>
              </div>

              {/* Acciones Masivas Toolbar */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-3 flex flex-wrap items-center gap-2">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wide mr-1">Acciones Masivas:</span>
                <button onClick={toggleCurrentPage} className="text-xs px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold transition-colors">
                  Seleccionar Pág. Actual
                </button>
                <button onClick={toggleAll} className="text-xs px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold transition-colors">
                  {selectedRows.size === filteredItems.length ? 'Deseleccionar Todo' : 'Seleccionar Todo'}
                </button>
                <div className="flex items-center gap-1 ml-2 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1">
                  <span className="text-[10px] text-slate-500 font-bold uppercase">Rango:</span>
                  <input type="number" value={rangeStart} onChange={e => setRangeStart(Number(e.target.value))} className="w-12 text-xs p-1 border border-slate-300 rounded" min="1" />
                  <span className="text-xs text-slate-400">-</span>
                  <input type="number" value={rangeEnd} onChange={e => setRangeEnd(Number(e.target.value))} className="w-12 text-xs p-1 border border-slate-300 rounded" min="1" />
                  <button onClick={selectRange} className="text-xs bg-emerald-100 hover:bg-emerald-200 text-emerald-700 px-2 py-1 rounded font-bold ml-1">Aplicar</button>
                </div>
                <span className="text-slate-200">|</span>
                <select value={bulkExposicion} onChange={e => setBulkExposicion(e.target.value)}
                  className="text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white focus:outline-none font-medium">
                  {EXPOSURE_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <button onClick={applyBulkExposicion} className="text-xs px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-700 text-white font-semibold transition-colors flex items-center gap-1">
                  <Star size={11}/> Aplicar Exposicion
                </button>
                <span className="text-slate-200">|</span>
                <select value={bulkEnvio} onChange={e => setBulkEnvio(e.target.value)}
                  className="text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white focus:outline-none font-medium">
                  {SHIPPING_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <button onClick={applyBulkEnvio} className="text-xs px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-700 text-white font-semibold transition-colors flex items-center gap-1">
                  <Zap size={11}/> Aplicar Envio
                </button>
                <span className="text-slate-200">|</span>
                <button onClick={handleRefreshImages} className="text-xs px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold transition-colors flex items-center gap-1">
                  <Camera size={11}/> Refrescar Fotos Locales
                </button>
                <div className="flex gap-2 ml-auto">
                  <button onClick={handleAIErrors} disabled={iaAllLoading}
                    className="text-xs px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 disabled:opacity-60 text-white font-semibold transition-colors flex items-center gap-1 shadow-sm">
                    {iaAllLoading
                      ? <><Loader2 size={12} className="animate-spin"/> {iaProgress.done}/{iaProgress.total}</>
                      : <><Bot size={12}/> Corregir Errores</>}
                  </button>
                  <button onClick={handleAIAll} disabled={iaAllLoading}
                    className="text-xs px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-semibold transition-colors flex items-center gap-1 shadow-sm">
                    {iaAllLoading
                      ? <><Loader2 size={12} className="animate-spin"/> {iaProgress.done}/{iaProgress.total}</>
                      : <><Bot size={12}/> Generar Fichas (IA)</>}
                  </button>
                </div>
              </div>

              {/* Toolbar Filtros / Paginacion */}
              <div className="flex flex-wrap items-center justify-between gap-4 px-4 py-3 bg-white rounded-xl border border-slate-200 shadow-sm">
                <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 cursor-pointer">
                  <input type="checkbox" checked={showPublished} onChange={e => setShowPublished(e.target.checked)} className="rounded text-emerald-600 focus:ring-emerald-500 w-4 h-4" />
                  Mostrar articulos ya publicados
                </label>
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-semibold text-slate-600">Mostrar:</span>
                  <select value={itemsPerPage} onChange={e => {setItemsPerPage(Number(e.target.value)); setCurrentPage(1);}} className="border border-slate-300 rounded-lg px-2 py-1 bg-white">
                    <option value={10}>10 por pagina</option>
                    <option value={50}>50 por pagina</option>
                    <option value={100}>100 por pagina</option>
                    <option value={500}>500 por pagina</option>
                  </select>
                </div>
              </div>

              {/* Vista Tabs + Table */}
              <div className="bg-transparent shadow-none">
                <div className="flex items-center gap-1 px-4 pt-3 mb-2">
                  <button onClick={() => setViewMode('categorias')}
                    className={`px-4 py-2 text-sm font-semibold rounded-t-lg transition-colors flex items-center gap-1.5 ${viewMode === 'categorias' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-slate-700 bg-white border border-b-0'}`}>
                    <LayoutGrid size={14}/> Agrupado por Categorias
                  </button>
                  <button onClick={() => setViewMode('lineal')}
                    className={`px-4 py-2 text-sm font-semibold rounded-t-lg transition-colors flex items-center gap-1.5 ${viewMode === 'lineal' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-slate-700 bg-white border border-b-0'}`}>
                    <Rows3 size={14}/> Lineal (Orden Excel)
                  </button>
                </div>

                <div className="w-full bg-white border-y border-slate-200 overflow-x-auto">
                  <div className="min-w-[1200px] p-4">
                    {/* ENCABEZADO DE TABLA (Diseño Original) */}
                    <div className="flex bg-[#0f172a] text-white text-[10px] font-bold uppercase tracking-wider p-3 rounded-t-lg items-center gap-4 mb-2">
                      <div className="w-4 shrink-0 flex justify-center"><input type="checkbox" checked={paginatedItems.length > 0 && paginatedItems.every(i => selectedRows.has(i.idx))} onChange={toggleCurrentPage} className="rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500 w-3 h-3" title="Seleccionar página actual" /></div>
                      <div className="flex-1 min-w-[280px]">TÍTULO, CATEGORÍA & ESTADO POR CUENTA</div>
                      <div className="w-24 shrink-0 text-center">PRECIO $</div>
                      <div className="w-16 shrink-0 text-center">STOCK</div>
                      <div className="w-40 shrink-0 text-center">EXPOSICIÓN & ENVÍO</div>
                      <div className="w-64 shrink-0 text-center">FICHA TÉCNICA & DESCRIPCIÓN FINAL</div>
                      <div className="w-48 shrink-0 text-center">GESTOR DE FOTOS LOCAL</div>
                    </div>

                    {!previewData.productos || previewData.productos.length === 0 ? (
                      <div className="py-12 text-center text-slate-400">
                        <FileSpreadsheet size={40} className="mx-auto mb-3 opacity-40"/>
                        <p className="font-medium">No hay productos aprobados. Revisa los filtros de configuracion.</p>
                      </div>
                    ) : filteredItems.length === 0 ? (
                      <div className="py-12 text-center text-emerald-600">
                        <CheckCircle2 size={40} className="mx-auto mb-3 opacity-80"/>
                        <p className="font-medium text-lg">Todos los articulos de este lote ya estan publicados.</p>
                        <p className="text-sm mt-1 opacity-80">Marca "Mostrar articulos ya publicados" arriba si deseas verlos.</p>
                      </div>
                    ) : viewMode === 'lineal' ? (
                      <div className="space-y-0 border border-t-0 border-slate-200 rounded-b-lg">
                        {paginatedItems.map(({ p, idx }) => (
                          <ProductRow key={idx} p={p} idx={idx} selected={selectedRows.has(idx)} onToggle={toggleOne} rowData={rowData[idx] || {}} onRowChange={onRowChange} onAIFill={onAIFill} onOpenCatSearch={(i) => setManualCatSearch({ isOpen: true, idx: i, query: '', results: [], loading: false })} onDiscard={(i) => { setDiscardedItems(prev => new Set(prev).add(i)); setSelectedRows(prev => { const n = new Set(prev); n.delete(i); return n; }); }} />
                        ))}
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {Object.entries(groupedByCategory).map(([catName, items]) => {
                          const allSel = items.every(it => selectedRows.has(it.idx));
                          return (
                            <div key={catName} className="mb-4 bg-white border border-slate-200 rounded-lg shadow-sm">
                              <div className="flex items-center gap-3 px-3 py-2.5 bg-slate-100 rounded-t-lg border-b border-slate-200">
                                <button onClick={() => {
                                  setFoldedCategories(prev => {
                                    const next = new Set(prev);
                                    if (next.has(catName)) next.delete(catName);
                                    else next.add(catName);
                                    return next;
                                  });
                                }} className="p-1 hover:bg-slate-200 rounded text-slate-500 transition-colors">
                                  {foldedCategories.has(catName) ? <ChevronDown size={18}/> : <ChevronUp size={18}/>}
                                </button>
                                <input type="checkbox" checked={allSel} onChange={() => toggleCategory(items)}
                                className="rounded border-slate-400 text-blue-600 focus:ring-blue-500 cursor-pointer w-4 h-4"/>
                                <span className="font-bold text-slate-800 text-sm flex-1 cursor-pointer" onClick={() => {
                                  setFoldedCategories(prev => {
                                    const next = new Set(prev);
                                    if (next.has(catName)) next.delete(catName);
                                    else next.add(catName);
                                    return next;
                                  });
                                }}>{catName}</span>
                                <span className="text-xs text-slate-500 bg-white border border-slate-200 px-2 py-0.5 rounded-full">{items.length} articulos</span>
                                <button onClick={() => {
                                  customConfirm(`¿Descartar los ${items.length} artículos de la categoría "${catName}" de esta vista?`, () => {
                                    setDiscardedItems(prev => {
                                      const next = new Set(prev);
                                      items.forEach(it => next.add(it.idx));
                                      return next;
                                    });
                                    setSelectedRows(prev => {
                                      const next = new Set(prev);
                                      items.forEach(it => next.delete(it.idx));
                                      return next;
                                    });
                                  });
                                }} className="text-xs bg-red-50 text-red-600 hover:bg-red-100 px-2 py-1 rounded font-bold border border-red-200 transition-colors flex items-center gap-1" title="Descartar categoría entera">
                                  &times; Descartar Categoría
                                </button>
                              </div>
                              {!foldedCategories.has(catName) && (
                                <div className="divide-y divide-slate-100">
                                  {items.map(({ p, idx }) => (
                                    <ProductRow key={idx} p={p} idx={idx} selected={selectedRows.has(idx)} onToggle={toggleOne} rowData={rowData[idx] || {}} onRowChange={onRowChange} onAIFill={onAIFill} onOpenCatSearch={(i) => setManualCatSearch({ isOpen: true, idx: i, query: '', results: [], loading: false })} onDiscard={(i) => { setDiscardedItems(prev => new Set(prev).add(i)); setSelectedRows(prev => { const n = new Set(prev); n.delete(i); return n; }); }} />
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                {totalPages > 1 && (
                  <div className="border-t border-slate-100 p-4 bg-slate-50 flex items-center justify-between rounded-b-xl min-w-[1200px]">
                    <button disabled={currentPage === 1} onClick={() => setCurrentPage(p => p - 1)} className="px-4 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 disabled:opacity-50 text-slate-700 font-semibold text-sm shadow-sm transition-all">&larr; Anterior</button>
                    <span className="text-sm font-semibold text-slate-600">Pagina {currentPage} de {totalPages}</span>
                    <button disabled={currentPage === totalPages} onClick={() => setCurrentPage(p => p + 1)} className="px-4 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 disabled:opacity-50 text-slate-700 font-semibold text-sm shadow-sm transition-all">Siguiente &rarr;</button>
                  </div>
                )}
                </div>
              </div>

              {/* Publish Bar */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex justify-between items-center">
                <div className="text-sm text-slate-500">
                  <span className="font-semibold text-slate-700">{selectedRows.size}</span> productos seleccionados para publicar
                </div>
                <button
                  onClick={handlePublish}
                  disabled={selectedRows.size === 0}
                  className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white px-8 py-2.5 rounded-lg font-bold flex items-center gap-2 shadow-lg hover:shadow-xl transition-all"
                >
                  <Play size={18}/> Publicar {selectedRows.size} Productos Ahora
                </button>
              </div>
            </div>
          )}

          {/* STEP 4: Publishing / Result */}
          {step === 4 && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center animate-in fade-in zoom-in-95 duration-300">
              {isPublishing ? (
                <div className="max-w-md mx-auto space-y-4">
                  <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-6">
                    <Loader2 size={32} className="animate-spin"/>
                  </div>
                  <h2 className="text-xl font-bold text-slate-800">{activeTaskName}</h2>
                  {progress && (
                    <>
                      <div className="text-sm font-medium text-slate-600 h-8">{progress.mensaje}</div>
                      <div className="w-full bg-slate-100 rounded-full h-4 overflow-hidden shadow-inner">
                        <div className="bg-blue-600 h-full transition-all duration-300 ease-out" style={{ width: `${progress.porcentaje}%` }}/>
                      </div>
                      <div className="flex justify-between text-xs text-slate-500 font-mono">
                        <span className="text-emerald-600">{progress.exitos} Exitos</span>
                        <span className="text-red-500">{progress.errores} Errores</span>
                        <span>{progress.porcentaje}%</span>
                      </div>
                    </>
                  )}
                  <p className="text-xs text-slate-400 mt-4">Por favor no cierres esta ventana hasta que el proceso finalice.</p>
                </div>
              ) : publishResult ? (
                <div className="max-w-3xl mx-auto text-left">
                  <div className="text-center mb-6">
                    <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
                      <CheckCircle2 size={32}/>
                    </div>
                    <h2 className="text-xl font-bold text-slate-800">Proceso Finalizado</h2>
                  </div>
                  <div className="bg-slate-900 text-slate-300 rounded-lg border border-slate-800 p-4 mb-6 max-h-[350px] overflow-y-auto text-sm font-mono space-y-1.5 shadow-inner">
                    {(publishResult.detalles || publishResult.logs || ['Proceso terminado exitosamente.']).map((log, i) => {
                      let cls = 'text-slate-300';
                      if (log.includes('Error') || log.includes('error')) cls = 'text-red-400';
                      else if (log.includes('Exito') || log.includes('exito')) cls = 'text-emerald-400';
                      else if (log.includes('Omitido')) cls = 'text-blue-300';
                      return <div key={i} className={cls}>{log}</div>;
                    })}
                  </div>
                  <div className="flex justify-center gap-4">
                    {activeTaskName === 'Sincronizando Memoria ML...' ? (
                      <button onClick={() => { setStep(1); setPublishResult(null); setActiveTaskName(''); }}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-2.5 rounded-lg font-bold transition-colors">
                        Volver
                      </button>
                    ) : (
                      <>
                        {previewData && (
                          <button onClick={handleReturnToStep3}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-2.5 rounded-lg font-bold transition-colors">
                            Volver a la tabla
                          </button>
                        )}
                        {previewData && previewData.archivo_reporte && (
                          <a href={`/api/descargar-reporte/${previewData.archivo_reporte}`} target="_blank" rel="noreferrer" className="bg-green-600 hover:bg-green-700 text-white px-8 py-2.5 rounded-lg font-bold transition-colors flex items-center justify-center gap-2">
                            <FileSpreadsheet size={20}/> Reporte Excel
                          </a>
                        )}
                        <button onClick={() => { 
                          setStep(1); 
                          setFile(null); 
                          setPreviewData(null); 
                          setRowData({}); 
                          setRawPreview([]);
                          setHojas([]);
                          setColumnas([]);
                        }}
                          className="bg-slate-200 hover:bg-slate-300 text-slate-800 px-8 py-2.5 rounded-lg font-bold transition-colors">
                          Finalizar y Volver al inicio
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ) : (
                <div className="max-w-md mx-auto space-y-4">
                  <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-6">
                    <AlertCircle size={32} />
                  </div>
                  <h2 className="text-xl font-bold text-slate-800">Error en la publicación</h2>
                  <p className="text-slate-600">Hubo un problema de conexión con el servidor. Puedes volver a intentarlo.</p>
                  <div className="flex justify-center mt-6">
                    <button onClick={() => setStep(3)} className="bg-slate-200 hover:bg-slate-300 text-slate-800 px-8 py-2.5 rounded-lg font-bold transition-colors">
                      Volver a la tabla
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
      {/* Toasts */}
      <div className="fixed bottom-4 right-4 z-[200] flex flex-col gap-2">
        {toasts.map(t => (
          <div key={t.id} className={`px-4 py-3 rounded-lg shadow-xl text-sm font-bold text-white flex items-center gap-2 transform transition-all duration-300 animate-in slide-in-from-right-8 ${t.type === 'error' ? 'bg-red-600' : 'bg-emerald-600'}`}>
            {t.type === 'error' ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
            {t.message}
          </div>
        ))}
      </div>

      {dialog.isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/60 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-6">
              <h3 className="text-lg font-bold text-slate-800 mb-2">{dialog.type === 'confirm' ? 'Confirmacion' : 'Aviso'}</h3>
              <p className="text-sm text-slate-600 whitespace-pre-wrap">{dialog.message}</p>
            </div>
            <div className="bg-slate-50 px-6 py-4 flex justify-end gap-3 border-t border-slate-100">
              {dialog.type === 'confirm' && (
                <button onClick={dialog.onCancel} className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-200 rounded-lg transition-colors">Cancelar</button>
              )}
              <button onClick={dialog.onConfirm} className={`px-4 py-2 text-sm font-bold text-white rounded-lg transition-colors ${dialog.type === 'confirm' ? 'bg-blue-600 hover:bg-blue-700' : 'bg-emerald-600 hover:bg-emerald-700'}`}>Aceptar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}








