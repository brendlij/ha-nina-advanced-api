# N.I.N.A. Advanced API – Home Assistant Integration

HACS-Integration für [N.I.N.A.](https://nighttime-imaging.eu/) über das
[Advanced API Plugin](https://github.com/christian-photo/ninaAPI) von Christian Palm.

## Status: v0.1 (Grundgerüst)

Aktuell abgedeckt:
- Config Flow (Host/Port, kein Auth nötig – das Plugin bietet aktuell keinen API-Key)
- Verbindungsstatus (`binary_sensor.connected`)
- Mount: RA/Dec/Alt/Az, Tracking/Parked/Slewing, Park/Unpark/Home-Buttons
- Kamera: Temperatur, Kühlerleistung, Verbunden/Kühlung aktiv

Geplant (v0.2+):
- WebSocket-Listener für Live-Push statt reinem 30s-Poll
- Filterwheel, Focuser, Rotator, Dome/Roof, Guider, Safety Monitor, Flat Panel
- Sequenz-Steuerung (Start/Stop/Pause) + Fortschritts-Sensor
- Options Flow (Poll-Intervall)
- Diagnostics-Export

## Voraussetzungen

- N.I.N.A. mit installiertem und aktiviertem **Advanced API** Plugin
  (Optionen → Plugins → Advanced API → "API Enabled" = ON)
- Der Rechner mit N.I.N.A. muss im lokalen Netz von Home Assistant aus erreichbar sein
- Standardport: `1888`

## Installation (HACS – Custom Repository, solange nicht im Default-Store)

1. HACS → Integrationen → ⋮ → Benutzerdefinierte Repositories
2. URL dieses Repos eintragen, Kategorie "Integration"
3. "N.I.N.A. Advanced API" installieren, Home Assistant neu starten
4. Einstellungen → Geräte & Dienste → Integration hinzufügen → "N.I.N.A. Advanced API"
5. Host/IP und Port (Standard 1888) eingeben

## Entwicklung

```bash
# Symlink in eine lokale HA-Testinstanz
ln -s $(pwd)/custom_components/nina_api /path/to/config/custom_components/nina_api
```

Wichtig: Die exakten Query-Parameter einiger Aktions-Endpunkte (z. B. Kamera-Kühlung,
Tracking-Modi) sind in diesem Grundgerüst nach bestem Wissen aus der öffentlichen
[API-Doku](https://bump.sh/christian-photo/doc/advanced-api/) übernommen, aber noch
**nicht gegen eine echte laufende NINA-Instanz verifiziert**. Vor produktivem Einsatz
gegen das eigene Setup testen und ggf. in `api.py` anpassen.
