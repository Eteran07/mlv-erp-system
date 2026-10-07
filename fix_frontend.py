import sys

payload_js = """
        let paginaActual = 0;
        let totalResultados = 0;

        function actualizarPerfilFlotante() {
            const sel = document.getElementById("cuenta-select");
            const tag = document.getElementById("nombre-perfil-activo");
            const div = document.getElementById("perfil-flotante");
            if (!sel || !tag || !div) return;
            if (sel.value === "TODAS") {
                tag.innerText = "Manager Global (Todas)";
                div.style.background = "#10b981";
                div.style.borderColor = "#34d399";
            } else {
                tag.innerText = "Perfil Activo: " + sel.options[sel.selectedIndex].text;
                div.style.background = "#2563eb";
                div.style.borderColor = "#60a5fa";
            }
        }

        async function cargarManagerML(offset = 0) {
            const select = document.getElementById('manager-cuenta-select');
            const searchBox = document.getElementById('manager-search');
            let query = searchBox ? searchBox.value : "";
            
            if (select.options.length === 0) {
                select.innerHTML = document.getElementById('cuenta-select').innerHTML;
                for (let i=0; i<select.options.length; i++) {
                    if (select.options[i].value === "TODAS") {
                        select.remove(i); break;
                    }
                }
            }
            
            const cuenta = select.value;
            if(!cuenta) return;
            
            paginaActual = offset;
            
            const tbody = document.getElementById('tbody-manager');
            const infoPaginacion = document.getElementById('manager-paginacion-info');
            
            tbody.innerHTML = "<tr><td colspan='8' style='text-align:center; padding:20px;'><br>Cargando inventario...<br><br></td></tr>";
            if (infoPaginacion) infoPaginacion.innerText = "Cargando...";
            
            try {
                const res = await fetch(`/api/manager/publicaciones?cuenta=${encodeURIComponent(cuenta)}&offset=${offset}&q=${encodeURIComponent(query)}`);
                const data = await res.json();
                
                if (data.error) {
                    tbody.innerHTML = `<tr><td colspan='8' style='text-align:center; color:red; padding:20px;'>${data.error}</td></tr>`;
                    return;
                }
                
                totalResultados = data.total;
                
                if (infoPaginacion) {
                    let totalPaginas = Math.ceil(totalResultados / 50);
                    let pagActualNum = Math.floor(offset / 50) + 1;
                    infoPaginacion.innerHTML = `Página <b>${totalResultados === 0 ? 0 : pagActualNum}</b> de <b>${totalPaginas}</b> <span style="margin-left:10px; color:#6b7280; font-size:12px;">(${totalResultados} Artículos Totales)</span>`;
                    
                    document.getElementById('btn-pag-ant').disabled = offset === 0;
                    document.getElementById('btn-pag-sig').disabled = (offset + 50) >= totalResultados;
                }
                
                const items = data.items;
                
                if (!items.length) {
                    tbody.innerHTML = "<tr><td colspan='8' style='text-align:center; padding:20px;'>No se encontraron publicaciones.</td></tr>";
                    return;
                }
                
                tbody.innerHTML = "";
                items.forEach(item => {
                    let colorEstado = item.status === 'active' ? '#10b981' : (item.status === 'paused' ? '#f59e0b' : '#ef4444');
                    
                    // Procesar las alertas de substatus para dar mas info en Revisar Calidad
                    let alertasStr = "";
                    if (item.sub_status && item.sub_status.length > 0) {
                        alertasStr = item.sub_status.join(", ");
                    }
                    
                    let badgeSalud;
                    if (item.health < 1 || alertasStr) {
                        badgeSalud = `<span style="background:#fee2e2; color:#ef4444; padding:2px 6px; border-radius:4px; font-size:11px;" title="${alertasStr}">Revisar Calidad ${alertasStr ? '('+alertasStr+')' : ''}</span>`;
                    } else {
                        badgeSalud = `<span style="color:#10b981; font-weight:bold;">Ok</span>`;
                    }
                    
                    tbody.innerHTML += `
                        <tr>
                            <td><input type="checkbox" class="manager-chk" value="${item.id}"></td>
                            <td><a href="https://articulo.mercadolibre.com.ve/${item.id}" target="_blank">${item.id}</a></td>
                            <td style="color:#2563eb; font-family:monospace;"><b>${item.sku}</b></td>
                            <td style="max-width:300px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${item.title}">${item.title}</td>
                            <td><b>$${item.price}</b></td>
                            <td style="text-align:center;">${item.stock}</td>
                            <td><span style="background:${colorEstado}; color:white; padding:2px 8px; border-radius:10px; font-size:12px;">${item.status}</span></td>
                            <td>${badgeSalud}</td>
                        </tr>
                    `;
                });
            } catch(e) {
                tbody.innerHTML = "<tr><td colspan='8' style='text-align:center; color:red; padding:20px;'>Error de conexión.</td></tr>";
            }
        }
        
        function managerPaginacion(direccion) {
            let nuevoOffset = paginaActual + (direccion * 50);
            if (nuevoOffset < 0) nuevoOffset = 0;
            cargarManagerML(nuevoOffset);
        }
        
        function buscarManager() {
            cargarManagerML(0);
        }
        
        async function cambiarEstadoMasivo(nuevoEstado) {
            const cuenta = document.getElementById('manager-cuenta-select').value;
            const checks = document.querySelectorAll('.manager-chk:checked');
            const ids = Array.from(checks).map(c => c.value);
            
            if (ids.length === 0) return alert("Selecciona al menos 1 artículo.");
            if (!confirm(`¿Estás seguro de cambiar el estado de ${ids.length} artículos a ${nuevoEstado}?`)) return;
            
            try {
                const res = await fetch('/api/manager/estado', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cuenta: cuenta, ids: ids, estado: nuevoEstado})
                });
                const data = await res.json();
                if (data.error) alert(data.error);
                else {
                    alert(`Operación completa.\\nÉxitos: ${data.exitos}\\nErrores: ${data.errores}`);
                    cargarManagerML(paginaActual);
                }
            } catch(e) {
                alert("Error de red.");
            }
        }
        
        function repararProblemasIA() {
            alert("El motor de IA abrirá estos artículos conflictivos para sugerir correcciones en títulos y descripciones basado en las políticas de ML.");
        }
        
        function abrirModalClonador() {
            alert("El Clonador Sindicado es la próxima fase. Extraerá esta lista y la inyectará en la cuenta destino validando SKUs y precios!");
        }
"""

