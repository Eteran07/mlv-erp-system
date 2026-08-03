import pandas as pd
import re

def procesar_excel_heuristico(temp_filename, hoja_objetivo="TODAS"):
    filas_extraidas = []
    
    if temp_filename.lower().endswith(".csv"):
        hojas_data = {"CSV": pd.read_csv(temp_filename, header=None, encoding='utf-8', sep=None, engine='python')}
    else:
        # Cierre seguro del manejador de Excel en Windows
        with pd.ExcelFile(temp_filename) as xls:
            nombres_hojas = xls.sheet_names if hoja_objetivo == "TODAS" else [hoja_objetivo]
            hojas_data = {nombre: xls.parse(nombre, header=None) for nombre in nombres_hojas if nombre in xls.sheet_names}

    palabras_header = ["codigo", "código", "sku", "producto", "descripcion", "descripción", "precio", "marca", "categoria", "nombre"]

    for nom_hoja, df_raw in hojas_data.items():
        if df_raw.empty:
            continue
        
        fila_header = -1
        for i in range(min(15, len(df_raw))):
            valores_fila = [str(val).lower().strip() for val in df_raw.iloc[i].tolist() if pd.notna(val)]
            coincidencias = sum(1 for w in palabras_header if any(w in v for v in valores_fila))
            if coincidencias >= 2:
                fila_header = i
                break
        
        if fila_header == -1:
            continue

        headers = [str(c).strip() for c in df_raw.iloc[fila_header].tolist()]
        df_data = df_raw.iloc[fila_header + 1:].copy()
        df_data.columns = headers

        col_sku, col_tit, col_pre, col_mar, col_stk, col_cat = None, None, None, None, None, None
        
        for col in df_data.columns:
            cl = str(col).lower().strip()
            if any(k in cl for k in ['codigo', 'código', 'sku', 'part number', 'nro parte']):
                if not col_sku: col_sku = col
            elif any(k in cl for k in ['nombre del producto', 'descripcion', 'descripción', 'producto', 'titulo', 'título']):
                if not col_tit: col_tit = col
            elif any(k in cl for k in ['precio$ ml', 'precio $ ml', 'precio $', 'precio', 'pvp', 'costo']):
                if not col_pre: col_pre = col
            elif any(k in cl for k in ['marca', 'brand']):
                if not col_mar: col_mar = col
            elif any(k in cl for k in ['disponibilidad', 'stock', 'cant', 'existencia', 'disponible']):
                if not col_stk: col_stk = col
            elif any(k in cl for k in ['categoria', 'categoría', 'rubro']):
                if not col_cat: col_cat = col

        categoria_banda_actual = "GENERAL"

        for _, row in df_data.iterrows():
            primera_celda = str(row.iloc[0]).strip() if len(row) > 0 and pd.notna(row.iloc[0]) else ""
            
            if "categoria:" in primera_celda.lower() or "categoría:" in primera_celda.lower():
                categoria_banda_actual = re.sub(r'(?i)categor[ií]a:\s*', '', primera_celda).split('(')[0].strip()
                continue

            sku_val = str(row[col_sku]).strip() if col_sku and pd.notna(row[col_sku]) else ""
            tit_val = str(row[col_tit]).strip() if col_tit and pd.notna(row[col_tit]) else ""

            if not tit_val or tit_val.lower() == "nan" or len(tit_val) < 4:
                continue

            try:
                pre_raw = row[col_pre] if col_pre and pd.notna(row[col_pre]) else 1.0
                pre_val = float(str(pre_raw).replace('$', '').replace(',', '').strip())
            except Exception:
                pre_val = 1.0
            pre_val = max(1.0, pre_val)

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
            if mar_val.lower() == "nan" or not mar_val: mar_val = "Generico"

            cat_linea = str(row[col_cat]).strip() if col_cat and pd.notna(row[col_cat]) else categoria_banda_actual
            if cat_linea.lower() == "nan" or not cat_linea: cat_linea = categoria_banda_actual

            filas_extraidas.append({
                "SKU": sku_val if sku_val and sku_val.lower() != "nan" else "Universal",
                "Titulo": tit_val,
                "Precio": pre_val,
                "Stock": stk_val,
                "Marca": mar_val,
                "CategoriaOrigen": cat_linea,
                "Hoja": nom_hoja
            })

    return filas_extraidas