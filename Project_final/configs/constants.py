"""Hằng số hình học bàn cờ và danh sách luật dùng chung cho hệ thống."""

# 4 góc bàn cờ Othello
CORNERS = frozenset({(0, 0), (0, 7), (7, 0), (7, 7)})

# Các ô X / C nguy hiểm -> Trỏ tới góc kề tương ứng
X_SQUARES = {
    (1, 1): (0, 0), (1, 6): (0, 7),
    (6, 1): (7, 0), (6, 6): (7, 7)
}

C_SQUARES = {
    (0, 1): (0, 0), (1, 0): (0, 0),
    (0, 6): (0, 7), (1, 7): (0, 7),
    (6, 0): (7, 0), (7, 1): (7, 0),
    (6, 7): (7, 7), (7, 6): (7, 7)
}

# Danh sách tên các luật ưu tiên
RULE_NAMES = (
    "win_now",
    "take_corner",
    "avoid_x_square",
    "avoid_c_square",
    "maximize_mobility",
    "maximize_discs"
)
DEFAULT_PRIORITIES = list(RULE_NAMES)
ENDGAME_ORDER = ("win_now", "take_corner", "maximize_discs", "maximize_mobility")

# ---------------------------------------------------------------------------
# THÊM MỚI: mức nguy hiểm của ô và hằng số hàm lượng giá của Alpha-Beta
# ---------------------------------------------------------------------------
DANGER_X, DANGER_C = 2, 1            # mức nguy hiểm: 2 = ô X, 1 = ô C (góc kề còn trống), 0 = an toàn
XC_PENALTY = {DANGER_X: 30.0, DANGER_C: 15.0}   # điểm phạt cho mỗi quân đứng trên ô nguy hiểm

WIN_SCORE = 10_000.0                 # điểm nút KẾT THÚC ván: thắng = +WIN_SCORE + chênh lệch quân (thua thì âm)

# các thành phần hàm lượng giá (khớp khóa `eval` trong agents.yaml) và độ lớn mặc định của chúng
EVAL_KEYS = ("disc_diff", "mobility", "corners", "x_c_squares", "stability")
DEFAULT_EVAL = {"disc_diff": True, "mobility": True, "corners": True, "x_c_squares": True, "stability": False}
EVAL_SCALES = {"disc_diff": 10.0, "mobility": 20.0, "corners": 100.0, "x_c_squares": 1.0, "stability": 0.0}

"""Hằng số đánh giá dùng chung cho hệ thống."""

WIN_SCORE = 10000.0

EVAL_KEYS = ("disc_diff", "corners", "x_c_squares", "mobility", "stability")

DEFAULT_EVAL = {
    "disc_diff": True,
    "corners": True,
    "x_c_squares": True,
    "mobility": True,
    "stability": False,
}

EVAL_SCALES = {
    "disc_diff": 10.0,
    "corners": 100.0,
    "x_c_squares": 30.0,
    "mobility": 20.0,
    "stability": 0.0,
}