import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Make ProductRow header more spacious
pr_header = r'className="flex items-start gap-3 p-3"'
pr_header_repl = r'className="flex items-center gap-4 p-4"'
code = code.replace(pr_header, pr_header_repl)

# Make inputs more spacious
input_precio = r'w-24 text-right text-sm font-bold border rounded px-2 py-0\.5'
input_precio_repl = r'w-28 text-right text-base font-bold border rounded-lg px-3 py-1.5'
code = code.replace(input_precio, input_precio_repl)

input_stock = r'w-16 text-right text-sm font-bold text-slate-700 border border-slate-200 rounded px-2 py-0\.5'
input_stock_repl = r'w-20 text-right text-base font-bold text-slate-700 border border-slate-300 rounded-lg px-3 py-1.5'
code = code.replace(input_stock, input_stock_repl)

input_title = r'w-full font-semibold text-slate-800 text-sm'
input_title_repl = r'w-full font-bold text-slate-800 text-base'
code = code.replace(input_title, input_title_repl)

select_exp = r'text-\[11px\] border border-slate-200 rounded px-1\.5 py-0\.5'
select_exp_repl = r'text-xs border border-slate-300 rounded-lg px-2 py-1'
code = code.replace(select_exp, select_exp_repl)

select_env = r'text-\[10px\] border border-slate-200 rounded px-1\.5 py-0\.5'
select_env_repl = r'text-xs border border-slate-300 rounded-lg px-2 py-1'
code = code.replace(select_env, select_env_repl)

badge_status = r'text-\[10px\] font-bold'
badge_status_repl = r'text-[11px] font-bold px-2 py-1'
code = code.replace(badge_status, badge_status_repl)

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched ProductRow spacing")
