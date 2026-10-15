"""Leitet die selbstaktualisierende Handy-Seite (jakob-live.html) aus der Artifact-Seite jakob.html ab.
Aufruf: python3 -I derive_live.py jakob.html jakob-live.html
Benötigt live_loader.js, live_places.json (Orte mit Seehöhen aus build_jakob.py) und live_stations.json
(TAWES-Stationsliste, Feld rows von meta/stations) im selben Ordner.
Schlägt eine rep(...)-Stelle fehl, hat sich die Artifact-Seite dort geändert: Stelle anpassen, Sinn beibehalten."""
import json, os, sys

here = os.path.dirname(os.path.abspath(__file__))
src = open(sys.argv[1], encoding="utf-8").read()
if "<body>" in src:
    src = src[src.index("<body>") + len("<body>"):]
src = src.replace("</body></html>", "").strip() + "\n"


def rep(a, b, n=1):
    global src
    assert src.count(a) == n, f"Stelle {src.count(a)}x statt {n}x gefunden: " + a[:80]
    src = src.replace(a, b)


# Statuszeile mit Knopf "Aktualisieren"
rep('    <p class="status" id="status" role="status"><span class="dot"></span><span id="statusText">Wetterdaten werden geladen …</span></p>',
    '    <div class="statusrow"><p class="status" id="status" role="status"><span class="dot"></span><span id="statusText">Wetterdaten werden geladen …</span></p>'
    '<button type="button" class="refresh" id="refreshBtn" aria-label="Jetzt aktualisieren">↻ Aktualisieren</button></div>')

# Hinweise zur manuellen Aktualisierung im Artifact
rep('notice("Noch keine Wetterdaten", "Bitte die Wetter-App manuell aktualisieren. Danach erscheinen hier die Prognose und die aktuelle Messung für den gewählten Ort.");',
    'notice("Noch keine Wetterdaten", "Die Seite holt die Daten gerade bei GeoSphere Austria. Falls nichts erscheint: Internetverbindung prüfen und auf „Aktualisieren“ tippen.");')
rep('notice("Noch keine Wetterdaten für diesen Ort", "Die Daten werden bei der nächsten manuellen Aktualisierung geholt.");',
    'notice("Noch keine Wetterdaten für diesen Ort", "Die Daten werden gerade geholt. Falls nichts erscheint: auf „Aktualisieren“ tippen.");')
rep('"Neuer Standort gespeichert – Wetterdaten folgen mit der nächsten manuellen Aktualisierung."', '"Neuer Standort gespeichert – Wetterdaten werden geholt …"')
rep('"Die Werte unten gelten noch für den vorherigen Standort. Neue Werte kommen mit der nächsten manuellen Aktualisierung."',
    '"Die Werte unten gelten noch für den vorherigen Standort. Neue Werte werden geholt …"')

# Quelle der LWD-Werte in der Fußzeile
rep('über lawinen.at bzw. LWD Tirol (CC BY 4.0)', 'über die Gesamtliste von avalanche.report (LINEA)')

# Zusätzliche LWD-Stationen (Feld lwdExtra, z. B. Großsee bei der Tauplitzalm)
rep('''      <dl class="readouts" id="lwdRo"></dl>
    </div>''', '''      <dl class="readouts" id="lwdRo"></dl>
    </div>
    <div id="lwdExtra"></div>''')