payload_html = """
        <div id="tab-manager" class="section-view">
            <h2>🌐 Manager Matrix & Clonador</h2>
            <div class="card" style="margin-bottom: 20px;">
                <div style="display: flex; gap: 15px; align-items: flex-end; flex-wrap: wrap;">
                    <div style="flex: 1;">
                        <label>Selecciona Cuenta a Inspeccionar:</label>
                        <select id="manager-cuenta-select" class="w-full"></select>
                    </div>
                    <div style="flex: 2;">
                        <label>Buscador (Título o ID ML):</label>
                        <input type="text" id="manager-search" class="w-full" placeholder="Ej: Monitor 144hz..." onkeydown="if(event.key === 'Enter') buscarManager()">
                    </div>
                    <button onclick="buscarManager()" style="background:#2563eb; color:white; padding:10px 20px; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">🔍 Buscar / Refrescar</button>
                </div>
            </div>
            
            <div class="card" style="margin-bottom: 20px;">
                <div style="display: flex; gap: 10px; margin-bottom: 15px; justify-content: space-between;">
                    <div style="display: flex; gap: 10px;">
                        <button onclick="cambiarEstadoMasivo('paused')" style="background:#f59e0b; color:white; padding:8px 15px; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">⏸ Pausar Seleccionados</button>
                        <button onclick="cambiarEstadoMasivo('active')" style="background:#10b981; color:white; padding:8px 15px; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">▶ Activar Seleccionados</button>
                        <button onclick="repararProblemasIA()" style="background:#8b5cf6; color:white; padding:8px 15px; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">🤖 Reparar con IA</button>
                        <button onclick="abrirModalClonador()" style="background:#ef4444; color:white; padding:8px 15px; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">👯‍♂️ Clonar Selección</button>
                    </div>
                    
                    <div style="display: flex; gap: 10px; align-items: center; background:#f3f4f6; padding:5px 15px; border-radius:8px;">
                        <button id="btn-pag-ant" onclick="managerPaginacion(-1)" style="border:none; background:white; padding:5px 10px; border-radius:4px; cursor:pointer; font-weight:bold; color:#374151;">◀ Ant</button>
                        <span id="manager-paginacion-info" style="font-size:13px; color:#374151;">Página 0 de 0</span>
                        <button id="btn-pag-sig" onclick="managerPaginacion(1)" style="border:none; background:white; padding:5px 10px; border-radius:4px; cursor:pointer; font-weight:bold; color:#374151;">Sig ▶</button>
                    </div>
                </div>
                
                <div class="table-container" style="max-height: 500px; overflow-y: auto;">
                    <table class="w-full table-matrix" id="tabla-manager">
                        <thead>
                            <tr>
                                <th style="width: 40px;"><input type="checkbox" onchange="document.querySelectorAll('.manager-chk').forEach(c => c.checked = this.checked)"></th>
                                <th style="width: 120px;">ID MLV</th>
                                <th style="width: 150px;">SKU</th>
                                <th>Título</th>
                                <th style="width: 100px;">Precio</th>
                                <th style="width: 80px;">Stock</th>
                                <th style="width: 100px;">Estado</th>
                                <th style="width: 150px;">Infracciones</th>
                            </tr>
                        </thead>
                        <tbody id="tbody-manager">
                            <tr><td colspan="8" style="text-align:center; padding:20px;">Selecciona una cuenta y presiona Buscar.</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
"""

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. REPLACE THE JS BLOCK (Wait, I replaced it partially in the previous step? Let's check if `let paginaActual = 0;` is there)
idx_start = content.find('let paginaActual = 0;')
if idx_start == -1:
    idx_start = content.find('function actualizarPerfilFlotante() {')

idx_end = content.find('function mostrarSeccion(idSeccion, el) {')

if idx_start != -1 and idx_end != -1:
    old_block = content[idx_start:idx_end]
    content = content.replace(old_block, payload_js + '\n        ')
    print('JS REPLACED')
else:
    print('JS NOT FOUND')

# 2. REPLACE THE HTML BLOCK
idx_html_start = content.find('<div id="tab-manager" class="section-view">')
idx_html_end = content.find('<div id="tab-tokens" class="section-view">')

if idx_html_start != -1 and idx_html_end != -1:
    old_html = content[idx_html_start:idx_html_end]
    content = content.replace(old_html, payload_html + '\n        ')
    print('HTML REPLACED')
else:
    print('HTML NOT FOUND')

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("ALL DONE")
