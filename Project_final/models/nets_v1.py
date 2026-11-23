"""Mạng policy-value nhỏ dùng chung cho cấp 5 (NN supervised) và cấp 6 (RL self-play).

Vào : tensor (B, 2, 8, 8) từ `othello.encoding.encode_planes` (plane 0 = quân của người đang đi,
      plane 1 = quân đối thủ). Luôn là GÓC NHÌN NGƯỜI ĐANG ĐI nên một mạng dùng được cho cả Đen lẫn Trắng.
Ra  : (policy_logits (B, 64), value (B,)) với value trong (-1, 1) (tanh), cũng theo góc nhìn người đang đi.
      Policy là logit THÔ cho cả 64 ô; nước bất hợp lệ phải được che bằng `masked_logits` trước khi
      softmax/argmax (ở cả lúc train lẫn lúc chọn nước).

Chạy được hoàn toàn trên CPU (khoảng 158k tham số với cấu hình mặc định channels=64, hidden=128).
"""

from pathlib import Path

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

from othello.encoding import BOARD_SIZE, action_to_index, encode_planes

NEG_INF = -1e9  # logit của ô bất hợp lệ sau khi che (đủ nhỏ để softmax ~ 0, nhưng không gây NaN)


class PolicyValueNet(nn.Module):
    """CNN 3 lớp tích chập 3x3 (giữ nguyên 8x8) + 2 đầu: policy (64 logit) và value (tanh)."""

    def __init__(self, input_planes: int = 2, policy_outputs: int = 64, channels: int = 64, hidden: int = 128):
        super().__init__()
        if policy_outputs != BOARD_SIZE * BOARD_SIZE:
            raise ValueError("policy_outputs phải là 64 để khớp action_to_index")
        self.config = {
            "input_planes": input_planes, "policy_outputs": policy_outputs,
            "channels": channels, "hidden": hidden,
        }
        # thân chung: trích đặc trưng không gian
        self.conv1 = nn.Conv2d(input_planes, channels, 3, padding=1)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1)
        self.conv3 = nn.Conv2d(channels, channels, 3, padding=1)
        # đầu policy: nén kênh (1x1) rồi tuyến tính ra 64 logit
        self.policy_conv = nn.Conv2d(channels, 4, 1)
        self.policy_fc = nn.Linear(4 * BOARD_SIZE * BOARD_SIZE, policy_outputs)
        # đầu value: nén kênh (1x1) -> FC `hidden` -> 1 số, tanh để nằm trong (-1, 1).
        # Dùng 8 kênh (không phải 1): bản 1 kênh + ReLU từng bị "chết" (đầu ra hằng số) trong lần chạy thử đầu tiên.
        self.value_conv = nn.Conv2d(channels, 8, 1)
        self.value_fc1 = nn.Linear(8 * BOARD_SIZE * BOARD_SIZE, hidden)
        self.value_fc2 = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor):
        h = F.relu(self.conv1(x))
        h = F.relu(self.conv2(h))
        h = F.relu(self.conv3(h))
        p = F.relu(self.policy_conv(h)).flatten(1)
        logits = self.policy_fc(p)
        v = F.relu(self.value_conv(h)).flatten(1)
        v = torch.tanh(self.value_fc2(F.relu(self.value_fc1(v)))).squeeze(1)
        return logits, v


def build_model(model_cfg: dict) -> PolicyValueNet:
    """Tạo mạng từ khối `model:` của train_*.yaml (khóa thiếu thì dùng mặc định)."""
    return PolicyValueNet(
        input_planes=int(model_cfg.get("input_planes", 2)),
        policy_outputs=int(model_cfg.get("policy_outputs", 64)),
        channels=int(model_cfg.get("channels", 64)),
        hidden=int(model_cfg.get("hidden", 128)),
    )


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())


# ---------- che nước bất hợp lệ ----------
def legal_mask_from_actions(actions) -> np.ndarray:
    """list[(row, col)] -> mảng bool (64,), True ở ô hợp lệ."""
    mask = np.zeros(BOARD_SIZE * BOARD_SIZE, dtype=bool)
    for a in actions:
        mask[action_to_index(a)] = True
    return mask


def masked_logits(logits: torch.Tensor, legal_mask: torch.Tensor) -> torch.Tensor:
    """Thay logit của ô bất hợp lệ bằng NEG_INF. `legal_mask` bool cùng shape với logits."""
    return logits.masked_fill(~legal_mask, NEG_INF)


def game_to_tensor(game, device="cpu"):
    """OthelloGame -> (planes (1,2,8,8), legal_mask (1,64)) theo góc nhìn người đang đi."""
    planes = encode_planes(game.board, game.current_player)
    mask = legal_mask_from_actions(game.legal_actions())
    return (torch.from_numpy(planes).unsqueeze(0).to(device),
            torch.from_numpy(mask).unsqueeze(0).to(device))


# ---------- lưu / nạp checkpoint ----------
# Checkpoint chỉ chứa kiểu dữ liệu thuần (dict, số, chuỗi, tensor) để torch.load(weights_only=True) nạp được an toàn.
def save_checkpoint(path, model: PolicyValueNet, meta: dict | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    torch.save({"model_config": model.config, "state_dict": state, "meta": meta or {}}, path)


def load_checkpoint(path, device="cpu"):
    """Trả về (model ở chế độ eval, meta). Raise FileNotFoundError kèm hướng dẫn nếu thiếu file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Không thấy checkpoint {path}. Train trước bằng notebook: "
            f"notebooks/04_generate_data.ipynb -> 05_train_supervised.ipynb (cấp 5) -> 06_train_rl.ipynb (cấp 6)."
        )
    blob = torch.load(path, map_location=device, weights_only=True)
    model = PolicyValueNet(**blob["model_config"])
    model.load_state_dict(blob["state_dict"])
    model.to(device).eval()
    return model, blob.get("meta", {})
