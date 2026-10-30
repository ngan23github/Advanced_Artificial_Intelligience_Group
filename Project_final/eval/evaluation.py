"""Hàm lượng giá thế cờ cho agent tìm kiếm: kiểm tra tham số + chấm điểm."""

from othello import board_features as bf
from configs.constants import DEFAULT_EVAL, EVAL_KEYS, EVAL_SCALES, WIN_SCORE
from configs.constants import CORNERS, X_SQUARES, C_SQUARES
from othello.encoding import BLACK, EMPTY, opponent
from othello.rules import apply_move, count_discs, legal_moves

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
    """Hàm đánh giá tĩnh (Heuristic Evaluation) cho trạng thái ở lá cây."""
    if eval_config is None:
        eval_config = {
            "disc_diff": True,
            "mobility": True,
            "corners": True,
            "x_c_squares": True,
        }

    opp = opponent(player)
    score = 0.0

    # 1. Chênh lệch số quân (disc_diff) - Đã sửa dấu nhân *
    if eval_config.get("disc_diff", True):
        p_coins = (board == player).sum()
        o_coins = (board == opp).sum()
        if p_coins + o_coins > 0:
            score += 10.0 * (p_coins - o_coins) / (p_coins + o_coins)

    # 2. Chiếm góc (corners) - Đã sửa dấu nhân *
    if eval_config.get("corners", True):
        p_corners = sum(1 for r, c in CORNERS if board[r, c] == player)
        o_corners = sum(1 for r, c in CORNERS if board[r, c] == opp)
        score += 100.0 * (p_corners - o_corners)

    # 3. Tránh ô X/C nguy hiểm (x_c_squares)
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

    # 4. Độ cơ động (mobility) - Đã sửa dấu nhân *
    if eval_config.get("mobility", True):
        p_moves = len(legal_moves(board, player))
        o_moves = len(legal_moves(board, opp))
        if p_moves + o_moves > 0:
            score += 20.0 * (p_moves - o_moves) / (p_moves + o_moves)

    return float(score)

