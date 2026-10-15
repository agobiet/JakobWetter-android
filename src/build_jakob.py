"""Jakob-Wetter: baut die Datenpakete (ein Dokument je Ort) aus GeoSphere-CSV-Dateien
im aktuellen Ordner:
  cur.csv               aktuelle TAWES-Werte aller Kandidaten-Stationen
  inca_<id>*.csv        INCA-Analyse inca-v1-1h-1km je Ort (letzte ~6 h, stuendlich)
  fc_<id>*.csv          Prognose nwp-v2-1h-1km je Ort (darf auf mehrere Dateien verteilt sein)
  nc_<id>*.csv          Nowcast nowcast-v1-15min-1km je Ort
  snow_<id>.csv         SNOWGRID snowgrid_cl-v2-1d-1km je Ort (snow_depth in m, taeglich, letzter Wert meist von gestern)
  snl_<id>.csv          Schneefallgrenze nwp-v2-1h-1km Parameter snowlmt je Ort (m)
  ens_<id>*.csv         Ensemble ensemble-v2-1h-1km je Ort (tp_p10, tp_p50, tp_p90 -> Regenwahrscheinlichkeit)
  points/standort.json  (optional) Dokument "standort" aus dem Speicher (ArtifactData get mit out_dir=.);
                        enthaelt req = {lat, lon, acc, at}, den Standort, den die Seite zuletzt gespeichert hat
  meta/stations.json    Liste aller TAWES-Stationen (ArtifactData get meta/stations mit out_dir=.)
Aufruf: "python3 build_points.py ids"  -> Stations-IDs fuer cur.csv und Koordinaten fuer den Standort
        "python3 build_points.py"      -> point_<id>.json je Ort
Unvollstaendige Abschnitte bleiben weg; die Ergebnisse point_<id>.json werden per
ArtifactData "update" eingespielt, alte Abschnitte bleiben dann erhalten."""
import csv, glob, io, json, math, os, sys, datetime as dt

