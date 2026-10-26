# Telefonda KASA — bilgisayarsız kurulum

Bu kılavuz **sadece telefonla** yapılır. Bilgisayar, kablo, ADB, Android Studio yok.
Toplam süre: ~25 dakika (çoğu indirme).

**Mimari:** `KASA (Python)  ──HTTP──▶  llama-server (llama.cpp)  ──▶  Gemma 4 E4B GGUF`

Neden böyle: telefonun kendi CPU'sunda çalışan resmî llama.cpp ikilisi modeli yükler,
Python tarafı sadece arayüz ve araçlar için çalışır. **Telefonda derleme yapılmaz** —
pip ile C++ derlemek Termux'ta 15-30 dakika sürer ve sık sık patlar; bu yol o riski kaldırır.

| | |
|---|---|
| Model | Gemma 4 E4B IT QAT Q4_0 (Apache-2.0) — 5.2 GB |
| Motor | llama.cpp resmî Android arm64 ikilisi — 77 MB, derleme yok |
| RAM | 8 GB önerilir · 6 GB sınırda · 4-6 GB ise **E2B** kullan (3.4 GB) |
| Boş alan | ~7 GB |
| İnternet | Sadece kurulumda (Wi-Fi). Sonrası tamamen çevrimdışı |

---

## Adım 0 — Kodu telefona getir

Kod, **herkese açık** bir depoda duruyor — telefonda GitHub şifresi/token gerekmez:

```
https://github.com/oyunlitee-cell/kasa-asistan
```

```bash
git clone https://github.com/oyunlitee-cell/kasa-asistan.git
cd kasa-asistan
```

Herkese açık olduğunu doğrulamak istersen: telefonun tarayıcısında **gizli sekmede**
(Chrome → ⋮ → Yeni gizli sekme) yukarıdaki adresi aç. Sayfa açılıyorsa şifresiz
erişim çalışıyor demektir. Giriş ekranı çıkarsa bana haber ver.

> Bu depo bir **ayna**: yalnızca `asistan/` klasörünü içerir. Asıl depo
> (`KASA-MASA-OYUNU`) özel kalır. Aynada hiçbir anahtar/şifre yoktur.

## Adım 1 — Termux kur (10 dk, bir kez)

> ⚠️ **Play Store'daki Termux'u KURMA.** O sürüm 2020'de terk edildi ve `pkg` çalışmaz.

1. Tarayıcıda aç: **https://f-droid.org/packages/com.termux/**
2. **Download APK** → kuruluma izin ver → kur.
3. İstersen bir de **Termux:API** kur (ekran kilidini engellemek için; zorunlu değil):
   `https://f-droid.org/packages/com.termux.api/`

Termux'u aç ve şunları çalıştır:

```bash
pkg update -y && pkg upgrade -y
pkg install -y python curl tar termux-api
```

`termux-api` kurulumu hata verirse sorun değil, atla — sadece kolaylık.

**Termux'un arka planda ölmesini engelle:**
Ayarlar → Uygulamalar → Termux → **Pil** → *Kısıtlanmamış* (veya "Pil optimizasyonu: Kapalı").

---

## Adım 2 — Kurulumu çalıştır (15 dk, çoğu indirme)

```bash
cd KASA-MASA-OYUNU
bash asistan/android/kur.sh
```

Betik sırayla şunları yapar ve her adımda ne yaptığını yazar:

| Adım | Ne olur | Süre |
|---|---|---|
| 1 | Termux + arm64 + boş alan denetimi | saniyeler |
| 2 | llama.cpp **resmî Android ikilisini** indirir, açar | ~1 dk |
| 3 | Gemma 4 E4B modelini indirir (5.2 GB, duraklatılabilir) | 5-20 dk |
| 4 | llama-server'ı bir kez açar, **gerçekten yanıt verdiğini test eder** | ~1 dk |
| 5 | `baslat.sh` / `durdur.sh` / `kontrol.sh` başlatıcılarını kurar | saniyeler |

4. adımda şunu görürsen hazırsın:

```
  ✓ MODEL GERÇEKTEN ÇALIŞIYOR
     Yanıt: "content":"Ankara"
```

Bu satır önemli: modelin telefonda gerçekten yüklendiğinin kanıtı. Demo değil.

**RAM'in 6 GB veya altındaysa** küçük modelle kur:
```bash
bash asistan/android/kur.sh e2b
```

---

## Adım 3 — Kontrol et

```bash
bash asistan/android/kontrol.sh
```

6 başlıkta ✓/✗ verir: cihaz, llama.cpp ikilisi, model dosyası (GGUF imzası dahil),
Python tarafı, canlı çıkarım, web arayüzü. Kırmızı ✗ varsa altındaki satır ne
yapman gerektiğini söyler.

---

## Adım 4 — Başlat

```bash
bash asistan/android/baslat.sh
```

Sırayla: model yüklenir (20-60 sn) → arayüz açılır → tarayıcı kendiliğinden açılır.

Adres: **http://127.0.0.1:8080**

Arayüzde sağ üstte şunu görmelisin:
`Gemma 4 E4B IT · cihaz içi model · llama-server · Apache-2.0`

"DEMO modu" yazıyorsa model yüklenmemiş demektir → Adım 2'yi tekrar çalıştır.

