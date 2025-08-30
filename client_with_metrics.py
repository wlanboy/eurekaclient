# client_wm.py
import json
import threading
import time
import sys
import signal
import os

# Importiere die Eureka-Client-Logik und die MetricsStore-Klasse
from eureka_client_lib import eureka_lifecycle, deregister_instance, MetricsStore
from eureka_client_lib import EUREKA_SERVER_URL # Um die URL im Start-Log auszugeben

# Importiere die Funktion zum Starten des Metrik-Webservers
from metrics_exporter import run_metrics_web_server # <-- Wichtige Änderung hier

# --- Konfiguration für den Metrik-Webserver ---
METRICS_SERVER_HOST = os.getenv("METRICS_SERVER_HOST", "0.0.0.0")
METRICS_SERVER_PORT = int(os.getenv("METRICS_SERVER_PORT", 9090))

# --- Globale Metrik-Speicher-Instanz ---
metrics_store = MetricsStore()

# --- Globale Listen für Threads und Services (für sauberes Herunterfahren) ---
eureka_lifecycle_threads = []
services_to_manage = []
stop_events = {} # Speichert Threading.Event-Objekte für jeden Service-Thread

def graceful_shutdown(signum, frame):
    """
    Handler für SIGINT (CTRL+C) und SIGTERM für sauberes Herunterfahren.
    """
    print("\nEmpfange Herunterfahren-Signal. Starte graziöses Herunterfahren...")

    # 1. Signal an alle Eureka-Lifecycle-Threads senden, sich zu beenden
    for service_name, event in stop_events.items():
        print(f"Sende Stopp-Signal an Service '{service_name}'.")
        event.set()

    # 2. Kurze Wartezeit, damit Threads ihre Schleifen beenden können
    time.sleep(2)

    # 3. Services von Eureka deregistrieren
    for service_data in services_to_manage:
        deregister_instance(service_data, metrics_store)

    print("Alle Services versucht zu deregistrieren. Beende Anwendung.")
    sys.exit(0)

# --- Hauptlogik ---
def main():
    global services_to_manage
    config_file = "services.json"

    # Signal-Handler für SIGINT (CTRL+C) und SIGTERM einrichten
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    print(f"Verwende Eureka Server URL: {EUREKA_SERVER_URL}")
    print(f"Metrik-Server lauscht auf {METRICS_SERVER_HOST}:{METRICS_SERVER_PORT}")

    try:
        with open(config_file, "r") as f:
            services_to_manage = json.load(f)
    except FileNotFoundError:
        print(f"Fehler: Konfigurationsdatei '{config_file}' nicht gefunden. Stelle sicher, dass sie im selben Verzeichnis liegt.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Fehler: Ungültiges JSON in der Konfigurationsdatei '{config_file}'. Bitte überprüfen Sie die Syntax.")
        sys.exit(1)

    # Starte Eureka Client Threads für jeden Service
    for service_data in services_to_manage:
        service_name_upper = service_data["serviceName"].upper()
        if "leaseInfo" not in service_data:
            service_data["leaseInfo"] = {
                "renewalIntervalInSecs": 30,
                "durationInSecs": 90
            }
        
        metrics_store.set_service_registered_status(service_name_upper, 0)

        stop_event = threading.Event()
        stop_events[service_name_upper] = stop_event

        thread = threading.Thread(target=eureka_lifecycle, args=(service_data, metrics_store, stop_event))
        eureka_lifecycle_threads.append(thread)
        thread.daemon = True
        thread.start()

    # Starte den Metrik-Webserver in einem separaten Thread
    # Rufe die ausgelagerte Funktion auf
    web_server_thread = threading.Thread(
        target=run_metrics_web_server,
        args=(metrics_store, METRICS_SERVER_HOST, METRICS_SERVER_PORT)
    )
    web_server_thread.daemon = True
    web_server_thread.start()

    print("Eureka Client Manager und Metrik-Webserver gestartet. Drücke STRG+C zum Beenden.")

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
