#!/usr/bin/env sh
# Serve the game locally and open it (macOS/Linux).
cd "$(dirname "$0")"
URL=http://localhost:8080
( sleep 1; (command -v xdg-open >/dev/null && xdg-open $URL) || (command -v open >/dev/null && open $URL) ) &
python3 -m http.server 8080
