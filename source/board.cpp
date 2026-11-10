#include "board.h"
#include <iostream>
#include <sstream>
#include <algorithm>
#include <cctype>

namespace {
    inline int sq(int row, int col) { return row * 8 + col; }
    inline Color other(Color c) { return c == WHITE ? BLACK : WHITE; }
}

ChessBoard::ChessBoard() {
    board.resize(8, std::vector<std::pair<Color, PieceType>>(8, {WHITE, EMPTY}));
    ep_row = -1;
    ep_col = -1;
    castling_rights[WHITE] = CastlingRights(true, true);
    castling_rights[BLACK] = CastlingRights(true, true);
    turn = WHITE;
    hash = 0;
    reset_board();
}

ChessBoard::~ChessBoard() = default;

void ChessBoard::reset_board() {
    for (int row = 0; row < 8; row++) {
        for (int col = 0; col < 8; col++) {
            board[row][col] = {WHITE, EMPTY};
        }
    }
    
    // Black pieces (top)
    board[0][0] = {BLACK, ROOK};
    board[0][1] = {BLACK, KNIGHT};
    board[0][2] = {BLACK, BISHOP};
    board[0][3] = {BLACK, QUEEN};
    board[0][4] = {BLACK, KING};
    board[0][5] = {BLACK, BISHOP};
    board[0][6] = {BLACK, KNIGHT};
    board[0][7] = {BLACK, ROOK};
    for (int col = 0; col < 8; col++) {
        board[1][col] = {BLACK, PAWN};
    }
    
    // White pieces (bottom)
    board[7][0] = {WHITE, ROOK};
    board[7][1] = {WHITE, KNIGHT};
    board[7][2] = {WHITE, BISHOP};
    board[7][3] = {WHITE, QUEEN};
    board[7][4] = {WHITE, KING};
    board[7][5] = {WHITE, BISHOP};
    board[7][6] = {WHITE, KNIGHT};
    board[7][7] = {WHITE, ROOK};
    for (int col = 0; col < 8; col++) {
        board[6][col] = {WHITE, PAWN};
    }
    
    turn = WHITE;
    castling_rights[WHITE] = CastlingRights(true, true);
    castling_rights[BLACK] = CastlingRights(true, true);
    ep_row = -1;
    ep_col = -1;
    move_stack.clear();
    hash = compute_hash();
}

uint64_t ChessBoard::compute_hash() const {
    uint64_t h = 0;
    for (int row = 0; row < 8; row++) {
        for (int col = 0; col < 8; col++) {
            auto piece = board[row][col];
            if (piece.second != EMPTY) {
                h ^= zobrist.get_piece_key(piece.first, piece.second, sq(row, col));
            }
        }
    }
    if (turn == BLACK) {
        h ^= zobrist.get_turn_key();
    }
    // Castling rights: indices 0=WK, 1=WQ, 2=BK, 3=BQ
    if (castling_rights.at(WHITE).kingside)   h ^= zobrist.get_castling_key(0);
    if (castling_rights.at(WHITE).queenside) h ^= zobrist.get_castling_key(1);
    if (castling_rights.at(BLACK).kingside)  h ^= zobrist.get_castling_key(2);
    if (castling_rights.at(BLACK).queenside) h ^= zobrist.get_castling_key(3);
    if (ep_row != -1) {
        h ^= zobrist.get_enpassant_key(ep_col);
    }
    return h;
}

uint64_t ChessBoard::get_hash() const {
    return hash;
}

bool ChessBoard::has_castling_right(Color color, bool kingside) const {
    auto it = castling_rights.find(color);
    if (it == castling_rights.end()) return false;
    return kingside ? it->second.kingside : it->second.queenside;
}

bool ChessBoard::get_en_passant(int& row, int& col) const {
    if (ep_row == -1) return false;
    row = ep_row;
    col = ep_col;
    return true;
}

