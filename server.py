#!/usr/bin/env python3
"""
BULK Globe — Backend Server
============================
Counts unique traders who have EVER opened a position on BULK Exchange
by collecting maker/taker pubkeys from the live WebSocket trades stream.

The set of unique pubkeys is persisted to disk (traders.json) so the
count survives server restarts and only ever grows.

BULK API integration:
  WebSocket wss://exchange-ws1.bulk.trade
    → trades (BTC-USD, ETH-USD, SOL-USD) → unique pubkeys
    → frontendContext → all-market summary every 2s
  HTTP https://exchange-api.bulk.trade/api/v1
    → GET /stats        → volume, OI, funding
    → GET /ticker/*     → per-market price data
    → GET /exchangeInfo → available markets

Run:
    pip install flask requests websocket-client
    python3 server.py
    open http://localhost:8080
"""

import json
import time
import threading
from pathlib import Path
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__, static_folder='static')
BASE = Path(__file__).parent
DATA = BASE / 'data'
TRADERS_FILE = BASE / 'traders.json'

# ─────────────────────────────────────────────────────────
# PERSISTENT UNIQUE TRADERS SET
# ─────────────────────────────────────────────────────────
def load_traders():
    """Load previously seen trader pubkeys from disk."""
    if TRADERS_FILE.exists():
        try:
            data = json.loads(TRADERS_FILE.read_text())
            pubkeys = set(data.get("pubkeys", []))
            print(f"[DISK] Loaded {len(pubkeys)} known traders from {TRADERS_FILE.name}")
            return pubkeys
        except Exception as e:
            print(f"[DISK] Error loading traders: {e}")
    return set()


def save_traders():
    """Save unique trader pubkeys to disk."""
    try:
        data = {
            "pubkeys": list(bulk["unique_traders"]),
            "count": len(bulk["unique_traders"]),
            "trades_total": bulk["trades_total"],
            "last_saved": time.time()
        }
        TRADERS_FILE.write_text(json.dumps(data))
    except Exception as e:
        print(f"[DISK] Error saving traders: {e}")


def save_traders_periodic():
    """Save to disk every 60 seconds."""
    while True:
        time.sleep(60)
        if bulk["unique_traders"]:
            save_traders()


