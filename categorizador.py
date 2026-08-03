import requests
import re

CACHE_CATEGORIAS_RAIZ = []
CACHE_ADIVINADOR = {}

def obtener_categorias_raices_mlv():
    """
    Consulta en vivo la API de Mercado Libre Venezuela (MLV)
    y retorna todas las categorías principales del sitio.
    """
    global CACHE_CATEGORIAS_RAIZ
    if CACHE_CATEGORIAS_RAIZ:
        return CACHE_CATEGORIAS_RAIZ

    url = "https://api.mercadolibre.com/sites/MLV/categories"
    try:
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            CACHE_CATEGORIAS_RAIZ = res.json()
            return CACHE_CATEGORIAS_RAIZ
    except Exception as e:
        print(f"Error obteniendo categorías MLV: {e}")
    
    # Respaldo si falla internet momentáneamente
    return [
        {"id": "MLV1648", "name": "Computación"},
        {"id": "MLV1000", "name": "Electrónica, Audio y Video"},
        {"id": "MLV1051", "name": "Celulares y Teléfonos"},
        {"id": "MLV1144", "name": "Consolas y Videojuegos"},
        {"id": "MLV1574", "name": "Hogar, Muebles y Jardín"},
        {"id": "MLV1747", "name": "Accesorios para Vehículos"},
        {"id": "MLV1499", "name": "Industrias y Oficinas"},
        {"id": "MLV1276", "name": "Deportes y Fitness"}
    ]

def adivinar_categoria_y_raiz(titulo, headers):
    """
    Usa el Domain Discovery de ML para encontrar el ID exacto y el nombre de categoría.
    """
    titulo_limpio = titulo.strip()
    if titulo_limpio in CACHE_ADIVINADOR:
        return CACHE_ADIVINADOR[titulo_limpio]

    url = "https://api.mercadolibre.com/sites/MLV/domain_discovery/search"
    try:
        response = requests.get(url, headers=headers, params={"q": titulo_limpio}, timeout=5)
        if response.status_code == 200 and len(response.json()) > 0:
            info = response.json()[0]
            cat_id = info.get("category_id", "MLV-DESCONOCIDA")
            cat_name = info.get("category_name", "Categoría General")
            resultado = (cat_id, cat_name)
            CACHE_ADIVINADOR[titulo_limpio] = resultado
            return resultado
    except Exception:
        pass

    return ("MLV-DESCONOCIDA", "Categoría General")

def coincide_con_categoria_elegida(titulo, cat_id_ml, filtro_id):
    """
    Determina si un producto hace match con la categoría elegida en el menú emergente.
    """
    if filtro_id == "TODAS" or not filtro_id:
        return True

    # Coincidencia por ID de categoría ML (ej. MLV1648 para Computación)
    if filtro_id in str(cat_id_ml):
        return True

    # Coincidencia semántica por palabras clave según las principales raíces de Mercado Libre
    t_low = titulo.lower()
    mapa_palabras = {
        "MLV1648": ["laptop", "computador", "pc", "monitor", "teclado", "mouse", "aspire", "intel", "ryzen", "impresora", "tinta", "toner", "router", "access point", "switch", "disco", "ssd", "ram"],
        "MLV1000": ["audio", "video", "tv", "televisor", "corneta", "audifono", "parlante", "camara", "cámara", "led", "pantalla"],
        "MLV1051": ["celular", "telefono", "teléfono", "iphone", "samsung", "xiaomi", "cargador", "forro", "pantalla", "bateria"],
        "MLV1144": ["consola", "ps4", "ps5", "xbox", "nintendo", "control", "gamepad", "videojuego"],
        "MLV1747": ["repuesto", "freno", "motor", "aceite", "filtro", "vehiculo", "carro", "moto", "bujia"],
        "MLV1499": ["industria", "oficina", "herramienta", "seguridad", "biometrico", "peso", "balanza"]
    }

    palabras = mapa_palabras.get(filtro_id, [])
    return any(p in t_low for p in palabras)