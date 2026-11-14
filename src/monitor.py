"""
Módulo orquestador de la lógica de negocio para el monitoreo continuo de red.
Cada fase de la medición se muestra con su propio spinner animado y su tiempo.
"""

import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

from src.config import (
    DISTANCIA_SERVIDOR_LEJANO_KM,
    DNS_DOMINIO_PRUEBA,
    FACTOR_ESTIMACION_JITTER,
    INTERVALO_SEGUNDOS,
    OUTPUT_FILE,
    PING_GATEWAY_CANTIDAD,
    PING_HOST,
    UMBRAL_DNS_LENTO_MS,
    REFERENCIA_BAJADA_MBPS,
    REFERENCIA_SUBIDA_MBPS,
    UMBRAL_BAJADA_MINIMA_MBPS,
    UMBRAL_JITTER_INESTABLE_MS,
    UMBRAL_PERDIDA_INESTABLE_PCT,
    UMBRAL_PING_INESTABLE_MS,
    UMBRAL_SENAL_DEBIL_PCT,
    VERSION,
)
from src.console import Spinner, color, cuenta_regresiva
from src.models import InfoWifi, MuestraRed, ResultadoLatencia
from src.network_service import NetworkService, PruebaVelocidad
from src.storage_service import StorageService

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
COLOR_ESTADO = {"Estable": "verde", "Inestable": "amarillo", "Caída detectada": "rojo"}
ANCHO = 60


def _franja_horaria(hora: int) -> str:
    if hora < 6:
        return "Madrugada"
    if hora < 12:
        return "Mañana"
    if hora < 19:
        return "Tarde"
    return "Noche"


@dataclass
class _MedicionVelocidad:
    """Resultados parciales del speedtest; los campos quedan en cero si una fase falla."""

    proveedor: str = "Desconocido"
    servidor: str = ""
    ubicacion: str = ""
    distancia_km: Optional[float] = None
    ip_publica: str = ""
    host_servidor: str = ""
    ip_servidor: str = ""
    puerto_servidor: Optional[int] = None
    bajada: float = 0.0
    subida: float = 0.0
    ping: float = 0.0
    datos_mb: float = 0.0
    error: str = ""


@dataclass
class _EstadisticasSesion:
    muestras: List[MuestraRed] = field(default_factory=list)
    inicio: float = field(default_factory=time.time)