# ─────────────────────────────────────────────────────────
# POPULATION DATA — UN World Population Prospects 2024
# ─────────────────────────────────────────────────────────
COUNTRIES = {
    "004": {"name": "Afghanistan", "pop": 42239854, "region": "Asia"},
    "008": {"name": "Albania", "pop": 2745972, "region": "Europe"},
    "010": {"name": "Antarctica", "pop": 0, "region": "Antarctica"},
    "012": {"name": "Algeria", "pop": 45606480, "region": "Africa"},
    "020": {"name": "Andorra", "pop": 80088, "region": "Europe"},
    "024": {"name": "Angola", "pop": 36684202, "region": "Africa"},
    "031": {"name": "Azerbaijan", "pop": 10412651, "region": "Asia"},
    "032": {"name": "Argentina", "pop": 46654581, "region": "Americas"},
    "036": {"name": "Australia", "pop": 26713205, "region": "Oceania"},
    "040": {"name": "Austria", "pop": 9158750, "region": "Europe"},
    "044": {"name": "Bahamas", "pop": 412623, "region": "Americas"},
    "048": {"name": "Bahrain", "pop": 1577059, "region": "Asia"},
    "050": {"name": "Bangladesh", "pop": 172954319, "region": "Asia"},
    "051": {"name": "Armenia", "pop": 2777970, "region": "Asia"},
    "056": {"name": "Belgium", "pop": 11822592, "region": "Europe"},
    "064": {"name": "Bhutan", "pop": 787424, "region": "Asia"},
    "068": {"name": "Bolivia", "pop": 12388571, "region": "Americas"},
    "070": {"name": "Bosnia and Herzegovina", "pop": 3210847, "region": "Europe"},
    "072": {"name": "Botswana", "pop": 2675352, "region": "Africa"},
    "076": {"name": "Brazil", "pop": 216422446, "region": "Americas"},
    "084": {"name": "Belize", "pop": 420110, "region": "Americas"},
    "090": {"name": "Solomon Islands", "pop": 740424, "region": "Oceania"},
    "096": {"name": "Brunei", "pop": 452524, "region": "Asia"},
    "100": {"name": "Bulgaria", "pop": 6447710, "region": "Europe"},
    "104": {"name": "Myanmar", "pop": 54179306, "region": "Asia"},
    "108": {"name": "Burundi", "pop": 13238559, "region": "Africa"},
    "112": {"name": "Belarus", "pop": 9056000, "region": "Europe"},
    "116": {"name": "Cambodia", "pop": 17423880, "region": "Asia"},
    "120": {"name": "Cameroon", "pop": 28647293, "region": "Africa"},
    "124": {"name": "Canada", "pop": 40097761, "region": "Americas"},
    "140": {"name": "Central African Republic", "pop": 5579144, "region": "Africa"},
    "144": {"name": "Sri Lanka", "pop": 22437000, "region": "Asia"},
    "148": {"name": "Chad", "pop": 18278568, "region": "Africa"},
    "152": {"name": "Chile", "pop": 19764771, "region": "Americas"},
    "156": {"name": "China", "pop": 1425178782, "region": "Asia"},
    "158": {"name": "Taiwan", "pop": 23923276, "region": "Asia"},
    "170": {"name": "Colombia", "pop": 52085168, "region": "Americas"},
    "178": {"name": "Congo", "pop": 6106869, "region": "Africa"},
    "180": {"name": "DR Congo", "pop": 105044646, "region": "Africa"},
    "188": {"name": "Costa Rica", "pop": 5212173, "region": "Americas"},
    "191": {"name": "Croatia", "pop": 3850894, "region": "Europe"},
    "192": {"name": "Cuba", "pop": 11194449, "region": "Americas"},
    "196": {"name": "Cyprus", "pop": 1358100, "region": "Asia"},
    "203": {"name": "Czechia", "pop": 10900555, "region": "Europe"},
    "204": {"name": "Benin", "pop": 13712828, "region": "Africa"},
    "208": {"name": "Denmark", "pop": 5946952, "region": "Europe"},
    "214": {"name": "Dominican Republic", "pop": 11427557, "region": "Americas"},
    "218": {"name": "Ecuador", "pop": 18190484, "region": "Americas"},
    "222": {"name": "El Salvador", "pop": 6364943, "region": "Americas"},
    "226": {"name": "Equatorial Guinea", "pop": 1714671, "region": "Africa"},
    "231": {"name": "Ethiopia", "pop": 129719719, "region": "Africa"},
    "232": {"name": "Eritrea", "pop": 3620312, "region": "Africa"},
    "233": {"name": "Estonia", "pop": 1373101, "region": "Europe"},
    "238": {"name": "Falkland Islands", "pop": 3791, "region": "Americas"},
    "242": {"name": "Fiji", "pop": 936375, "region": "Oceania"},
    "246": {"name": "Finland", "pop": 5603851, "region": "Europe"},
    "250": {"name": "France", "pop": 68170228, "region": "Europe"},
    "262": {"name": "Djibouti", "pop": 1136455, "region": "Africa"},
    "266": {"name": "Gabon", "pop": 2436566, "region": "Africa"},
    "268": {"name": "Georgia", "pop": 3728282, "region": "Asia"},
    "270": {"name": "Gambia", "pop": 2773168, "region": "Africa"},
    "275": {"name": "Palestine", "pop": 5371230, "region": "Asia"},
    "276": {"name": "Germany", "pop": 84482267, "region": "Europe"},
    "288": {"name": "Ghana", "pop": 34121985, "region": "Africa"},
    "300": {"name": "Greece", "pop": 10341277, "region": "Europe"},
    "304": {"name": "Greenland", "pop": 56865, "region": "Americas"},
    "320": {"name": "Guatemala", "pop": 18092026, "region": "Americas"},
    "324": {"name": "Guinea", "pop": 14431780, "region": "Africa"},
    "328": {"name": "Guyana", "pop": 813834, "region": "Americas"},
    "332": {"name": "Haiti", "pop": 11772557, "region": "Americas"},
    "340": {"name": "Honduras", "pop": 10593798, "region": "Americas"},
    "348": {"name": "Hungary", "pop": 9597085, "region": "Europe"},
    "352": {"name": "Iceland", "pop": 393396, "region": "Europe"},
    "356": {"name": "India", "pop": 1428627663, "region": "Asia"},
    "360": {"name": "Indonesia", "pop": 277534122, "region": "Asia"},
    "364": {"name": "Iran", "pop": 89172767, "region": "Asia"},
    "368": {"name": "Iraq", "pop": 44496122, "region": "Asia"},
    "372": {"name": "Ireland", "pop": 5262382, "region": "Europe"},
    "376": {"name": "Israel", "pop": 9557500, "region": "Asia"},
    "380": {"name": "Italy", "pop": 58870762, "region": "Europe"},
    "384": {"name": "Cote d'Ivoire", "pop": 29389150, "region": "Africa"},
    "388": {"name": "Jamaica", "pop": 2825544, "region": "Americas"},
    "392": {"name": "Japan", "pop": 123951692, "region": "Asia"},
    "398": {"name": "Kazakhstan", "pop": 20260000, "region": "Asia"},
    "400": {"name": "Jordan", "pop": 11500800, "region": "Asia"},
    "404": {"name": "Kenya", "pop": 56583200, "region": "Africa"},
    "408": {"name": "North Korea", "pop": 26160821, "region": "Asia"},
    "410": {"name": "South Korea", "pop": 51712619, "region": "Asia"},
    "414": {"name": "Kuwait", "pop": 4464521, "region": "Asia"},
    "417": {"name": "Kyrgyzstan", "pop": 7037900, "region": "Asia"},
    "418": {"name": "Laos", "pop": 7633779, "region": "Asia"},
    "422": {"name": "Lebanon", "pop": 5490000, "region": "Asia"},
    "426": {"name": "Lesotho", "pop": 2330318, "region": "Africa"},
    "428": {"name": "Latvia", "pop": 1830211, "region": "Europe"},
    "430": {"name": "Liberia", "pop": 5418377, "region": "Africa"},
    "434": {"name": "Libya", "pop": 7137931, "region": "Africa"},
    "440": {"name": "Lithuania", "pop": 2831639, "region": "Europe"},
    "442": {"name": "Luxembourg", "pop": 672050, "region": "Europe"},
    "450": {"name": "Madagascar", "pop": 30325732, "region": "Africa"},
    "454": {"name": "Malawi", "pop": 21196629, "region": "Africa"},
    "458": {"name": "Malaysia", "pop": 34308525, "region": "Asia"},
    "466": {"name": "Mali", "pop": 23293698, "region": "Africa"},
    "470": {"name": "Malta", "pop": 539560, "region": "Europe"},
    "478": {"name": "Mauritania", "pop": 4862989, "region": "Africa"},
    "480": {"name": "Mauritius", "pop": 1300557, "region": "Africa"},
    "484": {"name": "Mexico", "pop": 131541424, "region": "Americas"},
    "496": {"name": "Mongolia", "pop": 3447157, "region": "Asia"},
    "498": {"name": "Moldova", "pop": 2512758, "region": "Europe"},
    "499": {"name": "Montenegro", "pop": 616177, "region": "Europe"},
    "504": {"name": "Morocco", "pop": 37457971, "region": "Africa"},
    "508": {"name": "Mozambique", "pop": 33897354, "region": "Africa"},
    "512": {"name": "Oman", "pop": 4644384, "region": "Asia"},
    "516": {"name": "Namibia", "pop": 2604172, "region": "Africa"},
    "520": {"name": "Nauru", "pop": 12780, "region": "Oceania"},
    "524": {"name": "Nepal", "pop": 30896590, "region": "Asia"},
    "528": {"name": "Netherlands", "pop": 17947406, "region": "Europe"},
    "540": {"name": "New Caledonia", "pop": 292991, "region": "Oceania"},
    "548": {"name": "Vanuatu", "pop": 334506, "region": "Oceania"},
    "554": {"name": "New Zealand", "pop": 5228100, "region": "Oceania"},
    "558": {"name": "Nicaragua", "pop": 7046310, "region": "Americas"},
    "562": {"name": "Niger", "pop": 27202843, "region": "Africa"},
    "566": {"name": "Nigeria", "pop": 229152217, "region": "Africa"},
    "578": {"name": "Norway", "pop": 5488984, "region": "Europe"},
    "586": {"name": "Pakistan", "pop": 240485658, "region": "Asia"},
    "591": {"name": "Panama", "pop": 4468087, "region": "Americas"},
    "598": {"name": "Papua New Guinea", "pop": 10329931, "region": "Oceania"},
    "600": {"name": "Paraguay", "pop": 6861524, "region": "Americas"},
    "604": {"name": "Peru", "pop": 34352719, "region": "Americas"},
    "608": {"name": "Philippines", "pop": 117337368, "region": "Asia"},
    "616": {"name": "Poland", "pop": 37561599, "region": "Europe"},
    "620": {"name": "Portugal", "pop": 10425292, "region": "Europe"},
    "624": {"name": "Guinea-Bissau", "pop": 2150842, "region": "Africa"},
    "626": {"name": "Timor-Leste", "pop": 1360596, "region": "Asia"},
    "630": {"name": "Puerto Rico", "pop": 3205691, "region": "Americas"},
    "634": {"name": "Qatar", "pop": 2716391, "region": "Asia"},
    "642": {"name": "Romania", "pop": 19015080, "region": "Europe"},
    "643": {"name": "Russia", "pop": 144236933, "region": "Europe"},
    "646": {"name": "Rwanda", "pop": 14094683, "region": "Africa"},
    "682": {"name": "Saudi Arabia", "pop": 36947025, "region": "Asia"},
    "686": {"name": "Senegal", "pop": 17763163, "region": "Africa"},
    "688": {"name": "Serbia", "pop": 6641197, "region": "Europe"},
    "694": {"name": "Sierra Leone", "pop": 8791092, "region": "Africa"},
    "702": {"name": "Singapore", "pop": 5917600, "region": "Asia"},
    "703": {"name": "Slovakia", "pop": 5460185, "region": "Europe"},
    "704": {"name": "Vietnam", "pop": 100352115, "region": "Asia"},
    "705": {"name": "Slovenia", "pop": 2119675, "region": "Europe"},
    "706": {"name": "Somalia", "pop": 18143378, "region": "Africa"},
    "710": {"name": "South Africa", "pop": 62027503, "region": "Africa"},
    "716": {"name": "Zimbabwe", "pop": 16665409, "region": "Africa"},
    "724": {"name": "Spain", "pop": 47910526, "region": "Europe"},
    "728": {"name": "South Sudan", "pop": 11088796, "region": "Africa"},
    "732": {"name": "Western Sahara", "pop": 612000, "region": "Africa"},
    "740": {"name": "Suriname", "pop": 623236, "region": "Americas"},
    "748": {"name": "Eswatini", "pop": 1210822, "region": "Africa"},
    "752": {"name": "Sweden", "pop": 10612086, "region": "Europe"},
    "756": {"name": "Switzerland", "pop": 8921981, "region": "Europe"},
    "760": {"name": "Syria", "pop": 23227014, "region": "Asia"},
    "762": {"name": "Tajikistan", "pop": 10342300, "region": "Asia"},
    "764": {"name": "Thailand", "pop": 71801279, "region": "Asia"},
    "768": {"name": "Togo", "pop": 9053799, "region": "Africa"},
    "776": {"name": "Tonga", "pop": 107773, "region": "Oceania"},
    "780": {"name": "Trinidad and Tobago", "pop": 1405646, "region": "Americas"},
    "784": {"name": "United Arab Emirates", "pop": 10081785, "region": "Asia"},
    "788": {"name": "Tunisia", "pop": 12458223, "region": "Africa"},
    "792": {"name": "Turkey", "pop": 85816199, "region": "Asia"},
    "795": {"name": "Turkmenistan", "pop": 6516100, "region": "Asia"},
    "798": {"name": "Tuvalu", "pop": 11312, "region": "Oceania"},
    "800": {"name": "Uganda", "pop": 48582334, "region": "Africa"},
    "804": {"name": "Ukraine", "pop": 36744636, "region": "Europe"},
    "807": {"name": "North Macedonia", "pop": 1832696, "region": "Europe"},
    "818": {"name": "Egypt", "pop": 112716598, "region": "Africa"},
    "826": {"name": "United Kingdom", "pop": 68350000, "region": "Europe"},
    "834": {"name": "Tanzania", "pop": 67438106, "region": "Africa"},
    "840": {"name": "United States", "pop": 339996563, "region": "Americas"},
    "854": {"name": "Burkina Faso", "pop": 23251244, "region": "Africa"},
    "858": {"name": "Uruguay", "pop": 3423108, "region": "Americas"},
    "860": {"name": "Uzbekistan", "pop": 36361943, "region": "Asia"},
    "862": {"name": "Venezuela", "pop": 28838499, "region": "Americas"},
    "882": {"name": "Samoa", "pop": 225681, "region": "Oceania"},
    "887": {"name": "Yemen", "pop": 34449825, "region": "Asia"},
    "894": {"name": "Zambia", "pop": 20569737, "region": "Africa"},
    "900": {"name": "Kosovo", "pop": 1873160, "region": "Europe"},
}

