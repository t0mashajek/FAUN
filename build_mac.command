#!/bin/bash
# Builds FAUN.app from FAUN.py (double-click, or run in Terminal).
set -e
cd "$(dirname "$0")"

if ! python3 -c "import tkinter" 2>/dev/null; then
  echo "This Python has no tkinter. Install Python from python.org (it includes tkinter) and try again."
  exit 1
fi

python3 -m venv .buildenv
source .buildenv/bin/activate
pip install --quiet --upgrade pip pyinstaller tkinterdnd2

ICON=""
if [ -f FAUN.icns ]; then ICON="--icon FAUN.icns"; fi

pyinstaller --noconfirm --clean --windowed --name FAUN \
  --osx-bundle-identifier com.tomashajek.faun \
  --collect-all tkinterdnd2 $ICON FAUN.py

APP="dist/FAUN.app"
plutil -replace CFBundleShortVersionString -string "1.0" "$APP/Contents/Info.plist"
plutil -replace CFBundleVersion -string "1.0" "$APP/Contents/Info.plist"
plutil -replace NSHumanReadableCopyright -string "Created by Tomas Hajek" "$APP/Contents/Info.plist"
codesign --force --deep --sign - "$APP"      # ad-hoc signature (no Apple developer account needed)
ditto -c -k --keepParent "$APP" dist/FAUN-mac.zip

echo
echo "Done:  $(pwd)/$APP"
echo "Zip:   $(pwd)/dist/FAUN-mac.zip"
echo "On another Mac: right-click the app -> Open the first time (it is not notarized)."
