"""KASA Asistan — Türkçe konuşan, cihaz içi (offline) kişisel yapay zekâ asistanı.

Seçilen model : Gemma 4 E4B (Apache 2.0)
Android motoru: Google AI Edge LiteRT-LM
Masaüstü      : llama.cpp (GGUF)

Kullanım:
    python -m kasa_asistan.cli                     # terminal sohbeti
    python -m kasa_asistan.cli --sunucu --port 8080
"""

__version__ = "0.1.0"
__secilen_model__ = "gemma4-e4b"

from .agent import Asistan, asistan_kur  # noqa: E402

__all__ = ["Asistan", "asistan_kur", "__version__", "__secilen_model__"]