POINTS = [
    {"id": "st-peter", "name": "St. Peter", "lat": 47.0602, "lon": 15.4637, "order": 1, "elev": {"source": "EU-DEM 25 m (OpenTopoData), abgefragt 11.10.2026", "site": 364, "claef": {"lat": 47.061, "lon": 15.4672, "point": 370, "cell": 370}, "inca": {"lat": 47.0566, "lon": 15.4658, "point": 366, "cell": 363}, "snowgrid": {"lat": 47.0617, "lon": 15.4601, "point": 365, "cell": 365}}},  # derselbe Punkt wie Schulzentrum St. Peter
    {"id": "griesplatz", "name": "Griesplatz", "lat": 47.0655, "lon": 15.4314, "order": 2, "elev": {"source": "EU-DEM 25 m (OpenTopoData), abgefragt 11.10.2026", "site": 354, "claef": {"lat": 47.061, "lon": 15.4267, "point": 353, "cell": 354}, "inca": {"lat": 47.0664, "lon": 15.4267, "point": 361, "cell": 357}, "snowgrid": {"lat": 47.0622, "lon": 15.4338, "point": 346, "cell": 352}}},
    {"id": "turracher-hoehe", "name": "Turracher Höhe", "lat": 46.9144, "lon": 13.8750, "order": 3, "elev": {"source": "EU-DEM 25 m (OpenTopoData), abgefragt 11.10.2026", "site": 1791, "claef": {"lat": 46.917, "lon": 13.8742, "point": 1777, "cell": 1807}, "inca": {"lat": 46.9134, "lon": 13.871, "point": 1800, "cell": 1804}, "snowgrid": {"lat": 46.9183, "lon": 13.8783, "point": 1777, "cell": 1807}}},
    {"id": "schladming", "name": "Schladming", "lat": 47.3917, "lon": 13.6889, "order": 4, "elev": {"source": "EU-DEM 25 m (OpenTopoData), abgefragt 11.10.2026", "site": 746, "claef": {"lat": 47.394, "lon": 13.6852, "point": 734, "cell": 743}, "inca": {"lat": 47.391, "lon": 13.6903, "point": 750, "cell": 797}, "snowgrid": {"lat": 47.396, "lon": 13.6845, "point": 744, "cell": 757}}},
    {"id": "nassfeld", "name": "Nassfeld", "lat": 46.5637, "lon": 13.2742, "order": 5, "elev": {"source": "EU-DEM 25 m (OpenTopoData), abgefragt 14.10.2026", "site": 1513, "claef": {"lat": 46.566, "lon": 13.2802, "point": 1460, "cell": 1495}, "inca": {"lat": 46.5637, "lon": 13.2805, "point": 1493, "cell": 1537}, "snowgrid": {"lat": 46.5597, "lon": 13.2746, "point": 1541, "cell": 1547}}},  # Liftzentrum Passhöhe (Sonnenalpe Nassfeld)
    {"id": "st-anton", "name": "St. Anton am Arlberg", "lat": 47.1281, "lon": 10.2631, "order": 6, "elev": {"source": "EU-DEM 25 m (OpenTopoData), abgefragt 14.10.2026", "site": 1313, "claef": {"lat": 47.124, "lon": 10.2697, "point": 1603, "cell": 1600}, "inca": {"lat": 47.125, "lon": 10.2601, "point": 1325, "cell": 1381}, "snowgrid": {"lat": 47.1303, "lon": 10.2671, "point": 1296, "cell": 1333}}},  # Talstation Galzigbahn
    {"id": "planneralm", "name": "Planneralm", "lat": 47.4059, "lon": 14.2007, "order": 7, "elev": {"source": "EU-DEM 25 m (OpenTopoData), abgefragt 14.10.2026", "site": 1584, "claef": {"lat": 47.403, "lon": 14.1982, "point": 1630, "cell": 1652}, "inca": {"lat": 47.4063, "lon": 14.1941, "point": 1579, "cell": 1625}, "snowgrid": {"lat": 47.4022, "lon": 14.2014, "point": 1640, "cell": 1668}}},  # Talstation Plannereckbahn
    {"id": "tauplitzalm", "name": "Tauplitzalm", "lat": 47.5964, "lon": 13.9930, "order": 8, "elev": {"source": "EU-DEM 25 m (OpenTopoData), abgefragt 14.10.2026", "site": 1640, "claef": {"lat": 47.592, "lon": 13.9957, "point": 1637, "cell": 1629}, "inca": {"lat": 47.5965, "lon": 13.9977, "point": 1643, "cell": 1616}, "snowgrid": {"lat": 47.5926, "lon": 13.9917, "point": 1611, "cell": 1624}}},  # Liftzentrum Tauplitzalm (Plateau)
]
# TAWES-ID, Name, Breite, Laenge, Hoehe (m)
STATIONS = [
    ("8989104", "Graz Lendplatz Feuerwehrturm", 47.07528, 15.4294, 351),
    ("8989103", "Graz Lendplatz", 47.07556, 15.4289, 351),
    ("11291", "Graz Universität/Heinrichstraße", 47.08, 15.448056, 366),
    ("11238", "Graz-Straßgang", 47.04611, 15.41028, 357),
    ("11240", "Graz-Thalerhof Flughafen", 46.98056, 15.44, 340),
]
# Gruppe -> Parameter; der erste Parameter entscheidet, ob eine Station die Gruppe liefert
GROUPS = {"temp": ["TL", "TP", "RF"], "wind": ["FF", "FFX", "DD"], "rain": ["RR"],
          "sun": ["SO", "GLOW"], "pressure": ["PRED"], "snow": ["SCHNEE"]}

