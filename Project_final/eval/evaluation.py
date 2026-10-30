"""Hàm lượng giá thế cờ cho agent tìm kiếm: kiểm tra tham số + chấm điểm."""

from othello import board_features as bf
from configs.constants import DEFAULT_EVAL, EVAL_KEYS, EVAL_SCALES, WIN_SCORE
from configs.constants import CORNERS, X_SQUARES, C_SQUARES
from othello.encoding import BLACK, EMPTY, opponent
from othello.rules import apply_move, count_discs, legal_moves
from othello.bitboard import CORNER_MASK, flips_mask, legal_mask


def normalize_eval_config(eval_config=None) -> dict:
    """Gộp `eval` từ yaml với mặc định; khóa lạ -> ValueError; stability=true chưa cài đặt -> NotImplementedError."""
    cfg = dict(DEFAULT_EVAL)
    for k, v in (eval_config or {}).items():
        if k not in EVAL_KEYS:
            raise ValueError(f"eval: khóa không biết '{k}'. Hợp lệ: {list(EVAL_KEYS)}")
        cfg[k] = bool(v)
    if cfg["stability"]:
        raise NotImplementedError("eval.stability chưa cài đặt")
    return cfg


def normalize_weights(weights=None) -> dict:
    """Độ lớn (hệ số) của từng thành phần; dùng để tune. Khóa lạ -> ValueError."""
    scales = dict(EVAL_SCALES)
    for k, v in (weights or {}).items():
        if k not in EVAL_KEYS:
            raise ValueError(f"weights: khóa không biết '{k}'. Hợp lệ: {list(EVAL_KEYS)}")
        scales[k] = float(v)
    return scales


def terminal_score(board, root_player: int) -> float:
    """Điểm nút KẾT THÚC ván: thắng luôn cao hơn mọi điểm heuristic, thua luôn thấp hơn."""
    mine, theirs = bf.disc_counts(board, root_player)
    diff = mine - theirs
    return WIN_SCORE + diff if diff > 0 else (-WIN_SCORE + diff if diff < 0 else 0.0)


def evaluate_state(board, player: int, eval_config: dict = None) -> float:
    """Hàm đánh giá tĩnh (Heuristic Evaluation) cho trạng thái ở lá cây (Phiên bản Numpy)."""
    if eval_config is None:
        eval_config = {
            "disc_diff": True,
            "mobility": True,
            "corners": True,
            "x_c_squares": True,
        }

    opp = opponent(player)
    score = 0.0

    if eval_config.get("disc_diff", True):
        p_coins = (board == player).sum()
        o_coins = (board == opp).sum()
        if p_coins + o_coins > 0:
            score += 10.0 * (p_coins - o_coins) / (p_coins + o_coins)

    if eval_config.get("corners", True):
        p_corners = sum(1 for r, c in CORNERS if board[r, c] == player)
        o_corners = sum(1 for r, c in CORNERS if board[r, c] == opp)
        score += 100.0 * (p_corners - o_corners)

    if eval_config.get("x_c_squares", True):
        danger_penalty = 0
        for x_pos, corner_pos in X_SQUARES.items():
            if board[corner_pos] == EMPTY:
                if board[x_pos] == player:
                    danger_penalty -= 30
                elif board[x_pos] == opp:
                    danger_penalty += 30

        for c_pos, corner_pos in C_SQUARES.items():
            if board[corner_pos] == EMPTY:
                if board[c_pos] == player:
                    danger_penalty -= 15
                elif board[c_pos] == opp:
                    danger_penalty += 15
        score += danger_penalty

    if eval_config.get("mobility", True):
        p_moves = len(legal_moves(board, player))
        o_moves = len(legal_moves(board, opp))
        if p_moves + o_moves > 0:
            score += 20.0 * (p_moves - o_moves) / (p_moves + o_moves)

    return float(score)


# ---------------------------------------------------------------------------
# Phiên bản BITBOARD của evaluate_state (dùng cho AlphaBetaAgent siêu tốc)
# ---------------------------------------------------------------------------
def _sq_bit(pos) -> int:
    return 1 << (pos[0] * 8 + pos[1])


_CORNER_GROUPS = tuple(
    (_sq_bit(corner),
     _sq_bit(x_pos),
     sum(_sq_bit(c_pos) for c_pos, c_corner in C_SQUARES.items() if c_corner == corner))
    for x_pos, corner in X_SQUARES.items()
)


def _evaluate_bb(me: int, opp: int, cfg: dict) -> float:
    """Đánh giá theo góc nhìn `me` trực tiếp trên Bitboard 64-bit."""
    score = 0.0
    if cfg.get("disc_diff", True):
        p_coins, o_coins = me.bit_count(), opp.bit_count()
        if p_coins + o_coins > 0:
            score += 10.0 * (p_coins - o_coins) / (p_coins + o_coins)

    if cfg.get("corners", True):
        score += 100.0 * ((me & CORNER_MASK).bit_count() - (opp & CORNER_MASK).bit_count())

    if cfg.get("x_c_squares", True):
        danger = 0
        occupied = me | opp
        for corner_bit, x_bit, c_mask in _CORNER_GROUPS:
            if not (occupied & corner_bit):
                if me & x_bit:
                    danger -= 30
                elif opp & x_bit:
                    danger += 30
                danger -= 15 * (me & c_mask).bit_count()
                danger += 15 * (opp & c_mask).bit_count()
        score += danger

    if cfg.get("mobility", True):
        p_moves = legal_mask(me, opp).bit_count()
        o_moves = legal_mask(opp, me).bit_count()
        if p_moves + o_moves > 0:
            score += 20.0 * (p_moves - o_moves) / (p_moves + o_moves)

    return float(score)