#!/usr/bin/env python3
"""GUI для регистрации Яндекс-устройства по Wi-Fi через AP HTTP.

    python ap_wifi_gui.py

Ноутбук должен быть подключён к точке доступа устройства (Yandex-Hub),
устройство — в режиме настройки.
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

import ap_wifi

APP_TITLE = "Яндекс Станция — Wi-Fi через AP"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("620x560")
        self.minsize(560, 480)

        self.url = tk.StringVar(value=ap_wifi.DEFAULT_URL)
        self.ssid = tk.StringVar()
        self.password = tk.StringVar()
        self.token = tk.StringVar(value=ap_wifi.DEFAULT_TOKEN)
        self.wired = tk.BooleanVar(value=False)

        self._build()

    def _build(self) -> None:
        pad = {"padx": 10, "pady": 4}
        top = ttk.LabelFrame(self, text="Устройство")
        top.pack(fill="x", **pad)
        ttk.Label(top, text="URL:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(top, textvariable=self.url, width=42).grid(row=0, column=1, sticky="we", padx=6)
        ttk.Button(top, text="Проверить /info", command=self.on_info).grid(row=0, column=2, padx=6)
        top.columnconfigure(1, weight=1)

        net = ttk.LabelFrame(self, text="Wi-Fi")
        net.pack(fill="x", **pad)
        ttk.Label(net, text="SSID:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(net, textvariable=self.ssid).grid(row=0, column=1, sticky="we", padx=6)
        ttk.Label(net, text="Пароль:").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(net, textvariable=self.password, show="*").grid(row=1, column=1, sticky="we", padx=6)
        ttk.Label(net, text="Токен:").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(net, textvariable=self.token).grid(row=2, column=1, sticky="we", padx=6)
        ttk.Checkbutton(
            net,
            text="Проводной режим (Ethernet, без Wi-Fi)",
            variable=self.wired,
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=6, pady=4)
        net.columnconfigure(1, weight=1)

        actions = ttk.Frame(self)
        actions.pack(fill="x", **pad)
        self.connect_btn = ttk.Button(actions, text="Подключить", command=self.on_connect)
        self.connect_btn.pack(side="left", padx=6)
        ttk.Button(actions, text="Очистить лог", command=self.clear_log).pack(side="left", padx=6)

        self.log = scrolledtext.ScrolledText(self, height=16, state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ------------------------------------------------------------------ ui
    def clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def write(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def busy(self, value: bool) -> None:
        self.connect_btn.configure(state="disabled" if value else "normal")

    def on_info(self) -> None:
        threading.Thread(target=self._info, daemon=True).start()

    def _info(self) -> None:
        try:
            info = ap_wifi.get_info(self.url.get())
            self.write(ap_wifi.describe(info))
            if info.get("crypto_key"):
                self.write("crypto_key: получен")
        except Exception as exc:  # noqa: BLE001
            self.write(f"ошибка: {exc}")

    def on_connect(self) -> None:
        ssid = self.ssid.get().strip()
        wired = self.wired.get()
        if not wired and not ssid:
            messagebox.showwarning(APP_TITLE, "Укажите SSID или включите проводной режим.")
            return
        if not messagebox.askokcancel(
            APP_TITLE,
            "Устройство будет перезагружено в рабочую сеть.\n"
            "Ноутбук должен быть подключён к его точке доступа или к Ethernet Хаба.\n"
            "В проводном режиме SSID — только заглушка.\nПродолжить?",
        ):
            return
        self.busy(True)
        threading.Thread(target=self._connect, args=(ssid, wired), daemon=True).start()

    def _connect(self, ssid: str, wired: bool) -> None:
        try:
            self.write("--- /connect ---")
            info, answer = ap_wifi.connect(
                base_url=self.url.get(),
                ssid=ssid,
                password=self.password.get(),
                token=self.token.get() or ap_wifi.DEFAULT_TOKEN,
                wired=wired,
            )
            self.write(ap_wifi.describe(info))
            self.write(f"ответ: {answer}")
            if answer.get("status") == "ok":
                self.write("Готово: устройство подключается к сети.")
            elif answer.get("data") == "WIFI_SSID_NOT_FOUND":
                self.write("Устройство не видит SSID — проверьте 2.4 ГГц.")
            elif answer.get("data") == "WIFI_TIMEOUT":
                self.write("Таймаут Wi-Fi — проверьте пароль/сеть.")
        except Exception as exc:  # noqa: BLE001
            self.write(f"ошибка: {exc}")
        finally:
            self.busy(False)


if __name__ == "__main__":
    App().mainloop()
