# metrics_exporter.py
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Any, Type

# Importiere die MetricsStore-Klasse aus der Eureka-Client-Bibliothek
from eureka_client_lib import MetricsStore

# Logger für den Metrics Exporter
logger = logging.getLogger(__name__)

def create_metrics_handler(metrics_store_instance: MetricsStore, app_config: Dict[str, Any]) -> Type[BaseHTTPRequestHandler]:
    """
    Eine Fabrikfunktion, die eine CustomMetricsHandler-Klasse erstellt.
    Diese Klasse hat Zugriff auf die übergebene MetricsStore-Instanz
    und die Anwendungs-Konfigurationsdaten.
    """
    if metrics_store_instance is None:
        raise ValueError("metrics_store_instance darf nicht None sein")
    if app_config is None:
        raise ValueError("app_config darf nicht None sein")

    class CustomMetricsHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            """Überschreibe log_message um HTTP-Anfragen zu unterdrücken"""
            pass

        def do_GET(self) -> None:
            try:
                if self.path == '/metrics':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain; version=0.0.4; charset=utf-8')
                    self.end_headers()
                    metrics_output = self.generate_prometheus_metrics()
                    self.wfile.write(metrics_output.encode('utf-8'))
                elif self.path == '/info':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.end_headers()
                    json_output = json.dumps(app_config, indent=2)
                    self.wfile.write(json_output.encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'Not Found')
            except Exception as e:
                logger.exception(f"Fehler beim Verarbeiten der Anfrage {self.path}: {e}")
                try:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(b'Internal Server Error')
                except Exception:
                    pass

        def generate_prometheus_metrics(self) -> str:
            """
            Generiert die Metriken im Prometheus-Textformat.
            Greift über die äußere Funktion auf die metrics_store_instance zu.
            """
            try:
                metrics_data = metrics_store_instance.get_metrics_data()
                output = []

                output.append("# HELP python_eureka_successful_registrations_total Total number of successful service registrations.")
                output.append("# TYPE python_eureka_successful_registrations_total counter")
                output.append(f"python_eureka_successful_registrations_total {metrics_data['successful_registrations_total']}")

                output.append("\n# HELP python_eureka_registration_errors_total Total number of service registration errors.")
                output.append("# TYPE python_eureka_registration_errors_total counter")
                output.append(f"python_eureka_registration_errors_total {metrics_data['registration_errors_total']}")

                output.append("\n# HELP python_eureka_service_registered Status of service registration (1 if registered, 0 otherwise).")
                output.append("# TYPE python_eureka_service_registered gauge")
                for service_name, status in metrics_data['service_registered_status'].items():
                    output.append(f"python_eureka_service_registered{{service_name=\"{service_name}\"}} {status}")

                return "\n".join(output) + "\n"
            except Exception as e:
                logger.exception(f"Fehler beim Generieren der Prometheus-Metriken: {e}")
                return "# Error generating metrics\n"

    return CustomMetricsHandler

def run_metrics_web_server(metrics_store_instance: MetricsStore, app_config: Dict[str, Any], host: str, port: int) -> None:
    """
    Startet einen einfachen HTTP-Webserver in einem Thread, der Metriken und Info exponiert.
    """
    try:
        # Erstelle den Handler mit der MetricsStore-Instanz und der App-Konfiguration
        handler_class = create_metrics_handler(metrics_store_instance, app_config)
        server_address = (host, port)
        httpd = HTTPServer(server_address, handler_class)

        logger.info(f"Metrics web server running on http://{host}:{port}/metrics and http://{host}:{port}/info")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Metrics web server shutdown signal empfangen.")
        finally:
            httpd.server_close()
            logger.info("Metrics web server stopped.")
    except Exception as e:
        logger.exception(f"Fehler beim Starten des Metrics Web Servers: {e}")
        raise
