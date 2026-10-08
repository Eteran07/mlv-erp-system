import re
with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

filter_mode_pattern = r"const \[filterMode, setFilterMode\] = useState\('range'\);"
filter_mode_repl = r"const [filterMode, setFilterMode] = useState('all');"
code = re.sub(filter_mode_pattern, filter_mode_repl, code)

html_pattern = r'''                        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-3">
                          <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 cursor-pointer">
                            <input type="radio" name="filterMode" checked=\{filterMode === 'range'\} onChange=\{\(\) => setFilterMode\('range'\)\} className="text-emerald-600 focus:ring-emerald-500"\/>'''

html_repl = r'''                        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-3">
                          <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 cursor-pointer">
                            <input type="radio" name="filterMode" checked={filterMode === 'all'} onChange={() => setFilterMode('all')} className="text-emerald-600 focus:ring-emerald-500"/>
                            Procesar Todo el Archivo
                          </label>
                          <hr className="border-slate-200"/>
                          <label className="flex items-center gap-2 text-sm font-semibold text-slate-700 cursor-pointer">
                            <input type="radio" name="filterMode" checked={filterMode === 'range'} onChange={() => setFilterMode('range')} className="text-emerald-600 focus:ring-emerald-500"/>'''

code = re.sub(html_pattern, html_repl, code)

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched filterMode all")
