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