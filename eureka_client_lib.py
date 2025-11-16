# eureka_client_lib.py
import requests
import threading
import os
import socket
import logging
import xml.etree.ElementTree as ET

EUREKA_SERVER_URL = os.getenv("EUREKA_SERVER_URL", "http://localhost:8761/eureka/apps/")

class MetricsStore:
    def __init__(self):
        self._lock = threading.Lock()
        self.successful_registrations_total = 0
        self.registration_errors_total = 0
        self.service_registered_status = {}

    def increment_successful_registrations(self):
        with self._lock:
            self.successful_registrations_total += 1

    def increment_registration_errors(self):
        with self._lock:
            self.registration_errors_total += 1

    def set_service_registered_status(self, service_name, status: int):
        with self._lock:
            self.service_registered_status[service_name] = status

    def get_metrics_data(self):
        with self._lock:
            return {
                "successful_registrations_total": self.successful_registrations_total,
                "registration_errors_total": self.registration_errors_total,
                "service_registered_status": self.service_registered_status.copy()
            }

def get_ip_address(hostname: str) -> str:
    try:
        ip_addr = socket.gethostbyname(hostname)
        return ip_addr
    except socket.gaierror:
        print(f"Warnung: IP-Adresse für Hostname '{hostname}' konnte nicht ermittelt werden. Verwende '127.0.0.1'.")
        return "127.0.0.1"

def register_instance(service_data: dict, metrics_store: MetricsStore, logger=None) -> bool:
    service_name = service_data["serviceName"].upper()
    host_name = service_data["hostName"]
    http_port = service_data["httpPort"]
    instance_id = f"{host_name}:{service_name}:{http_port}"
    app_url = f"{EUREKA_SERVER_URL}{service_name}"

    ip_address = get_ip_address(host_name)
    secure_port = service_data.get("securePort", 443)
    data_center_info_name = service_data.get("dataCenterInfoName", "MyOwn")

    # Neues Feld sslPreferred aus services.json
    ssl_preferred = service_data.get("sslPreferred", False)

    if ssl_preferred:
        DISABLE_SSL = "false"
        secure_port_enabled = "true"
        port_enabled = "false"
        scheme = "https"
        active_port = service_data.get("securePort")
    else:
        DISABLE_SSL = "true"
        secure_port_enabled = "false"
        port_enabled = "true"
        scheme = "http"
        active_port = service_data.get("httpPort")

    instance_element = ET.Element("instance")
    ET.SubElement(instance_element, "instanceId").text = instance_id
    ET.SubElement(instance_element, "hostName").text = host_name
    ET.SubElement(instance_element, "app").text = service_name
    ET.SubElement(instance_element, "ipAddr").text = ip_address
    ET.SubElement(instance_element, "vipAddress").text = service_name.lower()
    ET.SubElement(instance_element, "secureVipAddress").text = service_name.lower()
    ET.SubElement(instance_element, "status").text = "UP"

    port_element = ET.SubElement(instance_element, "port", attrib={"enabled": port_enabled})
    port_element.text = str(http_port)

    secure_port_element = ET.SubElement(instance_element, "securePort", attrib={"enabled": secure_port_enabled})
    secure_port_element.text = str(secure_port)

    # URLs abhängig von SSL
    ET.SubElement(instance_element, "homePageUrl").text = f"{scheme}://{host_name}:{active_port}/"
    ET.SubElement(instance_element, "statusPageUrl").text = f"{scheme}://{host_name}:{active_port}{service_data['infoEndpointPath']}"
    ET.SubElement(instance_element, "healthCheckUrl").text = f"{scheme}://{host_name}:{active_port}{service_data['healthEndpointPath']}"

    data_center_info_element = ET.SubElement(instance_element, "dataCenterInfo",
                                             attrib={"class": "com.netflix.appinfo.InstanceInfo$DefaultDataCenterInfo"})
    ET.SubElement(data_center_info_element, "name").text = data_center_info_name

    xml_payload = ET.tostring(instance_element, encoding='utf-8', xml_declaration=True).decode('utf-8')

    print(f"[{service_name}] Versuche Registrierung bei Eureka unter {app_url} mit IP: {ip_address}, active_port: {active_port}, DataCenter: {data_center_info_name}, SSL: {ssl_preferred}")
    print(f"[{service_name}] Sende Payload:\n{xml_payload}")
    if logger:
        logger.info(f"Versuche Registrierung bei {app_url} mit IP: {ip_address}, active_port: {active_port}, DataCenter: {data_center_info_name}, SSL: {ssl_preferred}")
        logger.debug(f"XML-Payload:\n{xml_payload}")

    headers = {
        "Content-Type": "application/xml",
        "Accept": "application/xml"
    }

    try:
        response = requests.post(app_url, data=xml_payload, headers=headers)
        if response.status_code == 204:
            print(f"[{service_name}] Erfolgreich bei Eureka registriert.")
            if logger:
                logger.info("Erfolgreich bei Eureka registriert.")
            metrics_store.increment_successful_registrations()
            metrics_store.set_service_registered_status(service_name, 1)
            return True
        else:
            print(f"[{service_name}] Fehler bei der Registrierung ({response.status_code}): {response.text}")
            if logger:
                logger.error(f"Fehler bei der Registrierung ({response.status_code}): {response.text}")
            metrics_store.increment_registration_errors()
            metrics_store.set_service_registered_status(service_name, 0)
            return False
    except requests.exceptions.ConnectionError as e:
        print(f"[{service_name}] Fehler bei der Verbindung zu Eureka: {e}")
        if logger:
            logger.error(f"Verbindungsfehler bei Registrierung: {e}")
        metrics_store.increment_registration_errors()
        metrics_store.set_service_registered_status(service_name, 0)
        return False
    except Exception as e:
        print(f"[{service_name}] Ein unerwarteter Fehler ist aufgetreten: {e}")
        if logger:
            logger.exception(f"Unerwarteter Fehler bei Registrierung: {e}")
        metrics_store.increment_registration_errors()
        metrics_store.set_service_registered_status(service_name, 0)
        return False

