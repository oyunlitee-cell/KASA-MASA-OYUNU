#!/usr/bin/env python3
"""Türkçe kalite ölçümü — modeli kendi cihazında, kendi sorularınla sına.

Neden gerekiyor: Gemma 4 E4B ve Qwen3.5-4B için YAYINLANMIŞ bir Türkçe
benchmark yok. MMMLU (çok dilli) içinde Türkçe bulunmuyor; TurkBench /
TurkishMMLU gibi akademik setler ise bu küçük modelleri kapsamıyor.
Dolayısıyla "Türkçe kalitesi" iddiasını ölçmenin tek yolu, modeli elindeki
telefonda bu sorularla koşturmak.

Kullanım:
    PYTHONPATH=src python3 eval/turkce_degerlendir.py
    PYTHONPATH=src python3 eval/turkce_degerlendir.py --cikti rapor.json
    PYTHONPATH=src python3 eval/turkce_degerlendir.py --puanla   # elle 1-5 puan

Otomatik ölçütler (her yanıt için):
  • türkçe_oranı   : Türkçe'ye özgü harf/ek oranı (düşükse İngilizce kaçış var)
  • çeviri_kokusu  : "Here is", "Sure!", "I'd be happy" gibi İngilizce kalıplar
  • uzunluk        : kelime sayısı (çok uzun = küçük modelde saçmalama riski)
  • kod_blogu      : kod istenen görevlerde ``` bloğu var mı
  • süre / hız     : telefonda gerçekçi bekleme süresi
Elle puanlama (--puanla) eklenince 1-5 arası not ortalaması da rapora girer.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))

from kasa_asistan.agent import asistan_kur  # noqa: E402

SORULAR = [
    # (kategori, beklenti, soru)
    ("sohbet", "metin", "Merhaba! Kendini iki cümleyle tanıtır mısın?"),
    ("sohbet", "metin", "Bugün çok yorgunum ama yarın bir sunumum var. Ne yapmalıyım?"),
    ("sohbet", "metin", "Konya'da hafta sonu ne yapılır? Üç öneri ver."),
    ("sohbet", "metin", "Türkçe'de 'ayıptır söylemesi' ne demek? Bir cümlede kullan."),
    ("sohbet", "metin", "Bana kısa bir ninni yazar mısın?"),

    ("dil", "metin", "Aşağıdaki cümleyi daha doğal Türkçe'yle yeniden yaz: "
                     "'Toplantı esnasında proje ile alakalı olarak bir update aldık.'"),
    ("dil", "metin", "'Kafayı yemek', 'eline sağlık' ve 'işkillenmek' deyimlerini "
                     "birer cümleyle açıkla."),
    ("dil", "metin", "Şu cümleyi resmî Türkçe'ye çevir: 'Yarın gelirim ben, merak etme sen.'"),
    ("dil", "metin", "'Yapay zekâ' ve 'makine öğrenmesi' arasındaki farkı bir ortaokul "
                     "öğrencisine anlatır gibi anlat."),

    ("kod", "kod", "Python'da bir klasördeki tüm .txt dosyalarını tek bir dosyada "
                   "birleştiren bir fonksiyon yaz."),
    ("kod", "kod", "Şu JavaScript fonksiyonundaki hatayı bul ve düzelt: "
                   "function topla(a, b) { return a + b } console.log(topla('2', 3))"),
    ("kod", "kod", "Bir HTML dosyasında karanlık mod açan tek satırlık CSS ver."),
    ("kod", "kod", "Python'da 'list index out of range' hatası neden olur? "
                   "İki satırda açıkla ve örnek ver."),

    ("proje", "metin", "Telefonda çalışan, tamamen çevrimdışı bir not tutma uygulaması "
                       "yapmak istiyorum. Bana dosya yapısı ve 3 adımlık yol haritası çıkar."),
    ("proje", "metin", "Bir Flask API'sine Türkçe hata mesajı dönen bir hata yakalayıcı "
                       "(error handler) ekle. Sadece ilgili kodu ver."),

    ("talimat", "metin", "Tam olarak 3 maddelik bir liste ver. Her madde en fazla 6 kelime "
                         "olsun. Başka hiçbir şey yazma."),
    ("talimat", "metin", "Sadece 'tamam' kelimesini yaz, başka hiçbir şey ekleme."),
]

TURKCE_HARFLER = set("çğıöşüÇĞİÖŞÜ")
CEVIRI_KOKUSU = [
    r"\bHere('s| is)\b", r"\bSure[,!]", r"\bI'd be happy\b", r"\bGreat question\b",
    r"\bLet me know\b", r"\bAs an AI\b", r"\bCertainly\b", r"\bOf course[,!]",
    r"\bHowever\b", r"\bTherefore\b", r"\bAdditionally\b",
]


def olc(yanit: str, beklenti: str) -> dict:
    kelimeler = re.findall(r"\w+", yanit, re.UNICODE)
    harfler = [c for c in yanit if c.isalpha()]
    tr_oran = (sum(1 for c in harfler if c in TURKCE_HARFLER) / len(harfler)) if harfler else 0.0
    kokus = sum(len(re.findall(p, yanit, re.IGNORECASE)) for p in CEVIRI_KOKUSU)
    return {
        "türkçe_oranı": round(tr_oran, 3),
        "çeviri_kokusu": kokus,
        "kelime": len(kelimeler),
        "kod_blogu": "```" in yanit,
        "kod_beklendi": beklenti == "kod",
        "bos": len(yanit.strip()) == 0,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="KASA Asistan Türkçe değerlendirme")
    p.add_argument("--model", default=None, help="asistan.yaml model anahtarı")
    p.add_argument("--cikti", default=None, help="rapor JSON yolu")
    p.add_argument("--puanla", action="store_true", help="her yanıtı elle 1-5 puanla")
    p.add_argument("--arac-kapali", action="store_true")
    a = p.parse_args()

    asistan = asistan_kur(model=a.model, araclar=not a.arac_kapali)
    d = asistan.durum()
    print("─" * 66)
    print(f"  Model : {d['etiket']} [{d['model']}]  ·  arka uç: {d['arka_uc']}")
    if not d["gercek_model"]:
        print("  ⚠  DEMO modunda: ölçümler demo yanıtlarını yansıtır, modeli DEĞİL.")
    print(f"  Soru  : {len(SORULAR)}")
    print("─" * 66)

    sonuclar, puanlar = [], []
    for no, (kategori, beklenti, soru) in enumerate(SORULAR, 1):
        basla = time.time()
        yanit = asistan.yanit(soru)
        sure = time.time() - basla
        m = olc(yanit, beklenti)
        m.update({"no": no, "kategori": kategori, "soru": soru,
                  "sure": round(sure, 2), "hiz": round(asistan.istatistik.get("son_hiz", 0), 1),
                  "yanit": yanit})
        print(f"\n[{no:2d}] {kategori:8s} · {m['kelime']:4d} kelime · "
              f"Türkçe oranı {m['türkçe_oranı']:.2f} · çeviri kokusu {m['çeviri_kokusu']} "
              f"· {sure:.1f}s")
        print(f"     › {yanit.strip()[:160].replace(chr(10), ' ')}…")
        if a.puanla:
            try:
                puan = int(input("     puan (1-5, boş=atla) › ").strip() or 0)
            except (EOFError, ValueError):
                puan = 0
            if puan:
                puanlar.append(puan)
                m["puan"] = puan
        sonuclar.append(m)
        asistan.gecmis.clear()          # her soru bağımsız ölçülsün

    print("\n" + "═" * 66)
    print("  ÖZET")
    print("═" * 66)
    ort_tr = statistics.mean(x["türkçe_oranı"] for x in sonuclar)
    ort_kel = statistics.mean(x["kelime"] for x in sonuclar)
    toplam_kokus = sum(x["çeviri_kokusu"] for x in sonuclar)
    ort_sure = statistics.mean(x["sure"] for x in sonuclar)
    print(f"  Ortalama Türkçe karakter oranı : {ort_tr:.3f}   (0.03-0.10 aralığı sağlıklı)")
    print(f"  Toplam İngilizce kalıp kaçağı : {toplam_kokus}")
    print(f"  Ortalama yanıt uzunluğu       : {ort_kel:.0f} kelime")
    print(f"  Ortalama yanıt süresi         : {ort_sure:.1f} sn")
    kod_istenen = [x for x in sonuclar if x["kod_beklendi"]]
    if kod_istenen:
        basari = sum(1 for x in kod_istenen if x["kod_blogu"]) / len(kod_istenen)
        print(f"  Kod bloğu üretme başarısı     : {basari:.0%} ({len(kod_istenen)} görev)")
    if puanlar:
        print(f"  Elle puan ortalaması          : {statistics.mean(puanlar):.2f} / 5 "
              f"({len(puanlar)} yanıt)")

    print("\n  YORUM REHBERİ")
    print("   • türkçe_oranı < 0.02  → model İngilizce düşünüp Türkçe'ye çeviriyor;")
    print("                            sistem komutunu (persona.py) sıkılaştır.")
    print("   • çeviri_kokusu > 0    → 'Here is', 'Sure!' gibi kalıplar sızıyor.")
    print("   • kelime > 300         → küçük model saçmalıyor; maks_yeni_token düşür.")
    print("   • süre > 30 sn         → telefonda kullanışsız; E2B'ye geç veya bağlamı kıs.")

    if a.cikti:
        yol = Path(a.cikti)
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(json.dumps({"durum": d, "sonuclar": sonuclar},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  Rapor: {yol}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
