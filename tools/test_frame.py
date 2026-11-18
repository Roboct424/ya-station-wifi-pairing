#!/usr/bin/env python3
"""Самопроверка кодера: известные векторы + обратный разбор.

    python test_frame.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sound_protocol as sp  # noqa: E402

# Кадр, который реально принимался колонкой (SSID=YaRig, pass=11111111)
KNOWN_FRAME = bytes.fromhex(
    "02055961526967083131313131313131106c6f63616c7061697230303030303030a86a"
)

failures = []


def check(name: str, got, want):
    ok = got == want
    print(f"{'OK  ' if ok else 'FAIL'} {name}: {got!r}"
          + ("" if ok else f" != {want!r}"))
    if not ok:
        failures.append(name)


def main() -> int:
    frame = sp.build_frame(2, "YaRig", "11111111", "localpair0000000")
    check("кадр", frame.hex(), KNOWN_FRAME.hex())

    tones = sp.build_tones(frame)
    check("тонов", len(tones), 4 + 2 + 98 + 8)
    check("преамбула", tones[:4], sp.PREAMBLE)
    check("версия", tones[4:6], [1024, 1024])
    check("хвост", tones[-8:], sp.END)

    back = sp.decode_for_test(tones)
    check("обратный разбор", back.hex(), KNOWN_FRAME.hex())

    hidden = sp.build_frame(4, "YaRig", "11111111", "localpair0000000")
    code = int.from_bytes(hidden[1:3], "little", signed=True)
    check("скрытая: hashCode", code, sp.java_string_hash("YaRig") % 32767)

    opened = sp.build_frame(5, "YaRig", "11111111", "localpair0000000")
    check("открытая: без SSID", opened[0], 5)
    check("открытая: длина", len(opened), 1 + 1 + 16 + 2)

    info = sp.describe(frame)
    check("длительность", info["duration_sec"], 4.48)

    # WAV
    path = sp.make_wav(frame, "test_output.wav", gain=0.5)
    check("WAV существует", path.exists(), True)
    path.unlink()

    # паритет с JS-версией, если установлен dukpy
    try:
        import dukpy
        html = (Path(__file__).parent / "sound_code.html").read_text(encoding="utf-8")
        import re
        script = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
        logic = script.split("/* ---------- звук ---------- */")[0]
        shim = """
        function TextEncoder() {}
        TextEncoder.prototype.encode = function (s) {
          var out = [];
          for (var i = 0; i < s.length; i++) {
            var c = s.charCodeAt(i);
            if (c < 0x80) out.push(c);
            else if (c < 0x800) out.push(0xC0 | (c >> 6), 0x80 | (c & 0x3F));
            else out.push(0xE0 | (c >> 12), 0x80 | ((c >> 6) & 0x3F), 0x80 | (c & 0x3F));
          }
          return out;
        };
        """
        js = """
        var r = buildSequence(2, "YaRig", "11111111", "localpair0000000");
        Array.from(r.frame).map(b => b.toString(16).padStart(2,'0')).join('');
        """
        got = dukpy.evaljs(shim + logic + "\n" + js)
        check("JS = Python", got, KNOWN_FRAME.hex())
    except ImportError:
        print("SKIP JS-паритет: нет dukpy (pip install dukpy)")

    print()
    if failures:
        print("ПРОВАЛЕНО:", ", ".join(failures))
        return 1
    print("все проверки пройдены")
    return 0


if __name__ == "__main__":
    sys.exit(main())
