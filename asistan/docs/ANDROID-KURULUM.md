# Android'de KASA Asistan — Kurulum

> ### 👉 Bilgisayarın yoksa **[ANDROID-TELEFON.md](ANDROID-TELEFON.md)** dosyasını kullan.
> O kılavuz tamamen telefonla yapılır: Termux + llama.cpp resmî Android ikilisi +
> Gemma 4 GGUF, **derleme yok**, ~25 dakika.

Seçilen model: **Gemma 4 E4B** (Apache 2.0). Telefonda iki motor seçeneği var:

| Motor | Ne zaman | Derleme |
|---|---|---|
| **llama.cpp resmî Android ikilisi** (`llama-server`) | **Önerilen** — her Android'de | ❌ yok |
| Google AI Edge **LiteRT-LM** | GPU/NPU hızlandırma, hazır uygulama | ❌ yok |

Bu dosya üç yolu anlatır. Bilgisayarsız olan **Yol B**'dir.

| Yol | Bilgisayar gerekir? | Ne elde edersin |
|---|---|---|
| **A. Hazır uygulama (LiteRT)** | ❌ hayır | 10 dakikada çalışan sohbet; KASA'nın araçları yok |
| **B. Termux + bu depo** ⭐ | ❌ hayır | Tam KASA: araçlar, hafıza, arayüz — **önerilen** |
| **C. Kendi Android uygulaman (Kotlin)** | ✅ evet (Android Studio) | Dağıtılabilir APK |

---

## A. Hazır uygulama (en hızlı)

Modeli indir, uygulamaya ver, sohbet et.

```bash
# bilgisayarda veya Termux'ta
bash asistan/modeller/indir.sh --litertlm
ls -lh asistan/models/gemma-4-E4B-it.litertlm    # ~3.65 GB
```

Dosyayı USB / Google Drive ile telefona at, sonra şu uygulamalardan birini kur:

