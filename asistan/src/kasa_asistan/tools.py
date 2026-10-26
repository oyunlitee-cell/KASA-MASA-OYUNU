"""Kod araçları — dosya okuma/yazma, arama ve sınırlı komut çalıştırma.

Güvenlik notu: Bu araçlar 4B'lık bir modelin eline veriliyor. O yüzden
kabuk (shell) serbest değil; izinli komut listesi var ve tüm dosya
işlemleri tek bir çalışma diziniyle sınırlı (path traversal engelleniyor).
"""

from __future__ import annotations

import fnmatch
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

ATLANAN_DIZINLER = {".git", "node_modules", "__pycache__", ".venv", "venv",
                    "build", "dist", ".mypy_cache", ".pytest_cache"}
IKILI_UZANTILAR = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip",
                   ".gguf", ".litertlm", ".bin", ".safetensors", ".so", ".mp3"}


class AracHatasi(Exception):
    pass


@dataclass
class AracKutusu:
    kok: Path
    izinli_komutlar: list[str] = field(default_factory=lambda: ["ls", "git", "cat"])
    zaman_asimi: int = 60
    maks_kb: int = 512
    yedekle: bool = True
    degisiklikler: list[str] = field(default_factory=list)

    # -- güvenlik ---------------------------------------------------------
    def _coz(self, yol: str) -> Path:
        p = (self.kok / yol).resolve() if not Path(yol).is_absolute() else Path(yol).resolve()
        if self.kok.resolve() not in p.parents and p != self.kok.resolve():
            raise AracHatasi(f"İzin yok: çalışma dizini dışına çıkamam ({yol})")
        return p

    # -- araçlar ----------------------------------------------------------
    def dosya_oku(self, yol: str, limit: int = 400) -> str:
        p = self._coz(yol)
        if not p.exists():
            return f"HATA: dosya yok: {yol}"
        if p.suffix.lower() in IKILI_UZANTILAR:
            return f"HATA: {yol} ikili (binary) dosya, okunamaz."
        if p.stat().st_size > self.maks_kb * 1024:
            return f"HATA: {yol} çok büyük ({p.stat().st_size//1024} KB)."
        satirlar = p.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(satirlar) > limit:
            satirlar = satirlar[:limit] + [f"... ({len(satirlar)-limit} satır daha)"]
        numarali = "\n".join(f"{i+1:4d}| {s}" for i, s in enumerate(satirlar))
        return f"=== {yol} ===\n{numarali}"

    def dosya_yaz(self, yol: str, icerik: str) -> str:
        p = self._coz(yol)
        p.parent.mkdir(parents=True, exist_ok=True)
        if self.yedekle and p.exists():
            p.rename(p.with_suffix(p.suffix + ".bak"))
        p.write_text(icerik, encoding="utf-8")
        self.degisiklikler.append(str(p.relative_to(self.kok)))
        return f"YAZILDI: {p.relative_to(self.kok)} ({len(icerik)} karakter)"

    def dosya_liste(self, yol: str = ".", derinlik: int = 3) -> str:
        p = self._coz(yol)
        if not p.is_dir():
            return f"HATA: klasör değil: {yol}"
        cikti = []
        for dosya in sorted(p.rglob("*")):
            if any(k in dosya.parts for k in ATLANAN_DIZINLER):
                continue
            if len(dosya.relative_to(p).parts) > derinlik:
                continue
            if dosya.is_dir():
                cikti.append(f"d {dosya.relative_to(p)}/")
            else:
                cikti.append(f"- {dosya.relative_to(p)}  ({dosya.stat().st_size//1024} KB)")
            if len(cikti) > 200:
                cikti.append("... (liste kısaltıldı)")
                break
        return "\n".join(cikti) or "(boş klasör)"

    def ara(self, desen: str, yol: str = ".", en_fazla: int = 20) -> str:
        p = self._coz(yol)
        bulunan = []
        try:
            regex = re.compile(desen, re.IGNORECASE)
        except re.error as e:
            return f"HATA: geçersiz desen: {e}"
        for dosya in p.rglob("*"):
            if not dosya.is_file() or any(k in dosya.parts for k in ATLANAN_DIZINLER):
                continue
            if dosya.suffix.lower() in IKILI_UZANTILAR or dosya.stat().st_size > 512 * 1024:
                continue
            try:
                metin = dosya.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for no, satir in enumerate(metin.splitlines(), 1):
                if regex.search(satir):
                    bulunan.append(f"{dosya.relative_to(self.kok)}:{no}: {satir.strip()[:160]}")
                    break
            if len(bulunan) >= en_fazla:
                break
        return "\n".join(bulunan) or "bulunamadı"

    def komut(self, komut: str, argumanlar: list[str] | None = None) -> str:
        argumanlar = list(argumanlar or [])
        if komut not in self.izinli_komutlar:
            return (f"HATA: '{komut}' izinli değil. "
                    f"İzinli komutlar: {', '.join(self.izinli_komutlar)}")
        guvenli = {"komut": komut, "argumanlar": argumanlar}
        if guvenli["komut"] == "git" and any(a in ("push", "remote") for a in argumanlar):
            return "HATA: git push / remote değişiklikleri engellendi."
        try:
            out = subprocess.run(
                [komut, *[str(a) for a in argumanlar]],
                cwd=str(self.kok), capture_output=True, text=True,
                timeout=self.zaman_asimi, shell=False,
            )
        except subprocess.TimeoutExpired:
            return f"HATA: zaman aşımı ({self.zaman_asimi}s)"
        except FileNotFoundError:
            return f"HATA: komut bulunamadı: {komut}"
        cikti = (out.stdout or "") + (("\nSTDERR:\n" + out.stderr) if out.stderr else "")
        return (cikti[:4000] or "(çıktı yok)") + f"\n[çıkış kodu: {out.returncode}]"

    # -- dağıtım ----------------------------------------------------------
    def cagir(self, ad: str, argumanlar: dict | None = None) -> str:
        argumanlar = argumanlar or {}
        tablo = {
            "dosya_oku": lambda: self.dosya_oku(argumanlar.get("yol", "")),
            "dosya_yaz": lambda: self.dosya_yaz(argumanlar.get("yol", ""), argumanlar.get("icerik", "")),
            "dosya_liste": lambda: self.dosya_liste(argumanlar.get("yol", ".")),
            "ara": lambda: self.ara(argumanlar.get("desen", ""), argumanlar.get("yol", ".")),
            "komut": lambda: self.komut(argumanlar.get("komut", ""), argumanlar.get("argumanlar")),
        }
        if ad not in tablo:
            return f"HATA: bilinmeyen araç '{ad}'. Geçerli araçlar: {', '.join(tablo)}"
        try:
            return tablo[ad]()
        except AracHatasi as e:
            return f"HATA: {e}"
        except Exception as e:  # noqa: BLE001
            return f"HATA: {type(e).__name__}: {e}"


ARAC_ADLARI = ["dosya_oku", "dosya_yaz", "dosya_liste", "ara", "komut"]

ARAC_BLOK = re.compile(r"```tool\s*(\{.*?\})\s*```", re.DOTALL)


def arac_cagrisi_ayikla(metin: str) -> tuple[dict | None, str]:
    """Model çıktısından araç çağrısı yakalar.

    Dönen: (cagri veya None, çağrı dışında kalan temiz metin)
    """
    eslesme = ARAC_BLOK.search(metin or "")
    if not eslesme:
        return None, metin
    import json
    try:
        cagri = json.loads(eslesme.group(1))
    except json.JSONDecodeError:
        return None, metin
    if not isinstance(cagri, dict) or "arac" not in cagri:
        return None, metin
    temiz = (metin[:eslesme.start()] + metin[eslesme.end():]).strip()
    return cagri, temiz
