# BULK GLOBE — Paper Mainnet Population Comparator

Interactive 3D globe showing every country in the world.
Compares BULK Exchange user count against country populations.
Flask backend + D3.js frontend. Black & white terminal aesthetic.

---

## Quick Start (3 commands)

    unzip bulk-globe.zip -d bulk-globe
    cd bulk-globe
    pip3 install -r requirements.txt
    python3 server.py

Then open **http://localhost:8080**

Or even simpler — just run the startup script:

    ./start.sh

It installs dependencies, starts the server, and opens your browser.

---

## Step-by-Step Guide

### 1. Prerequisites

You need **Python 3.10+**. Check with:

    python3 --version

If not installed:
- **macOS**: `brew install python3`
- **Windows**: download from https://www.python.org/downloads/
- **Linux**: `sudo apt install python3 python3-pip`


### 2. Unzip

    unzip bulk-globe.zip -d bulk-globe
    cd bulk-globe


### 3. Install Dependencies

    pip3 install -r requirements.txt

If `pip3` doesn't work, try:

    python3 -m pip install -r requirements.txt


### 4. Run the Server

    python3 server.py

You'll see:

    ╔══════════════════════════════════════╗
    ║        BULK GLOBE SERVER             ║
    ║   → http://localhost:8080            ║
    ╚══════════════════════════════════════╝


### 5. Open Your Browser

Go to:

    http://localhost:8080


### 6. Interact with the Globe

- **Drag** to rotate the globe
- **Scroll** to zoom in/out
- **Hover** any country to see name + population
- **Click** any country to open a detail panel with:
  - Country name and region
  - Population (UN 2024 data)
  - BULK user count
  - Whether BULK users exceed the population
  - Excess amount and percentage
- **White/bright** countries = BULK users > population
- **Dark** countries = BULK users ≤ population
- Data auto-refreshes every 30 seconds


### 7. Stop the Server

Press **Ctrl+C** in the terminal.

---

## Project Structure

    bulk-globe/
    ├── server.py              ← Flask backend (main file)
    ├── start.sh               ← One-click startup script
    ├── requirements.txt       ← Python dependencies
    ├── README.md              ← This file
    ├── static/
    │   └── index.html         ← Frontend (D3.js globe)
    └── data/
        ├── countries-50m.json ← World map (medium detail, 241 countries)
        └── countries-10m.json ← World map (high detail, 255 countries)


## Backend API Endpoints

| Endpoint             | Method | Description                              |
|----------------------|--------|------------------------------------------|
| `/`                  | GET    | Serves the globe frontend                |
| `/api/topology`      | GET    | World TopoJSON data (?res=50m or 10m)    |
| `/api/countries`     | GET    | All 242 countries with population data   |
| `/api/country/:iso`  | GET    | Single country detail + BULK comparison  |
| `/api/bulk`          | GET    | Current BULK exchange stats              |
| `/api/comparison`    | GET    | Full comparison table                    |

Example:

    curl http://localhost:8080/api/country/840


## BULK Exchange API

The server polls the real BULK Exchange API every 30 seconds:

    GET https://exchange-api.bulk.trade/api/v1/stats

Docs: https://docs.bulk.trade/api-reference/introduction

The BULK API returns volume and open interest but does not currently
expose a "total users" endpoint. User count is simulated (~12.8M)
until such an endpoint is available.


## Troubleshooting

| Problem | Solution |
|---------|----------|
| `pip: command not found` | Use `pip3` or `python3 -m pip` |
| `python3: command not found` | Install Python: `brew install python3` |
| Port 8080 in use | Change `PORT = 8080` in server.py to another number |
| Globe shows no countries | Check that `data/countries-50m.json` exists (~739KB) |
| Browser shows blank page | Check terminal for errors, make sure server is running |
