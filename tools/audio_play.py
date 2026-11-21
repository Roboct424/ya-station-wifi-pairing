#!/usr/bin/env python3
"""Проигрывание WAV без обязательных зависимостей.

Зачем: ``sounddevice`` тянет libportaudio, которой нет в минимальном
Linux (и её нельзя собрать в PyInstaller без portaudio19-dev). Поэтому
сначала пробуем системный плеер, а sounddevice оставляем как запасной
вариант и для выбора конкретного устройства.

    Windows : winsound (stdlib, без зависимостей)
    Linux   : paplay → aplay → ffplay (первый найденный)
    macOS   : afplay

Использование::

    from audio_play import Player
    p = Player()
    p.play("pair_sound.wav")        # блокирующе
    p.play("pair_sound.wav", block=False)
    p.stop()
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

__all__ = ["Player", "native_player", "sounddevice_available"]


def sounddevice_available() -> bool:
    try:
        import sounddevice  # noqa: F401
        return True
    except Exception:
        return False


def native_player() -> str | None:
    """Имя системного плеера, которым можно проиграть WAV, или None."""
    system = platform.system()
    if system == "Windows":
        return "winsound"
    if system == "Darwin":
        return "afplay" if shutil.which("afplay") else None
    for name in ("paplay", "aplay", "ffplay", "play"):
        if shutil.which(name):
            return name
    return None


def _native_cmd(name: str, path: Path) -> list[str]:
    if name == "aplay":
        return ["aplay", "-q", str(path)]
    if name == "ffplay":
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)]
    return [name, str(path)]


class Player:
    """Единая точка проигрывания: системный плеер, иначе sounddevice."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._sd = None
        self.backend: str | None = None

    # ---------------------------------------------------------------- play
    def play(self, path: str | Path, device: int | None = None,
             block: bool = True) -> str:
        """Проигрывает WAV. Возвращает имя бэкенда.

        ``device`` — индекс устройства вывода (только sounddevice).
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(path)

        name = None if device is not None else native_player()
        if name:
            try:
                if name == "winsound":
                    import winsound
                    flags = winsound.SND_FILENAME
                    if not block:
                        flags |= winsound.SND_ASYNC
                    winsound.PlaySound(str(path), flags)
                    self.backend = "winsound"
                    return self.backend
                cmd = _native_cmd(name, path)
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if block:
                    self._proc.wait()
                    self._proc = None
                self.backend = name
                return self.backend
            except Exception:
                self._proc = None

        try:
            self._play_sounddevice(path, device, block)
        except Exception as exc:
            if device is not None:
                raise
            raise RuntimeError(
                f"нет аудиоплеера ({exc}): установите pulseaudio-utils (paplay) "
                f"или alsa-utils (aplay), либо pip install sounddevice"
            ) from exc
        return self.backend or "sounddevice"

    def _play_sounddevice(self, path: Path, device: int | None,
                          block: bool) -> None:
        import sounddevice as sd

        import sound_protocol as sp

        self._sd = sd
        if device is not None:
            sd.default.device = (None, int(device))
        audio, sr = sp.read_wav(path)
        sd.play(audio, sr, blocking=block)
        self.backend = "sounddevice"

    # ---------------------------------------------------------------- stop
    def stop(self) -> None:
        if self._proc is not None:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None
        if platform.system() == "Windows":
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        if self._sd is not None:
            try:
                self._sd.stop()
            except Exception:
                pass

    @property
    def playing(self) -> bool:
        return self._proc is not None and self._proc.poll() is None


if __name__ == "__main__":  # ручная проверка
    import sys
    if len(sys.argv) < 2:
        print("usage: python audio_play.py file.wav")
        print("native:", native_player(), "sounddevice:", sounddevice_available())
        raise SystemExit(2)
    print("playing with", Player().play(sys.argv[1]))
