#!/bin/sh
# chmod +x bot-vs-bot.sh
# Stockfish gra sam ze soba w nieskonczonej petli, przez HTTP.
#
# Zaczyna od pozycji startowej, wysyla FEN do /api/fen, z odpowiedzi bierze
# "best_fen" (pozycje po najlepszym ruchu) i wysyla go w nastepnym zadaniu.
# Gdy partia sie konczy (mat, pat, remis), zaczyna nowa od pozycji startowej.
# Gdy serwer jest nieosiagalny, ponawia to samo zadanie co RETRY_WAIT sekund.
# Zatrzymanie: Ctrl+C.
#
# Uzycie:
#   ./bot-vs-bot.sh adres:port
#   VM_HOST=192.168.88.99:8000 ./bot-vs-bot.sh
#   DELAY=1 ./bot-vs-bot.sh 192.168.88.99:8000    # 1 s przerwy miedzy ruchami
#
# Zmienne: VM_HOST (adres), DELAY (przerwa miedzy ruchami, domyslnie 0),
#          RETRY_WAIT (ponowienie po bledzie polaczenia, domyslnie 2).
# Potrzebuje tylko sh i curl.

START_FEN="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

host="${1:-${VM_HOST:-}}"
if [ -z "$host" ]; then
  echo "Uzycie: $0 adres:port   (lub ustaw VM_HOST, np. 192.168.1.50:8000)" >&2
  exit 1
fi
delay="${DELAY:-0}"
retry_wait="${RETRY_WAIT:-2}"
trap 'echo; echo "Zatrzymano. Rozegrane partie: $game, ruchy w biezacej: $moves"; exit 0' INT TERM

# Wyciaga wartosc tekstowa pola z JSON-a (FEN i SAN nie zawieraja cudzyslowow).
field() {
  printf '%s' "$2" | sed -n "s/.*\"$1\": *\"\\([^\"]*\\)\".*/\\1/p"
}

game=1
moves=0
fen="$START_FEN"
echo "Partia $game"

while true; do
  out=$(curl -sS -X POST "http://$host/api/fen" \
             -H "Content-Type: application/json" \
             -d "{\"fen\": \"$fen\"}" \
             -w '\n%{http_code}') || {
    echo "Brak polaczenia z $host, ponawiam za ${retry_wait}s..." >&2
    sleep "$retry_wait"
    continue
  }

  code=$(printf '%s\n' "$out" | tail -n 1)
  body=$(printf '%s\n' "$out" | sed '$d')

  if [ "$code" = "200" ]; then
    next=$(field best_fen "$body")
    if [ -z "$next" ]; then
      echo "Nieoczekiwana odpowiedz serwera: $body" >&2
      sleep "$retry_wait"
      continue
    fi
    moves=$((moves + 1))
    echo "$moves. $(field turn "$body") $(field san "$body") ($(field eval "$body"))"
    fen="$next"
    [ "$delay" != "0" ] && sleep "$delay"
  elif printf '%s' "$body" | grep -q "Game is already over"; then
    echo "$(field error "$body")"
    game=$((game + 1))
    moves=0
    fen="$START_FEN"
    echo
    echo "Partia $game"
  else
    echo "Blad serwera (HTTP $code): $body" >&2
    sleep "$retry_wait"
  fi
done