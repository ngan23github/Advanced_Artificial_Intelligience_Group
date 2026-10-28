"""Test phần học máy (Người 3).

Logic huấn luyện nằm trong notebook 04-06; ở đây:
  - các hàm trong ô `defs` của notebook được nạp và test đơn vị (không cần Jupyter),
  - cả 3 notebook được chạy từ đầu đến cuối ở chế độ QUICK_TEST (dữ liệu nhỏ, ghi ra thư mục tạm).
Không kiểm tra độ mạnh của agent, chỉ kiểm tra pipeline đúng.
"""

import json
import random

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from agents.nn_agent import NNAgent  # noqa: E402
from models.nets import (NEG_INF, PolicyValueNet, game_to_tensor, legal_mask_from_actions,  # noqa: E402
                         load_checkpoint, masked_logits, save_checkpoint)
from othello.encoding import BLACK, encode_planes  # noqa: E402
from othello.game import OthelloGame  # noqa: E402
from othello.rules import legal_moves  # noqa: E402
from notebook_utils import load_defs, run_notebook  # noqa: E402

REWARD = {"win": 1.0, "draw": 0.0, "loss": -1.0}
EXPERT = "heuristic"   # phải là mục có thật trong configs/agents.yaml (expert tạm `temp_positional` đã bị bỏ)


def random_positions(n, seed=0):
    """n vị trí đa dạng từ các ván ngẫu nhiên (kèm người đang đi)."""
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        g = OthelloGame()
        while not g.is_terminal():
            if rng.random() < 0.2:
                out.append((g.board.copy(), g.current_player))
            g.step(rng.choice(g.legal_actions()))
    return out[:n]


@pytest.fixture(scope="module")
def nb_data():
    return load_defs("04_generate_data.ipynb")


@pytest.fixture(scope="module")
def nb_sup():
    return load_defs("05_train_supervised.ipynb")


@pytest.fixture(scope="module")
def nb_rl():
    return load_defs("06_train_rl.ipynb")


# ---------- mạng, mặt nạ, checkpoint, agent ----------
def test_net_shapes_and_masking():
    net = PolicyValueNet(channels=8, hidden=16)
    game = OthelloGame()
    planes, mask = game_to_tensor(game)
    logits, value = net(planes)
    assert logits.shape == (1, 64) and value.shape == (1,) and -1 <= float(value.detach()) <= 1
    masked = masked_logits(logits, mask)
    assert (masked[~mask] == NEG_INF).all()
    assert mask.sum() == len(game.legal_actions())


def test_checkpoint_roundtrip(tmp_path):
    net = PolicyValueNet(channels=8, hidden=16)
    save_checkpoint(tmp_path / "m.pt", net, meta={"seed": 1})
    net2, meta = load_checkpoint(tmp_path / "m.pt")
    x = torch.randn(3, 2, 8, 8)
    assert torch.allclose(net(x)[0], net2(x)[0]) and meta["seed"] == 1


def test_missing_checkpoint_gives_helpful_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="notebook"):
        NNAgent(checkpoint=str(tmp_path / "khong_co.pt"))


def test_nn_agent_stats_and_greedy_is_deterministic(tmp_path):
    save_checkpoint(tmp_path / "m.pt", PolicyValueNet(channels=8, hidden=16))
    g = OthelloGame()
    a1 = NNAgent(checkpoint=str(tmp_path / "m.pt"))
    a2 = NNAgent(checkpoint=str(tmp_path / "m.pt"), seed=123)   # argmax: seed không ảnh hưởng
    assert a1.select_action(g) == a2.select_action(g)
    assert a1.stats()["forward_passes"] == 1 and -1 <= a1.stats()["value_estimate"] <= 1


# ---------- notebook 04: sinh dữ liệu ----------
def make_games(nb, n=12, opening_plies=6, eps=0.05):
    return [nb["generate_one_game"](1000 + i, EXPERT, opening_plies, eps) for i in range(n)]


