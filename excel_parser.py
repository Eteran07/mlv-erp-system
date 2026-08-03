import pandas as pd
import re

def limpiar_precio(val):
    try:
        if pd.isna(val):
            return 1.0
        s = str(val).replace('$', '').replace('USD', '').replace('usd', '').strip()
        if not s or s.lower() == 'nan':
            return 1.0
        
        if '.' in s and ',' in s:
            if s.rfind(',') > s.rfind('.'):
                s = s.replace('.', '').replace(',', '.')
            else:
                s = s.replace(',', '')
        elif ',' in s:
            s = s.replace(',', '.')
            
        val_float = float(s)
        return max(1.0, val_float) if val_float > 0 else 1.0
    except Exception as e:
        print(f"Aviso - No se pudo parsear precio '{val}', asignando 1.0: {e}")
        return 1.0

def limpiar_codigo(val):
    if pd.isna(val):
        return ""
    txt = str(val).strip()
    if txt.lower() == 'nan':
        return ""
    if txt.endswith('.0'):
        txt = txt[:-2]
    return txt

def obtener_encabezados_excel(temp_filename, hoja_objetivo="TODAS"):
    try:
        if temp_filename.lower().endswith(".csv"):
            df = pd.read_csv(temp_filename, nrows=10, header=None, encoding='utf-8', sep=None, engine='python')
        else:
            with pd.ExcelFile(temp_filename) as xls:
                hoja = xls.sheet_names[0] if hoja_objetivo == "TODAS" else hoja_objetivo
                df = xls.parse(hoja, nrows=10, header=None)
        
        palabras_header = ["codigo", "código", "sku", "producto", "descripcion", "descripción", "precio", "marca", "categoria", "nombre", "stock", "modelo", "linea", "garantia", "pvp", "$"]
        mejor_fila = 0
        max_coincidencias = -1
        for i in range(len(df)):
            vals = [str(val).lower().strip() for val in df.iloc[i].tolist() if pd.notna(val)]
            coincidencias = sum(1 for w in palabras_header if any(w in v for v in vals))
            if coincidencias > max_coincidencias and coincidencias >= 2:
                max_coincidencias = coincidencias
                mejor_fila = i
                
        # Fusión multi-fila para encabezados divididos (como en tu hoja LISTA DROP)
        headers_combinados = []
        num_cols = len(df.columns)
        for c in range(num_cols):
            v1 = str(df.iloc[mejor_fila, c]).strip() if pd.notna(df.iloc[mejor_fila, c]) else ""
            v2 = str(df.iloc[mejor_fila + 1, c]).strip() if mejor_fila + 1 < len(df) and pd.notna(df.iloc[mejor_fila + 1, c]) else ""
            if v1.lower() in ['nan', 'undefined']: v1 = ""
            if v2.lower() in ['nan', 'undefined']: v2 = ""
            
            if not v1 and v2:
                headers_combinados.append(v2)
            elif v1 and v2 and any(k in v2.lower() for k in ['precio', '$', 'pvp', 'stock', 'sku', 'codigo', 'código', 'modelo']):
                headers_combinados.append(f"{v1} {v2}".strip())
            elif v1:
                headers_combinados.append(v1)
            elif v2:
                headers_combinados.append(v2)
            else:
                headers_combinados.append(f"Col_{c+1}")
                
        return headers_combinados
    except Exception:
        return []

def obtener_vista_previa_excel(temp_filename):
    vistas = []
    try:
        if temp_filename.lower().endswith(".csv"):
            df = pd.read_csv(temp_filename, nrows=12, header=None, encoding='utf-8', sep=None, engine='python')
            filas_limpias = []
            for _, row in df.iterrows():
                filas_limpias.append([str(val) if pd.notna(val) else "" for val in row.tolist()])
            vistas.append({
                "nombre": "CSV (Hoja Única)",
                "filas": filas_limpias
            })
        else:
            with pd.ExcelFile(temp_filename) as xls:
                for nom_hoja in xls.sheet_names:
                    df = xls.parse(nom_hoja, nrows=10, header=None)
                    filas_limpias = []
                    for _, row in df.iterrows():
                        filas_limpias.append([str(val) if pd.notna(val) else "" for val in row.tolist()])
                    vistas.append({
                        "nombre": nom_hoja,
                        "filas": filas_limpias
                    })
    except Exception as e:
        print(f"Error generando vista previa: {e}")
    return vistas

