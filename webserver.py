from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from models import ClientConfig
import threading
import os
import json
import logging
import time
from typing import Dict, List, Any

from eureka_client_lib import eureka_lifecycle, MetricsStore

# Logger für den Webserver
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup-Logik
    logger.info("Server startet...")

    yield  # hier läuft die App

    # Shutdown-Logik
    logger.info("Server wird heruntergefahren. Stoppe alle Clients...")
    for name, event in stop_events.items():
        logger.info(f"Stoppe Client {name}")
        event.set()
    for name, thread in client_threads.items():
        if thread.is_alive():
            logger.info(f"Warte auf Thread von {name}")
            thread.join(timeout=5)
    logger.info("Alle Clients gestoppt.")

app = FastAPI(lifespan=lifespan)
metrics_store = MetricsStore()

# Static files (HTML, JS, CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
    logger.info(f"Logverzeichnis '{LOG_DIR}' wurde erstellt.")
else:
    logger.info(f"Logverzeichnis '{LOG_DIR}' ist vorhanden.")

# In-memory registry
clients: Dict[str, Dict[str, Any]] = {}
client_threads: Dict[str, threading.Thread] = {}
stop_events: Dict[str, threading.Event] = {}

EUREKA_SERVERS_FILE = "eureka_server.json"
EUREKA_SERVER_URLS: List[str] = []

# Lade Liste von Eureka-Servern
if os.path.exists(EUREKA_SERVERS_FILE):
    try:
        with open(EUREKA_SERVERS_FILE, "r") as f:
            config = json.load(f)
            EUREKA_SERVER_URLS = config.get("servers", [])
            logger.info(f"{len(EUREKA_SERVER_URLS)} Eureka-Server geladen.")
    except Exception as e:
        logger.error(f"Fehler beim Laden von {EUREKA_SERVERS_FILE}: {e}")
else:
    logger.warning(f"{EUREKA_SERVERS_FILE} nicht gefunden. Bitte erstellen mit 'servers' Liste.")


CONFIG_FILE = "services.json"

# Load clients from services.json if it exists
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            loaded_clients = json.load(f)
            for client in loaded_clients:
                name = client["serviceName"].upper()
                # Add default leaseInfo if missing
                if "leaseInfo" not in client:
                    client["leaseInfo"] = {
                        "renewalIntervalInSecs": 30,
                        "durationInSecs": 90
                    }
                clients[name] = client
                metrics_store.set_service_registered_status(name, 0)
        logger.info(f"{len(clients)} Clients aus {CONFIG_FILE} geladen.")
    except Exception as e:
        logger.error(f"Fehler beim Laden von {CONFIG_FILE}: {e}")

def save_clients_to_file() -> None:
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(list(clients.values()), f, indent=2)
    except Exception as e:
        logger.error(f"Fehler beim Speichern von Clients: {e}")

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")

@app.get("/clients")
def list_clients():
    return [
        {
            "serviceName": name,
            "running": client_threads[name].is_alive() if name in client_threads else False
        }
        for name in clients
    ]

@app.post("/clients")
def add_client(config: ClientConfig):
    name = config.serviceName.upper()
    if name in clients:
        raise HTTPException(status_code=400, detail="Client already exists")
    clients[name] = config.dict()
    metrics_store.set_service_registered_status(name, 0)
    save_clients_to_file()
    return {"message": f"Client {name} added."}

@app.delete("/clients/{name}")
def delete_client(name: str):
    name = name.upper()
    if name in client_threads and client_threads[name].is_alive():
        raise HTTPException(status_code=400, detail="Client is running. Stop it first.")
    if name in clients:
        clients.pop(name)
        save_clients_to_file()
        return {"message": f"Client {name} deleted."}
    else:
        raise HTTPException(status_code=404, detail="Client not found")

@app.post("/clients/{name}/start")
def start_client(name: str):
    name = name.upper()
    if name not in clients:
        raise HTTPException(status_code=404, detail="Client not found")
    if name in client_threads and client_threads[name].is_alive():
        raise HTTPException(status_code=400, detail="Client already running")

    stop_event = threading.Event()
    stop_events[name] = stop_event

    def run():
        service_data = clients[name]
        log_path = f"logs/{name}.log"

        service_logger = logging.getLogger(name)
        service_logger.setLevel(logging.INFO)
        service_logger.propagate = False

        # Nur Handler hinzufügen, wenn noch keiner vorhanden ist
        if not service_logger.handlers:
            handler = logging.FileHandler(log_path)
            formatter = logging.Formatter('%(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            service_logger.addHandler(handler)

        try:
            service_logger.info("Starte Eureka-Client...")
            eureka_lifecycle(service_data, metrics_store, stop_event, service_logger)
        except Exception as e:
            service_logger.exception(f"Fehler im eureka_lifecycle: {e}")
            logger.error(f"Client {name} fehlgeschlagen: {e}")

    thread = threading.Thread(target=run, daemon=False, name=f"eureka-{name}")
    client_threads[name] = thread
    thread.start()
    return {"message": f"Client {name} gestartet."}

@app.post("/clients/{name}/stop")
def stop_client(name: str):
    name = name.upper()
    if name not in client_threads or not client_threads[name].is_alive():
        raise HTTPException(status_code=400, detail="Client not running")

    # Signal thread to stop
    logger.info(f"Stoppe Client {name}...")
    stop_events[name].set()

    # Wait briefly for thread to exit (deregistration happens in eureka_lifecycle)
    thread = client_threads[name]
    thread.join(timeout=10)

    if thread.is_alive():
        logger.warning(f"Client {name} konnte nicht innerhalb von 10 Sekunden gestoppt werden.")
    else:
        logger.info(f"Client {name} erfolgreich gestoppt und deregistriert.")

    return {"message": f"Client {name} stopped and deregistered."}

@app.get("/clients/{name}/logs")
def stream_logs(name: str):
    name = name.upper()
    log_path = f"logs/{name}.log"
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="Logfile nicht gefunden")

    def log_streamer():
        with open(log_path, "r") as f:
            while True:
                line = f.readline()
                if line:
                    yield line
                else:
                    time.sleep(1)

    return StreamingResponse(log_streamer(), media_type="text/plain")