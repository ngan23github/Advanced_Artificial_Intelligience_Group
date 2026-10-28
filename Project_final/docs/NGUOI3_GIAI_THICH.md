# Phần Người 3 + UI + registry: giải thích code

Gồm 4 mảng: (A) agent học được và mạng, (B) notebook huấn luyện, (C) registry hợp nhất, (D) UI tách module.
Cấp 7 (PUCT/AlphaZero-inspired) **chưa làm** (điểm cộng, chỉ làm khi cấp 1-6 xong).

## A. Mạng và agent học được

**`models/nets.py`**
- `PolicyValueNet`: 3 lớp conv 3x3 (64 kênh) rồi 2 đầu. **Policy** ra 64 logit (mỗi ô một logit), **value** ra 1 số trong (-1, 1) (tanh)
  = dự đoán kết quả ván theo góc nhìn người đang đi. Khoảng 158k tham số, chạy được trên CPU.
- `masked_logits`: đặt logit ô bất hợp lệ về -1e9 trước softmax/argmax (cả lúc train lẫn lúc chơi) nên agent không bao giờ đi sai.
- `save_checkpoint/load_checkpoint`: lưu trọng số + cấu hình mạng + `meta` (seed, nguồn nhãn, config); chỉ dùng kiểu dữ liệu thuần để `torch.load(weights_only=True)` an toàn.
- Lỗi đã gặp: bản đầu đầu value chỉ 1 kênh + ReLU bị "chết" (đầu ra hằng số). Đổi thành 8 kênh thì học được.

**`agents/nn_agent.py` (NNAgent, cấp 5)**: mã hóa bàn cờ → 1 lần forward → che nước sai → `argmax` (mặc định) hoặc lấy mẫu theo `temperature`
bằng RNG riêng theo `seed`. `stats()` = `{"forward_passes": 1, "value_estimate": v}`. Cache mô hình theo (đường dẫn, mtime) vì giải đấu tạo agent mới mỗi ván.
Thiếu checkpoint thì báo lỗi chỉ tới notebook cần chạy.

**`agents/rl_agent.py` (RLAgent, cấp 6)**: kế thừa NNAgent. Khác biệt giữa cấp 5 và 6 nằm ở **cách huấn luyện**, không ở lúc chơi.

**`agents/temp_positional_agent.py` (expert tạm)**: greedy theo bảng điểm vị trí cổ điển (góc +100, ô X -50...). Dùng làm "thầy" gắn nhãn cho NN
và làm đối thủ cố định khi train RL, vì Heuristic/Alpha-Beta của Người 2 còn là stub. **Không phải Heuristic chính thức**; không đưa vào giải đấu chính thức.
Khi Alpha-Beta xong: đổi `data.expert_agent: alphabeta` trong `configs/train_supervised.yaml` rồi chạy lại notebook 04, 05, 06.

## B. Notebook huấn luyện (thay cho thư mục `train/`, đã xóa)

Mỗi notebook tự chứa toàn bộ logic, chú thích từng bước, hình tự cập nhật khi train. Ô đầu có `QUICK_TEST` (True = chạy thử vài giây, ghi ra thư mục tạm).
Ô gắn tag `setup`/`defs` chỉ chứa import và hàm, để test đơn vị được (xem `tests/notebook_utils.py`).

| Notebook | Làm gì | Điểm cần hiểu |
|---|---|---|
| `04_generate_data` | Expert chơi, ở **mọi** thế cờ ghi nhãn = nước expert chọn; nhãn value = kết quả ván theo góc nhìn người đi | Nước *thực sự đi* có khai cuộc ngẫu nhiên + xác suất ngẫu nhiên để ván không trùng, nhưng nhãn luôn là nước expert. Dedupe theo chuỗi nước. Chia 80/10/10 **theo ván** để không rò rỉ. Lưu `data/supervised_v1/` |
| `05_train_supervised` | Loss = CE(policy, đã che nước sai) + MSE(value); Adam; tăng cường 8 phép đối xứng (chỉ train) | Chọn checkpoint theo **val**; **test đúng 1 lần** cuối; accuracy = trùng nước expert (đo nguy cơ "học lại heuristic"); có mức tham chiếu đoán ngẫu nhiên |
| `06_train_rl` | REINFORCE có baseline, self-play lấy mẫu từ policy, reward ±1 cuối ván | `A = G - V(s)` (V là baseline, không nhận gradient policy); entropy bonus để khám phá; đánh giá định kỳ vs đối thủ cố định trên seed riêng (900) → learning curve; có điểm ở episode 0; đối thủ chưa dùng được bị bỏ qua có thông báo và ghi vào meta |
| `03_learning_curves` | Đọc log của 05 và 06, vẽ hình có CI Wilson | Phần kết luận câu hỏi 3 để trống, chỉ điền sau khi có số liệu chính thức |

