#!/usr/bin/env python3
"""Скачивает всё нужное для сборки APK без Android SDK (≈33 МБ).

    python fetch_tools.py

Кладёт в android/.tools/:
    android.jar   — android.jar API 16 (Maven Central)
    r8.jar        — D8 1.6.84 (последняя версия, работающая на Java 8)
    aapt2.jar     — aapt2 (Windows), внутри aapt2.exe
    apksig.jar    — библиотека подписи APK
    ecj.jar       — компилятор Java (работает на JRE 8, javac не нужен)
"""
from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / ".tools"

FILES = {
    "android.jar": "https://repo1.maven.org/maven2/com/google/android/android/4.1.1.4/android-4.1.1.4.jar",
    "r8.jar": "https://maven.aliyun.com/repository/google/com/android/tools/r8/1.6.84/r8-1.6.84.jar",
    "aapt2.jar": "https://maven.aliyun.com/repository/google/com/android/tools/build/aapt2/8.1.0-10154469/aapt2-8.1.0-10154469-windows.jar",
    "apksig.jar": "https://maven.aliyun.com/repository/google/com/android/tools/build/apksig/8.1.0/apksig-8.1.0.jar",
    "ecj.jar": "https://repo1.maven.org/maven2/org/eclipse/jdt/ecj/3.26.0/ecj-3.26.0.jar",
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        dest = OUT / name
        if dest.exists() and dest.stat().st_size > 100_000:
            print(f"{name}: уже есть")
            continue
        print(f"{name}: качаю…", flush=True)
        try:
            with urllib.request.urlopen(url, timeout=180) as r, open(dest, "wb") as f:
                f.write(r.read())
        except Exception as exc:
            print(f"{name}: ОШИБКА {type(exc).__name__}: {exc}")
            return 1
        print(f"{name}: {dest.stat().st_size / 1e6:.1f} МБ")

    # aapt2.exe лежит внутри aapt2.jar
    exe = OUT / "aapt2.exe"
    if not exe.exists():
        import zipfile
        with zipfile.ZipFile(OUT / "aapt2.jar") as z:
            with z.open("aapt2.exe") as src, open(exe, "wb") as dst:
                dst.write(src.read())
        print(f"aapt2.exe: распакован ({exe.stat().st_size / 1e6:.1f} МБ)")

    print("\nготово. Теперь: powershell -File build_apk.ps1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
