import sys

payload_js = """
        let paginaActual = 0;
        let totalResultados = 0;
        let seleccionadosGlobal = new Set();
        let itemsOriginales = {};
        let modoEdicion = false;
        let ultimasSugerenciasIA = [];

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

        function toggleSeleccion(id, isChecked) {
            if (isChecked) seleccionadosGlobal.add(id);
            else seleccionadosGlobal.delete(id);
            
            const btnPausa = document.getElementById('btn-pausar-sel');
            if (btnPausa) {
                btnPausa.innerText = `⏸ Pausar Seleccionados (${seleccionadosGlobal.size})`;
            }
        }

        function toggleTodosVisual(isChecked) {
            document.querySelectorAll('.manager-chk').forEach(c => {
                c.checked = isChecked;
                toggleSeleccion(c.value, isChecked);
            });
        }

        function toggleModoEdicion() {
            modoEdicion = !modoEdicion;
            document.querySelectorAll('.vista-texto').forEach(el => el.style.display = modoEdicion ? 'none' : 'block');
            document.querySelectorAll('.vista-input').forEach(el => {
                if(el.classList.contains('inline-price')) {
                    el.parentElement.style.display = modoEdicion ? 'flex' : 'none';
                } else {
                    el.style.display = modoEdicion ? 'block' : 'none';
                }
            });
            let btnGuardar = document.getElementById('btn-guardar-cambios');
            if (btnGuardar) btnGuardar.style.display = modoEdicion ? 'inline-block' : 'none';
            
            let btnToggle = document.getElementById('btn-toggle-edicion');
            if (btnToggle) btnToggle.innerText = modoEdicion ? '❌ Cancelar Edición' : '✏️ Activar Edición';
        }

        async function cargarManagerML(offset = 0) {
            const select = document.getElementById('manager-cuenta-select');
            const searchBox = document.getElementById('manager-search');
            const selectFiltro = document.getElementById('manager-filtro-estado');
            
            let query = searchBox ? searchBox.value : "";
            let filtro = selectFiltro ? selectFiltro.value : "todas";
            
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
            const masterChk = document.querySelector('thead input[type="checkbox"]');
            if(masterChk) masterChk.checked = false;
            
            const tbody = document.getElementById('tbody-manager');
            const infoPaginacion = document.getElementById('manager-paginacion-info');
            
            tbody.innerHTML = "<tr><td colspan='8' style='text-align:center; padding:20px;'><br>Cargando inventario...<br><br></td></tr>";
            if (infoPaginacion) infoPaginacion.innerText = "Cargando...";
            
            try {
                const res = await fetch(`/api/manager/publicaciones?cuenta=${encodeURIComponent(cuenta)}&offset=${offset}&q=${encodeURIComponent(query)}&filtro_estado=${encodeURIComponent(filtro)}`);
                const data = await res.json();
                
                if (data.error) {
                    tbody.innerHTML = `<tr><td colspan='8' style='text-align:center; color:red; padding:20px;'>${data.error}</td></tr>`;
                    return;
                }
                
                totalResultados = data.total;
                
                if (infoPaginacion) {
                    let totalPaginas = Math.ceil(totalResultados / 50);
                    let pagActualNum = Math.floor(offset / 50) + 1;
                    infoPaginacion.innerHTML = `Página <b>${totalResultados === 0 ? 0 : pagActualNum}</b> de <b>${totalPaginas}</b> <span style="margin-left:10px; color:#6b7280; font-size:12px;">(${totalResultados} Totales)</span>`;
                    
                    document.getElementById('btn-pag-ant').disabled = offset === 0;
                    document.getElementById('btn-pag-sig').disabled = (offset + 50) >= totalResultados;
                }
                
                const items = data.items;
                
                if (!items.length) {
                    tbody.innerHTML = "<tr><td colspan='8' style='text-align:center; padding:20px;'>No se encontraron publicaciones con esos criterios.</td></tr>";
                    return;
                }
                
                tbody.innerHTML = "";
                items.forEach(item => {
                    itemsOriginales[item.id] = {title: item.title, price: item.price};
                    
                    let colorEstado = item.status === 'active' ? '#10b981' : (item.status === 'paused' ? '#f59e0b' : '#ef4444');
                    
                    let alertasStr = "";
                    if (item.sub_status && item.sub_status.length > 0) {
                        alertasStr = item.sub_status.join(", ");
                    }
                    
                    let translatedStatus = "";
                    let esInfraccionReal = false;
                    
                    if (item.sub_status && item.sub_status.includes('duplicated')) { translatedStatus = "Publicación Duplicada"; esInfraccionReal = true; }
                    else if (item.sub_status && item.sub_status.includes('suspended')) { translatedStatus = "Suspendida por ML"; esInfraccionReal = true; }
                    else if (item.sub_status && item.sub_status.includes('banned')) { translatedStatus = "Baneada por ML"; esInfraccionReal = true; }
                    else if (item.sub_status && item.sub_status.includes('warning')) { translatedStatus = "Advertencia de ML"; esInfraccionReal = true; }
                    else if (item.status === 'under_review' || item.status === 'inactive') { translatedStatus = alertasStr || "Revisión/Inactiva"; esInfraccionReal = true; }
                    
                    if (item.sub_status && item.sub_status.includes('paused_by_seller')) {
                        esInfraccionReal = false; // Override, you paused it manually
                    }
                    
                    let badgeSalud;
                    if (esInfraccionReal) {
                        badgeSalud = `<span style="background:#fee2e2; color:#ef4444; padding:2px 6px; border-radius:4px; font-size:11px;" title="${translatedStatus}">🚨 Infracción ${translatedStatus ? '('+translatedStatus+')' : ''}</span>`;
                    } else {
                        badgeSalud = `<span style="color:#10b981; font-weight:bold;">✅ Ok</span>`;
                    }
                    
                    let checkedAttr = seleccionadosGlobal.has(item.id) ? 'checked' : '';
                    let titleEscaped = item.title.replace(/"/g, '&quot;');
                    let safePrice = item.price !== null ? item.price : 0;
                    
                    let displayTexto = modoEdicion ? 'none' : 'block';
                    let displayInput = modoEdicion ? 'block' : 'none';
                    let displayFlexInput = modoEdicion ? 'flex' : 'none';
                    
                    tbody.innerHTML += `
                        <tr id="row-${item.id}">
                            <td><input type="checkbox" class="manager-chk" value="${item.id}" ${checkedAttr} onchange="toggleSeleccion('${item.id}', this.checked)"></td>
                            <td><a href="https://articulo.mercadolibre.com.ve/${item.id}" target="_blank" style="color:#2563eb; text-decoration:underline; font-weight:bold;">${item.id}</a></td>
                            <td style="color:#4b5563; font-family:monospace; font-size:12px;"><b>${item.sku}</b></td>
                            <td style="max-width:300px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${titleEscaped}">
                                <span class="vista-texto" style="display:${displayTexto}">${titleEscaped}</span>
                                <input type="text" class="vista-input inline-title w-full" data-id="${item.id}" value="${titleEscaped}" style="display:${displayInput}; border:1px solid #d1d5db; border-radius:4px; padding:4px;">
                            </td>
                            <td>
                                <span class="vista-texto" style="display:${displayTexto}; font-weight:bold;">$${safePrice}</span>
                                <div class="vista-input" style="display:${displayFlexInput}; align-items:center;">$<input type="number" step="0.01" class="inline-price" data-id="${item.id}" value="${safePrice}" style="border:1px solid #d1d5db; border-radius:4px; padding:4px; width:70px; margin-left:4px;"></div>
                            </td>
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
            seleccionadosGlobal.clear();
            const btnPausa = document.getElementById('btn-pausar-sel');
            if (btnPausa) btnPausa.innerText = `⏸ Pausar Seleccionados`;
            cargarManagerML(0);
        }
        
        async function cambiarEstadoMasivo(nuevoEstado) {
            const cuenta = document.getElementById('manager-cuenta-select').value;
            const ids = Array.from(seleccionadosGlobal);
            
            if (ids.length === 0) return alert("Selecciona al menos 1 artículo. (Puedes seleccionarlos en varias páginas)");
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
                    seleccionadosGlobal.clear();
                    cargarManagerML(paginaActual);
                }
            } catch(e) {
                alert("Error de red.");
            }
        }
        
        async function guardarCambiosInline() {
            const cuenta = document.getElementById('manager-cuenta-select').value;
            const inputsTitle = document.querySelectorAll('.inline-title');
            
            let itemsCambiados = [];
            inputsTitle.forEach(inp => {
                let id = inp.getAttribute('data-id');
                let nuevoTitulo = inp.value;
                let priceNode = document.querySelector(`.inline-price[data-id="${id}"]`);
                let nuevoPrecio = priceNode ? priceNode.value : 0;
                
                let original = itemsOriginales[id];
                if (original.title !== nuevoTitulo || original.price != nuevoPrecio) {
                    itemsCambiados.push({id: id, title: nuevoTitulo, price: nuevoPrecio});
                }
            });
            
            if (itemsCambiados.length === 0) return alert("No has modificado ningún título o precio en esta página.");
            if (!confirm(`¿Guardar cambios en ${itemsCambiados.length} artículos en Mercado Libre?`)) return;
            
            try {
                const res = await fetch('/api/manager/actualizar-items', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cuenta: cuenta, items: itemsCambiados})
                });
                const data = await res.json();
                if (data.error) alert(data.error);
                else {
                    let msg = `Éxitos: ${data.exitos}\\nErrores: ${data.errores}`;
                    if (data.detalles && data.detalles.length) msg += `\\nDetalles: ${data.detalles.join(", ")}`;
                    alert(msg);
                    cargarManagerML(paginaActual);
                }
            } catch(e) {
                alert("Error guardando cambios.");
            }
        }
        
        function importarExcelManager() {
            document.getElementById('manager-excel-upload').click();
        }
        
        async function procesarExcelManager(input) {
            if (!input.files || input.files.length === 0) return;
            const file = input.files[0];
            const cuenta = document.getElementById('manager-cuenta-select').value;
            const filtro = document.getElementById('manager-filtro-estado').value;
            
            if (!cuenta) return alert("Selecciona una cuenta primero.");
            
            const fd = new FormData();
            fd.append("cuenta", cuenta);
            fd.append("filtro_estado", filtro);
            fd.append("file", file);
            
            input.value = "";
            alert("Analizando Excel y cruzando con la Memoria ERP...");
            
            try {
                const res = await fetch('/api/manager/seleccionar-por-excel', {
                    method: 'POST',
                    body: fd
                });
                const data = await res.json();
                if (data.error) return alert(data.error);
                
                let count = 0;
                data.ids.forEach(id => {
                    seleccionadosGlobal.add(id);
                    count++;
                });
                
                alert(`¡Se seleccionaron ${count} artículos automáticamente basados en tu Excel! Navega por las páginas y verás sus casillas marcadas.`);
                cargarManagerML(paginaActual);
            } catch(e) {
                alert("Error leyendo archivo.");
            }
        }

        function cerrarModalIAManager() {
            document.getElementById('modal-ia-manager').style.display = 'none';
        }

        async function repararProblemasIA() {
            const cuenta = document.getElementById('manager-cuenta-select').value;
            const ids = Array.from(seleccionadosGlobal);
            if (ids.length === 0) return alert("Selecciona al menos 1 artículo con infracción.");
            
            let itemsPayload = [];
            ids.forEach(id => {
                let row = document.getElementById(`row-${id}`);
                if (row) {
                    let title = row.querySelector('.inline-title').value;
                    let priceNode = row.querySelector('.inline-price');
                    let price = priceNode ? priceNode.value : 0;
                    let badge = row.querySelector('span[title]');
                    let infraccion = badge ? badge.getAttribute('title') : 'Desconocido';
                    itemsPayload.push({id: id, title: title, price: price, infraccion: infraccion});
                }
            });
            
            if (itemsPayload.length === 0) return alert("No se encontraron los datos en esta página. (Por favor repara los artículos de página en página).");
            
            document.getElementById('modal-ia-manager').style.display = 'flex';
            document.getElementById('ia-manager-loading').style.display = 'block';
            document.getElementById('ia-manager-content').style.display = 'none';
            document.getElementById('ia-manager-footer').style.display = 'none';
            
            try {
                const res = await fetch('/api/ia/analizar-infracciones', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cuenta: cuenta, items: itemsPayload})
                });
                const data = await res.json();
                
                if (data.error) {
                    alert(data.error);
                    cerrarModalIAManager();
                    return;
                }
                
                document.getElementById('ia-manager-log').innerText = data.log;
                
                let tbody = document.getElementById('ia-manager-sugerencias-tbody');
                tbody.innerHTML = "";
                ultimasSugerenciasIA = data.sugerencias || [];
                
                ultimasSugerenciasIA.forEach(sug => {
                    tbody.innerHTML += `
                        <tr>
                            <td style="font-weight:bold; color:#2563eb;">${sug.id}</td>
                            <td>${sug.nuevo_titulo}</td>
                            <td>$${sug.nuevo_precio}</td>
                        </tr>
                    `;
                });
                
                document.getElementById('ia-manager-loading').style.display = 'none';
                document.getElementById('ia-manager-content').style.display = 'block';
                document.getElementById('ia-manager-footer').style.display = 'flex';
                
            } catch(e) {
                alert("Error de red contactando a la IA.");
                cerrarModalIAManager();
            }
        }
        
        function aplicarSugerenciasIA() {
            if (!modoEdicion) toggleModoEdicion();
            
            ultimasSugerenciasIA.forEach(sug => {
                let inputT = document.querySelector(`.inline-title[data-id="${sug.id}"]`);
                let inputP = document.querySelector(`.inline-price[data-id="${sug.id}"]`);
                if (inputT) {
                    inputT.value = sug.nuevo_titulo;
                    inputT.style.border = "2px solid #10b981"; 
                    inputT.style.background = "#ecfdf5";
                }
                if (inputP) {
                    inputP.value = sug.nuevo_precio;
                    inputP.style.border = "2px solid #10b981";
                    inputP.style.background = "#ecfdf5";
                }
            });
            cerrarModalIAManager();
            alert("¡Sugerencias aplicadas en la tabla! Revisa que estén correctas y dale a 'Guardar Cambios en ML'.");
        }
"""

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx_start = content.find('let paginaActual = 0;')
idx_end = content.find('function mostrarSeccion(idSeccion, el) {')

if idx_start != -1 and idx_end != -1:
    old_block = content[idx_start:idx_end]
    content = content.replace(old_block, payload_js + '\n        ')
    with open('app_web.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("RESTORED JS")
else:
    print("NOT FOUND")
