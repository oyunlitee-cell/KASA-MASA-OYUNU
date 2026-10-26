"""Terminal sohbeti (Termux'ta da çalışır)."""

from __future__ import annotations

import argparse
import sys


def ana() -> int:
    p = argparse.ArgumentParser(
        prog="kasa-asistan",
        description="KASA — Türkçe konuşan, cihaz içi kişisel asistan",
    )
    p.add_argument("--model", default=None, help="asistan.yaml model anahtarı (gemma4-e4b vb.)")
    p.add_argument("--yapilandirma", default=None, help="asistan.yaml yolu")
    p.add_argument("--arac-kapali", action="store_true", help="araçları kapat")
    p.add_argument("--demo-yok", action="store_true",
                   help="gerçek model yoksa çalışmayı reddet (demo kapalı)")
    p.add_argument("--sunucu", action="store_true", help="HTTP sunucusunu başlat")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--host", default=None, help="arayüz adresi (telefonda 127.0.0.1 önerilir)")
    p.add_argument("--mesaj", default=None, help="tek seferlik soru")
    a = p.parse_args()

    import os
    a.model = a.model or os.environ.get("KASA_MODEL") or None

    if a.sunucu:
        from .server import calistir
        calistir(host=a.host or "0.0.0.0", port=a.port, model=a.model,
                 araclar=not a.arac_kapali, yapilandirma=a.yapilandirma,
                 demo_izin=not a.demo_yok)
        return 0

    from .agent import asistan_kur
    try:
        asistan = asistan_kur(a.yapilandirma, a.model, araclar=not a.arac_kapali,
                              demo_izin=not a.demo_yok)
    except Exception as e:  # noqa: BLE001
        from kasa_asistan.backends import ArkaUcHatasi
        if isinstance(e, ArkaUcHatasi):
            print("\n" + str(e) + "\n", file=sys.stderr)
            return 2
        raise
    d = asistan.durum()

    print("─" * 62)
    print(f"  KASA · {d['etiket']} · {d['lisans']}")
    if not d["gercek_model"]:
        print("  ⚠  DEMO modu: models/ klasöründe model yok, hazır yanıtlar dönüyor.")
        print("     Gerçek model için: bash asistan/modeller/indir.sh")
    if d.get("uyari"):
        print(f"  ⚠  {d['uyari']}")
    print("  Çıkış: /q   ·   Kaydet: /kaydet   ·   Hatırla: /hatırla <bilgi>")
    print("─" * 62)

    if a.mesaj:
        print(asistan.yanit(a.mesaj))
        return 0

    while True:
        try:
            giris = input("\nsen › ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGörüşürüz!")
            break
        if not giris:
            continue
        if giris in ("/q", "/quit", "/exit", "çıkış"):
            print("Görüşürüz!")
            break
        if giris == "/durum":
            for k, v in asistan.durum().items():
                print(f"  {k:16s}: {v}")
            continue
        if giris == "/kaydet":
            print(f"Kaydedildi: {asistan.kaydet()}")
            continue
        if giris.startswith("/hatırla "):
            print(asistan.hatirla(giris[len("/hatırla "):]))
            continue
        if giris == "/hafiza":
            print(asistan.hafiza_oku() or "(hafıza boş)")
            continue

        print(f"\n{d['model']} › ", end="", flush=True)
        for parca in asistan.yanit_akis(giris):
            print(parca, end="", flush=True)
        print()
        hiz = asistan.istatistik.get("son_hiz", 0)
        if hiz:
            print(f"          [{hiz} token/s]")

    return 0


if __name__ == "__main__":
    sys.exit(ana())