void ChessBoard::make_move(const Move& move, bool temporary) {
    (void)temporary; // All moves are recorded so unmake always works.
    
    Color us = turn;
    Color them = other(us);
    
    MoveStackEntry entry;
    entry.move = move;
    entry.hash_before = hash;
    entry.moved_piece = board[move.from_row][move.from_col];
    entry.old_white_rights = castling_rights[WHITE];
    entry.old_black_rights = castling_rights[BLACK];
    entry.old_ep_row = ep_row;
    entry.old_ep_col = ep_col;
    
    PieceType moving = entry.moved_piece.second;
    
    // Detect en passant: pawn moves diagonally to an empty ep square
    bool is_ep = (moving == PAWN) && (move.to_col != move.from_col) &&
                 (board[move.to_row][move.to_col].second == EMPTY) &&
                 (ep_row == move.to_row && ep_col == move.to_col);
    
    // --- Zobrist: remove moving piece from origin ---
    hash ^= zobrist.get_piece_key(us, moving, sq(move.from_row, move.from_col));
    
    // --- Capture ---
    if (is_ep) {
        entry.was_en_passant = true;
        entry.captured_piece = {them, PAWN};
        entry.captured_row = move.from_row;
        entry.captured_col = move.to_col;
        hash ^= zobrist.get_piece_key(them, PAWN, sq(move.from_row, move.to_col));
        board[move.from_row][move.to_col] = {WHITE, EMPTY};
    } else {
        entry.captured_piece = board[move.to_row][move.to_col];
        entry.captured_row = move.to_row;
        entry.captured_col = move.to_col;
        if (entry.captured_piece.second != EMPTY) {
            hash ^= zobrist.get_piece_key(them, entry.captured_piece.second,
                                          sq(move.to_row, move.to_col));
        }
    }
    
    // --- Move piece (with promotion) ---
    PieceType placed = (move.promotion != EMPTY) ? move.promotion : moving;
    board[move.to_row][move.to_col] = {us, placed};
    board[move.from_row][move.from_col] = {WHITE, EMPTY};
    hash ^= zobrist.get_piece_key(us, placed, sq(move.to_row, move.to_col));
    
    // --- Castling: move the rook as well ---
    if (moving == KING && std::abs(move.to_col - move.from_col) == 2) {
        int rook_from_col = (move.to_col > move.from_col) ? 7 : 0;
        int rook_to_col = (move.to_col > move.from_col) ? 5 : 3;
        entry.rook_from_row = move.from_row;
        entry.rook_from_col = rook_from_col;
        entry.rook_to_row = move.from_row;
        entry.rook_to_col = rook_to_col;
        
        auto rook = board[move.from_row][rook_from_col];
        board[move.from_row][rook_to_col] = rook;
        board[move.from_row][rook_from_col] = {WHITE, EMPTY};
        hash ^= zobrist.get_piece_key(us, ROOK, sq(move.from_row, rook_from_col));
        hash ^= zobrist.get_piece_key(us, ROOK, sq(move.from_row, rook_to_col));
    }
    
    // --- Castling rights ---
    // Mover's king/rook leaving home, or enemy rook captured on home square.
    int us_home = (us == WHITE) ? 7 : 0;
    int them_home = (them == WHITE) ? 7 : 0;
    int us_base = (us == WHITE) ? 0 : 2;
    int them_base = (them == WHITE) ? 0 : 2;
    
    auto clear = [&](Color c, int idx) {
        bool& right = (idx % 2 == 0) ? castling_rights[c].kingside
                                     : castling_rights[c].queenside;
        if (right) {
            right = false;
            hash ^= zobrist.get_castling_key(idx);
        }
    };
    
    if (moving == KING) {
        clear(us, us_base);
        clear(us, us_base + 1);
    } else if (moving == ROOK && move.from_row == us_home &&
               (move.from_col == 0 || move.from_col == 7)) {
        clear(us, us_base + (move.from_col == 7 ? 0 : 1));
    }
    
    if (entry.captured_piece.second == ROOK &&
        entry.captured_row == them_home &&
        (entry.captured_col == 0 || entry.captured_col == 7)) {
        clear(them, them_base + (entry.captured_col == 7 ? 0 : 1));
    }
    
    // --- En passant square ---
    int new_ep_row = -1, new_ep_col = -1;
    if (moving == PAWN && std::abs(move.to_row - move.from_row) == 2) {
        new_ep_row = (move.from_row + move.to_row) / 2;
        new_ep_col = move.from_col;
    }
    if (ep_row != -1) {
        hash ^= zobrist.get_enpassant_key(ep_col);
    }
    if (new_ep_row != -1) {
        hash ^= zobrist.get_enpassant_key(new_ep_col);
    }
    ep_row = new_ep_row;
    ep_col = new_ep_col;
    
    // --- Turn ---
    turn = them;
    hash ^= zobrist.get_turn_key();
    
    move_stack.push_back(entry);
}

