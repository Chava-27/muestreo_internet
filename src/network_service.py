"""
Servicio de infraestructura encargado de interactuar con la interfaz de red
del sistema operativo y ejecutar las pruebas de latencia y ancho de banda.
"""

import importlib.util
import locale
import os
import re
import socket
import subprocess
import sys
import time
import unicodedata
from typing import Dict, List, Optional

if importlib.util.find_spec("speedtest") is None:
    print("[Error Crítico] La librería 'speedtest-cli' no está instalada.")
    print("Ejecuta 'pip install -r requirements.txt' o utiliza el archivo ejecutar.bat.")
    sys.exit(1)

import speedtest

from src.config import (
    DNS_DOMINIO_PRUEBA,
    PING_CANTIDAD,
    PING_HOST,
    PING_TIMEOUT_MS,
    SPEEDTEST_SERVIDOR_IDS,
)
from src.models import InfoWifi, ResultadoLatencia

_RE_TIEMPO_PING = re.compile(r"[=<]\s*(\d+(?:[.,]\d+)?)\s*ms", re.IGNORECASE)
_RE_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def _ejecutar_comando(comando: List[str], timeout: float) -> str:
    """
    Ejecuta un comando y decodifica su salida de forma tolerante.
    Las herramientas de Windows pueden emitir UTF-8 o la página de códigos OEM
    (cp850 en español) según la consola, así que se prueban ambas.
    """
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    salida = subprocess.run(
        comando, capture_output=True, timeout=timeout, creationflags=flags
    ).stdout
    try:
        return salida.decode("utf-8")
    except UnicodeDecodeError:
        codificacion = "oem" if os.name == "nt" else locale.getpreferredencoding(False)
        return salida.decode(codificacion, errors="replace")


def _normalizar(texto: str) -> str:
    """Minúsculas y sin acentos, para comparar claves en español o inglés."""
    sin_acentos = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_acentos if not unicodedata.combining(c)).lower().strip()


def _a_float(valor: str) -> Optional[float]:
    try:
        return float(valor.replace(",", "."))
    except ValueError:
        return None


def _a_int(valor: str) -> Optional[int]:
    coincidencia = re.search(r"-?\d+", valor)
    return int(coincidencia.group()) if coincidencia else None


