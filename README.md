# Game AI đa cấp độ: Othello / Reversi 8x8

Đề tài cuối kỳ môn Trí tuệ nhân tạo nâng cao.
Nhóm: 10 (3 thành viên, xem `CONTRIBUTIONS.md`).

## 1. Giới thiệu ngắn

Nhóm tự xây engine Othello 8x8 chuẩn, rồi cài nhiều tác tử AI từ đơn giản đến phức tạp, cho đấu với nhau và phân tích kết quả để trả lời câu hỏi nghiên cứu.

**Câu hỏi nghiên cứu** (chốt lại với giảng viên rồi sửa ở đây):
1. TODO: ví dụ "MCTS có thắng Alpha-Beta khi cùng thời gian suy nghĩ mỗi nước không?"
2. TODO: ví dụ "Hàm đánh giá có mobility/góc có mạnh hơn hàm chỉ đếm quân không?"

## 2. Luật chơi áp dụng

- Bàn 8x8, vị trí đầu: 4 quân ở giữa, xếp chéo. Đen đi trước.
- Nước đi hợp lệ: đặt quân sao cho kẹp được ít nhất một chuỗi quân đối thủ theo 1 trong 8 hướng, các quân bị kẹp bị lật.
- Không có nước hợp lệ thì **phải pass**. Hai bên pass liên tiếp thì ván kết thúc.
- Kết thúc: bên có nhiều quân hơn thắng, bằng nhau là hòa.
- Reward theo góc nhìn người chơi: +1 thắng, 0 hòa, -1 thua.

## 3. Các tác tử

| Cấp | Tác tử | File | Trạng thái |
|---|---|---|---|
| 1 | Random | `agents/random_agent.py` | chưa làm |
| 2 | Heuristic | `agents/heuristic_agent.py` | chưa làm |
| 3 | Minimax / Alpha-Beta | `agents/alphabeta_agent.py` | chưa làm |
| 4 | MCTS (UCT) | `agents/mcts_agent.py` | chưa làm |
| 5 | Neural Network (supervised) | `agents/nn_agent.py` | chưa làm |
| 6 | Reinforcement Learning | `agents/rl_agent.py` | chưa làm |
| 7-8 | AlphaGo/AlphaZero-inspired (nếu kịp) | `agents/az_inspired/` | chưa làm |

(Cập nhật cột trạng thái khi làm xong.)

## 4. Cấu trúc thư mục

```
configs/      cấu hình thí nghiệm (YAML)
othello/      engine game
agents/       các tác tử
models/       kiến trúc mạng nơ-ron
train/        sinh dữ liệu và huấn luyện
eval/         giải đấu, ablation, độ đo
ui/           giao diện demo
tests/        test tự động (pytest)
scripts/      chạy lại thí nghiệm bằng 1 lệnh
notebooks/    tạo bảng/hình từ log thô
checkpoints/  trọng số mô hình
data/         dữ liệu huấn luyện
results/      log thô và hình
docs/         báo cáo, slide, poster
```

## 5. Cài đặt

Yêu cầu: Python 3.10 trở lên.

```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 6. Cách chạy

Các lệnh dưới đây là kế hoạch, sẽ chỉnh lại cho khớp khi code xong.

```
# chạy test (kể cả perft kiểm tra engine)
pytest tests/

# sinh dữ liệu và train agent học được
python -m train.generate_data --config configs/train_supervised.yaml
python -m train.train_supervised --config configs/train_supervised.yaml
python -m train.train_rl --config configs/train_rl.yaml

# giải đấu round-robin và ablation
python -m eval.tournament --config configs/tournament.yaml
python -m eval.ablations --config configs/tournament.yaml

# demo chơi người-máy / máy-máy
python -m ui.app
```

## 7. Tái lập thí nghiệm

- Mọi tham số nằm trong `configs/`, seed ghi rõ trong config.
- Log thô từng ván lưu ở `results/logs/`, không sửa tay.
- Hình và bảng trong báo cáo được sinh từ `notebooks/` đọc log thô.
- Ghi lại cấu hình máy (CPU/GPU/RAM) và thời gian train ở báo cáo, chương 4.

## 8. Nguồn tham khảo

Xem `CREDITS.md` (phần tự cài đặt, phần kế thừa, công cụ AI đã dùng).
