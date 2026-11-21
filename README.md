# ya-station-wifi-pairing

## Русский

Подключение Яндекс Станции к Wi-Fi **звуком или по AP HTTP**: без приложения,
облака и root. Колонка принимает SSID и пароль из акустического сигнала
длительностью 4.5 секунды, а устройства с точкой доступа — по локальному
HTTP с RSA-шифрованием.

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

### Wi-Fi по AP HTTP

У устройств с точкой доступа (Хабы, станции с экраном) есть второй локальный
путь: устройство поднимает `Yandex-Hub` (`192.168.43.1/24`) и HTTP на порту
`8080`. Ноутбук подключается к этой точке и отправляет Wi-Fi-креды:

```text
GET  /info      → crypto_key (RSA-2048), mac, uuid, version
POST /connect   → {"ssid": "...",
                    "password": "<base64(RSA_PKCS1(пароль))>",
                    "xtoken_code": "<base64(RSA_PKCS1(токен))>"}
```

- пароль и токен шифруются **RSA/PKCS1 v1.5** публичным ключом из `/info`
  (OAEP устройство не принимает);
- токен активации на шаге Wi-Fi **не проверяется** — подходит любая строка,
  облако не нужно;
- проводной режим: `{"ssid": "", "xtoken_code": ...}` без пароля — устройство
  использует Ethernet;
- часть устройств умеет только 2.4 ГГц: на 5 ГГц ответ
  `WIFI_SSID_NOT_FOUND`.

Подробно: [`docs/05-ap-http.md`](docs/05-ap-http.md).
Инструменты: [`tools/ap_wifi.py`](tools/ap_wifi.py) (CLI),
[`tools/ap_wifi_gui.py`](tools/ap_wifi_gui.py) (GUI),
[`tools/test_ap_wifi.py`](tools/test_ap_wifi.py) (mock-тест).

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
pip install numpy sounddevice cryptography

# звук
python tools/station_pairing.py sound --ssid "MyWiFi" --password "secret"

# Wi-Fi через AP HTTP (ноутбук подключён к Yandex-Hub)
python tools/station_pairing.py wifi --ssid "MyWiFi" --password "secret"

# проводной режим (Ethernet, без Wi-Fi-кредов)
python tools/station_pairing.py wifi --wired

# GUI: две вкладки — «Звук» и «Wi-Fi (AP)»
python tools/station_pairing.py gui
```

Готовые сборки:

* Windows: `dist/StationPairing.exe` (CLI) и
  `dist/StationPairingGUI.exe` (GUI);
* Linux/macOS: `bash packaging/build_unix.sh` (PyInstaller);
* Debian/Ubuntu: `python packaging/build_deb.py` (пакет ставит
  `ya-station-pairing` и `ya-station-pairing-gui`).

Старые раздельные команды (`pair_by_sound.py`, `provision.py`,
`ap_wifi.py`) остаются для совместимости.

Колонка должна быть в режиме настройки (новая или сброшенная).
Подробно: [`docs/03-practice.md`](docs/03-practice.md).

### Что внутри

| Файл | Содержание |
|---|---|
| [`docs/01-sound-protocol.md`](docs/01-sound-protocol.md) | звуковой протокол: кадр, RS(15,11) над GF(16), тоны, тайминги |
| [`docs/02-ble-protocol.md`](docs/02-ble-protocol.md) | BLE: GATT-карта, формат кадров, шифрование в TEE |
| [`docs/03-practice.md`](docs/03-practice.md) | практика: громкость, окно декодера, разбор проблем |
| [`docs/04-scope.md`](docs/04-scope.md) | границы проекта, безопасность, правовое |
| [`docs/05-ap-http.md`](docs/05-ap-http.md) | Wi-Fi через AP HTTP: `/info`, RSA/PKCS1, `/connect`, Ethernet |
| `tools/` | кодер, CLI, автопровижининг, GUI, AP HTTP, веб-версия, тесты |
| `android/` | APK и исходники (WebView, без разрешений) |
| `examples/` | пример кадра и полная последовательность тонов |

### Релизы

* `SoundCode.apk` — Android-приложение (звук)
* `StationPairing.exe` — Windows: звук + AP HTTP (CLI, один файл)
* `StationPairingGUI.exe` — Windows: звук + AP HTTP (GUI, один файл)
* `StationWiFiPairing.exe` — старая Windows-сборка (только звук)
* `ya-station-wifi-pairing_1.1.0_all.deb` — Debian/Ubuntu пакет
* `ya-station-wifi-pairing-1.1.0.tar.gz` — исходники для Linux/macOS
  (сборка: `bash packaging/build_unix.sh`)

### Проверка

```bash
python tools/test_frame.py
```

Проверено на Station Mini 2, прошивка `0.369.1.46`: приём подтверждён логом
`Successful parsing: Credentials{ SSID='YaRig' }`, эталонный кадр
`02055961526967083131313131313131106c6f63616c7061697230303030303030a86a`.

### Чего здесь нет

Нет подмены трафика, эмуляции облака, регистрации в аккаунте и получения root —
это отдельная задача. Здесь только подключение к Wi-Fi: звуком и через AP HTTP.

### Лицензия

MIT. Не аффилировано с вендором. Используйте на своих устройствах.

---

## English

Connecting a Yandex Station to Wi-Fi **over sound or AP HTTP**: no app, no
cloud, no root. The station receives the SSID and password from a 4.5-second
acoustic signal, and devices with an access point accept them over local HTTP
with RSA encryption.

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

### Wi-Fi over AP HTTP

Devices with an access point (Hubs, stations with a screen) have a second local
path: the device starts `Yandex-Hub` (`192.168.43.1/24`) and HTTP on port
`8080`. The laptop joins that AP and sends the credentials:

```text
GET  /info      → crypto_key (RSA-2048), mac, uuid, version
POST /connect   → {"ssid": "...",
                    "password": "<base64(RSA_PKCS1(password))>",
                    "xtoken_code": "<base64(RSA_PKCS1(token))>"}
