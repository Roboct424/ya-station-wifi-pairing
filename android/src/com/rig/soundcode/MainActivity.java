package com.rig.soundcode;

import android.app.Activity;
import android.net.Uri;
import android.os.Bundle;
import android.view.WindowManager;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URL;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/**
 * Оболочка вокруг tools/sound_code.html (он же ассет index.html).
 *
 * targetSdk 33: Play Protect блокирует сайдлоад приложений со старым
 * targetSdk. Вместе с этим нельзя использовать атрибут
 * android:usesCleartextTraffic (его нет в stub android.jar API 16),
 * поэтому HTTP к точке доступа устройства сделан вручную поверх
 * java.net.Socket: политика cleartext применяется к HttpURLConnection,
 * но не к сырым сокетам.
 *
 * Мост: JSONP (<script> не подчиняется CORS), RSA/PKCS#1 и JSON считает
 * сам HTML на BigInt — в stub android.jar нет org.json и javax.crypto.
 *
 * Запрос:  https://local.yandex/http?url=...&method=GET|POST&body=<base64url>&cb=name
 * Ответ:   name({"ok":true,"text":"<сырой ответ устройства>"})
 */
public class MainActivity extends Activity {
    private WebView web;
    private static final String LOCAL = "https://local.yandex/";

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        try {
            WebSettings.class.getMethod("setMediaPlaybackRequiresUserGesture", boolean.class)
                    .invoke(s, Boolean.FALSE);
        } catch (Throwable ignored) {
        }

        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, String url) {
                if (url == null || !url.startsWith(LOCAL)) return null;
                String js = handle(Uri.parse(url));
                try {
                    return new WebResourceResponse("application/javascript", "UTF-8",
                            new ByteArrayInputStream(js.getBytes("UTF-8")));
                } catch (Exception e) {
                    return null;
                }
            }
        });

        web.loadUrl("file:///android_asset/index.html");
        setContentView(web);
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    // ------------------------------------------------------------- bridge ---
    private String handle(Uri u) {
        String cb = u.getQueryParameter("cb");
        if (cb == null || cb.length() == 0) cb = "__yaBridge";

        String text = null;
        String error = null;
        try {
            String target = u.getQueryParameter("url");
            String method = u.getQueryParameter("method");
            if (method == null || method.length() == 0) method = "GET";
            String body = null;
            String b64 = u.getQueryParameter("body");
            if (b64 != null && b64.length() > 0) {
                body = new String(base64url(b64), "UTF-8");
            }
            text = http(method, target, body);
        } catch (Exception e) {
            error = e.toString();
        }

        StringBuilder sb = new StringBuilder();
        sb.append(cb).append("({");
        if (error == null) {
            sb.append("\"ok\":true,\"text\":\"").append(escape(text)).append('"');
        } else {
            sb.append("\"ok\":false,\"error\":\"").append(escape(error)).append('"');
        }
        sb.append("})");
        return sb.toString();
    }

    private static String escape(String s) {
        if (s == null) return "";
        StringBuilder b = new StringBuilder(s.length() + 16);
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '\\': b.append("\\\\"); break;
                case '"': b.append("\\\""); break;
                case '\n': b.append("\\n"); break;
                case '\r': b.append("\\r"); break;
                case '\t': b.append("\\t"); break;
                default:
                    if (c < 0x20 || c == 0x2028 || c == 0x2029) {
                        b.append(String.format("\\u%04x", (int) c));
                    } else {
                        b.append(c);
                    }
            }
        }
        return b.toString();
    }

    // --------------------------------------------------------------- http ---
    /** HTTP/1.1 поверх Socket: обходит политику cleartext для targetSdk 28+. */
    private String http(String method, String url, String body) throws Exception {
        URL u = new URL(url);
        String host = u.getHost();
        int port = u.getPort() > 0 ? u.getPort() : 80;
        String path = u.getFile();
        if (path == null || path.length() == 0) path = "/";

        Socket socket = new Socket();
        socket.connect(new InetSocketAddress(host, port), 5000);
        socket.setSoTimeout(30000);
        try {
            byte[] payload = body == null ? null : body.getBytes("UTF-8");
            StringBuilder head = new StringBuilder();
            head.append(method).append(' ').append(path).append(" HTTP/1.1\r\n");
            head.append("Host: ").append(host).append(':').append(port).append("\r\n");
            head.append("Accept: application/json\r\n");
            head.append("Connection: close\r\n");
            if (payload != null) {
                head.append("Content-Type: application/json\r\n");
                head.append("Content-Length: ").append(payload.length).append("\r\n");
            }
            head.append("\r\n");

            OutputStream out = socket.getOutputStream();
            out.write(head.toString().getBytes("UTF-8"));
            if (payload != null) out.write(payload);
            out.flush();

            InputStream in = socket.getInputStream();
            ByteArrayOutputStream raw = new ByteArrayOutputStream();
            int match = 0;
            while (true) {
                int c = in.read();
                if (c < 0) break;
                raw.write(c);
                if (c == '\r') match = (match == 2) ? 3 : 1;
                else if (c == '\n') match = (match == 1) ? 2 : (match == 3 ? 4 : 0);
                else match = 0;
                if (match == 4) break;
                if (raw.size() > 65536) throw new Exception("слишком длинные заголовки");
            }

            String headText = raw.toString("UTF-8");
            int split = headText.indexOf("\r\n\r\n");
            if (split < 0) throw new Exception("нет конца заголовков");
            String[] lines = headText.substring(0, split).split("\r\n");
            if (lines.length == 0) throw new Exception("пустой ответ");
            String[] status = lines[0].split(" ", 3);
            int code = Integer.parseInt(status[1]);

            Map<String, String> headers = new HashMap<String, String>();
            for (int i = 1; i < lines.length; i++) {
                int colon = lines[i].indexOf(':');
                if (colon > 0) {
                    headers.put(lines[i].substring(0, colon).trim().toLowerCase(Locale.US),
                            lines[i].substring(colon + 1).trim());
                }
            }

            byte[] decoded;
            if ("chunked".equalsIgnoreCase(headers.get("transfer-encoding"))) {
                decoded = readChunked(in);
            } else if (headers.containsKey("content-length")) {
                int len = Integer.parseInt(headers.get("content-length"));
                decoded = readExactly(in, len);
            } else {
                decoded = readAll(in);
            }
            String text = new String(decoded, "UTF-8");
            if (code >= 400) throw new Exception("HTTP " + code + ": " + text);
            return text;
        } finally {
            try { socket.close(); } catch (Exception ignored) { }
        }
    }

    private static byte[] readExactly(InputStream in, int len) throws Exception {
        byte[] buf = new byte[len];
        int off = 0;
        while (off < len) {
            int n = in.read(buf, off, len - off);
            if (n < 0) break;
            off += n;
        }
        if (off < len) throw new Exception("короткий ответ: " + off + "/" + len);
        return buf;
    }

    private static byte[] readAll(InputStream in) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n;
        while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
        return out.toByteArray();
    }

    private static String readLine(InputStream in) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        int c;
        while ((c = in.read()) >= 0) {
            if (c == '\n') break;
            if (c != '\r') out.write(c);
        }
        return out.toString("UTF-8");
    }

    private static byte[] readChunked(InputStream in) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        while (true) {
            String line = readLine(in);
            if (line.length() == 0) continue;
            int semi = line.indexOf(';');
            if (semi >= 0) line = line.substring(0, semi);
            int size = Integer.parseInt(line.trim(), 16);
            if (size == 0) break;
            out.write(readExactly(in, size));
            readLine(in);
        }
        return out.toByteArray();
    }

    // -------------------------------------------------------------- base64 ---
    private static final char[] B64 =
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".toCharArray();

    private static byte[] base64url(String s) throws Exception {
        String t = s.replace('-', '+').replace('_', '/');
        int pad = (4 - t.length() % 4) % 4;
        StringBuilder b = new StringBuilder(t);
        for (int i = 0; i < pad; i++) b.append('=');
        t = b.toString();

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        int acc = 0, bits = 0;
        for (int i = 0; i < t.length(); i++) {
            char c = t.charAt(i);
            if (c == '=') break;
            int v = index(c);
            if (v < 0) throw new Exception("bad base64");
            acc = (acc << 6) | v;
            bits += 6;
            if (bits >= 8) {
                bits -= 8;
                out.write((acc >> bits) & 0xff);
            }
        }
        return out.toByteArray();
    }

    private static int index(char c) {
        for (int i = 0; i < B64.length; i++) if (B64[i] == c) return i;
        return -1;
    }
}
