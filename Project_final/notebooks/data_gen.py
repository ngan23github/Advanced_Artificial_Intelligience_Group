"""Sinh ván cờ từ expert (Alpha-Beta/Heuristic) để làm dữ liệu cho NN supervised, CHẠY SONG SONG nhiều tiến trình.

Vì sao tách ra file .py thay vì để trong notebook: trên Windows, multiprocessing dùng "spawn" nên tiến trình con
phải `import` được hàm cần chạy; hàm định nghĩa trong ô notebook thì không import được.

Tái lập: ván thứ i luôn dùng seed = base_seed + i, KHÔNG phụ thuộc số tiến trình => cùng dữ liệu dù chạy 1 hay 12 worker.
"""

import os
import random
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from agents.registry import build_agent, load_agent_specs
from othello.encoding import BLACK, BOARD_SIZE, action_to_index
from othello.game import OthelloGame



def legal_mask_from_actions(actions) -> np.ndarray:
    """list[(row, col)] -> mảng bool (64,). Giống models.nets.legal_mask_from_actions nhưng KHÔNG import torch
    (để mỗi worker khởi động nhanh và nhẹ RAM; agent alphabeta/heuristic không cần torch)."""
    mask = np.zeros(BOARD_SIZE * BOARD_SIZE, dtype=bool)
    for a in actions:
        mask[action_to_index(a)] = True
    return mask


_SPECS = None  # đọc agents.yaml một lần cho mỗi tiến trình (trước đây đọc lại YAML ở MỖI ván)


def _spec(expert_name):
    global _SPECS
    if _SPECS is None:
        _SPECS = load_agent_specs()
    return _SPECS[expert_name]


def generate_one_game(game_seed, expert_name, opening_plies, random_move_prob):
    """Sinh 1 ván. Cùng game_seed => cùng ván. Trả về dict gồm các mảng mẫu và chuỗi nước đã đi."""
    rng = random.Random(game_seed)                       # RNG riêng cho việc chọn nước ngẫu nhiên
    expert = build_agent(_spec(expert_name), seed=game_seed, name=expert_name)
    expert.reset()

    game = OthelloGame()
    boards, players, actions, legals, plies, played = [], [], [], [], [], []
    while not game.is_terminal():
        legal = game.legal_actions()
        best = expert.select_action(game.clone(), None)  # expert nhận BẢN SAO của game (không được sửa game thật)
        boards.append(game.board.copy())                 # bàn cờ tuyệt đối (Đen=1, Trắng=-1)
        players.append(game.current_player)              # ai đang đi ở thế cờ này
        actions.append(action_to_index(best))            # NHÃN policy: chỉ số 0..63 của nước expert chọn
        legals.append(legal_mask_from_actions(legal))    # mặt nạ 64 ô hợp lệ (để che nước sai khi train)
        plies.append(len(played))

        explore = len(played) < opening_plies or rng.random() < random_move_prob
        move = rng.choice(legal) if explore else tuple(best)   # nước THỰC SỰ đi
        game.step(move)
        played.append(move)

    result_black = game.result(BLACK)
    return {
        "moves": [list(m) for m in played],
        "result_black": result_black,
        "board": np.stack(boards).astype(np.int8),
        "player": np.array(players, dtype=np.int8),
        "action": np.array(actions, dtype=np.int16),
        "legal": np.stack(legals),
        "ply": np.array(plies, dtype=np.int16),
        "value": (result_black * np.array(players)).astype(np.float32),   # NHÃN value theo góc nhìn người đi
    }


def _job(args):
    return generate_one_game(*args)


def default_workers() -> int:
    """Chừa 1 lõi cho máy/Jupyter. Đặt biến môi trường GEN_WORKERS để ép số worker."""
    env = os.environ.get("GEN_WORKERS")
    if env:
        return max(1, int(env))
    return max(1, (os.cpu_count() or 2) - 1)


def generate_games(num_games, base_seed, expert_name, opening_plies, random_move_prob, workers=None, progress=None):
    """Sinh `num_games` ván (ván i dùng seed base_seed + i). Trả về list theo đúng thứ tự i.

    workers : số tiến trình (None = cpu_count - 1; 1 = chạy trong tiến trình hiện tại, không dùng multiprocessing).
    progress: hàm bọc iterable để hiện thanh tiến độ, ví dụ `lambda it, total: tqdm(it, total=total)`.
    """
    workers = default_workers() if workers is None else max(1, int(workers))
    jobs = [(base_seed + i, expert_name, opening_plies, random_move_prob) for i in range(num_games)]
    wrap = progress or (lambda it, total: it)
    if workers == 1 or num_games <= 1:
        return list(wrap(map(_job, jobs), num_games))
    # chunksize nhỏ để các worker nhận việc đều (ván cuối-ván nhanh hơn ván giữa-ván nhiều)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(wrap(ex.map(_job, jobs, chunksize=4), num_games))
