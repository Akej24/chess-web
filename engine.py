"""Stockfish helpers shared by web.py and bestmove.py (python-chess, UCI protocol)."""

import os
import shutil
from contextlib import contextmanager
from dataclasses import dataclass

import chess
import chess.engine


def find_stockfish() -> str:
    """Locate the Stockfish binary.

    Order: STOCKFISH_PATH env var, then PATH, then ./stockfish/ folder.
    """
    env_path = os.environ.get("STOCKFISH_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    on_path = shutil.which("stockfish")
    if on_path:
        return on_path

    local_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stockfish")
    if os.path.isdir(local_dir):
        for name in sorted(os.listdir(local_dir)):
            full = os.path.join(local_dir, name)
            if name.lower().startswith("stockfish") and os.path.isfile(full):
                if os.access(full, os.X_OK) or name.lower().endswith(".exe"):
                    return full

    raise FileNotFoundError(
        "Stockfish not found. Install it (see README.md), then either put it on "
        "your PATH, drop the binary in ./stockfish/, or set STOCKFISH_PATH."
    )


@contextmanager
def open_engine(threads: int = 2, hash_mb: int = 256):
    """Start Stockfish and always shut it down when the block ends."""
    engine = chess.engine.SimpleEngine.popen_uci(find_stockfish())
    try:
        engine.configure({"Threads": threads, "Hash": hash_mb})
        yield engine
    finally:
        engine.quit()


def make_limit(depth: int = 18, time: float | None = None) -> chess.engine.Limit:
    """Search limit from command-line options: a time limit wins over depth."""
    return chess.engine.Limit(time=time) if time is not None else chess.engine.Limit(depth=depth)


def format_eval(score: chess.engine.Score) -> str:
    """Format a White-POV score: '+0.35' for centipawns, '#3' for mate."""
    if score.is_mate():
        return f"#{score.mate()}"
    return f"{score.score() / 100:+.2f}"


@dataclass(frozen=True)
class Analysis:
    """Stockfish's best move for one position."""

    board: chess.Board          # the position that was analysed
    move: chess.Move
    san: str
    score: chess.engine.Score   # from White's point of view
    depth: int | None

    @property
    def after(self) -> chess.Board:
        """The position after the best move is played."""
        board = self.board.copy()
        board.push(self.move)
        return board


def analyse_fen(engine: chess.engine.SimpleEngine, fen: str, limit: chess.engine.Limit) -> Analysis:
    """Validate a FEN and ask the engine for its best move.

    Raises ValueError with a human-readable message when the FEN is malformed,
    the position is illegal, the game is already over or the engine has no move.
    """
    try:
        board = chess.Board(fen)
    except ValueError as exc:
        raise ValueError(f"Invalid FEN: {exc}") from exc

    if not board.is_valid():
        raise ValueError("Invalid position (illegal piece setup, kings in check, etc.).")
    if board.is_game_over():
        raise ValueError(
            f"Game is already over: {board.result()} ({board.outcome().termination.name})."
        )

    info = engine.analyse(board, limit)
    pv = info.get("pv")
    if not pv:
        raise ValueError("Engine returned no move.")

    return Analysis(
        board=board,
        move=pv[0],
        san=board.san(pv[0]),
        score=info["score"].white(),
        depth=info.get("depth"),
    )
