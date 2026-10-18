"""Flask server: send a FEN over HTTP, see Stockfish's best move as an arrow.

Start the server:
    python web.py
Open http://127.0.0.1:8000 in your browser, then send a FEN from any terminal:

    # JSON body
    curl -X POST http://127.0.0.1:8000/api/fen \
         -H "Content-Type: application/json" \
         -d '{"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}'

    # form field
    curl -X POST http://127.0.0.1:8000/api/fen \
         --data-urlencode "fen=rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    # query string (also works pasted into a browser's address bar)
    curl -G http://127.0.0.1:8000/api/fen \
         --data-urlencode "fen=rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

The JSON reply contains the best move and the FEN after it. The open browser
page (static/index.html) updates by itself and shows the position you sent with
an arrow from the square the suggested piece stands on to the square it should
move to. Use fen=start for the initial position.

Options:
    --depth N          search depth (default 18)
    --time S           search time in seconds (overrides depth)
    --threads N        engine threads (default 2)
    --host H           bind address (default 127.0.0.1)
    --port P           port (default 8000; macOS uses 5000 for AirPlay)
    --orientation O    white | black | turn  (default white)
"""

import argparse
import threading

import chess
import chess.engine
import chess.svg
from flask import Flask, jsonify, request

from engine import Analysis, analyse_fen, format_eval, make_limit, open_engine

app = Flask(__name__)  # serves ./static/index.html at "/"

_lock = threading.Lock()          # guards _state (shared with the page's polling)
_engine_lock = threading.Lock()   # one analysis at a time on the single engine
_state = {"ready": False, "version": 0}

# Fields returned to API callers (the SVG is only for the page).
PUBLIC_KEYS = ("fen", "best_fen", "san", "uci", "eval", "depth", "turn")


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/state")
def api_state():
    """Latest result, polled by the page."""
    with _lock:
        return jsonify(dict(_state))


def extract_fen() -> str:
    """Pull the FEN from a JSON body, a form field, or a ?fen= query parameter."""
    data = request.get_json(silent=True)
    if isinstance(data, dict) and isinstance(data.get("fen"), str):
        return data["fen"].strip()
    return (request.values.get("fen") or "").strip()


@app.route("/api/fen", methods=["GET", "POST"])
def api_fen():
    """Analyze a FEN. Updates the page and returns the best move as JSON."""
    fen = extract_fen()
    if not fen:
        return (
            jsonify(error="Missing 'fen' (send a JSON body, a form field or a ?fen= parameter)."),
            400,
        )
    if fen.lower() == "start":
        fen = chess.STARTING_FEN

    try:
        with _engine_lock:
            result = analyze(
                app.config["ENGINE"], fen, app.config["LIMIT"], app.config["ORIENTATION"]
            )
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except chess.engine.EngineError as exc:
        return jsonify(error=f"Engine error: {exc}"), 500

    publish(result)
    return jsonify({key: result[key] for key in PUBLIC_KEYS})


def render_board(result: Analysis, orientation: str) -> str:
    """SVG of the analysed position with an arrow for the suggested move."""
    board = result.board
    if orientation == "turn":
        side = board.turn
    else:
        side = chess.WHITE if orientation == "white" else chess.BLACK

    return chess.svg.board(
        board,
        orientation=side,
        check=board.king(board.turn) if board.is_check() else None,
        arrows=[chess.svg.Arrow(result.move.from_square, result.move.to_square)],
    )


def analyze(engine, fen: str, limit: chess.engine.Limit, orientation: str) -> dict:
    """Return everything the page and API need. Raises ValueError for unusable input."""
    result = analyse_fen(engine, fen, limit)
    return {
        "fen": result.board.fen(),
        "best_fen": result.after.fen(),
        "board_svg": render_board(result, orientation),
        "san": result.san,
        "uci": result.move.uci(),
        "eval": format_eval(result.score),
        "depth": result.depth,
        "turn": "White" if result.board.turn == chess.WHITE else "Black",
    }


def publish(result: dict) -> None:
    with _lock:
        _state.update(result)
        _state["ready"] = True
        _state["version"] += 1


def main():
    parser = argparse.ArgumentParser(description="Send a FEN over HTTP, see the best move as an arrow")
    parser.add_argument("--depth", type=int, default=18)
    parser.add_argument("--time", type=float, default=None)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--orientation", choices=["white", "black", "turn"], default="white")
    args = parser.parse_args()

    app.config["LIMIT"] = make_limit(depth=args.depth, time=args.time)
    app.config["ORIENTATION"] = args.orientation

    base = f"http://{args.host}:{args.port}"
    with open_engine(threads=args.threads) as engine:
        app.config["ENGINE"] = engine
        print(f"Viewer  : {base}")
        print(f'Send FEN: curl -G {base}/api/fen --data-urlencode "fen=<FEN>"')
        app.run(host=args.host, port=args.port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
