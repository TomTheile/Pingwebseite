# Website Ping Service

Eine Flask-basierte Webanwendung, die kontinuierlich eine angegebene Website anpingt, um zu verhindern, dass sie in den Ruhemodus wechselt.

## Funktionen

- Regelmäßiges Pingen einer Website in konfigurierbaren Intervallen
- Automatische Wiederholungsversuche bei fehlgeschlagenen Pings
- Discord-Webhook-Integration für Benachrichtigungen
- Benutzerauthentifizierung mit vordefiniertem Konto
- Läuft kontinuierlich im Hintergrund, selbst wenn der Browser geschlossen wird

## Installation

1. Repository klonen:
   ```
   git clone https://github.com/dein-benutzername/website-ping-service.git
   cd website-ping-service
   ```

2. Abhängigkeiten installieren:
   ```
   pip install -r requirements.txt
   ```

3. Anwendung starten:
   ```
   python main.py
   ```

## Konfiguration

- **URL**: Die zu überwachende Website-URL
- **Intervall**: Zeit zwischen Pings (in Minuten)
- **Discord-Webhook**: URL für Discord-Benachrichtigungen (optional)
- **Wiederholungsversuche**: Anzahl der Wiederholungen bei Fehlern
- **Benachrichtigungseinstellungen**: Wann Benachrichtigungen gesendet werden

## Hosting-Hinweise

Diese Anwendung erfordert einen kontinuierlich laufenden Server, der Python-Code ausführen kann. Geeignete Hosting-Optionen sind:

- [Replit](https://replit.com)
- [PythonAnywhere](https://www.pythonanywhere.com)
- [Heroku](https://www.heroku.com)
- VPS-Dienste wie DigitalOcean, AWS oder GCP

Diese Anwendung ist **nicht** für statische Hosting-Dienste wie GitHub Pages oder Netlify geeignet.

## Lizenz

[MIT](https://choosealicense.com/licenses/mit/)