**Bu Termux penceresini kapatma.** Asistan o süreç ayakta olduğu sürece çalışır.
Durdurmak için `Ctrl+C`.

---

## Adım 5 — Telefona uygulama gibi ekle

1. Chrome'da `http://127.0.0.1:8080` aç
2. Menü (⋮) → **Ana ekrana ekle**
3. Artık ana ekranda KASA simgesi var, tıklayınca açılır.

> Not: Bu bir PWA kısayolu. Tarayıcı sekmesi gibi açılır ama tam ekran görünür.
> Gerçek bir APK istiyorsan `docs/ANDROID-KURULUM.md` → Yol C (Android Studio gerekir,
> yani bilgisayar ister — bu yüzden önerilmez).

---

## Günlük kullanım

```bash
# başlat
bash ~/KASA-MASA-OYUNU/asistan/android/baslat.sh

# durdur (ya da baslat.sh penceresinde Ctrl+C)
bash ~/KASA-MASA-OYUNU/asistan/android/durdur.sh
```

Kısayol: Termux'ta `~/kasa/baslat` gibi bir kısayol oluşturmak istersen:

```bash
echo 'bash ~/KASA-MASA-OYUNU/asistan/android/baslat.sh' >> ~/.bashrc
```

**Telefonu yeniden başlattığında** her şey sıfırlanır — tekrar `baslat.sh` çalıştır.
Uçak modunda da çalışır (internet gerekmez).

---

## Ne beklemelisin?

| Konu | Gerçekçi değer |
|---|---|
| Hız | Orta seviye telefonda **3-8 token/s** (CPU). Bir paragraf ~20-40 sn |
| İlk yükleme | 20-60 sn (model RAM'e alınıyor) |
| Isınma | 10-15 dk sonra ısınır; kılıfı çıkar, şarjda kullanma |
| Pil | 1000-2000 mAh/saat civarı — 2-3 saat sürekli sohbet |
| RAM | E4B ~4-5 GB kullanır. Arka planda başka uygulama açıkken Android öldürebilir |

**Daha hızlı istiyorsan iki seçenek:**
1. `bash asistan/android/kur.sh e2b` — 3.4 GB, belirgin şekilde hızlı, kod kalitesi düşük
2. `kontrol.sh` çıktısındaki `.so` sayısına bak: Snapdragon varyantı GPU/NPU'yu da
   getirir; `--n-gpu-layers` eklemek için `baslat.sh` içindeki llama-server satırına
   `--n-gpu-layers 99` ekleyebilirsin (cihaza göre değişir, denemek gerekir)

---

## Sorun giderme

| Belirti | Sebep | Çözüm |
|---|---|---|
| `pkg: command not found` | Play Store Termux'u | F-Droid sürümünü kur (Adım 1) |
| `HATA: yeterli boş alan yok` | 7 GB gerekiyor | Yer aç ya da `kur.sh e2b` |
| Adım 4'te "beklenmedik şekilde durdu" | RAM yetersiz veya `.so` bulunamadı | `tail -30 ~/kasa/llama-test.log` · E2B dene |
| `error while loading shared libraries` | paylaşımlı kütüphaneler | `baslat.sh` `LD_LIBRARY_PATH`'i kendisi kurar; yine olmazsa log'u bana gönder |
| Arayüz açılıyor ama "DEMO modu" | model yüklenmemiş | `bash asistan/android/kontrol.sh` → eksik adımı gösterir |
| Tarayıcı açılmıyor | `termux-api` yok | Elle aç: `http://127.0.0.1:8080` |
| Çok yavaş (1-2 token/s) | güç tasarrufu / düşük frekans | Şarjdan çıkar, pil tasarrufunu kapat, E2B'ye geç |
| Yanıtlar yarım kalıyor | bağlam/bellek | `asistan.yaml` → `maks_yeni_token: 512`, `baglam_penceresi: 2048` |
| Termux kendiliğinden kapanıyor | pil optimizasyonu | Adım 1'deki pil ayarını yap |
| Türkçe yanıtlar İngilizce karışık | model davranışı | `PYTHONPATH=src python3 eval/turkce_degerlendir.py --puanla` ile ölç |

Log dosyaları:
```bash
tail -f ~/kasa/llama.log      # model sunucusu
tail -f ~/kasa/asistan.log    # KASA arayüzü
```

---

## Ne doğrulandı, ne doğrulanmadı

Bu depoda **doğrulanmış** olanlar:
* llama.cpp resmî sürümlerinde Android arm64 ikilisi var (b11889, 25 Eki 2026):
  `llama-b11889-bin-android-arm64.tar.gz` (77 MB) ve `-snapdragon` (62 MB)
* llama-cpp-python 0.3.36'nın içindeki llama.cpp `LLM_ARCH_GEMMA4` içeriyor
  → Gemma 4 GGUF okunabilir
* HTTP istemcisi, akış, araç döngüsü ve arka uç seçimi: 22 otomatik test

**Doğrulanmamış** (bu ortamda imkânsız — model ve ikili indirilemiyor, Android yok):
* Senin telefonunda ölçülen gerçek token/s
* Snapdragon varyantının senin çipinde GPU'yu kullanıp kullanmadığı

Bunları `kontrol.sh` ve `baslat.sh` senin cihazında ölçer. Sonucu bana yaz,
ayarları ona göre sıkılaştırırım.
