# Holo Rick Secure Chatbot

Normale Chatbot-Webapp mit:

- Login für ein Admin-Konto
- persistente Login-Sessions mit „Angemeldet bleiben“
- öffentliche Registrierung mit E-Mail, Passwort, Anzeigename und expliziter Datenschutz-/Nutzungszustimmung
- optionale TOTP-2FA per Authenticator-App
- serverseitige Chat-/Upload-Trennung pro Konto
- unbegrenzte Nutzung für angemeldete Konten, Gastlimits nur für nicht angemeldete Besucher
- anonyme Nutzung: standardmäßig 3 Nachrichten pro öffentlicher IP
- Upload-Button im Composer für Dateien/Bilder
- automatische Bildwunsch-Erkennung mit separatem Bildgenerierungsmodell
- Groq-Key-Pool über `GROQ_API_KEYS`, damit Text/Vision-Anfragen über mehrere Keys verteilt werden
- Markdown-Rendering mit Tabellen, Codeblöcken und Sanitizing
- hochwertige flache Chat-Oberfläche mit Projektkontext, Smart Actions und dezent steuerbaren Antwortmodi
- Archiv für Chats
- sichere `.env` Konfiguration
- Reverse-Proxy-tauglich für `chat.pondsec.com`
- optionaler GitHub-Main-Branch-Updater mit Healthcheck-Rollback

## Start lokal

```bash
cd holo_rick_secure
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python app.py
```

Dann öffnen:

```text
http://127.0.0.1:5000
```

## Passwort sicher setzen

Nicht das Beispielpasswort in Git committen. Ja, wirklich. Menschen erfinden Lecks und nennen es dann Deployment.

Hash erzeugen:

```bash
python scripts/hash_password.py
```

Dann in `.env` eintragen:

```env
ADMIN_EMAIL=joshua@pondsec.com
ADMIN_PASSWORD_HASH=dein_hash
```

`ADMIN_PASSWORD` danach entfernen.

## Reverse Proxy mit Nginx

Beispiel:

```nginx
server {
    server_name chat.pondsec.com;

    client_max_body_size 128M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
}
```

TLS dann z.B. mit Certbot:

```bash
sudo certbot --nginx -d chat.pondsec.com
```

## Systemd Service

```ini
[Unit]
Description=Holo Rick Chatbot
After=network.target

[Service]
WorkingDirectory=/opt/HoloRick
ExecStart=/opt/HoloRick/.venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 app:app
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

## Auto Updater mit Rollback

Für Produktion sollte der Updater auf dem Host laufen, nicht im Container. Nur der Host kann Docker Compose sauber neu bauen, starten und bei einem kaputten Update zurückrollen.

Das Script `scripts/auto_update.sh` macht bewusst nur Fast-Forward-Updates vom konfigurierten Branch. Ablauf:

1. Lock setzen, damit nie zwei Updates parallel laufen.
2. Prüfen, ob der Arbeitsbaum sauber ist.
3. Aktuellen Commit und Datenbank-Backup merken.
4. `git fetch` und `git merge --ff-only origin/main`.
5. Docker-Image bauen und Service starten.
6. Healthcheck gegen `AUTO_UPDATE_HEALTH_URL`.
7. Bei Fehler: `git reset --hard` auf den letzten stabil laufenden Commit, Datenbank-Backup zurückspielen, neu bauen/starten, Healthcheck wiederholen.

Systemd installieren:

```bash
sudo cp deploy/holo-rick-auto-update.service /etc/systemd/system/
sudo cp deploy/holo-rick-auto-update.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now holo-rick-auto-update.timer
```

Nützliche `.env` Werte:

```env
AUTO_UPDATE_BRANCH=main
AUTO_UPDATE_REMOTE=origin
AUTO_UPDATE_SERVICE=holo-rick
AUTO_UPDATE_HEALTH_URL=http://127.0.0.1:8362/
```

Status prüfen:

```bash
systemctl list-timers holo-rick-auto-update.timer
journalctl -u holo-rick-auto-update.service -n 120 --no-pager
tail -n 120 logs/auto-update.log
```

Der Server muss als Git-Repository deployed sein und lokale Änderungen sollten nicht direkt auf dem Server editiert werden. Änderungen kommen über `main`, sonst bricht der Updater absichtlich ab.

## In-App Update Webhook

Webhook-Update:

```bash
curl -X POST https://chat.pondsec.com/api/update \
  -H "Content-Type: application/json" \
  -H "X-Update-Secret: dein_secret"
