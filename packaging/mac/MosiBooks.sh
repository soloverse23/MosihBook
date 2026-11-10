#!/bin/bash
# Starts the MosiBooks server in the background (if it is not already running) and opens it in the browser.
APP="$HOME/Library/Application Support/MosiBooks"
URL="http://127.0.0.1:8765"
up() { curl -s -o /dev/null --max-time 1 "$URL/api/auth/status"; }
if ! up; then
  [ -f "$APP/credentials.sh" ] && . "$APP/credentials.sh"
  export MOSIBOOKS_APP_DIR="$APP" PYTHONUTF8=1
  mkdir -p "$HOME/MosiBooks" && cd "$HOME/MosiBooks" || exit 1
  nohup "$APP/venv/bin/python" -m bookforge.cli serve --no-open > "$APP/server.log" 2>&1 &
  for _ in $(seq 90); do up && break; sleep 1; done
  if ! up; then
    osascript -e "display alert \"MosiBooks did not start\" message \"Details are in: $APP/server.log\""
    exit 1
  fi
fi
open "$URL"
