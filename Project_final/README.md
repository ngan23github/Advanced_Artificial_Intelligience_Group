# Game AI đa cấp độ: Othello / Reversi 8x8

Đề tài cuối kỳ môn Trí tuệ nhân tạo nâng cao.
Nhóm: 10 (3 thành viên, xem `CONTRIBUTIONS.md`).

> Trước khi code, đọc `API.md` (quy ước board, action, chữ ký hàm của game và agent).

## 1. Giới thiệu ngắn

Nhóm tự xây engine Othello 8x8 chuẩn, rồi cài nhiều tác tử AI từ đơn giản đến phức tạp, cho đấu với nhau và phân tích kết quả để trả lời câu hỏi nghiên cứu.

**Câu hỏi nghiên cứu**:
1. MCTS có thắng Alpha-Beta khi hai bên có cùng thời gian suy nghĩ mỗi nước không? Kết quả có đổi khi đổi ngân sách thời gian hay không?
2. Hàm đánh giá có góc và mobility có mạnh hơn hàm chỉ đếm quân không, và mạnh hơn bao nhiêu?
3. Self-play RL có cải thiện tác tử học được so với mô hình bắt chước Alpha-Beta (supervised) không?

## 2. Luật chơi áp dụng

Luật dưới đây là phiên bản nhóm đang dùng, cần xác nhận với giảng viên (đặc biệt phần pass và kết thúc ván).

- Bàn 8x8. Vị trí đầu: 4 quân ở giữa xếp chéo, Đen đi trước.
- Nước hợp lệ: đặt quân vào ô trống sao cho kẹp được ít nhất một chuỗi quân đối thủ theo 1 trong 8 hướng; các quân bị kẹp bị lật.
- Nếu người đến lượt không có nước hợp lệ thì bị bỏ lượt (pass). **Engine tự xử lý pass**, agent không bao giờ thấy action pass.
- Ván kết thúc khi cả hai bên đều không còn nước đi. Nhiều quân hơn thắng, bằng nhau hòa.
- Reward theo góc nhìn từng người chơi: +1 thắng, 0 hòa, -1 thua.
- Quy ước kỹ thuật: Đen = 1, Trắng = -1, ô trống = 0; action là `(row, col)` với chỉ số 0..7.

Xem chi tiết ở `rules_othello.md`

## 3. Các tác tử

| Cấp | Tác tử | File | Trạng thái |
|---|---|---|---|
| 1 | Random | `agents/random_agent.py` | xong (có test) |
| 2 | Heuristic | `agents/heuristic_agent.py` | chưa làm |
| 3 | Minimax / Alpha-Beta | `agents/alphabeta_agent.py` | chưa làm |
| 4 | MCTS (UCT) | `agents/mcts_agent.py` | chưa làm |
| 5 | Neural Network (supervised) | `agents/nn_agent.py` | code + test xong; chưa train bản chính thức |
| 6 | Reinforcement Learning | `agents/rl_agent.py` | code + test xong; chưa train bản chính thức |

Các thành phần khác:

| Thành phần | File | Trạng thái |
|---|---|---|
| Engine (luật, pass, kết thúc, clone) | `othello/` | xong (có test và perft) |
| Giải đấu round-robin, độ đo (`tournament.py`, `metrics.py`) | `eval/` | xong (có test) |
| Ablation, profile chi phí | `eval/ablations.py`, `profile_cost.py` | chưa làm |
| Giao diện demo | `ui/` (`python -m ui.app`) | chạy được: người-máy, máy-máy |

(Cập nhật cột trạng thái khi làm xong.)

## 4. Cấu trúc thư mục

```
configs/      cấu hình thí nghiệm (YAML)
othello/      engine game (encoding.py, rules.py, game.py)
agents/       các tác tử (base.py là giao diện chung)
models/       kiến trúc mạng nơ-ron
eval/         giải đấu, ablation, độ đo
ui/           giao diện demo
tests/        test tự động (pytest)
scripts/      chạy thử và chạy lại thí nghiệm bằng 1 lệnh
notebooks/    sinh dữ liệu + huấn luyện (04-06) và tạo bảng/hình từ log thô
checkpoints/  trọng số mô hình
data/         dữ liệu huấn luyện
results/      log thô và hình
docs/         báo cáo, slide, poster
```
Xem chi tiết ở `Structure.txt`

