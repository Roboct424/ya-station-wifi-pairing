#!/usr/bin/env python3
"""Графический генератор звукового кода сопряжения (Tkinter).

    python provision_gui.py
"""
from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sound_protocol as sp  # noqa: E402
from audio_play import Player  # noqa: E402

APP_DIR = Path(__file__).resolve().parent


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Звуковой код сопряжения — Яндекс Станция")
        self.geometry("560x640")
        self.resizable(False, False)

        self.frame = b""
        self.sr = sp.SR
        self.wav_path = APP_DIR / "pair_sound.wav"
        self.playing = False
        self.stop_flag = False
        self.player = Player()

        self._build()
        self._refresh(False)

    # ------------------------------------------------------------------ UI
    def _build(self):
        pad = {"padx": 10, "pady": 6}

        box = ttk.LabelFrame(self, text="Параметры Wi-Fi")
        box.pack(fill="x", **pad)

        ttk.Label(box, text="SSID").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.ssid = ttk.Entry(box, width=34)
        self.ssid.insert(0, "YaRig")
        self.ssid.grid(row=0, column=1, columnspan=3, sticky="we", pady=4)

        ttk.Label(box, text="Пароль").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.pwd = ttk.Entry(box, width=34, show="*")
        self.pwd.insert(0, "11111111")
        self.pwd.grid(row=1, column=1, columnspan=3, sticky="we", pady=4)
        self.show_pwd = tk.BooleanVar(value=False)
        ttk.Checkbutton(box, text="показать", variable=self.show_pwd,
                        command=self._toggle_pwd).grid(row=1, column=4, sticky="w")

        ttk.Label(box, text="Тип сети").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        self.wtype = ttk.Combobox(box, width=26, state="readonly",
                                  values=["2 — WPA/WPA2 (обычная)",
                                          "4 — скрытая сеть",
                                          "5 — открытая"])
        self.wtype.current(0)
        self.wtype.grid(row=2, column=1, columnspan=3, sticky="we", pady=4)

        ttk.Label(box, text="Токен").grid(row=3, column=0, sticky="w", padx=8, pady=4)
        self.token = ttk.Entry(box, width=34)
        self.token.insert(0, sp.DEFAULT_TOKEN)
        self.token.grid(row=3, column=1, columnspan=3, sticky="we", pady=4)

        ttk.Label(box, text="Громкость").grid(row=4, column=0, sticky="w", padx=8, pady=4)
        self.gain = tk.DoubleVar(value=sp.DEFAULT_GAIN)
        ttk.Scale(box, from_=0.1, to=0.95, variable=self.gain,
                  command=lambda _=None: self._refresh(False)).grid(
            row=4, column=1, columnspan=2, sticky="we", pady=4)
        self.gain_lbl = ttk.Label(box, text="0.50")
        self.gain_lbl.grid(row=4, column=3, sticky="w")

        ttk.Label(box, text="Предстарт (0–4)").grid(row=5, column=0, sticky="w", padx=8, pady=4)
        self.preroll = tk.IntVar(value=0)
        ttk.Spinbox(box, from_=0, to=4, textvariable=self.preroll, width=6).grid(
            row=5, column=1, sticky="w", pady=4)
        ttk.Label(box, text="повтор преамбулы для «пробуждения» декодера").grid(
            row=5, column=2, columnspan=2, sticky="w")

        info = ttk.LabelFrame(self, text="Кадр")
        info.pack(fill="x", **pad)
        self.frame_txt = tk.Text(info, height=3, wrap="char", font=("Consolas", 9))
        self.frame_txt.pack(fill="x", padx=8, pady=6)
        self.info_lbl = ttk.Label(info, text="")
        self.info_lbl.pack(anchor="w", padx=8, pady=(0, 6))

        act = ttk.Frame(self)
        act.pack(fill="x", **pad)
        for text, cmd in (("Сгенерировать", lambda: self._refresh(True)),
                          ("▶ Играть", self.play_once),
                          ("⟳ Цикл до подключения", self.play_loop),
                          ("■ Стоп", self.stop),
                          ("Сохранить WAV", self.save_wav)):
            ttk.Button(act, text=text, command=cmd).pack(side="left", padx=4)

        st = ttk.LabelFrame(self, text="Журнал")
        st.pack(fill="both", expand=True, **pad)
        self.log_txt = tk.Text(st, height=10, wrap="word", font=("Consolas", 9))
        self.log_txt.pack(fill="both", expand=True, padx=8, pady=6)

    # ------------------------------------------------------------- helpers
    def _toggle_pwd(self):
        self.pwd.config(show="" if self.show_pwd.get() else "*")

    def _log(self, msg: str):
        self.log_txt.insert("end", f"{time.strftime('%H:%M:%S')}  {msg}\n")
        self.log_txt.see("end")

    def _params(self):
        wtype = int(self.wtype.get().split("—")[0].strip())
        return self.ssid.get().strip(), self.pwd.get(), self.token.get().strip(), wtype

    def _refresh(self, log: bool):
        ssid, pwd, token, wtype = self._params()
        if not ssid:
            messagebox.showwarning("Нет SSID", "Введите имя сети")
            return
        gain = float(self.gain.get())
        self.gain_lbl.config(text=f"{gain:.2f}")
        preroll = max(0, min(4, int(self.preroll.get())))
        try:
            frame = sp.build_frame(wtype, ssid, pwd, token)
            path = sp.make_wav(frame, self.wav_path, gain=gain, preroll=preroll)
        except Exception as exc:
            messagebox.showerror("Ошибка", f"Не удалось собрать кадр: {exc}")
            return

        self.frame = frame
        self.wav_path = path
        info = sp.describe(frame, gain, preroll=preroll)
        self.frame_txt.delete("1.0", "end")
        self.frame_txt.insert("1.0", frame.hex())
        self.info_lbl.config(
            text=f"{info['frame_bytes']} байт · {info['tones']} тонов · "
                 f"{info['duration_sec']} с · тип {wtype}")
        if log:
            self._log(f"кадр: {frame.hex()}")

    # ------------------------------------------------------------ playback
    def play_once(self):
        if self.playing:
            return
        self._refresh(False)
        if not self.frame:
            return
        self.playing = True
        self._log(f"играю (громкость {float(self.gain.get()):.2f})")

        def run():
            try:
                self.player.play(self.wav_path)
                self._log(f"проиграно (плеер: {self.player.backend})")
            except Exception as exc:
                self._log(f"ошибка звука: {exc}")
            finally:
                self.playing = False

        threading.Thread(target=run, daemon=True).start()

    def play_loop(self):
        if self.playing:
            return
        self.stop_flag = False
        self.playing = True
        gains = [float(self.gain.get()), 0.35, 0.65, 0.8]

        def run():
            before = self._arp()
            attempt = 0
            preroll = max(0, min(4, int(self.preroll.get())))
            while not self.stop_flag:
                gain = gains[attempt % len(gains)]
                attempt += 1
                ssid, pwd, token, wtype = self._params()
                try:
                    frame = sp.build_frame(wtype, ssid, pwd, token)
                    path = sp.make_wav(frame, self.wav_path, gain=gain,
                                       preroll=preroll)
                except Exception as exc:
                    self._log(f"ошибка сборки: {exc}")
                    break
                self._log(f"[{attempt}] играю gain={gain}")
                try:
                    self.player.play(path)
                except Exception as exc:
                    self._log(f"ошибка звука: {exc}")
                    break
                for _ in range(10):
                    if self.stop_flag:
                        break
                    time.sleep(1)
                    new = self._arp() - before
                    if new:
                        ip, mac = sorted(new)[0]
                        self._log(f"ГОТОВО: колонка в сети {ip} ({mac}) — попытка {attempt}")
                        self.playing = False
                        return
                self._log("   пока не видно")
            self.playing = False
            self._log("остановлено")

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        self.stop_flag = True
        self.player.stop()

    def _arp(self) -> set[tuple[str, str]]:
        try:
            out = subprocess.run(["arp", "-a"], capture_output=True, text=True,
                                 errors="replace", timeout=8).stdout
        except Exception:
            return set()
        result = set()
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].count(".") == 3:
                mac = parts[1].lower()
                if "-" in mac or ":" in mac:
                    result.add((parts[0], mac))
        return result

    def save_wav(self):
        self._refresh(False)
        path = filedialog.asksaveasfilename(defaultextension=".wav",
                                            filetypes=[("WAV", "*.wav")])
        if path:
            Path(path).write_bytes(self.wav_path.read_bytes())
            self._log(f"сохранено: {path}")


if __name__ == "__main__":
    App().mainloop()
