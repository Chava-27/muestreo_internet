"""
Módulo orquestador de la lógica de negocio para el monitoreo continuo de red.
Incluye efectos visuales de carga en consola y gestión de flujos.
"""

import sys
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
    y almacenamiento de telemetría con una interfaz de consola dinámica.
    """

    def __init__(self) -> None:
        self.modo: str = "Automático"
        self.ssid_objetivo: str = "Red Activa Dinámica"

    def configurar_modo(self) -> None:
        """Despliega el menú interactivo en consola para seleccionar el modo de monitoreo."""
        print("========================================================")
        print("           SISTEMA DE TELEMETRÍA DE RED v2.1            ")
        print("========================================================")
        print(" [1] Modo Automático (Red conectada actual)")
        print(" [2] Modo Manual    (Fijar red objetivo)")
        print("--------------------------------------------------------")

        opcion = input(" Selecciona una opción [1/2]: ").strip()

        if opcion == "2":
            self._configurar_modo_manual()
        else:
            self.modo = "Automático"
            self.ssid_objetivo = "Red Activa Dinámica"

    def _configurar_modo_manual(self) -> None:
        """Solicita al usuario el nombre de la red objetivo para el modo manual."""
        print("\n--- Configuración Modo Manual ---")
        red_actual, _, _ = NetworkService.obtener_info_wi_fi()
        print(f" Red detectada actualmente: {red_actual}")
        red_manual = input(
            " Ingresa el nombre exacto de la red a monitorear (o ENTER para usar la actual): "
        ).strip()

        self.modo = "Manual"
        self.ssid_objetivo = red_manual if red_manual else red_actual

    @staticmethod
    def _evaluar_estado_conexion(ping_ms: float, bajada_mbps: float) -> Tuple[str, str]:
        """Diagnostica la estabilidad de la conexión en base a umbrales configurados."""
        if bajada_mbps == 0:
            return "Caída detectada", "Sin flujo de descarga"
        if ping_ms > UMBRAL_PING_INESTABLE_MS or bajada_mbps < UMBRAL_BAJADA_MINIMA_MBPS:
            return "Inestable", "Latencia elevada o velocidad baja"
        return "Estable", "Operación normal"

    @staticmethod
    def _animar_carga(mensaje: str, duracion_segundos: float = 1.5) -> None:
        """
        Muestra una animación fluida de puntos suspensivos en la misma línea de consola.
        """
        fases = [".    ", ". .  ", ". . .", "     "]
        inicio = time.time()
        idx = 0
        while time.time() - inicio < duracion_segundos:
            sys.stdout.write(f"\r {mensaje} {fases[idx % len(fases)]}")
            sys.stdout.flush()
            time.sleep(0.3)
            idx += 1
        # Limpiar la línea al terminar
        sys.stdout.write("\r" + " " * (len(mensaje) + 10) + "\r")
        sys.stdout.flush()

    def capturar_muestra(self, id_muestra: int) -> Optional[MuestraRed]:
        """Ejecuta un ciclo completo de medición y construye el objeto MuestraRed con animación."""
        inicio_medicion = time.time()
        timestamp_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Animación visual de toma de muestra
        self._animar_carga(f"Tomando muestra #{id_muestra}", duracion_segundos=1.2)

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
            sys.stdout.write(f"\r[Error] Falló la prueba de velocidad en ID #{id_muestra}: {error}\n")
            return None

    @staticmethod
    def _imprimir_resumen_limpio(muestra: MuestraRed) -> None:
        """Muestra en consola un formato limpio, moderno y estético de cada muestra registrada."""
        hora_actual = datetime.now().strftime("%H:%M:%S")
        print(f"[{hora_actual}] ✓ Muestra #{muestra.id_muestra} registrada exitosamente:")
        print(f"   ├── Red / ISP     : {muestra.ssid_actual} ({muestra.proveedor_servicio}) - Señal: {muestra.calidad_senal_porcentaje}%")
        print(f"   ├── Velocidades   : ↓ {muestra.velocidad_bajada_mbps} Mbps  |  ↑ {muestra.velocidad_subida_mbps} Mbps  |  Prom: {muestra.velocidad_promedio_mbps} Mbps")
        print(f"   └── Estado y Ping : Latencia: {muestra.ping_ms} ms  |  Estado: [{muestra.estado_conexion}]\n")

    def _esperar_siguiente_ciclo(self, inicio_ciclo: float) -> None:
        """Gestiona la pausa con una barra de progreso o conteo limpio hacia el siguiente ciclo."""
        tiempo_transcurrido = time.time() - inicio_ciclo
        tiempo_restante = INTERVALO_SEGUNDOS - tiempo_transcurrido

        if tiempo_restante > 0:
            for i in range(int(tiempo_restante), 0, -1):
                sys.stdout.write(f"\r Siguiente sondeo en {i} segundos... ")
                sys.stdout.flush()
                time.sleep(1)
            sys.stdout.write("\r" + " " * 40 + "\r") # Limpiar línea de espera
        else:
            print(f"[Aviso] El ciclo superó el intervalo de {INTERVALO_SEGUNDOS}s. Reiniciando de inmediato.\n")

    def iniciar(self) -> None:
        """Arranca el bucle continuo de muestreo con interfaz optimizada."""
        self.configurar_modo()
        StorageService.inicializar_entorno()

        print(f"\n[INFO] Modo activo     : {self.modo.upper()}")
        print(f"[INFO] Red objetivo    : {self.ssid_objetivo}")
        print(f"[INFO] Dataset destino : {OUTPUT_FILE}")
        print(f"[INFO] Frecuencia      : Cada {INTERVALO_SEGUNDOS} segundos")
        print("--------------------------------------------------------")
        print(" [!] Presiona CTRL + C en cualquier momento para detener.\n")

        try:
            while True:
                inicio_ciclo = time.time()
                id_actual = StorageService.obtener_siguiente_id()

                muestra = self.capturar_muestra(id_actual)
                if muestra:
                    StorageService.guardar_muestra(muestra)
                    self._imprimir_resumen_limpio(muestra)

                self._esperar_siguiente_ciclo(inicio_ciclo)

        except KeyboardInterrupt:
            print("\n\n[!] Monitoreo detenido por el usuario. Dataset guardado de forma segura.")