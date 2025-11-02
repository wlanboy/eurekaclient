from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import threading
import os
import json
import random

from eureka_client_lib import eureka_lifecycle, deregister_instance, MetricsStore

app = FastAPI()
metrics_store = MetricsStore()

# Static files (HTML, JS, CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")

# In-memory registry
clients = {}
client_threads = {}
stop_events = {}

import random

EUREKA_SERVERS_FILE = "eureka_servers.json"
EUREKA_SERVER_URLS = []

# Lade Liste von Eureka-Servern
if os.path.exists(EUREKA_SERVERS_FILE):
    try:
        with open(EUREKA_SERVERS_FILE, "r") as f:
            config = json.load(f)
            EUREKA_SERVER_URLS = config.get("servers", [])
            print(f"{len(EUREKA_SERVER_URLS)} Eureka-Server geladen.")
    except Exception as e:
        print(f"Fehler beim Laden von {EUREKA_SERVERS_FILE}: {e}")
else:
    print(f"Warnung: {EUREKA_SERVERS_FILE} nicht gefunden. Bitte erstellen mit 'servers' Liste.")


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
        print(f"{len(clients)} Clients aus {CONFIG_FILE} geladen.")
    except Exception as e:
        print(f"Fehler beim Laden von {CONFIG_FILE}: {e}")

def save_clients_to_file():
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(list(clients.values()), f, indent=2)
    except Exception as e:
        print(f"Fehler beim Speichern von Clients: {e}")

class ClientConfig(BaseModel):
    serviceName: str
    healthEndpointPath: str
    infoEndpointPath: str
    httpPort: int
    securePort: int
    hostName: str
    dataCenterInfoName: str
    leaseInfo: dict = {
        "renewalIntervalInSecs": 30,
        "durationInSecs": 90
    }

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
        success = False
        attempts = 0
        tried = set()

        while not success and len(tried) < len(EUREKA_SERVER_URLS):
            server = random.choice(EUREKA_SERVER_URLS)
            if server in tried:
                continue
            tried.add(server)
            service_data["eurekaServerUrl"] = server
            try:
                eureka_lifecycle(service_data, metrics_store, stop_event)
                success = True
            except Exception as e:
                print(f"Verbindung zu {server} fehlgeschlagen für {name}: {e}")
                continue

        if not success:
            print(f"Alle Eureka-Server fehlgeschlagen für {name}.")

    thread = threading.Thread(target=run, daemon=True)
    client_threads[name] = thread
    thread.start()
    return {"message": f"Client {name} gestartet (versucht mehrere Eureka-Server)."}

@app.post("/clients/{name}/stop")
def stop_client(name: str):
    name = name.upper()
    if name not in client_threads or not client_threads[name].is_alive():
        raise HTTPException(status_code=400, detail="Client not running")

    # Signal thread to stop
    stop_events[name].set()

    # Wait briefly for thread to exit
    thread = client_threads[name]
    thread.join(timeout=5)

    # Deregister from Eureka
    try:
        deregister_instance(clients[name], metrics_store)
        print(f"{name} deregistered from Eureka.")
    except Exception as e:
        print(f"Fehler beim Deregistrieren von {name}: {e}")

    return {"message": f"Client {name} stopped and deregistered."}
