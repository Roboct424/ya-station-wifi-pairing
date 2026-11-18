import com.android.apksig.ApkSigner;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.KeyFactory;
import java.security.PrivateKey;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.security.spec.PKCS8EncodedKeySpec;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collections;
import java.util.List;

public class Signer {
    private static byte[] pemBody(String path) throws Exception {
        String text = new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.US_ASCII);
        StringBuilder sb = new StringBuilder();
        for (String line : text.split("\\r?\\n")) {
            if (line.startsWith("-----")) {
                continue;
            }
            sb.append(line.trim());
        }
        return Base64.getDecoder().decode(sb.toString());
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 4) {
            System.out.println("usage: Signer in.apk out.apk private.pem cert.pem");
            return;
        }
        byte[] keyDer = pemBody(args[2]);
        PrivateKey key = KeyFactory.getInstance("RSA")
                .generatePrivate(new PKCS8EncodedKeySpec(keyDer));

        CertificateFactory cf = CertificateFactory.getInstance("X.509");
        X509Certificate cert;
        FileInputStream in = new FileInputStream(args[3]);
        try {
            cert = (X509Certificate) cf.generateCertificate(in);
        } finally {
            in.close();
        }

        List<X509Certificate> certs = new ArrayList<X509Certificate>();
        certs.add(cert);

        ApkSigner.SignerConfig cfg =
                new ApkSigner.SignerConfig.Builder("CERT", key, certs).build();
        new ApkSigner.Builder(Collections.singletonList(cfg))
                .setInputApk(new File(args[0]))
                .setOutputApk(new File(args[1]))
                .setV1SigningEnabled(true)
                .setV2SigningEnabled(true)
                .build()
                .sign();
        System.out.println("signed: " + args[1]);
    }
}
