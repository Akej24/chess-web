# Stockfish FEN viewer

Send a FEN over HTTP and get Stockfish's best move back as JSON. A small web page
shows the position with an arrow from the piece's square to the square it should
move to. Built on [python-chess](https://python-chess.readthedocs.io/) and Flask.

## Files

| File | Purpose |
|------|---------|
| `web.py` | Flask server: `/api/fen` takes a FEN, `/` shows the board with the arrow |
| `static/index.html` | The page served at `/` (polls `/api/state` and redraws) |
| `bestmove.py` | Command-line version: paste a FEN, get the best move and the resulting FEN |
| `engine.py` | Finds and starts Stockfish; `analyse_fen()` validates a FEN and returns the best move |
| `install.sh` | One-time setup of the app and its services on a fresh Ubuntu/Debian VM |
| `deploy/` | Proxmox VM script, systemd units, auto-update from GitHub (see `deploy/README.md`) |
| `requirements.txt` | Python dependencies (`chess`, `flask`) |

## 1. Python environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Install Stockfish

- **macOS (Homebrew):** `brew install stockfish`
- **Debian/Ubuntu:** `sudo apt install stockfish`
- **Windows (winget/choco):** `choco install stockfish`
- **Manual:** download a build from https://stockfishchess.org/download/ and either put
  the binary in a `stockfish/` folder next to these scripts or set `STOCKFISH_PATH` to
  its full path. On Linux/macOS run `chmod +x stockfish/stockfish*`.

The scripts look for the engine in this order: `STOCKFISH_PATH`, your `PATH`, then
the local `stockfish/` folder.

## 3. Run

```bash
python web.py                    # then open http://127.0.0.1:8000
```

Send a FEN from any terminal (JSON body, form field or query string all work):

```bash
curl -G http://127.0.0.1:8000/api/fen \
     --data-urlencode "fen=rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
```

The reply has `fen`, `best_fen` (the position after Stockfish's move), `san`, `uci`,
`eval` (White's view), `depth` and `turn`. Bad input returns HTTP 400 with
`{"error": ...}`. `fen=start` loads the initial position.

Options: `--port 8080`, `--host 0.0.0.0` (reachable from other devices), `--depth 22`,
`--time 2`, `--threads 4` and `--orientation white|black|turn`. Port 8000 is the
default because macOS uses port 5000 for AirPlay Receiver.

Command-line only, without the web page:

```bash
python bestmove.py "<FEN>"       # one-shot
python bestmove.py               # interactive: paste FENs at the prompt
```

## Using it in your own code

```python
from engine import analyse_fen, format_eval, make_limit, open_engine

with open_engine(threads=4, hash_mb=512) as engine:
    result = analyse_fen(engine, "<FEN>", make_limit(depth=20))
    print(result.san, format_eval(result.score), result.after.fen())
```

`analyse_fen` raises `ValueError` with a readable message for a malformed FEN, an
illegal position or a finished game.

## Tuning

- `Threads`: roughly your physical core count.
- `Hash`: transposition table in MB; 256-2048 is typical.
- Search effort: `--depth` or `--time` (time wins if both are given).

## Hosting on Proxmox

See `deploy/README.md`: one script builds an Ubuntu VM on your Proxmox host and the VM
then pulls updates from GitHub by itself.
