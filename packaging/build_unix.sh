#!/usr/bin/env bash
# Сборка однофайловых бинарников для Linux/macOS.
#
#   bash packaging/build_unix.sh
#
# Нужен Python 3.8+, pip. Звук играет системный плеер
# (paplay / aplay / ffplay / afplay), sounddevice и libportaudio2
# не требуются.
#
# Результат: dist/StationPairing (CLI), dist/StationPairingGUI
# (на macOS — .app).
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m pip install --upgrade pyinstaller cryptography numpy

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
