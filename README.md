<p align="center"><img src="docs/banner.svg" alt="MuestreoInternet v3.0 — monitoreo continuo de red con exportación a CSV" width="100%"></p>

<p align="center">
  <img alt="Versión" src="https://img.shields.io/badge/versi%C3%B3n-3.0-2dd4bf">
  <img alt="Python" src="https://img.shields.io/badge/Python-%E2%89%A53.10-3776AB?logo=python&logoColor=white">
  <img alt="Plataforma" src="https://img.shields.io/badge/plataforma-Windows-0078D6?logo=windows&logoColor=white">
  <img alt="Dataset" src="https://img.shields.io/badge/dataset-CSV%20%C2%B7%2050%20columnas-217346">
  <img alt="Dependencias" src="https://img.shields.io/badge/dependencias-speedtest--cli-555">
</p>

MuestreoInternet mide tu conexión a internet una y otra vez y guarda cada medición como una fila en `salidas/resultado.csv`. Cada muestra registra velocidad, latencia real, jitter, pérdida de paquetes, estado del router, tiempo de DNS, datos de la red Wi-Fi y un diagnóstico automático. Con unas horas de muestras puedes ver a qué hora se degrada tu servicio y si la falla está en tu Wi-Fi o en tu proveedor.

El proyecto solo monitorea: lee el estado de la red y ejecuta pruebas de medición. No cambia ninguna configuración del equipo.

---

## Qué verás en la consola

Cada fase de la medición tiene su propio indicador animado con el tiempo transcurrido. Al terminar, la línea se reemplaza con el resultado. Este es un ejemplo de salida:

```text
[23:34:43] Muestra #10
  ├─ ✓ Wi-Fi: IZZI-E2AD-5G · 70% · 5 GHz · canal 149 (0.2s)
  ├─ ✓ Latencia: 25.38 ms · jitter 3.71 ms · pérdida 0.0% · router 3.75 ms (7.2s)
  ├─ ✓ DNS: 9.14 ms (0.0s)
  ├─ ✓ Servidor: Totalplay (Monterrey, Mexico) · 12.4 km · ping 24.1 ms (2.1s)
  │    IP pública 177.248.xxx.xxx → 200.xxx.xxx.xxx:8080
  ├─ ✓ Descarga: ↓ 186.4 Mbps (10.2s)
  ├─ ✓ Subida:   ↑ 38.6 Mbps (10.1s)
  └─ ● Estable · Calidad 91/100 (Excelente) · 32.1s · guardada en CSV

  Próximo sondeo en  1.4s  ████████████░░░░░░░░░░░░
```

Al presionar `Ctrl + C` se muestra un resumen de la sesión: duración, número de muestras, descarga promedio/mínima/máxima, ping, jitter, calidad promedio y el porcentaje de muestras estables, inestables y caídas.

