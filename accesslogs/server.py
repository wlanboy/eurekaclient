import http.server
import socketserver
from datetime import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import re

LOG_DIR = './logs'
LOG_FILENAME_PREFIX = 'access_log'

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

class AccessFormatter(logging.Formatter):
    def format(self, record):
        return record.msg

access_logger = logging.getLogger('access_log')
access_logger.setLevel(logging.INFO)

handler = TimedRotatingFileHandler(
    os.path.join(LOG_DIR, LOG_FILENAME_PREFIX),
    when="midnight",
    interval=1,
    backupCount=30,
    encoding='utf-8'
)
handler.setFormatter(AccessFormatter())
access_logger.addHandler(handler)

class EurekaHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  
        now = datetime.now()
        # Format: [dd/MMM/yyyy:HH:mm:ss ZZZ]
        timestamp = now.strftime('[%d/%b/%Y:%H:%M:%S +0000]') 

        # Request Line (Methode, Pfad, Protokoll)
        request_line = f"{self.command} {self.path} {self.request_version}"

        status_code = self.send_response_only 
        response_status = args[1] if len(args) > 1 else '?' 

        source_ip = self.client_address[0]

        referer = self.headers.get('Referer', '-')
        user_agent = self.headers.get('User-Agent', '-')

        x_forwarded_for = self.headers.get('X-Forwarded-For', '-')
        x_forwarded_proto = self.headers.get('X-Forwarded-Proto', '-')

        log_entry = (
            f"{source_ip} - {timestamp} - \"{request_line}\" - {response_status}"
            f" \"{referer}\" \"{user_agent}\" \"{x_forwarded_for}\" \"{x_forwarded_proto}\""
        )
        access_logger.info(log_entry)

    def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Eureka ist offline")
    _last_sent_status = 200

    def send_response(self, code, message=None):
        self._last_sent_status = code
        super().send_response(code, message)

    def end_headers(self):
        super().end_headers()

PORT = 8000
IP = "0.0.0.0"

if __name__ == "__main__":
    print(f"Start web server dummy. Access Logs will be generated here: '{os.path.abspath(LOG_DIR)}'")
    with socketserver.TCPServer((IP, PORT), EurekaHandler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()
