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
      <div id="lwdSg"></div>
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
  // Je Station ein Knopf „Stationsgrafik“ (seit 1.11.2026, Wunsch von Andreas): letzte 7 Tage aus der Wochendatei (SMET) des Warndienstes
  let lwdShown = [];
  function renderLwd(P) {
    const L = P.lwd;
    const ex = Array.isArray(P.lwdExtra) ? P.lwdExtra : [];
    lwdShown = [L, ...ex];
    $("#lwdBox").hidden = !L;
    if (L) { $("#lwdSrc").textContent = lwdSrcTxt(L); $("#lwdRo").innerHTML = lwdRows(L); $("#lwdSg").innerHTML = sgUi(0); }
    $("#lwdExtra").innerHTML = ex.map((X, i) => `<div class="lwd"><h3>Station des Lawinenwarndienstes · ${esc(X.label || X.station?.name || "")}</h3>`
      + `<p class="src">${esc(lwdSrcTxt(X))}</p><dl class="readouts">${lwdRows(X)}</dl>${sgUi(i + 1)}</div>`).join("");
  }
  const sgUi = (i) => `<div class="sg"><button type="button" class="sgbtn" data-sg="${i}" aria-expanded="false">Stationsgrafik (7 Tage)</button><div class="sgbox" hidden></div></div>`;
  // Wochendatei je Betreiber: lawinen.at/smet/<Land>/woche/<Kürzel>.smet.gz; Kärnten und Tirol über eigene Server (ungeprüft)
  function sgUrls(st) {
    const id = encodeURIComponent(st.id || ""), op = String(st.operator || "");
    const land = [[/steiermark/i, "stm"], [/salzburg/i, "sbg"], [/ober(ö|oe)sterreich|\\bo(ö|oe)\\b/i, "ooe"], [/nieder(ö|oe)sterreich|\\bn(ö|oe)\\b/i, "noe"],
      [/vorarlberg/i, "vor"], [/bayern|bavaria/i, "bay"], [/k(ä|ae)rnten|carinthia/i, "ktn"], [/tirol|tyrol/i, "tir"]].find(([re]) => re.test(op));
    const out = [];
    if (land && land[1] === "ktn") out.push(`https://smet.hydrographie.info/${id}.smet`);
    if (land && land[1] === "tir") out.push(`https://wiski.tirol.gv.at/lawine/grafiken/smet/woche/${id}.smet.gz`);
    if (land) out.push(`https://lawinen.at/smet/${land[1]}/woche/${id}.smet.gz`);
    else ["stm", "sbg", "ooe", "ktn", "tir", "vor", "noe", "bay"].forEach((l) => out.push(`https://lawinen.at/smet/${l}/woche/${id}.smet.gz`));
    return out;
  }
  async function sgText(url) {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const buf = new Uint8Array(await r.arrayBuffer());
    if (buf[0] === 0x1f && buf[1] === 0x8b) {
      if (typeof DecompressionStream === "undefined") throw new Error("Browser kann gzip nicht entpacken");
      const st = new Blob([buf]).stream().pipeThrough(new DecompressionStream("gzip"));
      return await new Response(st).text();
    }
    return new TextDecoder().decode(buf);
  }
  function sgParse(text) {
    const k = text.indexOf("[DATA]");
    if (k < 0) throw new Error("keine SMET-Datei");
    const meta = {};
    text.slice(0, k).split(/\\r?\\n/).forEach((l) => { const m = l.match(/^\\s*([^=\\s]+)\\s*=\\s*(.*?)\\s*$/); if (m) meta[m[1]] = m[2]; });
    const fields = (meta.fields || "").split(/\\s+/), nod = +(meta.nodata ?? -999), tz = +(meta.tz ?? 0) || 0;
    const ti = fields.indexOf("timestamp");
    if (ti < 0) throw new Error("ohne Zeitspalte");
    const rows = [];
    text.slice(k + 6).split(/\\r?\\n/).forEach((l) => {
      const v = l.trim().split(/\\s+/); if (v.length < fields.length) return;
      const ts = v[ti], t = Date.parse(/Z$|[+-]\\d\\d:?\\d\\d$/.test(ts) ? ts : ts + "Z") - (/Z$|[+-]\\d\\d:?\\d\\d$/.test(ts) ? 0 : tz * 3600e3);
      if (!isNum(t)) return;
      const o = { t };
      fields.forEach((f, j) => { if (j === ti) return; const x = +v[j]; o[f] = isNum(x) && x !== nod && x !== -777 && x !== -999 ? x : null; });
      rows.push(o);
    });
    return { meta, rows: rows.sort((a, b) => a.t - b.t) };
  }
  function sgDraw(box, D, st) {
    const t1 = Date.now(), t0 = t1 - 7 * 864e5;
    const R = D.rows.filter((r) => r.t >= t0 && r.t <= t1);
    const val = (r, f) => (isNum(r[f]) ? r[f] : null);
    const TA = R.map((r) => [r.t, val(r, "TA") === null ? null : r.TA - 273.15]).filter((p) => p[1] !== null && p[1] > -60 && p[1] < 50);
    const HS = R.map((r) => [r.t, val(r, "HS") === null ? null : Math.max(0, r.HS * 100)]).filter((p) => p[1] !== null && p[1] < 1500);
    const VW = R.map((r) => [r.t, val(r, "VW") === null ? null : r.VW * 3.6]).filter((p) => p[1] !== null && p[1] >= 0 && p[1] < 400);
    const VX = R.map((r) => [r.t, val(r, "VW_MAX") === null ? null : r.VW_MAX * 3.6]).filter((p) => p[1] !== null && p[1] >= 0 && p[1] < 400);
    if (!TA.length && !HS.length && !VW.length) { box.innerHTML = `<p class="sgmsg">Die Station hat in den letzten 7 Tagen keine Temperatur-, Schnee- oder Windwerte geliefert.</p>`; return; }
    const W = Math.max(300, Math.round((box.clientWidth || 600) - 8)), m = { l: 36, r: 40 };
    const x = (t) => m.l + ((t - t0) / (t1 - t0)) * (W - m.l - m.r);
    const s = [];
    const panel = (y0, h) => ({ y0, h, y1: y0 + h });
    const P1 = panel(10, 140), P2 = panel(P1.y1 + 26, VW.length || VX.length ? 70 : 0), H = (P2.h ? P2.y1 : P1.y1) + 30;
    s.push(`<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Messwerte der letzten 7 Tage, ${esc(st.name || "")}">`);
    // Tage
    for (let t = Math.ceil(t0 / 3600e3) * 3600e3; t <= t1; t += 3600e3) {
      const o = lp(t); if (o.h !== 0 || o.minute !== "00") continue;
      s.push(`<line class="d" x1="${x(t).toFixed(1)}" x2="${x(t).toFixed(1)}" y1="${P1.y0}" y2="${(P2.h ? P2.y1 : P1.y1) + 4}"/>`);
      if (x(t) < W - m.r - 16) s.push(`<text class="axd" x="${(x(t) + 4).toFixed(1)}" y="${H - 6}">${x(t0 + 864e5) - x(t0) < 58 ? "" : esc(o.weekday.slice(0, 2)) + " "}${+o.day}.</text>`);
    }
    // Schneehöhe als Fläche (rechte Achse)
    if (HS.length) {
      const hMax = Math.max(10, Math.ceil(Math.max(...HS.map((p) => p[1])) / 10) * 10);
      const yh = (v) => P1.y1 - (v / hMax) * P1.h;
      s.push(`<path class="sn sgsn" d="M${x(HS[0][0]).toFixed(1)},${P1.y1} ${HS.map(([t, v]) => `L${x(t).toFixed(1)},${yh(v).toFixed(1)}`).join(" ")} L${x(HS[HS.length - 1][0]).toFixed(1)},${P1.y1} Z"/>`);
      s.push(`<text class="ax" x="${W - m.r + 6}" y="${P1.y0 + 4}">${hMax} cm</text><text class="ax" x="${W - m.r + 6}" y="${P1.y1 + 4}">0</text>`);
    }
    // Temperatur (linke Achse)
    if (TA.length) {
      let lo = Math.floor(Math.min(...TA.map((p) => p[1])) - 1), hi = Math.ceil(Math.max(...TA.map((p) => p[1])) + 1);
      const step = hi - lo > 16 ? 5 : hi - lo > 8 ? 2 : 1; lo = Math.floor(lo / step) * step; hi = Math.ceil(hi / step) * step;
      const y = (v) => P1.y0 + ((hi - v) / (hi - lo)) * P1.h;
      for (let v = lo; v <= hi; v += step) {
        s.push(`<line class="g" x1="${m.l}" x2="${W - m.r}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"${v === 0 ? ' stroke-dasharray="4 3"' : ""}/>`);
        s.push(`<text class="ax" x="${m.l - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${v}°</text>`);
      }
      s.push(`<polyline class="tr" points="${TA.map(([t, v]) => `${x(t).toFixed(1)},${y(v).toFixed(1)}`).join(" ")}"/>`);
    }
    // Wind (unteres Feld)
    if (P2.h) {
      const all = VW.concat(VX).map((p) => p[1]), wMax = Math.max(20, Math.ceil(Math.max(...all) / 10) * 10);
      const y = (v) => P2.y1 - (v / wMax) * P2.h;
      s.push(`<line class="g" x1="${m.l}" x2="${W - m.r}" y1="${P2.y1}" y2="${P2.y1}"/><line class="g" x1="${m.l}" x2="${W - m.r}" y1="${P2.y0}" y2="${P2.y0}"/>`);
      s.push(`<text class="ax" x="${m.l - 6}" y="${P2.y0 + 4}" text-anchor="end">${wMax}</text><text class="ax" x="${m.l - 6}" y="${P2.y1 + 4}" text-anchor="end">0</text><text class="ax" x="${W - m.r + 6}" y="${P2.y0 + 4}">km/h</text>`);
      if (VX.length) s.push(`<polyline class="sgvx" points="${VX.map(([t, v]) => `${x(t).toFixed(1)},${y(v).toFixed(1)}`).join(" ")}"/>`);
      if (VW.length) s.push(`<polyline class="nc sgvw" points="${VW.map(([t, v]) => `${x(t).toFixed(1)},${y(v).toFixed(1)}`).join(" ")}"/>`);
    }
    s.push(`</svg>`);
    const last = R.length ? R[R.length - 1].t : null;
    const lg = [TA.length ? `<span><i class="tr"></i>Temperatur</span>` : "", HS.length ? `<span><i class="sn"></i>Schneehöhe</span>` : "",
      VW.length ? `<span><i class="nc"></i>Wind (Mittel)</span>` : "", VX.length ? `<span><i class="sgvx"></i>Böen</span>` : ""].join("");
    box.innerHTML = `<p class="legend">${lg}</p><div class="chartbox sgchart">${s.join("")}</div>`
      + `<p class="sgmsg">${esc(st.name || "")}${last ? ` · letzter Wert ${esc(dayInline(lp(last)))} ${hm(last)} Uhr` : ""} · ungeprüfte Rohdaten des Warndienstes</p>`;
  }
  async function sgOpen(btn) {
    const box = btn.nextElementSibling, st = lwdShown[+btn.dataset.sg]?.station;
    const open = btn.getAttribute("aria-expanded") !== "true";
    btn.setAttribute("aria-expanded", String(open));
    box.hidden = !open;
    if (!open || !st || box.dataset.done) return;
    box.innerHTML = `<p class="sgmsg">Grafik wird geladen …</p>`;
    let err = "";
    for (const u of sgUrls(st)) {
      try { const D = sgParse(await sgText(u)); sgDraw(box, D, st); box.dataset.done = "1"; return; }
      catch (e) { err = (e && e.message) || "Fehler"; }
    }
    box.innerHTML = `<p class="sgmsg">Die Stationsgrafik ist nicht verfügbar – der Warndienst-Server liefert die Wochendaten für diese Station nicht oder erlaubt keinen Abruf aus dieser Seite (${esc(err)}).</p>`;
  }
  document.addEventListener("click", (e) => { const b = e.target.closest && e.target.closest(".sgbtn"); if (b) sgOpen(b); });

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
.sgbtn { font: 600 14px var(--f-display); letter-spacing: .02em; color: var(--ink); background: var(--sheet); border: 1px solid var(--rule); border-radius: 999px; padding: 5px 12px; cursor: pointer; }
.sgbtn[aria-expanded="true"] { background: var(--ink); color: var(--paper); }
.sgbox { display: grid; gap: 8px; margin-top: 10px; }
.sgmsg { margin: 0; font-size: 13px; color: var(--muted); }
.chartbox .sgsn { opacity: .55; }
.chartbox .sgvx { fill: none; stroke: var(--nowcast); stroke-width: 1; stroke-dasharray: 2 2; opacity: .8; }
.legend i.sgvx { border-color: var(--nowcast); border-top-width: 1px; border-top-style: dashed; }
.legend i.sn { height: 9px; border: 0; background: var(--snow); width: 8px; }
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
