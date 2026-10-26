#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
#  KASA Asistan — ANDROID TELEFON KURULUMU (bilgisayar GEREKMEZ)
#
#  Bu betik Termux içinde çalışır ve şunları yapar:
#    1. Ortamı denetler (Termux + arm64)
#    2. llama.cpp'nin RESMÎ Android arm64 ikilisini indirir  (~77 MB, derleme YOK)
#    3. Gemma 4 E4B modelini indirir                          (~5.2 GB, GGUF QAT)
#    4. llama-server'ı bir kez açıp modelin gerçekten yüklendiğini DOĞRULAR
#    5. baslat.sh / durdur.sh / kontrol.sh betiklerini kurar
#
#  Kullanım (Termux içinde):
#      bash asistan/android/kur.sh              # E4B (8 GB+ RAM önerilir)
#      bash asistan/android/kur.sh e2b          # E2B (4-6 GB RAM, 3.4 GB dosya)
# =============================================================================
set -euo pipefail

BOYUT="${1:-e4b}"

# ------------------------------------------------------------------ yardımcılar
kirmizi() { printf '\033[31m%s\033[0m\n' "$*"; }
yesil()   { printf '\033[32m%s\033[0m\n' "$*"; }
sari()    { printf '\033[33m%s\033[0m\n' "$*"; }
baslik()  { printf '\n\033[1m── %s ──\033[0m\n' "$*"; }

# ------------------------------------------------------------------ 1. ortam
baslik "1/5 Ortam denetimi"

if [ ! -d "/data/data/com.termux" ] && [ -z "${TERMUX_VERSION:-}" ]; then
  sari "UYARI: Termux ortamı gibi görünmüyor."
  sari "Bu betik Android telefon için yazıldı. Masaüstünde: bash asistan/modeller/indir.sh"
  printf "Devam edilsin mi? [e/H] "; read -r c
  case "$c" in e|E|y|Y) ;; *) exit 1 ;; esac
fi

MIMAR="$(uname -m)"
if [ "$MIMAR" != "aarch64" ] && [ "$MIMAR" != "arm64" ]; then
  kirmizi "HATA: Bu ikili arm64 içindir, cihazın: $MIMAR"
  exit 1
fi
yesil "✓ arm64 cihaz"

for arac in curl tar; do
  if ! command -v "$arac" >/dev/null 2>&1; then
    sari "Eksik araç: $arac — kuruluyor..."
    pkg install -y "$arac"
  fi
done
yesil "✓ curl, tar hazır"

ASISTAN_DIZIN="$(cd "$(dirname "$0")/.." && pwd)"     # .../asistan
KASA_DIZIN="$HOME/kasa"                               # model + ikili burada
mkdir -p "$KASA_DIZIN/llama.cpp" "$ASISTAN_DIZIN/models"

# ------------------------------------------------------------------ 2. llama.cpp
baslik "2/5 llama.cpp Android ikilisi"

if [ -x "$KASA_DIZIN/llama.cpp/llama-server" ] || find "$KASA_DIZIN/llama.cpp" -name "llama-server" -type f 2>/dev/null | grep -q .; then
  yesil "✓ llama-server zaten kurulu — atlanıyor"
