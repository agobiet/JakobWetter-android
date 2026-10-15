# Quelle der Jakob-Wetter-Webseite

- `jakob.html` – Seitenvorlage (ehemals Claude-Artifact „Jakob-Wetter“, gelöscht am 15.10.2026). Änderungen an der Seite hier machen.
- `live_loader.js` – Datenabruf im Browser (GeoSphere, Lawinenwarndienste, Lageberichte).
- `live_places.json` – Orte mit Seehöhen; `live_stations.json` – TAWES-Stationsliste.
- `derive_live.py` – erzeugt die fertige Seite: `python3 -I src/derive_live.py src/jakob.html /tmp/jakob-live.html`,
  danach die Kopfzeilen für das Homescreen-Symbol nach `<meta name="color-scheme" …>` einfügen und als `index.html` ablegen.
- `build_jakob.py` – Orte und Regeln (Warnregionen, Flachlandorte) der früheren Artifact-Version; dient als Referenz für `live_places.json`.
