import sys

js_func = """
        async function seleccionarTodasLasPaginas() {
            const cuenta = document.getElementById('manager-cuenta-select').value;
            const searchBox = document.getElementById('manager-search');
            const selectFiltro = document.getElementById('manager-filtro-estado');
            
            let query = searchBox ? searchBox.value : "";
            let filtro = selectFiltro ? selectFiltro.value : "todas";
            
            if (!cuenta) return alert("Selecciona una cuenta primero.");
            
            let originalText = document.getElementById('manager-paginacion-info').innerText;
            document.getElementById('manager-paginacion-info').innerText = "⏳ Recolectando IDs de todas las páginas, por favor espera...";
            
            try {
                const res = await fetch(`/api/manager/seleccionar-todas?cuenta=${encodeURIComponent(cuenta)}&q=${encodeURIComponent(query)}&filtro_estado=${encodeURIComponent(filtro)}`);
                const data = await res.json();
                
                if(data.error) {
                    alert(data.error);
                    document.getElementById('manager-paginacion-info').innerText = originalText;
                    return;
                }
                
                let ids = data.ids || [];
                if(ids.length === 0) {
                    alert("No hay artículos para seleccionar.");
                } else {
                    ids.forEach(id => seleccionadosGlobal.add(id));
                    
                    document.querySelectorAll('.manager-chk').forEach(c => {
                        if (seleccionadosGlobal.has(c.value)) c.checked = true;
                    });
                    
                    const btnPausa = document.getElementById('btn-pausar-sel');
                    if (btnPausa) {
                        btnPausa.innerText = `⏸ Pausar Seleccionados (${seleccionadosGlobal.size})`;
                    }
                    
                    alert(`¡Éxito! Se seleccionaron ${ids.length} artículos en total.\\n(Puedes comprobarlo en el contador del botón de pausa)`);
                }
            } catch(e) {
                alert("Error de red conectando con el servidor.");
            }
            document.getElementById('manager-paginacion-info').innerText = originalText;
        }
"""

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to replace the broken function with the correct one!
idx_start = content.find('async function seleccionarTodasLasPaginas() {')
idx_end = content.find('function importarExcelManager() {')

if idx_start != -1 and idx_end != -1:
    content = content[:idx_start] + js_func + "\n        " + content[idx_end:]
    with open('app_web.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("JS FUNCTION FIXED")
else:
    print("NOT FOUND")
