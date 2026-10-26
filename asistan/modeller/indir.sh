#!/usr/bin/env bash
# =============================================================================
#  KASA Asistan — model indirici
#
#  Kullanım:
#    bash asistan/modeller/indir.sh                 # varsayılan: Gemma 4 E4B
#    bash asistan/modeller/indir.sh gemma4-e2b      # hafif telefon modeli
#    bash asistan/modeller/indir.sh qwen35-4b       # deneysel (daha güçlü kod)
#    bash asistan/modeller/indir.sh --litertlm      # Android için .litertlm
#
#  Gerekenler: curl veya wget, ~4-6 GB boş alan.
#  Hugging Face'ten indirir (huggingface.co). Duvar varsa ModelScope deneyin.
# =============================================================================
set -euo pipefail

MODEL="${1:-gemma4-e4b}"
BIÇIM="${2:-gguf}"          # gguf | litertlm
HEDEF="$(cd "$(dirname "$0")" && pwd)"
cd "$HEDEF"

# --- model tanımları ---------------------------------------------------------
# gguf:     masaüstü / Termux (llama.cpp)
# litertlm: Android / iOS (LiteRT-LM)
declare -A URL_GGUF URL_LITERTLM

URL_GGUF[gemma4-e4b]="https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-gguf/resolve/main/gemma-4-E4B-it-qat-q4_0.gguf"
URL_GGUF[gemma4-e2b]="https://huggingface.co/google/gemma-4-E2B-it-qat-q4_0-gguf/resolve/main/gemma-4-E2B-it-qat-q4_0.gguf"
URL_GGUF[qwen35-4b]="https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/main/Qwen3.5-4B-Q4_K_M.gguf"
URL_GGUF[qwen3-4b]="https://huggingface.co/bartowski/Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"

URL_LITERTLM[gemma4-e4b]="https://huggingface.co/litert-community/gemma-4-E4B-it-litert-lm/resolve/main/gemma-4-E4B-it.litertlm"
URL_LITERTLM[gemma4-e2b]="https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm/resolve/main/gemma-4-E2B-it.litertlm"

case "$MODEL" in
  --litertlm) BIÇIM=litertlm; MODEL=gemma4-e4b ;;
esac

if [ "$BIÇIM" = "litertlm" ]; then
  URL="${URL_LITERTLM[$MODEL]:-}"
  UZANTI=".litertlm"
else
  URL="${URL_GGUF[$MODEL]:-}"
  UZANTI=".gguf"
fi

if [ -z "${URL:-}" ]; then
  echo "HATA: '$MODEL' için $BIÇIM bağlantısı tanımlı değil."
  echo "GGUF olanlar : ${!URL_GGUF[*]}"
  echo "LiteRT olanlar: ${!URL_LITERTLM[*]}"
  exit 1
fi

DOSYA="$(basename "$URL")"
echo "────────────────────────────────────────────────────────────"
echo "  Model : $MODEL"
echo "  Biçim : $BIÇIM  ($UZANTI)"
echo "  Hedef : $HEDEF/$DOSYA"
echo "  Lisans: Apache-2.0"
echo "────────────────────────────────────────────────────────────"

if [ -f "$DOSYA" ]; then
  echo "Zaten var: $DOSYA ($(du -h "$DOSYA" | cut -f1)) — atlanıyor."
  exit 0
fi

if command -v curl >/dev/null 2>&1; then
  curl -L --fail --retry 3 -o "$DOSYA.partial" "$URL" && mv "$DOSYA.partial" "$DOSYA"
elif command -v wget >/dev/null 2>&1; then
  wget -O "$DOSYA.partial" "$URL" && mv "$DOSYA.partial" "$DOSYA"
else
  echo "HATA: curl veya wget gerekli. Termux'ta: pkg install curl"
  exit 1
fi

echo ""
echo "İndirildi: $DOSYA ($(du -h "$DOSYA" | cut -f1))"
echo ""
echo "Sıradaki adım:"
if [ "$BIÇIM" = "litertlm" ]; then
  echo "  Bu dosyayı telefona atıp destekleyen bir uygulamada aç"
  echo "  (Google AI Edge Gallery / Pocket LLM → 'Model içe aktar')."
  echo "  Ayrıntılar: asistan/docs/ANDROID-KURULUM.md"
else
  echo "  python3 -m kasa_asistan.cli --model $MODEL"
  echo "  veya:    python3 -m kasa_asistan.cli --sunucu --port 8080"
fi