# ─────────────────────────────────────────────────────────
# LIVE DATA CACHE
# ─────────────────────────────────────────────────────────
bulk = {
    "unique_traders": load_traders(),  # persistent set of all-time pubkeys
    "trades_total": 0,                 # total trades observed this session
    "trades_session": 0,               # trades this session only
    # frontendContext data (all markets, updated every 2s via WS)
    "frontend_ctx": [],
    # HTTP /stats
    "volume_24h": None,
    "open_interest": None,
    "funding_rates": {},
    "markets": [],
    # HTTP /ticker
    "btc_price": None,
    "btc_mark_price": None,
    "btc_funding": None,
    # HTTP /exchangeInfo
    "exchange_markets": [],
    # Status
    "ws_status": "disconnected",
    "http_status": "init",
    "last_ws_trade": None,
    "last_http_poll": None,
    "last_new_trader": None,
}

BULK_HTTP = "https://exchange-api.bulk.trade/api/v1"
BULK_WS = "wss://exchange-ws1.bulk.trade"


# ─────────────────────────────────────────────────────────
# THREAD 1: WebSocket — trades + frontendContext
# ─────────────────────────────────────────────────────────
def ws_thread():
    try:
        import websocket
    except ImportError:
        print("[WS] websocket-client not installed. pip install websocket-client")
        bulk["ws_status"] = "no-library"
        return

    def on_open(ws):
        print("[WS] Connected to BULK Exchange")
        bulk["ws_status"] = "connected"

        # Get market symbols from exchangeInfo if available
        symbols = [m.get("symbol") for m in bulk["exchange_markets"]] if bulk["exchange_markets"] else []
        if not symbols:
            symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]

        subs = [{"type": "trades", "symbol": s} for s in symbols]
        subs.append({"type": "frontendContext"})  # all-market summary every 2s

        ws.send(json.dumps({"method": "subscribe", "subscription": subs}))
        print(f"[WS] Subscribed: trades({', '.join(symbols)}) + frontendContext")

    def on_message(ws, message):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")

        if msg_type == "subscriptionResponse":
            print(f"[WS] Confirmed: {data.get('topics', [])}")
            return

        # TRADES → collect unique pubkeys
        if msg_type == "trades":
            trades = data.get("data", {}).get("trades", [])
            new_count = 0
            for t in trades:
                for key in ("maker", "taker"):
                    pk = t.get(key)
                    if pk and pk not in bulk["unique_traders"]:
                        bulk["unique_traders"].add(pk)
                        new_count += 1
                        bulk["last_new_trader"] = time.time()
                bulk["trades_total"] += 1
                bulk["trades_session"] += 1

            if new_count > 0:
                print(f"[WS] +{new_count} new traders → total {len(bulk['unique_traders'])}")

            bulk["last_ws_trade"] = time.time()

        # FRONTEND CONTEXT → all-market summary
        elif msg_type == "frontendContext":
            bulk["frontend_ctx"] = data.get("data", {}).get("ctx", [])

    def on_error(ws, error):
        print(f"[WS] Error: {error}")
        bulk["ws_status"] = "error"

    def on_close(ws, code, msg):
        print(f"[WS] Closed: {code} {msg}")
        bulk["ws_status"] = "disconnected"

    delay = 2
    while True:
        try:
            bulk["ws_status"] = "connecting"
            ws = websocket.WebSocketApp(
                BULK_WS,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
            )
            ws.run_forever(ping_interval=25, ping_timeout=10)
        except Exception as e:
            print(f"[WS] Exception: {e}")

        bulk["ws_status"] = "reconnecting"
        save_traders()  # save on disconnect
        print(f"[WS] Reconnecting in {delay}s...")
        time.sleep(delay)
        delay = min(delay * 2, 60)


