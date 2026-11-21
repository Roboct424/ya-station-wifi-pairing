# 05 — Wi-Fi через AP HTTP (firstrund)

Это второй, «сетевой» способ настройки. Он не требует звука и не требует
приложения: устройство само поднимает открытую точку доступа и HTTP-сервер,
а мы отправляем ему Wi-Fi-креды, зашифрованные его же публичным ключом.

```
ноутбук ── Wi-Fi ──► Yandex-Hub (192.168.43.1)
                         │  HTTP :8080
                         ├── GET  /info      → RSA-ключ, mac, uuid, version
                         └── POST /connect   → ssid + RSA(password) + RSA(token)
                                              │
                                              ▼
                                        устройство → ваш Wi-Fi
```

## Когда применимо

- Устройство в режиме настройки (новое или после сброса) и поднимает AP.
- Обычно SSID `Yandex-Hub`, адрес `192.168.43.1/24`, HTTP-порт `8080`.
- Ноутбук подключается к этой точке (интернет на время настройки не нужен).

Если устройство не поднимает AP (например, уже сконфигурировано), этот путь
не сработает — нужен сброс или звуковой/штатный способ.

## Эндпоинты

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/info` | публичный ключ и идентификаторы |
| `GET` | `/get_last_error` | последняя ошибка |
| `GET` | `/ssid` | список сетей (обычно пустой) |
| `POST` | `/connect` | Wi-Fi-креды |
| `POST` | `/pause_access_point` | пауза точки доступа |

Пример `/info` (реальный ответ Хаба):

```json
{
  "crypto_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A...\n-----END PUBLIC KEY-----",
  "mac": "3c:0b:4f:15:40:6e\n",
  "uuid": "S006NQ20034ZFW",
  "version": "0.18.1.7.1717666568.20230419.factory-15.factory"
}
```

`crypto_key` — RSA-2048 в формате SubjectPublicKeyInfo (PEM). Ключ привязан к
устройству (хранится в Keymaster/TEE). **Берите его из `/info` при каждом
запуске**, не кэшируйте между сессиями.

## POST /connect

Тело — JSON:

```json
{
  "ssid": "MyWiFi",
  "password": "<base64(RSA_PKCS1(пароль))>",
  "xtoken_code": "<base64(RSA_PKCS1(токен))>"
}
```

Правила:

- `ssid` — открытая строка.
- `password` — **шифруется** публичным ключом из `/info`, схема
  **RSA/PKCS1 v1.5**, затем base64. Если отправить пароль открытым текстом,
  устройство воспримет его как base64 и отдаст в Keymaster — будет
  `Keymaster TA error -1000`.
- `xtoken_code` — тоже `base64(RSA_PKCS1(...))`. Токен активации на этом шаге
  **не проверяется**: подходит любая строка (например,
  `localpair0000000`). Это и есть локальный обход без облака.
- OAEP не поддерживается: устройство принимает только PKCS1 v1.5.
- Оба поля передаются как обычные JSON-строки; бинарные байты внутри не нужны.

Ответы:

```json
{"status": "ok"}
```

```json
{"data": "WIFI_TIMEOUT", "error_code": 3, "status": "error"}
```

```json
{"data": "WIFI_SSID_NOT_FOUND", "error_code": 1, "status": "error"}
```

`WIFI_SSID_NOT_FOUND` чаще всего означает, что устройство не видит сеть:
например, оно умеет только **2.4 ГГц**, а точка была 5 ГГц. `WIFI_TIMEOUT` —
неверный пароль или сеть не ответила.

## Проводной режим (Ethernet)

Если устройство подключено кабелем и у него есть интернет, Wi-Fi-креды можно
не передавать:

```json
{"ssid": "", "xtoken_code": "<base64(RSA_PKCS1(токен))>"}
```

Устройство уйдёт в состояние `connecting_to_network` и будет использовать
Ethernet. В прошивке это отдельная ветка (`ConnectionType.ETHERNET`,
`SetupEndpoint.MissingWifiCredentials`); если интернета по кабелю нет, оно
проиграет `activation_no_network_in_ethernet.wav`.

## Пример на Python

```python
import base64, json, urllib.request
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

BASE = "http://192.168.43.1:8080"

info = json.load(urllib.request.urlopen(BASE + "/info", timeout=5))
key = serialization.load_pem_public_key(info["crypto_key"].encode())

def enc(text: str) -> str:
    return base64.b64encode(key.encrypt(text.encode(), padding.PKCS1v15())).decode()

body = {
    "ssid": "MyWiFi",
    "password": enc("secret"),
    "xtoken_code": enc("localpair0000000"),
}
req = urllib.request.Request(
    BASE + "/connect",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
print(urllib.request.urlopen(req, timeout=30).read().decode())
```

Готовый CLI: [`../tools/station_pairing.py`](../tools/station_pairing.py)
(`wifi ...`), отдельный [`../tools/ap_wifi.py`](../tools/ap_wifi.py),
GUI: [`../tools/station_pairing_gui.py`](../tools/station_pairing_gui.py),
тест: [`../tools/test_ap_wifi.py`](../tools/test_ap_wifi.py).

## Отличия от звука и BLE

| Способ | Нужен AP | Нужен звук | Токен проверяется | Облако | Ограничения |
|---|---|---|---|---|---|
| Звук | нет | да (динамик/микрофон) | нет | нет | нужен динамик рядом; 4.5 с на кадр |
| AP HTTP | да (`Yandex-Hub`) | нет | нет | нет | ноутбук уходит в AP; только 2.4 ГГц у части устройств |
| BLE | нет | нет | — | — | конверт шифруется в TEE, ключ не экспортируется |

AP HTTP удобен для устройств с экраном/Хабов, у которых есть AP-режим;
звук — для колонок без AP. BLE для оффлайна не подходит (см.
[`02-ble-protocol.md`](02-ble-protocol.md)).

## Безопасность и правовое

Способ работает только с устройством, которое **само** подняло AP для
настройки, и только с вашими устройствами. Публичный ключ устройства не
является секретом; приватный ключ остаётся в TEE и не экспортируется.
Токен активации не подделывает аккаунт и не даёт доступ к чужому облаку —
он лишь проходит локальный шаг настройки.

## Проверено

- Хаб `S006NQ20034ZFW`, прошивка `0.18.1.7...factory-15.factory`:
  `/info` отдал RSA-2048, `POST /connect` с шифрованным паролем принят,
  устройство перешло в `connecting_to_network`; на 5 ГГц тестовой точке
  вернулся `WIFI_SSID_NOT_FOUND`.
- Keymaster подтвердил расшифровку: `probe` → `probe`, PKCS1; OAEP — ошибка.