void ChessBoard::unmake_move(bool temporary) {
    (void)temporary;
    if (move_stack.empty()) return;
    
    MoveStackEntry entry = move_stack.back();
    move_stack.pop_back();
    
    const Move& move = entry.move;
    Color us = other(turn); // side that made the move
    
    // Restore castling rook first (independent of piece squares)
    if (entry.rook_from_row != -1) {
        auto rook = board[entry.rook_to_row][entry.rook_to_col];
        board[entry.rook_from_row][entry.rook_from_col] = rook;
        board[entry.rook_to_row][entry.rook_to_col] = {WHITE, EMPTY};
    }
    
    // Restore moving piece to origin (original type, pre-promotion)
    board[move.from_row][move.from_col] = entry.moved_piece;
    
    // Restore captured piece / vacate target
    if (entry.was_en_passant) {
        board[move.to_row][move.to_col] = {WHITE, EMPTY};
        board[entry.captured_row][entry.captured_col] = entry.captured_piece;
    } else {
        board[move.to_row][move.to_col] = entry.captured_piece;
    }
    
    // Restore state
    castling_rights[WHITE] = entry.old_white_rights;
    castling_rights[BLACK] = entry.old_black_rights;
    ep_row = entry.old_ep_row;
    ep_col = entry.old_ep_col;
    
    turn = us;
    hash = entry.hash_before;
}

std::string ChessBoard::get_fen() {
    std::string fen;
    
    for (int row = 0; row < 8; row++) {
        int empty_count = 0;
        for (int col = 0; col < 8; col++) {
            auto piece = board[row][col];
            if (piece.second == EMPTY) {
                empty_count++;
            } else {
                if (empty_count > 0) {
                    fen += std::to_string(empty_count);
                    empty_count = 0;
                }
                char piece_char;
                switch (piece.second) {
                    case PAWN: piece_char = 'p'; break;
                    case KNIGHT: piece_char = 'n'; break;
                    case BISHOP: piece_char = 'b'; break;
                    case ROOK: piece_char = 'r'; break;
                    case QUEEN: piece_char = 'q'; break;
                    case KING: piece_char = 'k'; break;
                    default: piece_char = '?'; break;
                }
                if (piece.first == WHITE) piece_char = std::toupper(piece_char);
                fen += piece_char;
            }
        }
        if (empty_count > 0) fen += std::to_string(empty_count);
        if (row < 7) fen += "/";
    }
    
    fen += (turn == WHITE) ? " w " : " b ";
    
    std::string castling;
    if (castling_rights[WHITE].kingside) castling += "K";
    if (castling_rights[WHITE].queenside) castling += "Q";
    if (castling_rights[BLACK].kingside) castling += "k";
    if (castling_rights[BLACK].queenside) castling += "q";
    fen += (castling.empty() ? "-" : castling) + " ";
    
    if (ep_row != -1) {
        std::string files = "abcdefgh";
        std::string ranks = "87654321";
        fen += files.substr(ep_col, 1) + ranks.substr(ep_row, 1);
    } else {
        fen += "-";
    }
    
    fen += " 0 1";
    return fen;
}

