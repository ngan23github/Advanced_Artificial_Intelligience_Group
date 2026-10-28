"""Agent Neural Network (cấp 5): nạp checkpoint đã train và chọn nước bằng policy của mạng.

Người phụ trách: Người 3. Giữ đúng API trong API.md.

Cách chọn nước (một lần forward, không tìm kiếm):
  1. Mã hóa bàn cờ theo góc nhìn người đang đi (`encode_planes`).
  2. Mạng cho 64 logit policy; logit của ô BẤT HỢP LỆ bị che (`masked_logits`) TRƯỚC khi argmax/softmax,
     nên agent không bao giờ trả về nước sai.
  3. `temperature = 0` (mặc định): lấy argmax (tất định). `temperature > 0`: lấy mẫu từ softmax(logit / T)
     bằng RNG riêng theo `seed` (tái lập được).

`time_budget` bị bỏ qua vì một lần forward luôn rất nhanh (không có vòng lặp cần dừng theo giờ).
`stats()` trả về {"forward_passes": 1, "value_estimate": v}: value_estimate là đánh giá của đầu value cho vị trí
trước nước đi, theo góc nhìn người đang đi (dùng để giải thích nước đi trên UI/báo cáo). Giải đấu chỉ tính trung bình
"nodes" và "simulations", các khóa khác chỉ ghi vào log.
"""

from pathlib import Path
from typing import Optional

import numpy as np
import torch

from agents.base import Agent
from models.nets import game_to_tensor, load_checkpoint, masked_logits
from othello.encoding import index_to_action

# Giải đấu tạo agent MỚI cho mỗi ván; cache để không đọc lại file checkpoint hàng nghìn lần.
# Khóa gồm mtime nên train lại (ghi đè checkpoint) sẽ tự nạp bản mới. Mô hình ở chế độ eval, chỉ đọc => dùng chung an toàn.
_MODEL_CACHE: dict = {}


def _load_cached(path: str):
    p = Path(path)
    key = (str(p.resolve()), p.stat().st_mtime_ns if p.exists() else None)
    if key not in _MODEL_CACHE:
        _MODEL_CACHE[key] = load_checkpoint(p, device="cpu")
    return _MODEL_CACHE[key]


class NNAgent(Agent):
    def __init__(self, checkpoint: Optional[str] = None, seed: Optional[int] = None, temperature: float = 0.0,
                 name: str = "NN", model=None, num_threads: Optional[int] = 1):
        """
        checkpoint : đường dẫn file .pt (khai báo trong agents.yaml -> params).
        temperature: 0 = argmax; >0 = lấy mẫu theo softmax(logit / T).
        model      : (dùng khi huấn luyện/đánh giá nội bộ) truyền thẳng mạng đã có thay cho `checkpoint`.
        num_threads: số luồng torch khi chạy trong giải đấu nhiều tiến trình (1 để các worker không giành CPU).
        """
        if model is None and checkpoint is None:
            raise ValueError("NNAgent cần `checkpoint` (đường dẫn .pt) hoặc `model`.")
        if temperature < 0:
            raise ValueError("temperature phải >= 0")
        self.name = name
        self.seed = seed
        self.temperature = float(temperature)
        self.checkpoint = checkpoint
        self._rng = np.random.default_rng(seed)          # RNG riêng, không đụng RNG toàn cục
        if model is None:
            if num_threads:
                torch.set_num_threads(num_threads)
            model, _ = _load_cached(checkpoint)
        self.model = model
        self._stats: dict = {}

    def reset(self) -> None:
        self._stats = {}  # giữ nguyên dòng RNG giữa các ván (giống RandomAgent)

    @torch.no_grad()
    def select_action(self, game, time_budget: Optional[float] = None):
        legal = game.legal_actions()
        if not legal:
            raise RuntimeError("Không có nước đi hợp lệ để chọn.")
        planes, mask = game_to_tensor(game)
        device = next(self.model.parameters()).device
        logits, value = self.model(planes.to(device))
        logits = masked_logits(logits, mask.to(device))[0]
        if self.temperature == 0.0:
            idx = int(torch.argmax(logits))
        else:
            probs = torch.softmax(logits / self.temperature, dim=0).double().cpu().numpy()
            probs /= probs.sum()
            idx = int(self._rng.choice(len(probs), p=probs))
        action = index_to_action(idx)
        self._stats = {"forward_passes": 1, "value_estimate": float(value[0])}
        assert action in legal, "bug: nước được chọn không hợp lệ dù đã che"
        return action

    def stats(self) -> dict:
        return dict(self._stats)
