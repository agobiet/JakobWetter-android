# Jakob-Wetter

Ski- und Bergwetter für ausgewählte Orte in Österreich als Webseite: https://agobiet.github.io/JakobWetter-android/

Die Seite holt beim Öffnen alle Daten selbst im Browser:
- **GeoSphere Austria** ([data.hub.geosphere.at](https://data.hub.geosphere.at), CC BY 4.0): Messwerte, INCA, C-LAEF-Prognose, Nowcast, Ensemble, SNOWGRID
- **Lawinenwarndienste** über avalanche.report: Stationsmesswerte (LINEA) und Lawinenlageberichte (EAWS/CAAML)

`index.html` wird aus der Jakob-Wetter-Seite in Claude abgeleitet (Skript `derive_live.py`, siehe Projektdokumentation) und nicht von Hand bearbeitet.
