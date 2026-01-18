# client.py
import json
import threading
import time
import sys
import signal
import logging
import os
from typing import List, Dict, Any

# Importiere die Eureka-Client-Logik und die MetricsStore-Klasse
from eureka_client_lib import eureka_lifecycle, MetricsStore
from eureka_client_lib import EUREKA_SERVER_URL # Um die URL im Start-Log auszugeben

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Globale Metrik-Speicher-Instanz ---
# Jeder Client hat seine eigene Instanz von MetricsStore, um seine eigenen Metriken zu verfolgen.
metrics_store = MetricsStore()

# Logging
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
    print(f"Logverzeichnis '{LOG_DIR}' wurde erstellt.")
else:
    print(f"Logverzeichnis '{LOG_DIR}' ist vorhanden.")

# --- Globale Listen für Threads und Services (für sauberes Herunterfahren) ---
eureka_lifecycle_threads: List[threading.Thread] = []
services_to_manage: List[Dict[str, Any]] = [] # Muss global sein, damit der Signal-Handler darauf zugreifen kann
stop_events: Dict[str, threading.Event] = {} # Speichert Threading.Event-Objekte für jeden Service-Thread

def graceful_shutdown(signum, frame):
    """
    Handler für SIGINT (CTRL+C) und SIGTERM für sauberes Herunterfahren.
    """
    print("\nEmpfange Herunterfahren-Signal. Starte graziöses Herunterfahren...")

    # 1. Signal an alle Eureka-Lifecycle-Threads senden, sich zu beenden
    for service_name, event in stop_events.items():
        print(f"Sende Stopp-Signal an Service '{service_name}'.")
        event.set()

    # 2. Warte auf alle Threads, dass sie sich beenden
    print("Warte auf Beendigung aller Service-Threads...")
    for thread in eureka_lifecycle_threads:
        thread.join(timeout=10)
        if thread.is_alive():
            print(f"Warnung: Thread konnte nicht innerhalb von 10 Sekunden beendet werden.")

    print("Alle Services wurden heruntergefahren. Beende Anwendung.")
    sys.exit(0)

# --- Hauptlogik ---
def main():
    global services_to_manage # Zugriff auf die globale Liste
    config_file = "services.json" # Der Name der Konfigurationsdatei

    # Signal-Handler für SIGINT (CTRL+C) und SIGTERM einrichten
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    print(f"Verwende Eureka Server URL: {EUREKA_SERVER_URL}")
    print(f"Dieser Client wird Services aus '{config_file}' verwalten.")

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
        # Validiere erforderliche Felder
        if "serviceName" not in service_data:
            print(f"Fehler: Service-Konfiguration fehlt 'serviceName'. Überspringe: {service_data}")
            continue

        service_name_upper = service_data["serviceName"].upper()
        # Füge leaseInfo hinzu, falls nicht vorhanden
        if "leaseInfo" not in service_data:
            service_data["leaseInfo"] = {
                "renewalIntervalInSecs": 30,
                "durationInSecs": 90
            }

        # Initialisiere den Metrik-Status für diesen Service in diesem Client
        metrics_store.set_service_registered_status(service_name_upper, 0) # Startet als nicht registriert

        # Erstelle ein Stopp-Event für diesen Thread und speichere es
        stop_event = threading.Event()
        stop_events[service_name_upper] = stop_event

        log_path = f"logs/{service_name_upper}.log"
        logger = logging.getLogger(service_name_upper)
        logger.setLevel(logging.INFO)
        logger.propagate = False  # Verhindert Weitergabe an Root-Logger

        # Nur Handler hinzufügen, wenn noch keiner vorhanden ist
        if not logger.handlers:
            handler = logging.FileHandler(log_path)
            formatter = logging.Formatter('%(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        def run_lifecycle(svc_data, metrics, stop_evt, log, svc_name):
            try:
                eureka_lifecycle(svc_data, metrics, stop_evt, log)
            except Exception as e:
                log.exception(f"Error in eureka_lifecycle thread for {svc_name}: {e}")

        # Starte den Lebenszyklus-Thread für jeden Service
        thread = threading.Thread(
            target=run_lifecycle,
            args=(service_data, metrics_store, stop_event, logger, service_name_upper),
            name=f"eureka-{service_name_upper}"
        )
        eureka_lifecycle_threads.append(thread)
        thread.daemon = False  # Nicht-Daemon, damit graceful shutdown funktioniert
        thread.start()

    print("Eureka Client gestartet. Drücke STRG+C zum Beenden.")

    # Halte den Hauptthread am Leben, damit die Threads weiterlaufen
    # und der Signal-Handler auf STRG+C warten kann.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Falls KeyboardInterrupt nicht vom Signal-Handler abgefangen wird
        graceful_shutdown(None, None)

if __name__ == "__main__":
    main()
