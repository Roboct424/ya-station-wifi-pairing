#!/usr/bin/env python3
"""Сборка .deb-пакета (architecture: all) без dpkg-deb.

    python packaging/build_deb.py

Кладёт результат в dist/ya-station-wifi-pairing_<version>_all.deb
"""
from __future__ import annotations

import gzip
import hashlib
import io
import os
import tarfile
import time
from pathlib import Path

VERSION = "1.3.0"
PKG = "ya-station-wifi-pairing"
ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SHARE = f"usr/share/{PKG}"

FILES = [
    "sound_protocol.py",
    "pair_by_sound.py",
    "provision.py",
    "provision_gui.py",
    "test_frame.py",
    "sound_code.html",
    "ap_wifi.py",
    "audio_play.py",
    "station_pairing.py",
    "station_pairing_gui.py",
    "test_ap_wifi.py",
]

WRAPPERS = {
    "ya-station-pair": "pair_by_sound.py",
    "ya-station-provision": "provision.py",
    "ya-station-gui": "provision_gui.py",
    "ya-station-pairing": "station_pairing.py",
    "ya-station-pairing-gui": "station_pairing_gui.py",
}

DESKTOP = """[Desktop Entry]
Type=Application
Name=Station Wi-Fi Pairing
Name[ru]=Сопряжение Станции с Wi-Fi
Comment=Send Wi-Fi credentials to a Yandex Station over sound
Comment[ru]=Передать Wi-Fi колонке Яндекс Станция звуком
Exec=ya-station-pairing-gui
Terminal=false
Categories=Utility;Network;
"""

CONTROL = f"""Package: {PKG}
Version: {VERSION}
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.8), python3-numpy, python3-cryptography, python3-tk
Recommends: pulseaudio-utils | alsa-utils
Maintainer: Roboct424 <konstantinponomarev0808090683@gmail.com>
Homepage: https://github.com/Roboct424/ya-station-wifi-pairing
Description: Wi-Fi pairing for Yandex Station: sound + AP HTTP
 Send SSID and password to a Yandex Station acoustically or over the
 device's local AP (RSA/PKCS1): no app, no cloud, no root.
 Includes CLI, auto-provisioning, GUI and an Ethernet mode.
"""


def add_file(tar: tarfile.TarFile, name: str, data: bytes, mode: int = 0o644):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    info.mtime = int(time.time())
    info.uid = info.gid = 0
    info.uname = info.gname = "root"
    tar.addfile(info, io.BytesIO(data))


def tar_gz(files: dict[str, tuple[bytes, int]]) -> bytes:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tar:
        for name, (data, mode) in files.items():
            add_file(tar, name, data, mode)
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as gz:
        gz.write(raw.getvalue())
    return out.getvalue()


def ar_archive(members: list[tuple[str, bytes]]) -> bytes:
    out = io.BytesIO()
    out.write(b"!<arch>\n")
    for name, data in members:
        header = (
            f"{name:<16}"
            f"{int(time.time()):<12}"
            f"{0:<6}{0:<6}"
            f"{'100644':<8}"
            f"{len(data):<10}"
            "`\n"
        ).encode("ascii")
        assert len(header) == 60, len(header)
        out.write(header)
        out.write(data)
        if len(data) % 2:
            out.write(b"\n")
    return out.getvalue()


def main() -> int:
    DIST.mkdir(exist_ok=True)
    data: dict[str, tuple[bytes, int]] = {}

    for name in FILES:
        src = ROOT / "tools" / name
        if not src.exists():
            print(f"нет {src}")
            return 1
        data[f"./{SHARE}/{name}"] = (src.read_bytes(), 0o644)

    for cmd, script in WRAPPERS.items():
        body = (
            "#!/bin/sh\n"
            f'exec python3 "/{SHARE}/{script}" "$@"\n'
        ).encode()
        data[f"./usr/bin/{cmd}"] = (body, 0o755)

    data[f"./usr/share/applications/{PKG}.desktop"] = (DESKTOP.encode(), 0o644)

    # md5sums
    md5_lines = []
    for path, (blob, _mode) in sorted(data.items()):
        md5_lines.append(f"{hashlib.md5(blob).hexdigest()}  {path[2:]}")
    md5sums = ("\n".join(md5_lines) + "\n").encode()

    control = {
        "./control": (CONTROL.encode(), 0o644),
        "./md5sums": (md5sums, 0o644),
    }

    deb = ar_archive([
        ("debian-binary", b"2.0\n"),
        ("control.tar.gz", tar_gz(control)),
        ("data.tar.gz", tar_gz(data)),
    ])

    out = DIST / f"{PKG}_{VERSION}_all.deb"
    out.write_bytes(deb)
    print(f"готово: {out} ({out.stat().st_size / 1024:.0f} КБ)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
