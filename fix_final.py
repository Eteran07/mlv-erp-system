import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

tab_html = '''
        <div id="tab-manager" class="section-view">
            <h2>🌐 Manager Matrix & Clonador</h2>
            <div class="card" style="margin-bottom: 20px;">
                <div style="display: flex; gap: 15px; align-items: flex-end; flex-wrap: wrap;">
                    <div style="flex: 1;">
                        <label>Selecciona Cuenta a Inspeccionar:</label>
                        <select id="manager-cuenta-select" class="w-full"></select>
                    </div>
                    <button onclick="cargarManagerML()" style="background:#2563eb; color:white; padding:10px 20px; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">🔍 Cargar Catálogo en Vivo</button>
                </div>
            </div>
            
            <div class="card" style="margin-bottom: 20px;">
                <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                    <button onclick="cambiarEstadoMasivo('paused')" style="background:#f59e0b; color:white; padding:8px 15px; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">⏸ Pausar Seleccionados</button>
                    <button onclick="cambiarEstadoMasivo('active')" style="background:#10b981; color:white; padding:8px 15px; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">▶ Activar Seleccionados</button>
                    <button onclick="repararProblemasIA()" style="background:#8b5cf6; color:white; padding:8px 15px; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">🤖 Reparar Problemas con IA</button>
                    <button onclick="abrirModalClonador()" style="background:#ef4444; color:white; padding:8px 15px; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">👯‍♂️ Clonar hacia otra Cuenta</button>
                </div>
                
                <div class="table-container" style="max-height: 500px; overflow-y: auto;">
                    <table class="w-full table-matrix" id="tabla-manager">
                        <thead>
                            <tr>
                                <th><input type="checkbox" onchange="document.querySelectorAll('.manager-chk').forEach(c => c.checked = this.checked)"></th>
                                <th>ID MLV</th>
                                <th>SKU</th>
                                <th>Título</th>
                                <th>Precio</th>
                                <th>Estado</th>
                                <th>Salud / Infracciones</th>
                            </tr>
                        </thead>
                        <tbody id="tbody-manager">
                            <tr><td colspan="7" style="text-align:center; padding:20px;">Selecciona una cuenta y dale a Cargar.</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
'''

js_funcs = '''
        function actualizarPerfilFlotante() {
            const sel = document.getElementById("cuenta-select");
            const tag = document.getElementById("nombre-perfil-activo");
            const div = document.getElementById("perfil-flotante");
            if (!sel || !tag || !div) return;
            if (sel.value === "TODAS") {
                tag.innerText = "Manager Global (Todas)";
                div.style.background = "#10b981"; // Verde para el manager
                div.style.borderColor = "#34d399";
            } else {
                tag.innerText = "Perfil Activo: " + sel.options[sel.selectedIndex].text;
                div.style.background = "#2563eb"; // Azul para individual
                div.style.borderColor = "#60a5fa";
            }
        }

        async function cargarManagerML() {
            const select = document.getElementById('manager-cuenta-select');
            // Si est vaco, copio los de cuenta-select
            if (select.options.length === 0) {
                select.innerHTML = document.getElementById('cuenta-select').innerHTML;
                // remove TODAS if present
                for (let i=0; i<select.options.length; i++) {
                    if (select.options[i].value === "TODAS") {
                        select.remove(i); break;
                    }
                }
            }
            
            const cuenta = select.value;
            if(!cuenta) return;
            
            const tbody = document.getElementById('tbody-manager');
            tbody.innerHTML = "<tr><td colspan='7' style='text-align:center;'>Cargando inventario en vivo desde ML...</td></tr>";
            
            try {
                const res = await fetch('/api/manager/publicaciones?cuenta=' + encodeURIComponent(cuenta));
                const data = await res.json();
                
                if (data.error) {
                    tbody.innerHTML = "<tr><td colspan='7' style='text-align:center; color:red;'>" + data.error + "</td></tr>";
                    return;
                }
                if (!data.length) {
                    tbody.innerHTML = "<tr><td colspan='7' style='text-align:center;'>No se encontraron publicaciones.</td></tr>";
                    return;
                }
                
                tbody.innerHTML = "";
                data.forEach(item => {
                    let colorEstado = item.status === 'active' ? '#10b981' : (item.status === 'paused' ? '#f59e0b' : '#ef4444');
                    let badgeSalud = item.health < 1 ? <span style="background:#fee2e2; color:#ef4444; padding:2px 6px; border-radius:4px; font-size:11px;">Revisar Calidad</span> : <span style="color:#10b981;">Ok</span>;
                    
                    tbody.innerHTML += 
                        <tr>
                            <td><input type="checkbox" class="manager-chk" value=""></td>
                            <td><a href="https://articulo.mercadolibre.com.ve/" target="_blank"></a></td>
                            <td><b></b></td>
                            <td></td>
                            <td>{item.price}</td>
                            <td><span style="background:; color:white; padding:2px 8px; border-radius:10px; font-size:12px;"></span></td>
                            <td></td>
                        </tr>
                    ;
                });
            } catch(e) {
                tbody.innerHTML = "<tr><td colspan='7' style='text-align:center; color:red;'>Error de conexin.</td></tr>";
            }
        }
        
        async function cambiarEstadoMasivo(nuevoEstado) {
            const cuenta = document.getElementById('manager-cuenta-select').value;
            const checks = document.querySelectorAll('.manager-chk:checked');
            const ids = Array.from(checks).map(c => c.value);
            
            if (ids.length === 0) return alert("Selecciona al menos 1 artculo.");
            if (!confirm(Ests seguro de cambiar el estado de  artculos a ?)) return;
            
            try {
                const res = await fetch('/api/manager/estado', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cuenta: cuenta, ids: ids, estado: nuevoEstado})
                });
                const data = await res.json();
                if (data.error) alert(data.error);
                else {
                    alert(Operacin completa.\\nxitos: \\nErrores: );
                    cargarManagerML(); // Recargar
                }
            } catch(e) {
                alert("Error de red.");
            }
        }
        
        function repararProblemasIA() {
            alert("El motor de IA abrir estos artculos conflictivos para sugerir correcciones en ttulos y descripciones basado en las polticas de ML. (En desarrollo en el prximo mdulo)");
        }
        
        function abrirModalClonador() {
            alert("El Clonador Sindicado es la prxima fase. Extraer esta lista y la inyectar en la cuenta destino validando SKUs y precios!");
        }
'''

new_lines = []
for line in lines:
    if '<div id="tab-tokens" class="section-view">' in line:
        new_lines.append(tab_html)
        
    if 'function mostrarSeccion' in line:
        new_lines.append(js_funcs)
        
    new_lines.append(line)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