class NetworkService:
    """Provee métodos estáticos para consultar el estado físico y lógico de la red."""

    @staticmethod
    def obtener_info_wi_fi() -> InfoWifi:
        """Consulta 'netsh wlan show interfaces' y devuelve la interfaz conectada."""
        if os.name != "nt":
            return InfoWifi()
        try:
            salida = _ejecutar_comando(["netsh", "wlan", "show", "interfaces"], timeout=10)
        except Exception:
            return InfoWifi()
        return NetworkService._parsear_salida_netsh(salida)

    @staticmethod
    def _parsear_salida_netsh(salida_consola: str) -> InfoWifi:
        """Extrae los datos de la primera interfaz Wi-Fi conectada desde la salida de netsh."""
        interfaces: List[Dict[str, str]] = []
        actual: Dict[str, str] = {}

        for linea in salida_consola.splitlines():
            if ":" not in linea:
                continue
            clave_cruda, valor = linea.split(":", 1)
            clave = _normalizar(clave_cruda)
            valor = valor.strip()

            if clave in ("nombre", "name"):
                actual = {}
                interfaces.append(actual)
            elif clave == "ssid":
                actual["ssid"] = valor
            elif "bssid" in clave:
                actual["bssid"] = valor
            elif clave in ("banda", "band"):
                actual["banda"] = valor
            elif clave in ("canal", "channel"):
                actual["canal"] = valor
            elif clave in ("tipo de radio", "radio type"):
                actual["tipo_radio"] = valor
            elif clave.startswith("autenticaci") or clave == "authentication":
                actual["autenticacion"] = valor
            elif "recepci" in clave or "receive rate" in clave:
                actual["rx"] = valor
            elif "transmisi" in clave or "transmit rate" in clave:
                actual["tx"] = valor
            elif clave in ("senal", "signal") or (
                clave.startswith("se") and clave.endswith("al") and len(clave) <= 8
            ):
                actual["senal"] = valor
            elif clave == "rssi":
                actual["rssi"] = valor
            elif clave in ("estado", "state"):
                actual["estado"] = _normalizar(valor)

        if not interfaces and actual:
            interfaces.append(actual)

        for datos in interfaces:
            conectada = datos.get("estado", "conectado") in ("conectado", "connected")
            if conectada and datos.get("ssid"):
                return InfoWifi(
                    ssid=datos["ssid"],
                    tipo_conexion="Wi-Fi",
                    bssid=datos.get("bssid", ""),
                    banda=datos.get("banda", ""),
                    canal=datos.get("canal", ""),
                    tipo_radio=datos.get("tipo_radio", ""),
                    autenticacion=datos.get("autenticacion", ""),
                    senal_pct=_a_int(datos.get("senal", "")) or 0,
                    rssi_dbm=_a_int(datos.get("rssi", "")),
                    enlace_rx_mbps=_a_float(datos.get("rx", "")),
                    enlace_tx_mbps=_a_float(datos.get("tx", "")),
                )
        return InfoWifi()

    @staticmethod
    def obtener_gateway() -> str:
        """
        IPv4 del router, leída de ipconfig. Si hay varios adaptadores (VPN, máquinas
        virtuales), se elige el gateway que comparte subred con la IP de salida.
        """
        if os.name != "nt":
            return ""
        try:
            lineas = _ejecutar_comando(["ipconfig"], timeout=10).splitlines()
        except Exception:
            return ""

        gateways: List[str] = []
        for i, linea in enumerate(lineas):
            clave = _normalizar(linea.split(":", 1)[0])
            if "puerta de enlace" in clave or "default gateway" in clave:
                # La IPv4 puede venir en la misma línea o en las siguientes (tras una IPv6).
                for candidata in lineas[i : i + 3]:
                    ipv4 = _RE_IPV4.search(candidata)
                    if ipv4:
                        gateways.append(ipv4.group())
                        break
        if not gateways:
            return ""

        prefijo_local = NetworkService.obtener_ip_local().rsplit(".", 1)[0]
        for gateway in gateways:
            if prefijo_local and gateway.startswith(prefijo_local + "."):
                return gateway
        return gateways[0]

    @staticmethod
    def medir_dns(dominio: str = DNS_DOMINIO_PRUEBA) -> Optional[float]:
        """Milisegundos que tarda el sistema en resolver un dominio."""
        inicio = time.perf_counter()
        try:
            socket.getaddrinfo(dominio, 443, proto=socket.IPPROTO_TCP)
        except OSError:
            return None
        return round((time.perf_counter() - inicio) * 1000, 2)

    @staticmethod
    def obtener_ip_local() -> str:
        """
        IP de la interfaz que se usa para salir a internet. Un socket UDP con
        connect() solo consulta la tabla de rutas; no envía paquetes.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect((PING_HOST, 80))
                return sock.getsockname()[0]
        except OSError:
            return ""

    @staticmethod
    def medir_latencia(
        host: str = PING_HOST, cantidad: int = PING_CANTIDAD, timeout_ms: int = PING_TIMEOUT_MS
    ) -> ResultadoLatencia:
        """Envía una ráfaga de pings ICMP para calcular latencia, jitter y pérdida reales."""
        if os.name == "nt":
            comando = ["ping", "-n", str(cantidad), "-w", str(timeout_ms), host]
        else:
            comando = ["ping", "-c", str(cantidad), "-W", str(max(1, timeout_ms // 1000)), host]

        try:
            salida = _ejecutar_comando(comando, timeout=cantidad * (timeout_ms / 1000 + 1) + 5)
        except Exception:
            return ResultadoLatencia(enviados=cantidad)
        return ResultadoLatencia(
            enviados=cantidad, tiempos_ms=NetworkService._parsear_salida_ping(salida)
        )

    @staticmethod
    def _parsear_salida_ping(salida: str) -> List[float]:
        """Obtiene los tiempos de cada respuesta válida (líneas con TTL)."""
        tiempos: List[float] = []
        for linea in salida.splitlines():
            if "ttl" not in linea.lower():
                continue
            coincidencia = _RE_TIEMPO_PING.search(linea)
            if coincidencia:
                tiempos.append(float(coincidencia.group(1).replace(",", ".")))
        return tiempos


class PruebaVelocidad:
    """
    Envoltura por fases sobre speedtest-cli, para que la capa de presentación
    pueda mostrar el avance de cada etapa por separado.
    """

    def __init__(self) -> None:
        self._cliente = speedtest.Speedtest(secure=True)
        self.servidor: Dict = {}

    def seleccionar_servidor(self) -> Dict:
        if SPEEDTEST_SERVIDOR_IDS:
            self._cliente.get_servers(SPEEDTEST_SERVIDOR_IDS)
        self.servidor = self._cliente.get_best_server()
        return self.servidor

    def medir_descarga(self) -> float:
        return round(self._cliente.download() / 1_000_000, 2)

    def medir_subida(self) -> float:
        return round(self._cliente.upload(pre_allocate=False) / 1_000_000, 2)

    @property
    def ping_ms(self) -> float:
        return round(self._cliente.results.ping, 2)

    @property
    def proveedor(self) -> str:
        return self._cliente.config.get("client", {}).get("isp", "Desconocido")

    @property
    def ip_publica(self) -> str:
        return self._cliente.config.get("client", {}).get("ip", "")

    @property
    def host_servidor(self) -> str:
        """Nombre del host sin puerto (el campo 'host' de speedtest viene como 'nombre:puerto')."""
        return self.servidor.get("host", "").rsplit(":", 1)[0]

    @property
    def puerto_servidor(self) -> Optional[int]:
        host = self.servidor.get("host", "")
        if ":" in host:
            return _a_int(host.rsplit(":", 1)[1])
        return 443 if self.servidor.get("url", "").startswith("https") else 80

    @property
    def ip_servidor(self) -> str:
        try:
            return socket.gethostbyname(self.host_servidor) if self.host_servidor else ""
        except OSError:
            return ""

    @property
    def nombre_servidor(self) -> str:
        return self.servidor.get("sponsor", "")

    @property
    def ubicacion_servidor(self) -> str:
        partes = [self.servidor.get("name", ""), self.servidor.get("country", "")]
        return ", ".join(p for p in partes if p)

    @property
    def distancia_km(self) -> Optional[float]:
        distancia = self.servidor.get("d")
        return round(distancia, 1) if distancia is not None else None

    @property
    def datos_consumidos_mb(self) -> float:
        resultados = self._cliente.results
        return round((resultados.bytes_received + resultados.bytes_sent) / 1_000_000, 2)
