<p align="center"><img src="docs/banner.svg" alt="MuestreoInternet - Motor de telemetría de red y generación de datasets CSV" width="100%"></p>

<p align="center">
  <img alt="Versión" src="https://img.shields.io/badge/versi%C3%B3n-1.0.0-f2a93b">
  <img alt="Estado" src="https://img.shields.io/badge/estado-activo-brightgreen">
  <img alt="Python" src="https://img.shields.io/badge/Python-%E2%89%A53.10-3776AB?logo=python&logoColor=white">
  <img alt="Speedtest CLI" src="https://img.shields.io/badge/speedtest--cli-2.1.3-00D2FF?logo=speedtest&logoColor=white">
  <img alt="Formato Dataset" src="https://img.shields.io/badge/Dataset-CSV%20(UTF--8)-217346?logo=microsoftexcel&logoColor=white">
  <img alt="Automatización" src="https://img.shields.io/badge/Lanzador-Windows%20Batch-4D4D4D?logo=windowsterminal&logoColor=white">
  <img alt="Plataforma" src="https://img.shields.io/badge/plataforma-Windows-0078D6?logo=windows&logoColor=white">
  <img alt="Muestreo" src="https://img.shields.io/badge/intervalo-10s-orange">
  <img alt="Uso" src="https://img.shields.io/badge/uso-recolecci%C3%B3n%20de%20datos-lightgrey">
</p>

---

## 📋 Descripción General

**MuestreoInternet** es una utilidad automatizada diseñada para capturar métricas periódicas de rendimiento de red (velocidad de bajada, subida, velocidad promedio, latencia/ping, proveedor ISP y SSID) cada **10 segundos**, estructurando los registros de forma incremental en un dataset `.csv` listo para análisis exploratorio o entrenamiento de modelos.

---

## 📂 Estructura del Proyecto

```text
muestreo_internet/
├── docs/
│   └── banner.svg         # Banner vectorial de cabecera
├── salidas/
│   └── resultado.csv      # Dataset generado automáticamente
├── main.py                # Motor lógico y gestión de muestreo
├── config.py              # Constantes, cabeceras y rutas globales
├── ejecutar.bat           # Lanzador interactivo automatizado
├── requirements.txt       # Dependencias de Python
├── .gitignore             # Exclusiones de control de versiones
├── .gitattributes         # Normalización de saltos de línea
└── README.md              # Documentación técnica