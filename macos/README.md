# Holo Rick macOS App

Diese native macOS-App lädt direkt `https://chat.pondsec.com` in einem `WKWebView`.

- App-Name: `Holo Rick`
- Bundle ID: `com.pondsec.holorick`
- Mindestversion: macOS 13
- Netzwerk: HTTPS-only über App Transport Security
- Interne Navigation: nur `chat.pondsec.com`
- Externe Links: öffnen im Standardbrowser
- Cookies/Sessions: persistent über den normalen `WKWebView`-Datenspeicher

Build:

```bash
./macos/build_holo_rick_app.sh
```

Die gebaute App liegt danach unter:

```text
dist/Holo Rick.app
```