```

- the password and token are encrypted with **RSA/PKCS1 v1.5** using the key
  from `/info` (OAEP is rejected);
- the activation token is **not validated** during the Wi-Fi step — any string
  works, no cloud involved;
- wired mode: `{"ssid": "", "xtoken_code": ...}` without a password — the
  device uses Ethernet;
- some devices are 2.4 GHz only: a 5 GHz AP returns `WIFI_SSID_NOT_FOUND`.

Details: [`docs/05-ap-http.md`](docs/05-ap-http.md).
Tools: [`tools/ap_wifi.py`](tools/ap_wifi.py) (CLI),
[`tools/ap_wifi_gui.py`](tools/ap_wifi_gui.py) (GUI),
[`tools/test_ap_wifi.py`](tools/test_ap_wifi.py) (mock test).

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
pip install numpy sounddevice cryptography

# sound
python tools/station_pairing.py sound --ssid "MyWiFi" --password "secret"

# Wi-Fi over AP HTTP (laptop joined to Yandex-Hub)
python tools/station_pairing.py wifi --ssid "MyWiFi" --password "secret"

# wired mode (Ethernet, no Wi-Fi credentials)
python tools/station_pairing.py wifi --wired

# GUI with two tabs: Sound and Wi-Fi (AP)
python tools/station_pairing.py gui
```

Prebuilt binaries:

* Windows: `dist/StationPairing.exe` (CLI) and
  `dist/StationPairingGUI.exe` (GUI);
* Linux/macOS: `bash packaging/build_unix.sh` (PyInstaller);
* Debian/Ubuntu: `python packaging/build_deb.py` (installs
  `ya-station-pairing` and `ya-station-pairing-gui`).

The old separate commands (`pair_by_sound.py`, `provision.py`,
`ap_wifi.py`) remain for compatibility.

The station must be in setup mode (new or factory-reset).
Details: [`docs/03-practice.md`](docs/03-practice.md).

### Contents

| File | Description |
|---|---|
| [`docs/01-sound-protocol.md`](docs/01-sound-protocol.md) | sound protocol: frame, RS(15,11) over GF(16), tones, timing |
| [`docs/02-ble-protocol.md`](docs/02-ble-protocol.md) | BLE: GATT map, frame format, encryption in the TEE |
| [`docs/03-practice.md`](docs/03-practice.md) | practice: volume, decoder window, troubleshooting |
| [`docs/04-scope.md`](docs/04-scope.md) | scope, security, legal notes |
| [`docs/05-ap-http.md`](docs/05-ap-http.md) | Wi-Fi over AP HTTP: `/info`, RSA/PKCS1, `/connect`, Ethernet |
| `tools/` | encoder, CLI, auto-provisioning, GUI, AP HTTP, web version, tests |
| `android/` | APK and sources (WebView, no permissions) |
| `examples/` | sample frame and the full tone sequence |

### Releases

* `SoundCode.apk` — Android application (sound)
* `StationPairing.exe` — Windows: sound + AP HTTP (CLI, single file)
* `StationPairingGUI.exe` — Windows: sound + AP HTTP (GUI, single file)
* `StationWiFiPairing.exe` — older Windows build (sound only)
* `ya-station-wifi-pairing_1.1.0_all.deb` — Debian/Ubuntu package
* `ya-station-wifi-pairing-1.1.0.tar.gz` — sources for Linux/macOS
  (build: `bash packaging/build_unix.sh`)

### Self-test

```bash
python tools/test_frame.py
```

Verified on Station Mini 2, firmware `0.369.1.46`: reception confirmed by the log line
`Successful parsing: Credentials{ SSID='YaRig' }`; reference frame
`02055961526967083131313131313131106c6f63616c7061697230303030303030a86a`.

### Out of scope

No traffic interception, no cloud emulation, no account registration and no rooting —
that is a separate task. Only Wi-Fi provisioning is covered here: sound and AP HTTP.

### License

MIT. Not affiliated with the vendor. Use on your own devices.
