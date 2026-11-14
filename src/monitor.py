"""
Módulo orquestador de la lógica de negocio para el monitoreo continuo de red.
"""

import time
from datetime import datetime
from typing import Optional, Tuple

from src.config import (
    FACTOR_ESTIMACION_JITTER,
    INTERVALO_SEGUNDOS,
    OUTPUT_FILE,
    UMBRAL_BAJADA_MINIMA_MBPS,
    UMBRAL_PING_INESTABLE_MS,
)
from src.models import MuestraRed
from src.network_service import NetworkService
from src.storage_service import StorageService


class NetworkMonitor:
    """
    Orquesta la configuración de usuario, ejecución periódica de pruebas
    y almacenamiento de telemetría.
    """

    def __init__(self) -> None:
        self.modo: str = "Automático"
        self.ssid_objetivo: str = "Red Activa Dinámica"

    def configurar_modo(self) -> None:
        """
        Despliega el menú interactivo en consola para seleccionar el modo de monitoreo.
        """
        print("========================================")
        print("   SISTEMA AVANZADO DE MUESTREO DE RED  ")
        print("========================================")
        print("1. Modo Automático (Red conectada actual)")
        print("2. Modo Manual (Fijar red objetivo)")
        print("----------------------------------------")

        opcion = input("Selecciona una opción [1/2]: ").strip()

        if opcion == "2":
            self._configurar_modo_manual()
        else:
            self.modo = "Automático"
            self.ssid_objetivo = "Red Activa Dinámica"

    def _configurar_modo_manual(self) -> None:
        """Solicita al usuario el nombre de la red objetivo para el modo manual."""
        print("\n--- Configuración Modo Manual ---")
        red_actual, _, _ = NetworkService.obtener_info_wi_fi()
        print(f"Red detectada actualmente: {red_actual}")
        red_manual = input(
            "Ingresa el nombre exacto de la red a monitorear (o ENTER para usar la actual): "
        ).strip()

        self.modo = "Manual"
        self.ssid_objetivo = red_manual if red_manual else red_actual

    @staticmethod
    def _evaluar_estado_conexion(ping_ms: float, bajada_mbps: float) -> Tuple[str, str]:
        """
        Diagnostica la estabilidad de la conexión en base a umbrales configurados.

        Args:
            ping_ms: Latencia medida en milisegundos.
            bajada_mbps: Velocidad de descarga medida en Mbps.

        Returns:
            Tuple[str, str]: (estado_conexion, observaciones).
        """
        if bajada_mbps == 0:
            return "Caída detectada", "Sin flujo de descarga"
        if ping_ms > UMBRAL_PING_INESTABLE_MS or bajada_mbps < UMBRAL_BAJADA_MINIMA_MBPS:
            return "Inestable", "Latencia elevada o velocidad baja"
        return "Estable", "Operación normal"

    def capturar_muestra(self, id_muestra: int) -> Optional[MuestraRed]:
        """
        Ejecuta un ciclo completo de medición y construye el objeto MuestraRed.

        Args:
            id_muestra: Identificador secuencial asignado a esta captura.

        Returns:
            Optional[MuestraRed]: Instancia con los datos recolectados o None si falla la red.
        """
        inicio_medicion = time.time()
        timestamp_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ssid_actual, calidad_senal, tipo_conexion = NetworkService.obtener_info_wi_fi()

        try:
            metricas = NetworkService.ejecutar_test_velocidad()
            ping = metricas["ping_ms"]
            bajada = metricas["velocidad_bajada_mbps"]

            estado, observaciones = self._evaluar_estado_conexion(ping, bajada)
            tiempo_total = round(time.time() - inicio_medicion, 2)

            return MuestraRed(
                id_muestra=id_muestra,
                timestamp=timestamp_actual,
                modo_monitoreo=self.modo,
                proveedor_servicio=metricas["proveedor_servicio"],
                ssid_objetivo=self.ssid_objetivo,
                ssid_actual=ssid_actual,
                calidad_senal_porcentaje=calidad_senal,
                tipo_conexion=tipo_conexion,
                velocidad_bajada_mbps=bajada,
                velocidad_subida_mbps=metricas["velocidad_subida_mbps"],
                velocidad_promedio_mbps=metricas["velocidad_promedio_mbps"],
                ping_ms=ping,
                jitter_ms=round(ping * FACTOR_ESTIMACION_JITTER, 2),
                perdida_paquetes_pct=0.0,
                tiempo_registro_s=tiempo_total,
                estado_conexion=estado,
                observaciones=observaciones,
            )
        except Exception as error:
            print(f"[Error] Falló la prueba de velocidad en ID #{id_muestra}: {error}")
            return None

    @staticmethod
    def _imprimir_resumen_muestra(muestra: MuestraRed) -> None:
        """Muestra en consola un resumen legible de la muestra recién almacenada."""
        print(
            f"  -> ISP: {muestra.proveedor_servicio} | "
            f"Red: {muestra.ssid_actual} ({muestra.calidad_senal_porcentaje}% señal)"
        )
        print(
            f"  -> Bajada: {muestra.velocidad_bajada_mbps} Mbps | "
            f"Subida: {muestra.velocidad_subida_mbps} Mbps | Ping: {muestra.ping_ms} ms"
        )
        print(f"  -> Estado: [{muestra.estado_conexion}]\n")

    @staticmethod
    def _esperar_siguiente_ciclo(inicio_ciclo: float) -> None:
        """Calcula y ejecuta la pausa necesaria para respetar el intervalo configurado."""
        tiempo_transcurrido = time.time() - inicio_ciclo
        tiempo_restante = INTERVALO_SEGUNDOS - tiempo_transcurrido

        if tiempo_restante > 0:
            time.sleep(tiempo_restante)
        else:
            print(
                f"[Aviso] La prueba excedió los {INTERVALO_SEGUNDOS}s "
                f"({round(tiempo_transcurrido, 2)}s). Reiniciando ciclo...\n"
            )

    def iniciar(self) -> None:
        """Arranca el bucle continuo de muestreo hasta recibir interrupción manual."""
        self.configurar_modo()
        StorageService.inicializar_entorno()

        print(f"\n[INFO] Iniciando muestreo en MODO: {self.modo.upper()}")
        print(f"[INFO] Red objetivo / Contexto: {self.ssid_objetivo}")
        print(f"[INFO] Dataset de salida: {OUTPUT_FILE}")
        print(f"[INFO] Intervalo configurado: Cada {INTERVALO_SEGUNDOS} segundos")
        print("[!] Presiona CTRL + C en cualquier momento para detener de forma segura.\n")

        try:
            while True:
                inicio_ciclo = time.time()
                id_actual = StorageService.obtener_siguiente_id()
                hora_corta = datetime.now().strftime("%H:%M:%S")
                print(f"[{hora_corta}] Tomando muestra #{id_actual}...")

                muestra = self.capturar_muestra(id_actual)
                if muestra:
                    StorageService.guardar_muestra(muestra)
                    self._imprimir_resumen_muestra(muestra)

                self._esperar_siguiente_ciclo(inicio_ciclo)

        except KeyboardInterrupt:
            print("\n\n[!] Monitoreo detenido por el usuario. Dataset consolidado y guardado con éxito.")