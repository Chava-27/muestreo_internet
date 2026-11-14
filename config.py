import os

# Rutas base del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "salidas")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "resultado.csv")

# Configuración del muestreo (en segundos)
INTERVALO_SEGUNDOS = 10

# Cabeceras estándar para el dataset
CSV_HEADERS = [
    "timestamp",
    "modo_monitoreo",
    "proveedor_servicio",
    "ssid_objetivo",
    "ssid_actual",
    "tiempo_registro_s",
    "velocidad_promedio_mbps",
    "velocidad_subida_mbps",
    "velocidad_bajada_mbps",
    "ping_ms"
]