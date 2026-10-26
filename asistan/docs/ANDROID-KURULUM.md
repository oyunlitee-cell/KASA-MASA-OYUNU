# Android'de KASA Asistan — Kurulum

Seçilen model: **Gemma 4 E4B** (Apache 2.0) · Motor: **Google AI Edge LiteRT-LM**
E2B (2.58 GB) daha zayıf telefonlar için, E4B (3.65 GB) normal telefonlar için.

Telefonda üç farklı yol var. Aşağıdan kendine uygun olanı seç.

| Yol | Zorluk | Ne elde edersin |
|---|---|---|
| **A. Hazır uygulama** | ⭐ | 10 dakikada çalışan sohbet. Kod yok. |
| **B. Termux + bu depo** | ⭐⭐ | Python asistanı, araçlar, kendi sunucun, tam kontrol |
| **C. Kendi Android uygulaman (Kotlin)** | ⭐⭐⭐⭐ | LiteRT-LM SDK ile gerçek bir APK |

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

## B. Termux + bu depo (tam KASA)

Telefonda Python, araçlar, sunucu ve tarayıcı arayüzü. **Tavsiye edilen yol.**

```bash
# 1) Termux kur (F-Droid sürümü önerilir; Play Store sürümü eski)
#    https://f-droid.org/packages/com.termux/

pkg update && pkg upgrade -y
pkg install -y git python cmake clang make curl

# 2) Depoyu al
git clone https://github.com/oyunlitee-cell/KASA-MASA-OYUNU.git
cd KASA-MASA-OYUNU

# 3) Python paketi
python -m pip install llama-cpp-python
#    Derleme 10-25 dk sürer (telefonda normal). Hata alırsan:
#    CMAKE_ARGS="-DGGML_OPENMP=OFF" python -m pip install llama-cpp-python

# 4) Modeli indir (Wi-Fi'de yap, ~5.2 GB)
bash asistan/modeller/indir.sh

# 5) Çalıştır
cd asistan
PYTHONPATH=src python -m kasa_asistan.cli
```

### Arayüzü telefonda açmak

```bash
cd asistan
PYTHONPATH=src python -m kasa_asistan.cli --sunucu --port 8080
```

Sonra telefonun tarayıcısında: **http://localhost:8080**

Aynı Wi-Fi'deki bilgisayardan açmak için `asistan.yaml` → `sunucu.paylas_ag: true`
ve telefonun IP'si (`ifconfig` veya `ip addr`) ile `http://192.168.x.x:8080`.

### Termux'ta bilinmesi gerekenler

* **Pil optimizasyonu:** Termux'u "pil optimizasyondan muaf" tut, yoksa
  arka planda ölür: Ayarlar → Uygulamalar → Termux → Pil → Kısıtlanmamış.
* **Isınma:** 4B model CPU'da 20-30 dakika sonra telefonu ısıtır. Uzun
  sohbetlerde `--model gemma4-e2b` daha konforlu.
* **RAM:** 6 GB'lık telefondaysan E2B kullan; E4B bellek yetersizliğinden
  Android tarafından öldürülebilir.
* **Hız beklentisi:** 8 çekirdekli orta seviye bir telefonda GGUF Q4 ile
  gerçekçi olarak **4-10 token/s**. Yani bir paragraf ~15-40 saniye.
  LiteRT-LM (A yolu) GPU/NPU kullandığı için belirgin şekilde daha hızlı.

---

## C. Kendi Android uygulaman (Kotlin + LiteRT-LM)

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

* **Sadece çalışsın istiyorum** → A
* **KASA'nın kişiliği, araçları, kendi sunucum olsun** → B
* **Başkasına kurulabilir bir uygulama yapıyorum** → C

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
