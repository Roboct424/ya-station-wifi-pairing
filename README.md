# ya-station-wifi-pairing

## Русский

Подключение Яндекс Станции к Wi-Fi **звуком**: без приложения, облака и root.
Колонка принимает SSID и пароль из акустического сигнала длительностью 4.5 секунды.

В репозитории — разобранный протокол (кадр, Reed–Solomon, тоны), разбор BLE-канала
и объяснение, почему он не подходит для офлайна, готовые инструменты и приложение.

```
динамик ──── звук 4.5 с ────► колонка ──── Wi-Fi ────► роутер
```

### Как это работает

```
кадр:  [тип][len SSID][SSID][len пароль][пароль][len токен][токен][CRC32]
RS:    блоки 11 данных + 4 ECC ниббла, GF(16), полином 0x13
тоны:  f = 1024 + ниббл*256 Гц, по 40 мс, 16 кГц
эфир:  6192,6192,5120,5120 | версия, контроль | данные | 5632 × 8
```

Кадр 35 байт → 70 нибблов → 98 после RS → 112 тонов → 4.48 с.
Ключевая деталь: **токен активации колонка не проверяет** на этом шаге, поэтому
подходит любая строка и облако не требуется.

Полное описание, включая примеры и проверочные векторы:
[`docs/01-sound-protocol.md`](docs/01-sound-protocol.md).

### Почему не Bluetooth

BLE-канал принимает только зашифрованный конверт
`{"ciphertext": …, "M": …, "C": …}` (32 / 32 / 256 байт). Расшифровка выполняется
внутри защищённой среды (`keymaster`/TEE), ключ у каждого устройства свой и не
экспортируется. Открытый текст не принимается ни в одной из write-характеристик —
проверены все, включая разные схемы полей.

Итог: по BLE можно лишь повторить ранее полученный конверт на том же устройстве.
Для локальной настройки с любыми кредами и на любом устройстве подходит только звук.
Все проверки и GATT-карта: [`docs/02-ble-protocol.md`](docs/02-ble-protocol.md).

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

Проверено на Station Mini 2, прошивка `0.369.1.46`: приём подтверждён логом
`Successful parsing: Credentials{ SSID='YaRig' }`, эталонный кадр
`02055961526967083131313131313131106c6f63616c7061697230303030303030a86a`.

### Чего здесь нет

Нет подмены трафика, эмуляции облака, регистрации в аккаунте и получения root —
это отдельная задача. Здесь только подключение колонки к Wi-Fi.

### Лицензия

MIT. Не аффилировано с вендором. Используйте на своих устройствах.

---

## English

Connecting a Yandex Station to Wi-Fi **over sound**: no app, no cloud, no root.
The station receives the SSID and password from a 4.5-second acoustic signal.

The repository contains the reverse-engineered protocol (frame, Reed–Solomon, tones),
a full BLE analysis and an explanation of why it cannot be used offline, plus ready
tools and an application.

```
speaker ──── sound 4.5 s ────► station ──── Wi-Fi ────► router
```

### How it works

```
frame:  [type][len SSID][SSID][len password][password][len token][token][CRC32]
RS:     blocks of 11 data + 4 ECC nibbles, GF(16), polynomial 0x13
tones:  f = 1024 + nibble*256 Hz, 40 ms each, 16 kHz
air:    6192,6192,5120,5120 | version, checksum | data | 5632 × 8
```

The frame is 35 bytes → 70 nibbles → 98 after RS → 112 tones → 4.48 s.
The key detail: **the activation token is not validated** at this stage, so any
string works and no cloud is involved.

Full description with examples and test vectors:
[`docs/01-sound-protocol.md`](docs/01-sound-protocol.md).

### Why not Bluetooth

The BLE channel accepts only an encrypted envelope
`{"ciphertext": …, "M": …, "C": …}` (32 / 32 / 256 bytes). Decryption happens
inside the secure environment (`keymaster`/TEE); the key is per-device and is not
exportable. Plaintext is rejected by every write characteristic — all of them were
tested, including several field schemas.

Bottom line: BLE can only replay a previously obtained envelope on the same device.
For local provisioning with arbitrary credentials on any device, only sound works.
All checks and the GATT map: [`docs/02-ble-protocol.md`](docs/02-ble-protocol.md).

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

Verified on Station Mini 2, firmware `0.369.1.46`: reception confirmed by the log line
`Successful parsing: Credentials{ SSID='YaRig' }`; reference frame
`02055961526967083131313131313131106c6f63616c7061697230303030303030a86a`.

### Out of scope

No traffic interception, no cloud emulation, no account registration and no rooting —
that is a separate task. Only Wi-Fi provisioning is covered here.

### License

MIT. Not affiliated with the vendor. Use on your own devices.
