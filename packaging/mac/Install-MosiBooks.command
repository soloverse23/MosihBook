#!/bin/bash
# MosiBooks for Mac: double-click for a first install or a repair.
cd "$(dirname "$0")"
SRC="$PWD/payload"
APP="$HOME/Library/Application Support/MosiBooks"
URL="http://127.0.0.1:8765/api/auth/status"
case "$(uname -m)" in arm64) UVSRC="$SRC/uv-arm64" ;; *) UVSRC="$SRC/uv-x86_64" ;; esac
export UV_CACHE_DIR="$APP/cache" UV_PYTHON_INSTALL_DIR="$APP/python" UV_LINK_MODE=copy UV_NO_CONFIG=1

fail() {
  echo
  echo "Setup failed. Check the internet connection and run this file again."
  echo "If it fails again, send a screenshot of this window to the person who gave you MosiBooks."
  read -r -p "Press Enter to close."; exit 1
}

if [ ! -f "$UVSRC" ]; then echo "Please unzip the file first, then run Install-MosiBooks again."; read -r; exit 1; fi
if curl -s -o /dev/null --max-time 2 "$URL"; then
  echo "MosiBooks is running. Quit it first (run the Stop-MosiBooks file in this folder), then run this again."
  read -r -p "Press Enter to close."; exit 1
fi

echo
echo "Installing MosiBooks. The first install downloads about 300 MB"
echo "and can take several minutes. Please keep this window open."
echo

echo "[1/4] Copying files..."
mkdir -p "$APP" || fail
[ -f "$SRC/credentials.sh" ] && cp "$SRC/credentials.sh" "$APP/credentials.sh" && chmod 600 "$APP/credentials.sh"
rm -rf "$APP/payload" && mkdir -p "$APP/payload" || fail
cp -R "$SRC/app" "$SRC/requirements.lock" "$SRC/MosiBooks.sh" "$SRC/Claude-Login.command" "$APP/payload/" || fail
cp "$UVSRC" "$APP/payload/uv" && chmod +x "$APP/payload/uv" "$APP/payload/MosiBooks.sh" "$APP/payload/Claude-Login.command" || fail
xattr -dr com.apple.quarantine "$APP/payload" 2>/dev/null
UV="$APP/payload/uv"; PY="$APP/venv/bin/python"

echo "[2/4] Installing Python..."
"$UV" venv --clear --managed-python --python 3.12 "$APP/venv" || fail

echo "[3/4] Installing MosiBooks and Claude..."
"$UV" pip install --python "$PY" -r "$APP/payload/requirements.lock" || fail
"$UV" pip install --python "$PY" --no-deps --reinstall-package bookforge "$APP/payload/app" || fail

echo "[4/4] Creating the MosiBooks app in Applications and on the Desktop..."
BUNDLE="$HOME/Applications/MosiBooks.app"
rm -rf "$BUNDLE"; mkdir -p "$BUNDLE/Contents/MacOS" || fail
cat > "$BUNDLE/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>MosiBooks</string>
<key>CFBundleIdentifier</key><string>local.mosibooks</string>
<key>CFBundleExecutable</key><string>MosiBooks</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>LSUIElement</key><true/>
</dict></plist>
PLIST
printf '#!/bin/bash\nexec "%s/payload/MosiBooks.sh"\n' "$APP" > "$BUNDLE/Contents/MacOS/MosiBooks"
chmod +x "$BUNDLE/Contents/MacOS/MosiBooks"
rm -f "$HOME/Desktop/MosiBooks"; ln -s "$BUNDLE" "$HOME/Desktop/MosiBooks"

echo
echo "Done. Opening MosiBooks..."
"$APP/payload/MosiBooks.sh"
sleep 2
osascript -e 'tell application "Terminal" to close (every window whose name contains "Install-MosiBooks")' >/dev/null 2>&1 &
exit 0
