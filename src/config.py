"""
Módulo de configuración global para el sistema de telemetría de red.
Centraliza rutas, intervalos, umbrales de evaluación y cabeceras del dataset.
"""

import os
from typing import List

VERSION: str = "3.0"

# Rutas del sistema de archivos
SRC_DIR: str = os.path.dirname(os.path.abspath(__file__))
BASE_DIR: str = os.path.dirname(SRC_DIR)
OUTPUT_DIR: str = os.path.join(BASE_DIR, "salidas")
OUTPUT_FILE: str = os.path.join(OUTPUT_DIR, "resultado.csv")

# Parámetros de muestreo
INTERVALO_SEGUNDOS: int = 2  # Pausa entre el fin de una muestra y el inicio de la siguiente
FACTOR_ESTIMACION_JITTER: float = 0.12  # Respaldo si la prueba ICMP no obtiene respuestas

# Prueba de latencia ICMP (jitter y pérdida de paquetes reales)
PING_HOST: str = "8.8.8.8"
PING_CANTIDAD: int = 8
PING_TIMEOUT_MS: int = 1000
PING_GATEWAY_CANTIDAD: int = 4  # Pings al router para separar fallas locales de fallas del ISP

# Prueba de resolución DNS
DNS_DOMINIO_PRUEBA: str = "www.google.com"
UMBRAL_DNS_LENTO_MS: float = 300.0

# Speedtest: IDs de servidores preferidos (vacío = selección automática).
# Útil si la selección automática elige servidores lejanos; los IDs se ven en speedtest.net
# o ejecutando: speedtest-cli --list
SPEEDTEST_SERVIDOR_IDS: List[int] = []
DISTANCIA_SERVIDOR_LEJANO_KM: float = 1500.0

# Umbrales heurísticos de calidad de red
UMBRAL_PING_INESTABLE_MS: float = 150.0
UMBRAL_BAJADA_MINIMA_MBPS: float = 5.0
UMBRAL_JITTER_INESTABLE_MS: float = 30.0
UMBRAL_PERDIDA_INESTABLE_PCT: float = 2.0
UMBRAL_SENAL_DEBIL_PCT: int = 40

# Referencias para la puntuación de calidad (0-100): valores que otorgan puntaje máximo
REFERENCIA_BAJADA_MBPS: float = 100.0
REFERENCIA_SUBIDA_MBPS: float = 50.0

# Esquema de columnas para el archivo CSV
CSV_HEADERS: List[str] = [
    "id_muestra",
    "timestamp",
    "fecha",
    "hora",
    "dia_semana",
    "franja_horaria",
    "modo_monitoreo",
    "nombre_equipo",
    "pid_proceso",
    "proveedor_servicio",
    "ip_publica",
    "ip_local",
    "ip_gateway",
    "servidor_speedtest",
    "ubicacion_servidor",
    "distancia_servidor_km",
    "host_servidor",
    "ip_servidor",
    "puerto_servidor",
    "ssid_objetivo",
    "ssid_actual",
    "coincide_red_objetivo",
    "tipo_conexion",
    "bssid",
    "banda_wifi",
    "canal_wifi",
    "tipo_radio",
    "autenticacion",
    "calidad_senal_porcentaje",
    "rssi_dbm",
    "velocidad_enlace_rx_mbps",
    "velocidad_enlace_tx_mbps",
    "velocidad_bajada_mbps",
    "velocidad_subida_mbps",
    "velocidad_promedio_mbps",
    "ping_ms",
    "latencia_min_ms",
    "latencia_max_ms",
    "latencia_promedio_ms",
    "jitter_ms",
    "perdida_paquetes_pct",
    "latencia_gateway_ms",
    "perdida_gateway_pct",
    "tiempo_dns_ms",
    "datos_consumidos_mb",
    "tiempo_registro_s",
    "puntuacion_calidad",
    "clasificacion_calidad",
    "estado_conexion",
    "observaciones",
]