def test_generate_one_game_is_reproducible_and_labels_valid(nb_data):
    a = nb_data["generate_one_game"](5, EXPERT, 6, 0.05)
    b = nb_data["generate_one_game"](5, EXPERT, 6, 0.05)
    assert a["moves"] == b["moves"]
    assert a["legal"][np.arange(len(a["action"])), a["action"]].all()    # nhãn luôn là nước hợp lệ
    assert set(np.unique(a["value"])) <= {-1.0, 0.0, 1.0}
    # value theo góc nhìn người đi: hai bên cùng ván có dấu đối nhau (trừ hòa)
    assert set(a["value"][a["player"] == BLACK]) == {float(a["result_black"])}
    assert set(a["value"][a["player"] != BLACK]) == {-float(a["result_black"])}


def test_split_is_by_game_and_dedupe_counts(nb_data):
    games = make_games(nb_data, 20)
    games = games + [games[0], games[1]]                  # chèn 2 ván trùng
    splits, kept, stats = nb_data["build_dataset"](games, {"train": 0.8, "val": 0.1, "test": 0.1}, seed=0)
    assert stats["games_before_dedupe"] == 22 and stats["games_after_dedupe"] == 20 and stats["duplicates_removed"] == 2
    ids = {s: set(np.unique(d["game_id"]).tolist()) for s, d in splits.items()}
    assert not (ids["train"] & ids["val"]) and not (ids["train"] & ids["test"]) and not (ids["val"] & ids["test"])
    assert sum(len(v) for v in ids.values()) == 20
    assert stats["games_per_split"] == {"train": 16, "val": 2, "test": 2}


def test_split_game_ids_rejects_bad_ratio_and_tiny_sets(nb_data):
    with pytest.raises(ValueError):
        nb_data["split_game_ids"](10, {"train": 0.5, "val": 0.1, "test": 0.1}, 0)
    with pytest.raises(ValueError):
        nb_data["split_game_ids"](2, {"train": 0.8, "val": 0.1, "test": 0.1}, 0)


# ---------- notebook 05: mã hóa và đối xứng ----------
def test_to_planes_matches_encode_planes(nb_sup):
    pos = random_positions(30)
    boards = np.stack([b for b, _ in pos])
    players = np.array([p for _, p in pos], dtype=np.int8)
    assert np.array_equal(nb_sup["to_planes"](boards, players), np.stack([encode_planes(b, p) for b, p in pos]))


def test_symmetry_keeps_legal_moves_and_labels_consistent(nb_sup):
    """Luật Othello bất biến với 8 phép đối xứng: nước hợp lệ của bàn đã xoay/lật = nước hợp lệ cũ đã xoay/lật."""
    for board, player in random_positions(20, seed=1):
        legal_old = legal_mask_from_actions(legal_moves(board, player))
        a_old = int(np.flatnonzero(legal_old)[0])
        for k in range(8):
            perm = nb_sup["SYM_PERMS_NP"][k]
            board_new = board.ravel()[perm].reshape(8, 8)
            legal_new = legal_mask_from_actions(legal_moves(board_new, player))
            planes = torch.from_numpy(encode_planes(board, player)).unsqueeze(0)
            p2, l2, a2 = nb_sup["apply_symmetry"](planes, torch.from_numpy(legal_old).unsqueeze(0),
                                                  torch.tensor([a_old]), torch.tensor([k]))
            assert np.array_equal(l2[0].numpy(), legal_new)
            assert np.array_equal(p2[0].numpy(), encode_planes(board_new, player))
            assert legal_new[int(a2[0])]          # nhãn sau biến đổi vẫn là nước hợp lệ