def buscar_col_manual(nombre_req, columnas):
    if not nombre_req:
        return None
    req_limpio = re.sub(r'\s+', ' ', str(nombre_req).strip().lower())
    for c in columnas:
        c_limpio = re.sub(r'\s+', ' ', str(c).strip().lower())
        if c_limpio == req_limpio or req_limpio in c_limpio or c_limpio in req_limpio:
            return c
    return None

def procesar_excel_heuristico(temp_filename, hoja_objetivo="TODAS", filtro_especialidad="TODO", mapa_manual=None):
    filas_extraidas = []
    
    if temp_filename.lower().endswith(".csv"):
        hojas_data = {"CSV": pd.read_csv(temp_filename, header=None, encoding='utf-8', sep=None, engine='python')}
    else:
        with pd.ExcelFile(temp_filename) as xls:
            nombres_hojas = xls.sheet_names if hoja_objetivo == "TODAS" else [hoja_objetivo]
            hojas_data = {nombre: xls.parse(nombre, header=None) for nombre in nombres_hojas if nombre in xls.sheet_names}

    palabras_header = ["codigo", "código", "sku", "producto", "descripcion", "descripción", "precio", "marca", "categoria", "nombre", "stock", "modelo", "linea", "garantia", "pvp", "$"]

    BASURA_PROHIBIDA = {
        "descripción del artículo", "descripcion del articulo", "producto", "titulo", "título",
        "lista de precios", "codigo", "código", "sku", "modelo", "linea", "línea",
        "garantia", "garantía", "precio", "precios", "stock", "disponibilidad", "total", "subtotal"
    }

    for nom_hoja, df_raw in hojas_data.items():
        if df_raw.empty:
            continue
        
        mejor_fila = -1
        max_coincidencias = -1
        for i in range(min(15, len(df_raw))):
            valores_fila = [str(val).lower().strip() for val in df_raw.iloc[i].tolist() if pd.notna(val)]
            coincidencias = sum(1 for w in palabras_header if any(w in v for v in valores_fila))
            if coincidencias > max_coincidencias and coincidencias >= 2:
                max_coincidencias = coincidencias
                mejor_fila = i
        
        if mejor_fila == -1:
            continue

        # Fusión multi-fila para que no se pierdan columnas como PRECIO $ ML
        headers_combinados = []
        num_cols = len(df_raw.columns)
        for c in range(num_cols):
            v1 = str(df_raw.iloc[mejor_fila, c]).strip() if pd.notna(df_raw.iloc[mejor_fila, c]) else ""
            v2 = str(df_raw.iloc[mejor_fila + 1, c]).strip() if mejor_fila + 1 < len(df_raw) and pd.notna(df_raw.iloc[mejor_fila + 1, c]) else ""
            if v1.lower() in ['nan', 'undefined']: v1 = ""
            if v2.lower() in ['nan', 'undefined']: v2 = ""
            
            if not v1 and v2:
                headers_combinados.append(v2)
            elif v1 and v2 and any(k in v2.lower() for k in ['precio', '$', 'pvp', 'stock', 'sku', 'codigo', 'código', 'modelo']):
                headers_combinados.append(f"{v1} {v2}".strip())
            elif v1:
                headers_combinados.append(v1)
            elif v2:
                headers_combinados.append(v2)
            else:
                headers_combinados.append(f"Col_{c+1}")

        df_data = df_raw.iloc[mejor_fila + 1:].copy()
        df_data.columns = headers_combinados

        col_sku, col_mod, col_tit, col_pre, col_mar, col_stk, col_cat = None, None, None, None, None, None, None
        
        if mapa_manual and isinstance(mapa_manual, dict):
            col_tit = buscar_col_manual(mapa_manual.get("tit"), df_data.columns)
            col_sku = buscar_col_manual(mapa_manual.get("sku"), df_data.columns)
            col_mod = buscar_col_manual(mapa_manual.get("mod"), df_data.columns)
            col_pre = buscar_col_manual(mapa_manual.get("pre"), df_data.columns)
            col_stk = buscar_col_manual(mapa_manual.get("stk"), df_data.columns)
            col_mar = buscar_col_manual(mapa_manual.get("mar"), df_data.columns)
            col_cat = buscar_col_manual(mapa_manual.get("cat"), df_data.columns)

        for col in df_data.columns:
            cl = str(col).lower().strip()
            if not col_sku and any(k in cl for k in ['sku', 'código zmart', 'codigo zmart', 'código', 'codigo', 'part number', 'nro parte']):
                col_sku = col
            elif not col_mod and any(k in cl for k in ['modelo', 'model']):
                col_mod = col
            elif not col_tit and any(k in cl for k in ['nombre del producto', 'producto', 'titulo', 'título', 'descripcion', 'descripción', 'nombre']):
                col_tit = col
            elif not col_pre and any(k in cl for k in ['precio', 'pvp', 'costo', 'price', 'usd', '$', 'precios']):
                col_pre = col
            elif not col_mar and any(k in cl for k in ['marca', 'brand', 'fabricante']):
                col_mar = col
            elif not col_stk and any(k in cl for k in ['stock', 'disponibilidad', 'existencia', 'disponible', 'cant']):
                col_stk = col
            elif not col_cat and any(k in cl for k in ['categoria', 'categoría', 'rubro', 'línea', 'linea']):
                col_cat = col

        categoria_banda_actual = "GENERAL"

        for _, row in df_data.iterrows():
            primera_celda = str(row.iloc[0]).strip() if len(row) > 0 and pd.notna(row.iloc[0]) else ""
            if "categoria:" in primera_celda.lower() or "categoría:" in primera_celda.lower():
                categoria_banda_actual = re.sub(r'(?i)categor[ií]a:\s*', '', primera_celda).split('(')[0].strip()
                continue

            tit_val = str(row[col_tit]).strip() if col_tit and pd.notna(row[col_tit]) else ""
            
            if not tit_val or tit_val.lower() == "nan" or len(tit_val) < 4:
                continue
            if tit_val.lower().strip() in BASURA_PROHIBIDA:
                continue

            sku_val = limpiar_codigo(row[col_sku]) if col_sku else ""
            mod_val = limpiar_codigo(row[col_mod]) if col_mod else ""
            
            if sku_val.lower().strip() in BASURA_PROHIBIDA or mod_val.lower().strip() in BASURA_PROHIBIDA:
                continue

            if not sku_val and mod_val: sku_val = mod_val
            if not mod_val and sku_val: mod_val = sku_val
            if not sku_val and not mod_val:
                sku_val = "Universal"
                mod_val = "Universal"

            pre_val = limpiar_precio(row[col_pre]) if col_pre else 1.0

            stk_val = 5
            if col_stk and pd.notna(row[col_stk]):
                s_txt = str(row[col_stk]).upper().strip()
                if any(w in s_txt for w in ["INMEDIATA", "DISPONIBLE", "SI", "YES", "OK"]):
                    stk_val = 5
                else:
                    try: stk_val = max(1, int(float(s_txt)))
                    except Exception: stk_val = 5

            mar_val = str(row[col_mar]).strip() if col_mar and pd.notna(row[col_mar]) else "Generico"
            if mar_val.lower() == "nan" or not mar_val: mar_val = "Generico"

            cat_linea = str(row[col_cat]).strip() if col_cat and pd.notna(row[col_cat]) else categoria_banda_actual
            if cat_linea.lower() == "nan" or not cat_linea: cat_linea = categoria_banda_actual

            if filtro_especialidad != "TODO":
                texto_analisis = f"{tit_val} {cat_linea}".lower()
                if filtro_especialidad == "COMPUTACION" and not any(k in texto_analisis for k in ["laptop", "aspire", "notebook", "pc", "core", "ryzen", "portátil", "portatil", "intel", "amd"]): continue
                elif filtro_especialidad == "MONITORES" and not any(k in texto_analisis for k in ["monitor", "pantalla", "display", "aoc", "144hz", "ips", "vga", "hdmi"]): continue
                elif filtro_especialidad == "ACCESORIOS" and not any(k in texto_analisis for k in ["teclado", "mouse", "argomtech", "logitech", "aro de luz", "cable", "adaptador", "auricular", "gel"]): continue
                elif filtro_especialidad == "REDES" and not any(k in texto_analisis for k in ["access point", "router", "switch", "wi-fi", "wifi", "red", "ethernet", "tplink"]): continue

            filas_extraidas.append({
                "SKU": sku_val,
                "Modelo": mod_val,
                "Titulo": tit_val,
                "Precio": pre_val,
                "Stock": stk_val,
                "Marca": mar_val,
                "CategoriaOrigen": cat_linea,
                "Hoja": nom_hoja
            })

    return filas_extraidas