```

`.env`:

```env
AUTO_UPDATE_REPO=https://github.com/PondSec/HoloRick.git
AUTO_UPDATE_BRANCH=main
UPDATE_WEBHOOK_SECRET=langes_geheimes_secret
```

Optionaler Polling-Updater:

```env
AUTO_UPDATE_ENABLED=true
AUTO_UPDATE_INTERVAL_SECONDS=300
```

Wichtig: Der Updater funktioniert nur, wenn die App selbst als Git-Repository deployed wurde. Also nicht einfach ZIP irgendwo hinwerfen und erwarten, dass Git plötzlich aus kosmischer Scham entsteht.

Für Docker-Produktion ist der systemd-Updater oben sicherer, weil der Webhook im Container den Host-Compose-Stack nicht zuverlässig neu bauen kann.

## Sicherheitshinweise

- `.env` niemals öffentlich ausliefern oder committen.
- `FLASK_SECRET_KEY` oder `SECRET_KEY`, `IP_HASH_SECRET` und `UPDATE_WEBHOOK_SECRET` stark und lang setzen.
- App nur auf `127.0.0.1:8362` binden, öffentlich nur über Reverse Proxy.
- `TRUST_PROXY=true` nur setzen, wenn wirklich ein Reverse Proxy davor sitzt.
- `SESSION_COOKIE_SECURE=true` setzen, sobald die App ausschließlich über HTTPS erreichbar ist.
- Uploads sind nur für den eingeloggten Besitzer direkt abrufbar.
- Anonyme Nutzer bekommen keine gespeicherte Chat-Historie.
- Das IP-Limit ist bewusst simpel. Für harte Produktion Redis/Fail2ban/Cloudflare/WAF davor setzen.
- 2FA wird unter Einstellungen → Sicherheit aktiviert. Die App nutzt TOTP, kompatibel mit üblichen Authenticator-Apps.
- Bildanalyse nutzt das intern konfigurierte Vision-Modell. Sehr große Bilder werden nicht als Base64 an den Modellanbieter gesendet.

## v4 Hinweise

### 127.0.0.1 trotz öffentlicher Domain?

Wenn Nginx/Caddy/Apache auf demselben Server läuft wie Flask, ist `127.0.0.1:5000` richtig und sicherer. Der Reverse Proxy nimmt öffentliche HTTPS-Anfragen für `chat.pondsec.com` an und leitet intern an `http://127.0.0.1:5000` weiter. Flask selbst ist dadurch nicht direkt im Internet sichtbar.

Nur wenn der Reverse Proxy auf einem anderen Host oder in einem anderen Docker-Netz sitzt, muss Flask für diesen Proxy erreichbar sein, z. B. mit `APP_HOST=0.0.0.0`. Dann aber Firewall setzen und nur Proxy-IP erlauben, weil direkt offenes Flask im Internet so elegant ist wie ein Tresor aus Pappe.

### Identität

Holo Rick bekommt serverseitig mit, ob der Nutzer angemeldet ist. Angemeldet bedeutet Joshua/Admin. Gäste werden als öffentliche Gäste behandelt. Außerdem ist im Systemprompt fest hinterlegt, dass Joshua Dean Pond / PondSec der Entwickler und Betreiber der Holo-Rick-App ist.

## v5 Hinweise

- Standard-Port ist jetzt `8362`.
- Docker Compose bindet sicher auf `127.0.0.1:8362`, gedacht für Nginx/Caddy Reverse Proxy.
- Gäste dürfen standardmäßig 3 Nachrichten pro öffentlicher IP senden.
- Gäste dürfen standardmäßig nur 1 Nachricht mit Anhang senden.
- Chat-Zeilen in der Sidebar haben wieder Archiv- und Löschen-Buttons.
- Einstellungen sind jetzt in Tabs aufgeteilt: Modell, Identität, Limits, Oberfläche, Prompt.

## v6 Hinweise

