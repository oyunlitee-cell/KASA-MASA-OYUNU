"""Sohbet döngüsü, araç kullanımı ve hafıza.

4B'lık bir model aracı her zaman doğru formatta çağırmayabilir; bu yüzden
araç döngüsü "en fazla N tur" ile sınırlı ve bozuk çağrılar yok sayılıyor
(modelin metni kullanıcıya döner).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .backends import ArkaUc, Uretilen, arka_uc_kur
from .config import Ayarlar, ayarlari_yukle
from .persona import Kisilik, Profil
from .tools import AracKutusu, arac_cagrisi_ayikla


@dataclass
class Mesaj:
    rol: str          # system | user | assistant | tool
    icerik: str

    def sozluk(self) -> dict:
        return {"role": self.rol, "content": self.icerik}


@dataclass
class Asistan:
    ayarlar: Ayarlar
    model_anahtari: str | None = None
    araclar_acik: bool = True
    demo_izin: bool = True
    az_tur: int = 3                     # araç döngüsü tur limiti
    gecmis: list[Mesaj] = field(default_factory=list)
    kisilik: Kisilik | None = None
    arka_uc: ArkaUc | None = None
    profil: object = None
    arac_kutusu: AracKutusu | None = None
    istatistik: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ kurulum
    def __post_init__(self) -> None:
        self.arka_uc, self.profil = arka_uc_kur(
            self.ayarlar, self.model_anahtari, demo_izin=self.demo_izin)
        p = self.ayarlar.profil
        self.kisilik = Kisilik(
            profil=Profil(
                ad=p.get("ad", "KASA"),
                kullanici_ad=p.get("kullanici_ad", "Patron"),
                dil=p.get("dil", "tr"),
                hitap=p.get("hitap", "sen"),
                ton=p.get("ton", "sıcak ama net"),
            ),
            model_etiketi=getattr(self.profil, "parametre", "") or "4B",
            araclar_etkin=self.araclar_acik and self.ayarlar.araclar.get("etkin", True),
            hafiza_ozeti=self.hafiza_oku(),
        )
        a = self.ayarlar.araclar
        self.arac_kutusu = AracKutusu(
            kok=(self.ayarlar.kok / a.get("calisma_dizini", "..")).resolve(),
            izinli_komutlar=a.get("izinli_komutlar", ["ls"]),
            zaman_asimi=a.get("komut_zaman_asimi_saniye", 60),
            maks_kb=a.get("maks_dosya_boyutu_kb", 512),
            yedekle=a.get("yedekle", True),
        )

    # ------------------------------------------------------------------ hafıza
    @property
    def hafiza_yolu(self) -> Path:
        return self.ayarlar.yol(self.ayarlar.calisma.get("hafiza_dosyasi", "hafiza.md"))

    def hafiza_oku(self) -> str:
        yol = self.hafiza_yolu
        return yol.read_text(encoding="utf-8").strip() if yol.exists() else ""

    def hatirla(self, bilgi: str) -> str:
        """Kullanıcı 'bunu hatırla' derse kalıcı not düş."""
        yol = self.hafiza_yolu
        satir = f"- {datetime.now():%Y-%m-%d}: {bilgi.strip()}"
        mevcut = yol.read_text(encoding="utf-8") if yol.exists() else "# KASA Hafıza\n\n## Kullanıcı hakkında\n"
        if "## Kullanıcı hakkında" not in mevcut:
            mevcut += "## Kullanıcı hakkında\n"
        mevcut = mevcut.rstrip() + "\n" + satir + "\n"
        yol.write_text(mevcut, encoding="utf-8")
        if self.kisilik:
            self.kisilik.hafiza_ozeti = self.hafiza_oku()
        return f"Hatırlıyorum: {bilgi.strip()}"

    # ------------------------------------------------------------------ sohbet
    def _sistem(self) -> Mesaj:
        assert self.kisilik is not None
        return Mesaj("system", self.kisilik.sistem_komutu())

    def mesajlar(self, yeni: str) -> list[dict]:
        g = [self._sistem().sozluk()]
        g += [m.sozluk() for m in self.gecmis[-12:]]
        g.append({"role": "user", "content": yeni})
        return g

    def _ornekleme(self) -> dict:
        pr = getattr(self.profil, "ornekleme", {}) or {}
        return {
            "temperature": pr.get("temp", 0.7),
            "top_p": pr.get("top_p", 0.95),
            "top_k": pr.get("top_k", 40),
            "max_tokens": self.ayarlar.calisma.get("maks_yeni_token", 1024),
        }

    def yanit(self, kullanici_metni: str) -> str:
        """Araç döngüsü dahil tam yanıt (akışı birleştirir)."""
        return "".join(self.yanit_akis(kullanici_metni))

    def yanit_akis(self, kullanici_metni: str) -> Iterator[str]:
        """Gerçek token akışı + araç döngüsü.

        Telefonda üretim 5-10 token/s olduğu için akış şart: kullanıcı ilk
        kelimeyi ~1 saniyede görür, tüm yanıtı beklemez.

        Araç çağrısı (```tool ...```) ekrana basılmaz: son 12 karakter
        bekletilir, çit başladığı an akış susturulur, araç çalıştırılır,
        ardından modelin devam yanıtı yeniden akıtılır.
        """
        assert self.arka_uc is not None
        # ÖNEMLİ: mesajlar() geçmişi + yeni mesajı birleştirir; append sonra yapılmalı,
        # yoksa kullanıcı mesajı istemde iki kez görünür.
        mesajlar = self.mesajlar(kullanici_metni)
        self.gecmis.append(Mesaj("user", kullanici_metni))
        parametreler = self._ornekleme()
        arac_modu = bool(self.araclar_acik and self.arac_kutusu)
        basla = time.time()
        toplam_parca = 0

        for _tur in range(self.az_tur + 1):
            parcalar: list[str] = []
            gosterilen = 0
            cit_goruldu = False

            for parca in self.arka_uc.uret_stream(mesajlar, **parametreler):
                parcalar.append(parca)
                toplam_parca += 1
                biriken = "".join(parcalar)
                if arac_modu and "```tool" in biriken:
                    cit_goruldu = True
                if cit_goruldu:
                    continue
                guvenli = len(biriken) - 12          # çit başlangıcını kaçırma
                if guvenli > gosterilen:
                    yield biriken[gosterilen:guvenli]
                    gosterilen = guvenli

            biriken = "".join(parcalar)
            if not cit_goruldu and len(biriken) > gosterilen:
                yield biriken[gosterilen:]

            cagri, temiz = (arac_cagrisi_ayikla(biriken) if arac_modu else (None, biriken))
            if not cagri:
                self.gecmis.append(Mesaj("assistant", temiz or biriken))
                sure = time.time() - basla
                # Demo arka ucu anında yanıt verdiği için "46538 token/s" gibi
                # anlamsız değerler üretiyordu; hızı sadece gerçek modelde bildir.
                gercek = bool(self.arka_uc and self.arka_uc.gercek)
                self.istatistik.update({
                    "son_token": toplam_parca if gercek else 0,
                    "son_hiz": round(toplam_parca / sure, 1) if (gercek and sure > 0.2) else 0.0,
                })
                return

            assert self.arac_kutusu is not None
            yield f"\n\n⚙ {cagri['arac']} çalıştırılıyor…\n"
            sonuc = self.arac_kutusu.cagir(cagri["arac"], cagri.get("argumanlar") or {})
            mesajlar.append({"role": "assistant", "content": biriken})
            mesajlar.append({
                "role": "user",
                "content": f"ARAC SONUCU ({cagri['arac']}):\n{sonuc}",
            })

        # araç turu tükendi
        uyari = "\n\n(Araç turu sınırına ulaşıldı; sonuçlar yukarıda.)"
        yield uyari
        self.gecmis.append(Mesaj("assistant", uyari.strip()))

    # ------------------------------------------------------------------ geçmiş
    def kaydet(self, ad: str | None = None) -> Path:
        dizin = self.ayarlar.yol(self.ayarlar.calisma.get("gecmis_dizini", "gecmis"))
        dizin.mkdir(parents=True, exist_ok=True)
        ad = ad or f"{datetime.now():%Y%m%d-%H%M%S}.jsonl"
        yol = dizin / ad
        with yol.open("w", encoding="utf-8") as f:
            for m in self.gecmis:
                f.write(json.dumps(m.sozluk(), ensure_ascii=False) + "\n")
        return yol

    def durum(self) -> dict:
        assert self.arka_uc is not None
        bilgi = self.arka_uc.bilgi()
        bilgi.update({
            "model": getattr(self.profil, "anahtar", "?"),
            "etiket": getattr(self.profil, "etiket", "?"),
            "lisans": getattr(self.profil, "lisans", "?"),
            "baglam": getattr(self.profil, "baglam", "?"),
            "araclar": self.araclar_acik,
            "uyari": getattr(self.profil, "uyari", ""),
            "hafiza": self.hafiza_yolu.exists(),
            "mod": "gercek" if bilgi.get("gercek_model") else "demo",
        })
        return bilgi


def asistan_kur(yol: str | None = None, model: str | None = None,
                araclar: bool = True) -> Asistan:
    return Asistan(ayarlar=ayarlari_yukle(yol), model_anahtari=model, araclar_acik=araclar)
