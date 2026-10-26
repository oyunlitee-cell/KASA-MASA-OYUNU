#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
#  KASA Asistan — TELEFON SAĞLIK KONTROLÜ
#
#  "Gerçekten çalışıyor mu?" sorusunu tek tek yanıtlar. Hiçbir şeyi değiştirmez.
#  Çalıştır:  bash asistan/android/kontrol.sh
# =============================================================================
set -uo pipefail

ASISTAN_DIZIN="$(cd "$(dirname "$0")/.." && pwd)"
KASA_DIZIN="$HOME/kasa"
HATA=0

ok()    { printf '  \033[32m✓\033[0m %s\n' "$*"; }
hata()  { printf '  \033[31m✗\033[0m %s\n' "$*"; HATA=$((HATA+1)); }
uyari() { printf '  \033[33m!\033[0m %s\n' "$*"; }

echo "════════════════════════════════════════════════════════════"
echo "  KASA · telefon kontrolü"
echo "════════════════════════════════════════════════════════════"

echo
echo "1) Cihaz"
MIMAR="$(uname -m)"
[ "$MIMAR" = "aarch64" ] || [ "$MIMAR" = "arm64" ] && ok "mimari: $MIMAR" || hata "mimari desteklenmiyor: $MIMAR"
if [ -n "${TERMUX_VERSION:-}" ] || [ -d /data/data/com.termux ]; then
  ok "Termux ortamı"
else
  uyari "Termux değil (bilgisayarda çalışıyor olabilirsin)"
fi
RAM_KB="$(awk '/MemTotal/{print $2}' /proc/meminfo 2>/dev/null || echo 0)"
if [ "$RAM_KB" -gt 0 ]; then
  RAM_GB=$((RAM_KB / 1024 / 1024))
  echo "     toplam RAM: ${RAM_GB} GB"
  [ "$RAM_GB" -ge 7 ] && ok "E4B için yeterli RAM" || uyari "8 GB altı: E2B modeli daha güvenli (kur.sh e2b)"
fi
BOS_KB="$(df -Pk "$ASISTAN_DIZIN" | awk 'NR==2{print $4}')"
echo "     boş alan: $((BOS_KB / 1024 / 1024)) GB"

echo
echo "2) llama.cpp ikilisi"
LLAMA_BIN="$(find "$KASA_DIZIN/llama.cpp" -name "llama-server" -type f 2>/dev/null | head -1)"
if [ -n "$LLAMA_BIN" ]; then
  ok "llama-server: $LLAMA_BIN"
  if [ -x "$LLAMA_BIN" ]; then ok "çalıştırılabilir"; else hata "çalıştırma izni yok (chmod +x)"; fi
  echo "     sürüm: $("$LLAMA_BIN" --version 2>&1 | head -1)"
  SO_SAYISI="$(find "$KASA_DIZIN/llama.cpp" -name "*.so*" | wc -l)"
  [ "$SO_SAYISI" -gt 0 ] && ok "paylaşımlı kütüphane: $SO_SAYISI adet (.so)" || ok "statik ikili (.so yok)"
else
  hata "llama-server yok — bash asistan/android/kur.sh"
fi

echo
echo "3) Model dosyası"
MODEL_DOSYA=""
if [ -f "$KASA_DIZIN/model-bilgi.txt" ]; then
  MODEL_DOSYA="$(grep '^model=' "$KASA_DIZIN/model-bilgi.txt" | cut -d= -f2-)"
fi
[ -z "$MODEL_DOSYA" ] && MODEL_DOSYA="$(ls "$ASISTAN_DIZIN/models/"*.gguf 2>/dev/null | head -1 | xargs -r basename)"
if [ -n "$MODEL_DOSYA" ] && [ -f "$ASISTAN_DIZIN/models/$MODEL_DOSYA" ]; then
  BOYUT_MB=$(( $(stat -c%s "$ASISTAN_DIZIN/models/$MODEL_DOSYA" 2>/dev/null || echo 0) / 1024 / 1024 ))
  ok "$MODEL_DOSYA (${BOYUT_MB} MB)"
  if [ "$BOYUT_MB" -lt 1000 ]; then
    hata "dosya çok küçük — indirme yarım kalmış olabilir"
  fi
  # GGUF imzası: ilk 4 bayt "GGUF"
  IMZA="$(head -c 4 "$ASISTAN_DIZIN/models/$MODEL_DOSYA" 2>/dev/null)"
  [ "$IMZA" = "GGUF" ] && ok "GGUF dosya imzası doğru" || hata "GGUF imzası yok — dosya bozuk"
else
  hata "model dosyası yok — bash asistan/android/kur.sh"
fi

echo
echo "4) Python tarafı"
if PYTHONPATH="$ASISTAN_DIZIN/src" python3 -c "import kasa_asistan" 2>/dev/null; then
  ok "kasa_asistan paketi yükleniyor"
else
  hata "paket yüklenmiyor (PYTHONPATH / python3 kurulu mu?)"
fi
if PYTHONPATH="$ASISTAN_DIZIN/src" python3 -c "
from kasa_asistan.config import ayarlari_yukle
a = ayarlari_yukle('$ASISTAN_DIZIN/asistan.yaml'); a.model()" 2>/dev/null; then
  ok "asistan.yaml okunuyor"
else
  hata "asistan.yaml okunamıyor"
fi

echo
echo "5) Canlı çıkarım testi (llama-server açıksa)"
if curl -fsS --max-time 3 http://127.0.0.1:8081/health >/dev/null 2>&1; then
  ok "llama-server ayakta (8081)"
  BASLA=$(date +%s)
  CEVAP="$(curl -fsS --max-time 120 http://127.0.0.1:8081/v1/chat/completions \
    -H 'Content-Type: application/json' \
    -d '{"messages":[{"role":"user","content":"Sadece \"merhaba\" yaz."}],"max_tokens":12,"temperature":0.2}' \
    2>/dev/null | grep -o '"content":"[^"]*"' | head -1)"
  SURE=$(( $(date +%s) - BASLA ))
  if [ -n "$CEVAP" ]; then
    ok "model yanıt verdi (${SURE}s): $CEVAP"
  else
    hata "health OK ama yanıt yok — log: $KASA_DIZIN/llama.log"
  fi
else
  uyari "llama-server kapalı — başlatmak için: bash asistan/android/baslat.sh"
fi

echo
echo "6) Web arayüzü"
if curl -fsS --max-time 3 http://127.0.0.1:8080/api/durum >/dev/null 2>&1; then
  ok "arayüz ayakta: http://127.0.0.1:8080"
  curl -fsS http://127.0.0.1:8080/api/durum | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f\"     model: {d.get('model')} · arka uç: {d.get('arka_uc')} · mod: {d.get('mod')}\")
print('     GERÇEK model' if d.get('gercek_model') else '     DEMO (gerçek model yok)')
" 2>/dev/null || true
else
  uyari "arayüz kapalı (baslat.sh ile açılır)"
fi

echo
echo "════════════════════════════════════════════════════════════"
if [ "$HATA" -eq 0 ]; then
  printf '  \033[32mSONUÇ: Her şey yolunda.\033[0m\n'
  echo "  Çalıştır:  bash asistan/android/baslat.sh"
else
  printf '  \033[31mSONUÇ: %d sorun var (yukarıda ✗).\033[0m\n' "$HATA"
  echo "  Kurulum:   bash asistan/android/kur.sh"
fi
echo "════════════════════════════════════════════════════════════"
