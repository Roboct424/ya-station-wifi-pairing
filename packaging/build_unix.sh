#!/usr/bin/env bash
# Сборка объединённого инструмента под Linux/macOS.
#
#   bash packaging/build_unix.sh
#
# Требуется Python 3.8+, pip. На macOS для sounddevice:
#   brew install portaudio
#
# Результат: dist/StationPairing (CLI), dist/StationPairingGUI
# (на macOS — .app).
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m pip install --upgrade pyinstaller cryptography numpy sounddevice

python3 -m PyInstaller --noconfirm --onefile \
    --name StationPairing \
    --distpath dist --workpath build --specpath build \
    tools/station_pairing.py

python3 -m PyInstaller --noconfirm --onefile --windowed \
    --name StationPairingGUI \
    --distpath dist --workpath build --specpath build \
    tools/station_pairing_gui.py

echo
echo "готово:"
ls -1 dist/StationPairing* 2>/dev/null || true