# Alle TAWES-Stationen fuer den Standort: Dokument meta/stations im Speicher des Artifacts
# (ArtifactData get collection "meta", doc_id "stations", out_dir=. -> meta/stations.json),
# Feld rows = ["ID;Name;Breite;Laenge;Hoehe", ...] (Metadaten-Abruf 11.10.2026, nach "Stockerau" abgeschnitten).
try:
    ALL_STATIONS = [(i, n, float(a), float(o), int(h)) for i, n, a, o, h in
                    (r.split(";") for r in json.load(open(os.path.join("meta", "stations.json"), encoding="utf-8"))["rows"])]
except (OSError, ValueError, KeyError):
    ALL_STATIONS = []


# ---------- Naechste Station des Lawinenwarndienstes (seit 14.10.2026) ----------
# Dateien lwd_<gebiet>.txt: die WebFetch-Zeilen der Stationslisten (Prompt siehe Projektdokument).
#   #fmt=linea  Spalten: shortName|name|lat|lon|alt|operator|date|HS|HSD_24|TA|TA_MIN|TA_MAX|RH|VW|VW_MAX|DW|PSUM_24 (SI: K, m, m/s)
#   #fmt=tirol  Spalten: LWD-Nummer|name|lat|lon|alt|operator|date|HS|HSD24|LT|RH|WG|WG_BOE|WR|LWD-Region (°C, cm, Wind vermutlich km/h)
#   #tz=local   Zeitstempel sind Ortszeit, auch wenn sie mit Z enden (Kaernten, hydrographie.info)
# GeoSphere-Stationen werden ausgelassen (die stehen schon in TAWES). Gewaehlt wird die naechste
# Station mit Messzeit hoechstens 3 h alt und mindestens einem Wert (Temperatur, Schneehoehe, Wind).
LWD_MAX_AGE_H = 3
# Flachlandorte ohne LWD-Station (Wunsch von Andreas, 15.10.2026)
NO_LWD = {"st-peter", "griesplatz"}


def lwd_stations():
    from zoneinfo import ZoneInfo
    out = []
    for name in sorted(glob.glob("lwd_*.txt")):
        fmt, local = "linea", False
        for line in open(name, encoding="utf-8").read().splitlines():
            s = line.strip()
            if not s or s.startswith("```"):
                continue
            if s.startswith("#"):
                if s.startswith("#fmt="):
                    fmt = s[5:].split()[0]
                if s.startswith("#tz=local"):
                    local = True
                continue
            c = [x.strip() for x in s.split("|")]
            if len(c) < 15 or c[0].lower() in ("shortname", "lwd-nummer"):
                continue
            v = lambda i: num(c[i]) if i < len(c) and c[i] != "-" else None
            op = c[5] if c[5] not in ("-", "") else None
            if op and "geosphere" in op.lower():
                continue
            try:
                d = c[6].replace(" ", "T")
                if local:
                    t = dt.datetime.fromisoformat(d.rstrip("Z")[:19]).replace(tzinfo=ZoneInfo("Europe/Vienna"))
                else:
                    t = dt.datetime.fromisoformat(d.replace("Z", "+00:00"))
            except ValueError:
                continue
            if fmt == "tirol":
                hs, hsd, ta, vw, vx, dw = v(7), v(8), v(9), v(11), v(12), v(13)
                if hs is not None and hs < 0:
                    hs, hsd = None, None
            else:
                hs = v(7); hs = None if hs is None or hs < -0.5 else max(0.0, hs) * 100
                hsd = v(8); hsd = None if hsd is None or hs is None else hsd * 100
                ta = v(9); ta = None if ta is None else ta - 273.15
                vw = v(13); vw = None if vw is None else vw * 3.6
                vx = v(14); vx = None if vx is None else vx * 3.6
                dw = v(15)
            r = lambda x, n=1: None if x is None else round(x, n) + 0.0
            out.append({"station": {"id": c[0] if c[0] != "-" else None, "name": c[1], "lat": num(c[2]), "lon": num(c[3]),
                                    "alt": None if v(4) is None else round(v(4)), "operator": op},
                        "time": t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "TA": r(ta), "HS": r(hs, 0), "HSD24": r(hsd, 0), "VW": r(vw), "VWMAX": r(vx), "DW": r(dw, 0)})
    return out