Log ghi ra cùng định dạng cũ (`epochs.csv`, `test_metrics.json`, `train_log.csv`, `learning_curve.csv`, `meta.json`) nên notebook 03 đọc được.
Mỗi lần chạy chính thức đổi `RUN_NAME` (không ghi đè log). Chạy không cần Jupyter: `bash scripts/run_training.sh` (lưu bản đã chạy ở `results/executed_notebooks/`).
Notebook sinh dữ liệu chạy một tiến trình (bản cũ dùng nhiều tiến trình sẽ lỗi trên Windows vì hàm định nghĩa trong notebook không "pickle" được).

## C. Gộp `ui/agent_factory.py` vào `agents/registry.py`

Vấn đề: `agent_factory` tạo agent chỉ với tham số mặc định và danh sách cứng 6 loại, nên NN/RL (cần `checkpoint`) không chạy được; chức năng lại trùng với registry.

Giải pháp: **một nguồn duy nhất** `agents/registry.py`, mọi nơi (giải đấu, UI, `scripts/play_game.py`, notebook) dùng chung:
- `build_agent(spec, seed, name)`: như cũ (giải đấu dùng).
- `build_agent_by_name(name, seed)`: tạo theo **tên mục trong `configs/agents.yaml`**, nên tham số (checkpoint, depth, simulations...) đi theo YAML, kể cả biến thể ablation.
- `check_spec(spec)`: biết agent dùng được không **mà không tạo agent**: phát hiện stub ("not implemented yet") và thiếu checkpoint ("missing checkpoint: ...").
- `list_presets()`: danh sách mục kèm nhãn, tóm tắt tham số, trạng thái. UI dùng để dựng menu.
- Đường dẫn `checkpoint` tương đối được hiểu từ thư mục gốc repo (chạy từ đâu cũng được).
- Thêm agent mới: 1 dòng trong `AGENT_CLASSES` + 1 mục trong `agents.yaml`; UI tự có, không sửa UI.
- Đã thêm type `temp_positional` (expert tạm) và mục tương ứng trong `agents.yaml`.

## D. UI tách module (`ui/`)

`app.py` cũ ~495 dòng chứa tất cả. Giờ (tổng ~600 dòng nhưng mỗi file một việc):

| File | Việc |
|---|---|
| `app.py` (~100 dòng) | vòng lặp chính, chuyển menu/ván, xử lý phím/chuột |
| `config.py` | kích thước, màu, `MODES`, `TIMES` |
| `draw_utils.py` | `Fonts`, `disc` |
| `widgets.py` | `Button`, `Selector` (hộp chọn có mũi tên `<` `>`) |
| `menu.py` | màn hình menu; agent lấy từ registry |
| `match.py` | **logic** một ván + thread AI + undo; không import pygame nên test được |
| `game_view.py` | vẽ bàn cờ, thẻ điểm, trạng thái, nút |

Thay đổi hành vi (có chủ đích):
- Chọn agent bằng `Selector` thay lưới nút: lưới sẽ tràn màn hình khi `agents.yaml` có nhiều mục (ablation). Agent không dùng được hiện lý do màu đỏ và khóa Start.
- Thêm hàng nút "Time per move" (code cũ có `TIMES` nhưng menu không hiển thị).
- Thẻ điểm hiện `value` (đánh giá của NN/RL) cạnh số nút/số mô phỏng của Alpha-Beta/MCTS.
- Thêm `if __name__ == "__main__"` nên `python -m ui.app` thực sự chạy (bản cũ không có).
- Tạo agent lỗi (thiếu checkpoint...) thì báo trên menu, không văng lỗi.
- Rút gọn dòng gợi ý phím ở panel (bản cũ bị cắt chữ).

## Đã kiểm tra
- `pytest`: 57 test xanh (gồm test cũ của Người 1, test hàm trong notebook, chạy thử cả 3 notebook ở QUICK_TEST, test registry/Match/Menu/App với Pygame không màn hình).
- Chụp màn hình UI headless: menu, agent không dùng được, ván NN vs RL, người vs expert tạm.
- **Số liệu của các lần chạy thử là để kiểm tra pipeline, không phải kết quả đưa vào báo cáo.**

## Việc còn lại
1. Khi Người 2 xong Alpha-Beta/Heuristic: đổi `expert_agent`, chạy lại 04 → 05 → 06 (đổi `RUN_NAME`), train bản chính thức trước mốc đóng băng.
2. Nhờ Người 1 chỉnh `.gitignore` cho phép nộp checkpoint nhỏ (`checkpoints/final/`); mình đã cho phép `data/sample/`.
3. Chạy notebook 03 trên log chính thức, tự viết kết luận câu hỏi 3 (nêu hạn chế: mạng nhỏ, 1 seed, số ván train, reward thưa).
4. Viết phần báo cáo/slide của Người 3; cấp 7 nếu còn thời gian.
5. `tournament.yaml` chưa liệt kê `nn`/`rl` (việc của Người 1): thêm vào `agents` khi có checkpoint chính thức.
6. Cập nhật `CREDITS.md`/`CONTRIBUTIONS.md` cho khớp thực tế (ghi rõ phần AI hỗ trợ và phần nhóm tự sửa).
