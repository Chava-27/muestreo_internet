"""
Módulo de configuración global para el sistema de telemetría de red.
Centraliza rutas, intervalos, umbrales de evaluación y cabeceras del dataset.
"""

import os
from typing import List

# Rutas del sistema de archivos
SRC_DIR: str = os.path.dirname(os.path.abspath(__file__))
BASE_DIR: str = os.path.dirname(SRC_DIR)
OUTPUT_DIR: str = os.path.join(BASE_DIR, "salidas")
OUTPUT_FILE: str = os.path.join(OUTPUT_DIR, "resultado.csv")

# Parámetros de muestreo
INTERVALO_SEGUNDOS: int = 10
FACTOR_ESTIMACION_JITTER: float = 0.12

# Umbrales heurísticos de calidad de red
UMBRAL_PING_INESTABLE_MS: float = 150.0
UMBRAL_BAJADA_MINIMA_MBPS: float = 5.0

# Esquema de columnas para el archivo CSV
CSV_HEADERS: List[str] = [
    "id_muestra",
    "timestamp",
    "modo_monitoreo",
    "proveedor_servicio",
    "ssid_objetivo",
    "ssid_actual",
    "calidad_senal_porcentaje",
    "tipo_conexion",
    "velocidad_bajada_mbps",
    "velocidad_subida_mbps",
    "velocidad_promedio_mbps",
    "ping_ms",
    "jitter_ms",
    "perdida_paquetes_pct",
    "tiempo_registro_s",
    "estado_conexion",
    "observaciones",
]