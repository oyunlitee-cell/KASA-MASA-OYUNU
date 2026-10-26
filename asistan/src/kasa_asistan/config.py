"""asistan.yaml yükleyici.

Bağımlılık istemiyoruz (Termux'ta da çalışsın diye): PyYAML varsa onu kullanır,
yoksa bu dosyadaki küçük YAML-altküme ayrıştırıcısı devreye girer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parents[2]          # asistan/
DEPO_KOKU = KOK.parent                              # depo kökü


# ---------------------------------------------------------------------------
#  Küçük YAML altkümesi: iç içe mapping, liste, skaler, blok skaler (>- / |)
# ---------------------------------------------------------------------------
def _yorum_temizle(satir: str) -> str:
    """Satır sonundaki # yorumunu atar (tırnak içindeki #'lere dokunmaz)."""
    sonuc, tirnak = [], None
    for k, ch in enumerate(satir):
        if tirnak:
            sonuc.append(ch)
            if ch == tirnak:
                tirnak = None
            continue
        if ch in "\"'":
            tirnak = ch
            sonuc.append(ch)
            continue
        if ch == "#" and (k == 0 or satir[k - 1] in " \t"):
            break
        sonuc.append(ch)
    return "".join(sonuc).rstrip()


def _ayristir(metin: str) -> dict:
    satirlar = [
        _yorum_temizle(s) for s in metin.splitlines()
        if s.strip() and not s.lstrip().startswith("#")
    ]
    satirlar = [s for s in satirlar if s.strip()]
    kok: dict = {}
    yigin: list[tuple[int, Any]] = [(-1, kok)]
    i = 0
    while i < len(satirlar):
        satir = satirlar[i]
        girinti = len(satir) - len(satir.lstrip())
        govde = satir.strip()

        while yigin and girinti <= yigin[-1][0]:
            yigin.pop()
        kapsayici = yigin[-1][1]

        if govde.startswith("- "):
            if isinstance(kapsayici, list):
                kapsayici.append(_skaler(govde[2:].strip()))
            i += 1
            continue

        if ":" not in govde:
            i += 1
            continue

        anahtar, _, deger = govde.partition(":")
        anahtar = anahtar.strip().strip('"').strip("'")
        deger = deger.strip()

        if deger in (">-", ">", "|", "|-"):
            blok: list[str] = []
            i += 1
            taban = None
            while i < len(satirlar):
                s = satirlar[i]
                if not s.strip():
                    blok.append("")
                    i += 1
                    continue
                g = len(s) - len(s.lstrip())
                if taban is None:
                    taban = g
                if g < taban:
                    break
                blok.append(s[taban:])
                i += 1
            kapsayici[anahtar] = " ".join(x.strip() for x in blok).strip()
            continue

        if deger == "":
            # alt mapping mi liste mi? bir sonraki satıra bak
            alt_girinti = None
            liste = False
            j = i + 1
            while j < len(satirlar):
                s = satirlar[j]
                if not s.strip() or s.lstrip().startswith("#"):
                    j += 1
                    continue
                alt_girinti = len(s) - len(s.lstrip())
                liste = s.strip().startswith("- ")
                break
            if alt_girinti is None or alt_girinti <= girinti:
                kapsayici[anahtar] = {}
            else:
                kapsayici[anahtar] = [] if liste else {}
            yigin.append((girinti, kapsayici[anahtar]))
            i += 1
            continue

        if deger.startswith("[") and deger.endswith("]"):
            kapsayici[anahtar] = [
                _skaler(p) for p in deger[1:-1].split(",") if p.strip()
            ]
        elif "{" in deger and deger.endswith("}"):
            kapsayici[anahtar] = _satir_ici(deger[1:-1])
        else:
            kapsayici[anahtar] = _skaler(deger)
        i += 1
    return kok


def _satir_ici(icerik: str) -> dict:
    sonuc = {}
    for parca in icerik.split(","):
        if ":" in parca:
            k, _, v = parca.partition(":")
            sonuc[k.strip().strip('"').strip("'")] = _skaler(v.strip())
    return sonuc


def _skaler(deger: str) -> Any:
    deger = deger.strip().strip('"').strip("'")
    if deger in ("true", "yes", "evet"):
        return True
    if deger in ("false", "no", "hayir"):
        return False
    if deger in ("null", "~", ""):
        return None
    try:
        return int(deger)
    except ValueError:
        pass
    try:
        return float(deger)
    except ValueError:
        pass
    return deger


def yaml_yukle(yol: Path) -> dict:
    metin = yol.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        return yaml.safe_load(metin)
    except ImportError:
        return _ayristir(metin)


# ---------------------------------------------------------------------------
@dataclass
class ModelProfili:
    anahtar: str
    etiket: str = ""
    lisans: str = ""
    parametre: str = ""
    baglam: int = 8192
    motorlar: dict = field(default_factory=dict)
    dosyalar: dict = field(default_factory=dict)
    gereksinimler: dict = field(default_factory=dict)
    ornekleme: dict = field(default_factory=dict)
    yetenekler: list = field(default_factory=list)
    uyari: str = ""


@dataclass
class Ayarlar:
    ham: dict
    kok: Path = KOK

    @property
    def profil(self) -> dict:
        return self.ham.get("profil", {})

    @property
    def modeller(self) -> dict:
        return self.ham.get("modeller", {})

    @property
    def varsayilan_model(self) -> str:
        return self.ham.get("varsayilan_model", "gemma4-e4b")

    @property
    def calisma(self) -> dict:
        return self.ham.get("calisma", {})

    @property
    def araclar(self) -> dict:
        return self.ham.get("araclar", {})

    @property
    def sunucu(self) -> dict:
        return self.ham.get("sunucu", {})

    def model(self, anahtar: str | None = None) -> ModelProfili:
        anahtar = anahtar or self.varsayilan_model
        veri = self.modeller.get(anahtar)
        if veri is None:
            raise KeyError(
                f"'{anahtar}' modeli asistan.yaml içinde yok. "
                f"Seçenekler: {', '.join(self.modeller)}"
            )
        gecerli = {f for f in ModelProfili.__dataclass_fields__ if f != "anahtar"}
        return ModelProfili(anahtar=anahtar, **{k: v for k, v in veri.items() if k in gecerli})

    def yol(self, *parcalar: str) -> Path:
        return self.kok.joinpath(*parcalar)


def ayarlari_yukle(yol: str | Path | None = None) -> Ayarlar:
    yol = Path(yol) if yol else KOK / "asistan.yaml"
    return Ayarlar(ham=yaml_yukle(yol), kok=KOK)


def ortamdan() -> dict:
    """Ortam değişkenleriyle geçersiz kılma (KASA_MODEL, KASA_MODELS_DIR ...)."""
    gecersiz = {}
    if os.environ.get("KASA_MODEL"):
        gecersiz["model"] = os.environ["KASA_MODEL"]
    if os.environ.get("KASA_MODELS_DIR"):
        gecersiz["model_dizini"] = os.environ["KASA_MODELS_DIR"]
    return gecersiz
