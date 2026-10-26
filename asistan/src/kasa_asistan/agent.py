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
    az_tur: int = 3                     # araç döngüsü tur limiti
    gecmis: list[Mesaj] = field(default_factory=list)
    kisilik: Kisilik | None = None
    arka_uc: ArkaUc | None = None
    profil: object = None
    arac_kutusu: AracKutusu | None = None
    istatistik: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ kurulum
    def __post_init__(self) -> None:
        self.arka_uc, self.profil = arka_uc_kur(self.ayarlar, self.model_anahtari)
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
        """Araç döngüsü dahil tam yanıt (akışsız)."""
        self.gecmis.append(Mesaj("user", kullanici_metni))
        assert self.arka_uc is not None
        mesajlar = self.mesajlar(kullanici_metni)
        ham = self.arka_uc.uret(mesajlar, **self._ornekleme())
        metin = ham.metin if isinstance(ham, Uretilen) else str(ham)
        self.istatistik["son_token"] = getattr(ham, "token_sayisi", 0)
        self.istatistik["son_hiz"] = round(getattr(ham, "token_hizi", 0.0), 1)

        if not (self.araclar_acik and self.arac_kutusu):
            self.gecmis.append(Mesaj("assistant", metin))
            return metin

        for _ in range(self.az_tur):
            cagri, temiz = arac_cagrisi_ayikla(metin)
            if not cagri:
                metin = temiz
                break
            sonuc = self.arac_kutusu.cagir(cagri["arac"], cagri.get("argumanlar") or {})
            mesajlar.append({"role": "assistant", "content": metin})
            mesajlar.append({"role": "user", "content": f"ARAC SONUCU ({cagri['arac']}):\n{sonuc}"})
            ham = self.arka_uc.uret(mesajlar, **self._ornekleme())
            metin = ham.metin if isinstance(ham, Uretilen) else str(ham)

        self.gecmis.append(Mesaj("assistant", metin))
        return metin

    def yanit_akis(self, kullanici_metni: str) -> Iterator[str]:
        """Token token akış. Araç gerekiyorsa akışsız yola düşer (nadirdir)."""
        tam = self.yanit(kullanici_metni)
        for parca in re.findall(r"\S+\s*", tam):
            yield parca

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
        })
        return bilgi


def asistan_kur(yol: str | None = None, model: str | None = None,
                araclar: bool = True) -> Asistan:
    return Asistan(ayarlar=ayarlari_yukle(yol), model_anahtari=model, araclar_acik=araclar)
