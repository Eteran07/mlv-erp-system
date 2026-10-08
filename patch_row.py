import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Remove max-w-6xl for full width in Step 3
container_pattern = r'''<div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-6xl mx-auto space-y-4">'''
container_repl = r'''<div className="flex-1 overflow-y-auto p-6">
        <div className={`mx-auto space-y-4 ${step === 3 ? 'w-full' : 'max-w-6xl'}`}>'''
code = code.replace(container_pattern, container_repl)

# 2. Change ProductRow wrapper to not be a "cuadro"
row_wrapper = r'''className={`border rounded-xl mb-2 overflow-hidden transition-all shadow-sm \$\{selected \? 'border-blue-200 bg-white' : 'border-slate-200 bg-slate-50 opacity-60'\}`}'''
row_wrapper_repl = r'''className={`border-b transition-all ${selected ? 'bg-white' : 'bg-slate-50 opacity-60'}`}'''
code = re.sub(row_wrapper, row_wrapper_repl, code)

# 3. Inject modal state and buttons in ProductRow
row_state = r'''const \[expanded, setExpanded\] = useState\(false\);
  const \[iaLoading, setIaLoading\] = useState\(false\);'''
row_state_repl = r'''const [expanded, setExpanded] = useState(false);
  const [iaLoading, setIaLoading] = useState(false);
  const [showAttrModal, setShowAttrModal] = useState(false);

  const verDescripcionFinal = () => {
    const BLOQUE_SUPERIOR = "SOMOS TIENDA FÍSICA, Empresa Mayorista Líder en el Mercado de la Computación Producto 100% de calidad";
    const BLOQUE_INFERIOR = ".\nPor Favor Verifique la disponibilidad antes de ofertar\nPor Favor Verifique la disponibilidad antes de ofertar\nPor Favor Verifique la disponibilidad antes de ofertar\n**************************************************************************************************\n- Emitimos factura LEGAL\n- Trabajamos con agentes de retención\n- Enviamos a todo el País.\n**************************************************************************************************\nCOMENTARIOS:\n- Realice todas las preguntas necesarias Antes de ofertar.\n- El equipo de ventas está a tu disposición para responder tus consultas.\n- Te invitamos a que solo ofertes cuando estés seguro de realizar la compra.\n- La disponibilidad y precio del producto publicado solo se garantiza por un lapso de 24hrs luego de haber solicitado la compra.\n- Si presentas algún inconveniente durante el proceso de compras estaremos a tu completa disposición para atenderte y solventar la situación. Deseamos que tu compra con nosotros siempre genere una calificación positiva.\n****************************************************************************************************\nHORARIO DE TRABAJO\n****************************************************\nDe Lunes A Viernes\nDe 8:30am A 5:30pm";
    
    let t = rowData.titulo ?? p.Titulo;
    let descFinal = `${BLOQUE_SUPERIOR}\n\n${t}\n${t}\n${t}\n\n`;
    const custom = rowData.descripcion ?? p.DescripcionCustom ?? '';
    if (custom.trim().length > 5) descFinal += `${custom}\n\n`;
    
    descFinal += "========================================\nCARACTERÍSTICAS TÉCNICAS\n========================================\n\n";
    const attrs = rowData.aiAtributos || {};
    Object.entries(attrs).forEach(([k,v]) => {
      descFinal += `  ${k.replace(/_/g, ' ')}: ${v}\n`;
    });
    descFinal += "\n========================================\n\n" + BLOQUE_INFERIOR;
    alert(descFinal);
  };'''
code = re.sub(row_state, row_state_repl, code)

# 4. Add the buttons to the expanded view and the modal component
exp_panel = r'''\{/\* Descripcion \*/\}
          <div>
            <label className="block text-xs font-bold text-slate-600 mb-1">Descripcion Comercial</label>'''
exp_panel_repl = r'''{/* Atributos Modal */}
      <AttributesModal isOpen={showAttrModal} onClose={() => setShowAttrModal(false)} catId={p.Categoria_ID} titulo={rowData.titulo ?? p.Titulo} rowData={rowData} onSave={(vals) => onRowChange(idx, 'aiAtributos', vals)} />
      
      {/* Descripcion */}
          <div className="flex flex-col">
            <div className="flex justify-between items-end mb-1">
              <label className="block text-xs font-bold text-slate-600">Descripcion Comercial (Cuerpo Central)</label>
              <button onClick={verDescripcionFinal} className="text-[10px] bg-slate-800 text-white px-2 py-1 rounded font-bold hover:bg-slate-700">Ver Plantilla Final</button>
            </div>'''
code = code.replace(exp_panel, exp_panel_repl)

attr_ia = r'''\{/\* Atributos IA \*/\}
          \{rowData\.aiAtributos && Object\.keys\(rowData\.aiAtributos\)\.length > 0 && \('''
attr_ia_repl = r'''{/* Atributos IA */}
          <div className="col-span-2 mt-2">
            <div className="flex items-center gap-3 mb-2">
              <label className="block text-xs font-bold text-slate-600">Ficha Técnica / Atributos (IA o Manual)</label>
              <button onClick={() => setShowAttrModal(true)} className="text-[10px] bg-blue-100 text-blue-700 px-2 py-1 rounded font-bold hover:bg-blue-200">Editar Manualmente</button>
            </div>
            {rowData.aiAtributos && Object.keys(rowData.aiAtributos).length > 0 && ('''
code = re.sub(attr_ia, attr_ia_repl, code)

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched ProductRow UI and features")