## 5. Cài đặt

Yêu cầu: Python 3.10 trở lên.

```bash
python -m venv .venv
source .venv/Scripts/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 6. Cách chạy

### Chạy được ngay bây giờ

```bash
python -m pytest                       # test nhanh, gồm perft độ sâu 1-6 (vài giây)
python -m pytest -m slow               # perft độ sâu 7 (khoảng 13 giây)
python scripts/play_game.py            # Chơi game trên giao diện

# giải đấu
python -m eval.tournament --config configs/tournament.yaml --games 20 --run-name smoke
# kết quả: results/logs/smoke/ (games.jsonl, summary.json, matrix_<mode>.csv, meta.json...)
```

### Học máy (cấp 5-6): sinh dữ liệu và huấn luyện (bằng notebook)

Toàn bộ quy trình nằm trong 3 notebook (có chú thích từng bước, hình tự cập nhật khi train). Chạy lần lượt:

| Notebook | Việc | Đầu ra |
|---|---|---|
| `notebooks/04_generate_data.ipynb` | expert chơi và gắn nhãn, dedupe, chia train/val/test theo ván | `data/supervised_v1/` |
| `notebooks/05_train_supervised.ipynb` | train NN bắt chước expert (cấp 5), test đúng 1 lần | `checkpoints/nn_supervised.pt`, `results/logs/train_supervised/<run>/` |
| `notebooks/06_train_rl.ipynb` | RL self-play (cấp 6), learning curve | `checkpoints/rl_selfplay.pt`, `results/logs/train_rl/<run>/` |
| `notebooks/03_learning_curves.ipynb` | vẽ hình từ log thô của 05 và 06 | `results/figures/` |

- Mỗi notebook có biến `QUICK_TEST` (ô đầu): đặt `True` để chạy thử cả notebook trong vài giây, ghi ra thư mục tạm.
- Chạy không cần mở Jupyter: `bash scripts/run_training.sh` (lưu bản đã chạy vào `results/executed_notebooks/`).
- Mỗi lần chạy chính thức đổi `RUN_NAME` trong notebook 05/06 (không ghi đè log thô).
- Nhãn dữ liệu do expert gắn (`data.expert_agent` trong `configs/train_supervised.yaml`). 
- Dữ liệu mẫu nhỏ (100 ván) ở `data/sample/`; notebook 05 ở chế độ `QUICK_TEST` dùng nó.
- Test: `python -m pytest tests/test_nn_pipeline.py` (gồm chạy thử cả 3 notebook ở chế độ QUICK_TEST).

### Giao diện (Pygame)

```bash
python -m ui.app                 # menu: chọn Human vs Agent / Agent vs Agent, chọn agent bằng nút < >, thời gian mỗi nước
python scripts/play_game.py --cli --black random --white temp_positional --games 100   # không giao diện
```

- Danh sách agent trong menu lấy thẳng từ `configs/agents.yaml` (mỗi mục là một agent, kể cả biến thể ablation và tham số
  như `checkpoint`). Agent chưa code hoặc thiếu checkpoint hiện lý do màu đỏ và khóa nút Start (không crash).
- Tạo agent ở mọi nơi (giải đấu, UI, scripts, notebook) đều qua `agents/registry.py` (`build_agent_by_name`, `list_presets`).
- Cấu trúc `ui/`: `app.py` (vòng lặp), `menu.py`, `match.py` (logic ván + thread AI), `game_view.py` (vẽ bàn cờ/bảng điểm),
  `widgets.py`, `draw_utils.py`, `config.py` (kích thước, màu).

<!-- ### Kế hoạch (chưa chạy được, sẽ chỉnh lại cho khớp khi code xong)

```bash
# ablation
python -m eval.ablations --config configs/tournament.yaml

# demo chơi người-máy / máy-máy
python -m ui.app
``` -->

## 7. Tái lập thí nghiệm

- Mọi tham số nằm trong `configs/`, seed ghi rõ trong config.
- Log thô từng ván lưu ở `results/logs/`, không sửa tay.
- Hình và bảng trong báo cáo được sinh từ `notebooks/` đọc log thô.
- Ghi lại cấu hình máy (CPU/GPU/RAM) và thời gian train ở báo cáo, chương 4.

## 8. Nguồn tham khảo

Xem `CREDITS.md` (phần tự cài đặt, phần kế thừa).