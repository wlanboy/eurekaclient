import os
import re
from collections import defaultdict

def analyze_log_file(log_file_path):
    """
    Analysiert ein Logfile und extrahiert eindeutige Source-IPs pro Class B Subnetzwerk.
    """
    # Dictionary, um IPs nach Class B Subnetzwerk zu gruppieren
    # Format: {'192.168': {'192.168.1.1', '192.168.1.2'}, '10.0': {'10.0.0.1'}}
    class_b_networks = defaultdict(set) 
    
    ip_pattern = re.compile(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s-\s\[')

    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = ip_pattern.match(line)
                if match:
                    source_ip = match.group(1)
                    if is_valid_ipv4(source_ip):
                        parts = source_ip.split('.')
                        if len(parts) == 4:
                            class_b_prefix = f"{parts[0]}.{parts[1]}"
                            class_b_networks[class_b_prefix].add(source_ip)
    except FileNotFoundError:
        print(f"Fehler: Logfile '{log_file_path}' nicht gefunden.")
        return None
    except Exception as e:
        print(f"Ein Fehler ist beim Lesen des Logfiles aufgetreten: {e}")
        return None

    return class_b_networks

def is_valid_ipv4(ip):
    """Überprüft, ob ein String eine gültige IPv4-Adresse ist."""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        try:
            num = int(part)
            if not (0 <= num <= 255):
                return False
        except ValueError:
            return False
    return True

def display_results(networks_data):
    """Zeigt die extrahierten Daten in einer formatierten Tabelle an."""
    if not networks_data:
        print("Keine IP-Adressen gefunden oder Logfile war leer.")
        return

    print("\n--- Analyse der Class B Netzwerke ---")
    
    sorted_networks = sorted(networks_data.keys())

    for prefix in sorted_networks:
        ips = sorted(list(networks_data[prefix])) 
        print(f"\nSubnetzwerk: {prefix}.0.0/16")
        print("--------------------------")
        for ip in ips:
            print(f"  - {ip}")
        print(f"Eindeutige IPs in diesem Subnetz: {len(ips)}")
    print("\n--------------------------")


# --- Hauptprogramm ---
if __name__ == "__main__":
    LOG_FILE_PATH = os.path.join('./logs', 'access_log') 
    print(f"Load Logfile: {LOG_FILE_PATH}")

    network_data = analyze_log_file(LOG_FILE_PATH)
    if network_data:
        display_results(network_data)
