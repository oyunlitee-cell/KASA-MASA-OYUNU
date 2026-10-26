"""llama-server (HTTP) arka ucu testleri.

Telefonda çalışan llama-server'ın OpenAI uyumlu arayüzünü taklit eden küçük
bir sahte sunucu ayağa kaldırıp gerçek HTTP üzerinden konuşuruz. Böylece
istemci kodu ve araç döngüsü gerçek soketlerle doğrulanır.
"""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))

from kasa_asistan import config as cfg                       # noqa: E402
from kasa_asistan.agent import Asistan                        # noqa: E402
from kasa_asistan.backends import (                           # noqa: E402
    ArkaUcHatasi, DemoBackend, LlamaServerBackend, arka_uc_kur,
)


# --------------------------------------------------------------------------- sahte sunucu
class SahteLlamaSunucu:
    """llama-server taklidi: /health, /v1/chat/completions (akışlı + akışsız)."""

    def __init__(self, yanitlar: list[str]) -> None:
        self.yanitlar = list(yanitlar)
        self.istekler: list[dict] = []
        self.kapali = False
        sahip = self

        class Isleyici(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def do_GET(self):
                if sahip.kapali:
                    self.send_error(503)
                    return
                if self.path == "/health":
                    govde = b'{"status":"ok"}'
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(govde)))
                    self.end_headers()
                    self.wfile.write(govde)
                    return
                self.send_error(404)

            def do_POST(self):
                uzunluk = int(self.headers.get("Content-Length") or 0)
                veri = json.loads(self.rfile.read(uzunluk) or b"{}")
                sahip.istekler.append(veri)
                metin = sahip.yanitlar.pop(0) if sahip.yanitlar else "..."
                if veri.get("stream"):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Transfer-Encoding", "chunked")
                    self.end_headers()
                    for parca in [metin[i:i + 5] for i in range(0, len(metin), 5)]:
                        olay = json.dumps({"choices": [{"delta": {"content": parca}}]})
                        ham = f"data: {olay}\n\n".encode()
                        self.wfile.write(f"{len(ham):X}\r\n".encode() + ham + b"\r\n")
                        self.wfile.flush()
                    son = b"data: [DONE]\n\n"
                    self.wfile.write(f"{len(son):X}\r\n".encode() + son + b"\r\n")
                    self.wfile.write(b"0\r\n\r\n")
                    self.wfile.flush()
                else:
                    govde = json.dumps({
                        "choices": [{"message": {"role": "assistant", "content": metin}}],
                        "usage": {"completion_tokens": 7},
                    }).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(govde)))
                    self.end_headers()
                    self.wfile.write(govde)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Isleyici)
        self.port = self.httpd.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.islec = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.islec.start()

    def kapat(self):
        self.kapali = True
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def sunucu():
    s = SahteLlamaSunucu(["Merhaba! Ben KASA."])
    yield s
    s.kapat()


# --------------------------------------------------------------------------- arka uç
def test_saglik_kontrolu(sunucu):
    assert LlamaServerBackend(sunucu.url).saglik() is True


def test_erisilemeyen_sunucu_saglik_false():
    assert LlamaServerBackend("http://127.0.0.1:1").saglik() is False


def test_aksissiz_yanit(sunucu):
    arka = LlamaServerBackend(sunucu.url)
    sonuc = arka.uret([{"role": "user", "content": "selam"}], akis=False)
    assert sonuc.metin == "Merhaba! Ben KASA."
    assert sonuc.token_sayisi == 7
    assert sunucu.istekler[-1]["stream"] is False
    assert sunucu.istekler[-1]["messages"][0]["content"] == "selam"


def test_akilli_akis_parcalari_birlestirir(sunucu):
    arka = LlamaServerBackend(sunucu.url)
    parcalar = list(arka.uret_stream([{"role": "user", "content": "selam"}]))
    assert len(parcalar) > 1                       # gerçekten parça parça geldi
    assert "".join(parcalar) == "Merhaba! Ben KASA."
    assert sunucu.istekler[-1]["stream"] is True


def test_sunucu_yoksa_net_hata():
    arka = LlamaServerBackend("http://127.0.0.1:1", zaman_asimi=1)
    with pytest.raises(ArkaUcHatasi):
        arka.hazirla()
    with pytest.raises(ArkaUcHatasi):
        arka.uret([{"role": "user", "content": "x"}], akis=False)


