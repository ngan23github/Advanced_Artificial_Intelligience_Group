# Phân công công việc: Othello Game AI (nhóm 3 người)

Tài liệu này dựa trên (1) đề cuối kỳ TTNTNC, (2) trạng thái code hiện tại, (3) rubric 100 điểm.
Mốc thời gian ghi theo "Tuần" tính từ ngày chốt phân công; nhóm map sang hạn nộp thật rồi sửa lại.

## 0. Trạng thái hiện tại

Đã xong: engine + test + perft, giải đấu round-robin + độ đo (Wilson/bootstrap), Random agent, config đã khớp code.

Còn stub (chưa có code): Heuristic, Alpha-Beta, MCTS, NN, RL, models/nets.py, train/*, UI, ablations, profile_cost, 3 notebook, báo cáo, slide, poster.

Phạm vi nhóm chọn: bắt buộc cấp 1-4 + cấp 5 và 6 (khuyến khích), cấp 7 là điểm cộng nếu kịp. Cấp 8 không làm trừ khi dư thời gian.

## 1. Chia vai

| | Vai trò | Phụ trách chính | Rubric |
|---|---|---|---|
| Người 1 | Nhóm trưởng: engine, đánh giá, UI, tích hợp | Engine, giải đấu, ablation, profile chi phí, UI, notebook 01/02, README/đóng gói | 1, 2, 5, 8 |
| Người 2 | Tác tử tìm kiếm | Heuristic, Alpha-Beta, MCTS, tune, phân tích ván | 3 |
| Người 3 | Tác tử học được | Dữ liệu, NN supervised, RL self-play, notebook 03, (cấp 7) | 4 |

Điểm 6 (kết quả, thảo luận) và 7 (báo cáo, slide, demo) là việc chung, xem mục 5.

## 2. Quy tắc chung (cả nhóm)

1. Giữ nguyên `API.md` (board, action `(row, col)`, tên lớp agent, `select_action(game, time_budget)`, `stats()`). Muốn đổi thì báo cả nhóm.
2. Mỗi người một branch, merge vào `main` bằng PR. Review chéo: 1 review 2, 2 review 3, 3 review 1.
3. Mỗi agent "xong" khi đủ 5 thứ: có code đúng tên lớp, có dòng trong `AGENT_FACTORIES` của `tests/test_agents.py`, có mục trong `configs/agents.yaml`, `pytest` xanh, cập nhật bảng trạng thái trong README và `CREDITS.md`.
4. Tách tập tune và tập đánh giá cuối (đề cấm dùng ván đánh giá cuối để chọn siêu tham số):
   - Tune: `configs/tournament_tune.yaml` (Người 1 tạo, copy từ tournament.yaml) với `seeds: [100, 101, 102]`, `games_per_pair: 40`, `run_name` bắt đầu bằng `tune_`.
   - Đánh giá cuối: seeds `[0, 1, 2]`, 200 ván/cặp, chỉ chạy sau mốc đóng băng.
5. Đóng băng (cuối Tuần 2): sau mốc này không sửa agent, config agent, hay luật. Chỉ sửa bug và phải ghi lại. Mỗi lần chạy chính thức dùng `run_name` mới, không xóa hay chỉnh tay log.
6. Không đưa vào báo cáo kết quả chưa chạy. Mọi hình/bảng phải sinh từ notebook đọc log thô.
7. Ghi `CREDITS.md`: phần tự cài đặt, phần tham khảo (sách Mark Liu, repo, công cụ AI) cho từng file mình làm.

## 3. Câu hỏi nghiên cứu

1. MCTS có thắng Alpha-Beta khi hai bên có cùng thời gian suy nghĩ mỗi nước không? Kết quả có đổi khi đổi ngân sách thời gian hay không?
2. Hàm đánh giá có góc và mobility có mạnh hơn hàm chỉ đếm quân không, và mạnh hơn bao nhiêu?
3. Self-play RL có cải thiện tác tử học được so với mô hình bắt chước Alpha-Beta (supervised) không?

Hai ablation bắt buộc sẽ lấy từ đây: Alpha-Beta bật/tắt cắt tỉa và số mô phỏng MCTS (thêm hàm đánh giá/heuristic bật-tắt làm ablation thứ ba, và policy-only vs policy+MCTS nếu làm cấp 7).

## 4. Việc chi tiết từng người

### Người 1: Engine, đánh giá, UI, tích hợp

**Tuần 1 (chặn người khác, làm trước)**
- [ ] Tăng tốc engine (hiện khoảng 4300 nước/giây): `OthelloGame._advance_turn` đang tính `legal_moves` của người kế tiếp rồi bỏ, nên `legal_actions()` tính lại. Lưu kết quả vào `_cache_legal`. Nếu vẫn chậm, cân nhắc bitboard cho `rules.py`. Xong khi: perft và test cũ vẫn xanh, đo lại nước/giây và ghi vào README.
- [ ] Hỗ trợ giới hạn thời gian: thêm helper `Deadline` trong `agents/base.py` (`Deadline(time_budget).expired()`) để Người 2 và 3 dùng chung. Trong `tournament.py` ghi thêm cờ `over_budget` (thời gian nước > ngân sách × 1,1) vào log và đếm trong `summary.json`.
- [ ] Tạo `configs/tournament_tune.yaml` (mục 2.4) và thêm cờ `--agents a,b,c` cho `eval/tournament.py` (config đã từng nhắc nhưng code chưa có).
- [ ] Chốt câu hỏi nghiên cứu cùng nhóm, hỏi giảng viên về luật pass/kết thúc, cập nhật README mục 1 và 2.
- [ ] Sửa `.gitignore` để checkpoint nhỏ (`.pt`) có thể nộp (hoặc có thư mục `checkpoints/final/` không bị bỏ qua).

**Tuần 1-2: UI (`ui/app.py`, Pygame)**
- [ ] Người vs Máy và Máy vs Máy, chọn cấp AI cho mỗi bên từ `agents.yaml` qua `build_agent`.
- [ ] Hiển thị bàn cờ, nước hợp lệ, điểm số, lượt đi, tự xử lý pass, nút ván mới; hiện thời gian nghĩ và số nút/mô phỏng của AI (gợi ý giải thích nước đi).
- [ ] AI chạy ở thread riêng để UI không đơ. Chạy `python -m ui.app` phải ổn định, không crash khi agent chưa có (hiện thông báo thay vì văng lỗi).

**Tuần 2: đánh giá nâng cao**
- [ ] `eval/ablations.py` + `scripts/run_ablations.sh`: chạy các cặp biến thể (alphabeta vs alphabeta_nopruning: phải cùng nước đi, khác số nút/thời gian; mcts_100/500/1000/5000; alphabeta_discs_only; heuristic_discs_only) và ghi log riêng. Đọc khóa `ablations` trong `tournament.yaml` hoặc đổi thành config riêng.
- [ ] `eval/profile_cost.py`: thời gian/nước, p95, số nút, số mô phỏng, RAM (tracemalloc hoặc psutil), VRAM nếu có GPU; ghi thành `results/logs/profile_*.json`.
- [ ] Sửa `bootstrap_score_ci` để lấy mẫu theo cặp ván (2 ván cùng khai cuộc), hiện đang coi mỗi ván độc lập nên CI hơi hẹp.
- [ ] Viết `tests/test_metrics.py` (Wilson tại biên 0/n, score có hòa, bootstrap tái lập theo seed, `aggregate_match` trên log giả).
- [ ] Phân tích lợi thế đi trước: tỷ lệ Đen thắng từ log (đã có `black_win_rate`), kiểm tra ảnh hưởng seed, depth, simulation budget (đề yêu cầu ở 3.5).

**Tuần 3: chạy chính thức và hình**
- [ ] Sau đóng băng: chạy giải đấu chính thức đủ 6 agent (hai chế độ ngân sách), `workers = số lõi - 1`, ghi cấu hình máy vào báo cáo. Kiểm tra `summary.json`: agent chạy quá giờ, ván lỗi, ma trận bất thường.
- [ ] Notebook `01_tournament_results.ipynb` (ma trận score/WDL, CI, p95, nút/mô phỏng, lợi thế đi trước) và `02_ablations.ipynb`. Hình lưu vào `results/figures/`.
- [ ] Chọn ván minh họa theo quy tắc đã định trước (ví dụ ván có số nước dài nhất, ván thua của agent mạnh nhất), không chọn riêng ván thắng.

**Tuần 4: đóng gói**
- [ ] Cập nhật README (bảng trạng thái, cách chạy thật, tái lập), `Structure.txt`, `requirements.txt` (pip freeze), `CONTRIBUTIONS.md` (tên, MSSV, tỷ lệ dựa trên commit), link GitHub.
- [ ] Ghép báo cáo/slide/poster, chạy thử demo, đặt tên zip `NhomXX_Othello_TTNTNC_HoTen_MaSV.zip`, kiểm tra clone sạch rồi `pip install -r requirements.txt && pytest && python -m eval.tournament ...` chạy được.

### Người 2: Tác tử tìm kiếm (cấp 2, 3, 4)

Giao theo thứ tự này vì Người 3 cần Alpha-Beta để sinh dữ liệu.

**Lưu ý chung khi viết tìm kiếm:** sau `game.step()` người đi tiếp có thể vẫn là cùng một người (do pass), nên đừng đảo dấu theo độ sâu. Hãy xác định max/min bằng `game.current_player == người của mình`. Luôn dùng `game.clone()`; `step` sửa tại chỗ. Test phải có vị trí có pass.

**Tuần 1**
- [ ] `HeuristicAgent` (cấp 2), tham số `priorities` theo `agents.yaml`: take_corner, avoid_x_square, avoid_c_square, maximize_mobility, maximize_discs. Ghi rõ thứ tự ưu tiên và các xung đột luật (ví dụ góc vs X-square) vào docstring để đưa vào báo cáo. Tie-break bằng RNG riêng theo seed.
- [ ] `AlphaBetaAgent` bản đầu (cấp 3): Minimax thuần + Alpha-Beta với cờ `pruning`, đếm `nodes` trong `stats()`, hàm đánh giá theo cờ `eval` (disc_diff, mobility, corners, x_c_squares, stability tùy chọn), `depth` cố định, `move_ordering`.
- [ ] Báo cho Người 3 ngay khi AlphaBeta chạy được (để họ sinh dữ liệu). Trước đó Người 3 dùng Heuristic làm expert tạm.

**Tuần 2**
- [ ] AlphaBeta: iterative deepening tôn trọng `time_budget` (dùng `Deadline` của Người 1), luôn trả nước hợp lệ tốt nhất đã tìm được khi hết giờ.
- [ ] Test: pruning bật/tắt cho cùng giá trị (và cùng nước nếu tie-break tất định), nodes pruning < nodes không pruning, thắng ngay khi có nước thắng, kết quả tái lập.
- [ ] `MCTSAgent` (cấp 4): UCT với 4 bước Selection-Expansion-Simulation-Backpropagation, `simulations`, `exploration_c`, rollout random, chọn nước theo số lượt thăm; hỗ trợ `time_budget` (dừng theo giờ thay vì số mô phỏng khi được truyền); ghi `simulations` vào `stats()`. Xử lý pass trong cây (lượt có thể không đổi) và backpropagation theo người chơi tại từng nút.
- [ ] Thêm cả 3 agent vào `AGENT_FACTORIES`, `agents.yaml` (kèm biến thể ablation: nopruning, mcts_100/5000, discs_only), cập nhật README.
- [ ] Tune trên tập tune (mục 2.4): độ sâu, `exploration_c`, trọng số hàm đánh giá. Ghi bảng tune để đưa vào phụ lục.

**Tuần 3-4**
- [ ] Phân tích kết quả của agent mình: tại sao MCTS thắng/thua Alpha-Beta theo từng chế độ ngân sách, ảnh hưởng độ sâu/số mô phỏng, ví dụ vài vị trí chiến thuật (góc, mobility), các lỗi điển hình (horizon effect, rollout random yếu).
- [ ] Viết các phần báo cáo của mình (mục 5) và slide phần tìm kiếm.

### Người 3: Tác tử học được (cấp 5, 6, và 7 nếu kịp)

**Tuần 1**
- [ ] `models/nets.py`: mạng nhỏ dùng chung (CNN vài lớp hoặc MLP), đầu vào `encode_planes` (2, 8, 8), đầu ra policy 64 logit + value (tanh). Dùng được trên CPU.
- [ ] `train/generate_data.py`: sinh ván từ expert trong `configs/train_supervised.yaml` (tạm Heuristic, sau đổi sang Alpha-Beta). Dùng `opening_plies` ngẫu nhiên, có thể thêm tỷ lệ nước ngẫu nhiên nhỏ để tăng đa dạng. Lưu theo ván, loại trùng, ghi số ván trước/sau dedupe. Nhãn: policy = nước expert; value = kết quả cuối theo góc nhìn bên đi. Chia train/val/test 80/10/10 THEO VÁN (trước khi augmentation, nếu dùng đối xứng chỉ augment tập train).
- [ ] Tạo dữ liệu mẫu nhỏ trong `data/` và ghi cách tái sinh trong README.

**Tuần 2**
- [ ] `train/train_supervised.py`: loss (cross-entropy policy + MSE value), lưu `checkpoints/nn_supervised.pt` kèm seed và config, log loss/accuracy theo epoch vào `results/logs/train_supervised/`, chọn checkpoint theo val, chỉ báo test một lần cuối. Ghi CPU/GPU và thời gian huấn luyện.
- [ ] `NNAgent` (cấp 5): load checkpoint, che nước bất hợp lệ trước softmax/argmax, tham số `checkpoint` đúng như `agents.yaml`, tái lập theo seed. Báo cáo nguy cơ "học lại heuristic" (mục 3.4 của đề), có thể so sánh tỷ lệ trùng nước với expert.
- [ ] `train/train_rl.py` + `RLAgent` (cấp 6): self-play, policy gradient (REINFORCE có baseline từ value head). Sửa `train_rl.yaml` cho nhất quán: exploration là `policy_sampling` kèm `entropy_coef` thay cho epsilon-greedy (nếu giữ epsilon thì phải đổi sang DQN). Reward ±1 ở cuối ván, `episodes` đủ lớn theo tài nguyên.
- [ ] Đường cong học tập: cứ `every_episodes` cho agent đang train đấu `random` và `heuristic` trên seed/khai cuộc riêng (không dùng seed đánh giá cuối); ghi CSV; lưu checkpoint định kỳ.
- [ ] Thêm cả hai agent vào `AGENT_FACTORIES` (dùng checkpoint nhỏ trong test hoặc bỏ qua nếu thiếu file) và `agents.yaml`.

**Tuần 3-4**
- [ ] Notebook `03_learning_curves.ipynb`: loss/accuracy NN, reward/winrate RL theo episode.
- [ ] Trả lời câu hỏi 3: RL self-play so với NN bắt chước, nêu nguyên nhân và hạn chế (ngân sách huấn luyện, mạng nhỏ).
- [ ] (Điểm cộng, chỉ khi cấp 1-6 đã xong) cấp 7: `agents/az_inspired/puct_mcts.py` dùng policy/value làm prior trong MCTS (PUCT), ghi rõ thành phần đã/chưa cài đặt (không gọi là tái hiện AlphaGo). Ablation policy-only vs policy+MCTS. Có thể tái dùng code cây của Người 2.
- [ ] Viết các phần báo cáo của mình (mục 5) và slide phần học máy.

## 5. Báo cáo, slide, poster

| Phần | Người viết chính | Ghi chú |
|---|---|---|
| Ch.1 Giới thiệu (game, luật, câu hỏi nghiên cứu, phạm vi) | Người 1 | |
| Ch.2 Minimax, Alpha-Beta, MCTS/UCT | Người 2 | |
| Ch.2 NN, RL/self-play, AlphaGo/AlphaZero-inspired | Người 3 | phân biệt rõ "inspired" |
| Ch.3 Engine, giải đấu, độ đo, thiết kế công bằng | Người 1 | |
| Ch.3 Thuật toán và tham số cấp 2-4 | Người 2 | |
| Ch.3 Dữ liệu, huấn luyện cấp 5-6 | Người 3 | |
| Ch.4 Môi trường, ma trận đối đầu, chi phí, ablation | Người 1 | |
| Ch.4 Phân tích agent tìm kiếm, ván điển hình, thất bại | Người 2 | |
| Ch.4 Learning curves, so sánh NN vs RL | Người 3 | |
| Ch.5 Kết luận, hạn chế, hướng phát triển | cả nhóm | Người 1 tổng hợp |
| Slide | mỗi người làm phần mình, Người 1 ghép | |
| Poster | Người 1 dàn trang, mỗi người đưa 1 hình | |

Mỗi người đọc lại toàn bộ báo cáo một lượt trước khi nộp (kiểm tra số liệu khớp với `summary.json`).

## 6. Lịch gợi ý

| Mốc | Người 1 | Người 2 | Người 3 |
|---|---|---|---|
| Tuần 1 | Tăng tốc engine, `Deadline`, tune config, `--agents`, bắt đầu UI | Heuristic, Alpha-Beta bản đầu | nets, generate_data (expert tạm) |
| Tuần 2 | UI xong, ablations, profile_cost, test_metrics | AB iterative deepening, MCTS, test, tune | train_supervised, NNAgent, train_rl, RLAgent |
| Cuối Tuần 2 | **Đóng băng agent và config** | | |
| Tuần 3 | Chạy giải đấu chính thức + ablation, notebook 01/02 | Phân tích tìm kiếm, viết báo cáo | Hoàn thiện RL, notebook 03, (cấp 7), viết báo cáo |
| Tuần 4 | Ghép báo cáo/slide/poster, README, đóng gói, tập demo | Slide, tập demo | Slide, tập demo |

## 7. Phụ thuộc và rủi ro

- Người 3 cần Alpha-Beta của Người 2 để sinh dữ liệu: có phương án tạm dùng Heuristic, nhưng cần đổi expert sau và ghi rõ nguồn nhãn.
- MCTS và Alpha-Beta cần engine nhanh hơn từ Người 1 (Tuần 1) kẻo giải đấu chạy hàng giờ. Nên chạy thử `--games 20` trước khi chạy 200 ván.
- Agent theo thời gian kém ổn định khi nhiều tiến trình cùng chạy: giữ `workers` ≤ số lõi vật lý - 1 và chạy chính thức trên cùng một máy.
- Cấp 7 chỉ làm khi cấp 1-6 đã chạy xong và log đầy đủ; điểm cộng không thay phần bắt buộc.
- Nếu huấn luyện RL quá chậm, giảm `episodes` và ghi trung thực số ván đã train thay vì ước lượng.

## 8. Đối chiếu rubric

| Tiêu chí | Điểm | Chủ trì | Cần có để đạt |
|---|---|---|---|
| 1. Bài toán/game | 10 | Người 1 | luật, state/action/reward, câu hỏi nghiên cứu, test engine (đã có phần lớn) |
| 2. Hệ thống | 15 | Người 1 | API thống nhất, engine đúng, UI người-máy và máy-máy |
| 3. Tác tử tìm kiếm | 20 | Người 2 | Random, Heuristic, Alpha-Beta, MCTS đúng, có giải thích và so sánh có/không cắt tỉa |
| 4. Tác tử học được | 15 | Người 3 | NN và RL thật sự huấn luyện, dữ liệu, loss/reward, checkpoint, learning curve |
| 5. Thiết kế đánh giá | 15 | Người 1 | cân bằng lượt, nhiều seed, 2 chế độ ngân sách, ≥ 2 ablation |
| 6. Kết quả, thảo luận | 10 | cả nhóm | ma trận đối đầu, chi phí, CI, nguyên nhân, hạn chế |
| 7. Báo cáo, slide, demo | 10 | cả nhóm | 5 chương, slide, poster, demo ổn định |
| 8. Tái lập và đạo đức | 5 | Người 1 | README chạy được, log thô, dẫn nguồn, tỷ lệ đóng góp |