- Chats, Messages und Uploads haben `user_id`; API-Endpunkte filtern serverseitig nach dem eingeloggten Konto.
- Login-Sessions bleiben auf Wunsch browserübergreifend erhalten, solange der Session-Key stabil bleibt.
- Mutierende API-Requests verlangen einen CSRF-Token.
- Security-Header inklusive CSP, Frame-Schutz und `nosniff` werden von Flask gesetzt.
- Markdown wird serverseitig mit Tabellen-Support gerendert und anschließend bereinigt.
- PDF- und Textanhänge werden als Textkontext extrahiert; Bildanhänge werden an das intern konfigurierte Vision-Modell übergeben, sofern sie klein genug sind.
- Der Composer unterstützt Antwortmodi (`Holo`, `Präzise`, `Deep`, `Code`) und Formate (`Auto`, `Schritte`, `Tabelle`), die serverseitig in den Modellprompt einfließen.

## v7 Hinweise

- Chats haben einen privaten Projektkontext. Er wird pro Konto und Chat gespeichert und in jede weitere Modellanfrage dieses Chats eingebaut.
- Der Projektkontext kann manuell gepflegt oder per Smart Brief aus dem bisherigen Chat verdichtet werden.
- Assistant-Antworten haben dezente Smart Actions: Kurzfassung, To-dos und Risiko-Check.
- Die Moduswahl ist kein dauerhaft sichtbares Dock mehr, sondern ein kompaktes Popover im Modell-Pill.
- Uploads sind standardmäßig auf 25 MB pro Datei und 5 Dateien pro Nachricht ausgelegt; der Reverse Proxy sollte entsprechend größer als der gesamte Multipart-Request konfiguriert sein.

## v8 Hinweise

- Neue Nutzer können sich selbst registrieren. Die App speichert Consent-Zeitpunkt, Datenschutzversion, Nutzungsbedingungen-Version und einen gehashten Registrierungs-IP-Wert.
- Registrierte Nutzer sind nicht vom öffentlichen Gastlimit betroffen; öffentliche Limits werden nur für nicht angemeldete Besucher gezählt.
- In der Oberfläche werden nur öffentliche Modellnamen wie `Holo Rick 120b` angezeigt.
- Anbieter-Rate-Limits werden als ruhiges Banner „Holo Rick braucht eine Pause“ mit Wartezeit angezeigt, ohne technische Provider-Fehler an Nutzer durchzureichen.

## v9 Hinweise

- `GROQ_API_KEYS` kann mehrere Groq-Keys kommagetrennt aufnehmen. Die App bevorzugt den aktuell am wenigsten genutzten Key und überspringt temporär rate-limitierte Keys.
- Bildwünsche wie „erstelle ein Bild ...“ werden automatisch erkannt und nicht an das normale Chatmodell geschickt.
- Bildgenerierung nutzt einen OpenAI-kompatiblen Images-Endpunkt über `IMAGE_GENERATION_API_KEY`, optional `IMAGE_GENERATION_ENDPOINT`, `IMAGE_GENERATION_MODEL` und `IMAGE_GENERATION_SIZE`.
- Generierte Bilder werden im Chat als ruhige Bildkarte angezeigt. Der Download-Button erscheint dezent beim Hover; auf Mobile bleibt er sichtbar.
- Groq unterstützt laut offizieller Doku Bildverständnis/OCR über Vision-Modelle, aber keine Text-zu-Bild-Generierung über die gelisteten Groq-Modelle. Dafür ist ein separater Bildmodell-Provider nötig.

## v10 Hinweise

- Angemeldete Nutzer können ihr Konto unter Einstellungen → Sicherheit endgültig löschen. Dafür sind Passwort, bei aktiver 2FA ein aktueller Code und die Bestätigung `KONTO LÖSCHEN` nötig.
- Beim Löschen werden Nutzerkonto, Chats, Nachrichten, Upload-Datenbankeinträge und die zugehörigen Upload-Dateien entfernt.
- Der neue Host-Updater kann `main` automatisch holen und rollt bei Build-, Start- oder Healthcheck-Fehlern auf den vorher stabil laufenden Commit zurück.

Start mit Docker:

```bash
docker compose up -d --build
```

Reverse Proxy Ziel:

```text
http://127.0.0.1:8362
```
