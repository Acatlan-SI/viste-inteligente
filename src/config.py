"""Constantes de UI y catálogos usados por el front.
NO contiene rutas de datos, modelos ni lógica ML — todo eso vive en el servicio ML.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- tipo de prenda
CLASES = ["superior", "inferior", "completo", "calzado", "otro"]
NOMBRE_CLASE = {
    "superior": "👕 Arriba",
    "inferior": "👖 Abajo",
    "completo": "👗 Completo",
    "calzado": "👟 Calzado",
    "otro": "👜 Otro",
}

# ---------------------------------------------------------------- color
COLORES = ["negro", "blanco", "gris", "beige", "café", "azul marino", "azul", "celeste",
           "turquesa", "verde", "amarillo", "naranja", "rojo", "vino", "rosa", "morado", "multicolor"]

# ---------------------------------------------------------------- patrón
PATRONES = ["liso", "rayas", "cuadros", "floral", "lunares", "animal print", "gráfico / logo", "otro estampado"]

# ---------------------------------------------------------------- ocasiones
OCASIONES = ["casual", "business_casual", "formal", "deportivo", "fiesta"]
NOMBRE_OCASION = {
    "casual": "Casual / diario",
    "business_casual": "Business casual",
    "formal": "Formal / evento",
    "deportivo": "Deportivo",
    "fiesta": "Fiesta / noche",
}

# ---------------------------------------------------------------- Mi clóset
DIAS_GUARDADO = 30
ESTILO_CSS = RAIZ / "assets" / "estilo.css"