i = src.index("  function renderLwd(P) {")
j = src.index("  // ---------- Rest des Tages (Kurzüberblick) ----------")
src = src[:i] + """  function lwdSrcTxt(L) {
    const s = L.station || {}, t = Date.parse(L.time);
    const NH0 = new Intl.NumberFormat("de-AT", { useGrouping: false });
    return [s.name, isNum(s.km) ? N1.format(s.km) + " km" : "", isNum(s.alt) ? NH0.format(s.alt) + "\\u00a0m" : "", s.operator,
      isNum(t) ? `Messung ${hm(t)} Uhr` + ((Date.now() - t) / 60000 > 60 ? " · " + ago(t) : "") : ""].filter(Boolean).join(" · ");
  }
  function lwdRows(L) {
    const ro = [];
    const item = (label, val, unit, det) => ro.push(`<div class="ro"><dt>${label}</dt><dd><span class="val">${val}<small>${unit}</small></span><span class="det">${det}</span></dd></div>`);
    if (isNum(L.TA)) item("Temperatur", f1(L.TA), "°C", "");
    if (isNum(L.HS)) item("Schneehöhe", f0(L.HS), "cm", isNum(L.HSD24) ? `${L.HSD24 > 0 ? "+" : ""}${f0(L.HSD24)} cm in 24 h` : "");
    if (isNum(L.VW)) {
      const calm = L.VW < 2;
      item("Wind", calm ? "0" : f0(L.VW), "km/h", [calm ? "windstill" : isNum(L.DW) ? `aus ${dirTxt(L.DW)}` : "", isNum(L.VWMAX) ? `Böen ${f0(L.VWMAX)} km/h` : ""].filter(Boolean).join(" · "));
    }
    return ro.join("");
  }
  // Nächste Station des Lawinenwarndienstes (Feld lwd) und zusätzlich gewünschte Stationen (Feld lwdExtra)
  function renderLwd(P) {
    const L = P.lwd;
    $("#lwdBox").hidden = !L;
    if (L) { $("#lwdSrc").textContent = lwdSrcTxt(L); $("#lwdRo").innerHTML = lwdRows(L); }
    const ex = Array.isArray(P.lwdExtra) ? P.lwdExtra : [];
    $("#lwdExtra").innerHTML = ex.map((X) => `<div class="lwd"><h3>Station des Lawinenwarndienstes · ${esc(X.label || X.station?.name || "")}</h3>`
      + `<p class="src">${esc(lwdSrcTxt(X))}</p><dl class="readouts">${lwdRows(X)}</dl></div>`).join("");
  }

""" + src[j:]

# Standort: im Browser bestimmen bzw. eingeben, in der Seite merken
i = src.index("  async function saveLoc(lat, lon, acc) {")
j = src.index("  function locate() {")
src = src[:i] + """  function saveLoc(lat, lon) {
    if (!(lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180)) { locMsg("bad", "Das sind keine gültigen Koordinaten."); return; }
    const outside = lat < 45.5 || lat > 49.5 || lon < 8.5 || lon > 17.8;
    try { localStorage.setItem("jakob.live.standort", JSON.stringify({ lat, lon, at: new Date().toISOString() })); } catch (e) {}
    selected = LOC_ID;
    try { localStorage.setItem("punktwetter.sel", selected); } catch (e) {}
    locMsg(outside ? "warn" : "", `Gespeichert: ${N4.format(lat)}° N · ${N4.format(lon)}° O – Wetterdaten werden geholt …`
      + (outside ? " Achtung: Der Ort liegt außerhalb von Österreich – die GeoSphere-Daten reichen dort eventuell nicht hin." : ""));
    $("#locForm").hidden = true;
    locOpen = false;
    window.jakobRefresh && window.jakobRefresh();
  }
""" + src[j:]
rep('      (pos) => { $("#locBtn").disabled = false; locBusy = false; saveLoc(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy); },',
    '      (pos) => { $("#locBtn").disabled = false; locBusy = false; saveLoc(pos.coords.latitude, pos.coords.longitude); },')
rep('    saveLoc(c.lat, c.lon, null);', '    saveLoc(c.lat, c.lon);')

# Datenquelle: statt Artifact-Datenspeicher der Live-Abruf
i = src.index("  // ---------- Daten aus dem Speicher ----------")
j = src.index("})();\n</script>")
loader = open(os.path.join(here, "live_loader.js"), encoding="utf-8").read()
loader = loader.replace("__PLACES__", json.dumps(json.load(open(os.path.join(here, "live_places.json"), encoding="utf-8")), ensure_ascii=False))
loader = loader.replace("__STATIONS__", json.dumps(json.load(open(os.path.join(here, "live_stations.json"), encoding="utf-8")), ensure_ascii=False))
loader += "  window.jakobRefresh = () => refreshAll(false);\n"
src = src[:i] + loader + src[j:]

css = """
.statusrow { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.refresh { font: 600 14px var(--f-display); letter-spacing: .02em; color: var(--ink); background: var(--sheet); border: 1px solid var(--rule); border-radius: 999px; padding: 5px 12px; cursor: pointer; }
.refresh:disabled { opacity: .5; }
#lwdExtra:empty { display: none; }
#lwdExtra { display: grid; gap: 16px; }
</style>"""
k = src.index("</style>")
src = src[:k] + css + src[k + len("</style>"):]

page = ('<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
        '<meta name="color-scheme" content="light dark">\n'
        '<style>html,body{margin:0;padding:0}[hidden]{display:none!important}img{max-width:100%}</style>\n'
        '</head>\n<body>\n' + src + '\n</body>\n</html>\n')
assert "claude.use" not in page and "manuell" not in page, "Seite enthält noch Artifact-Teile"
open(sys.argv[2], "w", encoding="utf-8").write(page)
print("ok", len(page), "Zeichen")
