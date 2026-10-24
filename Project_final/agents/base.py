"""Giao diện chung cho mọi agent.

Quy ước của cả nhóm (xem API.md):
- Agent nhận `game` (OthelloGame) đang ở lượt của nó, trả về MỘT action nằm trong
  game.legal_actions().
- Agent KHÔNG được sửa `game`. Muốn tìm kiếm thì dùng game.clone().
- Agent không xử lý pass: engine lo. select_action chỉ được gọi khi có nước đi.
- time_budget: giây cho mỗi nước (None = không giới hạn / dùng cấu hình mặc định).
"""

from abc import ABC, abstractmethod
from typing import Optional


class Agent(ABC):
    name: str = "Agent"

    def reset(self) -> None:
        """Gọi đầu mỗi ván (xóa thống kê/cây tìm kiếm cũ nếu có)."""

    @abstractmethod
    def select_action(self, game, time_budget: Optional[float] = None):
        """Trả về một action (row, col) hợp lệ."""
        raise NotImplementedError

    def stats(self) -> dict:
        """Thống kê của nước đi vừa rồi (số nút, số mô phỏng...). Dùng cho eval."""
        return {}
