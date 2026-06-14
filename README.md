# Holo Rick Secure Chatbot

Normale Chatbot-Webapp mit:

- Login für ein Admin-Konto
- anonyme Nutzung: 1 Nachricht pro öffentlicher IP
- Upload-Button im Composer für Dateien/Bilder
- Archiv für Chats
- sichere `.env` Konfiguration
- Reverse-Proxy-tauglich für `chat.pondsec.com`
- optionaler GitHub-Main-Branch-Updater

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

    client_max_body_size 12M;

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

## Auto Updater

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

## Sicherheitshinweise

- `.env` niemals öffentlich ausliefern oder committen.
- `FLASK_SECRET_KEY`, `IP_HASH_SECRET` und `UPDATE_WEBHOOK_SECRET` stark und lang setzen.
- App nur auf `127.0.0.1:5000` binden, öffentlich nur über Reverse Proxy.
- `TRUST_PROXY=true` nur setzen, wenn wirklich ein Reverse Proxy davor sitzt.
- Uploads sind nur für eingeloggte Nutzer direkt abrufbar.
- Anonyme Nutzer bekommen keine gespeicherte Chat-Historie.
- Das IP-Limit ist bewusst simpel. Für harte Produktion Redis/Fail2ban/Cloudflare/WAF davor setzen.

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

Start mit Docker:

```bash
docker compose up -d --build
```

Reverse Proxy Ziel:

```text
http://127.0.0.1:8362
```
