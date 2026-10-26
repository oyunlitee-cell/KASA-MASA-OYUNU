#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
#  KASA Asistan — telefonda tek komutla başlat
#
#  Sırayla:
#    1. llama-server  (modeli yükler, 127.0.0.1:8081)
#    2. KASA arayüzü  (http://127.0.0.1:8080)
#    3. tarayıcıyı açar
#
#  Durdurmak için: Ctrl+C  (ya da bash asistan/android/durdur.sh)
# =============================================================================
set -uo pipefail

ASISTAN_DIZIN="$(cd "$(dirname "$0")/.." && pwd)"
KASA_DIZIN="$HOME/kasa"
PORT_WEB="${KASA_PORT:-8080}"
PORT_LLM="${KASA_LLM_PORT:-8081}"

kirmizi() { printf '\033[31m%s\033[0m\n' "$*"; }
yesil()   { printf '\033[32m%s\033[0m\n' "$*"; }
sari()    { printf '\033[33m%s\033[0m\n' "$*"; }

# --- ön koşul ---------------------------------------------------------------
if [ ! -f "$KASA_DIZIN/model-bilgi.txt" ]; then
  kirmizi "Kurulum bulunamadı. Önce şunu çalıştır:"
  echo "    bash $ASISTAN_DIZIN/android/kur.sh"
  exit 1
fi

LLAMA_BIN="$(find "$KASA_DIZIN/llama.cpp" -name "llama-server" -type f | head -1)"
MODEL="$(grep '^model=' "$KASA_DIZIN/model-bilgi.txt" | cut -d= -f2-)"
LIB_DIZINLER="$(find "$KASA_DIZIN/llama.cpp" -name "*.so*" -exec dirname {} \; | sort -u | tr '\n' ':')"

if [ ! -x "$LLAMA_BIN" ]; then
  kirmizi "llama-server bulunamadı: $LLAMA_BIN"
  exit 1
fi

# --- ekran/batarya ---------------------------------------------------------
if command -v termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock 2>/dev/null || true
  sari "Ekran kilidi devre dışı (termux-wake-lock)."
fi

TEMIZLIK_YAPILDI=0
temizle() {
  [ "$TEMIZLIK_YAPILDI" = "1" ] && return
  TEMIZLIK_YAPILDI=1
  echo
  sari "Kapatılıyor..."
  [ -n "${WEB_PID:-}" ] && kill "$WEB_PID" 2>/dev/null || true
  [ -n "${LLM_PID:-}" ] && kill "$LLM_PID" 2>/dev/null || true
  command -v termux-wake-unlock >/dev/null 2>&1 && termux-wake-unlock 2>/dev/null || true
  exit 0
}
trap temizle INT TERM

# --- 1. llama-server -------------------------------------------------------
echo "Model yükleniyor: $MODEL"
echo "(ilk yükleme 20-60 saniye sürebilir, sonrası hızlı)"
(
  export LD_LIBRARY_PATH="${LIB_DIZINLER}${LD_LIBRARY_PATH:-}"
  exec "$LLAMA_BIN" \
    --model "$ASISTAN_DIZIN/models/$MODEL" \
    --host 127.0.0.1 --port "$PORT_LLM" \
    --ctx-size "${KASA_CTX:-4096}" --threads "${KASA_THREADS:-4}" --jinja
) > "$KASA_DIZIN/llama.log" 2>&1 &
LLM_PID=$!

HAZIR=0
for i in $(seq 1 120); do
  if ! kill -0 "$LLM_PID" 2>/dev/null; then
    kirmizi "llama-server durdu. Log'un son satırları:"
    tail -20 "$KASA_DIZIN/llama.log"
    echo
    echo "RAM yetersizse: bash asistan/android/kur.sh e2b"
    exit 1
  fi
  if curl -fsS --max-time 2 "http://127.0.0.1:${PORT_LLM}/health" >/dev/null 2>&1; then
    HAZIR=1; break
  fi
  sleep 1
done

if [ "$HAZIR" != "1" ]; then
  kirmizi "llama-server 120 saniyede hazır olmadı. Log: $KASA_DIZIN/llama.log"
  kill "$LLM_PID" 2>/dev/null || true
  exit 1
fi
yesil "✓ Model hazır (gerçek çıkarım, tamamen cihaz içi)"

# --- 2. KASA web arayüzü ---------------------------------------------------
cd "$ASISTAN_DIZIN"
KASA_LLAMA_SUNUCU="http://127.0.0.1:${PORT_LLM}" \
KASA_MODEL="${KASA_MODEL:-gemma4-e4b}" \
PYTHONPATH=src \
  python3 -m kasa_asistan.cli --sunucu --host 127.0.0.1 --port "$PORT_WEB" --demo-yok \
  > "$KASA_DIZIN/asistan.log" 2>&1 &
WEB_PID=$!

for i in $(seq 1 30); do
  if ! kill -0 "$WEB_PID" 2>/dev/null; then
    kirmizi "Asistan sunucusu başlamadı. Log:"
    tail -20 "$KASA_DIZIN/asistan.log"
    kill "$LLM_PID" 2>/dev/null || true
    exit 1
  fi
  if curl -fsS --max-time 2 "http://127.0.0.1:${PORT_WEB}/api/durum" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
yesil "✓ Arayüz hazır: http://127.0.0.1:${PORT_WEB}"

# --- 3. tarayıcı -----------------------------------------------------------
if command -v termux-open-url >/dev/null 2>&1; then
  termux-open-url "http://127.0.0.1:${PORT_WEB}" 2>/dev/null || true
else
  echo "Tarayıcıda aç: http://127.0.0.1:${PORT_WEB}"
fi

echo
echo "════════════════════════════════════════════════════════"
echo "  KASA hazır. Bu pencereyi KAPATMA."
echo "  Durdurmak için Ctrl+C."
echo "════════════════════════════════════════════════════════"

wait "$WEB_PID"
