# metrics_exporter.py
import os
import json # <-- Neu hinzugefügt für JSON-Ausgabe
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Importiere die MetricsStore-Klasse aus der Eureka-Client-Bibliothek
from eureka_client_lib import MetricsStore

def create_metrics_handler(metrics_store_instance: MetricsStore, app_config: dict): # <-- app_config als neues Argument
    """
    Eine Fabrikfunktion, die eine CustomMetricsHandler-Klasse erstellt.
    Diese Klasse hat Zugriff auf die übergebene MetricsStore-Instanz
    und die Anwendungs-Konfigurationsdaten.
    """
    class CustomMetricsHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/metrics':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain; version=0.0.4; charset=utf-8')
                self.end_headers()
                self.wfile.write(self.generate_prometheus_metrics().encode('utf-8'))
            elif self.path == '/info': 
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8') 
                self.end_headers()
                # Gebe die gesamte Konfiguration als schön formatierten JSON-String aus
                self.wfile.write(json.dumps(app_config, indent=2).encode('utf-8')) # <-- Zugriff auf app_config
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'Not Found')

        def generate_prometheus_metrics(self) -> str:
            """
            Generiert die Metriken im Prometheus-Textformat.
            Greift über die äußere Funktion auf die metrics_store_instance zu.
            """
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
    
    return CustomMetricsHandler

def run_metrics_web_server(metrics_store_instance: MetricsStore, app_config: dict, host: str, port: int): # <-- app_config als neues Argument
    """
    Startet einen einfachen HTTP-Webserver in einem Thread, der Metriken und Info exponiert.
    """
    # Erstelle den Handler mit der MetricsStore-Instanz und der App-Konfiguration
    handler_class = create_metrics_handler(metrics_store_instance, app_config)
    server_address = (host, port)
    httpd = HTTPServer(server_address, handler_class)
    # Ausgabe im Log, dass der Info-Endpunkt verfügbar ist
    print(f"Metrics web server running on http://{host}:{port}/metrics and http://{host}:{port}/info")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("Metrics web server stopped.")
