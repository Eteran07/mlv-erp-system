import pandas as pd
import re

def limpiar_precio(val):
    """
    Convierte cualquier formato de precio de Excel/CSV ($120,50 | 1.234,56 | 120.50 | USD 45)
    en un número flotante limpio sin caer en 1.0 por error.
    """
    try:
        if pd.isna(val):
            return 1.0
        s = str(val).replace('$', '').replace('USD', '').replace('usd', '').strip()
        if not s or s.lower() == 'nan':
            return 1.0
        
        # Manejo inteligente de miles y decimales (ej: 1.234,56 vs 1,234.56 vs 120,50)
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
    """
    Evita que códigos numéricos en Excel terminen con '.0' al final (ej: 201836.0 -> 201836).
    """
    if pd.isna(val):
        return ""
    txt = str(val).strip()
    if txt.lower() == 'nan':
        return ""
    if txt.endswith('.0'):
        txt = txt[:-2]
    return txt

def procesar_excel_heuristico(temp_filename, hoja_objetivo="TODAS", filtro_especialidad="TODO"):
    filas_extraidas = []
    
    if temp_filename.lower().endswith(".csv"):
        hojas_data = {"CSV": pd.read_csv(temp_filename, header=None, encoding='utf-8', sep=None, engine='python')}
    else:
        with pd.ExcelFile(temp_filename) as xls:
            nombres_hojas = xls.sheet_names if hoja_objetivo == "TODAS" else [hoja_objetivo]
            hojas_data = {nombre: xls.parse(nombre, header=None) for nombre in nombres_hojas if nombre in xls.sheet_names}

    palabras_header = [
        "codigo", "código", "sku", "producto", "descripcion", "descripción", 
        "precio", "marca", "categoria", "nombre", "stock", "disponible", 
        "pvp", "costo", "modelo", "part number"
    ]

    for nom_hoja, df_raw in hojas_data.items():
        if df_raw.empty:
            continue
        
        # 1. Encontrar la fila que tenga MÁS coincidencias con encabezados reales (evita títulos del banner)
        mejor_fila = -1
        max_coincidencias = 0
        for i in range(min(20, len(df_raw))):
            valores_fila = [str(val).lower().strip() for val in df_raw.iloc[i].tolist() if pd.notna(val)]
            coincidencias = sum(1 for w in palabras_header if any(w in v for v in valores_fila))
            if coincidencias > max_coincidencias and coincidencias >= 2:
                max_coincidencias = coincidencias
                mejor_fila = i
        
        if mejor_fila == -1:
            continue

        headers = [str(c).strip() for c in df_raw.iloc[mejor_fila].tolist()]
        df_data = df_raw.iloc[mejor_fila + 1:].copy()
        df_data.columns = headers

        # 2. Detección de columnas separando SKU de MODELO y cubriendo precios venezolanos
        col_sku, col_mod, col_tit, col_pre, col_mar, col_stk, col_cat = None, None, None, None, None, None, None
        
        for col in df_data.columns:
            cl = str(col).lower().strip()
            # SKU / Código de parte / Código Zmart
            if any(k in cl for k in ['sku', 'código zmart', 'codigo zmart', 'código', 'codigo', 'part number', 'nro parte', 'nro. parte', 'cod', 'referencia']):
                if not col_sku: col_sku = col
            # Modelo independiente
            elif any(k in cl for k in ['modelo', 'model']):
                if not col_mod: col_mod = col
            # Título / Producto
            elif any(k in cl for k in ['nombre del producto', 'producto', 'titulo', 'título', 'descripcion', 'descripción', 'nombre', 'detalle']):
                if not col_tit: col_tit = col
            # Precio ($ | USD | PVP | Costo)
            elif any(k in cl for k in ['precio', 'pvp', 'costo', 'price', 'usd', '$', 'monto', 'valor', 'p.v.p']):
                if not col_pre: col_pre = col
            # Marca
            elif any(k in cl for k in ['marca', 'brand', 'fabricante']):
                if not col_mar: col_mar = col
            # Stock
            elif any(k in cl for k in ['stock', 'disponibilidad', 'existencia', 'disponible', 'cant', 'qty']):
                if not col_stk: col_stk = col
            # Categoría
            elif any(k in cl for k in ['categoria', 'categoría', 'rubro', 'línea', 'linea', 'grupo']):
                if not col_cat: col_cat = col

        categoria_banda_actual = "GENERAL"

        for _, row in df_data.iterrows():
            primera_celda = str(row.iloc[0]).strip() if len(row) > 0 and pd.notna(row.iloc[0]) else ""
            
            if "categoria:" in primera_celda.lower() or "categoría:" in primera_celda.lower():
                categoria_banda_actual = re.sub(r'(?i)categor[ií]a:\s*', '', primera_celda).split('(')[0].strip()
                continue

            tit_val = str(row[col_tit]).strip() if col_tit and pd.notna(row[col_tit]) else ""
            if not tit_val or tit_val.lower() == "nan" or len(tit_val) < 4:
                continue

            # Extracción limpia de SKU y Modelo
            sku_val = limpiar_codigo(row[col_sku]) if col_sku else ""
            mod_val = limpiar_codigo(row[col_mod]) if col_mod else ""
            
            if not sku_val and mod_val:
                sku_val = mod_val
            if not mod_val and sku_val:
                mod_val = sku_val
            if not sku_val and not mod_val:
                sku_val = "Universal"
                mod_val = "Universal"

            # Extracción limpia del precio
            pre_val = limpiar_precio(row[col_pre]) if col_pre else 1.0

            # Extracción limpia del stock
            stk_val = 5
            if col_stk and pd.notna(row[col_stk]):
                s_txt = str(row[col_stk]).upper().strip()
                if any(w in s_txt for w in ["INMEDIATA", "DISPONIBLE", "SI", "YES", "OK"]):
                    stk_val = 5
                else:
                    try:
                        stk_val = max(1, int(float(s_txt)))
                    except Exception:
                        stk_val = 5

            mar_val = str(row[col_mar]).strip() if col_mar and pd.notna(row[col_mar]) else "Generico"
            if mar_val.lower() == "nan" or not mar_val:
                mar_val = "Generico"

            cat_linea = str(row[col_cat]).strip() if col_cat and pd.notna(row[col_cat]) else categoria_banda_actual
            if cat_linea.lower() == "nan" or not cat_linea:
                cat_linea = categoria_banda_actual

            # Filtro por Especialidad en la interfaz
            if filtro_especialidad != "TODO":
                texto_analisis = f"{tit_val} {cat_linea}".lower()
                if filtro_especialidad == "COMPUTACION":
                    if not any(k in texto_analisis for k in ["laptop", "aspire", "notebook", "pc", "core", "ryzen", "portátil", "portatil", "intel", "amd"]):
                        continue
                elif filtro_especialidad == "MONITORES":
                    if not any(k in texto_analisis for k in ["monitor", "pantalla", "display", "aoc", "144hz", "ips", "vga", "hdmi"]):
                        continue
                elif filtro_especialidad == "ACCESORIOS":
                    if not any(k in texto_analisis for k in ["teclado", "mouse", "argomtech", "logitech", "aro de luz", "cable", "adaptador", "auricular", "gel"]):
                        continue
                elif filtro_especialidad == "REDES":
                    if not any(k in texto_analisis for k in ["access point", "router", "switch", "wi-fi", "wifi", "red", "ethernet", "tplink"]):
                        continue

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