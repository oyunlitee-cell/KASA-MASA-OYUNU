#!/data/data/com.termux/files/usr/bin/bash
# KASA Asistan — çalışan süreçleri durdur
set -uo pipefail
KASA_DIZIN="$HOME/kasa"

DURDURULDU=0
for ad in "llama-server" "kasa_asistan.cli"; do
  if pgrep -f "$ad" >/dev/null 2>&1; then
    pkill -f "$ad" 2>/dev/null && echo "durduruldu: $ad" && DURDURULDU=1
  fi
done

command -v termux-wake-unlock >/dev/null 2>&1 && termux-wake-unlock 2>/dev/null || true

if [ "$DURDURULDU" = "0" ]; then
  echo "Çalışan KASA süreci yok."
else
  echo "Bitti. Tekrar başlatmak için: bash asistan/android/baslat.sh"
fi
[ -f "$KASA_DIZIN/llama.log" ] && echo "Log: $KASA_DIZIN/llama.log"