def send_heartbeat(service_data: dict, logger=None):
    service_name = service_data["serviceName"].upper()
    host_name = service_data["hostName"]
    http_port = service_data["httpPort"]
    instance_id = f"{host_name}:{service_name}:{http_port}"
    heartbeat_url = f"{EUREKA_SERVER_URL}{service_name}/{instance_id}"

    try:
        response = requests.put(heartbeat_url)
        if response.status_code == 200:
            print(f"[{service_name}] Heartbeat erfolgreich gesendet.")
            if logger:
                logger.info("Heartbeat erfolgreich gesendet.")
        else:
            print(f"[{service_name}] Fehler beim Senden des Heartbeats ({response.status_code}): {response.text}")
            if logger:
                logger.warning(f"Fehler beim Heartbeat ({response.status_code}): {response.text}")
    except requests.exceptions.ConnectionError as e:
        print(f"[{service_name}] Fehler bei der Verbindung zu Eureka für Heartbeat: {e}")
        if logger:
            logger.error(f"Verbindungsfehler beim Heartbeat: {e}")

def deregister_instance(service_data: dict, metrics_store: MetricsStore, logger=None):
    service_name = service_data["serviceName"].upper()
    host_name = service_data["hostName"]
    http_port = service_data["httpPort"]
    instance_id = f"{host_name}:{service_name}:{http_port}"
    deregister_url = f"{EUREKA_SERVER_URL}{service_name}/{instance_id}"

    print(f"[{service_name}] Versuche Deregistrierung von Eureka unter {deregister_url}")
    if logger:
        logger.info(f"Versuche Deregistrierung von {deregister_url}")

    try:
        response = requests.delete(deregister_url)
        if response.status_code == 200:
            print(f"[{service_name}] Erfolgreich von Eureka deregistriert.")
            if logger:
                logger.info("Erfolgreich von Eureka deregistriert.")
            metrics_store.set_service_registered_status(service_name, 0)
        else:
            print(f"[{service_name}] Fehler bei der Deregistrierung ({response.status_code}): {response.text}")
            if logger:
                logger.warning(f"Fehler bei Deregistrierung ({response.status_code}): {response.text}")
    except requests.exceptions.ConnectionError as e:
        print(f"[{service_name}] Fehler bei der Verbindung zu Eureka für Deregistrierung: {e}")
        if logger:
            logger.error(f"Verbindungsfehler bei Deregistrierung: {e}")

def eureka_lifecycle(service_data: dict, metrics_store: MetricsStore, stop_event: threading.Event, logger=None):
    """
    Verwaltet den Lebenszyklus eines Services bei Eureka.
    stop_event wird verwendet, um den Thread sauber zu beenden.
    """
    service_name = service_data["serviceName"].upper()
    lease_renewal_interval = service_data.get("leaseInfo", {}).get("renewalIntervalInSecs", 20)

    print(f"[{service_name}] Starte Lebenszyklus.")
    if logger:
        logger.info("Starte Lebenszyklus.")

    # Registrierung versuchen
    if register_instance(service_data, metrics_store, logger=logger):
        print(f"[{service_name}] Registrierung erfolgreich. Starte Heartbeat-Schleife.")
        if logger:
            logger.info("Registrierung erfolgreich. Starte Heartbeat-Schleife.")

        # Heartbeat-Schleife, solange kein Stopp-Signal empfangen wird
        while not stop_event.is_set():
            send_heartbeat(service_data, logger=logger)
            if stop_event.wait(timeout=lease_renewal_interval):
                print(f"[{service_name}] Stopp-Signal für Heartbeat-Schleife empfangen.")
                if logger:
                    logger.info("Stopp-Signal empfangen. Beende Heartbeat-Schleife.")
                break
    else:
        print(f"[{service_name}] Registrierung fehlgeschlagen. Keine Heartbeat-Schleife gestartet.")
        if logger:
            logger.warning("Registrierung fehlgeschlagen. Keine Heartbeat-Schleife gestartet.")
