# eureka_client_lib.py
import requests
import threading
import os
import socket
import logging
import time
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional

EUREKA_SERVER_URL = os.getenv("EUREKA_SERVER_URL", "http://localhost:8761/eureka/apps/")

class MetricsStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.successful_registrations_total: int = 0
        self.registration_errors_total: int = 0
        self.service_registered_status: Dict[str, int] = {}

    def increment_successful_registrations(self) -> None:
        with self._lock:
            self.successful_registrations_total += 1

    def increment_registration_errors(self) -> None:
        with self._lock:
            self.registration_errors_total += 1

    def set_service_registered_status(self, service_name: str, status: int) -> None:
        with self._lock:
            self.service_registered_status[service_name] = status

    def get_metrics_data(self) -> Dict[str, Any]:
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

def register_instance(service_data: Dict[str, Any], metrics_store: MetricsStore, logger: Optional[logging.Logger] = None) -> bool:
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
        secure_port_enabled = "true"
        port_enabled = "false"
        scheme = "https"
        active_port = service_data.get("securePort", secure_port)
    else:
        secure_port_enabled = "false"
        port_enabled = "true"
        scheme = "http"
        active_port = service_data.get("httpPort", http_port)

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
            if logger:
                logger.info("Erfolgreich bei Eureka registriert.")
            metrics_store.increment_successful_registrations()
            metrics_store.set_service_registered_status(service_name, 1)
            return True
        else:
            if logger:
                logger.error(f"Fehler bei der Registrierung ({response.status_code}): {response.text}")
            metrics_store.increment_registration_errors()
            metrics_store.set_service_registered_status(service_name, 0)
            return False
    except requests.exceptions.ConnectionError as e:
        if logger:
            logger.error(f"Verbindungsfehler bei Registrierung: {e}")
        metrics_store.increment_registration_errors()
        metrics_store.set_service_registered_status(service_name, 0)
        return False
    except Exception as e:
        if logger:
            logger.exception(f"Unerwarteter Fehler bei Registrierung: {e}")
        metrics_store.increment_registration_errors()
        metrics_store.set_service_registered_status(service_name, 0)
        return False

def send_heartbeat(service_data: Dict[str, Any], metrics_store: MetricsStore, logger: Optional[logging.Logger] = None, max_retries: int = 3) -> bool:
    """
    Sendet einen Heartbeat an Eureka mit Retry-Mechanismus.
    Bei 404 wird eine Neu-Registrierung durchgeführt.
    """
    service_name = service_data["serviceName"].upper()
    host_name = service_data["hostName"]
    http_port = service_data["httpPort"]
    instance_id = f"{host_name}:{service_name}:{http_port}"
    heartbeat_url = f"{EUREKA_SERVER_URL}{service_name}/{instance_id}"

    attempt = 0
    while attempt < max_retries:
        attempt += 1
        try:
            response = requests.put(heartbeat_url)
            if response.status_code == 200:
                if logger:
                    logger.info(f"Heartbeat erfolgreich gesendet (Versuch {attempt}).")
                return True
            elif response.status_code == 404:
                if logger:
                    logger.warning("Heartbeat 404 – Instanz nicht gefunden. Starte Neu-Registrierung.")
                # Neu-Registrierung durchführen
                if register_instance(service_data, metrics_store, logger=logger):
                    if logger:
                        logger.info("Neu-Registrierung erfolgreich. Sende Heartbeat erneut.")
                    # nach erfolgreicher Registrierung direkt neuen Versuch starten
                    continue
                else:
                    if logger:
                        logger.error("Neu-Registrierung fehlgeschlagen.")
                    return False
            else:
                if logger:
                    logger.warning(f"Fehler beim Heartbeat ({response.status_code}): {response.text}")
        except requests.exceptions.ConnectionError as e:
            if logger:
                logger.error(f"Verbindungsfehler beim Heartbeat: {e}")
        except Exception as e:
            if logger:
                logger.exception(f"Unerwarteter Fehler beim Heartbeat: {e}")

        # Backoff vor erneutem Versuch
        wait_time = min(2 * attempt, 10)
        if logger:
            logger.info(f"Warte {wait_time}s vor erneutem Heartbeat-Versuch...")
        time.sleep(wait_time)

    if logger:
        logger.error("Alle Heartbeat-Versuche fehlgeschlagen.")
    return False

