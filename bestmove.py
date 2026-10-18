"""Command-line helper: paste a FEN, get the best move back as a FEN.

Usage:
    python bestmove.py                 # interactive: paste FENs one per line
    python bestmove.py "<FEN>"         # one-shot
Options:
    --depth N     search depth (default 20)
    --time S      search time in seconds (overrides depth)
    --threads N   engine threads (default 2)

For each FEN it prints:
    - the best move (SAN and UCI)
    - the evaluation (White's view)
    - the FEN of the position AFTER the best move is played
Type 'quit' or press Ctrl+C / Ctrl+D to exit.
"""

import argparse

from engine import analyse_fen, format_eval, make_limit, open_engine


def best_move_text(engine, fen, limit) -> str:
    try:
        result = analyse_fen(engine, fen, limit)
    except ValueError as exc:
        return str(exc)

    return (
        f"Best move : {result.san} ({result.move.uci()})\n"
        f"Eval (W)  : {format_eval(result.score)}\n"
        f"FEN after : {result.after.fen()}"
    )


def main():
    parser = argparse.ArgumentParser(description="Best move from a FEN, returned as a FEN")
    parser.add_argument("fen", nargs="?", help="FEN to analyze (omit for interactive mode)")
    parser.add_argument("--depth", type=int, default=20)
    parser.add_argument("--time", type=float, default=None)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()

    limit = make_limit(depth=args.depth, time=args.time)

    with open_engine(threads=args.threads) as engine:
        if args.fen:
            print(best_move_text(engine, args.fen, limit))
            return

        print("Paste a FEN and press Enter ('quit' to exit).")
        while True:
            try:
                line = input("\nFEN> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            if line.lower() in {"quit", "exit", "q"}:
                break
            print(best_move_text(engine, line, limit))


if __name__ == "__main__":
    main()
