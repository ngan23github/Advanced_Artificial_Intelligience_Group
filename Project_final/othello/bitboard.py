"""Bitboard cho Othello 8x8: thuần Python (int 64 bit), không cần thư viện ngoài.

Quy ước bit: bit i = ô (row, col) với i = row * 8 + col (cùng quy ước `action_to_index`).
Duyệt bit từ thấp lên cao <=> duyệt ô theo thứ tự (row, col) tăng dần, nên danh sách nước đi
sinh ra từ đây GIỐNG HỆT thứ tự của `rules.legal_moves` bản cũ (kết quả tất định không đổi).

Vì sao cần file này: bản cũ duyệt 64 ô x 8 hướng bằng vòng lặp Python + chỉ số numpy (rất chậm,
~0.28 ms mỗi lần `legal_moves`). Bitboard tính cùng việc đó bằng vài chục phép dịch bit (~10 us).
"""

import numpy as np

FULL = 0xFFFFFFFFFFFFFFFF
NOT_COL0 = 0xFEFEFEFEFEFEFEFE   # loại cột 0 (sau khi dịch sang phải/chéo bị "tràn" từ cột 7)
NOT_COL7 = 0x7F7F7F7F7F7F7F7F   # loại cột 7 (sau khi dịch sang trái)

# (số bit dịch, mặt nạ sau dịch). Dịch trái = tăng chỉ số bit; dịch phải = giảm.
#   << 1: sang cột bên phải (col+1)     << 8: xuống hàng dưới (row+1)
#   << 9: xuống-phải                    << 7: xuống-trái
SHIFT_LEFT = ((1, NOT_COL0), (8, FULL), (9, NOT_COL0), (7, NOT_COL7))
SHIFT_RIGHT = ((1, NOT_COL7), (8, FULL), (9, NOT_COL7), (7, NOT_COL0))

CORNER_MASK = (1 << 0) | (1 << 7) | (1 << 56) | (1 << 63)


def popcount(x: int) -> int:
    return x.bit_count()


def board_to_bb(board: np.ndarray) -> tuple:
    """Mảng numpy (8,8) (Đen=1, Trắng=-1) -> (black_bb, white_bb)."""
    flat = board.ravel()
    black = int.from_bytes(np.packbits(flat == 1, bitorder="little").tobytes(), "little")
    white = int.from_bytes(np.packbits(flat == -1, bitorder="little").tobytes(), "little")
    return black, white


def bb_to_squares(mask: int) -> list:
    """Mặt nạ bit -> list[(row, col)] theo thứ tự tăng dần của (row, col)."""
    out = []
    while mask:
        low = mask & -mask
        out.append(divmod(low.bit_length() - 1, 8))
        mask ^= low
    return out


def legal_mask(me: int, opp: int) -> int:
    """Mặt nạ các ô `me` có thể đi (đặt quân), khi `opp` là quân đối thủ."""
    empty = ~(me | opp) & FULL
    moves = 0
    for s, m in SHIFT_LEFT:
        x = ((me << s) & m) & opp
        x |= ((x << s) & m) & opp
        x |= ((x << s) & m) & opp
        x |= ((x << s) & m) & opp
        x |= ((x << s) & m) & opp
        x |= ((x << s) & m) & opp
        moves |= ((x << s) & m) & empty
    for s, m in SHIFT_RIGHT:
        x = ((me >> s) & m) & opp
        x |= ((x >> s) & m) & opp
        x |= ((x >> s) & m) & opp
        x |= ((x >> s) & m) & opp
        x |= ((x >> s) & m) & opp
        x |= ((x >> s) & m) & opp
        moves |= ((x >> s) & m) & empty
    return moves


def flips_mask(me: int, opp: int, sq_bit: int) -> int:
    """Mặt nạ các quân đối thủ bị lật khi `me` đặt quân tại ô `sq_bit` (1 << index)."""
    flips = 0
    for s, m in SHIFT_LEFT:
        line = 0
        t = (sq_bit << s) & m
        while t & opp:
            line |= t
            t = (t << s) & m
        if t & me:
            flips |= line
    for s, m in SHIFT_RIGHT:
        line = 0
        t = (sq_bit >> s) & m
        while t & opp:
            line |= t
            t = (t >> s) & m
        if t & me:
            flips |= line
    return flips
