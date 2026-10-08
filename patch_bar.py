import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

pattern = r'''                          <button
                            onClick=\{\(\) => setShowCategoryModal\(true\)\}
                            disabled=\{loadingPreview \|\| !mapping\.col_tit\}
                            className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white px-6 py-2 rounded-lg font-bold flex items-center gap-2 shadow transition-all"
                          >
                            \{loadingPreview \? <Loader2 className="animate-spin" size=\{18\}\/> : <Eye size=\{18\}\/>\}
                            Generar Previsualizacion
                          </button>
                        </div>'''

repl = r'''                          <button
                            onClick={() => setShowCategoryModal(true)}
                            disabled={loadingPreview || !mapping.col_tit}
                            className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white px-6 py-2 rounded-lg font-bold flex items-center gap-2 shadow transition-all"
                          >
                            {loadingPreview ? <Loader2 className="animate-spin" size={18}/> : <Eye size={18}/>}
                            Generar Previsualizacion
                          </button>
                        </div>
                        {loadingPreview && progress && (
                          <div className="mt-4 w-full text-center animate-in fade-in">
                            <div className="text-sm font-medium text-slate-600 mb-1">{progress.mensaje}</div>
                            <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden shadow-inner max-w-lg mx-auto">
                              <div className="bg-emerald-500 h-full transition-all duration-300 ease-out" style={{ width: `${progress.porcentaje}%` }}/>
                            </div>
                          </div>
                        )}'''

code = re.sub(pattern, repl, code)

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched loading bar")