# ---------- notebook 06: RL ----------
def test_self_play_returns_match_rewards(nb_rl):
    torch.manual_seed(0)
    net = PolicyValueNet(channels=8, hidden=16)
    batch, stats = nb_rl["self_play_batch"](net, 3, 4, 1.0, random.Random(0), torch.Generator().manual_seed(0),
                                            "cpu", REWARD, 1.0)
    assert set(batch["ret"].tolist()) <= {-1.0, 0.0, 1.0}
    assert batch["legal"][torch.arange(len(batch["action"])), batch["action"]].all()   # chỉ lấy mẫu nước hợp lệ
    assert 0 <= stats["black_win_rate"] <= 1


def test_policy_gradient_update_moves_weights(nb_rl):
    torch.manual_seed(0)
    net = PolicyValueNet(channels=8, hidden=16)
    batch, _ = nb_rl["self_play_batch"](net, 4, 4, 1.0, random.Random(1), torch.Generator().manual_seed(1),
                                        "cpu", REWARD, 1.0)
    before = [p.detach().clone() for p in net.parameters()]
    opt = torch.optim.Adam(net.parameters(), lr=0.01)
    st = nb_rl["policy_gradient_update"](net, opt, batch, entropy_coef=0.01)
    assert any(not torch.equal(b, p) for b, p in zip(before, net.parameters()))
    assert np.isfinite(list(st.values())).all() and st["entropy"] > 0


# ---------- chạy cả notebook ở chế độ QUICK_TEST ----------
def test_notebook_04_runs_end_to_end():
    ns = run_notebook("04_generate_data.ipynb", quick=True)
    assert (ns["OUT_DIR"] / "train.npz").exists() and (ns["OUT_DIR"] / "meta.json").exists()
    assert ns["stats"]["games_after_dedupe"] <= ns["stats"]["games_before_dedupe"] == 40


@pytest.fixture()
def sample_data_dir(nb_data, tmp_path):
    """Bộ dữ liệu mẫu nhỏ (20 ván) cùng định dạng notebook 04 ghi ra, để notebook 05 không phụ thuộc `data/sample/`
    (thư mục đó bị .gitignore nên clone sạch sẽ không có)."""
    games = make_games(nb_data, 20)
    splits, kept, stats = nb_data["build_dataset"](games, {"train": 0.8, "val": 0.1, "test": 0.1}, seed=0)
    out = tmp_path / "sample"
    out.mkdir()
    for name, arrays in splits.items():
        np.savez_compressed(out / f"{name}.npz", **arrays)
    meta = {"label_source": {"expert_agent": EXPERT, "is_temporary_expert": False, "note": "dữ liệu mẫu cho test"},
            "games_per_split": stats["games_per_split"], "samples_per_split": stats["samples_per_split"]}
    (out / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return out


def test_notebook_05_runs_end_to_end(sample_data_dir):
    # QUICK_TEST của notebook 05 trỏ vào REPO/"data"/"sample"; đổi sang dữ liệu mẫu tạm do test tự sinh.
    ns = run_notebook("05_train_supervised.ipynb", quick=True,
                      replace={'REPO / "data" / "sample"': f"Path({str(sample_data_dir)!r})"})
    assert len(ns["history"]) == 2 and ns["CKPT_PATH"].exists()
    assert (ns["LOG_DIR"] / "epochs.csv").exists() and (ns["LOG_DIR"] / "test_metrics.json").exists()
    _, meta = load_checkpoint(ns["CKPT_PATH"])
    assert meta["kind"] == "supervised" and meta["label_source"]["expert_agent"]


def test_notebook_06_runs_end_to_end():
    ns = run_notebook("06_train_rl.ipynb", quick=True)
    assert (ns["CKPT_PATH"]).exists() and (ns["CKPT_PATH"].parent / "rl_periodic" / "rl_ep000016.pt").exists()
    assert sorted({r["episodes"] for r in ns["curve_rows"]}) == [0, 16, 32]   # có điểm xuất phát (episode 0)
    _, meta = load_checkpoint(ns["CKPT_PATH"])
    assert meta["kind"] == "rl_selfplay" and meta["init_from"] == "from_scratch"