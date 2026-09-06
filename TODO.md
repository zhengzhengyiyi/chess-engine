# TODO.md - Pure Math Chess Engine Architecture

## Phase 1: Board Representation & State Management
- [ ] Implement board state representation (Array/Bitboards).
- [ ] Track piece types (`P`, `N`, `B`, `R`, `Q`, `K`) and colors (`WHITE`, `BLACK`).
- [ ] Track auxiliary states: turn, castling rights, en passant square, move counters.
- [ ] Build `make_move(move)` and `unmake_move(move)` methods for lightweight tree traversal.

## Phase 2: Move Generation (No Third-Party Engines)
- [ ] Generate pseudo-legal moves for sliding pieces, stepping pieces, pawns, and castling.
- [ ] Implement `is_square_attacked(square, color)` to filter out moves leaving King in check.
- [ ] Filter pseudo-legal moves into fully legal moves.
- [ ] Detect game-over terminal states (Checkmate, Stalemate).

## Phase 3: Pure Material Evaluation (Zero Tactical Heuristics)
- [ ] Assign base static values: Pawn=100, Knight=320, Bishop=330, Rook=500, Queen=900, King=20000.
- [ ] Calculate net material score: `Sum(White Pieces) - Sum(Black Pieces)`.
- [ ] Implement Mate Distance scoring (`100000 - ply_count`) to prioritize fast checkmates.

## Phase 4: Search Engine & Horizon Fix
- [ ] Load `Settings.depth` and convert to search plies (`plies = Settings.depth * 2`).
- [ ] Implement `quiescence_search(alpha, beta)` to extend tactical captures beyond depth 0 (prevents piece-wasting/horizon effect).
- [ ] Implement `minimax(ply, alpha, beta, is_maximizing)` with Alpha-Beta pruning using the material evaluator + quiescence search.

## Phase 5: Move Ranking Pipeline
- [ ] Iterate through all legal moves at the root position.
- [ ] Run `minimax()` on each move's resulting board state to get its guaranteed evaluation score.
- [ ] Sort the list of root moves by evaluation score (descending for White, ascending for Black).
- [ ] Return the sorted array of moves from best to worst.