"""KASA Asistan HTTP sunucusu.

Standart kütüphaneyle yazıldı (FastAPI/Flask yok) — Termux'ta tek komutla
çalışsın diye. Üç arayüz sunar:

  GET  /                      -> Türkçe sohbet arayüzü (web/index.html)
  GET  /api/durum             -> model/arka uç bilgisi
  POST /api/sohbet            -> SSE akışlı sohbet (arayüz bunu kullanır)
  POST /v1/chat/completions   -> OpenAI uyumlu uç (SillyTavern, Continue,
                                 Open WebUI, kendi kodun gibi istemciler için)
  GET  /v1/models             -> OpenAI uyumlu model listesi
"""

from __future__ import annotations

import argparse
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .agent import Asistan
from .config import ayarlari_yukle

WEB_DIZIN = Path(__file__).resolve().parents[2] / "web"


class Sunucu:
    def __init__(self, asistan: Asistan) -> None:
        self.asistan = asistan
        self.kilit = threading.Lock()          # model tek seferde bir istek
        self.baslangic = time.time()

    # ------------------------------------------------------------------
    def sohbet(self, mesaj: str, akis: bool = True):
        with self.kilit:
            if akis:
                for parca in self.asistan.yanit_akis(mesaj):
                    yield parca
            else:
                yield self.asistan.yanit(mesaj)

    def durum(self) -> dict:
        d = self.asistan.durum()
        d["calisma_suresi_saniye"] = int(time.time() - self.baslangic)
        d["sunucu"] = "KASA Asistan"
        return d


MIME = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png",
        ".json": "application/json; charset=utf-8", ".ico": "image/x-icon"}


def isleyici_olustur(sunucu: Sunucu):
    class Isleyici(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        # --- yardımcılar -------------------------------------------------
        def log_message(self, *args):  # sessiz
            pass

        def _cors(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")

        def _json(self, veri: Any, kod: int = 200) -> None:
            govde = json.dumps(veri, ensure_ascii=False).encode("utf-8")
            self.send_response(kod)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(govde)))
            self._cors()
            self.end_headers()
            self.wfile.write(govde)

        def _sse(self, olaylar) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            # Kapatmayı kendimiz yönetiyoruz: yarıda kesilen akış bağlantıyı
            # yeniden kullanıma bırakırsa protokol karışır.
            self.send_header("Connection", "close")
            self.close_connection = True
            self._cors()
            self.end_headers()
            try:
                for parca in olaylar:
                    if self.wfile.closed:
                        break
                    veri = json.dumps({"tur": "parca", "metin": parca}, ensure_ascii=False)
                    self.wfile.write(f"data: {veri}\n\n".encode("utf-8"))
                    self.wfile.flush()
                bitti = json.dumps({
                    "tur": "bitti",
                    "istatistik": {
                        "token": sunucu.asistan.istatistik.get("son_token", 0),
                        "hiz": sunucu.asistan.istatistik.get("son_hiz", 0),
                    },
                }, ensure_ascii=False)
                self.wfile.write(f"data: {bitti}\n\n".encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                # Kullanıcı sekmeyi kapattıysa üreteç yarıda kalır. Kapatmazsak
                # `with self.kilit` bloğu açık kalır ve SONRAKİ istek sonsuza
                # kadar bekler.
                kapat = getattr(olaylar, "close", None)
                if kapat is not None:
                    try:
                        kapat()
                    except (BrokenPipeError, ConnectionResetError, RuntimeError):
                        pass

        def _govde(self) -> dict:
            uzunluk = int(self.headers.get("Content-Length") or 0)
            if not uzunluk:
                return {}
            try:
                return json.loads(self.rfile.read(uzunluk).decode("utf-8"))
            except json.JSONDecodeError:
                return {}

        # --- rotalar -----------------------------------------------------
        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self) -> None:
            yol = self.path.split("?")[0]

            if yol in ("/", "/index.html"):
                dosya = WEB_DIZIN / "index.html"
                govde = dosya.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", MIME[".html"])
                self.send_header("Content-Length", str(len(govde)))
                self.end_headers()
                self.wfile.write(govde)
                return

            if yol == "/api/durum":
                self._json(sunucu.durum())
                return

            if yol == "/v1/models":
                d = sunucu.asistan.durum()
                self._json({"object": "list", "data": [{
                    "id": d["model"], "object": "model", "created": int(sunucu.baslangic),
                    "owned_by": "kasa-asistan",
                }]})
                return

            if yol.startswith("/web/") or yol.startswith("/static/"):
                ad = Path(yol).name
                dosya = WEB_DIZIN / ad
                if dosya.exists():
                    govde = dosya.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", MIME.get(dosya.suffix, "application/octet-stream"))
                    self.send_header("Content-Length", str(len(govde)))
                    self.end_headers()
                    self.wfile.write(govde)
                    return

            self._json({"hata": "bulunamadı", "yol": yol}, 404)

        def do_POST(self) -> None:
            yol = self.path.split("?")[0]
            govde = self._govde()

            if yol == "/api/sohbet":
                mesaj = (govde.get("mesaj") or "").strip()
                if not mesaj:
                    self._json({"hata": "mesaj boş"}, 400)
                    return
                self._sse(sunucu.sohbet(mesaj))
                return

            if yol == "/v1/chat/completions":
                mesajlar = govde.get("messages") or []
                if not mesajlar:
                    self._json({"hata": "messages boş"}, 400)
                    return
                son = ""
                for m in mesajlar:
                    if m.get("role") == "user":
                        son = m.get("content", "")
                tam = "".join(sunucu.sohbet(son, akis=False))
                self._json({
                    "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": sunucu.asistan.durum()["model"],
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": tam},
                        "finish_reason": "stop",
                    }],
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": sunucu.asistan.istatistik.get("son_token", 0),
                        "total_tokens": sunucu.asistan.istatistik.get("son_token", 0),
                    },
                })
                return

            if yol == "/api/hatirla":
                bilgi = (govde.get("bilgi") or "").strip()
                if not bilgi:
                    self._json({"hata": "bilgi boş"}, 400)
                    return
                self._json({"sonuc": sunucu.asistan.hatirla(bilgi)})
                return

            self._json({"hata": "bulunamadı", "yol": yol}, 404)

    return Isleyici


