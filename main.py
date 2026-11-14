import csv
import importlib.util
import os
import subprocess
import sys
import time
from datetime import datetime

# Verificación interna de dependencias críticas antes de iniciar
DEPENDENCIAS = ["speedtest"]

def verificar_dependencias():
    for dep in DEPENDENCIAS:
        if importlib.util.find_spec(dep) is None:
            print(f"[Error Crítico] La librería '{dep}' no está instalada.")
            print("Ejecuta 'pip install -r requirements.txt' o utiliza el archivo .bat para corregirlo.")
            sys.exit(1)

verificar_dependencias()

import speedtest
from config import OUTPUT_DIR, OUTPUT_FILE, INTERVALO_SEGUNDOS, CSV_HEADERS


def obtener_ssid_actual():
    """Obtiene el nombre de la red Wi-Fi actual en sistemas Windows."""
    try:
        resultado = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True
        )
        for linea in resultado.stdout.split("\n"):
            if "SSID" in linea and "BSSID" not in linea:
                partes = linea.split(":")
                if len(partes) > 1:
                    return partes[1].strip()
    except Exception:
        pass
    return "Ethernet / Desconocido"


def listar_redes_disponibles():
    """Devuelve una lista de redes Wi-Fi cercanas detectadas."""
    redes = []
    try:
        resultado = subprocess.run(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True
        )
        for linea in resultado.stdout.split("\n"):
            if "SSID" in linea and "BSSID" not in linea:
                partes = linea.split(":")
                if len(partes) > 1:
                    ssid = partes[1].strip()
                    if ssid and ssid not in redes:
                        redes.append(ssid)
    except Exception:
        pass
    return redes


def inicializar_entorno():
    """Valida y crea el directorio de salidas y el archivo CSV si no existen."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as archivo:
            writer = csv.DictWriter(archivo, fieldnames=CSV_HEADERS)
            writer.writeheader()


def medir_internet(modo, ssid_objetivo):
    """Ejecuta las pruebas de velocidad y recolecta los metadatos."""
    tiempo_inicio = time.time()
    timestamp_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ssid_actual = obtener_ssid_actual()
    
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        
        velocidad_bajada_bps = st.download()
        velocidad_subida_bps = st.upload()
        
        velocidad_bajada_mbps = round(velocidad_bajada_bps / 1_000_000, 2)
        velocidad_subida_mbps = round(velocidad_subida_bps / 1_000_000, 2)
        velocidad_promedio_mbps = round((velocidad_bajada_mbps + velocidad_subida_mbps) / 2, 2)
        
        ping = st.results.ping
        proveedor_servicio = st.results.client.get("isp", "Desconocido")
        
        tiempo_fin = time.time()
        tiempo_registro = round(tiempo_fin - tiempo_inicio, 2)
        
        return {
            "timestamp": timestamp_actual,
            "modo_monitoreo": modo,
            "proveedor_servicio": proveedor_servicio,
            "ssid_objetivo": ssid_objetivo,
            "ssid_actual": ssid_actual,
            "tiempo_registro_s": tiempo_registro,
            "velocidad_promedio_mbps": velocidad_promedio_mbps,
            "velocidad_subida_mbps": velocidad_subida_mbps,
            "velocidad_bajada_mbps": velocidad_bajada_mbps,
            "ping_ms": ping
        }
    except Exception as e:
        print(f"[Error] Falló la prueba de velocidad: {e}")
        return None


def guardar_fila(datos):
    """Agrega un nuevo registro al final del archivo CSV."""
    with open(OUTPUT_FILE, mode="a", newline="", encoding="utf-8") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=CSV_HEADERS)
        writer.writerow(datos)


def seleccionar_modo():
    """Menú interactivo en consola para elegir el modo de operación."""
    print("========================================")
    print("   SISTEMA DE MUESTREO DE INTERNET      ")
    print("========================================")
    print("1. Modo Automático (Red conectada actual)")
    print("2. Modo Manual (Elegir o fijar red objetivo)")
    print("----------------------------------------")
    
    opcion = input("Selecciona una opción [1/2]: ").strip()
    
    if opcion == "2":
        print("\n--- Configuración Modo Manual ---")
        red_actual = obtener_ssid_actual()
        print(f"Red detectada actualmente: {red_actual}")
        red_manual = input("Ingresa el nombre exacto de la red a monitorear (o presiona ENTER para usar la actual): ").strip()
        ssid_objetivo = red_manual if red_manual else red_actual
        return "Manual", ssid_objetivo
    else:
        return "Automático", "Red Activa Dinámica"


def ejecutar_monitoreo():
    modo, ssid_objetivo = seleccionar_modo()
    inicializar_entorno()
    
    print(f"\n[INFO] Iniciando muestreo en MODO: {modo.upper()}")
    print(f"[INFO] Red objetivo / Contexto: {ssid_objetivo}")
    print(f"[INFO] Archivo de salida: {OUTPUT_FILE}")
    print(f"[INFO] Frecuencia: Cada {INTERVALO_SEGUNDOS} segundos")
    print("[!] Presiona CTRL + C en cualquier momento para detener de forma segura.\n")
    
    try:
        while True:
            inicio_ciclo = time.time()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Tomando muestra de red...")
            
            datos_muestra = medir_internet(modo, ssid_objetivo)
            if datos_muestra:
                guardar_fila(datos_muestra)
                print(f"  -> ISP: {datos_muestra['proveedor_servicio']} | Red Actual: {datos_muestra['ssid_actual']}")
                print(f"  -> Bajada: {datos_muestra['velocidad_bajada_mbps']} Mbps | Subida: {datos_muestra['velocidad_subida_mbps']} Mbps | Ping: {datos_muestra['ping_ms']} ms\n")
            
            tiempo_transcurrido = time.time() - inicio_ciclo
            tiempo_espera = INTERVALO_SEGUNDOS - tiempo_transcurrido
            
            if tiempo_espera > 0:
                time.sleep(tiempo_espera)
            else:
                print(f"[Aviso] La prueba excedió los {INTERVALO_SEGUNDOS}s ({round(tiempo_transcurrido, 2)}s). Reiniciando ciclo...\n")
                
    except KeyboardInterrupt:
        print("\n\n[!] Monitoreo detenido por el usuario. Datos guardados con éxito en el dataset.")


if __name__ == "__main__":
    ejecutar_monitoreo()