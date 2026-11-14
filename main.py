"""
Punto de entrada principal de la aplicación MuestreoInternet.
"""

from src.monitor import NetworkMonitor


def main() -> None:
    """Instancia y ejecuta el monitor de telemetría de red."""
    monitor = NetworkMonitor()
    monitor.iniciar()


if __name__ == "__main__":
    main()