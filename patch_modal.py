import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Add AttributesModal and description preview
modal_code = r'''
function AttributesModal({ isOpen, onClose, catId, titulo, rowData, onSave }) {
  const [attrs, setAttrs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [localVals, setLocalVals] = useState(rowData.aiAtributos || {});

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    fetch(`/api/atributos-categoria/${catId}`)
      .then(r => r.json())
      .then(d => { setAttrs(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [isOpen, catId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="p-4 border-b border-slate-200 flex justify-between items-center">
          <h3 className="font-bold text-lg text-slate-800">Ficha Técnica: {titulo}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 font-bold">&times;</button>
        </div>
        <div className="p-4 overflow-y-auto flex-1">
          {loading ? (
            <div className="flex justify-center p-8"><Loader2 className="animate-spin text-blue-500" size={32}/></div>
          ) : attrs.length === 0 ? (
            <div className="text-slate-500 text-center p-8">No hay atributos obligatorios para esta categoría.</div>
          ) : (
            <div className="space-y-4">
              {attrs.map(a => (
                <div key={a.id}>
                  <label className="block text-sm font-bold text-slate-700 mb-1">{a.name} {a.tags?.includes('required') && <span className="text-red-500">*</span>}</label>
                  {a.values_list && a.values_list.length > 0 ? (
                    <select value={localVals[a.id] || ''} onChange={e => setLocalVals({...localVals, [a.id]: e.target.value})} className="w-full border border-slate-300 rounded-lg p-2 text-sm bg-white">
                      <option value="">Seleccione...</option>
                      {a.values_list.map(v => <option key={v.id} value={v.name}>{v.name}</option>)}
                    </select>
                  ) : (
                    <input type="text" value={localVals[a.id] || ''} onChange={e => setLocalVals({...localVals, [a.id]: e.target.value})} className="w-full border border-slate-300 rounded-lg p-2 text-sm" placeholder={a.hint || ''} />
                  )}
                </div>
              ))}
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
'''
code = code.replace("export default function ExcelSync() {", modal_code + "\nexport default function ExcelSync() {")

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched AttributesModal component")
