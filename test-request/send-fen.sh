#!/bin/sh
# chmod +x send-fen.sh
# Wysyla FEN do aplikacji i wypisuje odpowiedz (najlepszy ruch jako JSON).
#
# Uzycie:
#   ./send-fen.sh "<FEN>" [adres:port]
#   ./send-fen.sh start 192.168.88.99:8000 
#   VM_HOST=192.168.88.99:8000 ./send-fen.sh "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
#
# Adres maszyny z aplikacja podajesz jako drugi argument albo zmienna VM_HOST.
# Potrzebuje tylko sh i curl.
# chmod +x send-fen.sh
# ./send-fen.sh "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1" 192.168.88.99:8000
#
# export VM_HOST=192.168.88.99:8000
# ./send-fen.sh start
# ./send-fen.sh "<FEN>"
# ./send-fen.sh "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"

if [ $# -lt 1 ] || [ -z "$1" ]; then
  echo "Uzycie: $0 \"<FEN>\" [adres:port]" >&2
  exit 1
fi

host="${2:-${VM_HOST:-}}"
if [ -z "$host" ]; then
  echo "Podaj adres maszyny jako drugi argument lub zmienna VM_HOST (np. 192.168.88.99:8000)." >&2
  exit 1
fi

# Zabezpiecza cudzyslowy i backslashe, zeby FEN nie zepsul JSON-a.
fen=$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')

curl -sS -X POST "http://$host/api/fen" \
     -H "Content-Type: application/json" \
     -d "{\"fen\": \"$fen\"}"
status=$?
echo
exit $status