class NetworkMonitor:
    """
    Orquesta la configuración de usuario, ejecución periódica de pruebas
    y almacenamiento de telemetría con trazabilidad animada en consola.
    """

    def __init__(self) -> None:
        self.modo: str = "Automático"
        self.ssid_objetivo: str = "Red Activa Dinámica"
        self.sesion = _EstadisticasSesion()

    # ------------------------------------------------------------------ menú

    def configurar_modo(self) -> None:
        """Despliega el menú interactivo en consola para seleccionar el modo de monitoreo."""
        titulo = f"SISTEMA DE TELEMETRÍA DE RED v{VERSION}"
        print(color("═" * ANCHO, "cian"))
        print(color(titulo.center(ANCHO), "negrita"))
        print(color("═" * ANCHO, "cian"))
        print(" [1] Modo Automático (red conectada actual)")
        print(" [2] Modo Manual     (fijar red objetivo)")
        print(color("─" * ANCHO, "gris"))

        opcion = input(" Selecciona una opción [1/2]: ").strip()
        if opcion == "2":
            self._configurar_modo_manual()

    def _configurar_modo_manual(self) -> None:
        """Solicita al usuario el nombre de la red objetivo para el modo manual."""
        print(color("\n─── Configuración Modo Manual ───", "cian"))
        red_actual = NetworkService.obtener_info_wi_fi().ssid
        print(f" Red detectada actualmente: {color(red_actual, 'negrita')}")
        red_manual = input(
            " Ingresa el nombre exacto de la red a monitorear (ENTER para usar la actual): "
        ).strip()

        self.modo = "Manual"
        self.ssid_objetivo = red_manual or red_actual

    # ------------------------------------------------------------ diagnóstico

    @staticmethod
    def _evaluar_estado_conexion(
        medicion: _MedicionVelocidad, latencia: ResultadoLatencia, jitter: float, wifi: InfoWifi
    ) -> Tuple[str, str]:
        """Diagnostica la estabilidad de la conexión en base a umbrales configurados."""
        if medicion.error and latencia.recibidos == 0:
            return "Caída detectada", f"Sin conectividad: {medicion.error}"
        if medicion.bajada == 0:
            motivo = medicion.error or "Sin flujo de descarga"
            return "Caída detectada", motivo

        motivos = []
        latencia_real = NetworkMonitor._latencia_efectiva(medicion, latencia)
        if latencia_real > UMBRAL_PING_INESTABLE_MS:
            motivos.append(f"latencia alta ({latencia_real} ms)")
        if medicion.bajada < UMBRAL_BAJADA_MINIMA_MBPS:
            motivos.append(f"descarga baja ({medicion.bajada} Mbps)")
        if jitter > UMBRAL_JITTER_INESTABLE_MS:
            motivos.append(f"jitter alto ({jitter} ms)")
        if latencia.perdida_pct > UMBRAL_PERDIDA_INESTABLE_PCT:
            motivos.append(f"pérdida de paquetes ({latencia.perdida_pct}%)")
        if medicion.error:
            motivos.append(medicion.error)

        # Avisos informativos: no marcan inestabilidad por sí solos.
        avisos = []
        if wifi.tipo_conexion == "Wi-Fi" and wifi.senal_pct < UMBRAL_SENAL_DEBIL_PCT:
            avisos.append(f"señal Wi-Fi débil ({wifi.senal_pct}%)")
        if medicion.distancia_km and medicion.distancia_km > DISTANCIA_SERVIDOR_LEJANO_KM:
            avisos.append(
                f"servidor speedtest lejano ({medicion.distancia_km:.0f} km), "
                "velocidades posiblemente subestimadas"
            )

        if motivos:
            texto = "; ".join(motivos + avisos)
            return "Inestable", texto[0].upper() + texto[1:]
        return "Estable", "; ".join(["Operación normal"] + avisos)

    @staticmethod
    def _agregar_avisos_locales(
        observaciones: str,
        latencia: ResultadoLatencia,
        latencia_gw: Optional[ResultadoLatencia],
        tiempo_dns: Optional[float],
    ) -> str:
        """Indica si la falla parece estar en la red local (router/Wi-Fi) o en el proveedor."""
        avisos = []
        if latencia_gw is not None:
            if latencia_gw.recibidos == 0:
                avisos.append("el router no responde: posible falla local o Wi-Fi")
            elif latencia_gw.perdida_pct > 0 and latencia.perdida_pct > 0:
                avisos.append("hay pérdida también hacia el router: problema en la red local")
            elif latencia.perdida_pct > 0:
                avisos.append("el router responde bien: la pérdida está del lado del proveedor")
        if tiempo_dns is None:
            avisos.append("falla de resolución DNS")
        elif tiempo_dns > UMBRAL_DNS_LENTO_MS:
            avisos.append(f"DNS lento ({tiempo_dns} ms)")
        return "; ".join([observaciones] + avisos)

    @staticmethod
    def _latencia_efectiva(medicion: _MedicionVelocidad, latencia: ResultadoLatencia) -> float:
        """Prioriza la latencia ICMP real; el ping de speedtest depende de la distancia al servidor."""
        return latencia.promedio if latencia.promedio is not None else medicion.ping

    @staticmethod
    def _puntuar_calidad(
        medicion: _MedicionVelocidad, latencia: ResultadoLatencia, jitter: float
    ) -> Tuple[int, str]:
        """Calcula una puntuación ponderada 0-100 y su clasificación cualitativa."""
        if medicion.bajada == 0:
            return 0, "Sin servicio"
        latencia_real = NetworkMonitor._latencia_efectiva(medicion, latencia)
        perdida_pct = latencia.perdida_pct

        def acotar(valor: float) -> float:
            return max(0.0, min(1.0, valor))

        puntos = (
            35 * acotar(medicion.bajada / REFERENCIA_BAJADA_MBPS)
            + 15 * acotar(medicion.subida / REFERENCIA_SUBIDA_MBPS)
            + 20 * acotar(1 - (latencia_real - 20) / 180)
            + 15 * acotar(1 - jitter / 50)
            + 15 * acotar(1 - perdida_pct / 10)
        )
        puntuacion = round(puntos)
        if puntuacion >= 85:
            return puntuacion, "Excelente"
        if puntuacion >= 65:
            return puntuacion, "Buena"
        if puntuacion >= 40:
            return puntuacion, "Regular"
        return puntuacion, "Mala"

    # --------------------------------------------------------------- medición

    @staticmethod
    def _fase_wifi() -> InfoWifi:
        with Spinner("Leyendo interfaz de red", prefijo="  ├─") as sp:
            wifi = NetworkService.obtener_info_wi_fi()
            if wifi.tipo_conexion == "Wi-Fi":
                detalles = [f"{wifi.senal_pct}%"]
                if wifi.banda:
                    detalles.append(wifi.banda)
                if wifi.canal:
                    detalles.append(f"canal {wifi.canal}")
                sp.exito(f"Wi-Fi: {color(wifi.ssid, 'negrita')} · " + " · ".join(detalles))
            else:
                sp.exito("Conexión: Ethernet / Cable (sin Wi-Fi activo)")
        return wifi

    @staticmethod
    def _fase_latencia() -> Tuple[ResultadoLatencia, Optional[ResultadoLatencia], str]:
        """Pings a internet y al router en paralelo, para separar fallas locales de las del ISP."""
        gateway = NetworkService.obtener_gateway()
        with Spinner(f"Midiendo latencia a {PING_HOST} y al router", prefijo="  ├─") as sp:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futuro_inet = pool.submit(NetworkService.medir_latencia)
                futuro_gw = (
                    pool.submit(NetworkService.medir_latencia, gateway, PING_GATEWAY_CANTIDAD)
                    if gateway
                    else None
                )
                latencia = futuro_inet.result()
                latencia_gw = futuro_gw.result() if futuro_gw else None

            texto_gw = ""
            if latencia_gw is not None:
                valor = f"{latencia_gw.promedio} ms" if latencia_gw.recibidos else "sin respuesta"
                texto_gw = f" · router {valor}"
            if latencia.recibidos:
                sp.exito(
                    f"Latencia: {latencia.promedio} ms · jitter {latencia.jitter or 0} ms"
                    f" · pérdida {latencia.perdida_pct}%{texto_gw}"
                )
            else:
                sp.fallo(f"Latencia: sin respuesta de {PING_HOST} (pérdida 100%){texto_gw}")
        return latencia, latencia_gw, gateway

    @staticmethod
    def _fase_dns() -> Optional[float]:
        with Spinner(f"Resolviendo DNS de {DNS_DOMINIO_PRUEBA}", prefijo="  ├─") as sp:
            tiempo = NetworkService.medir_dns()
            if tiempo is None:
                sp.fallo(f"DNS: no se pudo resolver {DNS_DOMINIO_PRUEBA}")
            else:
                sp.exito(f"DNS: {tiempo} ms")
        return tiempo

    @staticmethod
    def _fase_velocidad() -> _MedicionVelocidad:
        """Ejecuta el speedtest por etapas; si una falla, se omiten las siguientes."""
        medicion = _MedicionVelocidad()
        fase = "conectar con Speedtest"
        try:
            with Spinner("Conectando con Speedtest y eligiendo servidor", prefijo="  ├─") as sp:
                prueba = PruebaVelocidad()
                fase = "seleccionar servidor"
                prueba.seleccionar_servidor()
                medicion.proveedor = prueba.proveedor
                medicion.servidor = prueba.nombre_servidor
                medicion.ubicacion = prueba.ubicacion_servidor
                medicion.distancia_km = prueba.distancia_km
                medicion.ping = prueba.ping_ms
                medicion.ip_publica = prueba.ip_publica
                medicion.host_servidor = prueba.host_servidor
                medicion.ip_servidor = prueba.ip_servidor
                medicion.puerto_servidor = prueba.puerto_servidor
                sp.exito(
                    f"Servidor: {medicion.servidor} ({medicion.ubicacion})"
                    f" · {medicion.distancia_km} km · ping {medicion.ping} ms"
                )
            print(
                f"  │    IP pública {medicion.ip_publica or '?'} → "
                f"{medicion.ip_servidor or medicion.host_servidor}:{medicion.puerto_servidor}"
            )

            fase = "medir descarga"
            with Spinner("Midiendo velocidad de descarga", prefijo="  ├─") as sp:
                medicion.bajada = prueba.medir_descarga()
                sp.exito(f"Descarga: {color(f'↓ {medicion.bajada} Mbps', 'negrita')}")

            fase = "medir subida"
            with Spinner("Midiendo velocidad de subida", prefijo="  ├─") as sp:
                medicion.subida = prueba.medir_subida()
                sp.exito(f"Subida:   {color(f'↑ {medicion.subida} Mbps', 'negrita')}")

            medicion.datos_mb = prueba.datos_consumidos_mb
        except KeyboardInterrupt:
            raise
        except Exception as error:
            mensaje = str(error).strip() or type(error).__name__
            medicion.error = f"Falló al {fase}: {mensaje}"[:150]
        return medicion

    def capturar_muestra(self, id_muestra: int) -> MuestraRed:
        """Ejecuta un ciclo completo de medición y construye el registro de la muestra."""
        inicio = time.time()
        ahora = datetime.now()
        print(
            color(f"[{ahora:%H:%M:%S}]", "gris")
            + color(f" Muestra #{id_muestra}", "negrita")
        )

        wifi = self._fase_wifi()
        latencia, latencia_gw, gateway = self._fase_latencia()
        tiempo_dns = self._fase_dns()
        medicion = self._fase_velocidad()

        jitter = latencia.jitter
        if jitter is None:
            jitter = round(medicion.ping * FACTOR_ESTIMACION_JITTER, 2)

        estado, observaciones = self._evaluar_estado_conexion(medicion, latencia, jitter, wifi)
        observaciones = self._agregar_avisos_locales(observaciones, latencia, latencia_gw, tiempo_dns)
        puntuacion, clasificacion = self._puntuar_calidad(medicion, latencia, jitter)

        if self.modo == "Manual":
            coincide = "Sí" if wifi.ssid == self.ssid_objetivo else "No"
            if coincide == "No":
                observaciones += f"; conectado a '{wifi.ssid}' en lugar de la red objetivo"
        else:
            coincide = "N/A"

        return MuestraRed(
            id_muestra=id_muestra,
            timestamp=f"{ahora:%Y-%m-%d %H:%M:%S}",
            fecha=f"{ahora:%Y-%m-%d}",
            hora=f"{ahora:%H:%M:%S}",
            dia_semana=DIAS_SEMANA[ahora.weekday()],
            franja_horaria=_franja_horaria(ahora.hour),
            modo_monitoreo=self.modo,
            nombre_equipo=socket.gethostname(),
            pid_proceso=os.getpid(),
            proveedor_servicio=medicion.proveedor,
            ip_publica=medicion.ip_publica,
            ip_local=NetworkService.obtener_ip_local(),
            ip_gateway=gateway,
            servidor_speedtest=medicion.servidor,
            ubicacion_servidor=medicion.ubicacion,
            distancia_servidor_km=medicion.distancia_km,
            host_servidor=medicion.host_servidor,
            ip_servidor=medicion.ip_servidor,
            puerto_servidor=medicion.puerto_servidor,
            ssid_objetivo=self.ssid_objetivo,
            ssid_actual=wifi.ssid,
            coincide_red_objetivo=coincide,
            tipo_conexion=wifi.tipo_conexion,
            bssid=wifi.bssid,
            banda_wifi=wifi.banda,
            canal_wifi=wifi.canal,
            tipo_radio=wifi.tipo_radio,
            autenticacion=wifi.autenticacion,
            calidad_senal_porcentaje=wifi.senal_pct,
            rssi_dbm=wifi.rssi_dbm,
            velocidad_enlace_rx_mbps=wifi.enlace_rx_mbps,
            velocidad_enlace_tx_mbps=wifi.enlace_tx_mbps,
            velocidad_bajada_mbps=medicion.bajada,
            velocidad_subida_mbps=medicion.subida,
            velocidad_promedio_mbps=round((medicion.bajada + medicion.subida) / 2, 2),
            ping_ms=medicion.ping,
            latencia_min_ms=latencia.minimo,
            latencia_max_ms=latencia.maximo,
            latencia_promedio_ms=latencia.promedio,
            jitter_ms=jitter,
            perdida_paquetes_pct=latencia.perdida_pct,
            latencia_gateway_ms=latencia_gw.promedio if latencia_gw else None,
            perdida_gateway_pct=latencia_gw.perdida_pct if latencia_gw else None,
            tiempo_dns_ms=tiempo_dns,
            datos_consumidos_mb=medicion.datos_mb,
            tiempo_registro_s=round(time.time() - inicio, 2),
            puntuacion_calidad=puntuacion,
            clasificacion_calidad=clasificacion,
            estado_conexion=estado,
            observaciones=observaciones,
        )

    # ----------------------------------------------------------- presentación

    @staticmethod
    def _imprimir_resumen(muestra: MuestraRed) -> None:
        tono = COLOR_ESTADO.get(muestra.estado_conexion, "gris")
        estado = color(f"● {muestra.estado_conexion}", tono)
        print(
            f"  └─ {estado} · Calidad {muestra.puntuacion_calidad}/100"
            f" ({muestra.clasificacion_calidad}) · {muestra.tiempo_registro_s}s"
            + color(" · guardada en CSV", "gris")
        )
        if muestra.observaciones != "Operación normal":
            print(color(f"     {muestra.observaciones}", "gris"))
        print()

    def _imprimir_cabecera_sesion(self, respaldo: Optional[str]) -> None:
        print()
        print(f"{color('[INFO]', 'cian')} Modo activo     : {self.modo.upper()}")
        print(f"{color('[INFO]', 'cian')} Red objetivo    : {self.ssid_objetivo}")
        print(f"{color('[INFO]', 'cian')} PID del proceso : {os.getpid()}")
        print(f"{color('[INFO]', 'cian')} IP local        : {NetworkService.obtener_ip_local() or '?'}")
        print(f"{color('[INFO]', 'cian')} Dataset destino : {OUTPUT_FILE}")
        print(f"{color('[INFO]', 'cian')} Pausa entre muestras: {INTERVALO_SEGUNDOS} s")
        if respaldo:
            print(
                f"{color('[AVISO]', 'amarillo')} El CSV tenía columnas antiguas; se migró al"
                f" nuevo esquema. Respaldo: {respaldo}"
            )
        print(color("─" * ANCHO, "gris"))
        print(" Presiona CTRL + C en cualquier momento para detener.\n")

    def _imprimir_resumen_sesion(self) -> None:
        muestras = self.sesion.muestras
        print("\n")
        print(color("═" * ANCHO, "cian"))
        print(color("RESUMEN DE LA SESIÓN".center(ANCHO), "negrita"))
        print(color("═" * ANCHO, "cian"))
        duracion = int(time.time() - self.sesion.inicio)
        print(f" Duración            : {duracion // 60} min {duracion % 60} s")
        print(f" Muestras guardadas  : {len(muestras)}")

        con_servicio = [m for m in muestras if m.velocidad_bajada_mbps > 0]
        if con_servicio:
            def promedio(valores: List[float]) -> float:
                return round(sum(valores) / len(valores), 2)

            bajadas = [m.velocidad_bajada_mbps for m in con_servicio]
            print(
                f" Descarga (prom/min/máx): {promedio(bajadas)} / {min(bajadas)} / {max(bajadas)} Mbps"
            )
            print(f" Subida promedio     : {promedio([m.velocidad_subida_mbps for m in con_servicio])} Mbps")
            print(f" Ping promedio       : {promedio([m.ping_ms for m in con_servicio])} ms")
            print(f" Jitter promedio     : {promedio([m.jitter_ms for m in con_servicio])} ms")
            print(f" Calidad promedio    : {promedio([m.puntuacion_calidad for m in con_servicio])}/100")

        for estado, tono in COLOR_ESTADO.items():
            cantidad = sum(1 for m in muestras if m.estado_conexion == estado)
            if cantidad:
                porcentaje = round(cantidad / len(muestras) * 100, 1)
                print(f" {color('●', tono)} {estado:<18}: {cantidad} ({porcentaje}%)")
        print(color("═" * ANCHO, "cian"))
        print(" Dataset guardado de forma segura.")

    # ------------------------------------------------------------------ bucle

    def iniciar(self) -> None:
        """Arranca el bucle continuo de muestreo."""
        try:
            self.configurar_modo()
        except (KeyboardInterrupt, EOFError):
            print("\n Cancelado por el usuario.")
            return

        respaldo = StorageService.inicializar_entorno()
        self._imprimir_cabecera_sesion(respaldo)
        self.sesion = _EstadisticasSesion()

        try:
            while True:
                muestra = self.capturar_muestra(StorageService.obtener_siguiente_id())
                StorageService.guardar_muestra(muestra)
                self.sesion.muestras.append(muestra)
                self._imprimir_resumen(muestra)
                cuenta_regresiva(INTERVALO_SEGUNDOS)
        except KeyboardInterrupt:
            self._imprimir_resumen_sesion()
