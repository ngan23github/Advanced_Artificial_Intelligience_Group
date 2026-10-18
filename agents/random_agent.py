"""Cấp 1: Random agent, chọn đều trong các nước hợp lệ. Dùng làm baseline."""

import random
from typing import Optional

from agents.base import Agent


class RandomAgent(Agent):
    def __init__(self, seed: Optional[int] = None, name: str = "Random"):
        self.name = name
        self.seed = seed
        self._rng = random.Random(seed)  # RNG riêng, không đụng random toàn cục

    def reset(self) -> None:
        pass  # giữ nguyên dòng RNG để nhiều ván liên tiếp vẫn tái lập được từ 1 seed

    def select_action(self, game, time_budget: Optional[float] = None):
        actions = game.legal_actions()
        if not actions:
            raise RuntimeError("Không có nước đi hợp lệ để chọn.")
        return self._rng.choice(actions)
