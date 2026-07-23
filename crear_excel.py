import pandas as pd

# Creamos los datos de prueba exactos que necesitamos
datos = {
    "Titulo": ["Toner Maxiprint Compatible Xerox B205/B210/B215 106R04348"],
    "Precio": [15.0],
    "Stock": [10],
    "Imagen": ["https://http2.mlstatic.com/D_NQ_NP_908358-MLV52220490945_102022-O.webp"] # Imagen de prueba real de ML
}

# Convertimos a formato tabla y guardamos como Excel
df = pd.DataFrame(datos)
df.to_excel("inventario.xlsx", index=False)
print("✅ Archivo 'inventario.xlsx' creado exitosamente en tu carpeta.")