# ─────────────────────────────────────────────────────────
# THREAD 2: HTTP polling
# ─────────────────────────────────────────────────────────
def http_thread():
    import requests

    try:
        r = requests.get(f"{BULK_HTTP}/exchangeInfo", timeout=10)
        if r.ok:
            bulk["exchange_markets"] = r.json()
            symbols = [m.get("symbol") for m in bulk["exchange_markets"]]
            print(f"[HTTP] Markets: {', '.join(symbols)}")
    except Exception as e:
        print(f"[HTTP] exchangeInfo: {e}")

    while True:
        try:
            r = requests.get(f"{BULK_HTTP}/stats", timeout=10)
            if r.ok:
                d = r.json()
                bulk["volume_24h"] = d.get("volume", {}).get("totalUsd")
                bulk["open_interest"] = d.get("openInterest", {}).get("totalUsd")
                bulk["funding_rates"] = d.get("funding", {}).get("rates", {})
                bulk["markets"] = d.get("markets", [])
                bulk["http_status"] = "live"
        except Exception as e:
            bulk["http_status"] = "error"

        try:
            r = requests.get(f"{BULK_HTTP}/ticker/BTC-USD", timeout=10)
            if r.ok:
                t = r.json()
                bulk["btc_price"] = t.get("lastPrice")
                bulk["btc_mark_price"] = t.get("markPrice")
                bulk["btc_funding"] = t.get("fundingRate")
        except Exception:
            pass

        bulk["last_http_poll"] = time.time()
        time.sleep(30)


