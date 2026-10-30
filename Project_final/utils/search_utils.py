"""Tiện ích chung cho agent tìm kiếm theo thời gian: hạn giờ, lịch độ sâu (lặp sâu dần), sắp xếp nước đi."""

import time

from configs.constants import C_SQUARES, CORNERS, X_SQUARES
from othello.encoding import EMPTY


class SearchTimeout(Exception):
    """Ném ra khi hết ngân sách thời gian giữa lúc tìm kiếm."""


class Deadline:
    """Hạn giờ: dùng 95% ngân sách (chừa chỗ cho phần còn lại của nước đi)."""

    def __init__(self, budget_seconds: float, margin: float = 0.95):
        self.limit = time.perf_counter() + margin * budget_seconds

    def expired(self) -> bool:
        return time.perf_counter() > self.limit


def depth_schedule(game, time_budget, fixed_depth: int, max_depth=None):
    """(các độ sâu cần thử, Deadline hoặc None).
    Không có time_budget -> đúng 1 độ sâu cố định. Có time_budget -> 1, 2, 3, ... (lặp sâu), tối đa số ô trống."""
    if time_budget is None:
        return [fixed_depth], None
    empties = int((game.board == EMPTY).sum())
    cap = max(1, min(max_depth or empties, empties))
    return range(1, cap + 1), Deadline(time_budget)


def order_moves(actions, enabled: bool = True):
    """Góc trước, ô thường giữa, ô X/C cuối (sort ổn định -> kết quả tất định). enabled=False: giữ nguyên thứ tự."""
    if not enabled:
        return list(actions)
    return sorted(actions, key=lambda a: (a in CORNERS, not (a in X_SQUARES or a in C_SQUARES)), reverse=True)
