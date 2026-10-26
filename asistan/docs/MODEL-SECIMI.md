# Model Seçim Raporu — KASA Asistan

**Tarih:** 26 Ekim 2026 · **Hazırlayan:** Arena.ai Agent Mode (otomatik araştırma + uygulama)
**İstenen:** Türkçe konuşan, sohbet edebilen, kod yazan/hata ayıklayan, tam proje
kurabilen ve **Android telefonda yerel (offline)** çalışan kişisel asistan.

---

## 🇬🇧 Executive summary (English)

**Selected model: Gemma 4 E4B IT (Apache 2.0)** — with `gemma4-e2b` as the low-RAM
variant and `qwen35-4b` / `qwen3-4b` shipped as switchable alternates.

| Requirement | Verdict |
|---|---|
| **License** | ✅ Apache 2.0 — true OSI open source, commercial use, no gating. (Gemma 3 and older were *not*: custom "Gemma Terms of Use".) |
| **Android fit** | ✅ Google's own on-device runtime (LiteRT-LM) ships Gemma 4 E2B/E4B with *measured* numbers on a Samsung S26 Ultra: E4B = 3.65 GB file, 22 tok/s decode on GPU, 0.8 s to first token. |
| **Storage/RAM** | ✅ 3.65 GB `.litertlm` (E2B: 2.58 GB). Runs on 6–8 GB phones. |
| **Coding** | ✅ LiveCodeBench v6 **52.0** — the best score of any ~4B open model I could verify; the runner-up Qwen3-4B-Instruct-2507 scores 35.1. Codeforces ELO 940. |
| **Turkish** | ⚠️ **No published Turkish benchmark exists for any of these models.** MMMLU (the multilingual benchmark both vendors quote) does not include Turkish. Indirect evidence is roughly a tie (Gemma 4 E4B MMMLU 76.6 vs Qwen3.5-4B 76.1), and Turkish-community work clusters around Qwen. **Because I could not verify this, I built a 18-prompt Turkish eval harness into the repo** so you can measure it on your own phone before committing. See `eval/turkce_degerlendir.py`. |
| **"Build complete software projects"** | ⚠️ Honest limit: a 4B model on a phone writes and debugs single files and small modules well; it is **not** an autonomous repo-building agent. I added a file/command tool loop plus a project-scaffolding mode to push this as far as 4B realistically goes. See "Sınırlar". |

**Why not Qwen3.5-4B?** It is very likely the stronger model on paper (LCB v6 55.8,
201 languages, 262K context) but it uses a **hybrid Gated-DeltaNet / SSM architecture**.
On Android that is a practical problem today: llama.cpp only learned the operator in
Feb 2026, Qwen publishes **no official GGUF** (every quant is a community requant),
conversion bugs were still being filed in Aug 2026, and there is an **open CPU-correctness
bug** for the whole `qwen35` family as of 21 Oct 2026. It ships in the repo as an
optional profile, flagged experimental. Details in "Neden Qwen3.5 değil".

---

## 1. Kriterler ve ağırlıklar

| # | Kriter | Ağırlık | Neden |
|---|---|---|---|
| 1 | **Android'de gerçekten çalışması** | %30 | İstek "telefonda yerel" — kâğıt üstü kalite tek başına işe yaramaz |
| 2 | **Lisans** | %20 | "Open-source" denildi; Apache-2.0 / MIT dışı lisanslar (Llama Community, eski Gemma ToU) elendi |
| 3 | **Türkçe kalite** | %20 | Birinci sınıf gereksinim |
| 4 | **Kod yeteneği** | %20 | Kod yazma + hata ayıklama + proje kurma |
| 5 | **Depolama / RAM** | %10 | Telefonda 3-4 GB'lık dosya gerçek bir maliyet |

## 2. Aday havuzu ve eleme

Elenenler ve gerekçeleri:

| Model | Durum | Gerekçe |
|---|---|---|
| Qwen3-Coder-30B-A3B, Qwen3-Coder-Next (80B-A3B), Devstral Small, GLM-5.x, Kimi K3, DeepSeek-V4, Qwen3.6-27B / Qwen3.8-27B | ❌ | 17-38 GB; telefon ölçeği değil. (Qwen3.8-27B, Ağustos 2026'da Apache 2.0 ile açıldı — masaüstü yedeği olarak not edildi [1](https://codersera.com/blog/qwen-3-5-complete-guide-2026/)) |
| gpt-oss-20b / 120b (OpenAI) | ❌ | Apache 2.0 ve güçlü ama 12-60 GB |
| Llama 3.2 3B / Llama 4 Scout | ❌ | **Llama Community License** — açık ağırlık, ama gerçek açık kaynak değil (ticari kullanım sınırlı) |
| Gemma 3 1B/4B, Gemma 3n E2B/E4B | ❌ | Gemma 3 lisansı **kaynak-erişilebilir**, özgür yazılım değil [20](https://en.wikipedia.org/wiki/Gemma_(language_model)) |
| Phi-4-mini 3.8B (MIT) | ⚠️ | Lisans mükemmel, telefon 10-18 tok/s; ancak çok dilli başarımı Qwen/Gemma 4'ün gerisinde ve kod tarafı 4B sınıfında Gemma 4 E4B'nin altında |
| Qwen3-0.6B / 1.7B | ⚠️ | 6 GB altı telefonlar için mantıklı (LiteRT-LM'de Qwen3-0.6B = 586 MB) ama sohbet kalitesi düşük |
| **Gemma 4 E2B / E4B** | ✅ | Apache 2.0 + resmî Android motoru + sınıfının en iyi kod skoru |
| **Qwen3.5-4B** | ⚠️ | Kağıt üstü en güçlü 4B; olgunlaşmamış çalışma zamanı |
| **Qwen3-4B-Instruct-2507** | ✅ | Klasik transformer, her yerde çalışır — uyumluluk yedeği |

## 3. Finalistlerin karşılaştırması

| | **Gemma 4 E4B** | **Gemma 4 E2B** | **Qwen3.5-4B** | **Qwen3-4B-Inst-2507** |
|---|---|---|---|---|
| Lisans | Apache 2.0 | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| Parametre | 4.5B etkin / 8B toplam [4](https://ai.google.dev/gemma/docs/core/model_card_4) | 2.3B etkin / 5.1B toplam [4](https://ai.google.dev/gemma/docs/core/model_card_4) | 4B (hibrit GDN) | 4.0B [2](https://huggingface.co/Qwen/Qwen3.5-4B) |
| Bağlam | 128K | 128K | 262K [9](https://huggingface.co/datasets/egeboy35/qwen3.5-4b-tr-en-evaluation) | 262K [1](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) |
| Dosya boyutu | **3.65 GB** `.litertlm` [7](https://ai.google.dev/edge/litert-lm/models/gemma-4) | **2.58 GB** [7](https://ai.google.dev/edge/litert-lm/models/gemma-4) | ~2.7 GB GGUF (topluluk) | 2.65 GB GGUF |
| Telefon RAM | 6-8 GB | 4-6 GB | 6-8 GB (riskli) | 6-8 GB |
| Android motoru | **LiteRT-LM (resmî)** | **LiteRT-LM (resmî)** | llama.cpp (GGUF) | llama.cpp (GGUF) |
| Ölçülen hız (S26 Ultra, GPU) | **22 tok/s**, TTFT 0.8 s [7](https://ai.google.dev/edge/litert-lm/models/gemma-4) | **52 tok/s**, TTFT 0.3 s [7](https://ai.google.dev/edge/litert-lm/models/gemma-4) | veri yok | veri yok |
| LiveCodeBench v6 (kod) | **52.0** [3](https://www.promptquorum.com/local-llms/small-local-llm-models) | 44.0 [3](https://www.promptquorum.com/local-llms/small-local-llm-models) | **55.8** [3](https://www.promptquorum.com/local-llms/small-local-llm-models) | 35.1 |
| MMLU-Pro | 69.4 [3](https://www.promptquorum.com/local-llms/small-local-llm-models) | 60.0 | 79.1 [3](https://www.promptquorum.com/local-llms/small-local-llm-models) | ~65 |
| MMMLU (çok dilli) | **76.6** [3](https://www.promptquorum.com/local-llms/small-local-llm-models) | 67.4 | 76.1 [3](https://www.promptquorum.com/local-llms/small-local-llm-models) | — |
| Dil iddiası | 140+ dil [4](https://ai.google.dev/gemma/docs/core/model_card_4) | 140+ | **201 dil** [6](https://github.com/QwenLM/Qwen3.8) | 119 dil |
| Girdi türleri | metin + görüntü + **ses** [4](https://ai.google.dev/gemma/docs/core/model_card_4) | metin + görüntü + ses | metin + görüntü + video | metin |
| Sesli asistan | ✅ (ses girdisi yerleşik) | ✅ | ❌ | ❌ |

**Karar:** Android uyumluluğu %30 ağırlıkla birinci kriter. Gemma 4 E4B, kod skorunda
Qwen3.5-4B'ye 3.8 puan farkla yenilirken, **çalışma zamanı olgunluğunda bir nesil önde**.
Türkçe'de ikisi başabaş görünüyor (ve ikisi için de kesin kanıt yok). Bu yüzden
**önce çalışan, ölçülebilir olan** seçildi.

## 4. Neden Qwen3.5-4B seçilmedi (ayrıntılı)

Qwen3.5, Şubat 2026'da gelen yeni nesil: **Gated Delta Net + seyrek MoE** hibrit
mimarisi, 201 dil, 262K bağlam, yerleşik görüntü/video [6](https://github.com/QwenLM/Qwen3.8).
Telefonda bunu çalıştırmanın tek yolu llama.cpp + GGUF, ve orada tablo şöyle:

1. **Yeni operatör gerekiyor.** llama.cpp'ye `qwen35` desteği 10 Şubat 2026'da
   eklendi; Gated DeltaNet için ayrı bir `GATED_DELTA_NET` ggml operatörü yazıldı
   [1](https://github.com/ggml-org/llama.cpp/pull/19468). Eski derlemeler dosyayı
   açamıyor bile.
2. **Resmî GGUF yok.** Qwen hiçbir Qwen3.5 boyutu için GGUF yayınlamıyor; dolaşımdaki
   tüm dosyalar topluluk requant'ları [16](https://iotdigitaltwinplm.com/slm-cpu-inference-models-compared-2026/).
3. **Dönüştürme hataları sürüyor.** Ağustos 2026'da hâlâ `ssm_conv1d` kernel boyutuyla
   ilgili dönüştürme hatası bildiriliyor [10](https://github.com/ggml-org/llama.cpp/issues/27019).
4. **Açık doğruluk hatası.** 21 Ekim 2026 tarihli açık sorun: `qwen35` ailesinde
   **CPU arka ucu tekrar döngülerine girip saçmalıyor**, aynı ikili dosyayla Vulkan
   doğru çalışıyor [20](https://github.com/ggml-org/llama.cpp/issues/30906).
   Android'de çoğu cihaz CPU/yarı-GPU yoluyla çalışır — bu doğrudan hedef platform.

Bunların hiçbiri kalıcı değil; 6 ay içinde kapanabilir. O yüzden model **silinmedi**,
`asistan.yaml` içinde `qwen35-4b` profili olarak duruyor ve `uyari` alanıyla işaretlendi.
Telefonunda denemek istersen: `bash asistan/modeller/indir.sh qwen35-4b`.

## 5. Türkçe meselesi — bilinmeyenleri saklamıyorum

Bu başlıkta **kesin bir kazanan yok** ve bunu uydurmak istemedim:

* **MMMLU, her iki üreticinin de alıntıladığı çok dilli benchmark, Türkçe içermiyor.**
  Gemma 4 E4B 76.6 / Qwen3.5-4B 76.1 — neredeyse eşit, ama bu Türkçe hakkında
  doğrudan bir şey söylemiyor [3](https://www.promptquorum.com/local-llms/small-local-llm-models).
* Akademik taraf: **TurkBench** (8.151 örnek, 21 alt görev, Ocak 2026) Türkçe'ye özel
  tek kapsamlı set; tablosunda Qwen3 ailesi üst sıralarda (Qwen3-Next-80B 75.0,
  Qwen3-30B-A3B 73.4) ama **4B sınıfı ve Gemma 4 hiç yok** [1](https://arxiv.org/html/2601.07020v1).
  TurkishMMLU da aynı şekilde eski modelleri kapsıyor [12](https://arxiv.org/html/2407.12402v2).
* Topluluk verisi: bir geliştirici Qwen3.5-4B'yi 360 Türkçe soruyla denemiş —
  TR-MMLU benzeri bilgi sorularında ~%80, **Türkçe kültür/deyimlerde %33**,
  genel ortalama %65 [9](https://huggingface.co/datasets/egeboy35/qwen3.5-4b-tr-en-evaluation).
  Yani bilgi dili iyi, **kültürel/deyimsel Türkçe zayıf** — bu, küçük modellerin ortak zaafı.
* Türkçe'ye özel ince ayar çalışmaları Qwen tarafında yoğunlaşmış (TÜDÜM: Qwen3.5-27B
  üzerine Türkçe-düşünen model; Turkish MMLU 82.3) [15](https://arxiv.org/html/2607.01927v1).

**Çıkarım:** Gemma 4 E4B Türkçe'de *muhtemelen* iyi ama **kanıtlanmış değil**;
Qwen tarafı Türkçe'de bir miktar daha güvenli görünüyor ama telefonda çalıştırmak riskli.
Bu yüzden depoya **Türkçe değerlendirme seti** koydum: modeli kendi telefonunda
18 soruyla çalıştırıp Türkçe karakter oranı, İngilizce kalıp kaçağı, kod bloğu üretimi
ve hız ölçümü alıyorsun. Sonuç kötüyse sistem komutunu (`persona.py`) sıkılaştırıp
tekrar denemek 5 dakika sürüyor.

```bash
PYTHONPATH=src python3 eval/turkce_degerlendir.py --puanla
```

## 6. "Tam yazılım projesi kurabilsin" — gerçekçi sınır

4B model, telefonda, 8K bağlamla:

| Yapabilir | Yapamaz |
|---|---|
| Tek dosyalık betik/uygulama yazmak (HTML oyunu, Flask API, CLI aracı) | 20 dosyalık bir depoyu tek seferde tutarlı kurmak |
| Verilen hata mesajından sebebi bulup düzeltmek | Derin, çok katmanlı mimari tasarlamak |
| Bir dosyayı okuyup baştan yazmak (araçlarla) | Kendi kendine saatlerce otonom çalışmak |
| Proje iskeleti + yol haritası çıkarmak | Büyük bağlam gerektiren refactoring |

Bunu olabildiğince ileri taşımak için asistana **araç döngüsü** ekledim
(`dosya_oku`, `dosya_yaz`, `dosya_liste`, `ara`, `komut`): model tahmin etmek
yerine dosyayı gerçekten okuyor, yazıyor, komut çalıştırıyor. Güvenlik için
komutlar izinli listede (`git push` engelli) ve tüm dosya işlemleri tek bir
çalışma dizinine kilitli — testlerde doğrulandı (`tests/test_smoke.py`).

Bağlamı bilinçli olarak **8K** ile sınırladım: 128K'yı doldurmak telefonda hem
pili hem hafızayı bitirir, küçük model de uzun bağlamda kalite kaybeder.

## 7. Sınırlar (kısa liste)

1. **Türkçe kalite ölçülmedi** — yukarıya bakın, `eval/` ile kendin ölç.
2. **Telefonda gerçek çıkarımı bu ortamda test edemedim.** Sandbox'ta Android
   derleyici/cihaz yok ve model dosyaları (3.6 GB) indirilemiyor. Test edilen:
   Python paketi, yapılandırma ayrıştırma, araç döngüsü, güvenlik sınırları,
   HTTP sunucusu ve arayüz (12 test geçiyor). llama-cpp-python derlenip kuruldu
   (v0.3.36) — yani model dosyasını koyduğun anda çıkarım yolu hazır.
3. **Araçlı kod düzenleme, modelin aracı doğru formatta çağırmasına bağlı.**
   4B modeller araç çağrılarında hata yapabilir; döngü en fazla 3 tur ve bozuk
   çağrı yok sayılıyor. İlk denemede ters giden bir dosya yazarsa `.bak`
   yedeği bırakılıyor.
4. **Sesli kullanım için ek iş gerekir.** Gemma 4 E4B ses *girdisi* alıyor ama
   bu repoda ses yakalama (mikrofon → model) yazılmadı; LiteRT-LM tarafında
   veya Android MediaPipe ile eklenebilir.
5. **Batarya ve ısınma.** 4B model sürekli çalıştırıldığında telefonu ısıtır;
   uzun sohbetlerde E2B'ye geçmek mantıklı.

## 8. Kaynaklar

Model kartları ve resmî belgeler
1. Google DeepMind — Gemma 4 model card: <https://ai.google.dev/gemma/docs/core/model_card_4>
2. Google AI Edge — Gemma 4 (LiteRT-LM, boyut ve cihaz hızları): <https://ai.google.dev/edge/litert-lm/models/gemma-4>
3. Google AI Edge — LiteRT-LM desteklenen modeller tablosu: <https://developers.google.com/edge/litert-lm/overview>
4. Google Developers Blog — Gemma 4 on edge (2 Nisan 2026): <https://developers.googleblog.com/bring-state-of-the-art-agentic-skills-to-the-edge-with-gemma-4/>
5. QwenLM/Qwen3.8 — resmî depo (Qwen3.5/3.6/3.8, 201 dil, hibrit mimari): <https://github.com/QwenLM/Qwen3.8>
6. Qwen3-4B-Instruct-2507 — model kartı: <https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507>
7. Qwen3.5-4B — model kartı (çok dilli tablolar): <https://huggingface.co/Qwen/Qwen3.5-4B>

Lisans
8. Wikipedia — Gemma (Gemma 4 = Apache 2.0, Gemma 3 ve öncesi = kaynak erişilebilir): <https://en.wikipedia.org/wiki/Gemma_(language_model)>
9. QwenLM/Qwen3 — "All our open-weight models are licensed under Apache 2.0": <https://github.com/qwenLM/qwen3>

Karşılaştırmalı ölçütler
10. PromptQuorum — Best Small LLM 2026 (Qwen3.5 4B / Gemma 4 E4B skorları): <https://www.promptquorum.com/local-llms/small-local-llm-models>
11. Codersera — Qwen 3.5 → 3.8 sürüm haritası: <https://codersera.com/blog/qwen-3-5-complete-guide-2026/>
12. AI Edge — MediaPipe LLM Inference API bakım modunda, LiteRT-LM'e geçin: <https://developers.google.com/edge/mediapipe/solutions/genai/llm_inference>

Türkçe
13. TurkBench — Türkçe LLM benchmark'ı (arXiv 2601.07020): <https://arxiv.org/html/2601.07020v1>
14. TurkishMMLU (arXiv 2407.12402): <https://arxiv.org/html/2407.12402v2>
15. TÜDÜM — Qwen3.5-27B üzerine Türkçe-düşünen model (arXiv 2607.01927): <https://arxiv.org/html/2607.01927v1>
16. Qwen3.5-4B Türkçe/İngilizce topluluk değerlendirmesi: <https://huggingface.co/datasets/egeboy35/qwen3.5-4b-tr-en-evaluation>

Çalışma zamanı / Android
17. llama.cpp — Qwen3.5 desteği (PR #19468, 10 Şubat 2026): <https://github.com/ggml-org/llama.cpp/pull/19468>
18. llama.cpp — `qwen35` CPU arka ucu hatalı çıktı üretiyor (açık sorun, 21 Eki 2026): <https://github.com/ggml-org/llama.cpp/issues/30906>
19. llama.cpp — Qwen3.5 dönüştürme hatası (Ağu 2026): <https://github.com/ggml-org/llama.cpp/issues/27019>
20. CPU dağıtım notu — Qwen3.5 için resmî GGUF yok: <https://iotdigitaltwinplm.com/slm-cpu-inference-models-compared-2026/>
21. Android örnek uygulama (Gemma 4 E4B LiteRT = amiral gemisi, E2B = orta seviye): <https://github.com/dineshsoudagar/local-llms-on-android>

---

## 9. Ek: Android doğrulaması (26 Ekim 2026, ikinci tur)

Telefon-only hedefi için yapılan doğrulamalar ve bunun mimariye etkisi:

### Doğrulananlar

| Soru | Yöntem | Sonuç |
|---|---|---|
| llama.cpp'nin resmî Android ikilisi var mı? | GitHub Releases API | ✅ `b11889` (25 Eki 2026): `llama-b11889-bin-android-arm64.tar.gz` (77 MB) ve `-snapdragon` varyantı (62 MB) — CPU/Adreno/Hexagon |
| Python bağlayıcısı Gemma 4 GGUF okuyabiliyor mu? | sdist kaynağında mimari kaydı | ✅ llama-cpp-python 0.3.36 içindeki llama.cpp'de `LLM_ARCH_GEMMA4` ve `gemma4-assistant` tanımlı |
| Telefonda derleme gerekiyor mu? | mimari kararı | ❌ **Hayır** — resmî ikili + GGUF yeterli |

### Mimari değişikliği

İlk sürüm modeli Python süreci içinde yüklüyordu (`llama-cpp-python`). Telefonda bu,
C++ derlemesi demek: Termux'ta 15-30 dakika, `cmake`+`clang`, ve sık başarısızlık.
Bu yüzden **llama-server (HTTP) yolu eklendi ve Android için varsayılan yapıldı**:

```
KASA (saf Python) ──HTTP/OpenAI──▶ llama-server (resmî Android ikilisi) ──▶ Gemma 4 GGUF
```

Kazançlar:
* Telefonda **sıfır derleme**; Python tarafında hiçbir pip bağımlılığı yok.
* Yeni mimariler (Qwen3.5/3.8 gibi) llama-server güncellenince anında gelir;
  Python bağlayıcısının sürümünü beklemek gerekmez.
* Model ayrı süreçte: çökerse arayüz ayakta kalır, log ayrı okunur.

`llama-cpp-python` yolu **kaldırılmadı** — yedek olarak duruyor (masaüstü ve
derlemek isteyenler için). Seçim sırası: `llama-server` → yerel GGUF → demo.

### Bu ortamda doğrulanamayanlar (dürüstçe)

* Gerçek sürüm hızı ve bellek tüketimi: sandbox'ta Android cihaz yok, ayrıca
  egress kısıtlı olduğu için **model (huggingface.co) ve ikili
  (objects.githubusercontent.com) indirilemiyor**.
* Snapdragon varyantının NPU/GPU yolunu senin çipinde açıp açmadığı.
  `asistan/android/kontrol.sh` bunu cihazında ölçer.
