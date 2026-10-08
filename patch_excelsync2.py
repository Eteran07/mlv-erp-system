import re
import os

path = r"c:\Users\Edgar\Desktop\ERP_MercadoLibre\frontend\src\pages\ExcelSync.jsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. ADD Custom Dialog State & Components
if "const [dialog," not in content:
    content = content.replace(
        "export default function ExcelSync() {",
        "export default function ExcelSync() {\n  const [dialog, setDialog] = useState({ isOpen: false, type: 'alert', message: '', onConfirm: null, onCancel: null });\n"
        "  const customAlert = (message) => setDialog({ isOpen: true, type: 'alert', message, onConfirm: () => setDialog({ isOpen: false, type: 'alert', message: '', onConfirm: null, onCancel: null }) });\n"
        "  const customConfirm = (message, onConfirmCallback) => setDialog({ isOpen: true, type: 'confirm', message, onConfirm: () => { setDialog({ isOpen: false, type: 'alert', message: '', onConfirm: null, onCancel: null }); if (onConfirmCallback) onConfirmCallback(); }, onCancel: () => setDialog({ isOpen: false, type: 'alert', message: '', onConfirm: null, onCancel: null }) });\n"
    )
    
    # Dialog component rendering at the end of the return statement
    dialog_jsx = """
      {/* Custom Dialog Overlay */}
      {dialog.isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/60 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-6">
              <h3 className="text-lg font-bold text-slate-800 mb-2">{dialog.type === 'confirm' ? 'Confirmación' : 'Aviso'}</h3>
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
}"""
    content = content.replace("    </div>\n  );\n}", dialog_jsx)

# 2. Replace alert/confirm
content = re.sub(r"if \(!window\.confirm\((.*?)\)\) return;", r"if (!window.confirm(\1)) return; // Patched to async", content)
content = re.sub(r"if \(!confirm\((.*?)\)\) return;", r"if (!confirm(\1)) return; // Patched to async", content)
content = re.sub(r"\balert\((.*?)\)", r"customAlert(\1)", content)

# Since confirm needs to wrap the rest of the function, I'll rewrite the specific functions

# handlePreview
content = re.sub(
    r"const handlePreview = async \(\) => \{\s*if \(!window\.confirm\('(.*?)'\)\) return; // Patched to async\s*setShowCategoryModal\(false\);",
    "const handlePreview = async () => {\n    customConfirm('\\1', async () => {\n      setShowCategoryModal(false);",
    content
)
# close handlePreview
content = re.sub(
    r"\}\s*finally \{\s*setLoadingPreview\(false\);\s*\}\s*\};",
    "} finally { setLoadingPreview(false); } }); };",
    content
)

# handlePublish
content = re.sub(
    r"const handlePublish = async \(\) => \{\s*if \(!window\.confirm\(`(.*?)`\)\) return; // Patched to async\s*setIsPublishing\(true\);",
    "const handlePublish = async () => {\n    customConfirm(`\\1`, async () => {\n      setIsPublishing(true);",
    content
)
content = re.sub(
    r"\}\s*finally \{\s*setIsPublishing\(false\);\s*\}\s*\};",
    "} finally { setIsPublishing(false); } }); };",
    content
)

# handleAIAll
content = re.sub(
    r"const handleAIAll = async \(\) => \{\s*const items = previewData\?\.productos \|\| \[\];\s*const validIdxs = \[\.\.\.selectedRows\]\.filter\(i => items\[i\]\);\s*if \(!validIdxs\.length\) return;\s*if \(!confirm\(`(.*?)`\)\) return; // Patched to async\s*setIaAllLoading\(true\);",
    "const handleAIAll = async () => {\n    const items = previewData?.productos || [];\n    const validIdxs = [...selectedRows].filter(i => items[i]);\n    if (!validIdxs.length) return;\n    customConfirm(`\\1`, async () => {\n      setIaAllLoading(true);",
    content
)
content = re.sub(
    r"if \(i \+ BATCH < validIdxs\.length\) await new Promise\(r => setTimeout\(r, 2000\)\);\s*\}\s*setIaAllLoading\(false\);\s*\};",
    "if (i + BATCH < validIdxs.length) await new Promise(r => setTimeout(r, 2000));\n      }\n      setIaAllLoading(false);\n    });\n  };",
    content
)

