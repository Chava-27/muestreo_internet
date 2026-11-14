"""
Servicio de infraestructura encargado de interactuar con la interfaz de red
del sistema operativo y ejecutar las pruebas de ancho de banda.
"""

import importlib.util
import subprocess
import sys
from typing import Dict, Tuple

if importlib.util.find_spec("speedtest") is None:
    print("[Error Crítico] La librería 'speedtest-cli' no está instalada.")
    print("Ejecuta 'pip install -r requirements.txt' o utiliza el archivo ejecutar.bat.")
    sys.exit(1)

import speedtest


class NetworkService:
    """Provee métodos estáticos para consultar el estado físico y lógico de la red."""

    @staticmethod
    def obtener_info_wi_fi() -> Tuple[str, int, str]:
        """
        Consulta mediante comandos nativos de Windows los detalles de la interfaz Wi-Fi.

        Returns:
            Tuple[str, int, str]: Una tupla con (ssid_actual, porcentaje_senal, tipo_conexion).
        """
        ssid = "Desconocido"
        senal = 0
        tipo = "Ethernet / Cable"

        try:
            resultado = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            )
            ssid, senal, tipo = NetworkService._parsear_salida_netsh(resultado.stdout)
        except Exception:
            pass

        return ssid, senal, tipo

    @staticmethod
    def _parsear_salida_netsh(salida_consola: str) -> Tuple[str, int, str]:
        """
        Extrae el SSID y el porcentaje de señal desde el texto crudo de netsh.

        Args:
            salida_consola: Texto devuelto por 'netsh wlan show interfaces'.

        Returns:
            Tuple[str, int, str]: (ssid, senal, tipo_conexion).
        """
        ssid = "Desconocido"
        senal = 0
        tipo = "Ethernet / Cable"

        for linea in salida_consola.splitlines():
            linea_limpia = linea.strip()
            if "SSID" in linea_limpia and "BSSID" not in linea_limpia:
                partes = linea_limpia.split(":", 1)
                if len(partes) > 1 and partes[1].strip():
                    ssid = partes[1].strip()
                    tipo = "Wi-Fi"
            elif "Señal" in linea_limpia or "Signal" in linea_limpia:
                partes = linea_limpia.split(":", 1)
                if len(partes) > 1:
                    valor_senal = partes[1].strip().replace("%", "")
                    if valor_senal.isdigit():
                        senal = int(valor_senal)

        return ssid, senal, tipo

    @staticmethod
    def ejecutar_test_velocidad() -> Dict[str, any]:
        """
        Ejecuta una prueba completa contra el mejor servidor Speedtest disponible.

        Returns:
            Dict[str, any]: Diccionario con proveedor, bajada, subida, promedio y ping.
        """
        cliente_speedtest = speedtest.Speedtest()
        cliente_speedtest.get_best_server()

        bajada_mbps = round(cliente_speedtest.download() / 1_000_000, 2)
        subida_mbps = round(cliente_speedtest.upload() / 1_000_000, 2)
        promedio_mbps = round((bajada_mbps + subida_mbps) / 2, 2)

        return {
            "proveedor_servicio": cliente_speedtest.results.client.get("isp", "Desconocido"),
            "velocidad_bajada_mbps": bajada_mbps,
            "velocidad_subida_mbps": subida_mbps,
            "velocidad_promedio_mbps": promedio_mbps,
            "ping_ms": round(cliente_speedtest.results.ping, 2),
        }