def deregister_instance(service_data: Dict[str, Any], metrics_store: MetricsStore, logger: Optional[logging.Logger] = None) -> None:
    service_name = service_data["serviceName"].upper()
    host_name = service_data["hostName"]
    http_port = service_data["httpPort"]
    instance_id = f"{host_name}:{service_name}:{http_port}"
    deregister_url = f"{EUREKA_SERVER_URL}{service_name}/{instance_id}"

    if logger:
        logger.info(f"Versuche Deregistrierung von {deregister_url}")

    try:
        response = requests.delete(deregister_url)
        if response.status_code == 200:
            if logger:
                logger.info("Erfolgreich von Eureka deregistriert.")
            metrics_store.set_service_registered_status(service_name, 0)
        else:
            if logger:
                logger.warning(f"Fehler bei Deregistrierung ({response.status_code}): {response.text}")
    except requests.exceptions.ConnectionError as e:
        if logger:
            logger.error(f"Verbindungsfehler bei Deregistrierung: {e}")
    except Exception as e:
        if logger:
            logger.exception(f"Unerwarteter Fehler bei Deregistrierung: {e}")

def eureka_lifecycle(service_data: Dict[str, Any], metrics_store: MetricsStore, stop_event: threading.Event, logger: Optional[logging.Logger] = None) -> None:
    """
    Verwaltet den Lebenszyklus eines Services bei Eureka.
    stop_event wird verwendet, um den Thread sauber zu beenden.
    """
    lease_renewal_interval = service_data.get("leaseInfo", {}).get("renewalIntervalInSecs", 20)

    if logger:
        logger.info("Starte Lebenszyklus.")

    # --- Registrierung mit Retry ---
    max_reg_retries = 10
    reg_attempt = 0
    registered = False

    while reg_attempt < max_reg_retries and not registered and not stop_event.is_set():
        reg_attempt += 1
        if logger:
            logger.info(f"Registrierungsversuch {reg_attempt}/{max_reg_retries}")

        registered = register_instance(service_data, metrics_store, logger=logger)
        if not registered:
            wait_time = min(5 * reg_attempt, 30)  # Exponential Backoff bis max. 30s
            if logger:
                logger.warning(f"Registrierung fehlgeschlagen, erneuter Versuch in {wait_time}s...")
            stop_event.wait(wait_time)

    if not registered:
        if logger:
            logger.error("Registrierung endgültig fehlgeschlagen. Lifecycle beendet.")
        return

    if logger:
        logger.info("Registrierung erfolgreich. Starte Heartbeat-Schleife.")

    # --- Heartbeat-Schleife ---
    while not stop_event.is_set():
        # send_heartbeat hat bereits einen eingebauten Retry-Mechanismus
        hb_success = send_heartbeat(service_data, metrics_store=metrics_store, logger=logger, max_retries=3)

        if not hb_success:
            if logger:
                logger.error("Heartbeat endgültig fehlgeschlagen.")
            # Bei kritischem Fehler Lifecycle beenden
            break

        # Warte bis zum nächsten Heartbeat oder Stop-Signal
        if stop_event.wait(timeout=lease_renewal_interval):
            if logger:
                logger.info("Stopp-Signal empfangen. Beende Heartbeat-Schleife.")
            break

    # --- Deregistrierung beim Shutdown ---
    if logger:
        logger.info("Deregistriere Service von Eureka...")
    deregister_instance(service_data, metrics_store, logger=logger)