def lwd_nearest(lat, lon, cands, now_utc):
    best = None
    for s in cands:
        age = (now_utc - dt.datetime.fromisoformat(s["time"].replace("Z", "+00:00"))).total_seconds() / 3600
        if age > LWD_MAX_AGE_H or age < -0.25 or all(s[k] is None for k in ("TA", "HS", "VW")):
            continue
        d = km(lat, lon, s["station"]["lat"], s["station"]["lon"])
        if best is None or d < best[0]:
            best = (d, s)
    if not best:
        return None
    s = json.loads(json.dumps(best[1]))
    s["station"]["km"] = round(best[0], 2)
    return s


# ---------- Lawinenlagebericht (seit 15.10.2026, Wunsch von Andreas) ----------
# Warnregion je Ort (EAWS-Mikroregion, ermittelt über die microRegionID der nächsten LWD-Stationen, 15.10.2026).
AVA = {
    "turracher-hoehe": [("AT-02-04-01", "Nockberge Mitte", "AT-02"),       # Station Turracherhoehe
                        ("AT-06-18", "Murberge, Gurktaler Alpen", "AT-06")],  # steirische Seite (Wunsch von Andreas, 15.10.2026)
    "schladming": ("AT-06-04-01", "Schladminger Tauern Nord", "AT-06"),    # Hochwurzen/Hauser Kaibling (AT-06-04)
    "nassfeld": ("AT-02-15-02", "Karnische Alpen Nassfeld", "AT-02"),      # Watschigeralm, Garnitzen Törl
    "st-anton": ("AT-07-07", "Lechtaler Alpen West", "AT-07"),             # Skigebiet Galzig/Kapall; Rendl liegt in AT-07-10
    "planneralm": ("AT-06-05", "Wölzer Tauern Nord", "AT-06"),             # Planneralm-Stationen
    "tauplitzalm": ("AT-06-02", "Totes Gebirge Süd", "AT-06"),             # Lawinenstein
}
AVA_SITE = {"AT-02": ("LWD Kärnten", "https://lawinenwarndienst.ktn.gv.at"),
            "AT-06": ("LWD Steiermark", "https://www.lawine-steiermark.at"),
            "AT-07": ("LWD Tirol", "https://lawinen.report")}
LEVEL = {"low": 1, "moderate": 2, "considerable": 3, "high": 4, "very_high": 5}


def ava_bulletins(region):
    """Liest ava_<Land>.txt (WebFetch-Zeilen, Prompt im Projektdokument). Fehlt die Datei: None (nicht geprüft);
    enthält sie ERROR oder keine Zeile: [] (kein Bericht)."""
    try:
        text = open(f"ava_{region}.txt", encoding="utf-8").read()
    except OSError:
        return None
    out = []
    for line in text.splitlines():
        if not line.strip().startswith("B"):
            continue
        f = {}
        for part in line.split(" | ")[1:]:
            if "=" in part:
                k, v = part.split("=", 1)
                f[k.strip()] = v.strip()
        dash = lambda x: None if x in ("-", "", "n/a", None) else x
        ratings = []
        for r in filter(None, (f.get("ratings") or "").split(";")):
            v = (r.strip().split("@") + ["-"] * 4)[:4]
            ratings.append({"value": v[0], "level": LEVEL.get(v[0]), "lower": dash(v[1]), "upper": dash(v[2]), "period": dash(v[3]) or "all_day"})
        problems = []
        for r in filter(None, (f.get("problems") or "").split(";")):
            v = (r.strip().split("@") + ["-"] * 5)[:5]
            problems.append({"type": v[0], "aspects": [a for a in v[1].split(",") if a and a != "-"], "lower": dash(v[2]),
                             "upper": dash(v[3]), "period": dash(v[4]) or "all_day"})
        out.append({"published": dash(f.get("pub")), "validFrom": dash(f.get("from")), "validTo": dash(f.get("to")),
                    "unscheduled": f.get("unscheduled") == "true", "ratings": ratings, "problems": problems,
                    "tendency": dash(f.get("tendency")), "regions": [x.strip() for x in (f.get("regions") or "").split(",") if x.strip()]})
    return out


