"""Çıkarım (inference) motorları.

Üç arka uç var:

1. LlamaCppBackend  — gerçek model. llama-cpp-python kuruluysa GGUF çalıştırır.
                      Telefonda Termux, masaüstünde doğrudan çalışır.
2. LiteRtBackend    — Google AI Edge LiteRT-LM (Android'deki asıl hedef).
                      Bu depo bir Python paketi değil; Android tarafı
                      docs/ANDROID-KURULUM.md içinde anlatılıyor.
3. DemoBackend      — model dosyası yokken arayüzü/akışı denemek için.
                      Türkçe hazır yanıtlar döner, KENDİNİ ASLA GERÇEK
                      MODEL OLARAK TANITMAZ.

Hiçbiri kurulu değilse bile import hatası vermez; çağrıldığında net mesaj verir.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


class ArkaUcHatasi(RuntimeError):
    pass


@dataclass
class Uretilen:
    metin: str
    token_sayisi: int = 0
    sure_saniye: float = 0.0

    @property
    def token_hizi(self) -> float:
        return (self.token_sayisi / self.sure_saniye) if self.sure_saniye > 0 else 0.0


class ArkaUc:
    """Tüm arka uçların ortak arayüzü."""

    ad = "temel"
    gercek = False

    def __init__(self, **kwargs: Any) -> None:
        self.ayarlar = kwargs

    def hazirla(self) -> None:
        """Modeli belleğe al (tembel çağrılır)."""

    def uret(self, mesajlar: list[dict], akis: bool = False, **kw: Any):
        metin = self._tamamlama(mesajlar, **kw)
        if akis:
            def _parca():
                for kelime in re.findall(r"\S+\s*", metin):
                    yield kelime
            return _parca()
        return metin

    def uret_stream(self, mesajlar: list[dict], **kw: Any) -> Iterator[str]:
        """Token token akış. Varsayılan: tam yanıtı kelimelere böler."""
        metin = self._tamamlama(mesajlar, **kw)
        for kelime in re.findall(r"\S+\s*", metin):
            yield kelime

    def _tamamlama(self, mesajlar: list[dict], **kw: Any) -> str:
        raise NotImplementedError

    def bilgi(self) -> dict:
        return {"arka_uc": self.ad, "gercek_model": self.gercek}


# ---------------------------------------------------------------------------
class LlamaCppBackend(ArkaUc):
    """GGUF modelleri için llama.cpp (llama-cpp-python üzerinden)."""

    ad = "llama-cpp"
    gercek = True

    def __init__(self, model_yolu: str | Path, n_ctx: int = 8192,
                 n_threads: int = 4, n_gpu_layers: int = -1, **kw: Any) -> None:
        super().__init__(**kw)
        self.model_yolu = Path(model_yolu)
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers
        self._llm = None

    def hazirla(self) -> None:
        if self._llm is not None:
            return
        if not self.model_yolu.exists():
            raise ArkaUcHatasi(
                f"Model dosyası yok: {self.model_yolu}\n"
                f"İndirmek için: bash asistan/modeller/indir.sh"
            )
        try:
            from llama_cpp import Llama
        except ImportError as e:  # pragma: no cover
            raise ArkaUcHatasi(
                "llama-cpp-python kurulu değil.\n"
                "  python3 -m pip install llama-cpp-python\n"
                "Termux'ta: pkg install cmake && pip install llama-cpp-python"
            ) from e
        self._llm = Llama(
            model_path=str(self.model_yolu),
            n_ctx=self.n_ctx,
            n_threads=self.n_threads,
            n_gpu_layers=self.n_gpu_layers,
            verbose=False,
        )

    def uret(self, mesajlar: list[dict], akis: bool = False, **kw: Any):
        self.hazirla()
        assert self._llm is not None
        basla = time.time()
        if akis:
            return self._akis(mesajlar, basla, **kw)
        cvp = self._llm.create_chat_completion(
            messages=mesajlar,
            temperature=kw.get("temperature", 0.7),
            top_p=kw.get("top_p", 0.95),
            top_k=kw.get("top_k", 40),
            max_tokens=kw.get("max_tokens", 1024),
        )
        metin = cvp["choices"][0]["message"]["content"] or ""
        kullan = cvp.get("usage", {}) or {}
        return Uretilen(
            metin=metin,
            token_sayisi=kullan.get("completion_tokens", 0),
            sure_saniye=time.time() - basla,
        )

    def uret_stream(self, mesajlar: list[dict], **kw: Any) -> Iterator[str]:
        self.hazirla()
        assert self._llm is not None
        akis = self._llm.create_chat_completion(
            messages=mesajlar,
            temperature=kw.get("temperature", 0.7),
            top_p=kw.get("top_p", 0.95),
            top_k=kw.get("top_k", 40),
            max_tokens=kw.get("max_tokens", 1024),
            stream=True,
        )
        for parca in akis:
            delta = parca.get("choices", [{}])[0].get("delta", {})
            if delta.get("content"):
                yield delta["content"]

    def _akis(self, mesajlar: list[dict], basla: float, **kw) -> Iterator[str]:
        assert self._llm is not None
        akis = self._llm.create_chat_completion(
            messages=mesajlar,
            temperature=kw.get("temperature", 0.7),
            top_p=kw.get("top_p", 0.95),
            top_k=kw.get("top_k", 40),
            max_tokens=kw.get("max_tokens", 1024),
            stream=True,
        )
        for parca in akis:
            delta = parca.get("choices", [{}])[0].get("delta", {})
            if delta.get("content"):
                yield delta["content"]

    def bilgi(self) -> dict:
        return {
            "arka_uc": self.ad,
            "gercek_model": True,
            "model_yolu": str(self.model_yolu),
            "baglam": self.n_ctx,
        }


# ---------------------------------------------------------------------------
class LlamaServerBackend(ArkaUc):
    """Telefonda çalışan `llama-server` ile konuşur (OpenAI uyumlu HTTP).

    NEDEN BU VAR — Android'de asıl yol budur:
      * Telefonda C++ derlemek gerekmez. llama.cpp'nin resmî Android arm64
        ikilisi indirilip çalıştırılır (77 MB), modeli o yükler.
      * Python tarafı saf standart kütüphane kalır → Termux'ta pip derlemesi yok.
      * Yeni model mimarileri (Gemma 4, Qwen3.5) llama-server ile anında gelir;
        Python bağlayıcısının sürümünü beklemek gerekmez.

    Sadece `urllib` kullanır: telefon-önizleme uyumu ve bağımlılıksızlık için.
    """

    ad = "llama-server"
    gercek = True

    def __init__(self, taban_url: str = "http://127.0.0.1:8081",
                 model_adi: str | None = None, zaman_asimi: int = 900, **kw: Any) -> None:
        super().__init__(**kw)
        self.taban_url = taban_url.rstrip("/")
        self.model_adi = model_adi
        self.zaman_asimi = zaman_asimi

    # ------------------------------------------------------------------
    def saglik(self, zaman_asimi: int = 3) -> bool:
        """llama-server ayakta mı? (GET /health -> 200 {"status":"ok"})"""
        import urllib.error
        import urllib.request

        try:
            with urllib.request.urlopen(f"{self.taban_url}/health",
                                        timeout=zaman_asimi) as y:
                return y.status == 200
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def _istek(self, yol: str, veri: dict):
        import urllib.request

        govde = json.dumps(veri, ensure_ascii=False).encode("utf-8")
        istek = urllib.request.Request(
            f"{self.taban_url}{yol}", data=govde, method="POST",
            headers={"Content-Type": "application/json"},
        )
        return urllib.request.urlopen(istek, timeout=self.zaman_asimi)

    def hazirla(self) -> None:
        if not self.saglik(zaman_asimi=10):
            raise ArkaUcHatasi(
                f"llama-server'e ulaşamadım: {self.taban_url}\n"
                "Telefonda sırayla çalıştır:\n"
                "  bash asistan/android/baslat.sh\n"
                "(Baslat.sh önce llama-server'ı, sonra bu asistanı açar.)"
            )

    # ------------------------------------------------------------------
    def uret(self, mesajlar: list[dict], akis: bool = False, **kw: Any):
        if akis:
            return self.uret_stream(mesajlar, **kw)
        basla = time.time()
        veri = {"messages": mesajlar, "stream": False, **self._parametreler(kw)}
        if self.model_adi:
            veri["model"] = self.model_adi
        try:
            with self._istek("/v1/chat/completions", veri) as y:
                cvp = json.loads(y.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            raise ArkaUcHatasi(f"llama-server hatası: {e}") from e
        metin = (cvp.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
        kullan = cvp.get("usage") or {}
        return Uretilen(
            metin=metin,
            token_sayisi=kullan.get("completion_tokens", 0),
            sure_saniye=time.time() - basla,
        )

    def uret_stream(self, mesajlar: list[dict], **kw: Any) -> Iterator[str]:
        veri = {"messages": mesajlar, "stream": True, **self._parametreler(kw)}
        if self.model_adi:
            veri["model"] = self.model_adi
        try:
            yanit = self._istek("/v1/chat/completions", veri)
        except Exception as e:  # noqa: BLE001
            raise ArkaUcHatasi(f"llama-server hatası: {e}") from e
        with yanit:
            for ham in yanit:
                satir = ham.decode("utf-8", "replace").strip()
                if not satir.startswith("data:"):
                    continue
                govde = satir[5:].strip()
                if govde == "[DONE]":
                    break
                try:
                    parca = json.loads(govde)
                except json.JSONDecodeError:
                    continue
                secim = (parca.get("choices") or [{}])[0]
                delta = secim.get("delta") or {}
                icerik = delta.get("content")
                if icerik:
                    yield icerik

    def _parametreler(self, kw: dict) -> dict:
        return {
            "temperature": kw.get("temperature", 1.0),
            "top_p": kw.get("top_p", 0.95),
            "top_k": kw.get("top_k", 64),
            "max_tokens": kw.get("max_tokens", 1024),
        }

    def bilgi(self) -> dict:
        return {"arka_uc": self.ad, "gercek_model": True,
                "sunucu": self.taban_url}


class LiteRtBackend(ArkaUc):
    """Google AI Edge LiteRT-LM — Android/iOS hedefi.

    Python tarafında `litert-lm` CLI'si bir köprü olarak kullanılabilir;
    asıl üretim yolu Kotlin/Swift. Buradaki sınıf, sunucu tarafında aynı
    modelin litertlm dosyası bulunduğunda CLI üzerinden çağırmak için var.
    """

    ad = "litert-lm"
    gercek = True

    def __init__(self, model_yolu: str | Path, **kw: Any) -> None:
        super().__init__(**kw)
        self.model_yolu = Path(model_yolu)

    def _tamamlama(self, mesajlar: list[dict], **kw: Any) -> str:
        import shutil
        import subprocess

        if not shutil.which("litert-lm"):
            raise ArkaUcHatasi(
                "litert-lm bulunamadı. Android'de LiteRT-LM kullanmak için "
                "docs/ANDROID-KURULUM.md dosyasına bak; masaüstünde GGUF + "
                "llama.cpp daha pratiktir."
            )
        komut = ["litert-lm", "run", str(self.model_yolu), "--prompt", mesajlar[-1]["content"]]
        out = subprocess.run(komut, capture_output=True, text=True, timeout=600)
        if out.returncode != 0:
            raise ArkaUcHatasi(out.stderr.strip() or "litert-lm hata verdi")
        return out.stdout.strip()


# ---------------------------------------------------------------------------
DEMO_YANITLAR = [
    ("Merhaba! Ben KASA. Şu an DEMO modundayım: arkada gerçek bir dil modeli "
     "yüklü değil, hazır yanıtlar dönüyorum.\n\n"
     "Gerçek modeli çalıştırmak için:\n"
     "1) `bash asistan/modeller/indir.sh` (Gemma 4 E4B, ~3.7 GB)\n"
     "2) `python3 -m kasa_asistan.cli --model gemma4-e4b`\n\n"
     "Bu arada arayüzü, araçları ve sohbet akışını rahatça test edebilirsin."),
    "DEMO: Bu yanıt kalıptan geliyor. Model yüklendiğinde burada gerçek üretim olacak.",
]


class DemoBackend(ArkaUc):
    """Model yokken arayüzü denemek için deterministic Türkçe yanıtlar."""

    ad = "demo"
    gercek = False
    _sayac = 0

    def _tamamlama(self, mesajlar: list[dict], **kw: Any) -> str:
        son = (mesajlar[-1]["content"] or "").strip()
        alt = son.lower()

        if any(k in alt for k in ("merhaba", "selam", "sa ", "naber")):
            return ("Merhaba! Ben KASA, yanındaki çevrimdışı asistanım. "
                    "(DEMO modu — model yüklü değil.) Sana nasıl yardımcı olayım?")
        if "?" in son and any(k in alt for k in ("nasıl", "nedir", "ne ", "kim")):
            return ("DEMO yanıtı: gerçek model yüklendiğinde soruna doğrudan cevap veririm. "
                    "Şu an arkada model yok; `asistan/modeller/indir.sh` ile Gemma 4 E4B'yi "
                    "indirip tekrar dene.")
        if any(k in alt for k in ("kod", "python", "fonksiyon", "hata", "debug")):
            return ("DEMO: Kod isteklerinde dosyaları okuyup yazabilirim. Gerçek model "
                    "yüklendiğinde `dosya_oku` / `dosya_yaz` araçlarımı kullanırım.")
        DemoBackend._sayac += 1
        return DEMO_YANITLAR[DemoBackend._sayac % len(DEMO_YANITLAR)]

    def bilgi(self) -> dict:
        return {"arka_uc": self.ad, "gercek_model": False,
                "not": "Model yüklü değil — demo yanıtları"}


# ---------------------------------------------------------------------------
def gguf_bul(model_dizini: Path, desen: str = "*.gguf") -> Path | None:
    dosyalar = sorted(Path(model_dizini).rglob(desen))
    return dosyalar[0] if dosyalar else None


def arka_uc_kur(ayarlar, model_anahtari: str | None = None, zorla: str | None = None,
                demo_izin: bool = True):
    """Ayarlara ve diskteki dosyalara bakıp uygun arka ucu döndürür.

    Sıra (Android için tasarlandı):
      1. llama-server (Termux'ta çalışan resmî Android ikilisi) — derleme yok
      2. Yerel GGUF + llama-cpp-python                           — derleme var
      3. Demo                                                     — sadece izinliyse
    """
    import os

    from .config import Ayarlar  # yerel import (döngüyü önler)

    assert isinstance(ayarlar, Ayarlar)
    anahtar = model_anahtari or ayarlar.varsayilan_model
    profil = ayarlar.model(anahtar)
    dizin = ayarlar.yol(ayarlar.calisma.get("model_dizini", "models"))
    cal = ayarlar.calisma

    if zorla == "demo":
        return DemoBackend(), profil

    # 1) llama-server — ortam değişkeni veya yapılandırma ile
    sunucu_url = (os.environ.get("KASA_LLAMA_SUNUCU")
                  or cal.get("llama_sunucu_url") or "")
    if zorla == "llama-server":
        return LlamaServerBackend(str(sunucu_url or "http://127.0.0.1:8081")), profil
    if sunucu_url:
        aday = LlamaServerBackend(str(sunucu_url))
        if aday.saglik():
            return aday, profil

    # 2) LiteRT-LM dosyası varsa CLI köprüsü
    litertlm = list(Path(dizin).rglob("*.litertlm"))
    if zorla == "litert-lm" or (litertlm and zorla is None and not gguf_bul(dizin)):
        return LiteRtBackend(litertlm[0] if litertlm else dizin), profil

    # 3) Yerel GGUF
    gguf = gguf_bul(dizin)
    if gguf is not None:
        istenen = int(cal.get("baglam_penceresi", 8192))
        n_ctx = min(int(profil.baglam or istenen), istenen) if profil.baglam else istenen
        return LlamaCppBackend(
            model_yolu=gguf,
            n_ctx=n_ctx,
            n_threads=int(cal.get("is_parcacigi", 4)),
            n_gpu_layers=int(cal.get("gpu_katmanlari", -1)),
        ), profil

    # 4) Hiçbiri yok
    if not demo_izin:
        raise ArkaUcHatasi(
            "Gerçek model bulunamadı — demo modu kapalı (--demo-yok).\n"
            "Telefonda:  bash asistan/android/baslat.sh\n"
            "Masaüstünde: bash asistan/modeller/indir.sh"
        )
    return DemoBackend(), profil
