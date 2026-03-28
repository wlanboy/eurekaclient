# Eureka REST API – Beispiele

Dieses Verzeichnis enthält HTTP-Beispielanfragen für die Eureka REST API sowie eine Beispielantwort im XML-Format.

Offizielle API-Dokumentation: <https://github.com/Netflix/eureka/wiki/Eureka-REST-operations>

## Dateien

| Datei | Beschreibung |
| --- | --- |
| `register.http` | Registriert eine neue Service-Instanz beim Eureka-Server |
| `get.http` | Fragt alle Instanzen einer Applikation ab |
| `heartbeat.http` | Erneuert die Lease einer Instanz (Heartbeat / Keep-Alive) |
| `delete.http` | Meldet eine Instanz vom Eureka-Server ab |
| `service.xml` | Beispiel-XML-Antwort des Eureka-Servers für eine registrierte Applikation |

## Ablauf

Ein Eureka-Client durchläuft typischerweise folgende Schritte:

1. **Registrierung** (`register.http`) — beim Start einmalig, mit vollständigen Instanzdaten (IP, Port, Health-URL usw.)
2. **Heartbeat** (`heartbeat.http`) — alle 30 Sekunden, um die Lease zu verlängern (Standard: 90 s Ablaufzeit)
3. **Abfrage** (`get.http`) — um andere registrierte Instanzen einer Applikation zu ermitteln
4. **Abmeldung** (`delete.http`) — beim geordneten Herunterfahren

## Hinweise

- Der Eureka-Server läuft in den Beispielen unter `http://gmk:8761`
- Die Instanz-ID hat das Format `<hostname>:<appname>:<port>` (z. B. `gmk.local:SERVICEONE:8080`)
- HTTP-Dateien können direkt mit dem VS Code REST Client Plugin oder IntelliJ HTTP Client ausgeführt werden
