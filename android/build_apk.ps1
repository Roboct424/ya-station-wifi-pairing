# Сборка APK без Android SDK и Gradle.
#   1) python fetch_tools.py     (скачает aapt2, d8, android.jar, apksig, ecj)
#   2) powershell -File build_apk.ps1
#
# Требуется только JRE 8+ (javac не нужен: компилируем ecj, dex — d8, подпись — apksig).
$ErrorActionPreference = 'Stop'
$proj = $PSScriptRoot
$tools = Join-Path $proj '.tools'
$build = Join-Path $proj 'build'

$androidJar = Join-Path $tools 'android.jar'
$r8 = Join-Path $tools 'r8.jar'
$aapt2 = Join-Path $tools 'aapt2.exe'
$apksig = Join-Path $tools 'apksig.jar'
$ecj = Join-Path $tools 'ecj.jar'

foreach ($f in @($androidJar, $r8, $aapt2, $apksig, $ecj)) {
    if (-not (Test-Path $f)) { throw "нет $f - запустите python fetch_tools.py" }
}

if (Test-Path $build) { Remove-Item $build -Recurse -Force }
New-Item -ItemType Directory -Force -Path (Join-Path $build 'classes'), (Join-Path $build 'dex') | Out-Null

# ассеты: то же веб-приложение, что и в tools/
$assets = Join-Path $build 'assets'
New-Item -ItemType Directory -Force -Path $assets | Out-Null
Copy-Item (Join-Path $proj '..\tools\sound_code.html') (Join-Path $assets 'index.html') -Force

Write-Host "aapt2 link..."
& $aapt2 link -o (Join-Path $build 'base.apk') -I $androidJar --manifest (Join-Path $proj 'AndroidManifest.xml') -A $assets
if ($LASTEXITCODE -ne 0) { throw "aapt2 link failed" }

Write-Host "ecj (javac-замена)..."
$rt = Join-Path $env:JAVA_HOME 'lib\rt.jar'
if (-not (Test-Path $rt)) {
    $candidates = @(
        (Join-Path $env:ProgramFiles 'Java\jre1.8.0_51\lib\rt.jar'),
        (Join-Path $env:ProgramFiles 'Java\jdk1.8.0_51\jre\lib\rt.jar')
    ) | Where-Object { Test-Path $_ }
    if (-not $candidates) { throw "не найден rt.jar (нужна Java 8)" }
    $rt = $candidates[0]
}
& java -jar $ecj -source 8 -target 8 -nowarn -bootclasspath $rt -cp $androidJar -d (Join-Path $build 'classes') (Join-Path $proj 'src\com\rig\soundcode\MainActivity.java')
if ($LASTEXITCODE -ne 0) { throw "ecj failed" }

$classes = Get-ChildItem (Join-Path $build 'classes') -Recurse -Filter '*.class' | ForEach-Object { $_.FullName }
Write-Host "d8..."
& java -cp $r8 com.android.tools.r8.D8 --lib $androidJar --lib $rt --min-api 16 --output (Join-Path $build 'dex') @classes
if ($LASTEXITCODE -ne 0) { throw "d8 failed" }

Write-Host "упаковка dex..."
python -c "import zipfile,sys
apk,dex=sys.argv[1],sys.argv[2]
with zipfile.ZipFile(apk,'a',zipfile.ZIP_DEFLATED) as z: z.write(dex,'classes.dex')
print('classes.dex добавлен')" (Join-Path $build 'base.apk') (Join-Path $build 'dex\classes.dex')
if ($LASTEXITCODE -ne 0) { throw "dex pack failed" }

# ключ (PEM) — генерируется один раз
$keyPem = Join-Path $proj 'rig.key.pem'
$crtPem = Join-Path $proj 'rig.crt.pem'
if (-not (Test-Path $keyPem)) {
    Write-Host "генерирую ключ подписи..."
    python -c "from cryptography import x509; from cryptography.x509.oid import NameOID; from cryptography.hazmat.primitives import hashes, serialization; from cryptography.hazmat.primitives.asymmetric import rsa; import datetime
key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,u'Station Sound Code')])
now=datetime.datetime.now(datetime.timezone.utc)
cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(days=1)).not_valid_after(now+datetime.timedelta(days=3650)).add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True).sign(key,hashes.SHA256()))
open('rig.key.pem','wb').write(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
open('rig.crt.pem','wb').write(cert.public_bytes(serialization.Encoding.PEM))
print('ключ создан')"
}

Write-Host "подпись (v1+v2 через apksig)..."
New-Item -ItemType Directory -Force -Path (Join-Path $build 'signer') | Out-Null
& java -jar $ecj -source 8 -target 8 -nowarn -bootclasspath $rt -cp $apksig -d (Join-Path $build 'signer') (Join-Path $proj 'signer\Signer.java')
if ($LASTEXITCODE -ne 0) { throw "signer compile failed" }

$out = Join-Path $proj 'SoundCode.apk'
& java -cp "$(Join-Path $build 'signer');$apksig" Signer (Join-Path $build 'base.apk') $out $keyPem $crtPem
if ($LASTEXITCODE -ne 0) { throw "signing failed" }

Get-Item $out | Select-Object FullName, Length
Write-Host "ГОТОВО: $out"
