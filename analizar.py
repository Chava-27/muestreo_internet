"""
Genera un reporte en consola a partir del dataset salidas/resultado.csv:
promedios generales, distribución de estados y comportamiento por franja
horaria, día de la semana y red. Solo usa la biblioteca estándar.

Uso:
    python analizar.py               # analiza salidas/resultado.csv
    python analizar.py otro.csv      # analiza otro archivo con el mismo esquema
"""

import csv
import sys
from collections import Counter, defaultdict
from statistics import mean, median
from typing import Dict, List, Optional

from src.config import OUTPUT_FILE
from src.console import color

ANCHO = 72


def _numero(valor: Optional[str]) -> Optional[float]:
    try:
        return float(valor) if valor not in (None, "") else None
    except ValueError:
        return None


def _valores(filas: List[Dict[str, str]], columna: str) -> List[float]:
    return [v for v in (_numero(f.get(columna)) for f in filas) if v is not None]


def _fmt(valores: List[float], decimales: int = 2) -> str:
    if not valores:
        return "-"
    promedio = mean(valores)
    return f"{round(promedio)}" if decimales == 0 else f"{round(promedio, decimales)}"


def _titulo(texto: str) -> None:
    print()
    print(color(texto, "negrita"))
    print(color("─" * ANCHO, "gris"))


def _tabla_por_grupo(filas: List[Dict[str, str]], columna: str, orden: Optional[List[str]] = None) -> None:
    grupos: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for fila in filas:
        grupos[fila.get(columna) or "(vacío)"].append(fila)

    claves = [c for c in (orden or []) if c in grupos] + sorted(k for k in grupos if k not in (orden or []))
    print(f" {'Grupo':<20}{'Muestras':>9}{'↓ Mbps':>10}{'↑ Mbps':>10}{'Ping ms':>10}{'Calidad':>9}{'% Estable':>11}")
    for clave in claves:
        grupo = grupos[clave]
        con_servicio = [f for f in grupo if (_numero(f.get("velocidad_bajada_mbps")) or 0) > 0]
        estables = sum(1 for f in grupo if f.get("estado_conexion") == "Estable")
        latencias = _valores(con_servicio, "latencia_promedio_ms") or _valores(con_servicio, "ping_ms")
        print(
            f" {clave[:19]:<20}{len(grupo):>9}"
            f"{_fmt(_valores(con_servicio, 'velocidad_bajada_mbps')):>10}"
            f"{_fmt(_valores(con_servicio, 'velocidad_subida_mbps')):>10}"
            f"{_fmt(latencias):>10}"
            f"{_fmt(_valores(grupo, 'puntuacion_calidad'), 0):>9}"
            f"{round(estables / len(grupo) * 100, 1):>10}%"
        )


def analizar(ruta: str) -> int:
    try:
        with open(ruta, newline="", encoding="utf-8-sig") as archivo:
            filas = list(csv.DictReader(archivo))
    except FileNotFoundError:
        print(f"No existe el archivo: {ruta}")
        return 1

    if not filas:
        print("El dataset está vacío; ejecuta primero el monitor (main.py).")
        return 1

    print(color("═" * ANCHO, "cian"))
    print(color("REPORTE DEL DATASET DE TELEMETRÍA".center(ANCHO), "negrita"))
    print(color("═" * ANCHO, "cian"))
    marcas = sorted(f["timestamp"] for f in filas if f.get("timestamp"))
    print(f" Archivo  : {ruta}")
    print(f" Muestras : {len(filas)}")
    if marcas:
        print(f" Periodo  : {marcas[0]}  →  {marcas[-1]}")

    con_servicio = [f for f in filas if (_numero(f.get("velocidad_bajada_mbps")) or 0) > 0]

    _titulo("Métricas generales (muestras con servicio)")
    metricas = [
        ("Descarga (Mbps)", "velocidad_bajada_mbps"),
        ("Subida (Mbps)", "velocidad_subida_mbps"),
        ("Latencia ICMP (ms)", "latencia_promedio_ms"),
        ("Ping speedtest (ms)", "ping_ms"),
        ("Jitter (ms)", "jitter_ms"),
        ("Pérdida paquetes (%)", "perdida_paquetes_pct"),
        ("Latencia router (ms)", "latencia_gateway_ms"),
        ("DNS (ms)", "tiempo_dns_ms"),
        ("Señal Wi-Fi (%)", "calidad_senal_porcentaje"),
        ("Calidad (0-100)", "puntuacion_calidad"),
    ]
    print(f" {'Métrica':<24}{'Promedio':>10}{'Mediana':>10}{'Mínimo':>10}{'Máximo':>10}")
    for nombre, columna in metricas:
        valores = _valores(con_servicio, columna)
        if not valores:
            continue
        print(
            f" {nombre:<24}{round(mean(valores), 2):>10}{round(median(valores), 2):>10}"
            f"{min(valores):>10}{max(valores):>10}"
        )
    datos = _valores(filas, "datos_consumidos_mb")
    if datos:
        print(f" Datos consumidos por las pruebas: {round(sum(datos), 1)} MB")

    _titulo("Estado de la conexión")
    tonos = {"Estable": "verde", "Inestable": "amarillo", "Caída detectada": "rojo"}
    for estado, cantidad in Counter(f.get("estado_conexion") or "(sin dato)" for f in filas).most_common():
        porcentaje = round(cantidad / len(filas) * 100, 1)
        barra = "█" * int(porcentaje / 2.5)
        print(f" {color('●', tonos.get(estado, 'gris'))} {estado:<18}{cantidad:>6}  {porcentaje:>5}%  {color(barra, tonos.get(estado, 'gris'))}")

    _titulo("Por franja horaria")
    _tabla_por_grupo(filas, "franja_horaria", ["Madrugada", "Mañana", "Tarde", "Noche"])

    _titulo("Por día de la semana")
    _tabla_por_grupo(
        filas, "dia_semana", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    )

    _titulo("Por red (SSID)")
    _tabla_por_grupo(filas, "ssid_actual")

    caidas = [f for f in filas if f.get("estado_conexion") == "Caída detectada"]
    if caidas:
        _titulo(f"Últimas caídas registradas ({min(len(caidas), 10)} de {len(caidas)})")
        for fila in caidas[-10:]:
            print(f" {fila.get('timestamp', '')}  {fila.get('observaciones', '')[:ANCHO - 22]}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(analizar(sys.argv[1] if len(sys.argv) > 1 else OUTPUT_FILE))