# ─────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/topology')
def topology():
    from flask import request as req
    res = req.args.get('res', '50m')
    fname = 'countries-10m.json' if res == '10m' else 'countries-50m.json'
    fpath = DATA / fname
    if not fpath.exists():
        return jsonify({"error": f"{fname} not found"}), 404
    return send_from_directory(str(DATA), fname, mimetype='application/json')

@app.route('/api/countries')
def countries():
    return jsonify(COUNTRIES)

@app.route('/api/country/<iso>')
def country_detail(iso):
    iso = iso.zfill(3)
    c = COUNTRIES.get(iso)
    if not c:
        return jsonify({"error": f"ISO {iso} not found"}), 404
    users = len(bulk["unique_traders"])
    exceeded = users > c["pop"] if c["pop"] > 0 else False
    excess = users - c["pop"] if exceeded else 0
    pct = round((excess / c["pop"]) * 100, 2) if exceeded and c["pop"] > 0 else 0
    return jsonify({
        "iso": iso, "name": c["name"], "population": c["pop"],
        "region": c["region"], "bulkUsers": users,
        "exceeded": exceeded, "excess": excess, "excessPercent": pct
    })

@app.route('/api/bulk')
def bulk_status():
    return jsonify({
        "uniqueTraders": len(bulk["unique_traders"]),
        "tradesTotal": bulk["trades_total"],
        "tradesSession": bulk["trades_session"],
        "frontendCtx": bulk["frontend_ctx"],
        "volume24h": bulk["volume_24h"],
        "openInterest": bulk["open_interest"],
        "fundingRates": bulk["funding_rates"],
        "markets": bulk["markets"],
        "btcPrice": bulk["btc_price"],
        "btcMarkPrice": bulk["btc_mark_price"],
        "btcFunding": bulk["btc_funding"],
        "exchangeMarkets": [m.get("symbol") for m in bulk["exchange_markets"]] if bulk["exchange_markets"] else [],
        "wsStatus": bulk["ws_status"],
        "httpStatus": bulk["http_status"],
        "lastWsTrade": bulk["last_ws_trade"],
        "lastHttpPoll": bulk["last_http_poll"],
        "lastNewTrader": bulk["last_new_trader"],
    })

