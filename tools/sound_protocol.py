#!/usr/bin/env python3
"""Звуковой протокол сопряжения Яндекс Станции.

Полное описание формата — в docs/01-sound-protocol.md.

Кратко:
    кадр  : [тип][len+SSID][len+пароль][len+токен][crc32 & 0xFFFF LE]
    нибблы: старший полубайт первым
    RS    : (15, 11) над GF(16), полином 0x13, база 1, 4 ECC-ниббла
    тоны  : 1024 + ниббл*256 Гц, по 40 мс, 16 кГц
    старт : 6192, 6192, 5120, 5120
    версия: [1024 + version*256, 1024 + checksum*256]
    конец : 5632 x 8
"""
from __future__ import annotations

import struct
import wave
import zlib
from pathlib import Path

SR = 16000
SYMBOL_SEC = 0.04
SYMBOL_SAMPLES = int(SR * SYMBOL_SEC)  # 640

BASE = 1024
STEP = 256

PREAMBLE = [6192, 6192, 5120, 5120]
END = [5632] * 8

WIFI_TYPE_WPA = 2
WIFI_TYPE_HIDDEN = 4
WIFI_TYPE_OPEN = 5

DEFAULT_TOKEN = "localpair0000000"
DEFAULT_GAIN = 0.5


# ---------------------------------------------------------------- кадр -----
def _lp(text: str) -> bytes:
    """Строка с однобайтовой длиной (UTF-8; как в оригинальном протоколе)."""
    raw = text.encode("utf-8")
    if len(raw) > 255:
        raise ValueError(f"поле длиннее 255 байт: {text!r}")
    return bytes([len(raw)]) + raw


def java_string_hash(text: str) -> int:
    """java.lang.String.hashCode() — используется для скрытых сетей."""
    units = text.encode("utf-16-le")
    h = 0
    for i in range(0, len(units), 2):
        cu = units[i] | (units[i + 1] << 8)
        h = (31 * h + cu) & 0xFFFFFFFF
    if h >= 2 ** 31:
        h -= 2 ** 32
    return h


def build_frame(wifi_type: int, ssid: str, password: str,
                token: str = DEFAULT_TOKEN) -> bytes:
    """Собирает кадр учетных данных."""
    if wifi_type not in (WIFI_TYPE_WPA, WIFI_TYPE_HIDDEN, WIFI_TYPE_OPEN):
        raise ValueError("тип сети: 2 (WPA), 4 (скрытая), 5 (открытая)")

    buf = bytearray([wifi_type])
    if wifi_type == WIFI_TYPE_WPA:
        buf += _lp(ssid)
        buf += _lp(password)
    elif wifi_type == WIFI_TYPE_HIDDEN:
        # вместо SSID передаётся его hashCode, урезанный до 15 бит
        code = java_string_hash(ssid) % 32767
        buf += struct.pack("<h", code)
        buf += _lp(password)
    # type 5 — без SSID и пароля

    buf += _lp(token)
    buf += struct.pack("<H", zlib.crc32(bytes(buf)) & 0xFFFF)
    return bytes(buf)


# ------------------------------------------------------- Reed-Solomon -----
def _build_gf(prim: int = 0x13, size: int = 16):
    exp = [0] * (size * 2)
    log = [0] * size
    x = 1
    for i in range(size - 1):
        exp[i] = x
        log[x] = i
        x <<= 1
        if x & size:
            x ^= prim
    for i in range(size - 1, size * 2):
        exp[i] = exp[i - (size - 1)]
    return exp, log


_EXP, _LOG = _build_gf()


def _gmul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[(_LOG[a] + _LOG[b]) % 15]