else
  SABIT_SURUM="b11889"
  SARI_URL="https://api.github.com/repos/ggml-org/llama.cpp/releases"
  echo "En güncel sürüm sorgulanıyor..."
  ETIKET="$(curl -fsSL "$SARI_URL?per_page=1" 2>/dev/null \
            | grep -o '"tag_name": *"[^"]*"' | head -1 \
            | sed 's/.*"tag_name": *"//; s/"$//')" || true
  [ -n "${ETIKET:-}" ] || ETIKET="$SABIT_SURUM"
  echo "Sürüm: $ETIKET"

  # Snapdragon varyantı CPU+Adreno+Hexagon içerir; diğer cihazlar için genel ikili
  INDIRILDI=0
  for VARYANT in snapdragon ""; do
    if [ -n "$VARYANT" ]; then
      AD="llama-${ETIKET}-bin-android-arm64-${VARYANT}.tar.gz"
    else
      AD="llama-${ETIKET}-bin-android-arm64.tar.gz"
    fi
    URL="https://github.com/ggml-org/llama.cpp/releases/download/${ETIKET}/${AD}"
    echo "  deneniyor: $AD"
    if curl -fL --retry 2 --connect-timeout 25 -o "$KASA_DIZIN/llama.tar.gz" "$URL" 2>/dev/null; then
      INDIRILDI=1; break
    fi
  done

  if [ "$INDIRILDI" != "1" ]; then
    kirmizi "HATA: llama.cpp ikilisi indirilemedi (ağ/duvar olabilir)."
    echo "Elle indirme: https://github.com/ggml-org/llama.cpp/releases"
    echo "Dosyayı şuraya koy: $KASA_DIZIN/llama.tar.gz  ve betiği tekrar çalıştır."
    exit 1
  fi

  tar xzf "$KASA_DIZIN/llama.tar.gz" -C "$KASA_DIZIN/llama.cpp"
  rm -f "$KASA_DIZIN/llama.tar.gz"

  SUNUCU_BIN="$(find "$KASA_DIZIN/llama.cpp" -name "llama-server" -type f | head -1)"
  if [ -z "$SUNUCU_BIN" ]; then
    kirmizi "HATA: arşivde llama-server yok. İçerik:"
    find "$KASA_DIZIN/llama.cpp" -maxdepth 2 | head -20
    exit 1
  fi
  chmod +x "$SUNUCU_BIN"
  # Resmî Android derlemeleri paylaşımlı kütüphane kullanır
  chmod -R u+x "$KASA_DIZIN/llama.cpp" 2>/dev/null || true
  yesil "✓ llama-server: $SUNUCU_BIN"
fi

# ------------------------------------------------------------------ 3. model
baslik "3/5 Model indirme (Gemma 4, Apache-2.0)"

HF="https://huggingface.co"
if [ "$BOYUT" = "e2b" ]; then
  MODEL_URL="$HF/google/gemma-4-E2B-it-qat-q4_0-gguf/resolve/main/gemma-4-E2B-it-qat-q4_0.gguf"
  MODEL_DOSYA="gemma-4-E2B-qat-q4_0.gguf"
  TAHMIN_GB=3.4
else
  MODEL_URL="$HF/google/gemma-4-E4B-it-qat-q4_0-gguf/resolve/main/gemma-4-E4B-it-qat-q4_0.gguf"
  MODEL_DOSYA="gemma-4-E4B-qat-q4_0.gguf"
  TAHMIN_GB=5.2
fi
MODEL_YOL="$ASISTAN_DIZIN/models/$MODEL_DOSYA"

if [ -f "$MODEL_YOL" ]; then
  yesil "✓ Model zaten var: $MODEL_DOSYA ($(du -h "$MODEL_YOL" | cut -f1))"
else
  BOS_KB="$(df -Pk "$ASISTAN_DIZIN/models" | awk 'NR==2{print $4}')"
  BOS_GB=$((BOS_KB / 1024 / 1024))
  echo "Boş alan: ${BOS_GB} GB · gereken: ~${TAHMIN_GB} GB"
  if [ "$BOS_GB" -lt "$(( ${TAHMIN_GB%.*} + 1 ))" ]; then
    kirmizi "HATA: yeterli boş alan yok."
    echo "  Küçük model dene: bash asistan/android/kur.sh e2b"
    exit 1
  fi
  sari "İndirme başlıyor (~${TAHMIN_GB} GB). Wi-Fi'de yap. Duraklatıp devam ettirebilirsin."
  curl -fL -C - --retry 3 --connect-timeout 30 -o "$MODEL_YOL" "$MODEL_URL"
  yesil "✓ İndirildi: $MODEL_DOSYA ($(du -h "$MODEL_YOL" | cut -f1))"
fi

# asistan.yaml'a modeli tanıt (mevcut dosya korunur, sadece gerekli satır eklenir)
CFG="$ASISTAN_DIZIN/asistan.yaml"
if ! grep -q "telefon_model:" "$CFG" 2>/dev/null; then
  printf '\n# Android kurulumunun seçtiği model dosyası (kur.sh yazdı)\ntelefon_model: "%s"\n' "$MODEL_DOSYA" >> "$CFG"
fi

# ------------------------------------------------------------------ 4. doğrulama
baslik "4/5 Gerçek model yükleniyor mu? (canlı test)"

SUNUCU_BIN="$(find "$KASA_DIZIN/llama.cpp" -name "llama-server" -type f | head -1)"
LIB_DIZINLER="$(find "$KASA_DIZIN/llama.cpp" -name "*.so*" -exec dirname {} \; | sort -u | tr '\n' ':')"

echo "llama-server başlatılıyor (ilk yükleme 20-60 sn sürebilir)..."
( export LD_LIBRARY_PATH="${LIB_DIZINLER}${LD_LIBRARY_PATH:-}"
  exec "$SUNUCU_BIN" \
    --model "$MODEL_YOL" \
    --host 127.0.0.1 --port 8081 \
    --ctx-size 4096 --threads 4 --jinja ) > "$KASA_DIZIN/llama-test.log" 2>&1 &
TEST_PID=$!

BASARILI=0
for i in $(seq 1 90); do
  if ! kill -0 "$TEST_PID" 2>/dev/null; then
    kirmizi "llama-server beklenmedik şekilde durdu. Son log:"
    tail -25 "$KASA_DIZIN/llama-test.log"
    break
  fi
  if curl -fsS --max-time 2 http://127.0.0.1:8081/health >/dev/null 2>&1; then
    CEVAP="$(curl -fsS --max-time 120 http://127.0.0.1:8081/v1/chat/completions \
      -H 'Content-Type: application/json' \
      -d '{"messages":[{"role":"user","content":"Tek kelimeyle yanıtla: Türkiye'"'"'nin başkenti neresi?"}],"max_tokens":16,"temperature":0.2}' \
      2>/dev/null | grep -o '"content":"[^"]*"' | head -1)"
    if [ -n "$CEVAP" ]; then
      yesil "✓ MODEL GERÇEKTEN ÇALIŞIYOR"
      echo "   Yanıt: $CEVAP"
      BASARILI=1
    else
      sari "Sunucu ayakta ama yanıt alınamadı."
    fi
    break
  fi
  sleep 1
