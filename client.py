# client.py
import json
import threading
import time
import sys
import signal
import os

# Importiere die Eureka-Client-Logik und die MetricsStore-Klasse
from eureka_client_lib import eureka_lifecycle, deregister_instance, MetricsStore
from eureka_client_lib import EUREKA_SERVER_URL # Um die URL im Start-Log auszugeben

# --- Globale Metrik-Speicher-Instanz ---
# Jeder Client hat seine eigene Instanz von MetricsStore, um seine eigenen Metriken zu verfolgen.
metrics_store = MetricsStore()

# --- Globale Listen für Threads und Services (für sauberes Herunterfahren) ---
eureka_lifecycle_threads = []
services_to_manage = [] # Muss global sein, damit der Signal-Handler darauf zugreifen kann
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
    time.sleep(2) # Gib den Threads 2 Sekunden Zeit

    # 3. Services von Eureka deregistrieren
    # Hier verwenden wir die globale metrics_store Instanz dieses Clients
    for service_data in services_to_manage:
        deregister_instance(service_data, metrics_store)

    print("Alle Services versucht zu deregistrieren. Beende Anwendung.")
    sys.exit(0) # Beendet das Programm

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

        # Starte den Lebenszyklus-Thread für jeden Service
        thread = threading.Thread(target=eureka_lifecycle, args=(service_data, metrics_store, stop_event))
        eureka_lifecycle_threads.append(thread)
        thread.daemon = True # Wichtig: Ermöglicht das Beenden des Hauptprogramms, auch wenn diese Threads laufen
        thread.start()

    print("Eureka Client gestartet. Drücke STRG+C zum Beenden.")

    # Halte den Hauptthread am Leben, damit die Daemon-Threads weiterlaufen
    # und der Signal-Handler auf STRG+C warten kann.
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
