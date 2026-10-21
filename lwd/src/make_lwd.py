"""Baut die Webseite „LWD Wetter“ (index.html) aus der Jakob-Wetter-Quelle.
Aufruf: python3 -I make_lwd.py <Ordner mit jakob.html, live_loader.js, derive_live.py, live_stations.json> index.html
Unterschiede zu Jakob-Wetter (Wunsch von Andreas, 21.10.2026):
- Name „LWD Wetter“, Text-Banner statt Bild
- eigene feste Orte (lwd_places.json), geordnet von Nord nach Süd, bei gleicher Breite West vor Ost
- Lawinen-Warnregion: fest für Planneralm und Turracher Höhe (wie Jakob-Wetter), sonst automatisch über die
  microRegionID der nächsten LWD-Station (bis 15 km)
- eigene Speicher-Schlüssel im Browser (lwd.live.*, lwdwetter.sel), damit sich die Seiten auf agobiet.github.io nicht stören
Schlägt eine rep(...)-Stelle fehl, hat sich die Jakob-Quelle dort geändert: Stelle anpassen, Sinn beibehalten."""
import json, os, shutil, subprocess, sys, tempfile

src_dir, out = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))


def rep(s, a, b, n=1):
    assert s.count(a) == n, f"Stelle {s.count(a)}x statt {n}x gefunden: " + a[:90]
    return s.replace(a, b)


# ---------- Seite ----------
page = open(os.path.join(src_dir, "jakob.html"), encoding="utf-8").read()
page = rep(page, "<title>Jakob-Wetter</title>", "<title>LWD Wetter</title>")
i = page.index('    <div class="banner">')
j = page.index("    </div>", i) + len("    </div>")
page = page[:i] + '    <div class="banner txt">\n      <h1>LWD Wetter</h1>\n      <p class="sub">Berg- und Lawinenwetter</p>\n    </div>' + page[j:]
page = rep(page, '<h2 class="place" id="placeName">Jakob-Wetter</h2>', '<h2 class="place" id="placeName">LWD Wetter</h2>')
page = rep(page, "</style>", """.banner.txt { aspect-ratio: auto; background: linear-gradient(135deg, var(--sky-top), var(--sky-bot)); padding: 20px 18px 18px; }
.banner.txt h1 { position: static; margin: 0; }
.banner.txt .sub { margin: 4px 0 0; color: var(--banner-ink); font: 600 15px var(--f-display); letter-spacing: .06em; text-transform: uppercase; opacity: .9; }
</style>""")

# ---------- Datenlader ----------
L = open(os.path.join(src_dir, "live_loader.js"), encoding="utf-8").read()
i = L.index("  const STATIONS_FIXED = [")
j = L.index("  ];\n", i) + len("  ];\n")
L = L[:i] + "  const STATIONS_FIXED = [];\n" + L[j:]
L = rep(L, 'const NO_LWD = new Set(["st-peter", "griesplatz"]);', "const NO_LWD = new Set([]);")
L = rep(L, 'const LWD_EXTRA = { tauplitzalm: [{ label: "Großsee", re: /gro(ß|ss|s)\\s*see/i }] };', "const LWD_EXTRA = {};")
L = rep(L, 'const STORE = "jakob.live.v1", STORE_LWD = "jakob.live.lwd.v1", STORE_LOC = "jakob.live.standort";',
        'const STORE = "lwd.live.v1", STORE_LWD = "lwd.live.lwd.v2", STORE_LOC = "lwd.live.standort";')
# feste Warnregionen nur noch für die Orte, die es auch bei Jakob-Wetter gibt
i = L.index("  const AVA = {")
j = L.index("  };\n", i) + len("  };\n")
L = L[:i] + """  const AVA = {
    "turracher-hoehe": [["AT-02-04-01", "Nockberge Mitte", "AT-02"], ["AT-06-18", "Murberge, Gurktaler Alpen", "AT-06"]],
    planneralm: ["AT-06-05", "Wölzer Tauern Nord", "AT-06"],
  };
  // übrige Orte: Warnregion der nächsten LWD-Station mit microRegionID (LINEA-Liste), höchstens AVA_AUTO_KM entfernt
  const AVA_AUTO_KM = 15;
  function avaRegions(p, lwd) {
    const a = AVA[p.id];
    if (a) return Array.isArray(a[0]) ? a : [a];
    if (!lwd) return [];
    let best = null, bd = Infinity;
    for (const s of lwd) {
      if (!s[13]) continue;
      const d = kmBetween(p.lat, p.lon, s[2], s[3]);
      if (d < bd) { bd = d; best = s; }
    }
    if (!best || bd > AVA_AUTO_KM) return [];
    const land = String(best[13]).slice(0, 5);
    return AVA_SITE[land] ? [[String(best[13]), null, land]] : [];
  }
""" + L[j:]
L = rep(L, '"AT-07": ["LWD Tirol", "https://lawinen.report"] };',
        '"AT-07": ["LWD Tirol", "https://lawinen.report"],\n    "AT-04": ["LWD Oberösterreich", "https://www.land-oberoesterreich.gv.at/lawinenwarndienst"], "AT-05": ["LWD Salzburg", "https://lawine.salzburg.at"] };')