void ChessBoard::set_from_fen(const std::string& fen) {
    std::istringstream iss(fen);
    std::string token;
    
    for (int row = 0; row < 8; row++) {
        for (int col = 0; col < 8; col++) {
            board[row][col] = {WHITE, EMPTY};
        }
    }
    
    iss >> token;
    int row = 0, col = 0;
    for (char c : token) {
        if (c == '/') {
            row++;
            col = 0;
        } else if (std::isdigit(static_cast<unsigned char>(c))) {
            col += (c - '0');
        } else {
            Color color = std::isupper(static_cast<unsigned char>(c)) ? WHITE : BLACK;
            PieceType piece;
            switch (std::tolower(static_cast<unsigned char>(c))) {
                case 'p': piece = PAWN; break;
                case 'n': piece = KNIGHT; break;
                case 'b': piece = BISHOP; break;
                case 'r': piece = ROOK; break;
                case 'q': piece = QUEEN; break;
                case 'k': piece = KING; break;
                default: piece = EMPTY; break;
            }
            if (row < 8 && col < 8) board[row][col] = {color, piece};
            col++;
        }
    }
    
    iss >> token;
    turn = (token == "w" || token == "W") ? WHITE : BLACK;
    
    iss >> token;
    castling_rights[WHITE] = CastlingRights(false, false);
    castling_rights[BLACK] = CastlingRights(false, false);
    for (char c : token) {
        switch (c) {
            case 'K': castling_rights[WHITE].kingside = true; break;
            case 'Q': castling_rights[WHITE].queenside = true; break;
            case 'k': castling_rights[BLACK].kingside = true; break;
            case 'q': castling_rights[BLACK].queenside = true; break;
        }
    }
    
    iss >> token;
    ep_row = -1;
    ep_col = -1;
    if (token != "-" && token.size() >= 2) {
        std::string files = "abcdefgh";
        std::string ranks = "87654321";
        size_t f = files.find(token[0]);
        size_t r = ranks.find(token[1]);
        if (f != std::string::npos && r != std::string::npos) {
            ep_col = static_cast<int>(f);
            ep_row = static_cast<int>(r);
        }
    }
    
    move_stack.clear();
    hash = compute_hash();
}

void ChessBoard::display_board() {
    std::cout << "  a b c d e f g h" << std::endl;
    for (int row = 0; row < 8; row++) {
        std::cout << (8 - row) << " ";
        for (int col = 0; col < 8; col++) {
            auto piece = board[row][col];
            if (piece.second == EMPTY) {
                std::cout << ". ";
            } else {
                char piece_char;
                if (piece.first == WHITE) {
                    switch (piece.second) {
                        case PAWN: piece_char = 'P'; break;
                        case KNIGHT: piece_char = 'N'; break;
                        case BISHOP: piece_char = 'B'; break;
                        case ROOK: piece_char = 'R'; break;
                        case QUEEN: piece_char = 'Q'; break;
                        case KING: piece_char = 'K'; break;
                        default: piece_char = ' '; break;
                    }
                } else {
                    switch (piece.second) {
                        case PAWN: piece_char = 'p'; break;
                        case KNIGHT: piece_char = 'n'; break;
                        case BISHOP: piece_char = 'b'; break;
                        case ROOK: piece_char = 'r'; break;
                        case QUEEN: piece_char = 'q'; break;
                        case KING: piece_char = 'k'; break;
                        default: piece_char = ' '; break;
                    }
                }
                std::cout << piece_char << " ";
            }
        }
        std::cout << (8 - row) << std::endl;
    }
    std::cout << "  a b c d e f g h" << std::endl;
    std::cout << "Turn: " << (turn == WHITE ? "White" : "Black") << std::endl;
}

std::vector<std::vector<std::pair<Color, PieceType>>>& ChessBoard::get_board() {
    return board;
}

const std::vector<std::vector<std::pair<Color, PieceType>>>& ChessBoard::get_board() const {
    return board;
}

Color ChessBoard::get_turn() const {
    return turn;
}

void ChessBoard::set_turn(Color t) {
    turn = t;
}
