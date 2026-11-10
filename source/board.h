#ifndef BOARD_H
#define BOARD_H

#include <vector>
#include <string>
#include <unordered_map>
#include <cstdint>
#include "types.h"
#include "zobrist.h"

class ChessBoard {
private:
    std::vector<std::vector<std::pair<Color, PieceType>>> board;
    Color turn;
    
    struct CastlingRights {
        bool kingside;
        bool queenside;
        
        CastlingRights() : kingside(false), queenside(false) {}
        CastlingRights(bool k, bool q) : kingside(k), queenside(q) {}
    };
    std::unordered_map<Color, CastlingRights> castling_rights;
    
    // En passant target square; ep_row == -1 means none
    int ep_row;
    int ep_col;
    
    struct MoveStackEntry {
        Move move;
        std::pair<Color, PieceType> moved_piece;      // piece before promotion
        std::pair<Color, PieceType> captured_piece;   // EMPTY if no capture
        bool was_en_passant;
        int captured_row;
        int captured_col;
        // Castling rook movement (-1 when not a castle)
        int rook_from_row;
        int rook_from_col;
        int rook_to_row;
        int rook_to_col;
        CastlingRights old_white_rights;
        CastlingRights old_black_rights;
        int old_ep_row;
        int old_ep_col;
        uint64_t hash_before;
        
        MoveStackEntry()
            : move(), moved_piece({WHITE, EMPTY}), captured_piece({WHITE, EMPTY}),
              was_en_passant(false), captured_row(-1), captured_col(-1),
              rook_from_row(-1), rook_from_col(-1), rook_to_row(-1), rook_to_col(-1),
              old_ep_row(-1), old_ep_col(-1), hash_before(0) {}
    };
    std::vector<MoveStackEntry> move_stack;
    
    ZobristHash zobrist;
    uint64_t hash;
    
    uint64_t compute_hash() const;
    
public:
    ChessBoard();
    ~ChessBoard();
    
    void reset_board();
    void make_move(const Move& move, bool temporary = false);
    void unmake_move(bool temporary = false);
    std::string get_fen();
    void set_from_fen(const std::string& fen);
    void display_board();
    
    // Getters
    std::vector<std::vector<std::pair<Color, PieceType>>>& get_board();
    const std::vector<std::vector<std::pair<Color, PieceType>>>& get_board() const;
    Color get_turn() const;
    void set_turn(Color t);
    const std::unordered_map<Color, CastlingRights>& get_castling_rights() const;
    bool has_castling_right(Color color, bool kingside) const;
    bool get_en_passant(int& row, int& col) const;
    uint64_t get_hash() const;
};

#endif // BOARD_H
