#ifndef MOVEGEN_H
#define MOVEGEN_H

#include <vector>
#include "types.h"
#include "board.h"

class MoveGenerator {
private:
    ChessBoard& cb;
    std::vector<std::vector<std::pair<Color, PieceType>>>& board;
    Color turn;
    
    bool is_on_board(int row, int col) const;
    void add_pawn_moves(std::vector<Move>& moves, int row, int col);
    void add_knight_moves(std::vector<Move>& moves, int row, int col);
    void add_sliding_moves(std::vector<Move>& moves, int row, int col, const int directions[8][2], int num_dirs);
    void add_king_moves(std::vector<Move>& moves, int row, int col);
    void add_castling_moves(std::vector<Move>& moves, int row, int col);
    
public:
    MoveGenerator(ChessBoard& b);
    std::vector<Move> generate_pseudo_legal_moves();
    std::vector<Move> generate_legal_moves();
    bool is_square_attacked(int row, int col, Color by_color) const;
    bool is_in_check(Color color) const;
};

#endif // MOVEGEN_H
