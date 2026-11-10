"""Bridge between the local C++ chess engine and a Lichess bot account.

- Auto-accepts incoming challenges
- Plays games using CppChessEngine (the non-Python engine)
- Streams moves via the Lichess API (berserk)

Setup:
    pip install berserk
    export LICHESS_BOT_TOKEN="lip_..."   # bot token from lichess.org/settings/tokens
    python3 lichess.py
"""

import os
import sys
import threading
import chess
import berserk

from source.cpp_engine_wrapper import CppChessEngine

TOKEN = os.environ.get("LICHESS_BOT_TOKEN") or os.environ.get("LICHESS_TOKEN")
if not TOKEN:
    sys.exit("Set LICHESS_BOT_TOKEN env var with your lichess bot token")

# ENGINE_DEPTH = 6          # max plies for iterative deepening
ENGINE_DEPTH = 24
# ENGINE_TIME = 1.0         # seconds per move (engine also bounded by depth)
ENGINE_TIME=0.1

session = berserk.TokenSession(TOKEN)
client = berserk.Client(session=session)

_engine_local = threading.local()
BOT_USERNAME = None  # set in main()


def get_engine():
    eng = getattr(_engine_local, "engine", None)
    if eng is None:
        eng = CppChessEngine(depth=ENGINE_DEPTH, search_time=ENGINE_TIME, quiet=True)
        _engine_local.engine = eng
    return eng


def board_from_moves(moves_str):
    board = chess.Board()
    if moves_str:
        for uci in moves_str.split():
            board.push_uci(uci)
    return board


def resign_if_lost(board, game_id):
    """Resign when the position is hopeless (checkmate or bare-king material)."""
    if board.is_checkmate():
        try:
            client.bots.resign_game(game_id)
        except Exception:
            pass


def resolve_color(game_id, fallback):
    """Determine the bot's color from the authoritative game record."""
    try:
        g = client.games.export(game_id)
        players = g.get("players", {})
        for side in ("white", "black"):
            name = players.get(side, {}).get("user", {}).get("name")
            if name and BOT_USERNAME and name.lower() == BOT_USERNAME.lower():
                return side
    except Exception as e:
        print(f"[{game_id}] could not resolve color, using event value: {e}")
    return fallback


def play_game(game_id, color):
    """Play one game to completion in its own thread."""
    engine = get_engine()
    color = resolve_color(game_id, color)
    print(f"[{game_id}] playing as {color}")
    try:
        for state in client.bots.stream_game_state(game_id):
            # Stop if the game is no longer in progress
            if state.get("status") not in (None, "started"):
                break
            board = board_from_moves(state.get("moves", ""))

            if board.is_game_over():
                break
            our_turn = (board.turn == chess.WHITE) == (color == "white")
            if not our_turn:
                continue

            move = engine.search(board)
            if move is None:
                resign_if_lost(board, game_id)
                break

            try:
                client.bots.make_move(game_id, move.uci())
            except Exception as e:
                # Move rejected (not our turn yet / game over) - resync and continue
                print(f"[{game_id}] move {move.uci()} rejected: {e}")
    except Exception as e:
        print(f"[{game_id}] game thread error: {e}")
    finally:
        _engine_local.engine = None


def accept_challenge(ch):
    """Accept a challenge if it is still open."""
    try:
        client.challenges.accept(ch["id"])
        challenger = ch.get("challenger", {}).get("name", "?")
        print(f"Accepted challenge from {challenger} "
              f"({(ch.get('variant') or {}).get('key', 'standard')})")
    except Exception as e:
        print(f"Could not accept challenge {ch.get('id')}: {e}")


def main():
    global BOT_USERNAME
    me = client.account.get()["username"]
    BOT_USERNAME = me
    print(f"Bot '{me}' online. Auto-accepting challenges (Ctrl+C to stop)...")

    for event in client.bots.stream_incoming_events():
        etype = event.get("type")

        if etype == "challenge":
            ch = event["challenge"]
            # Open statuses: "created" (pending) or "offline" (challenger left)
            if ch.get("status") in ("created", "offline"):
                accept_challenge(ch)

        elif etype == "challengeDeclined":
            ch = event["challenge"]
            print(f"Challenge {ch.get('id')} was declined "
                  f"(challenger may have canceled or it expired)")

        elif etype == "challengeCanceled":
            ch = event["challenge"]
            print(f"Challenge {ch.get('id')} was canceled")

        elif etype == "gameStart":
            game = event["game"]
            gid = game["id"]
            color = game.get("color")  # 'white' or 'black'
            print(f"Game started: {gid} (you are {color})")
            threading.Thread(target=play_game, args=(gid, color),
                             daemon=True).start()

        elif etype == "gameFinish":
            game = event["game"]
            print(f"Game finished: {game['id']} "
                  f"(winner: {game.get('winner', '?')})")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBot stopped.")
