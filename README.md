# ya-station-wifi-pairing

## Русский

Подключение Яндекс Станции к Wi-Fi **звуком**: без приложения, облака и root.
Колонка принимает SSID и пароль из акустического сигнала длиной 4.5 секунды.

В репозитории — разобранный протокол (кадр, Reed–Solomon, тоны), разбор BLE-канала
и объяснение, почему он не подходит, готовые инструменты и приложение.

```
динамик ──── звук 4.5 с ────► колонка ──── Wi-Fi ────► роутер
```

## English

Wi-Fi provisioning for Yandex Station **over sound**: no app, no cloud, no root.
The speaker receives SSID and password from a 4.5-second acoustic signal.

This repo contains the reverse-engineered protocol (frame, Reed–Solomon, tones),
a full BLE analysis and why it can't be used offline, plus tools and a mobile app.

---

## Quick start / Быстрый старт

```bash
pip install numpy sounddevice

# один раз / once
python tools/pair_by_sound.py --ssid "MyWiFi" --password "secret"

# играть, пока колонка не появится в сети / loop until online
python tools/provision.py --ssid "MyWiFi" --password "secret"
```

Колонка должна быть в режиме настройки (новая или сброшенная).
Подробно: [`docs/03-practice.md`](docs/03-practice.md).

## Что внутри / Contents

| | |
|---|---|
| [`docs/01-sound-protocol.md`](docs/01-sound-protocol.md) | звуковой протокол: кадр, RS(15,11) над GF(16), тоны, тайминги |
| [`docs/02-ble-protocol.md`](docs/02-ble-protocol.md) | BLE: GATT-карта, формат кадров, шифрование в TEE |
| [`docs/03-practice.md`](docs/03-practice.md) | практика: громкость, окно декодера, разбор проблем |
| [`docs/04-scope.md`](docs/04-scope.md) | границы проекта, безопасность, правовое |
| `tools/` | кодер, CLI, автопровижининг, GUI, веб-версия, тесты |
| `android/` | APK и исходники (WebView, без разрешений) |
| `examples/` | пример кадра и полная последовательность тонов |

## Релизы / Releases

* `SoundCode.apk` — Android-приложение
* `StationWiFiPairing.exe` — Windows (GUI, один файл)
* `ya-station-wifi-pairing_1.0.0_all.deb` — Debian/Ubuntu пакет
* `ya-station-wifi-pairing-1.0.0.tar.gz` — исходники для Linux/macOS

## Проверка / Self-test

```bash
python tools/test_frame.py
```

## Чего здесь нет / Out of scope

Нет подмены трафика, эмуляции облака, регистрации и получения root —
это отдельная задача. Здесь только подключение колонки к Wi-Fi.

No traffic interception, cloud emulation, account registration or rooting.
Only Wi-Fi provisioning.

## Лицензия / License

MIT. Не аффилировано с вендором. Используйте на своих устройствах.
Not affiliated with the vendor. Use on your own devices.
