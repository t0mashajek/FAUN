#!/bin/bash
# Builds FAUN.app from FAUN.py (double-click, or run in Terminal).
set -e
cd "$(dirname "$0")"

# Usage:  bash build_mac.command                          -> dist/FAUN-mac-legacy.zip, built with the python.org Python (runs on older Macs too)
#         bash build_mac.command /opt/homebrew/bin/python3  -> dist/FAUN-mac.zip, built with another Python (e.g. the Homebrew one);
#                                                              that app only runs on the macOS version that Python was built for or newer
# Use the Python from python.org if it is installed: it runs on older Macs too.
# (The Homebrew Python is built for the newest macOS only, and the app would not start on older Macs.)
PY="$1"
LABEL="${2:-}"
[ -z "$PY" ] && LABEL="${2:-legacy}"
for v in 3.13 3.12 3.14 3.11 3.10; do
  if [ -z "$PY" ] && [ -x "/Library/Frameworks/Python.framework/Versions/$v/bin/python3" ]; then
    PY="/Library/Frameworks/Python.framework/Versions/$v/bin/python3"
    break
  fi
done
if [ -z "$PY" ]; then
  LABEL="${2:-}"
  PY="$(command -v python3 || true)"
  echo "WARNING: the Python from python.org was not found, using: $PY"
  echo "         An app built with the Homebrew Python may not start on Macs with an older macOS."
  echo "         Recommended: install Python 3.12 or 3.13 from https://www.python.org/downloads/macos/ and run this again."
  echo
fi
if [ -z "$PY" ] || ! "$PY" -c "import tkinter" 2>/dev/null; then
  echo "This Python has no tkinter. Install Python from python.org (it includes tkinter) and try again."
  exit 1
fi
echo "Python: $PY"

rm -rf .buildenv build dist FAUN.spec
"$PY" -m venv .buildenv
source .buildenv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet pyinstaller tkinterdnd2

ICON=""
if [ -f FAUN.icns ]; then ICON="--icon FAUN.icns"; fi

python -m PyInstaller --noconfirm --clean --windowed --name FAUN \
  --osx-bundle-identifier com.tomashajek.faun \
  --collect-all tkinterdnd2 $ICON FAUN.py

APP="dist/FAUN.app"
plutil -replace CFBundleShortVersionString -string "1.1" "$APP/Contents/Info.plist"
plutil -replace CFBundleVersion -string "1.1" "$APP/Contents/Info.plist"
plutil -replace NSHumanReadableCopyright -string "Created by Tomas Hajek" "$APP/Contents/Info.plist"
codesign --force --deep --sign - "$APP"      # ad-hoc signature (no Apple developer account needed)
ZIP="dist/FAUN-mac${LABEL:+-$LABEL}.zip"
ditto -c -k --keepParent "$APP" "$ZIP"

echo
echo "Done:  $(pwd)/$APP"
echo "Zip:   $(pwd)/$ZIP"
echo "Oldest macOS this app needs (a low number such as 10.13 or 11.0 is good, 26 or 27 is not):"
PYLIB="$(find "$APP/Contents/Frameworks" -name Python -type f -path "*Python.framework*" 2>/dev/null | head -1)"
[ -z "$PYLIB" ] && PYLIB="$(find "$APP/Contents" -name "libpython*.dylib" 2>/dev/null | head -1)"
[ -n "$PYLIB" ] && otool -l "$PYLIB" | grep -E "minos|version [0-9]" | head -2 || true
echo "On another Mac: System Settings -> Privacy & Security -> Open Anyway the first time (it is not notarized)."
