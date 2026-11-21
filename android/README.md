# Android-приложение «Сопряжение Станции»

Офлайн-приложение: WebView + та же HTML-страница, что в `tools/sound_code.html`.
Две вкладки — **Звук** и **Wi-Fi (AP)**. Аналитики нет; единственное разрешение —
`INTERNET`, и оно нужно только для локального HTTP к точке доступа устройства
(в интернет приложение не ходит). Размер APK — ~21 КБ.

## Готовый APK

`SoundCode.apk` — можно сразу ставить на телефон (Android 4.2+, `minSdk 17`).
При установке разрешите «установку из неизвестных источников».

## Сборка из исходников

Нужна только **JRE 8+** (javac и Android SDK не требуются).

```powershell
python fetch_tools.py       # ≈33 МБ: aapt2, d8/r8, android.jar, apksig, ecj
powershell -File build_apk.ps1
```

Ключ подписи (`rig.key.pem` / `rig.crt.pem`) генерируется при первой сборке
в каталоге `android/` и в git не попадает (см. `.gitignore`).

Почему именно такие версии:

| Инструмент | Почему |
|---|---|
| `ecj 3.26.0` | компилирует Java 8 и сам работает на JRE 8 |
| `r8 1.6.84` | последняя версия D8, собранная под Java 8 (новые требуют Java 11) |
| `aapt2 8.1.0` | линкует манифест и ассеты без SDK |
| `apksig 8.1.0` | подпись v1+v2 без `apksigner` и keystore (ключ в PEM) |

`android.jar` из Maven — это **stub API 16**: в нём нет `org.json`,
`javax.crypto` и даже `android.webkit.JavascriptInterface`. Поэтому мост в Java
не использует ни `@JavascriptInterface`, ни JSON-библиотеки:

* Java умеет только локальный HTTP (`HttpURLConnection`) и отдаёт **сырой текст**
  ответа устройства;
* RSA/PKCS#1 v1.5 и JSON считает сам HTML на `BigInt` (`rsaEncrypt()`);
* передача — через JSONP: `<script src="https://local.yandex/http?...&cb=...">`,
  который перехватывает `WebViewClient.shouldInterceptRequest`
  (у `<script>` нет CORS-ограничений, поэтому работает из `file://`).

`targetSdkVersion=27` выбран специально: cleartext-HTTP к `192.168.43.1`
разрешён по умолчанию (блокировка появилась с `targetSdk 28`), при этом
подпись v2 уже есть.

## Структура

```
AndroidManifest.xml              minSdk 17, targetSdk 27, INTERNET
src/com/rig/soundcode/MainActivity.java  WebView + JSONP-мост (HTTP)
signer/Signer.java               подпись через apksig (PEM-ключ)
fetch_tools.py                   скачивание инструментов в .tools/
build_apk.ps1                    сборка одной командой
SoundCode.apk                    готовый артефакт
```

## Что делает приложение

Открывает локальную страницу `file:///android_asset/index.html` в WebView.

Вкладка **Звук**:

* поля SSID/пароль/тип сети/токен;
* ползунок громкости и **предстарт 0–4** (повтор преамбулы);
* воспроизведение и повтор каждые 10 секунд;
* сохранение WAV.

Вкладка **Wi-Fi (AP)**:

* URL устройства (по умолчанию `http://192.168.43.1:8080`);
* SSID/пароль/токен, галочка «проводной режим»;
* «Проверить /info» — показывает `uuid`, `version`, `crypto_key`;
* «Подключить» — RSA/PKCS#1 пароля и токена, `POST /connect`;
* человекочитаемые ошибки: `WIFI_SSID_NOT_FOUND` (5 ГГц / нет сети),
  `WIFI_TIMEOUT` (неверный пароль).

Телефон должен быть подключён к точке доступа устройства (`Yandex-Hub`).
Звук стартует без «нажмите, чтобы разрешить» —
`setMediaPlaybackRequiresUserGesture(false)` вызывается через рефлексию,
чтобы код собирался под старый `android.jar`.