@app.route('/api/comparison')
def comparison():
    users = len(bulk["unique_traders"])
    results = []
    for iso, c in COUNTRIES.items():
        if c["pop"] == 0: continue
        exceeded = users > c["pop"]
        results.append({
            "iso": iso, "name": c["name"], "population": c["pop"],
            "region": c["region"], "exceeded": exceeded,
            "excess": users - c["pop"] if exceeded else 0
        })
    results.sort(key=lambda x: x["population"])
    return jsonify({
        "bulkUsers": users,
        "totalCountries": len(results),
        "exceededCount": sum(1 for r in results if r["exceeded"]),
        "countries": results
    })


# ─────────────────────────────────────────────────────────
# TRADER MARKERS — users pin their location on the globe
# Persisted to markers.json
# ─────────────────────────────────────────────────────────
MARKERS_FILE = BASE / 'markers.json'

def load_markers():
    if MARKERS_FILE.exists():
        try:
            return json.loads(MARKERS_FILE.read_text())
        except Exception:
            pass
    return []

def save_markers(markers):
    try:
        MARKERS_FILE.write_text(json.dumps(markers, indent=2))
    except Exception as e:
        print(f"[MARKERS] Save error: {e}")

@app.route('/api/markers', methods=['GET'])
def get_markers():
    ms = load_markers()
    # Strip secret tokens — only the creator knows their secret
    safe = [{k: v for k, v in m.items() if k != 'secret'} for m in ms]
    return jsonify(safe)

