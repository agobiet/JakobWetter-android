  // ---------- Daten live laden (GeoSphere Austria + Lawinenwarndienste, direkt im Browser) ----------
  // Port von build_jakob.py: dieselben Abschnitte je Ort (now, recent, forecast, nowcast, ensemble, snow, snowlimit, lwd, elev).
  const PLACES = __PLACES__;
  const STATIONS_ALL = __STATIONS__.map((r) => { const [id, name, la, lo, h] = r.split(";"); return { id, name, lat: +la, lon: +lo, alt: +h }; });
  const STATIONS_FIXED = [
    { id: "8989104", name: "Graz Lendplatz Feuerwehrturm", lat: 47.07528, lon: 15.4294, alt: 351 },
    { id: "8989103", name: "Graz Lendplatz", lat: 47.07556, lon: 15.4289, alt: 351 },
    { id: "11291", name: "Graz Universität/Heinrichstraße", lat: 47.08, lon: 15.448056, alt: 366 },
    { id: "11238", name: "Graz-Straßgang", lat: 47.04611, lon: 15.41028, alt: 357 },
    { id: "11240", name: "Graz-Thalerhof Flughafen", lat: 46.98056, lon: 15.44, alt: 340 },
  ];
  const GROUPS = { temp: ["TL", "TP", "RF"], wind: ["FF", "FFX", "DD"], rain: ["RR"], sun: ["SO", "GLOW"], pressure: ["PRED"], snow: ["SCHNEE"] };
  const API = "https://dataset.api.hub.geosphere.at/v1";
  // Gesamtliste aller Stationen der Lawinenwarndienste (LINEA-Format, SI-Einheiten); die Kärntner Liste
  // (hydrographie.info) erlaubt keinen Abruf aus fremden Seiten, die Gesamtliste schon (Test vom 14.10.2026).
  const LWD_URL = "https://static.avalanche.report/eaws_weather_stations/linea.geojson";
  const LWD_EVERY_MIN = 60, LWD_MAX_AGE_H = 3;
  // zusätzlich angezeigte LWD-Stationen je Ort (Wunsch von Andreas, 14.10.2026)
  // Flachlandorte ohne LWD-Station (Wunsch von Andreas, 15.10.2026)
  const NO_LWD = new Set(["st-peter", "griesplatz"]);
  const LWD_EXTRA = { tauplitzalm: [{ label: "Großsee", re: /gro(ß|ss|s)\s*see/i }] };
  const STORE = "jakob.live.v1", STORE_LWD = "jakob.live.lwd.v1", STORE_LOC = "jakob.live.standort";
  const REFRESH_MIN = 10;

  const pad2 = (n) => String(n).padStart(2, "0");
  const isoH = (d) => `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(d.getUTCDate())}T${pad2(d.getUTCHours())}:00`;
  const isoD = (d) => `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(d.getUTCDate())}T00:00`;
  const r2 = (x, n) => (isNum(x) ? Math.round(x * 10 ** n) / 10 ** n + 0 : null);
  function kmBetween(a, b, c, d) {
    const R = Math.PI / 180, p1 = a * R, p2 = c * R;
    const h = Math.sin((p2 - p1) / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(((d - b) * R) / 2) ** 2;
    return 2 * 6371 * Math.asin(Math.sqrt(h));
  }
  function store(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function load(k) { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch (e) { return null; } }

  function placesNow() {
    const loc = load(STORE_LOC);
    const list = PLACES.slice();
    if (loc && isNum(loc.lat) && isNum(loc.lon)) list.push({ id: LOC_ID, name: "Aktueller Standort", lat: r2(loc.lat, 4), lon: r2(loc.lon, 4), order: 0 });
    return list;
  }
  // feste Graz-Stationen plus die 3 nächsten (Gipfel über 1800 m nur unter 5 km), davon nur die bis 30 km
  function candidates(p) {
    const near = STATIONS_ALL.filter((s) => s.alt <= 1800 || kmBetween(p.lat, p.lon, s.lat, s.lon) < 5)
      .sort((a, b) => kmBetween(p.lat, p.lon, a.lat, a.lon) - kmBetween(p.lat, p.lon, b.lat, b.lon)).slice(0, 3);
    return STATIONS_FIXED.concat(near.filter((n) => !STATIONS_FIXED.some((s) => s.id === n.id)))
      .filter((s) => kmBetween(p.lat, p.lon, s.lat, s.lon) <= 30);
  }

  // ---------- Abrufe ----------
  let running = 0;
  const waiting = [];
  function slot() { return new Promise((res) => { if (running < 6) { running++; res(); } else waiting.push(res); }); }
  function release() { const n = waiting.shift(); if (n) n(); else running--; }
  async function get(url, ms = 25000) {
    await slot();
    const ctl = new AbortController(), to = setTimeout(() => ctl.abort(), ms);
    try {
      const r = await fetch(url, { cache: "no-store", signal: ctl.signal });
      if (!r.ok) throw new Error("HTTP " + r.status);
      return await r.text();
    } finally { clearTimeout(to); release(); }
  }
  async function attempt(fn) { try { return await fn(); } catch (e) { return null; } }

  function parseCsv(text) {
    const lines = String(text).split(/\r?\n/).map((l) => l.trim()).filter((l) => l && !l.startsWith("```"));
    if (lines.length < 2) return [];
    const head = lines[0].split(",");
    return lines.slice(1).map((l) => { const v = l.split(","); const o = {}; head.forEach((h, i) => (o[h] = v[i] ?? "")); return o; });
  }
  const key = (c) => c.split(" [")[0];
  const num = (s) => (s === undefined || s === null || String(s).trim() === "" ? null : (isFinite(+s) ? +s : null));
  function byTime(rows) {
    const m = new Map();
    rows.filter((r) => r.time).forEach((r) => m.set(r.time, r));
    return [...m.values()].sort((a, b) => Date.parse(a.time) - Date.parse(b.time));
  }
  const steady = (times, min) => times.length > 1 && times.every((t, i) => i === 0 || Date.parse(t) - Date.parse(times[i - 1]) === min * 60000);
  const cols = (r) => Object.fromEntries(Object.keys(r[0]).map((c) => [key(c), c]));

  function buildNow(p, cur, stations) {
    const by = Object.fromEntries(cur.map((r) => [r.station, r]));
    const order = stations.slice().sort((a, b) => kmBetween(p.lat, p.lon, a.lat, a.lon) - kmBetween(p.lat, p.lon, b.lat, b.lon));
    const groups = {};
    for (const [g, keys] of Object.entries(GROUPS)) {
      for (const s of order) {
        const r = by[s.id];
        if (!r || num(r[keys[0]]) === null) continue;
        groups[g] = { station: { id: s.id, name: s.name, alt: s.alt, km: r2(kmBetween(p.lat, p.lon, s.lat, s.lon), 2) }, time: r.time };
        keys.forEach((k) => (groups[g][k] = num(r[k])));
        break;
      }
    }
    return Object.keys(groups).length ? { groups } : null;
  }
  function buildRecent(rows) {
    const r = byTime(rows); if (r.length < 3) return null;
    const c = cols(r), times = r.map((x) => x.time);
    if (!c.T2M || !steady(times, 60)) return null;
    return { source: "inca", dataset: "inca-v1-1h-1km", grid: { lat: r2(num(r[0].lat), 4), lon: r2(num(r[0].lon), 4) },
      time: times, TL: r.map((x) => num(x[c.T2M])), RR: c.RR ? r.map((x) => num(x[c.RR])) : null };
  }
  function buildForecast(rows) {
    const r = byTime(rows); if (r.length < 2) return null;
    const c = cols(r), times = r.map((x) => x.time);
    if (!["2t", "tp", "10fg", "tcc", "sund"].every((k) => c[k]) || !steady(times, 60)) return null;
    const f = (k) => (c[k] ? r.map((x) => num(x[c[k]])) : null);
    const run = new Date(Date.parse(times[times.length - 1]) - 60 * 3600e3);
    return { dataset: "nwp-v2-1h-1km", model: "C-LAEF AlpeAdria deterministisch", run: isoH(run) + "Z",
      grid: { lat: r2(num(r[0].lat), 4), lon: r2(num(r[0].lon), 4) }, time: times,
      t2m: f("2t"), tp: f("tp"), sf: f("sf"), fg: f("10fg"), tcc: f("tcc"), sund: f("sund"), u: f("10u"), v: f("10v") };
  }
  function buildNowcast(rows) {
    const r = byTime(rows); if (r.length < 2) return null;
    const c = cols(r), times = r.map((x) => x.time);
    if (!c.t2m || !c.rr || !steady(times, 15)) return null;
    return { dataset: "nowcast-v1-15min-1km", time: times, t2m: r.map((x) => num(x[c.t2m])), rr: r.map((x) => num(x[c.rr])) };
  }
  function buildEnsemble(rows) {
    const r = byTime(rows); if (r.length < 2) return null;
    const c = cols(r), times = r.map((x) => x.time), ks = ["tp_p10", "tp_p50", "tp_p90"];
    if (!ks.every((k) => c[k]) || !steady(times, 60)) return null;
    const o = { dataset: "ensemble-v2-1h-1km", time: times };
    ks.forEach((k) => (o[k] = r.map((x) => num(x[c[k]]))));
    return o;
  }
  function buildSnow(rows) {
    const r = byTime(rows); if (!r.length) return null;
    const c = cols(r); if (!c.snow_depth) return null;
    const last = r.filter((x) => num(x[c.snow_depth]) !== null).pop(); if (!last) return null;
    return { dataset: "snowgrid_cl-v2-1d-1km", time: last.time, depth_cm: Math.round(num(last[c.snow_depth]) * 100),
      grid: { lat: r2(num(last.lat), 4), lon: r2(num(last.lon), 4) } };
  }
  function buildSnowlimit(rows) {
    const r = byTime(rows); if (r.length < 2) return null;
    const c = cols(r), times = r.map((x) => x.time);
    if (!c.snowlmt || !steady(times, 60)) return null;
    return { dataset: "nwp-v2-1h-1km", time: times, m: r.map((x) => { const v = num(x[c.snowlmt]); return v === null ? null : Math.round(v); }) };
  }

  // ---------- Lawinenlagebericht (EAWS/CAAML über avalanche.report) ----------
  const AVA = {
    "turracher-hoehe": [["AT-02-04-01", "Nockberge Mitte", "AT-02"], ["AT-06-18", "Murberge, Gurktaler Alpen", "AT-06"]],
    schladming: ["AT-06-04-01", "Schladminger Tauern Nord", "AT-06"],
    nassfeld: ["AT-02-15-02", "Karnische Alpen Nassfeld", "AT-02"],
    "st-anton": ["AT-07-07", "Lechtaler Alpen West", "AT-07"],
    planneralm: ["AT-06-05", "Wölzer Tauern Nord", "AT-06"],
    tauplitzalm: ["AT-06-02", "Totes Gebirge Süd", "AT-06"],
  };
  const AVA_SITE = { "AT-02": ["LWD Kärnten", "https://lawinenwarndienst.ktn.gv.at"], "AT-06": ["LWD Steiermark", "https://www.lawine-steiermark.at"], "AT-07": ["LWD Tirol", "https://lawinen.report"] };
  const AVA_LEVEL = { low: 1, moderate: 2, considerable: 3, high: 4, very_high: 5 };
  // Gültigkeitstag: Berichte gelten von 17 Uhr bis 17 Uhr; ab 17 Uhr Ortszeit gilt der Bericht für morgen
  function avaDay() {
    const o = lp(Date.now());
    const base = new Date(Date.UTC(+o.key.slice(0, 4), +o.key.slice(5, 7) - 1, +o.key.slice(8, 10)));
    if (o.h >= 17) base.setUTCDate(base.getUTCDate() + 1);
    return base.toISOString().slice(0, 10);
  }
  async function avaLoad(land) {
    const d = avaDay();
    const text = await attempt(() => get(`https://static.avalanche.report/eaws_bulletins/${d}/${d}-${land}.json`));
    if (!text) return [];
    return (await attempt(async () => JSON.parse(text).bulletins || [])) || [];
  }
  function avaFor(pid, bulletins) {
    const a = AVA[pid]; if (!a) return null;
    return (Array.isArray(a[0]) ? a : [a]).map((r) => avaOne(r, bulletins));
  }
  function avaOne(a, bulletins) {
    const [rid, rname, land] = a, [prov, link] = AVA_SITE[land];
    const out = { region: rid, regionName: rname, provider: prov, link, checked: new Date().toISOString().slice(0, 19) + "Z", current: false };
    const now = Date.now();
    for (const b of bulletins[land] || []) {
      if (!(b.regions || []).some((r) => r.regionID === rid)) continue;
      const vf = Date.parse(b.validTime?.startTime), vt = Date.parse(b.validTime?.endTime);
      if (!(vf <= now && now < vt)) continue;
      const el = (e) => [e?.lowerBound ?? null, e?.upperBound ?? null];
      Object.assign(out, {
        current: true, published: b.publicationTime, validFrom: b.validTime.startTime, validTo: b.validTime.endTime, unscheduled: !!b.unscheduled,
        ratings: (b.dangerRatings || []).map((r) => { const [lo, hi] = el(r.elevation); return { value: r.mainValue, level: AVA_LEVEL[r.mainValue] ?? null, lower: lo, upper: hi, period: r.validTimePeriod || "all_day" }; }),
        problems: (b.avalancheProblems || []).map((p) => { const [lo, hi] = el(p.elevation); return { type: p.problemType, aspects: p.aspects || [], lower: lo, upper: hi, period: p.validTimePeriod || "all_day" }; }),
        tendency: (b.tendency && b.tendency[0] && b.tendency[0].tendencyType) || null,
      });
    }
    return out;
  }

  // ---------- Lawinenwarndienst-Stationen ----------
  function lwdTime(s) {
    const x = String(s || "").trim().replace(" ", "T");
    let t = Date.parse(/Z$|[+-]\d\d:?\d\d$/.test(x) ? x : x + "Z");
    // Kärnten: Zeitstempel auf "Z", aber offenbar Ortszeit (beobachtet 14.10.2026). Liegt eine Zeit unmöglich
    // in der Zukunft, wird sie als Wiener Ortszeit gelesen (MEZ +1 h, MESZ +2 h).
    if (isNum(t) && t - Date.now() > 15 * 60000) t -= viennaOffsetMs(t);
    return isNum(t) ? t : null;
  }
  function viennaOffsetMs(t) {
    try {
      const s = new Intl.DateTimeFormat("en-US", { timeZone: "Europe/Vienna", timeZoneName: "shortOffset" }).formatToParts(new Date(t))
        .find((x) => x.type === "timeZoneName").value;   // z. B. "GMT+2"
      const m = s.match(/GMT([+-]\d+)/);
      return (m ? +m[1] : 1) * 3600e3;
    } catch (e) { return 3600e3; }
  }
  function parseLwd(text) {
    const j = JSON.parse(text), out = [];
    for (const f of j.features || []) {
      const p = f.properties || {}, c = (f.geometry && f.geometry.coordinates) || [];
      if (c.length < 2) continue;
      const op = p.operator && p.operator !== "null" ? String(p.operator) : null;
      if (op && /geosphere|zamg/i.test(op)) continue;
      const t = lwdTime(p.date); if (t === null) continue;
      const v = (k) => (isNum(p[k]) && p[k] !== -777 ? p[k] : null);
      const hsM = v("HS"), hs = hsM === null || hsM < -0.5 ? null : Math.max(0, hsM) * 100;
      out.push([p.shortName || f.id || null, p.name || "", +c[1], +c[0], isNum(c[2]) ? Math.round(c[2]) : null, op, t,
        v("TA") === null ? null : r2(v("TA") - 273.15, 1), r2(hs, 0), hs === null || v("HSD_24") === null ? null : r2(v("HSD_24") * 100, 0),
        v("VW") === null ? null : r2(v("VW") * 3.6, 1), v("VW_MAX") === null ? null : r2(v("VW_MAX") * 3.6, 1), v("DW")]);
    }
    return out;
  }
  function lwdDoc(p, s) {
    return { station: { id: s[0], name: s[1], lat: s[2], lon: s[3], alt: s[4], operator: s[5], km: r2(kmBetween(p.lat, p.lon, s[2], s[3]), 2) },
      time: new Date(s[6]).toISOString().slice(0, 19) + "Z", TA: s[7], HS: s[8], HSD24: s[9], VW: s[10], VWMAX: s[11], DW: s[12] };
  }
  const lwdFresh = (s) => { const age = (Date.now() - s[6]) / 3600e3; return age <= LWD_MAX_AGE_H && age >= -0.25 && (s[7] !== null || s[8] !== null || s[10] !== null); };
  function lwdNearest(p, all, filter) {
    let best = null, bd = Infinity;
    for (const s of all) {
      if (filter && !filter(s)) continue;
      if (!lwdFresh(s)) continue;
      const d = kmBetween(p.lat, p.lon, s[2], s[3]);
      if (d < bd) { bd = d; best = s; }
    }
    return best ? lwdDoc(p, best) : null;
  }
  async function lwdStations(force) {
    const c = load(STORE_LWD);
    if (!force && c && Date.now() - c.at < LWD_EVERY_MIN * 60000 && Array.isArray(c.s)) return c.s;
    const text = await attempt(() => get(LWD_URL, 45000));
    if (!text) return c && Array.isArray(c.s) ? c.s : null;
    const s = await attempt(async () => parseLwd(text));
    if (!s) return c && Array.isArray(c.s) ? c.s : null;
    store(STORE_LWD, { at: Date.now(), s });
    return s;
  }

  // ---------- Ablauf ----------
  let busy = false, lastError = "";
  function show() { render(); if (busy) setStatus("", "Wird aktualisiert …"); }
  function saveAll() { store(STORE, { fetched: new Date().toISOString(), points }); }
  function sortPoints() { points.sort((a, b) => (a.order ?? 99) - (b.order ?? 99) || String(a.name).localeCompare(String(b.name), "de")); }
  function mergePoint(doc) {
    const i = points.findIndex((p) => p.id === doc.id);
    if (i >= 0) points[i] = Object.assign({}, points[i], doc); else points.push(doc);
    sortPoints();
  }
  // Längerfristige Prognose (10 Tage) für den Verlauf: ECMWF IFS über Open-Meteo (CC BY 4.0, ohne Schlüssel nur nicht-kommerziell)
  const OM = "https://api.open-meteo.com/v1/ecmwf";
  async function loadEcmwf(p) {
    const q = `latitude=${p.lat}&longitude=${p.lon}&hourly=temperature_2m,precipitation,snowfall&forecast_days=10&timeformat=unixtime`
      + (isNum(p.elev?.site) ? `&elevation=${Math.round(p.elev.site)}` : "");
    for (const extra of ["&models=ecmwf_ifs", ""]) {
      const txt = await attempt(() => get(`${OM}?${q}${extra}`));
      if (!txt) continue;
      try {
        const j = JSON.parse(txt), H = j.hourly || {};
        const pick = (k) => { const key = Object.keys(H).find((n) => n === k || n.startsWith(k + "_")); return key ? H[key] : []; };
        const tt = (H.time || []).map((v) => v * 1000), t2 = pick("temperature_2m");
        if (tt.length < 24 || !t2.some(isNum)) continue;
        return { model: "ECMWF IFS (Open-Meteo)", time: tt.map((v) => new Date(v).toISOString().slice(0, 19) + "Z"),
          t2m: t2, tp: pick("precipitation"), sf: pick("snowfall"), elev: j.elevation, got: new Date().toISOString().slice(0, 19) + "Z" };
      } catch (e) {}
    }
    return null;
  }
  async function loadPlace(p, cur, lwd, ava) {
    const f1 = new Date(); f1.setUTCMinutes(0, 0, 0);
    const ll = `${p.lat},${p.lon}`, h = (x) => new Date(f1.getTime() + x * 3600e3);
    const d0 = new Date(f1); d0.setUTCHours(0);
    const [fc, nc, inc, ens, sg, sl, ec] = await Promise.all([
      attempt(() => get(`${API}/timeseries/forecast/nwp-v2-1h-1km?parameters=2t,tp,sf,10fg,tcc,sund,10u,10v&lat_lon=${ll}&start=${isoH(f1)}&output_format=csv`)),
      attempt(() => get(`${API}/timeseries/forecast/nowcast-v1-15min-1km?parameters=t2m,rr&lat_lon=${ll}&output_format=csv`)),
      attempt(() => get(`${API}/timeseries/historical/inca-v1-1h-1km?parameters=T2M,RR&lat_lon=${ll}&start=${isoH(h(-6))}&end=${isoH(h(1))}&output_format=csv`)),
      attempt(() => get(`${API}/timeseries/forecast/ensemble-v2-1h-1km?parameters=tp_p10,tp_p50,tp_p90&lat_lon=${ll}&start=${isoH(f1)}&output_format=csv`)),
      attempt(() => get(`${API}/timeseries/historical/snowgrid_cl-v2-1d-1km?parameters=snow_depth&lat_lon=${ll}&start=${isoD(new Date(d0.getTime() - 5 * 864e5))}&end=${isoD(d0)}&output_format=csv`)),
      attempt(() => get(`${API}/timeseries/forecast/nwp-v2-1h-1km?parameters=snowlmt&lat_lon=${ll}&start=${isoH(f1)}&output_format=csv`)),
      loadEcmwf(p),
    ]);
    const old = points.find((x) => x.id === p.id);
    const moved = old && p.id === LOC_ID && (Math.abs(old.lat - p.lat) > 1e-4 || Math.abs(old.lon - p.lon) > 1e-4);
    const doc = moved ? {} : Object.assign({}, old || {});
    Object.assign(doc, { id: p.id, name: p.name, lat: p.lat, lon: p.lon, order: p.order });
    if (p.elev) doc.elev = p.elev; else delete doc.elev;
    let ok = 0;
    const put = (k, v, count) => { if (v) { doc[k] = v; if (count) ok++; } };
    if (cur) put("now", buildNow(p, cur, candidates(p)), true);
    put("forecast", fc && buildForecast(parseCsv(fc)), true);
    put("nowcast", nc && buildNowcast(parseCsv(nc)), true);
    put("recent", inc && buildRecent(parseCsv(inc)), true);
    put("ensemble", ens && buildEnsemble(parseCsv(ens)), true);
    put("snow", sg && buildSnow(parseCsv(sg)), false);
    put("snowlimit", sl && buildSnowlimit(parseCsv(sl)), false);
    put("ecmwf", ec, false);
    if (NO_LWD.has(p.id)) { delete doc.lwd; delete doc.lwdExtra; }
    else if (lwd) {
      const l = lwdNearest(p, lwd);
      if (l) doc.lwd = l; else delete doc.lwd;
      const ex = (LWD_EXTRA[p.id] || []).map((e) => {
        const d = lwdNearest(p, lwd, (s) => e.re.test(s[1]));
        return d && d.station.name !== (doc.lwd && doc.lwd.station.name) ? Object.assign(d, { label: e.label }) : null;
      }).filter(Boolean);
      if (ex.length) doc.lwdExtra = ex; else delete doc.lwdExtra;
    }
    const A = ava && avaFor(p.id, ava);
    if (A) doc.avalanche = A;
    if (ok) doc.updated = new Date().toISOString().slice(0, 19) + "Z";
    mergePoint(doc);
    return ok;
  }
  async function refreshAll(force) {
    if (busy) return;
    busy = true; lastError = "";
    $("#refreshBtn").disabled = true;
    setStatus("", "Wird aktualisiert …");
    try {
      const list = placesNow();
      // Ort "Aktueller Standort" entfernen, wenn er nicht mehr gespeichert ist
      points = points.filter((p) => p.id !== LOC_ID || list.some((x) => x.id === LOC_ID));
      const ids = [...new Set(list.flatMap((p) => candidates(p).map((s) => s.id)))].join(",");
      const curP = attempt(() => get(`${API}/station/current/tawes-v1-10min?parameters=TL,TP,RF,DD,FF,FFX,RR,SO,GLOW,PRED,SCHNEE&station_ids=${ids}&output_format=csv`)).then((t) => (t ? parseCsv(t) : null));
      const lwdP = lwdStations(force);
      const lands = [...new Set(list.flatMap((p) => { const a = AVA[p.id]; return !a ? [] : Array.isArray(a[0]) ? a.map((x) => x[2]) : [a[2]]; }))];
      const avaP = Promise.all(lands.map(async (l) => [l, await avaLoad(l)])).then((x) => Object.fromEntries(x));
      const [cur, lwd, ava] = await Promise.all([curP, lwdP, avaP]);
      if (!cur) lastError = "Messwerte nicht erreichbar";
      // gewählter Ort zuerst, dann die übrigen
      const sel = (current() && current().id) || list[0].id;
      const ordered = list.slice().sort((a, b) => (a.id === sel ? -1 : b.id === sel ? 1 : 0));
      let total = 0;
      const first = await loadPlace(ordered[0], cur, lwd, ava);
      total += first;
      show(); saveAll();
      await Promise.all(ordered.slice(1).map(async (p) => { total += await loadPlace(p, cur, lwd, ava); show(); }));
      saveAll();
      if (!total) lastError = "Keine Daten von GeoSphere erhalten (Internet?)";
    } catch (e) {
      lastError = (e && e.message) || "Fehler";
    } finally {
      busy = false;
      $("#refreshBtn").disabled = false;
      render();
      if (lastError) setStatus("bad", "Aktualisieren unvollständig: " + lastError + (current() ? " · zeige letzten Stand" : ""));
    }
  }
  function maybeRefresh() {
    const c = load(STORE);
    const age = c && c.fetched ? (Date.now() - Date.parse(c.fetched)) / 60000 : Infinity;
    if (age >= REFRESH_MIN || placesNow().some((p) => !points.some((x) => x.id === p.id))) refreshAll(false);
  }

  // Start: letzten Stand sofort zeigen, dann bei Bedarf neu laden
  db = {};   // nur als Kennzeichen: Standort-Knopf zeigen
  { const c = load(STORE); points = c && Array.isArray(c.points) ? c.points.filter((p) => p.id !== LOC_ID || load(STORE_LOC)) : []; sortPoints(); }
  render();
  $("#refreshBtn").addEventListener("click", () => refreshAll(true));
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") maybeRefresh(); });
  maybeRefresh();