def ava_for(pid, now_utc):
    """Liste der Lageberichte je Warnregion des Orts (meist eine), oder None."""
    if pid not in AVA:
        return None
    regs = AVA[pid] if isinstance(AVA[pid], list) else [AVA[pid]]
    out = [ava_one(r, now_utc) for r in regs]
    return None if any(o is None for o in out) else out


def ava_one(reg, now_utc):
    rid, rname, land = reg
    bl = ava_bulletins(land)
    if bl is None:
        return None
    prov, link = AVA_SITE[land]
    out = {"region": rid, "regionName": rname, "provider": prov, "link": link,
           "checked": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), "current": False}
    for b in bl:
        if rid not in b["regions"]:
            continue
        try:
            ok = ts(b["validFrom"]) <= now_utc < ts(b["validTo"])
        except (TypeError, ValueError):
            ok = False
        if ok:
            out.update({k: b[k] for k in ("published", "validFrom", "validTo", "unscheduled", "ratings", "problems", "tendency")})
            out["current"] = True
    return out


def standort():
    """Liest den von der Seite gespeicherten Standort (points/standort.json) oder None."""
    try:
        d = json.load(open(os.path.join("points", "standort.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return None
    r = d.get("req") or {}
    if not (isinstance(r.get("lat"), (int, float)) and isinstance(r.get("lon"), (int, float))):
        return None
    return {"id": "standort", "name": "Aktueller Standort", "lat": round(r["lat"], 4), "lon": round(r["lon"], 4),
            "order": 0, "dataFor": r.get("at")}


def near_stations(lat, lon, n=3):
    """Die n naechsten Stationen; Gipfelstationen (ueber 1800 m) nur, wenn naeher als 5 km."""
    c = [s for s in ALL_STATIONS if s[4] <= 1800 or km(lat, lon, s[2], s[3]) < 5]
    return sorted(c, key=lambda s: km(lat, lon, s[2], s[3]))[:n]


def km(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(d - b) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def rows(pattern):
    """Liest eine oder mehrere CSV-Dateien (Glob), entfernt ```-Zeilen, fuehrt sie zusammen."""
    out = []
    for name in sorted(glob.glob(pattern)):
        text = "\n".join(l for l in open(name, encoding="utf-8").read().splitlines()
                         if l.strip() and not l.strip().startswith("```"))
        out += list(csv.DictReader(io.StringIO(text)))
    return out or None


def num(x):
    try:
        return None if x in (None, "") else float(x)
    except ValueError:
        return None


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def key(col):  # "2t [degree Celsius]" -> "2t"
    return col.split(" [")[0]


def steady(times, minutes):
    t = [ts(x) for x in times]
    return len(t) > 1 and all((b - a) == dt.timedelta(minutes=minutes) for a, b in zip(t, t[1:]))


def by_time(rs):  # doppelte Zeitpunkte entfernen, nach Zeit sortieren
    return sorted({r["time"]: r for r in rs}.values(), key=lambda r: ts(r["time"]))


for P in POINTS:
    # feste Graz-Stationen und die 3 naechsten aus ALL_STATIONS, aber nur bis 30 km Entfernung
    cand = STATIONS + [s for s in near_stations(P["lat"], P["lon"]) if s[0] not in {x[0] for x in STATIONS}]
    P["stations"] = [s for s in cand if km(P["lat"], P["lon"], s[2], s[3]) <= 30]

S = standort()  # "Aktueller Standort" (seit 14.10.2026), von der Seite in points/standort gespeichert
if S:
    cand = STATIONS + [s for s in near_stations(S["lat"], S["lon"]) if s[0] not in {x[0] for x in STATIONS}]
    S["stations"] = [s for s in cand if km(S["lat"], S["lon"], s[2], s[3]) <= 30]
    POINTS = POINTS + [S]

if len(sys.argv) > 1 and sys.argv[1] == "ids":
    ids = []
    for P in POINTS:
        ids += [s[0] for s in P.get("stations", STATIONS) if s[0] not in ids]
    print("station_ids=" + ",".join(ids))
    print(f"standort; {S['lat']},{S['lon']}" if S else "kein Standort gespeichert")
    sys.exit(0)

now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
cur = rows("cur.csv")
LWD = lwd_stations()

for P in POINTS:
    out = {k: v for k, v in P.items() if k not in ("prefer", "stations")}
    out["updated"] = now
    pref = P.get("prefer", [])
    # bevorzugte Stationen zuerst (in angegebener Reihenfolge), danach nach Entfernung
    order = sorted(P.get("stations", STATIONS), key=lambda s: (pref.index(s[0]) if s[0] in pref else len(pref),
                                            km(P["lat"], P["lon"], s[2], s[3])))
    if cur:
        by = {r["station"]: r for r in cur}
        groups = {}
        for g, keys in GROUPS.items():
            for sid, name, la, lo, alt in order:
                r = by.get(sid)
                if r and num(r.get(keys[0])) is not None:
                    groups[g] = {"station": {"id": sid, "name": name, "alt": alt,
                                             "km": round(km(P["lat"], P["lon"], la, lo), 2)},
                                 "time": r["time"], **{k: num(r.get(k)) for k in keys}}
                    break
        if groups:
            out["now"] = {"groups": groups}

    if P["id"] in NO_LWD:
        out["lwd"] = {"__delete__": True}
    elif LWD:
        L = lwd_nearest(P["lat"], P["lon"], LWD, dt.datetime.now(dt.timezone.utc))
        out["lwd"] = L if L else {"__delete__": True}

    A = ava_for(P["id"], dt.datetime.now(dt.timezone.utc))
    if A:
        out["avalanche"] = A

    # Verlauf der letzten Stunden: INCA-Analyse am naechsten Gitterpunkt (stuendlich)
    inc = rows(f"inca_{P['id']}*.csv")
    if inc:
        inc = by_time(inc)
        cols = {key(c): c for c in inc[0].keys()}
        if len(inc) >= 3 and steady([r["time"] for r in inc], 60) and "T2M" in cols:
            # "station" stammt aus dem frueheren Stationsverlauf und wird beim update entfernt
            out["recent"] = {"source": "inca", "dataset": "inca-v1-1h-1km", "station": {"__delete__": True},
                             "grid": {"lat": round(num(inc[0]["lat"]), 4), "lon": round(num(inc[0]["lon"]), 4)},
                             "time": [r["time"] for r in inc], "TL": [num(r[cols["T2M"]]) for r in inc],
                             "RR": [num(r[cols["RR"]]) for r in inc] if "RR" in cols else None}
        else:
            print(f"  ! {P['id']}: INCA unvollstaendig, nicht uebernommen")

    fc = rows(f"fc_{P['id']}*.csv")
    if fc:
        fc = by_time(fc)
        cols = {key(c): c for c in fc[0].keys()}
        times = [r["time"] for r in fc]
        if steady(times, 60) and all(k in cols for k in ("2t", "tp", "10fg", "tcc", "sund")):
            f = lambda k: [num(r[cols[k]]) for r in fc] if k in cols else None
            out["forecast"] = {
                "dataset": "nwp-v2-1h-1km", "model": "C-LAEF AlpeAdria deterministisch",
                "run": (ts(times[-1]) - dt.timedelta(hours=60)).strftime("%Y-%m-%dT%H:%MZ"),
                "grid": {"lat": round(num(fc[0]["lat"]), 4), "lon": round(num(fc[0]["lon"]), 4)},
                "time": times, "t2m": f("2t"), "tp": f("tp"), "sf": f("sf"), "fg": f("10fg"),
                "tcc": f("tcc"), "sund": f("sund"), "u": f("10u"), "v": f("10v")}
        else:
            print(f"  ! {P['id']}: Prognose unvollstaendig, nicht uebernommen")

    nc = rows(f"nc_{P['id']}*.csv")
    if nc:
        nc = by_time(nc)
        cols = {key(c): c for c in nc[0].keys()}
        times = [r["time"] for r in nc]
        if steady(times, 15) and "t2m" in cols and "rr" in cols:
            out["nowcast"] = {"dataset": "nowcast-v1-15min-1km", "time": times,
                              "t2m": [num(r[cols["t2m"]]) for r in nc], "rr": [num(r[cols["rr"]]) for r in nc]}

    ens = rows(f"ens_{P['id']}*.csv")
    if ens:
        ens = by_time(ens)
        cols = {key(c): c for c in ens[0].keys()}
        times = [r["time"] for r in ens]
        if steady(times, 60) and all(k in cols for k in ("tp_p10", "tp_p50", "tp_p90")):
            out["ensemble"] = {"dataset": "ensemble-v2-1h-1km", "time": times,
                               **{k: [num(r[cols[k]]) for r in ens] for k in ("tp_p10", "tp_p50", "tp_p90")}}
        else:
            print(f"  ! {P['id']}: Ensemble unvollstaendig, nicht uebernommen")

    # Schnee: modellierte Schneehoehe (SNOWGRID, letzter vorhandener Tag) und Schneefallgrenze
    sg = rows(f"snow_{P['id']}*.csv")
    if sg:
        sg = [r for r in by_time(sg) if num(r[[c for c in r if key(c) == "snow_depth"][0]]) is not None]
        if sg:
            r = sg[-1]
            out["snow"] = {"dataset": "snowgrid_cl-v2-1d-1km", "time": r["time"],
                           "depth_cm": round(num(r[[c for c in r if key(c) == "snow_depth"][0]]) * 100),
                           "grid": {"lat": round(num(r["lat"]), 4), "lon": round(num(r["lon"]), 4)}}
    sl = rows(f"snl_{P['id']}*.csv")
    if sl:
        sl = by_time(sl)
        cols = {key(c): c for c in sl[0].keys()}
        if steady([r["time"] for r in sl], 60) and "snowlmt" in cols:
            out["snowlimit"] = {"dataset": "nwp-v2-1h-1km", "time": [r["time"] for r in sl],
                                "m": [None if num(r[cols["snowlmt"]]) is None else round(num(r[cols["snowlmt"]])) for r in sl]}

    if P["id"] == "standort" and "forecast" not in out:
        # ohne Prognose gilt der neue Standort noch nicht als versorgt (Seite zeigt weiter "Daten folgen")
        for k in ("lat", "lon", "dataFor"):
            out.pop(k, None)
    json.dump(out, open(f"point_{P['id']}.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(P["id"], "->", [k for k in ("now", "recent", "forecast", "nowcast", "ensemble") if k in out])
    if "recent" in out:
        print("    INCA:", out["recent"]["time"][0][:16], "bis", out["recent"]["time"][-1][:16], "Gitterpunkt", out["recent"]["grid"])
    for g, v in out.get("now", {}).get("groups", {}).items():
        print(f"    {g}: {v['station']['name']} ({v['station']['km']} km) {v['time']}")
    if isinstance(out.get("lwd"), dict) and "station" in out["lwd"]:
        L = out["lwd"]; print(f"    LWD: {L['station']['name']} ({L['station']['km']} km, {L['station']['alt']} m) {L['time']} TA={L['TA']} HS={L['HS']} VW={L['VW']}")
    if "snow" in out:
        print("    SNOWGRID:", out["snow"]["time"][:10], out["snow"]["depth_cm"], "cm")
    if "forecast" in out:
        print("    Prognose:", len(out["forecast"]["time"]), "Stunden, Lauf", out["forecast"]["run"])