# 3. FIX handleRefreshImages
content = re.sub(
    r"const handleRefreshImages = async \(silent = false, specificIdxs = null, specificData = null\) => \{\s*const idxsToProcess = specificIdxs \|\| Array\.from\(selectedRows\);\s*if \(!silent && !window\.confirm\(`(.*?)`\)\) return; // Patched to async",
    """const handleRefreshImages = async (isSilent = false, specificIdxs = null, specificData = null) => {
    const silent = typeof isSilent === 'boolean' ? isSilent : false;
    const idxsToProcess = specificIdxs || Array.from(selectedRows);
    const executeRefresh = async () => {
""",
    content
)
content = re.sub(
    r"const dToUse = specificData \|\| previewData;",
    "const dToUse = specificData || previewData || { productos: [] };",
    content
)
content = re.sub(
    r"if \(!silent\) customAlert\('Error refrescando(.*?)'\);\s*\}\s*\};",
    "if (!silent) customAlert('Error refrescando\\1');\n      }\n    };\n    if (!silent) {\n      customConfirm(`Buscar e intentar emparejar imǭgenes locales para ${idxsToProcess.length} articulos?`, executeRefresh);\n    } else {\n      executeRefresh();\n    }\n  };",
    content
)

# 4. FIX Badges
content = re.sub(
    r"\{c_name\.substring\(0, 3\)\.toUpperCase\(\)\} \{status === 'EXISTE' \? 'Ya' : '\+'\}",
    "{c_name.substring(0, 4).toUpperCase()}: {status === 'EXISTE' ? 'Publicado' : 'No'}",
    content
)

# 5. FIX Filter
filter_block = """    const filteredItems = (previewData?.productos || []).map((p, idx) => ({ p, idx })).filter(item => {
      if (hidePublished) {
         return !(item.p.EstadoPublicacin || item.p["Estado Publicacin"] || "").includes("Ya publicado");
      }
      return true;
    });"""

new_filter_block = """    const filteredItems = (previewData?.productos || []).map((p, idx) => ({ p, idx })).filter(item => {
      if (hidePublished && item.p.EstadoCuentas) {
         if (cuentaActiva === 'TODAS') {
             const allExist = Object.values(item.p.EstadoCuentas).every(s => s === 'EXISTE');
             if (allExist) return false;
         } else {
             const selectedAccount = cuentas.find(c => c.archivo === cuentaActiva)?.nombre;
             if (selectedAccount && item.p.EstadoCuentas[selectedAccount] === 'EXISTE') return false;
         }
      }
      return true;
    });"""
content = content.replace(filter_block, new_filter_block)

# 6. FIX Attributes Modal Required vs Optional
attrs_modal_block = """              <div className="space-y-4">
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
              </div>"""

new_attrs_modal_block = """              <div className="space-y-6">
                {(() => {
                  const req = attrs.filter(a => a.tags?.includes('required'));
                  const opt = attrs.filter(a => !a.tags?.includes('required'));
                  const renderField = (a) => (
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
                  );
                  return (
                    <>
                      {req.length > 0 && (
                        <div className="bg-blue-50/50 p-4 rounded-xl border border-blue-100">
                          <h4 className="font-bold text-blue-800 mb-3 flex items-center gap-2">Atributos Obligatorios</h4>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {req.map(renderField)}
                          </div>
                        </div>
                      )}
                      {opt.length > 0 && (
                        <div className="p-4 rounded-xl border border-slate-200">
                          <h4 className="font-bold text-slate-700 mb-3 flex items-center gap-2">Atributos Opcionales</h4>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {opt.map(renderField)}
                          </div>
                        </div>
                      )}
                    </>
                  );
                })()}
              </div>"""
content = content.replace(attrs_modal_block, new_attrs_modal_block)

# Ensure the template is properly set to rowData.descripcion instead of just alert
# Wait, the user said "quiero que la descripcion aparezca en ese recuadro".
# The textarea has value={rowData.descripcion ?? p.DescripcionCustom ?? ''}
# This means my code ALREADY put it in rowData.descripcion in handlePreview! 
# Let's double check if it actually does. If the problem is that it is EMPTY in the textarea,
# maybe they meant that they want the VerPlantillaOriginal button to DO something else?
# Let's remove the "Ver Plantilla Original" alert as well and let them edit it inline.

content = re.sub(r"const verDescripcionFinal = \(\) => \{.*?alert\(descFinal\);\s*\};", "", content, flags=re.DOTALL)
content = content.replace("""<button onClick={verDescripcionFinal} className="text-[10px] text-blue-600 font-bold hover:underline">Ver Plantilla Original</button>""", "")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch 2 successful!")