def calistir(host: str = "0.0.0.0", port: int = 8080, model: str | None = None,
             araclar: bool = True, yapilandirma: str | None = None,
             demo_izin: bool = True) -> None:
    try:
        asistan = Asistan(
            ayarlar=ayarlari_yukle(yapilandirma),
            model_anahtari=model,
            araclar_acik=araclar,
            demo_izin=demo_izin,
        )
    except Exception as e:  # noqa: BLE001
        from .backends import ArkaUcHatasi
        if isinstance(e, ArkaUcHatasi):
            print("\n" + str(e) + "\n")
            raise SystemExit(2) from e
        raise
    sunucu = Sunucu(asistan)
    httpd = ThreadingHTTPServer((host, port), isleyici_olustur(sunucu))
    d = asistan.durum()
    print("─" * 62)
    print("  KASA Asistan hazır")
    print(f"  Model    : {d['etiket']}  [{d['model']}]  · lisans {d['lisans']}")
    print(f"  Arka uç  : {d['arka_uc']}  · gerçek model: {d['gercek_model']}")
    if not d["gercek_model"]:
        print("  ⚠  DEMO modu — gerçek model yok (hazır yanıtlar).")
        print("     Android: bash asistan/android/baslat.sh")
        print("     Masaüstü: bash asistan/modeller/indir.sh")
    print(f"  Arayüz   : http://localhost:{port}/")
    print(f"  OpenAI   : http://localhost:{port}/v1/chat/completions")
    print("─" * 62)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nKapatılıyor...")
        httpd.shutdown()


def ana() -> None:
    p = argparse.ArgumentParser(description="KASA Asistan sunucusu")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--model", default=None, help="asistan.yaml içindeki model anahtarı")
    p.add_argument("--arac-kapali", action="store_true", help="dosya/komut araçlarını kapat")
    p.add_argument("--demo-yok", action="store_true",
                   help="gerçek model yoksa başlatmayı reddet (demo kapalı)")
    p.add_argument("--yapilandirma", default=None)
    a = p.parse_args()
    calistir(host=a.host, port=a.port, model=a.model,
             araclar=not a.arac_kapali, yapilandirma=a.yapilandirma,
             demo_izin=not a.demo_yok)


if __name__ == "__main__":
    ana()