En Windows Terminal y VS Code se usan un spinner braille y los símbolos ✓/✗. En la consola clásica (`conhost`) el programa cambia a `| / - \` y `OK`/`X` para que todo se vea bien. Si la salida se redirige a un archivo, las animaciones se desactivan y solo quedan las líneas finales.

---

## Inicio rápido

**Requisitos:** Windows 10/11, Python 3.10 o superior en el `PATH` y conexión por Wi-Fi o cable.

1. Da doble clic en **`ejecutar.bat`**. Instala `speedtest-cli`, crea `salidas/` y arranca el monitor.
2. Elige el modo:
   - **`[1] Automático`**: registra la red a la que estés conectado en cada momento.
   - **`[2] Manual`**: fija una red objetivo. Si el equipo se conecta a otra, la columna `coincide_red_objetivo` queda en `No` y se anota en `observaciones`.
3. Déjalo corriendo. Cada muestra tarda entre 30 y 60 segundos, según tu velocidad.
4. Detén con **`Ctrl + C`**. Las filas ya guardadas no se pierden; cada una se escribe en cuanto termina.

Sin el `.bat`:

```bash
pip install -r requirements.txt
python main.py
```

---

## Analizar el dataset

```bash
python analizar.py                 # usa salidas/resultado.csv
python analizar.py otra_ruta.csv   # cualquier CSV con el mismo esquema
```

Imprime promedio, mediana, mínimo y máximo de cada métrica, la distribución de estados y tablas por **franja horaria**, **día de la semana** y **red (SSID)**, además de las últimas caídas registradas. Solo usa la biblioteca estándar de Python.

El CSV se guarda en UTF-8 con BOM, así que Excel muestra bien los acentos. También se abre directo en Pandas o Power BI.

---

## Cómo se diagnostica cada muestra

| Estado | Cuándo |
|---|---|
| **Caída detectada** | La prueba de velocidad falló o la descarga fue 0 Mbps. |
| **Inestable** | Latencia > 150 ms, descarga < 5 Mbps, jitter > 30 ms o pérdida de paquetes > 2 %. |
| **Estable** | Ninguna de las anteriores. |

La latencia que se compara con el umbral es la **latencia ICMP real** (8 pings a `8.8.8.8`). El ping de speedtest se guarda aparte porque depende de qué tan lejos esté el servidor elegido.

En `observaciones` se agregan pistas para ubicar la falla:

- **El router no responde**: el problema está en tu red local o en el Wi-Fi.
- **Pérdida también hacia el router**: la red local pierde paquetes.
- **El router responde bien pero hay pérdida a internet**: el problema está del lado del proveedor.
- **DNS lento o sin resolver**, **señal Wi-Fi débil (< 40 %)** y **servidor speedtest lejano**.

La **puntuación de calidad (0–100)** pondera descarga (35), subida (15), latencia (20), jitter (15) y pérdida (15). La clasificación es Excelente (≥ 85), Buena (≥ 65), Regular (≥ 40) o Mala.

---

## Columnas del dataset (50)

| # | Columna | Descripción |
|---|---|---|
| 1 | `id_muestra` | Número consecutivo; continúa entre ejecuciones. |
| 2 | `timestamp` | Fecha y hora de inicio de la muestra (`YYYY-MM-DD HH:MM:SS`). |
| 3 | `fecha` | Solo la fecha. |
| 4 | `hora` | Solo la hora. |
| 5 | `dia_semana` | Lunes a Domingo. |
| 6 | `franja_horaria` | Madrugada (0–5 h), Mañana (6–11 h), Tarde (12–18 h) o Noche (19–23 h). |
| 7 | `modo_monitoreo` | Automático o Manual. |
| 8 | `nombre_equipo` | Nombre del equipo que midió. |
| 9 | `pid_proceso` | PID del proceso de Python que tomó la muestra. |
| 10 | `proveedor_servicio` | ISP detectado por speedtest. |
| 11 | `ip_publica` | IP pública con la que sales a internet. |
| 12 | `ip_local` | IP del equipo en la red local. |
| 13 | `ip_gateway` | IP del router (puerta de enlace en la misma subred). |
| 14 | `servidor_speedtest` | Patrocinador del servidor de prueba. |
| 15 | `ubicacion_servidor` | Ciudad y país del servidor. |
| 16 | `distancia_servidor_km` | Distancia estimada al servidor. |
| 17 | `host_servidor` | Nombre de host del servidor. |
| 18 | `ip_servidor` | IP resuelta del servidor. |
| 19 | `puerto_servidor` | Puerto usado para la prueba. |
| 20 | `ssid_objetivo` | Red configurada en modo manual. |
| 21 | `ssid_actual` | Red Wi-Fi conectada. |
| 22 | `coincide_red_objetivo` | Sí / No en modo manual; N/A en automático. |
| 23 | `tipo_conexion` | Wi-Fi o Ethernet / Cable. |
| 24 | `bssid` | MAC del punto de acceso. |
| 25 | `banda_wifi` | 2.4 GHz, 5 GHz o 6 GHz. |
| 26 | `canal_wifi` | Canal de radio. |
| 27 | `tipo_radio` | Estándar 802.11 (n, ac, ax…). |
| 28 | `autenticacion` | Seguridad de la red (WPA2, WPA3…). |
| 29 | `calidad_senal_porcentaje` | Señal Wi-Fi reportada por Windows (0–100). |
| 30 | `rssi_dbm` | Intensidad de señal en dBm. |
| 31 | `velocidad_enlace_rx_mbps` | Velocidad de enlace Wi-Fi de recepción. |
| 32 | `velocidad_enlace_tx_mbps` | Velocidad de enlace Wi-Fi de transmisión. |
| 33 | `velocidad_bajada_mbps` | Descarga medida. |
| 34 | `velocidad_subida_mbps` | Subida medida. |
| 35 | `velocidad_promedio_mbps` | Promedio de bajada y subida. |
| 36 | `ping_ms` | Ping al servidor speedtest. |
| 37 | `latencia_min_ms` | Latencia ICMP mínima. |
| 38 | `latencia_max_ms` | Latencia ICMP máxima. |
| 39 | `latencia_promedio_ms` | Latencia ICMP promedio. |
| 40 | `jitter_ms` | Variación media entre pings consecutivos. |
| 41 | `perdida_paquetes_pct` | Porcentaje de pings sin respuesta. |
| 42 | `latencia_gateway_ms` | Latencia promedio al router. |
| 43 | `perdida_gateway_pct` | Pérdida de paquetes hacia el router. |
| 44 | `tiempo_dns_ms` | Tiempo en resolver el dominio de prueba. |
| 45 | `datos_consumidos_mb` | MB transferidos por la prueba de velocidad. |
| 46 | `tiempo_registro_s` | Duración total de la muestra. |
| 47 | `puntuacion_calidad` | Puntuación 0–100. |
| 48 | `clasificacion_calidad` | Excelente, Buena, Regular, Mala o Sin servicio. |
| 49 | `estado_conexion` | Estable, Inestable o Caída detectada. |
| 50 | `observaciones` | Motivos del diagnóstico y avisos. |

Las celdas quedan vacías cuando un dato no aplica, por ejemplo los campos Wi-Fi en una conexión por cable.

**Si ya tenías un CSV de una versión anterior**, al iniciar se crea un respaldo (`salidas/resultado_respaldo_<fecha>.csv`) y el archivo se migra al esquema nuevo. Las filas antiguas se conservan con las columnas nuevas en blanco.

---

## Configuración

Todo se ajusta en [`src/config.py`](src/config.py):

| Variable | Valor | Para qué sirve |
|---|---|---|
| `INTERVALO_SEGUNDOS` | `2` | Pausa entre el final de una muestra y el inicio de la siguiente. |
| `PING_HOST` / `PING_CANTIDAD` | `8.8.8.8` / `8` | Destino y número de pings para latencia, jitter y pérdida. |
| `PING_GATEWAY_CANTIDAD` | `4` | Pings al router en cada muestra. |
| `DNS_DOMINIO_PRUEBA` | `www.google.com` | Dominio para medir el DNS. |
| `SPEEDTEST_SERVIDOR_IDS` | `[]` | IDs de servidores speedtest preferidos. Vacío = automático. |
| `DISTANCIA_SERVIDOR_LEJANO_KM` | `1500` | Distancia a partir de la cual se avisa que el servidor está lejos. |
| `UMBRAL_*` | — | Límites del diagnóstico (ping, descarga, jitter, pérdida, señal, DNS). |
| `REFERENCIA_BAJADA_MBPS` / `REFERENCIA_SUBIDA_MBPS` | `100` / `50` | Velocidades que obtienen el puntaje máximo. Ajústalas a tu plan contratado. |

> **Servidor speedtest lejano.** `speedtest-cli` 2.1.3 a veces elige servidores en otro continente, y eso baja las velocidades medidas. Si `observaciones` lo reporta, ejecuta `speedtest-cli --list`, copia el ID de un servidor cercano y ponlo en `SPEEDTEST_SERVIDOR_IDS`, por ejemplo `[12345]`.

Cada muestra descarga y sube alrededor de 20 MB o más, según tu velocidad. Si tu plan tiene límite de datos, sube `INTERVALO_SEGUNDOS`.

---

## Estructura

```text
muestreo_internet/
├── main.py                 # Punto de entrada
├── analizar.py             # Reporte estadístico del CSV
├── ejecutar.bat            # Lanzador para Windows (instala dependencias y ejecuta)
├── requirements.txt
├── docs/banner.svg
├── salidas/resultado.csv   # Dataset (se genera al ejecutar)
└── src/
    ├── config.py           # Rutas, umbrales y esquema de columnas
    ├── models.py           # Dataclasses: MuestraRed, InfoWifi, ResultadoLatencia
    ├── network_service.py  # netsh, ipconfig, ping, DNS y speedtest por fases
    ├── storage_service.py  # Creación, migración y escritura del CSV
    ├── console.py          # Colores, spinner animado y barra de cuenta regresiva
    └── monitor.py          # Ciclo de muestreo, diagnóstico y resumen de sesión
```

---

## Privacidad

El CSV guarda tu IP pública, la IP local, el BSSID del router y el nombre del equipo. `salidas/*.csv` está en `.gitignore`. Revisa el archivo antes de compartirlo.
