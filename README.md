# ya-station-wifi-pairing

## Русский

Подключение Яндекс Станции к Wi-Fi **звуком**: без приложения, облака и root.
Колонка принимает SSID и пароль из акустического сигнала длительностью 4.5 секунды.

В репозитории — разобранный протокол (кадр, Reed–Solomon, тоны), разбор BLE-канала
и объяснение, почему он не подходит для офлайна, готовые инструменты и приложение.

```
динамик ──── звук 4.5 с ────► колонка ──── Wi-Fi ────► роутер
```

### Быстрый старт

```bash
pip install numpy sounddevice

# один раз
python tools/pair_by_sound.py --ssid "MyWiFi" --password "secret"

# играть, пока колонка не появится в сети
python tools/provision.py --ssid "MyWiFi" --password "secret"
```

Колонка должна быть в режиме настройки (новая или сброшенная).
Подробно: [`docs/03-practice.md`](docs/03-practice.md).

### Что внутри

| Файл | Содержание |
|---|---|
| [`docs/01-sound-protocol.md`](docs/01-sound-protocol.md) | звуковой протокол: кадр, RS(15,11) над GF(16), тоны, тайминги |
| [`docs/02-ble-protocol.md`](docs/02-ble-protocol.md) | BLE: GATT-карта, формат кадров, шифрование в TEE |
| [`docs/03-practice.md`](docs/03-practice.md) | практика: громкость, окно декодера, разбор проблем |
| [`docs/04-scope.md`](docs/04-scope.md) | границы проекта, безопасность, правовое |
| `tools/` | кодер, CLI, автопровижининг, GUI, веб-версия, тесты |
| `android/` | APK и исходники (WebView, без разрешений) |
| `examples/` | пример кадра и полная последовательность тонов |

### Релизы

* `SoundCode.apk` — Android-приложение
* `StationWiFiPairing.exe` — Windows (GUI, один файл)
* `ya-station-wifi-pairing_1.0.0_all.deb` — Debian/Ubuntu пакет
* `ya-station-wifi-pairing-1.0.0.tar.gz` — исходники для Linux/macOS

### Проверка

```bash
python tools/test_frame.py
```

### Чего здесь нет

Нет подмены трафика, эмуляции облака, регистрации в аккаунте и получения root —
это отдельная задача. Здесь только подключение колонки к Wi-Fi.

### Лицензия

MIT. Не аффилировано с вендором. Используйте на своих устройствах.

---

## English

Connecting a Yandex Station to Wi-Fi **over sound**: no app, no cloud, no root.
The speaker receives the SSID and password from a 4.5-second acoustic signal.

The repository contains the reverse-engineered protocol (frame, Reed–Solomon, tones),
a full BLE analysis and an explanation of why it cannot be used offline, plus ready
tools and an application.

```
speaker ──── sound 4.5 s ────► station ──── Wi-Fi ────► router
```

### Quick start

```bash
pip install numpy sounddevice

# once
python tools/pair_by_sound.py --ssid "MyWiFi" --password "secret"

# play until the station appears on the network
python tools/provision.py --ssid "MyWiFi" --password "secret"
```

The station must be in setup mode (new or factory-reset).
Details: [`docs/03-practice.md`](docs/03-practice.md).

### Contents

| File | Description |
|---|---|
| [`docs/01-sound-protocol.md`](docs/01-sound-protocol.md) | sound protocol: frame, RS(15,11) over GF(16), tones, timing |
| [`docs/02-ble-protocol.md`](docs/02-ble-protocol.md) | BLE: GATT map, frame format, encryption in the TEE |
| [`docs/03-practice.md`](docs/03-practice.md) | practice: volume, decoder window, troubleshooting |
| [`docs/04-scope.md`](docs/04-scope.md) | scope, security, legal notes |
| `tools/` | encoder, CLI, auto-provisioning, GUI, web version, tests |
| `android/` | APK and sources (WebView, no permissions) |
| `examples/` | sample frame and the full tone sequence |

### Releases

* `SoundCode.apk` — Android application
* `StationWiFiPairing.exe` — Windows (GUI, single file)
* `ya-station-wifi-pairing_1.0.0_all.deb` — Debian/Ubuntu package
* `ya-station-wifi-pairing-1.0.0.tar.gz` — sources for Linux/macOS

### Self-test

```bash
python tools/test_frame.py
```

### Out of scope

No traffic interception, no cloud emulation, no account registration and no rooting —
that is a separate task. Only Wi-Fi provisioning is covered here.

### License

MIT. Not affiliated with the vendor. Use on your own devices.