# --------------------------------------------------------------------------- seçim mantığı
def _ayarlar(tmp_path):
    a = cfg.ayarlari_yukle()
    a.ham["calisma"]["model_dizini"] = str(tmp_path / "models")
    a.ham["calisma"]["hafiza_dosyasi"] = str(tmp_path / "hafiza.md")
    a.ham["calisma"]["gecmis_dizini"] = str(tmp_path / "gecmis")
    a.ham["araclar"]["calisma_dizini"] = str(tmp_path)
    return a


def test_llama_sunucu_onde_gelir(tmp_path, sunucu, monkeypatch):
    """llama-server ayaktaysa yerel GGUF'a tercih edilir (Android yolu)."""
    a = _ayarlar(tmp_path)
    monkeypatch.setenv("KASA_LLAMA_SUNUCU", sunucu.url)
    arka, _ = arka_uc_kur(a)
    assert isinstance(arka, LlamaServerBackend)


def test_sunucu_yoksa_gguf_ya_da_demo(tmp_path, monkeypatch):
    a = _ayarlar(tmp_path)
    monkeypatch.setenv("KASA_LLAMA_SUNUCU", "http://127.0.0.1:1")
    arka, _ = arka_uc_kur(a)
    assert isinstance(arka, DemoBackend)           # model dosyası da yok


def test_demo_yok_ise_hata(tmp_path, monkeypatch):
    """--demo-yok: gerçek model yoksa sessizce demo'ya düşmez."""
    a = _ayarlar(tmp_path)
    monkeypatch.delenv("KASA_LLAMA_SUNUCU", raising=False)
    with pytest.raises(ArkaUcHatasi):
        arka_uc_kur(a, demo_izin=False)


# --------------------------------------------------------------------------- ajan <-> sunucu
def test_ajan_llama_server_ile_akar(tmp_path, sunucu, monkeypatch):
    monkeypatch.setenv("KASA_LLAMA_SUNUCU", sunucu.url)
    ajan = Asistan(ayarlar=_ayarlar(tmp_path), demo_izin=False)
    assert ajan.durum()["arka_uc"] == "llama-server"
    assert ajan.durum()["gercek_model"] is True
    assert ajan.durum()["mod"] == "gercek"

    parcalar = list(ajan.yanit_akis("Merhaba"))
    assert "".join(parcalar).strip() == "Merhaba! Ben KASA."
    assert len(parcalar) > 1


def test_arac_cagrisi_ekrana_basilmaz(tmp_path, sunucu, monkeypatch):
    """Model araç çağırırsa ham JSON kullanıcıya gösterilmemeli."""
    (tmp_path / "veri.txt").write_text("gizli içerik", encoding="utf-8")
    sunucu.yanitlar = [
        '```tool\n{"arac": "dosya_oku", "argumanlar": {"yol": "veri.txt"}}\n```',
        "Dosyada 'gizli içerik' yazıyor.",
    ]
    monkeypatch.setenv("KASA_LLAMA_SUNUCU", sunucu.url)
    ajan = Asistan(ayarlar=_ayarlar(tmp_path), demo_izin=False)

    parcalar = list(ajan.yanit_akis("veri.txt ne diyor?"))
    birlesik = "".join(parcalar)

    assert "gizli içerik" in birlesik           # sonuç kullanıcıya döndü
    assert "dosya_oku çalıştırılıyor" in birlesik
    assert '"arac"' not in birlesik             # ham JSON gösterilmedi
    assert "```tool" not in birlesik


# --------------------------------------------------------------------------- sunucu kilidi
def test_yarida_kesilen_akis_kilidi_birakir(tmp_path, sunucu, monkeypatch):
    """Regresyon: SSE akışı yarıda kesilirse model kilidi bırakılmalı.

    Aksi halde kullanıcı sekmeyi kapatınca sunucu sonraki isteği sonsuza
    kadar bekletir (canlı testte yakalandı).
    """
    from kasa_asistan.server import Sunucu

    monkeypatch.setenv("KASA_LLAMA_SUNUCU", sunucu.url)
    ajan = Asistan(ayarlar=_ayarlar(tmp_path), demo_izin=False)
    srv = Sunucu(ajan)

    akis = srv.sohbet("Merhaba")
    next(akis)          # ilk parçayı al
    akis.close()        # istemci bağlantıyı kesti

    assert not srv.kilit.locked(), "kilit bırakılmadı — sonraki istek kilitlenir"

    # ve sonraki istek normal çalışmalı
    sunucu.yanitlar = ["İkinci yanıt."]
    assert "".join(srv.sohbet("tekrar")).strip() == "İkinci yanıt."
