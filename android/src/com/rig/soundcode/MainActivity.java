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
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Оболочка вокруг tools/sound_code.html (он же ассет index.html).
 *
 * Мост для вкладки «Wi-Fi (AP)» сделан через JSONP, а не через
 * @JavascriptInterface: в Maven-stub android.jar (API 16) нет
 * android.webkit.JavascriptInterface, org.json и javax.crypto.
 * Поэтому Java умеет только локальный HTTP, а RSA/PKCS1 и JSON
 * считает сам HTML на BigInt.
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
    private String read(InputStream in) throws Exception {
        if (in == null) return "";
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n;
        while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
        in.close();
        return out.toString("UTF-8");
    }

    private String http(String method, String url, String body) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setRequestMethod(method);
        c.setConnectTimeout(5000);
        c.setReadTimeout(30000);
        c.setRequestProperty("Accept", "application/json");
        if (body != null) {
            c.setDoOutput(true);
            c.setRequestProperty("Content-Type", "application/json");
            byte[] data = body.getBytes("UTF-8");
            OutputStream os = c.getOutputStream();
            os.write(data);
            os.close();
        }
        int code = c.getResponseCode();
        InputStream in = code >= 400 ? c.getErrorStream() : c.getInputStream();
        String text = read(in);
        if (code >= 400) throw new Exception("HTTP " + code + ": " + text);
        return text;
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
