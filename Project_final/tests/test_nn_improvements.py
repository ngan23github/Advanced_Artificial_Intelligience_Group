"""Cải tiến v2 của NN/RL: khối residual trong mạng, trộn đối thủ cố định và reward margin trong self-play."""
import random

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from agents.registry import build_agent_by_name  # noqa: E402
from models.nets import PolicyValueNet, build_model, count_params, load_checkpoint, save_checkpoint  # noqa: E402
from notebook_utils import load_defs  # noqa: E402

OLD_KEYS = {"conv1.weight", "conv1.bias", "conv2.weight", "conv2.bias", "conv3.weight", "conv3.bias",
            "policy_conv.weight", "policy_conv.bias", "policy_fc.weight", "policy_fc.bias",
            "value_conv.weight", "value_conv.bias", "value_fc1.weight", "value_fc1.bias",
            "value_fc2.weight", "value_fc2.bias"}


def test_res_blocks_change_size_and_keep_output_shape():
    base, deep = PolicyValueNet(), PolicyValueNet(num_res_blocks=2)
    assert count_params(deep) > count_params(base)
    x = torch.randn(5, 2, 8, 8)
    logits, v = deep(x)
    assert logits.shape == (5, 64) and v.shape == (5,)
    assert deep.config["num_res_blocks"] == 2 and base.config["num_res_blocks"] == 0


def test_old_checkpoint_format_still_loads(tmp_path):
    """Checkpoint v1 (model_config không có num_res_blocks, state_dict chỉ có khóa cũ) phải nạp được."""
    m = PolicyValueNet()
    assert set(m.state_dict()) == OLD_KEYS                       # mạng 0 khối: không thêm khóa lạ
    path = tmp_path / "old.pt"
    cfg = {k: v for k, v in m.config.items() if k != "num_res_blocks"}
    torch.save({"model_config": cfg, "state_dict": {k: v.clone() for k, v in m.state_dict().items()}, "meta": {}}, path)
    loaded, _ = load_checkpoint(path)
    assert loaded.config["num_res_blocks"] == 0
    x = torch.randn(3, 2, 8, 8)
    assert torch.allclose(m.eval()(x)[0], loaded(x)[0])


def test_new_checkpoint_roundtrip_and_build_model(tmp_path):
    m = build_model({"channels": 32, "hidden": 16, "num_res_blocks": 2})
    save_checkpoint(tmp_path / "m.pt", m, meta={"k": 1})
    loaded, meta = load_checkpoint(tmp_path / "m.pt")
    assert loaded.config == m.config and meta == {"k": 1}
    x = torch.randn(2, 2, 8, 8)
    assert torch.allclose(m.eval()(x)[1], loaded(x)[1])


@pytest.fixture(scope="module")
def rl():
    return load_defs("06_train_rl.ipynb")


REWARD = {"win": 1.0, "draw": 0.0, "loss": -1.0}


def _run(rl, **kw):
    torch.manual_seed(0)                                   # cùng trọng số mạng => cùng ván, chỉ khác reward
    model = PolicyValueNet(channels=16, hidden=16)
    return rl["self_play_batch"](model, 8, 4, 1.0, random.Random(0), torch.Generator().manual_seed(0), "cpu", REWARD, 1.0, **kw)


def test_pure_self_play_is_default(rl):
    batch, st = _run(rl)
    assert st["vs_fixed_frac"] == 0.0 and batch is not None


def test_fixed_opponent_games_only_learn_from_network_moves(rl):
    pool, probs = [build_agent_by_name("heuristic", seed=1), None], [1.0, 0.0]
    b_mix, st_mix = _run(rl, opponent_pool=pool, opponent_probs=probs)
    b_self, st_self = _run(rl)
    assert st_mix["vs_fixed_frac"] == 1.0
    # cùng 8 ván: đấu agent cố định chỉ ghi nước của mạng (~ một nửa số nước) so với self-play ghi cả hai bên
    assert len(b_mix["action"]) < 0.75 * len(b_self["action"])


def test_build_opponent_pool_validates_weights(rl):
    pool, probs = rl["build_opponent_pool"]([{"agent": "heuristic", "weight": 0.25}], 0)
    assert pool[-1] is None and probs == pytest.approx([0.25, 0.75])
    with pytest.raises(ValueError):
        rl["build_opponent_pool"]([{"agent": "heuristic", "weight": 0.7}, {"agent": "random", "weight": 0.5}], 0)


def test_margin_coef_changes_returns_within_bound(rl):
    plain, _ = _run(rl)
    shaped, _ = _run(rl, margin_coef=0.5)
    r0, r1 = plain["ret"].numpy(), shaped["ret"].numpy()
    assert r0.shape == r1.shape and not np.allclose(r0, r1)
    assert np.all(np.abs(r1) <= 1.0 + 0.5 + 1e-6)
    assert np.all(np.abs(r1 - r0) <= 0.5 + 1e-6)
