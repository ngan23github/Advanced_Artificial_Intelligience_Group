# API chung (cả nhóm phải giữ nguyên; ai muốn đổi phải báo cả nhóm)

## Quy ước
- Board: `numpy.ndarray` int8 (8, 8). `EMPTY=0`, `BLACK=1`, `WHITE=-1` (xem `othello/encoding.py`).
- Action: tuple `(row, col)`, 0..7. Không dùng `(x, y)`. Với NN: `action_to_index` / `index_to_action` (0..63).
- Đen đi trước. Pass do **engine tự xử lý**, agent không bao giờ nhận hay trả về action pass.
- Ván kết thúc khi cả hai bên đều không có nước đi. Thắng/thua theo số quân.
- `result(player)`: +1 thắng, 0 hòa, -1 thua, theo góc nhìn `player` (mặc định BLACK). Chỉ gọi khi `is_terminal()`.

## OthelloGame (`othello/game.py`)
| Hàm | Mô tả |
|---|---|
| `reset()` | Về vị trí đầu, trả về chính game |
| `legal_actions()` | list `(row, col)` của người đang đến lượt; `[]` nếu hết ván |
| `step(action)` | Đi 1 nước, **sửa game tại chỗ**, trả về chính game. Nước sai -> `IllegalMoveError`, trạng thái không đổi |
| `is_terminal()` | bool |
| `result(player=BLACK)` | +1 / 0 / -1 |
| `render()` | str bàn cờ |
| `clone()` | bản sao độc lập (board, lượt, lịch sử). Tìm kiếm luôn dùng clone, không đụng game thật |
| `score()` | `(số quân đen, số quân trắng)` |
| thuộc tính | `board`, `current_player`, `move_history` |

Hàm thuần trong `othello/rules.py` (`legal_moves`, `flips_for_move`, `apply_move`) **không sửa** board đầu vào.

## Agent (`agents/base.py`)
```python
class Agent(ABC):
    name: str
    def reset(self) -> None: ...                      # đầu mỗi ván
    def select_action(self, game, time_budget=None):  # trả về action nằm trong game.legal_actions()
    def stats(self) -> dict: ...                      # {"nodes": ..., "simulations": ...} của nước vừa đi
```
- Agent nhận `game` đang ở lượt của nó, **không được sửa** `game` (dùng `game.clone()`).
- `time_budget`: giây/nước; `None` = cấu hình mặc định.
- Agent có ngẫu nhiên phải nhận `seed` trong `__init__` và dùng RNG riêng (xem `RandomAgent`).
- Thêm agent mới: thêm 1 dòng vào `AGENT_FACTORIES` trong `tests/test_agents.py` là được test tự động.

### Để agent chạy được trong giải đấu (`agents/registry.py`, `configs/agents.yaml`)
Tên lớp phải đúng như bảng sau (registry import theo tên này):

| type trong YAML | Lớp |
|---|---|
| `random` | `agents.random_agent.RandomAgent` |
| `heuristic` | `agents.heuristic_agent.HeuristicAgent` |
| `alphabeta` | `agents.alphabeta_agent.AlphaBetaAgent` |
| `mcts` | `agents.mcts_agent.MCTSAgent` |
| `nn` | `agents.nn_agent.NNAgent` |
| `rl` | `agents.rl_agent.RLAgent` |

- Mọi tham số chỉnh được (độ sâu, số mô phỏng, đường dẫn checkpoint...) phải là tham số của `__init__` để khai báo trong YAML (`params:`).
- Nếu `__init__` có tham số tên `seed`, giải đấu tự truyền seed theo từng ván. Agent phải dùng RNG riêng (như `RandomAgent`).
- `time_budget` (giây/nước) do giải đấu truyền vào `select_action`. Agent tìm kiếm theo thời gian (MCTS, Alpha-Beta lặp sâu) phải tôn trọng nó; `None` = dùng cấu hình mặc định của agent.
- `stats()` trả về dict của NƯỚC VỪA ĐI. Giải đấu ghi lại và tính trung bình hai khóa chuẩn: `"nodes"` (số nút duyệt) và `"simulations"` (số mô phỏng). Khóa khác vẫn được ghi vào log.
- Giải đấu đưa cho agent một bản `game.clone()`, nên agent có sửa nó cũng không ảnh hưởng ván thật. Trả về nước không hợp lệ thì giải đấu dừng với lỗi `IllegalAgentMove`.

## Giải đấu (`eval/tournament.py`)
`python -m eval.tournament --config configs/tournament.yaml`. Mỗi ván được ghi 1 dòng JSON trong `results/logs/<run_name>/games.jsonl` (kết quả theo góc nhìn Đen, `a_is_black`, khai cuộc, `move_log` gồm người đi, nước, thời gian ms, stats). Độ đo tính trong `eval/metrics.py`.
