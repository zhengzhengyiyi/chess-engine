import chess
import chess.pgn
import io

# Paste your UCI moves here
uci_moves = "g1f3 b8c6 f3g5 c6d4 e2e4 e7e5 c2c3 d8g5 c3c4 g8f6 h2h4 g5h6 f2f3 h6g6 d2d3 f8b4 b1c3 g6g3 e1d2 g3f4 d2e1 b4c3 b2c3 f4g3 e1d2 g3f4 d2e1 f4g3 e1d2 g3f4 d2e1 f4g3 e1d2 g3f4 d2e1 f4g3 e1d2 g3f2 f1e2 d4e2 d1e2 f6e4 f3e4 f2f4 e2e3 f4g4 e3f3 g4g6 g2g3 g6h6 f3e3 h6g6 d3d4 g6d6 d4d5 h7h6 d2e2 g7g6 h4h5 g6h5 h1h5 f7f6 h1h6 h8h6 e3h6 c7c6 h6h5 e8f8 c1h6 f8e7 d5c6 d6c6 e2f2 c6c4 a2a3 c4c3 a1a2 c3c6 g3g4 c6e4 h6e3 d7d6 a3a4 c8g4 h5h6 e4f3 f2g1 f3g3 a2g2 g3e1 g1h2 d6d5 e3c5 e7e8 h6h8 e8f7 h8a8 e1h4 h2g1 h4e1 g1h2 e1h4 h2g1 h4e1 g1h2 e1h4 h2g1 h4e1 g1h2 e1h4 h2g1 h4e1 g1h2 e1h4 h2g1 h4e1 g1h2 e1h4 h2g1 h4e1 g1h2 e1h4 h2g1 h4e1 g1h2 e1h4 h2g1 h4e1 g1h2"

board = chess.Board()
game = chess.pgn.Game()
node = game

# Loop through and push each move, translating to SAN
for m_str in uci_moves.split():
    move = chess.Move.from_uci(m_str)
    node = node.add_variation(move)
    board.push(move)

# Export to standard PGN string
exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=True)
pgn_output = game.accept(exporter)
print(pgn_output)