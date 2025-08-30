# eureka_client_lib.py
import json
import requests
import time
import threading
import uuid
import os
import socket
import sys
import xml.etree.ElementTree as ET # Importiere die XML-Bibliothek

# --- Eureka Konfiguration ---
EUREKA_SERVER_URL = os.getenv("EUREKA_SERVER_URL", "http://localhost:8761/eureka/apps/")

# --- Metrics Store Class ---
class MetricsStore:
    """
    Speichert und verwaltet die Metriken des Eureka Clients.
    Thread-sicher durch Verwendung eines Locks.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self.successful_registrations_total = 0
        self.registration_errors_total = 0
        # Speichert {service_name: 0 oder 1} für den Registrierungsstatus jedes Services
        self.service_registered_status = {}

    def increment_successful_registrations(self):
        with self._lock:
            self.successful_registrations_total += 1

    def increment_registration_errors(self):
        with self._lock:
            self.registration_errors_total += 1

    def set_service_registered_status(self, service_name, status: int):
        # status: 1 für registriert, 0 für deregistriert/fehlgeschlagen
        with self._lock:
            self.service_registered_status[service_name] = status

    def get_metrics_data(self):
        """
        Gibt eine thread-sichere Kopie der aktuellen Metrikdaten zurück.
        """
        with self._lock:
            return {
                "successful_registrations_total": self.successful_registrations_total,
                "registration_errors_total": self.registration_errors_total,
                "service_registered_status": self.service_registered_status.copy()
            }

# --- Hilfsfunktionen für Eureka-Interaktion ---

def get_ip_address(hostname: str) -> str:
    """
    Ermittelt die IP-Adresse für einen gegebenen Hostnamen.
    Gibt '127.0.0.1' zurück, wenn die IP nicht ermittelt werden kann.
    """
    try:
        ip_addr = socket.gethostbyname(hostname)
        return ip_addr
    except socket.gaierror:
        print(f"Warnung: IP-Adresse für Hostname '{hostname}' konnte nicht ermittelt werden. Verwende '127.0.0.1'.")
        return "127.0.0.1"

def register_instance(service_data: dict, metrics_store: MetricsStore) -> bool:
    """Registriert eine Instanz bei Eureka."""
    service_name = service_data["serviceName"].upper()
    host_name = service_data["hostName"]
    http_port = service_data["httpPort"]
    instance_id = f"{host_name}:{service_name}:{http_port}"
    app_url = f"{EUREKA_SERVER_URL}{service_name}"

    ip_address = get_ip_address(host_name)
    secure_port = service_data.get("securePort", 443)
    secure_port_enabled = "true" if secure_port > 0 else "false"
    data_center_info_name = service_data.get("dataCenterInfoName", "MyOwn")

    # --- XML-Payload Generierung ---
    # Nutze das Beispiel-JSON als Vorlage für die XML-Struktur
    # (Beachte, dass das ursprüngliche "JSON" eine XML-Struktur mit speziellen Attributen darstellt)

    # Das <instance>-Element wird direkt als Kind von <application> hinzugefügt
    instance_element = ET.Element("instance")

    # Kinder-Elemente
    ET.SubElement(instance_element, "instanceId").text = instance_id
    ET.SubElement(instance_element, "hostName").text = host_name
    ET.SubElement(instance_element, "app").text = service_name
    ET.SubElement(instance_element, "ipAddr").text = ip_address
    ET.SubElement(instance_element, "vipAddress").text = service_name.lower() 
    ET.SubElement(instance_element, "secureVipAddress").text = service_name.lower() 
    ET.SubElement(instance_element, "status").text = "UP"

    # <port> mit Attribut
    port_element = ET.SubElement(instance_element, "port", attrib={"enabled": "true"})
    port_element.text = str(http_port)

    # <securePort> mit Attribut
    DISABLE_SSL = os.getenv("DISABLE_SSL", "false")
    if DISABLE_SSL == "true": 
        secure_port_enabled = "false"

    secure_port_element = ET.SubElement(instance_element, "securePort", attrib={"enabled": secure_port_enabled})
    secure_port_element.text = str(secure_port)
    
    # URLs
    ET.SubElement(instance_element, "homePageUrl").text = f"http://{host_name}:{http_port}/"
    ET.SubElement(instance_element, "statusPageUrl").text = f"http://{host_name}:{http_port}{service_data['infoEndpointPath']}"
    ET.SubElement(instance_element, "healthCheckUrl").text = f"http://{host_name}:{http_port}{service_data['healthEndpointPath']}"

    # <dataCenterInfo> mit Attribut und Kinder-Element
    data_center_info_element = ET.SubElement(instance_element, "dataCenterInfo",
                                             attrib={"class": "com.netflix.appinfo.InstanceInfo$DefaultDataCenterInfo"})
    ET.SubElement(data_center_info_element, "name").text = data_center_info_name
    
    # XML-Baum in einen String umwandeln
    xml_payload = ET.tostring(instance_element, encoding='utf-8', xml_declaration=True).decode('utf-8')
    
    # --- Ende der XML-Payload Generierung ---

    headers = {
        "Content-Type": "application/xml",  # WICHTIG: Content-Type auf XML setzen
        "Accept": "application/xml"
    }

    print(f"[{service_name}] Versuche Registrierung bei Eureka unter {app_url} mit IP: {ip_address}, SecurePort: {secure_port}, DataCenter: {data_center_info_name}")
    print(f"[{service_name}] Sende Payload:\n{xml_payload}")

    try:
        response = requests.post(app_url, data=xml_payload, headers=headers)
        if response.status_code == 204: # 204 No Content ist der erwartete Success-Code von Eureka
            print(f"[{service_name}] Erfolgreich bei Eureka registriert.")
            metrics_store.increment_successful_registrations()
            metrics_store.set_service_registered_status(service_name, 1)
            return True
        else:
            print(f"[{service_name}] Fehler bei der Registrierung ({response.status_code}): {response.text}")
            metrics_store.increment_registration_errors()
            metrics_store.set_service_registered_status(service_name, 0)
            return False
    except requests.exceptions.ConnectionError as e:
        print(f"[{service_name}] Fehler bei der Verbindung zu Eureka: {e}")
        metrics_store.increment_registration_errors()
        metrics_store.set_service_registered_status(service_name, 0)
        return False
    except Exception as e:
        print(f"[{service_name}] Ein unerwarteter Fehler ist aufgetreten: {e}")
        metrics_store.increment_registration_errors()
        metrics_store.set_service_registered_status(service_name, 0)
        return False

def send_heartbeat(service_data: dict):
    """Sendet einen Keepalive (Heartbeat) an Eureka."""
    service_name = service_data["serviceName"].upper()
    host_name = service_data["hostName"]
    http_port = service_data["httpPort"]
    instance_id = f"{host_name}:{service_name}:{http_port}"
    heartbeat_url = f"{EUREKA_SERVER_URL}{service_name}/{instance_id}"

    try:
        response = requests.put(heartbeat_url)
        if response.status_code == 200:
            print(f"[{service_name}] Heartbeat erfolgreich gesendet.") # Auskommentiert für weniger Log-Output
            pass
        else:
            print(f"[{service_name}] Fehler beim Senden des Heartbeats ({response.status_code}): {response.text}")
    except requests.exceptions.ConnectionError as e:
        print(f"[{service_name}] Fehler bei der Verbindung zu Eureka für Heartbeat: {e}")

def deregister_instance(service_data: dict, metrics_store: MetricsStore):
    """Deregistriert eine Instanz von Eureka."""
    service_name = service_data["serviceName"].upper()
    host_name = service_data["hostName"]
    http_port = service_data["httpPort"]
    instance_id = f"{host_name}:{service_name}:{http_port}"
    deregister_url = f"{EUREKA_SERVER_URL}{service_name}/{instance_id}"

    print(f"[{service_name}] Versuche Deregistrierung von Eureka unter {deregister_url}")

    try:
        response = requests.delete(deregister_url)
        if response.status_code == 200:
            print(f"[{service_name}] Erfolgreich von Eureka deregistriert.")
            metrics_store.set_service_registered_status(service_name, 0) # Status auf 0 setzen
        else:
            print(f"[{service_name}] Fehler bei der Deregistrierung ({response.status_code}): {response.text}")
    except requests.exceptions.ConnectionError as e:
        print(f"[{service_name}] Fehler bei der Verbindung zu Eureka für Deregistrierung: {e}")

def eureka_lifecycle(service_data: dict, metrics_store: MetricsStore, stop_event: threading.Event):
    """
    Verwaltet den Lebenszyklus eines Services bei Eureka.
    stop_event wird verwendet, um den Thread sauber zu beenden.
    """
    service_name = service_data["serviceName"].upper()
    
    # Standard-Lease-Informationen, wenn nicht in service_data vorhanden
    lease_renewal_interval = service_data.get("leaseInfo", {}).get("renewalIntervalInSecs", 20)

    # Registrierung versuchen
    if register_instance(service_data, metrics_store):
        # Heartbeat-Schleife, solange kein Stopp-Signal empfangen wird
        while not stop_event.is_set():
            send_heartbeat(service_data)
            # wait() gibt True zurück, wenn das Event gesetzt wurde, False bei Timeout
            if stop_event.wait(timeout=lease_renewal_interval):
                print(f"[{service_name}] Stopp-Signal für Heartbeat-Schleife empfangen.")
                break # Schleife beenden, da Stopp-Signal empfangen
    else:
        print(f"[{service_name}] Registrierung für Service '{service_name}' fehlgeschlagen. Starte keine Heartbeat-Schleife.")
