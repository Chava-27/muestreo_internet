"""
Modelos de dominio que representan las entidades de datos del monitoreo.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class MuestraRed:
    """
    Representa un registro individual y completo de telemetría de red.

    Attributes:
        id_muestra: Identificador secuencial único de la muestra.
        timestamp: Fecha y hora exacta de captura (YYYY-MM-DD HH:MM:SS).
        modo_monitoreo: Modo de operación ('Automático' o 'Manual').
        proveedor_servicio: Nombre del ISP detectado.
        ssid_objetivo: Red objetivo configurada como referencia.
        ssid_actual: Nombre de la red Wi-Fi conectada al momento del muestreo.
        calidad_senal_porcentaje: Intensidad de señal Wi-Fi (0 a 100).
        tipo_conexion: Medio físico utilizado ('Wi-Fi' o 'Ethernet / Cable').
        velocidad_bajada_mbps: Tasa de descarga en Megabits por segundo.
        velocidad_subida_mbps: Tasa de carga en Megabits por segundo.
        velocidad_promedio_mbps: Promedio aritmético entre bajada y subida.
        ping_ms: Latencia de respuesta en milisegundos.
        jitter_ms: Variación estimada de latencia en milisegundos.
        perdida_paquetes_pct: Porcentaje de pérdida de paquetes registrada.
        tiempo_registro_s: Duración total del ciclo de medición en segundos.
        estado_conexion: Diagnóstico heurístico ('Estable', 'Inestable', 'Caída detectada').
        observaciones: Detalle textual del estado de la red.
    """

    id_muestra: int
    timestamp: str
    modo_monitoreo: str
    proveedor_servicio: str
    ssid_objetivo: str
    ssid_actual: str
    calidad_senal_porcentaje: int
    tipo_conexion: str
    velocidad_bajada_mbps: float
    velocidad_subida_mbps: float
    velocidad_promedio_mbps: float
    ping_ms: float
    jitter_ms: float
    perdida_paquetes_pct: float
    tiempo_registro_s: float
    estado_conexion: str
    observaciones: str

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la instancia del modelo en un diccionario serializable para CSV."""
        return asdict(self)