#!/usr/bin/env python3
"""Единое окно: звук + Wi-Fi через AP HTTP (Tkinter).

    python station_pairing_gui.py

Вкладка «Звук» — генерирует и проигрывает WAV с SSID/паролем.
Вкладка «Wi-Fi (AP)» — отправляет те же креды по HTTP на 192.168.43.1:8080.
"""
from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from pathlib import Path

import ap_wifi
import sound_protocol as sp

APP_TITLE = "Яндекс Станция — сопряжение"
APP_DIR = Path(__file__).resolve().parent
WAV_PATH = APP_DIR / "pair_sound.wav"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("640x680")
        self.minsize(580, 560)
        self.stop_flag = False
        self.playing = False
        self.sound_frame: bytes | None = None

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ UI
    def _build(self) -> None:
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=(10, 4))
        nb.add(self._sound_tab(nb), text="Звук")
        nb.add(self._wifi_tab(nb), text="Wi-Fi (AP)")

        self.log = scrolledtext.ScrolledText(self, height=14, state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _sound_tab(self, parent) -> ttk.Frame:
        f = ttk.Frame(parent)
        pad = {"padx": 8, "pady": 4}
        self.s_ssid = tk.StringVar()
        self.s_pass = tk.StringVar()
        self.s_token = tk.StringVar(value=sp.DEFAULT_TOKEN)
        self.s_type = tk.IntVar(value=sp.WIFI_TYPE_WPA)
        self.s_gain = tk.DoubleVar(value=sp.DEFAULT_GAIN)
        self.s_repeat = tk.IntVar(value=3)
        self.s_gap = tk.DoubleVar(value=9.0)

        grid = ttk.Frame(f)
        grid.pack(fill="x", **pad)
        ttk.Label(grid, text="SSID:").grid(row=0, column=0, sticky="w")
        ttk.Entry(grid, textvariable=self.s_ssid).grid(row=0, column=1, sticky="we", padx=6)
        ttk.Label(grid, text="Пароль:").grid(row=1, column=0, sticky="w")
        ttk.Entry(grid, textvariable=self.s_pass, show="*").grid(row=1, column=1, sticky="we", padx=6)
        ttk.Label(grid, text="Токен:").grid(row=2, column=0, sticky="w")
        ttk.Entry(grid, textvariable=self.s_token).grid(row=2, column=1, sticky="we", padx=6)
        ttk.Label(grid, text="Тип:").grid(row=3, column=0, sticky="w")
        ttk.Combobox(
            grid, textvariable=self.s_type, values=(2, 4, 5), width=6, state="readonly"
        ).grid(row=3, column=1, sticky="w", padx=6)
        ttk.Label(grid, text="2=WPA, 4=скрытая, 5=открытая").grid(row=3, column=1, sticky="e")
        ttk.Label(grid, text="Громкость:").grid(row=4, column=0, sticky="w")
        ttk.Scale(grid, from_=0.1, to=0.9, variable=self.s_gain).grid(row=4, column=1, sticky="we", padx=6)
        ttk.Label(grid, text="Повторов:").grid(row=5, column=0, sticky="w")
        ttk.Spinbox(grid, from_=1, to=20, textvariable=self.s_repeat, width=6).grid(row=5, column=1, sticky="w", padx=6)
        ttk.Label(grid, text="Пауза, с:").grid(row=6, column=0, sticky="w")
        ttk.Spinbox(grid, from_=1, to=60, increment=1, textvariable=self.s_gap, width=6).grid(row=6, column=1, sticky="w", padx=6)
        grid.columnconfigure(1, weight=1)

        btns = ttk.Frame(f)
        btns.pack(fill="x", **pad)
        ttk.Button(btns, text="Сгенерировать WAV", command=self.on_make_sound).pack(side="left", padx=4)
        ttk.Button(btns, text="Проиграть", command=self.on_play_sound).pack(side="left", padx=4)
        ttk.Button(btns, text="Стоп", command=self.on_stop_sound).pack(side="left", padx=4)
        ttk.Label(
            f,
            text="Колонка должна быть в режиме настройки. Поднесите динамик к колонке,\n"
                 "громкость телефона/ноутбука — высокая. Кадр длится ~4.5 с.",
            justify="left",
        ).pack(fill="x", padx=8, pady=8)
        return f

    def _wifi_tab(self, parent) -> ttk.Frame:
        f = ttk.Frame(parent)
        pad = {"padx": 8, "pady": 4}
        self.w_url = tk.StringVar(value=ap_wifi.DEFAULT_URL)
        self.w_ssid = tk.StringVar()
        self.w_pass = tk.StringVar()
        self.w_token = tk.StringVar(value=ap_wifi.DEFAULT_TOKEN)
        self.w_wired = tk.BooleanVar(value=False)

        grid = ttk.Frame(f)
        grid.pack(fill="x", **pad)
        ttk.Label(grid, text="URL:").grid(row=0, column=0, sticky="w")
        ttk.Entry(grid, textvariable=self.w_url).grid(row=0, column=1, sticky="we", padx=6)
        ttk.Label(grid, text="SSID:").grid(row=1, column=0, sticky="w")
        ttk.Entry(grid, textvariable=self.w_ssid).grid(row=1, column=1, sticky="we", padx=6)
        ttk.Label(grid, text="Пароль:").grid(row=2, column=0, sticky="w")
        ttk.Entry(grid, textvariable=self.w_pass, show="*").grid(row=2, column=1, sticky="we", padx=6)
        ttk.Label(grid, text="Токен:").grid(row=3, column=0, sticky="w")
        ttk.Entry(grid, textvariable=self.w_token).grid(row=3, column=1, sticky="we", padx=6)
        ttk.Checkbutton(
            grid, text="Проводной режим (Ethernet, без Wi-Fi)", variable=self.w_wired
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
        grid.columnconfigure(1, weight=1)

        btns = ttk.Frame(f)
        btns.pack(fill="x", **pad)
        ttk.Button(btns, text="Проверить /info", command=self.on_wifi_info).pack(side="left", padx=4)
        ttk.Button(btns, text="Подключить", command=self.on_wifi_connect).pack(side="left", padx=4)
        ttk.Label(
            f,
            text="Ноутбук должен быть подключён к точке доступа устройства (Yandex-Hub).\n"
                 "Wi-Fi-пароль шифруется RSA/PKCS1 ключом из /info; токен не проверяется.",
            justify="left",
        ).pack(fill="x", padx=8, pady=8)
        return f

    # --------------------------------------------------------------- utils
    def write(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _thread(self, fn, *args) -> None:
        threading.Thread(target=fn, args=args, daemon=True).start()

    # --------------------------------------------------------------- sound
    def on_make_sound(self) -> None:
        ssid = self.s_ssid.get().strip()
        if not ssid:
            messagebox.showwarning(APP_TITLE, "Укажите SSID.")
            return
        try:
            frame = sp.build_frame(
                int(self.s_type.get()), ssid, self.s_pass.get(), self.s_token.get() or sp.DEFAULT_TOKEN
            )
            path = sp.make_wav(frame, WAV_PATH, gain=float(self.s_gain.get()))
            info = sp.describe(frame, float(self.s_gain.get()))
            self.sound_frame = frame
            self.write(f"звук: {path}")
            self.write(
                f"  кадр {info['frame_bytes']} Б, нибблов {info['nibbles']}, "
                f"после RS {info['encoded_nibbles']}, тонов {info['tones']}, "
                f"{info['duration_sec']} с"
            )
            self.write(f"  hex: {frame.hex()}")
        except Exception as exc:  # noqa: BLE001
            self.write(f"ошибка: {exc}")

    def on_play_sound(self) -> None:
        if self.playing:
            return
        if self.sound_frame is None:
            self.on_make_sound()
        if self.sound_frame is None:
            return
        self.stop_flag = False
        self.playing = True
        self._thread(self._play_loop)

    def _play_loop(self) -> None:
        try:
            import sounddevice as sd
        except Exception as exc:  # noqa: BLE001
            self.write(f"нет sounddevice: {exc}")
            self.playing = False
            return
        try:
            data, sr = sp.read_wav(WAV_PATH)
            repeat = max(1, int(self.s_repeat.get()))
            gap = max(0.0, float(self.s_gap.get()))
            for i in range(repeat):
                if self.stop_flag:
                    break
                self.write(f"проигрывание {i + 1}/{repeat}…")
                sd.play(data, sr)
                sd.wait()
                if i + 1 < repeat and not self.stop_flag:
                    end = time.time() + gap
                    while time.time() < end and not self.stop_flag:
                        time.sleep(0.05)
        except Exception as exc:  # noqa: BLE001
            self.write(f"ошибка воспроизведения: {exc}")
        finally:
            self.playing = False
            self.write("звук: готово")

    def on_stop_sound(self) -> None:
        self.stop_flag = True
        try:
            import sounddevice as sd

            sd.stop()
        except Exception:  # noqa: BLE001
            pass
        self.write("звук: остановлен")

    # ---------------------------------------------------------------- wifi
    def on_wifi_info(self) -> None:
        self._thread(self._wifi_info)

    def _wifi_info(self) -> None:
        try:
            info = ap_wifi.get_info(self.w_url.get())
            self.write("--- /info ---")
            self.write(ap_wifi.describe(info))
        except Exception as exc:  # noqa: BLE001
            self.write(f"ошибка: {exc}")

    def on_wifi_connect(self) -> None:
        ssid = self.w_ssid.get().strip()
        wired = self.w_wired.get()
        if not wired and not ssid:
            messagebox.showwarning(APP_TITLE, "Укажите SSID или включите проводной режим.")
            return
        self._thread(self._wifi_connect, ssid, wired)

    def _wifi_connect(self, ssid: str, wired: bool) -> None:
        try:
            self.write("--- /connect ---")
            info, answer = ap_wifi.connect(
                base_url=self.w_url.get(),
                ssid=ssid,
                password=self.w_pass.get(),
                token=self.w_token.get() or ap_wifi.DEFAULT_TOKEN,
                wired=wired,
            )
            self.write(ap_wifi.describe(info))
            self.write(f"ответ: {answer}")
            if answer.get("status") == "ok":
                self.write("готово: устройство подключается к сети")
            elif answer.get("data") == "WIFI_SSID_NOT_FOUND":
                self.write("SSID не найден — проверьте 2.4 ГГц")
            elif answer.get("data") == "WIFI_TIMEOUT":
                self.write("таймаут Wi-Fi — проверьте пароль/сеть")
        except Exception as exc:  # noqa: BLE001
            self.write(f"ошибка: {exc}")

    # --------------------------------------------------------------- close
    def _on_close(self) -> None:
        self.stop_flag = True
        try:
            import sounddevice as sd

            sd.stop()
        except Exception:  # noqa: BLE001
            pass
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