**Google AI Edge Gallery** (Google'ın kendi uygulaması, ücretsiz)
- Play Store → "Google AI Edge Gallery"
- Gemma 4 E2B/E4B'yi listeden indirebilir veya `.litertlm` dosyasını içe aktarabilir
- Hızlandırma GPU/NPU; S26 Ultra'da E4B ≈ 22 token/s

**Pocket LLM / PocketLM** (LiteRT + GGUF karışık destekler)
- "Model içe aktar" → `.litertlm` dosyasını seç
- Gemma 4 E4B / E2B ve Qwen3-0.6B destekli

**PocketPal AI** (GGUF, topluluk favorisi)
- GGUF yolu için: `bash asistan/modeller/indir.sh` (QAT Q4 dosyası, ~5.2 GB)
- Bu durumda aşağıdaki B yolundaki `models/` klasörüne de aynı dosyayı koyabilirsin

> ⚠️ Bu uygulamalar **KASA'nın kişiliğini bilmez** — genel amaçlı sohbet edersin.
> KASA olması için sistem komutunu (aşağıda) "system prompt" alanına yapıştır.

### KASA sistem komutu (kopyala-yapıştır)

```
Sen KASA, kullanıcının kişisel yapay zekâ asistanısın. Telefonda, tamamen
çevrimdışı çalışıyorsun.

DİL: Kullanıcı hangi dilde yazarsa o dilde yanıt ver. Türkçe soruya Türkçe,
doğal ve düzgün bir Türkçe ile yanıt ver; çeviri kokan cümle kurma. Kod
değişken adları İngilizce kalabilir, açıklamalar Türkçe olur.

KİŞİLİK: Kullanıcıya "sen" diye hitap et. Sıcak ama net ol. "Harika soru!"
gibi dolgu yok, doğrudan cevaba gir. Bilmiyorsan "bilmiyorum" de, uydurma.
Emin olmadığın sürüm/tarih/API adını verirken "kontrol etmelisin" de.

KISA TUT: Sormadıkça 200 kelimeyi geçme. Adım adım anlatacaksan numaralı
liste kullan. Kod istenirse dosyayı TAM ver, "...devamı" deme.

KOD: Önce tek cümlede ne yapacağını söyle, sonra kodu ver. Kod bloğunda dili
belirt. Hata ayıklarken önce sebebi söyle, sonra düzeltmeyi ver.
```

İstersen `profil:` alanını `asistan.yaml` içinden değiştirip bu metni
`python3 -c "from kasa_asistan.persona import *; print(varsayilan_kisilik('4.5B').sistem_komutu())"`
ile yeniden üretebilirsin.

---

## B. Termux + bu depo (tam KASA) — bilgisayar GEREKMEZ

Tam adım adım anlatım: **[ANDROID-TELEFON.md](ANDROID-TELEFON.md)**. Özeti:

```bash
# 1) Termux (F-Droid sürümü!)
pkg update -y && pkg install -y python curl tar git

# 2) Kodu al
git clone -b arena/64436ca2-kasa-masa-oyunu \
  https://github.com/oyunlitee-cell/KASA-MASA-OYUNU.git
cd KASA-MASA-OYUNU

# 3) Tek komut: llama.cpp ikilisi + model + doğrulama
bash asistan/android/kur.sh          # 8 GB+ RAM
bash asistan/android/kur.sh e2b      # 4-6 GB RAM

# 4) Kontrol ve başlat
bash asistan/android/kontrol.sh
bash asistan/android/baslat.sh       # http://127.0.0.1:8080
```

**Neden `pip install llama-cpp-python` yok?** Telefonda C++ derlemek 15-30 dakika
sürer ve sık başarısız olur. Bunun yerine llama.cpp'nin **resmî Android arm64
ikilisi** (77 MB) indirilir; modeli o yükler, Python tarafı saf standart kütüphane kalır.
Derleme yolu hâlâ mümkün (yedek): `pkg install cmake clang && pip install llama-cpp-python`
— llama-cpp-python 0.3.36'nın içindeki llama.cpp `gemma4` mimarisini destekliyor,
ama bu yol yavaş ve kırılgandır.

### Arayüzü telefonda açmak

`baslat.sh` bunu kendisi yapar ve tarayıcıyı açar: **http://127.0.0.1:8080**

Aynı Wi-Fi'deki başka cihazdan açmak için `baslat.sh` yerine elle:
```bash
KASA_LLAMA_SUNUCU=http://127.0.0.1:8081 PYTHONPATH=src \
  python3 -m kasa_asistan.cli --sunucu --host 0.0.0.0 --port 8080
```
(Güvenlik: `baslat.sh` her zaman `--host 127.0.0.1` kullanır — telefonda arayüz
LAN'a açılmaz. Bilinçli olarak açmak istiyorsan `--host 0.0.0.0` ver.)

### Termux'ta bilinmesi gerekenler

* **Pil optimizasyonu:** Ayarlar → Uygulamalar → Termux → Pil → Kısıtlanmamış.
* **Isınma:** 10-15 dakika sonra ısınır; kılıfı çıkar, şarjda kullanma.
* **RAM:** 6 GB ve altındaysan E2B kullan.
* **Hız beklentisi:** CPU'da gerçekçi **3-8 token/s**. Bir paragraf ~20-40 sn.

## C. Kendi Android uygulaman (Kotlin + LiteRT-LM)

> ⚠️ Bu yol **bilgisayar** (Android Studio) gerektirir. Telefon-only hedefi için B'yi kullan.

Dağıtılabilir bir APK istiyorsan doğru yol bu. Android Studio **Quail 4**
(Eylül 2026) Gemma 4'ü yerleşik olarak destekliyor.

### 1. Bağımlılık

`gradle/libs.versions.toml`:

```toml
[versions]
kotlin = "2.2.0"        # LiteRT-LM Kotlin 2.2+ istiyor
litertlm = "0.10.0"

[libraries]
litertlm = { group = "com.google.ai.edge.litertlm", name = "litertlm-android", version.ref = "litertlm" }
```

`app/build.gradle.kts`:

```kotlin
android { /* ... */ }
dependencies {
    implementation(libs.litertlm)
}
```

### 2. Modeli pakete koyma (önerilen: ilk açılışta indir)

Modeli `assets/` içine koymak APK'yı 3.6 GB yapar — kimse indirmez.
İlk açılışta indirip `filesDir`'e yaz:

```kotlin
private const val MODEL_URL =
    "https://huggingface.co/litert-community/gemma-4-E4B-it-litert-lm/resolve/main/gemma-4-E4B-it.litertlm"
```

### 3. Motoru başlatma

```kotlin
import com.google.ai.edge.litertlm.Engine
import com.google.ai.edge.litertlm.EngineConfig
import com.google.ai.edge.litertlm.Backend

class KasaMotor(private val modelDosyasi: File) {

    private val engine = Engine(
        EngineConfig(
            modelPath = modelDosyasi.absolutePath,
            backend = Backend.GPU,          // GPU yoksa Backend.CPU'ya düş
            maxTokens = 4096,
            cacheDir = null,
        )
    )

    suspend fun yanitla(sistemKomutu: String, kullanici: String): String =
        engine.createSession(
            systemInstruction = sistemKomutu,
            temperature = 1.0f,             // Gemma 4 önerilen
            topP = 0.95f,
            topK = 64,
        ).use { oturum ->
            oturum.sendMessage(kullanici)
        }
}
```

> SDK sürümüne göre `EngineConfig`/`Session` imzaları değişebilir.
> Güncel imza için: <https://developers.google.com/edge/litert-lm/android>

### 4. Sistem komutunu gömme

`assets/kasa_sistem.txt` dosyasına A bölümündeki metni koy, açılışta oku.
Asistanın kişiliğini değiştirmek istediğinde tek dosya düzenlemen yeter.

### 5. Sesli asistan (opsiyonel)

Gemma 4 E4B **ses girdisi** alıyor. Mikrofon → 16 kHz PCM → LiteRT-LM
multimodal oturumu ile akış kurulabilir. Bu depoda bu kısım yok; ilk sürümde
yazılı sohbetle başlamanı öneririm.

---

## Hangi yolu seçmeli?

* **Sadece çalışsın istiyorum, kod yok** → A
* **KASA'nın kişiliği ve araçları olsun, bilgisayar kullanmayayım** → **B** ⭐
* **Başkasına kurulabilir bir APK yapıyorum (bilgisayarım var)** → C

---

## Sorun giderme

| Belirti | Sebep / çözüm |
|---|---|
| `Model dosyası yok` | `bash asistan/modeller/indir.sh` çalıştır |
| `unknown model architecture` | llama.cpp eski derleme. Qwen3.5 için güncel gerekir: `pip install -U llama-cpp-python` |
| Uygulama açılışta kapanıyor | Model RAM'e sığmıyor — E2B'ye geç veya `baglam_penceresi` düşür (4096) |
| Çok yavaş (1-2 token/s) | CPU yolu; GPU arka ucunu dene veya E2B'ye geç |
| Türkçe yanıtlar İngilizce karışık | `eval/turkce_degerlendir.py` ile ölç, `persona.py` kurallarını sıkılaştır |
| Yanıtlar saçmalıyor, tekrar döngüsü | `maks_yeni_token` düşür (512), `temp` 0.8'e indir |
