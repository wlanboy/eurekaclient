# Eureka Access Log Server

Dieses Tool dient als **Dummy-Ersatz für einen abgeschalteten Eureka-Server**, um herauszufinden, welche Clients ihn noch aktiv ansprechen.

## Hintergrund

Wenn ein Eureka-Server abgeschaltet werden soll, ist oft unklar, welche Dienste ihn noch registrieren oder abfragen. Statt den Server einfach abzuschalten und Fehler in Produktion zu riskieren, wird dieser Dummy-Server an seiner Stelle betrieben. Er antwortet auf alle Anfragen mit `200 OK` und der Meldung `"Eureka ist offline"`, protokolliert dabei aber jede eingehende Verbindung mit vollständigen Zugriffsinformationen.

## Komponenten

### `server.py` — Dummy HTTP-Server

Startet einen einfachen HTTP-Server (Standard-Port `8000`), der:

- auf **alle GET-Anfragen** mit `200 OK` antwortet (verhindert Fehler auf Client-Seite)
- für jede Anfrage ein **Access Log** im Apache-ähnlichen Format schreibt:

  ```text
  <source-ip> - [timestamp] - "<methode pfad protokoll>" - <status> "<referer>" "<user-agent>" "<x-forwarded-for>" "<x-forwarded-proto>"
  ```

- Logs täglich rotiert und **30 Tage** aufbewahrt (unter `./logs/`)

**Starten:**

```bash
python server.py
```

### `table.py` — Log-Analyse

Liest das aktuelle Access Log und gruppiert alle zugreifenden IPs nach **Class-B-Subnetz** (`/16`), um einen Überblick zu geben, aus welchen Netzbereichen noch Anfragen kommen.

**Ausgabe-Beispiel:**

```text
Subnetzwerk: 10.20.0.0/16
--------------------------
  - 10.20.1.15
  - 10.20.3.42
Eindeutige IPs in diesem Subnetz: 2
```

**Ausführen:**

```bash
python table.py
```

## Typischer Ablauf

1. Eureka-Server abschalten / DNS-Eintrag auf diesen Dummy umleiten
2. `server.py` starten
3. Einige Tage warten, bis alle Clients ihre Registrierungsversuche geloggt haben
4. `table.py` ausführen, um die zugreifenden Clients zu identifizieren
5. Betroffene Teams informieren und Clients migrieren
