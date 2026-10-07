import sys
import base64

payload_b64 = b"""
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

        async function cargarManagerML() {
            const select = document.getElementById('manager-cuenta-select');
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
                    let badgeSalud = item.health < 1 ? `<span style="background:#fee2e2; color:#ef4444; padding:2px 6px; border-radius:4px; font-size:11px;">Revisar Calidad</span>` : `<span style="color:#10b981;">Ok</span>`;
                    
                    tbody.innerHTML += `
                        <tr>
                            <td><input type="checkbox" class="manager-chk" value="${item.id}"></td>
                            <td><a href="https://articulo.mercadolibre.com.ve/${item.id}" target="_blank">${item.id}</a></td>
                            <td><b>${item.sku}</b></td>
                            <td>${item.title}</td>
                            <td>$${item.price}</td>
                            <td><span style="background:${colorEstado}; color:white; padding:2px 8px; border-radius:10px; font-size:12px;">${item.status}</span></td>
                            <td>${badgeSalud}</td>
                        </tr>
                    `;
                });
            } catch(e) {
                tbody.innerHTML = "<tr><td colspan='7' style='text-align:center; color:red;'>Error de conexi\\u00f3n.</td></tr>";
            }
        }
        
        async function cambiarEstadoMasivo(nuevoEstado) {
            const cuenta = document.getElementById('manager-cuenta-select').value;
            const checks = document.querySelectorAll('.manager-chk:checked');
            const ids = Array.from(checks).map(c => c.value);
            
            if (ids.length === 0) return alert("Selecciona al menos 1 art\\u00edculo.");
            if (!confirm(`\\u00bfEst\\u00e1s seguro de cambiar el estado de ${ids.length} art\\u00edculos a ${nuevoEstado}?`)) return;
            
            try {
                const res = await fetch('/api/manager/estado', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cuenta: cuenta, ids: ids, estado: nuevoEstado})
                });
                const data = await res.json();
                if (data.error) alert(data.error);
                else {
                    alert(`Operaci\\u00f3n completa.\\n\\u00c9xitos: ${data.exitos}\\nErrores: ${data.errores}`);
                    cargarManagerML();
                }
            } catch(e) {
                alert("Error de red.");
            }
        }
        
        function repararProblemasIA() {
            alert("El motor de IA abrir\\u00e1 estos art\\u00edculos conflictivos para sugerir correcciones en t\\u00edtulos y descripciones basado en las pol\\u00edticas de ML.");
        }
        
        function abrirModalClonador() {
            alert("El Clonador Sindicado es la pr\\u00f3xima fase. Extraer\\u00e1 esta lista y la inyectar\\u00e1 en la cuenta destino validando SKUs y precios!");
        }
"""

payload = payload_b64.decode("utf-8")

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx_start = content.find('function actualizarPerfilFlotante() {')
idx_end = content.find('function mostrarSeccion(idSeccion, el) {')

if idx_start != -1 and idx_end != -1:
    old_block = content[idx_start:idx_end]
    content = content.replace(old_block, payload + '\n        ')
    with open('app_web.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('CORRECTED')
else:
    print('NOT FOUND')
