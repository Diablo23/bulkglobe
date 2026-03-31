#!/bin/bash
cd "$(dirname "$0")"

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install: brew install python3"
    read -p "Press Enter to close..."
    exit 1
fi

python3 -c "import flask" 2>/dev/null || {
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
}

echo ""
echo "Starting BULK GLOBE..."
echo "  → http://localhost:8080"
echo ""
echo "  BULK API connections:"
echo "    WS  wss://exchange-ws1.bulk.trade (trades → active traders)"
echo "    HTTP /stats, /ticker, /exchangeInfo"
echo ""

(sleep 2 && open "http://localhost:8080" 2>/dev/null || xdg-open "http://localhost:8080" 2>/dev/null) &

python3 server.py
