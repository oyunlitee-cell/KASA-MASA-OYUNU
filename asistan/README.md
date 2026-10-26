# KASA Asistan

Türkçe konuşan, **tamamen çevrimdışı** çalışan kişisel yapay zekâ asistanı.
Sohbet eder, kod yazar ve hata ayıklar, dosyalarında çalışabilir.

**Seçilen model: Gemma 4 E4B · Apache 2.0 · 128K bağlam**

📱 **Telefonda, bilgisayarsız kurulum: [docs/ANDROID-TELEFON.md](docs/ANDROID-TELEFON.md)**
(3 komut: `kur.sh` → `kontrol.sh` → `baslat.sh`, derleme yok)
→ Model seçim gerekçesi ve sınırlar: [docs/MODEL-SECIMI.md](docs/MODEL-SECIMI.md)

---

## 📱 Telefonda (önerilen)

```bash
pkg install -y python curl tar git            # Termux
git clone https://github.com/oyunlitee-cell/KASA-MASA-OYUNU.git && cd KASA-MASA-OYUNU
bash asistan/android/kur.sh                   # llama.cpp ikilisi + Gemma 4 + doğrulama
bash asistan/android/baslat.sh                # tarayıcı açılır: 127.0.0.1:8080
```

Ayrıntı: **[docs/ANDROID-TELEFON.md](docs/ANDROID-TELEFON.md)** · Derleme yok, bilgisayar yok.

## Masaüstünde dene

Model olmadan da arayüz çalışır (demo yanıtlarıyla):

```bash
cd asistan
PYTHONPATH=src python3 -m kasa_asistan.cli --sunucu --port 8080
# tarayıcı: http://localhost:8080
```

Gerçek modelle:

```bash
bash asistan/modeller/indir.sh              # Gemma 4 E4B, ~5.2 GB (GGUF QAT)
cd asistan
PYTHONPATH=src python3 -m kasa_asistan.cli  # terminal sohbeti
```

Gereken: Python 3.10+, `llama-cpp-python` (`python3 -m pip install llama-cpp-python`).
Başka bağımlılık yok — sunucu ve YAML ayrıştırıcı standart kütüphaneyle yazıldı,
böylece Termux'ta sorunsuz kurulur.

---

## Ne yapabilir?

| | |
|---|---|
| 📱 **Telefonda çalışır** | llama.cpp resmî Android ikilisi + Gemma 4; derleme gerekmez |
| ⚡ **Gerçek akış** | Token token yazma — 5 tok/s'de bile ilk kelime ~1 sn'de görünür |
| 💬 **Türkçe sohbet** | Doğal, çeviri kokmayan Türkçe; kullanıcının diline uyar |
| 🧑‍💻 **Kod yazma** | Tam dosya üretir, "...devamı" demez; LiveCodeBench v6 = 52.0 (4B sınıfının en iyisi) |
| 🐛 **Hata ayıklama** | Hatanın sebebini söyler, düzeltilmiş kodu verir |
| 🛠️ **Dosyada çalışma** | `dosya_oku`, `dosya_yaz`, `dosya_liste`, `ara`, `komut` araçları |
| 🧠 **Hafıza** | `hafiza.md` — senin hakkında öğrendiklerini kalıcı tutar |
| 🌐 **Arayüz** | Telefonda çalışan, akışlı (streaming) Türkçe web sohbet arayüzü |
| 🔌 **OpenAI uyumlu API** | `/v1/chat/completions` — Continue, Open WebUI, SillyTavern vb. |
| 🔒 **Çevrimdışı** | Hiçbir istek cihazdan çıkmaz |

## Kullanım

```bash
# terminal sohbeti
PYTHONPATH=src python3 -m kasa_asistan.cli

# model seç
PYTHONPATH=src python3 -m kasa_asistan.cli --model gemma4-e2b

# web sunucusu + arayüz
PYTHONPATH=src python3 -m kasa_asistan.cli --sunucu --port 8080

# tek soru
PYTHONPATH=src python3 -m kasa_asistan.cli --mesaj "Python'da liste nasıl ters çevrilir?"

# araçları kapat (daha hızlı, daha güvenli)
PYTHONPATH=src python3 -m kasa_asistan.cli --arac-kapali
```

Sohbet içi komutlar: `/durum` `/kaydet` `/hafiza` `/hatırla <bilgi>` `/q`