L = rep(L, """  function avaFor(pid, bulletins) {
    const a = AVA[pid]; if (!a) return null;
    return (Array.isArray(a[0]) ? a : [a]).map((r) => avaOne(r, bulletins));
  }""", """  function avaFor(p, bulletins, lwd) {
    const list = avaRegions(p, lwd);
    return list.length ? list.map((r) => avaOne(r, bulletins)) : null;
  }""")
L = rep(L, """    const out = { region: rid, regionName: rname, provider: prov, link, checked: new Date().toISOString().slice(0, 19) + "Z", current: false };""",
        """    const out = { region: rid, regionName: rname || "", provider: prov, link, checked: new Date().toISOString().slice(0, 19) + "Z", current: false };""")
L = rep(L, """      if (!(b.regions || []).some((r) => r.regionID === rid)) continue;""",
        """      const reg = (b.regions || []).find((r) => r.regionID === rid);
      if (!reg) continue;
      if (!rname && reg.name) out.regionName = reg.name;""")
L = rep(L, """        v("VW") === null ? null : r2(v("VW") * 3.6, 1), v("VW_MAX") === null ? null : r2(v("VW_MAX") * 3.6, 1), v("DW")]);""",
        """        v("VW") === null ? null : r2(v("VW") * 3.6, 1), v("VW_MAX") === null ? null : r2(v("VW_MAX") * 3.6, 1), v("DW"),
        p.microRegionID || p.microRegionId || p.microregionID || null]);""")
L = rep(L, """      const lands = [...new Set(list.flatMap((p) => { const a = AVA[p.id]; return !a ? [] : Array.isArray(a[0]) ? a.map((x) => x[2]) : [a[2]]; }))];
      const avaP = Promise.all(lands.map(async (l) => [l, await avaLoad(l)])).then((x) => Object.fromEntries(x));
      const [cur, lwd, ava] = await Promise.all([curP, lwdP, avaP]);""",
        """      const [cur, lwd] = await Promise.all([curP, lwdP]);
      const lands = [...new Set(list.flatMap((p) => avaRegions(p, lwd).map((x) => x[2])))];
      const ava = await Promise.all(lands.map(async (l) => [l, await avaLoad(l)])).then((x) => Object.fromEntries(x));""")
L = rep(L, "    const A = ava && avaFor(p.id, ava);", "    const A = ava && avaFor(p, ava, lwd);\n    if (!A) delete doc.avalanche;")

# ---------- ableiten wie die Jakob-Handy-Seite ----------
tmp = tempfile.mkdtemp(dir=here)
try:
    shutil.copy(os.path.join(src_dir, "derive_live.py"), tmp)
    shutil.copy(os.path.join(src_dir, "live_stations.json"), tmp)
    shutil.copy(os.path.join(here, "lwd_places.json"), os.path.join(tmp, "live_places.json"))
    open(os.path.join(tmp, "live_loader.js"), "w", encoding="utf-8").write(L)
    open(os.path.join(tmp, "page.html"), "w", encoding="utf-8").write(page)
    subprocess.run([sys.executable, "-I", os.path.join(tmp, "derive_live.py"), os.path.join(tmp, "page.html"), os.path.join(tmp, "live.html")], check=True)
    html = open(os.path.join(tmp, "live.html"), encoding="utf-8").read()
finally:
    shutil.rmtree(tmp)

html = rep(html, '"punktwetter.sel"', '"lwdwetter.sel"', html.count('"punktwetter.sel"'))
html = rep(html, '"jakob.live.standort"', '"lwd.live.standort"', html.count('"jakob.live.standort"'))
assert "punktwetter.sel" not in html and "jakob.live" not in html, "noch Jakob-Speicher"
html = rep(html, '<meta name="color-scheme" content="light dark">\n', '''<meta name="color-scheme" content="light dark">
<meta name="apple-mobile-web-app-title" content="LWD Wetter">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
''')
open(out, "w", encoding="utf-8").write(html)
print("ok", len(html), "Zeichen")
