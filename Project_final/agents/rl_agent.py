"""Agent Reinforcement Learning (cấp 6).

Người phụ trách: Người 3. Giữ đúng API trong API.md.

RLAgent chỉ là bước SUY LUẬN: nạp checkpoint do `train/train_rl.py` (self-play, policy gradient) tạo ra và chọn nước
giống hệt NNAgent (che nước bất hợp lệ, argmax hoặc lấy mẫu theo `temperature`). Khác biệt giữa cấp 5 và cấp 6
nằm ở CÁCH HUẤN LUYỆN (bắt chước expert vs. tự chơi và học từ kết quả), không nằm ở lúc chơi, nên dùng chung mã
suy luận là có chủ đích: so sánh NN vs RL khi đó chỉ phản ánh khác biệt trọng số.
"""

from typing import Optional

from agents.nn_agent import NNAgent


class RLAgent(NNAgent):
    def __init__(self, checkpoint: Optional[str] = None, seed: Optional[int] = None, temperature: float = 0.0,
                 name: str = "RL", model=None, num_threads: Optional[int] = 1):
        super().__init__(checkpoint=checkpoint, seed=seed, temperature=temperature,
                         name=name, model=model, num_threads=num_threads)