def _poly_mul(p, q):
    r = [0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            r[i + j] ^= _gmul(a, b)
    return r


def _build_generator(degree: int = 4, base: int = 1):
    g = [1]
    for i in range(degree):
        g = _poly_mul(g, [1, _EXP[(i + base) % 15]])
    return g


_GEN = _build_generator(4, 1)


def _rs_ecc(data) -> list[int]:
    msg = list(data) + [0] * 4
    for i in range(len(data)):
        coef = msg[i]
        if coef == 0:
            continue
        for j in range(1, len(_GEN)):
            msg[i + j] ^= _gmul(_GEN[j], coef)
    return msg[len(data):]


def rs_encode(nibbles) -> list[int]:
    """Блоки по 11 данных + 4 ECC. Последний блок может быть короче."""
    out: list[int] = []
    for i in range(0, len(nibbles), 11):
        chunk = list(nibbles[i:i + 11])
        out += chunk + _rs_ecc(chunk)
    return out


def to_nibbles(data: bytes) -> list[int]:
    out = []
    for b in data:
        out.append((b >> 4) & 0xF)
        out.append(b & 0xF)
    return out


# ------------------------------------------------------------ тоны --------
def build_tones(frame: bytes, version: int = 0, checksum: int = 0,
                preroll: int = 0) -> list[int]:
    """Полная последовательность частот (по 40 мс на символ).

    ``preroll`` (0..4) — сколько раз повторить преамбулу перед кадром,
    чтобы «разбудить» декодер колонки. 0 — как раньше.
    """
    encoded = rs_encode(to_nibbles(frame))
    preroll = max(0, min(4, int(preroll)))
    tones: list[int] = []
    for _ in range(preroll):
        tones += PREAMBLE
    tones += PREAMBLE
    tones += [BASE + version * STEP, BASE + checksum * STEP]
    tones += [BASE + n * STEP for n in encoded]
    tones += END
    return tones


def tone_to_nibble(freq: int) -> int:
    return (freq - BASE) // STEP


# ------------------------------------------------------------- WAV --------
def make_wav(frame: bytes, out: str | Path, gain: float = DEFAULT_GAIN,
             version: int = 0, checksum: int = 0,
             preroll: int = 0) -> Path:
    """Пишет WAV 16 кГц / 16 бит / моно."""
    import numpy as np

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tones = build_tones(frame, version, checksum, preroll)

    samples = []
    t = np.arange(SYMBOL_SAMPLES)
    for freq in tones:
        samples.append(np.sin(2 * np.pi * freq * t / SR) * 32767.0 * gain)
    audio = np.concatenate(samples).astype("<i2")

    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(audio.tobytes())
    return out


def read_wav(path: str | Path):
    """Возвращает (samples float32, sample_rate)."""
    import numpy as np

    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    return data.astype(np.float32) / 32768.0, sr


# --------------------------------------------------------- удобства -------
def describe(frame: bytes, gain: float = DEFAULT_GAIN,
             preroll: int = 0) -> dict:
    tones = build_tones(frame, preroll=preroll)
    return {
        "frame_hex": frame.hex(),
        "frame_bytes": len(frame),
        "nibbles": len(to_nibbles(frame)),
        "encoded_nibbles": len(rs_encode(to_nibbles(frame))),
        "tones": len(tones),
        "duration_sec": round(len(tones) * SYMBOL_SEC, 3),
        "gain": gain,
    }


def decode_for_test(tones: list[int]) -> bytes:
    """Обратный разбор последовательности (только для тестов)."""
    body = [(f - BASE) // STEP if f >= BASE else 0 for f in tones[4 + 2:-8]]
    data_nibbles: list[int] = []
    full = (len(body) // 15) * 15
    for i in range(0, full, 15):
        data_nibbles += body[i:i + 11]
    rest = len(body) - full
    if rest > 4:
        # в неполном блоке последние 4 ниббла — ECC
        data_nibbles += body[full:full + min(11, rest - 4)]
    return bytes((data_nibbles[i] << 4) | data_nibbles[i + 1]
                 for i in range(0, len(data_nibbles) - 1, 2))