### OpenAI uyumlu uç

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4-e4b","messages":[{"role":"user","content":"Merhaba!"}]}'
```

## Modeller

| Anahtar | Model | Lisans | Boyut | Ne zaman |
|---|---|---|---|---|
| `gemma4-e4b` | Gemma 4 E4B IT | Apache-2.0 | 3.65 GB | **Varsayılan** — 6-8 GB RAM |
| `gemma4-e2b` | Gemma 4 E2B IT | Apache-2.0 | 2.58 GB | 4-6 GB RAM'li telefonlar, daha hızlı |
| `qwen35-4b` | Qwen3.5-4B | Apache-2.0 | ~2.7 GB | Deneysel — kağıt üstü daha güçlü, çalışma zamanı olgun değil |
| `qwen3-4b` | Qwen3-4B-Inst-2507 | Apache-2.0 | 2.65 GB | Uyumluluk yedeği — klasik transformer, her yerde çalışır |

Model değiştirmek için `asistan.yaml` içindeki `varsayilan_model` alanını
düzenle veya `--model` ver. Yeni model eklemek: `modeller:` altına aynı
şablonla bir blok ekle, `indir.sh` içine URL'sini yaz.

## Kişiselleştirme

`asistan.yaml` → `profil:` bölümü: ad, hitap (sen/siz), ton.
Kişilik kuralları ve araç tanımları: `src/kasa_asistan/persona.py`.

```yaml
profil:
  ad: "KASA"
  kullanici_ad: "Patron"
  hitap: "sen"          # veya "siz"
  ton: "sıcak ama net"
```

## Türkçe kalitesini ölç

Bu modeller için yayınlanmış Türkçe benchmark **yok**. Kendin ölç:

```bash
PYTHONPATH=src python3 eval/turkce_degerlendir.py --puanla
```

18 Türkçe soru (sohbet, deyim, kod, talimat uyumu) sorar; Türkçe karakter
oranı, İngilizce kalıp kaçağı, kod bloğu üretimi ve yanıt süresini raporlar.

## Test

```bash
PYTHONPATH=src python3 -m pytest tests -q      # 22 test
```

Araç `tests/test_llama_server.py` gerçek bir HTTP sunucusu ayağa kaldırıp
llama-server istemcisini, akışı ve araç döngüsünü soket üzerinden doğrular.

## Yapı

```
asistan/
├── asistan.yaml              # yapılandırma (model, kişilik, araçlar, sunucu)
├── src/kasa_asistan/
│   ├── persona.py            # Türkçe sistem komutu + araç tanımları
│   ├── config.py             # YAML yükleyici (bağımlılıksız)
│   ├── backends.py           # llama.cpp / LiteRT-LM / demo arka uçları
│   ├── tools.py              # dosya + komut araçları (sandbox'lı)
│   ├── agent.py              # sohbet döngüsü, araç döngüsü, hafıza
│   ├── server.py             # HTTP sunucusu (stdlib) + OpenAI uç noktası
│   └── cli.py                # terminal arayüzü
├── web/index.html            # Türkçe sohbet arayüzü (tek dosya, bağımlılıksız)
├── android/
│   ├── kur.sh                # telefonda tek komut kurulum (llama.cpp + model + test)
│   ├── baslat.sh             # llama-server + arayüz + tarayıcı
│   ├── durdur.sh             # süreçleri kapat
│   └── kontrol.sh            # 6 başlıkta sağlık kontrolü
├── modeller/indir.sh         # model indirici (masaüstü)
├── eval/turkce_degerlendir.py# Türkçe kalite ölçümü
├── tests/test_smoke.py       # 12 test
└── docs/
    ├── MODEL-SECIMI.md       # model karşılaştırma raporu + kaynaklar
    ├── ANDROID-TELEFON.md    # ⭐ bilgisayarsız kurulum
    └── ANDROID-KURULUM.md    # üç kurulum yolu (LiteRT / Termux / Kotlin)
```

## Güvenlik

Model 4B ve deneysel — bu yüzden araçlar bilinçli olarak kısıtlı:

* Kabuk serbest değil; sadece `asistan.yaml → araclar.izinli_komutlar` çalışır.
* `git push`, `git remote` engelli.
* Tüm dosya işlemleri tek bir çalışma dizinine kilitli; `../` kaçışı reddedilir.
* Yazma öncesi `.bak` yedeği alınır.
* Araç döngüsü en fazla 3 tur; bozuk araç çağrıları yok sayılır.

## Sınırlar

Ayrıntılı liste: [docs/MODEL-SECIMI.md §7](docs/MODEL-SECIMI.md). Kısaca:

* 4B model **otonom bir yazılım ajanı değil**. Tek dosya/ küçük modül yazar,
  20 dosyalık bir depoyu tek seferde tutarlı kuramaz.
* Telefonda CPU'da gerçekçi hız 4-10 token/s. Hızlı istiyorsan LiteRT-LM
  (GPU/NPU) yolunu kullan — bkz. Android kılavuzu.
* Türkçe kalitesi bu repoda ölçülmedi; `eval/` ile kendin ölçmelisin.
* Sesli giriş/çıkış henüz yok (model ses girdisini destekliyor, arayüz yok).
* Telefonda ölçülen hız cihaza göre **3-8 token/s**; bu bir "hızlı sohbet" değil,
  "cebinde çalışan" bir asistan. Beklentiyi buna göre kur.

## Lisans

Kod: bu deponun lisansına tabidir.
Model ağırlıkları: **Gemma 4 → Apache 2.0** (Google DeepMind).
Apache 2.0, ticari kullanım ve değiştirmeye izin verir; lisans ve telif
bildirimini koruman gerekir.