@app.route('/api/markers', methods=['POST'])
def add_marker():
    from flask import request as req
    data = req.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    lat = data.get("lat")
    lon = data.get("lon")
    wallet = (data.get("wallet") or "").strip()
    username = (data.get("username") or "").strip()

    if lat is None or lon is None:
        return jsonify({"error": "lat and lon required"}), 400
    if not wallet:
        return jsonify({"error": "wallet address required"}), 400
    if not username:
        return jsonify({"error": "username required"}), 400
    if len(wallet) > 100 or len(username) > 50:
        return jsonify({"error": "fields too long"}), 400

    markers = load_markers()

    # Prevent duplicate wallet
    for m in markers:
        if m.get("wallet") == wallet:
            return jsonify({"error": "This wallet is already on the map"}), 409

    import hashlib, secrets
    secret = secrets.token_hex(16)  # 32-char hex token
    marker_id = hashlib.sha256(f"{wallet}{time.time()}".encode()).hexdigest()[:12]

    marker = {
        "id": marker_id,
        "lat": float(lat),
        "lon": float(lon),
        "wallet": wallet,
        "username": username,
        "created": time.time(),
        "secret": secret,  # stored on server, sent only on creation
    }
    markers.append(marker)
    save_markers(markers)
    print(f"[MARKER] +{username} ({wallet[:12]}...) at {lat:.1f},{lon:.1f}")
    return jsonify(marker), 201  # includes secret in response

