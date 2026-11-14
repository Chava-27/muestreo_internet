"""
Utilidades de interfaz de consola: colores ANSI, spinner animado en hilo
secundario y barra de cuenta regresiva, con degradación segura en Windows.
"""

import os
import shutil
import sys
import threading
import time
from typing import Optional


def _habilitar_vt_windows() -> bool:
    """Activa el procesamiento de secuencias ANSI en la consola de Windows."""
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        modo = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(modo)):
            return False
        return bool(kernel32.SetConsoleMode(handle, modo.value | 0x0004))
    except Exception:
        return False


def _configurar_salida() -> None:
    """Fuerza UTF-8 en stdout para que los símbolos no rompan la ejecución."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_configurar_salida()
ES_TTY: bool = sys.stdout.isatty()
ANSI: bool = ES_TTY and _habilitar_vt_windows() and "NO_COLOR" not in os.environ

# Terminales modernas (Windows Terminal, VS Code, Linux/macOS) muestran braille y ✓.
UNICODE_RICO: bool = bool(
    os.environ.get("WT_SESSION") or os.environ.get("TERM_PROGRAM") or os.name != "nt"
)

FRAMES_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏" if UNICODE_RICO else "|/-\\"
OK = "✓" if UNICODE_RICO else "OK"
FALLO = "✗" if UNICODE_RICO else "X"

_COLORES = {
    "gris": "90",
    "rojo": "91",
    "verde": "92",
    "amarillo": "93",
    "azul": "94",
    "magenta": "95",
    "cian": "96",
    "negrita": "1",
}


def color(texto: str, nombre: str) -> str:
    """Envuelve el texto en el color ANSI indicado si la terminal lo soporta."""
    if not ANSI:
        return texto
    return f"\033[{_COLORES[nombre]}m{texto}\033[0m"


def _ancho_terminal() -> int:
    return shutil.get_terminal_size((100, 20)).columns


def _reescribir_linea(texto: str) -> None:
    """Sobrescribe la línea actual completa sin dejar residuos."""
    if ANSI:
        sys.stdout.write(f"\r{texto}\033[K")
    else:
        sys.stdout.write("\r" + texto.ljust(_ancho_terminal() - 1))
    sys.stdout.flush()


def limpiar_linea() -> None:
    """Borra la línea actual y deja el cursor al inicio."""
    if not ES_TTY:
        return
    if ANSI:
        sys.stdout.write("\r\033[K")
    else:
        sys.stdout.write("\r" + " " * (_ancho_terminal() - 1) + "\r")
    sys.stdout.flush()


class Spinner:
    """
    Indicador de progreso animado que corre en un hilo mientras se ejecuta
    una tarea bloqueante. Al terminar deja una línea final con el resultado.

    Uso:
        with Spinner("Midiendo descarga", prefijo="  ├─") as sp:
            valor = tarea()
            sp.exito(f"Descarga: {valor} Mbps")
    """

    def __init__(self, mensaje: str, prefijo: str = "") -> None:
        self.mensaje = mensaje
        self.prefijo = prefijo
        self._resultado: Optional[str] = None
        self._fallido = False
        self._detener = threading.Event()
        self._hilo = threading.Thread(target=self._animar, daemon=True)
        self._inicio = 0.0

    @property
    def transcurrido(self) -> float:
        return time.time() - self._inicio

    def _animar(self) -> None:
        indice = 0
        while not self._detener.is_set():
            frame = color(FRAMES_SPINNER[indice % len(FRAMES_SPINNER)], "cian")
            tiempo = color(f"{self.transcurrido:5.1f}s", "gris")
            _reescribir_linea(f"{self.prefijo} {frame} {self.mensaje}... {tiempo}")
            indice += 1
            self._detener.wait(0.1)

    def exito(self, resultado: str) -> None:
        self._resultado = resultado

    def fallo(self, resultado: str) -> None:
        self._resultado = resultado
        self._fallido = True

    def __enter__(self) -> "Spinner":
        self._inicio = time.time()
        if ES_TTY:
            self._hilo.start()
        return self

    def __exit__(self, tipo_exc, valor_exc, traza) -> bool:
        self._detener.set()
        if self._hilo.is_alive():
            self._hilo.join()
        limpiar_linea()

        tiempo = color(f"({self.transcurrido:.1f}s)", "gris")
        if tipo_exc is KeyboardInterrupt:
            print(f"{self.prefijo} {color(FALLO, 'amarillo')} {self.mensaje}: cancelado")
        elif tipo_exc is not None or self._fallido:
            detalle = self._resultado or f"{self.mensaje}: {valor_exc}"
            print(f"{self.prefijo} {color(FALLO, 'rojo')} {detalle} {tiempo}")
        else:
            print(f"{self.prefijo} {color(OK, 'verde')} {self._resultado or self.mensaje} {tiempo}")
        return False


def cuenta_regresiva(segundos: float, ancho_barra: int = 24) -> None:
    """Muestra una barra de progreso que se vacía hasta el siguiente ciclo."""
    if segundos <= 0:
        return
    if not ES_TTY:
        time.sleep(segundos)
        return

    lleno, vacio = ("█", "░") if UNICODE_RICO else ("#", "-")
    fin = time.time() + segundos
    try:
        while (restante := fin - time.time()) > 0:
            progreso = 1 - restante / segundos
            bloques = int(progreso * ancho_barra)
            barra = color(lleno * bloques, "cian") + color(vacio * (ancho_barra - bloques), "gris")
            _reescribir_linea(f"  Próximo sondeo en {restante:4.1f}s  {barra}")
            time.sleep(min(0.1, restante))
    finally:
        limpiar_linea()
