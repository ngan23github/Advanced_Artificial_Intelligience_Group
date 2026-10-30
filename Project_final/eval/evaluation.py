"""Hàm lượng giá thế cờ cho agent tìm kiếm: kiểm tra tham số + chấm điểm.
s
"""

from othello import board_features as bf
from configs.constants import DEFAULT_EVAL, EVAL_KEYS, EVAL_SCALES, WIN_SCORE
# from othello.encoding import opponent


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


def evaluate_state(board, player: int, eval_config: dict = None, weights: dict = None) -> float:
    """Điểm tĩnh của thế cờ (không kết thúc) theo góc nhìn `player`.
    eval_config / weights chưa chuẩn hóa vẫn dùng được (None = mặc định)."""
    cfg = DEFAULT_EVAL if eval_config is None else {**DEFAULT_EVAL, **eval_config}
    scale = EVAL_SCALES if weights is None else {**EVAL_SCALES, **weights}
    score = 0.0
    if cfg["disc_diff"]:
        m, o = bf.disc_counts(board, player)
        if m + o:
            score += scale["disc_diff"] * (m - o) / (m + o)
    if cfg["corners"]:
        m, o = bf.corner_counts(board, player)
        score += scale["corners"] * (m - o)
    if cfg["x_c_squares"]:
        score += scale["x_c_squares"] * bf.x_c_balance(board, player)
    if cfg["mobility"]:
        m, o = bf.mobility_counts(board, player)
        if m + o:
            score += scale["mobility"] * (m - o) / (m + o)
    return float(score)
