"""
Servicio de persistencia encargado de la gestión de directorios, migración
de esquema y escritura incremental de registros en el dataset CSV.
"""

import csv
import os
import shutil
from datetime import datetime
from typing import Optional

from src.config import CSV_HEADERS, OUTPUT_DIR, OUTPUT_FILE
from src.models import MuestraRed


class StorageService:
    """Administra las operaciones de lectura y escritura sobre el archivo CSV de salida."""

    _siguiente_id: int = 1

    @staticmethod
    def inicializar_entorno() -> Optional[str]:
        """
        Crea el directorio y el CSV si no existen. Si el CSV tiene un esquema de
        columnas anterior, lo migra al actual conservando los datos y deja un respaldo.

        Returns:
            Ruta del respaldo creado si hubo migración, o None.
        """
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        respaldo = None

        if not os.path.exists(OUTPUT_FILE) or os.path.getsize(OUTPUT_FILE) == 0:
            StorageService._escribir_cabecera()
        else:
            with open(OUTPUT_FILE, mode="r", newline="", encoding="utf-8-sig") as archivo:
                cabecera = next(csv.reader(archivo), [])
            if cabecera != CSV_HEADERS:
                respaldo = StorageService._migrar_esquema()

        StorageService._siguiente_id = StorageService._calcular_siguiente_id()
        return respaldo

    @staticmethod
    def _escribir_cabecera() -> None:
        # utf-8-sig agrega BOM para que Excel muestre correctamente los acentos.
        with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8-sig") as archivo:
            csv.DictWriter(archivo, fieldnames=CSV_HEADERS).writeheader()

    @staticmethod
    def _migrar_esquema() -> str:
        """Reescribe el CSV con las columnas nuevas; las que no existían quedan vacías."""
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        respaldo = os.path.join(OUTPUT_DIR, f"resultado_respaldo_{marca}.csv")
        shutil.copy2(OUTPUT_FILE, respaldo)

        with open(respaldo, mode="r", newline="", encoding="utf-8-sig") as origen:
            filas = list(csv.DictReader(origen))

        with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8-sig") as destino:
            escritor = csv.DictWriter(
                destino, fieldnames=CSV_HEADERS, restval="", extrasaction="ignore"
            )
            escritor.writeheader()
            escritor.writerows(filas)
        return respaldo

    @staticmethod
    def _calcular_siguiente_id() -> int:
        """Lee el último id_muestra registrado (una sola vez, al iniciar)."""
        ultimo = 0
        try:
            with open(OUTPUT_FILE, mode="r", newline="", encoding="utf-8-sig") as archivo:
                for fila in csv.DictReader(archivo):
                    valor = (fila.get("id_muestra") or "").strip()
                    if valor.isdigit():
                        ultimo = max(ultimo, int(valor))
        except OSError:
            pass
        return ultimo + 1

    @staticmethod
    def obtener_siguiente_id() -> int:
        """Devuelve el próximo identificador autoincremental disponible."""
        return StorageService._siguiente_id

    @staticmethod
    def guardar_muestra(muestra: MuestraRed) -> None:
        """Agrega una nueva fila al final del dataset CSV."""
        with open(OUTPUT_FILE, mode="a", newline="", encoding="utf-8") as archivo:
            csv.DictWriter(archivo, fieldnames=CSV_HEADERS).writerow(muestra.to_dict())
        StorageService._siguiente_id = muestra.id_muestra + 1
