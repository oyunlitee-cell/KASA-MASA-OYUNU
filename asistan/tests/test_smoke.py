"""KASA Asistan duman testleri.

Çalıştır:  PYTHONPATH=src python3 -m pytest tests -q
(Gerekirse: python3 -m pip install pytest)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))

from kasa_asistan import config as cfg            # noqa: E402
from kasa_asistan.agent import Asistan            # noqa: E402
from kasa_asistan.backends import ArkaUc          # noqa: E402
from kasa_asistan.tools import AracKutusu, arac_cagrisi_ayikla  # noqa: E402


# --------------------------------------------------------------------------- config
def test_yaml_yuklenir():
    a = cfg.ayarlari_yukle()
    assert a.varsayilan_model == "gemma4-e4b"
    assert set(a.modeller) >= {"gemma4-e4b", "gemma4-e2b", "qwen35-4b", "qwen3-4b"}


def test_model_profili():
    m = cfg.ayarlari_yukle().model("gemma4-e4b")
    assert m.lisans == "Apache-2.0"
    assert m.baglam == 128000
    assert "türkçe" in m.yetenekler
    assert m.motorlar["android"] == "litert-lm"


def test_satir_ici_liste_ve_yorum():
    a = cfg.ayarlari_yukle()
    assert "git" in a.araclar["izinli_komutlar"]
    assert isinstance(a.araclar["izinli_komutlar"], list)


def test_bilinmeyen_model():
    with pytest.raises(KeyError):
        cfg.ayarlari_yukle().model("olmayan-model")


# --------------------------------------------------------------------------- araçlar
def test_arac_blok_ayiklama():
    metin = 'Şunu okuyayım:\n```tool\n{"arac": "dosya_oku", "argumanlar": {"yol": "a.txt"}}\n```\n'
    cagri, temiz = arac_cagrisi_ayikla(metin)
    assert cagri["arac"] == "dosya_oku"
    assert "Şunu okuyayım" in temiz

    assert arac_cagrisi_ayikla("merhaba dünya")[0] is None
    assert arac_cagrisi_ayikla('```tool\n{bozuk json}\n```')[0] is None


def test_arac_kutusu_yazma_ve_traversal(tmp_path):
    kutu = AracKutusu(kok=tmp_path, izinli_komutlar=["ls"])
    assert "YAZILDI" in kutu.dosya_yaz("deneme.txt", "merhaba")
    assert "merhaba" in kutu.dosya_oku("deneme.txt")
    assert (tmp_path / "deneme.txt").exists()

    # çalışma dizini dışına çıkış engellenmeli
    with pytest.raises(Exception):
        kutu._coz("../../etc/passwd")
    assert "İzin" in kutu.cagir("dosya_oku", {"yol": "../../etc/passwd"})
    assert "İzin" in kutu.cagir("dosya_yaz", {"yol": "../kacis.txt", "icerik": "x"})
    assert not (tmp_path.parent / "kacis.txt").exists()


def test_komut_izin_listesi(tmp_path):
    kutu = AracKutusu(kok=tmp_path, izinli_komutlar=["ls", "git"])
    assert "izinli değil" in kutu.komut("rm", ["-rf", "/"])
    assert "engellendi" in kutu.komut("git", ["push"])


# --------------------------------------------------------------------------- ajan
class SahteArkaUc(ArkaUc):
    """Sırayla verilen yanıtları döndürür (araç döngüsünü test eder)."""

    ad = "sahte"
    gercek = False

    def __init__(self, yanitlar):
        super().__init__()
        self.yanitlar = list(yanitlar)
        self.gorulen = []

    def uret(self, mesajlar, akis=False, **kw):
        self.gorulen.append(list(mesajlar))
        return self.yanitlar.pop(0)


def _ajan(arka_uc, tmp_path):
    a = cfg.ayarlari_yukle()
    a.ham["araclar"]["calisma_dizini"] = str(tmp_path)
    a.ham["calisma"]["hafiza_dosyasi"] = str(tmp_path / "hafiza.md")
    a.ham["calisma"]["gecmis_dizini"] = str(tmp_path / "gecmis")
    ajan = Asistan(ayarlar=a, araclar_acik=True)
    ajan.arka_uc = arka_uc
    return ajan


def test_arac_dongusu_calisir(tmp_path, capsys):
    (tmp_path / "not.txt").write_text("ilk satır\n ikinci satır", encoding="utf-8")
    arka = SahteArkaUc([
        '```tool\n{"arac": "dosya_oku", "argumanlar": {"yol": "not.txt"}}\n```',
        "Dosyanda iki satır var: 'ilk satır' ve 'ikinci satır'.",
    ])
    ajan = _ajan(arka, tmp_path)
    yanit = ajan.yanit("not.txt içinde ne var?")
    assert "iki satır" in yanit
    assert "ARAC SONUCU" in arka.gorulen[-1][-1]["content"]


def test_arac_tur_siniri(tmp_path):
    """Model sürekli araç çağırırsa döngü en fazla `az_tur` kadar döner."""
    sonsuz = ['```tool\n{"arac": "dosya_liste", "argumanlar": {"yol": "."}}\n```'] * 10
    arka = SahteArkaUc(sonsuz)
    ajan = _ajan(arka, tmp_path)
    ajan.yanit("klasörü listele")
    assert len(arka.gorulen) <= ajan.az_tur + 1


def test_hafiza_yazilir(tmp_path):
    arka = SahteArkaUc(["tamam"])
    ajan = _ajan(arka, tmp_path)
    ajan.hatirla("Kullanıcı Konya'da yaşıyor ve Türkçe konuşuyor.")
    icerik = (tmp_path / "hafiza.md").read_text(encoding="utf-8")
    assert "Konya" in icerik
    assert "Konya" in ajan.kisilik.hafiza_ozeti


def test_gecmis_kaydi(tmp_path):
    arka = SahteArkaUc(["merhaba!"])
    ajan = _ajan(arka, tmp_path)
    ajan.yanit("selam")
    yol = ajan.kaydet()
    satirlar = [json.loads(s) for s in yol.read_text(encoding="utf-8").splitlines()]
    assert satirlar[-1]["role"] == "assistant"


def test_sistem_komutu_turkce_ve_aracli():
    arka = SahteArkaUc(["tamam"])
    ajan = _ajan(arka, Path(__file__).parent)
    sistem = ajan._sistem().icerik
    assert "Türkçe" in sistem
    assert "dosya_oku" in sistem
    assert "KASA" in sistem