@app.route('/api/markers/<marker_id>', methods=['DELETE'])
def delete_marker(marker_id):
    from flask import request as req
    data = req.get_json() or {}
    token = data.get("secret", "")

    markers = load_markers()
    target = None
    for m in markers:
        if m.get("id") == marker_id:
            target = m
            break

    if not target:
        return jsonify({"error": "Marker not found"}), 404

    if not token or token != target.get("secret"):
        return jsonify({"error": "Unauthorized — wrong or missing secret"}), 403

    markers = [m for m in markers if m.get("id") != marker_id]
    save_markers(markers)
    print(f"[MARKER] Deleted {target.get('username')} ({marker_id})")
    return jsonify({"ok": True})


@app.route('/api/wallet-stats/<wallet>')
def wallet_stats(wallet):
    """Fetch trading stats for a wallet from BULK API.
    Uses POST /account with types: fills, positions (unsigned, public)."""
    import requests as req

    stats = {
        "wallet": wallet,
        "totalTrades": 0,
        "totalVolume": 0,
        "totalPnl": 0,
        "liquidations": 0,
        "status": "loading"
    }

    # Fetch fills (trade history)
    try:
        r = req.post(f"{BULK_HTTP}/account",
            json={"type": "fills", "user": wallet},
            headers={"Content-Type": "application/json"},
            timeout=10)
        if r.ok:
            fills = r.json()
            total_trades = 0
            total_volume = 0
            for item in fills:
                f = item.get("fills")
                if not f:
                    continue
                total_trades += 1
                price = f.get("price", 0)
                amount = abs(f.get("amount", 0))
                total_volume += price * amount
            stats["totalTrades"] = total_trades
            stats["totalVolume"] = round(total_volume, 2)
    except Exception as e:
        print(f"[STATS] fills error for {wallet[:12]}: {e}")

    # Fetch closed positions (PnL + liquidations)
    try:
        r = req.post(f"{BULK_HTTP}/account",
            json={"type": "positions", "user": wallet},
            headers={"Content-Type": "application/json"},
            timeout=10)
        if r.ok:
            positions = r.json()
            total_pnl = 0
            liquidations = 0
            for item in positions:
                p = item.get("positions")
                if not p:
                    continue
                total_pnl += p.get("realizedPnl", 0)
                total_pnl -= p.get("fees", 0)
                total_pnl += p.get("funding", 0)
                if p.get("closeReason") == "liquidation":
                    liquidations += 1
            stats["totalPnl"] = round(total_pnl, 2)
            stats["liquidations"] = liquidations
    except Exception as e:
        print(f"[STATS] positions error for {wallet[:12]}: {e}")

    stats["status"] = "ok"
    return jsonify(stats)

# ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    import os
    PORT = int(os.environ.get('PORT', 8080))
    for f in ['countries-50m.json']:
        if not (DATA / f).exists():
            print(f"WARNING: {DATA / f} not found!")

    threading.Thread(target=ws_thread, daemon=True).start()
    threading.Thread(target=http_thread, daemon=True).start()
    threading.Thread(target=save_traders_periodic, daemon=True).start()

    n = len(bulk["unique_traders"])
    print()
    print("  ╔════════════════════════════════════════════════╗")
    print("  ║            BULK GLOBE SERVER                   ║")
    print("  ║                                                ║")
    print(f"  ║   → http://localhost:{PORT}                      ║")
    print("  ║                                                ║")
    print(f"  ║   Known traders from disk: {n:<20} ║")
    print("  ║   Traders file: traders.json                   ║")
    print("  ║                                                ║")
    print("  ║   WS  trades + frontendContext                 ║")
    print("  ║   HTTP /stats /ticker /exchangeInfo            ║")
    print("  ╚════════════════════════════════════════════════╝")
    print()

    app.run(host='0.0.0.0', port=PORT, debug=False)
