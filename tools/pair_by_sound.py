#!/usr/bin/env python3
"""Генерация и проигрывание звукового кода сопряжения.

Примеры:
    python pair_by_sound.py --ssid YaRig --password 11111111
    python pair_by_sound.py --ssid Home --password secret --repeat 4 --gap 10
    python pair_by_sound.py --ssid Home --password secret --gain 0.35
    python pair_by_sound.py --ssid YaRig --password 11111111 --dry-run
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sound_protocol as sp  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Звуковой код сопряжения Яндекс Станции")
    ap.add_argument("--ssid", required=True, help="имя Wi-Fi сети")
    ap.add_argument("--password", default="", help="пароль (пусто для открытой)")
    ap.add_argument("--token", default=sp.DEFAULT_TOKEN,
                    help="токен активации, колонке он не важен")
    ap.add_argument("--type", type=int, default=sp.WIFI_TYPE_WPA,
                    choices=(2, 4, 5), help="2=WPA, 4=скрытая, 5=открытая")
    ap.add_argument("--gain", type=float, default=sp.DEFAULT_GAIN,
                    help="амплитуда 0.1..0.9 (0.5 — рабочая)")
    ap.add_argument("--preroll", type=int, default=0, choices=(0, 1, 2, 3, 4),
                    help="предстарт 0..4: сколько раз повторить преамбулу")
    ap.add_argument("--repeat", type=int, default=3, help="сколько раз проиграть")
    ap.add_argument("--gap", type=float, default=9.0,
                    help="пауза между повторами, с (колонка глохнет на 5-9 с)")
    ap.add_argument("--out", default="pair_sound.wav", help="куда сохранить WAV")
    ap.add_argument("--device", default=None, help="индекс устройства вывода")
    ap.add_argument("--dry-run", action="store_true", help="только показать кадр")
    a = ap.parse_args(argv)

    frame = sp.build_frame(a.type, a.ssid, a.password, a.token)
    path = sp.make_wav(frame, a.out, gain=a.gain, preroll=a.preroll)
    info = sp.describe(frame, a.gain, preroll=a.preroll)

    print(f"SSID     : {a.ssid!r}  тип={a.type}")
    print(f"кадр     : {frame.hex()}")
    print(f"байт     : {info['frame_bytes']}  ниблов: {info['nibbles']}  "
          f"после RS: {info['encoded_nibbles']}")
    print(f"тонов    : {info['tones']}  длительность: {info['duration_sec']} с")
    print(f"WAV      : {path}  (громкость {a.gain})")

    if a.dry_run:
        return 0

    from audio_play import Player

    player = Player()
    device = None if a.device is None else int(a.device)
    for i in range(a.repeat):
        print(f"проигрывание {i + 1}/{a.repeat}", flush=True)
        try:
            player.play(path, device=device)
        except Exception as exc:  # pragma: no cover
            print(f"не удалось проиграть: {exc}\nWAV сохранён: {path}")
            return 0
        if i + 1 < a.repeat:
            time.sleep(a.gap)
    print(f"готово (плеер: {player.backend})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