done

kill "$TEST_PID" 2>/dev/null || true
wait "$TEST_PID" 2>/dev/null || true

if [ "$BASARILI" != "1" ]; then
  kirmizi "Doğrulama başarısız. Log: $KASA_DIZIN/llama-test.log"
  echo "Olası sebepler: RAM yetersiz (E2B dene), eksik .so (log'a bak), bozuk indirme."
  exit 1
fi

# ------------------------------------------------------------------ 5. betikler
baslik "5/5 Başlatıcılar kuruluyor"

cat > "$ASISTAN_DIZIN/android/calistir-llama.sh" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
# kur.sh tarafından üretildi — llama-server'ı başlatır
export LD_LIBRARY_PATH="${LIB_DIZINLER}\${LD_LIBRARY_PATH:-}"
exec "$SUNUCU_BIN" \\
  --model "$MODEL_YOL" \\
  --host 127.0.0.1 --port 8081 \\
  --ctx-size 4096 --threads 4 --jinja \\
  --mlock || exec "$SUNUCU_BIN" --model "$MODEL_YOL" --host 127.0.0.1 --port 8081 --ctx-size 4096 --threads 4 --jinja
EOF
chmod +x "$ASISTAN_DIZIN/android/calistir-llama.sh"

cat > "$KASA_DIZIN/model-bilgi.txt" <<EOF
model=$MODEL_DOSYA
boyut=$BOYUT
llama_server=$SUNUCU_BIN
kutuphaneler=$LIB_DIZINLER
kurulum=$(date '+%Y-%m-%d %H:%M')
EOF

yesil "✓ Kurulum tamam"
echo
echo "════════════════════════════════════════════════════════"
echo "  SIRADAKİ ADIM — şunu çalıştır:"
echo
echo "      bash $ASISTAN_DIZIN/android/baslat.sh"
echo
echo "  Tarayıcı otomatik açılır: http://127.0.0.1:8080"
echo "════════════════════════════════════════════════════════"
