"""
Modelos de dominio que representan las entidades de datos del monitoreo.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class InfoWifi:
    """Estado de la interfaz inalámbrica leído desde el sistema operativo."""

    ssid: str = "Desconocido"
    tipo_conexion: str = "Ethernet / Cable"
    bssid: str = ""
    banda: str = ""
    canal: str = ""
    tipo_radio: str = ""
    autenticacion: str = ""
    senal_pct: int = 0
    rssi_dbm: Optional[int] = None
    enlace_rx_mbps: Optional[float] = None
    enlace_tx_mbps: Optional[float] = None


@dataclass(frozen=True)
class ResultadoLatencia:
    """Resultado de una ráfaga de pings ICMP."""

    enviados: int
    tiempos_ms: List[float] = field(default_factory=list)

    @property
    def recibidos(self) -> int:
        return len(self.tiempos_ms)

    @property
    def perdida_pct(self) -> float:
        if self.enviados == 0:
            return 0.0
        return round((self.enviados - self.recibidos) / self.enviados * 100, 2)

    @property
    def minimo(self) -> Optional[float]:
        return min(self.tiempos_ms) if self.tiempos_ms else None

    @property
    def maximo(self) -> Optional[float]:
        return max(self.tiempos_ms) if self.tiempos_ms else None

    @property
    def promedio(self) -> Optional[float]:
        if not self.tiempos_ms:
            return None
        return round(sum(self.tiempos_ms) / len(self.tiempos_ms), 2)

    @property
    def jitter(self) -> Optional[float]:
        """Variación media absoluta entre pings consecutivos (estilo RFC 3550)."""
        if len(self.tiempos_ms) < 2:
            return None
        difs = [abs(b - a) for a, b in zip(self.tiempos_ms, self.tiempos_ms[1:])]
        return round(sum(difs) / len(difs), 2)


@dataclass(frozen=True)
class MuestraRed:
    """
    Registro individual y completo de telemetría de red.
    El orden de los campos coincide con CSV_HEADERS en config.py.
    """

    id_muestra: int
    timestamp: str
    fecha: str
    hora: str
    dia_semana: str
    franja_horaria: str
    modo_monitoreo: str
    nombre_equipo: str
    pid_proceso: int
    proveedor_servicio: str
    ip_publica: str
    ip_local: str
    ip_gateway: str
    servidor_speedtest: str
    ubicacion_servidor: str
    distancia_servidor_km: Optional[float]
    host_servidor: str
    ip_servidor: str
    puerto_servidor: Optional[int]
    ssid_objetivo: str
    ssid_actual: str
    coincide_red_objetivo: str
    tipo_conexion: str
    bssid: str
    banda_wifi: str
    canal_wifi: str
    tipo_radio: str
    autenticacion: str
    calidad_senal_porcentaje: int
    rssi_dbm: Optional[int]
    velocidad_enlace_rx_mbps: Optional[float]
    velocidad_enlace_tx_mbps: Optional[float]
    velocidad_bajada_mbps: float
    velocidad_subida_mbps: float
    velocidad_promedio_mbps: float
    ping_ms: float
    latencia_min_ms: Optional[float]
    latencia_max_ms: Optional[float]
    latencia_promedio_ms: Optional[float]
    jitter_ms: float
    perdida_paquetes_pct: float
    latencia_gateway_ms: Optional[float]
    perdida_gateway_pct: Optional[float]
    tiempo_dns_ms: Optional[float]
    datos_consumidos_mb: float
    tiempo_registro_s: float
    puntuacion_calidad: int
    clasificacion_calidad: str
    estado_conexion: str
    observaciones: str

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la instancia en un diccionario serializable para CSV (None -> vacío)."""
        return {k: ("" if v is None else v) for k, v in asdict(self).items()}
