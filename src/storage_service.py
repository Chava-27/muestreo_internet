"""
Servicio de persistencia encargado de la gestión de directorios y escritura
incremental de registros en el dataset CSV.
"""

import csv
import os
from src.config import CSV_HEADERS, OUTPUT_DIR, OUTPUT_FILE
from src.models import MuestraRed


class StorageService:
    """Administra las operaciones de lectura y escritura sobre el archivo CSV de salida."""

    @staticmethod
    def inicializar_entorno() -> None:
        """
        Crea el directorio de salidas y genera el archivo CSV con cabeceras si no existe.
        """
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        if not os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as archivo:
                escritor = csv.DictWriter(archivo, fieldnames=CSV_HEADERS)
                escritor.writeheader()

    @staticmethod
    def obtener_siguiente_id() -> int:
        """
        Calcula el próximo identificador autoincremental inspeccionando el último registro.

        Returns:
            int: Siguiente número de ID disponible (comienza en 1).
        """
        if not os.path.exists(OUTPUT_FILE):
            return 1

        try:
            with open(OUTPUT_FILE, mode="r", encoding="utf-8") as archivo:
                filas = list(csv.reader(archivo))
                if len(filas) <= 1:
                    return 1
                ultima_fila = filas[-1]
                if ultima_fila and ultima_fila[0].isdigit():
                    return int(ultima_fila[0]) + 1
        except Exception:
            pass

        return 1

    @staticmethod
    def guardar_muestra(muestra: MuestraRed) -> None:
        """
        Agrega una nueva fila al final del dataset CSV de manera segura.

        Args:
            muestra: Objeto MuestraRed con los datos validados del ciclo actual.
        """
        with open(OUTPUT_FILE, mode="a", newline="", encoding="utf-8") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=CSV_HEADERS)
            escritor.writerow(muestra.to_dict())