#!/usr/bin/env python3
"""
BULK API Diagnostic — run this to find where the problem is.
Usage: python3 diagnose.py
"""
import sys, json, time

print("\n" + "="*56)
print("  BULK API DIAGNOSTIC")
print("="*56 + "\n")

# 1. Dependencies
print("[1/6] Dependencies...")
ok = True
for mod, pkg in [("requests","requests"),("flask","flask"),("websocket","websocket-client")]:
    try:
        m = __import__(mod)
        print(f"  ✓ {pkg} {getattr(m,'__version__','ok')}")
    except ImportError:
        print(f"  ✗ {pkg} MISSING")
        ok = False
if not ok:
    print("\n  Fix: pip3 install flask requests websocket-client\n")
import requests

# 2. exchangeInfo
print("\n[2/6] GET /exchangeInfo ...")
B = "https://exchange-api.bulk.trade/api/v1"
try:
    r = requests.get(f"{B}/exchangeInfo", timeout=10)
    if r.ok:
        d = r.json()
        syms = [m.get("symbol","?") for m in d] if isinstance(d,list) else []
        print(f"  ✓ {len(syms)} markets: {', '.join(syms)}")
    else: print(f"  ✗ HTTP {r.status_code}: {r.text[:100]}")
except Exception as e: print(f"  ✗ {e}")

# 3. stats
print("\n[3/6] GET /stats ...")
try:
    r = requests.get(f"{B}/stats", timeout=10)
    if r.ok:
        d = r.json()
        v = d.get("volume",{}).get("totalUsd")
        o = d.get("openInterest",{}).get("totalUsd")
        print(f"  ✓ Volume: ${v:,.0f}" if v else "  - Volume: null")
        print(f"  ✓ OI: ${o:,.0f}" if o else "  - OI: null")
    else: print(f"  ✗ HTTP {r.status_code}")
except Exception as e: print(f"  ✗ {e}")

# 4. ticker
print("\n[4/6] GET /ticker/BTC-USD ...")
try:
    r = requests.get(f"{B}/ticker/BTC-USD", timeout=10)
    if r.ok:
        d = r.json()
        print(f"  ✓ Price: ${d.get('lastPrice')}  Mark: ${d.get('markPrice')}")
    else: print(f"  ✗ HTTP {r.status_code}")
except Exception as e: print(f"  ✗ {e}")

# 5. WebSocket
print("\n[5/6] WebSocket wss://exchange-ws1.bulk.trade (15s)...")
try:
    import websocket, threading
    res = {"conn":False,"sub":False,"topics":[],"trades":0,"traders":set(),"ctx":False}
    def on_o(ws):
        res["conn"] = True; print("  ✓ Connected")
        ws.send(json.dumps({"method":"subscribe","subscription":[
            {"type":"trades","symbol":"BTC-USD"},{"type":"frontendContext"}]}))
    def on_m(ws, m):
        d = json.loads(m)
        if d.get("type")=="subscriptionResponse":
            res["sub"]=True; res["topics"]=d.get("topics",[])
            print(f"  ✓ Subscribed: {res['topics']}")
        elif d.get("type")=="trades":
            for t in d.get("data",{}).get("trades",[]):
                res["trades"]+=1
                for k in("maker","taker"):
                    if t.get(k): res["traders"].add(t[k])
                if res["trades"]<=3:
                    print(f"  ✓ Trade: {t.get('s')} {'BUY' if t.get('side') else 'SELL'} {t.get('sz')} @ ${t.get('px')}")
        elif d.get("type")=="frontendContext":
            res["ctx"]=True
            ctx=d.get("data",{}).get("ctx",[])
            if ctx and not hasattr(res,'ctx_shown'):
                res['ctx_shown']=True
                print(f"  ✓ frontendContext: {len(ctx)} markets")
    def on_e(ws,e): print(f"  ✗ {e}")
    ws=websocket.WebSocketApp("wss://exchange-ws1.bulk.trade",on_open=on_o,on_message=on_m,on_error=on_e)
    t=threading.Thread(target=lambda:ws.run_forever(ping_interval=25,ping_timeout=10),daemon=True)
    t.start()
    for _ in range(15):
        time.sleep(1)
        if res["trades"]>=5: break
    ws.close(); time.sleep(0.5)
    print(f"\n  Summary: connected={res['conn']}, subscribed={res['sub']}")
    print(f"  Trades: {res['trades']}, Unique traders: {len(res['traders'])}")
    print(f"  frontendContext received: {res['ctx']}")
except ImportError: print("  ✗ Skipped (websocket-client not installed)")
except Exception as e: print(f"  ✗ {e}")

# 6. Local server
print("\n[6/6] Local server http://localhost:8080 ...")
try:
    r = requests.get("http://localhost:8080/api/bulk", timeout=5)
    if r.ok:
        d = r.json()
        print(f"  ✓ Running!")
        print(f"    Unique traders: {d.get('uniqueTraders',0)}")
        print(f"    Trades total:   {d.get('tradesTotal',0)}")
        print(f"    This session:   {d.get('tradesSession',0)}")
        print(f"    WS: {d.get('wsStatus')}  HTTP: {d.get('httpStatus')}")
        print(f"    BTC: {d.get('btcPrice')}  Vol: {d.get('volume24h')}")
except requests.exceptions.ConnectionRefused:
    print("  ✗ Not running → python3 server.py")
except Exception as e: print(f"  ✗ {e}")

print("\n" + "="*56)
print("  DONE")
print("="*56)
print("""
  Unique traders = 0?
    → BULK is on alphanet with limited activity
    → The count grows as trades happen (persisted to disk)
    → Leave server running; count only goes up

  HTTP fails?
    → BULK API may be down / network issue
    → Check https://alphanet.bulk.trade in browser

  WebSocket fails?
    → Firewall may block wss:// connections
    → HTTP data still works independently
""")
