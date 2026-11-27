# Game AI đa cấp độ: Othello / Reversi 8x8

Đề tài cuối kỳ môn Trí tuệ nhân tạo nâng cao.

## Thành viên và phân công
 
Nhóm gồm 3 thành viên.
 
| Họ tên | MSSV | Phần việc chính | Tỷ lệ đóng góp |
|---|---|---|---|
| Lê Đoàn Kim Ngân | 3123410231 | Engine `othello/`, NN supervised và RL self-play (`agents/nn_agent.py`, `rl_agent.py`, `models/`), sinh dữ liệu và huấn luyện (notebook 03-06),báo cáo, slide và poster | 33.33% |
| Lâm Tú Nhi | 3123410250 | Heuristic, Alpha-Beta, MCTS và MCTS lai (`agents/`), tune tham số, phân tích ván của các tác tử tìm kiếm (notebook 07-08), báo cáo và slide | 33.33% |
| Phạm Văn Tuấn | 3123410413 | Giải đấu và độ đo `eval/`, giao diện Pygame `ui/`, notebook 01-02 (kết quả giải đấu, đo chi phí tính toán, ablation), báo cáo và slide | 33.33% |

Nhóm tự viết engine Othello 8x8, cài 6 cấp tác tử AI (từ Random đến RL self-play), cho đấu round-robin với nhau rồi phân tích kết quả để trả lời 3 câu hỏi nghiên cứu bên dưới. Project có kèm giao diện Pygame để chơi thử người-máy và máy-máy.

> Trước khi sửa code, đọc `API.md` (quy ước board, action, chữ ký hàm của game và agent).

**Trạng thái hiện tại: đã xong cả 6 cấp agent, engine, giải đấu, ablation, tune, huấn luyện, giao diện, báo cáo và slide.** Phần kết quả nằm ở mục 5.

## Mục lục

1. [Câu hỏi nghiên cứu](#1-câu-hỏi-nghiên-cứu)
2. [Luật chơi áp dụng](#2-luật-chơi-áp-dụng)
3. [Các tác tử](#3-các-tác-tử)
4. [Cấu trúc thư mục](#4-cấu-trúc-thư-mục)
5. [Kết quả chính](#5-kết-quả-chính)
6. [Cài đặt](#6-cài-đặt)
7. [Cách chạy](#7-cách-chạy)
8. [Tái lập thí nghiệm](#8-tái-lập-thí-nghiệm)
9. [Lưu ý khi dùng repo](#9-lưu-ý-khi-dùng-repo)
10. [Báo cáo, slide, log](#10-báo-cáo-slide-log)

## 1. Câu hỏi nghiên cứu

1. MCTS có thắng Alpha-Beta khi hai bên có cùng thời gian suy nghĩ mỗi nước không? Kết quả có đổi khi đổi ngân sách thời gian không?
2. Hàm đánh giá có góc và mobility có mạnh hơn hàm chỉ đếm quân không, và mạnh hơn bao nhiêu?
3. Self-play RL có cải thiện tác tử học được so với mô hình bắt chước Alpha-Beta (supervised) không?

## 2. Luật chơi áp dụng

Chi tiết xem `rules_othello.md`. Tóm tắt phần engine đang cài:

- Bàn 8x8. Vị trí đầu: 4 quân ở giữa xếp chéo, Đen đi trước.
- Nước hợp lệ: đặt quân vào ô trống sao cho kẹp được ít nhất một chuỗi quân đối thủ theo 1 trong 8 hướng; các quân bị kẹp bị lật hết.
- Không có nước hợp lệ thì bị bỏ lượt (pass). **Engine tự xử lý pass**, agent không bao giờ thấy action pass.
- Ván kết thúc khi cả hai bên đều không còn nước đi. Nhiều quân hơn thắng, bằng nhau hòa.
- Reward theo góc nhìn từng người chơi: +1 thắng, 0 hòa, -1 thua.
- Quy ước kỹ thuật: Đen = 1, Trắng = -1, ô trống = 0; action là `(row, col)` với chỉ số 0..7.

## 3. Các tác tử

Tất cả đều tạo qua `agents/registry.py` từ các mục trong `configs/agents.yaml`.

| Cấp | Tác tử | File | Ghi chú |
|---|---|---|---|
| 1 | Random | `agents/random_agent.py` | có seed riêng |
| 2 | Heuristic | `agents/heuristic_agent.py` | chọn nước theo thứ tự luật ưu tiên (thắng ngay, lấy góc, chặn góc đối thủ, tránh ô X/C, mobility, số quân); thứ tự đọc từ `configs/agents_heuristic.yaml`, đổi luật khi gần tàn cuộc |
| 3 | Minimax / Alpha-Beta | `agents/alphabeta_agent.py` | chạy trên bitboard, lặp sâu theo `time_budget`, có bật/tắt cắt tỉa và sắp xếp nước, hàm đánh giá gồm số quân, mobility, góc, ô X/C (`stability` chưa cài) |
| 4 | MCTS (UCT) | `agents/mcts_agent.py` | rollout random hoặc heuristic, dừng theo thời gian hoặc theo số mô phỏng |
| 4b | MCTS lai (`mcts_leaf`) | `agents/mcts_agent.py` (`leaf_eval: true`) | không rollout, đánh giá nút lá bằng hàm đánh giá của Alpha-Beta qua sigmoid |
| 5 | Neural Network (supervised) | `agents/nn_agent.py` | CNN + 4 khối ResBlock (~1.56 triệu tham số), học bắt chước Alpha-Beta; che nước sai trước khi argmax |
| 6 | Reinforcement Learning | `agents/rl_agent.py` | cùng mạng và cùng code suy luận với cấp 5, khác ở cách train: REINFORCE có baseline, self-play, khởi tạo từ checkpoint của cấp 5 |

Các thành phần khác:

| Thành phần | File | Ghi chú |
|---|---|---|
| Engine (luật, pass, kết thúc, clone) | `othello/` | có test và perft; `bitboard.py` dùng cho agent tìm kiếm |
| Giải đấu round-robin | `eval/tournament.py`, `eval/metrics.py` | chia đều đi trước/sau, nhiều seed, Wilson CI, bootstrap |
| Ablation | `eval/ablations.py`, `scripts/run_heuristic_ablation.py` | xem mục 9 về biến thể ablation đang bị comment |
| Profile chi phí | `eval/profile_cost.py` | thời gian/nước, nodes, RAM |
| Phân tích ván và chất lượng nước đi | `eval/game_analysis.py`, `eval/move_quality.py` | đọc từ log thô, không chạy lại agent |
| Tune tham số | `scripts/run_tuning.py`, `notebooks/tune.py`, `eval/tune_report.py` | tune bằng seed riêng (100/200), không dùng seed đánh giá cuối |
| Giao diện demo | `ui/` | Pygame, người-máy và máy-máy, có panel vẽ cây tìm kiếm (phím `T`) |

## 4. Cấu trúc thư mục

```
Project_final/
├── README.md
├── API.md                          # quy ước board/action/pass + chữ ký hàm game và agent
├── rules_othello.md                # luật chơi chi tiết
├── TTNTNC_De_tai_cuoi_ky_Game_AI.pdf   # đề bài
├── requirements.txt
├── pytest.ini                      # mặc định bỏ test chậm; chạy bằng `pytest -m slow`
├── .gitignore
│
├── configs/                        # mọi tham số thí nghiệm, không hard-code
│   ├── constants.py                # hằng số: góc, ô X/C, tên luật heuristic, trọng số mặc định của hàm đánh giá
│   ├── game.yaml                   # luật game (tài liệu hóa; engine cài cứng, có test đối chiếu)
│   ├── agents.yaml                 # NGUỒN cấu hình các agent (cả UI, giải đấu, scripts đều đọc file này)
│   ├── agents_heuristic.yaml       # thứ tự luật ưu tiên của Heuristic
│   ├── agents_alphabeta.yaml       # các biến thể Alpha-Beta để copy sang agents.yaml (đang comment)
│   ├── tournament.yaml             # giải đấu chính: 200 ván/cặp, seed 0-2, 2 chế độ ngân sách
│   ├── tournament_tune.yaml        # giải đấu tune: 40 ván/cặp, seed 100-102
│   ├── train_supervised.yaml       # siêu tham số NN supervised
│   └── train_rl.yaml               # siêu tham số RL self-play
│
├── othello/                        # engine
│   ├── encoding.py                 # hằng số, action <-> chỉ số 0..63, encode_planes() cho NN
│   ├── rules.py                    # hàm thuần: legal_moves, flips_for_move, apply_move
│   ├── game.py                     # OthelloGame: step, clone, tự xử lý pass và kết thúc ván
│   ├── bitboard.py                 # bản bitboard (nhanh hơn nhiều) cho Alpha-Beta và MCTS
│   └── board_features.py           # đặc trưng bàn cờ dùng chung: góc, mobility, ô X/C, số quân
│
├── agents/
│   ├── base.py                     # lớp Agent: select_action, reset, stats
│   ├── random_agent.py             # cấp 1
│   ├── heuristic_agent.py          # cấp 2
│   ├── alphabeta_agent.py          # cấp 3 (bản đang dùng)
│   ├── alphabeta_agent1.py         # bản Alpha-Beta cũ, vẫn còn vài test import
│   ├── mcts_agent.py               # cấp 4 và 4b (MCTS lai)
│   ├── nn_agent.py                 # cấp 5
│   ├── rl_agent.py                 # cấp 6 (kế thừa NNAgent)
│   └── registry.py                 # tạo agent từ agents.yaml
│
├── models/
│   ├── nets.py                     # PolicyValueNet (bản đang dùng, có ResBlock)
│   └── nets_v1.py                  # bản mạng cũ (không ResBlock), vẫn còn vài test import
│
├── eval/
│   ├── tournament.py               # round-robin, ghi log thô
│   ├── metrics.py                  # W/D/L, score, Wilson CI, bootstrap, latency
│   ├── evaluation.py               # hàm đánh giá thế cờ cho Alpha-Beta và MCTS lai
│   ├── ablations.py                # chạy 3 ablation bằng runner của giải đấu
│   ├── profile_cost.py             # đo thời gian/nodes/RAM theo agent
│   ├── game_analysis.py            # phân tích ván từ log thô
│   ├── move_quality.py             # chấm chất lượng từng nước đi bằng Alpha-Beta tham chiếu
│   └── tune_report.py              # gộp log tune thành bảng markdown + hình
│
├── utils/
│   └── search_utils.py             # Deadline, lịch lặp sâu, sắp xếp nước đi
│
├── ui/                             # giao diện Pygame
│   ├── app.py                      # vòng lặp chính
│   ├── menu.py                     # menu chọn chế độ, agent, thời gian
│   ├── match.py                    # logic một ván + thread AI
│   ├── game_view.py                # vẽ bàn cờ, bảng điểm
│   ├── tree.py                     # panel vẽ cây tìm kiếm
│   ├── widgets.py, draw_utils.py, config.py
│   └── assets/chess_sound.mp3
│
├── scripts/
│   ├── play_game.py                # chơi 1 ván / chạy nhiều ván không giao diện
│   ├── run_tournament.sh           # giải đấu theo tournament.yaml
│   ├── run_ablations.sh            # 3 ablation chính
│   ├── run_training.sh             # chạy notebook 04-06 bằng nbconvert
│   ├── run_tuning.py               # toàn bộ thí nghiệm tune
│   ├── run_heuristic_ablation.py   # bỏ từng luật của Heuristic
│   ├── run_exp.py                  # thí nghiệm bổ sung e1-e4 (mục 4.7 báo cáo)
│   └── exp_common.py
│
├── notebooks/                      # tạo bảng/hình từ log thô + huấn luyện
│   ├── 01_tournament_results.ipynb
│   ├── 02_ablations.ipynb
│   ├── 03_learning_curves.ipynb
│   ├── 04_generate_data.ipynb      # sinh dữ liệu expert
│   ├── 05_train_supervised.ipynb   # train NN cấp 5
│   ├── 06_train_rl.ipynb           # RL self-play cấp 6
│   ├── 07_game_analysis.ipynb
│   ├── 08_tuning_analysis.ipynb
│   ├── data_gen.py                 # sinh ván song song (notebook 04 gọi)
│   └── tune.py                     # chạy 1 thí nghiệm tune (run_tuning.py gọi)
│
├── tests/                          # pytest (game, perft, agents, config, metrics, tournament, NN, registry/UI...)
│
├── checkpoints/
│   ├── nn_supervised_alphabeta_v2.pt    # đang dùng trong agents.yaml (cấp 5)
│   ├── rl_selfplay_alphabeta_v2.pt      # đang dùng trong agents.yaml (cấp 6)
│   └── ...                              # bản cũ: v1, expert heuristic, nn_supervised_alphabeta_v2_1.pt
│
├── data/
│   ├── supervised_alphabeta_v1/    # dữ liệu expert Alpha-Beta bản v1 (games.jsonl, train/val/test.npz, meta.json)
│   └── supervised_heuristic_v1/    # dữ liệu expert Heuristic bản v1
│
├── results/
│   ├── figures/                    # hình dùng trong báo cáo (01_*, 02_*, 03_*)
│   ├── analysis/round_robin_v2/    # selected_games.md: ván chọn theo quy tắc cố định
│   └── logs/Log.md                 # link tới log thô trên Google Drive
│
└── docs/
    ├── report/BaoCao.md            # link báo cáo
    ├── slides/Slide.md             # link slide
    └── poster/                     # poster PDF
```

## 5. Kết quả chính

Số liệu lấy từ notebook `01`-`03` (giải đấu `round_robin_v4`: 7 agent, 21 cặp, 200 ván/cặp, seed 0-2, 2 chế độ ngân sách, tổng 8400 ván). Score = (thắng + 0.5 × hòa) / số ván, mỗi agent đấu 1200 ván mỗi chế độ.

| Hạng | Agent | Score (0.5 s/nước) | Score (cấu hình mặc định) |
|---|---|---|---|
| 1 | Alpha-Beta | 0.953 | 0.888 |
| 2 | MCTS lai (leaf) | 0.780 | 0.673 |
| 3 | RL self-play | 0.493 | 0.548 |
| 4 | NN supervised | 0.485 | 0.542 |
| 5 | MCTS (rollout) | 0.478 | 0.539 |
| 6 | Heuristic | 0.304 | 0.302 |
| 7 | Random | 0.008 | 0.008 |

**Câu hỏi 1 (MCTS vs Alpha-Beta):** Alpha-Beta thắng MCTS rollout rất rõ (score 0.975 ở 0.5 s/nước, 0.88 ở cấu hình mặc định). MCTS lai bám sát hơn nhưng Alpha-Beta vẫn thắng (score Alpha-Beta 0.8175 ở 0.5 s/nước, 0.7825 ở cấu hình mặc định). Trong ablation số mô phỏng, khi không giới hạn thời gian thì tăng mô phỏng làm score MCTS tăng mạnh (`mcts_100`: 0.05 → `mcts_5000`: 0.84), còn khi cố định 0.5 s/nước thì gần như không đổi vì cả 4 biến thể đều bị chặn bởi thời gian.

**Câu hỏi 2 (hàm đánh giá):** Alpha-Beta với hàm đánh giá đầy đủ thắng bản chỉ đếm quân 96/1/3 trên 100 ván; Heuristic đủ luật thắng Heuristic chỉ đếm quân 98/0/2.

**Câu hỏi 3 (RL vs supervised):** NN supervised đạt 58.8% trùng nước expert trên tập test (đoán ngẫu nhiên trong nước hợp lệ: 20.5%), train 80 epoch, chọn epoch 40 theo val. RL train 30000 ván self-play từ checkpoint đó. Đối đầu trực tiếp NN vs RL: 104-9-87 (score NN 0.5425). Trong learning curve, RL chỉ tăng rõ khi đấu Heuristic (0.72 → 0.80); với Alpha-Beta (0.175 → 0.18) và NN (0.495 → 0.4925) chưa phân biệt được với đầu kỳ ở 200 ván. Nói cách khác, chưa có bằng chứng RL cải thiện đáng kể so với mô hình bắt chước.

Phần nhận xét đầy đủ và các thí nghiệm bổ sung nằm trong báo cáo (mục 10).

## 6. Cài đặt

Yêu cầu: Python 3.10 trở lên.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` gồm numpy, PyYAML, tqdm, torch, pandas, scipy, statsmodels, matplotlib, jupyter, pygame, pytest. Train NN/RL chạy được trên CPU nhưng có GPU sẽ nhanh hơn nhiều (nhóm train trên RTX 3050 Laptop: NN supervised ~55 phút, RL 30000 ván ~87 phút).

## 7. Cách chạy

Chạy tất cả lệnh từ thư mục gốc của project.

### Giao diện và chơi thử

```bash
python -m ui.app          # menu: Human vs Agent / Agent vs Agent, chọn agent bằng nút < >, chọn thời gian mỗi nước
python scripts/play_game.py                                   # chơi trên giao diện
python scripts/play_game.py --cli --black random --white heuristic --games 100   # không giao diện
```

Danh sách agent trong menu lấy từ `configs/agents.yaml`. Agent thiếu checkpoint hoặc chưa có code sẽ hiện lý do màu đỏ và khóa nút Start (không crash).

### Test

```bash
python -m pytest                 # test nhanh (gồm perft độ sâu 1-6)
python -m pytest -m slow         # perft độ sâu 7
```

### Giải đấu và đánh giá

```bash
# giải đấu chính (agent, chế độ ngân sách, seed trong configs/tournament.yaml)
python -m eval.tournament --config configs/tournament.yaml --run-name round_robin_v5 --workers 3
bash scripts/run_tournament.sh --run-name round_robin_v5 --workers 3

# chạy thử nhanh
python -m eval.tournament --config configs/tournament.yaml --games 20 --run-name smoke

# giải đấu tune (seed riêng 100-102)
python -m eval.tournament --config configs/tournament_tune.yaml

# ablation (xem mục 9 trước khi chạy)
python -m eval.ablations --config configs/tournament.yaml --out results/logs/ablations
python scripts/run_heuristic_ablation.py --games 200

# profile chi phí
python -m eval.profile_cost --agents random,heuristic,alphabeta,mcts --samples 20 --time-budget 0.5

# phân tích ván và chất lượng nước đi từ log thô
python -m eval.game_analysis --run results/logs/<run_name> --out results/analysis/<run_name>
python -m eval.move_quality --games results/logs/<run_name>/games.jsonl --agent mcts alphabeta random --mode time_per_move
```

Kết quả giải đấu ghi vào `results/logs/<run_name>/` (`games.jsonl`, `summary.json`, `matrix_<mode>.csv`, `meta.json`, snapshot config). Thư mục `run_name` phải chưa tồn tại hoặc rỗng để không ghi đè log thô.

### Tune tham số

```bash
python scripts/run_tuning.py --list
python scripts/run_tuning.py --only mcts_rollout mcts_c --workers 4
```

Xong thì mở `notebooks/08_tuning_analysis.ipynb` (hoặc `python -m eval.tune_report`) để ra bảng và lý do chọn tham số.

### Huấn luyện NN (cấp 5) và RL (cấp 6)

Toàn bộ quy trình nằm trong notebook, chạy lần lượt:

| Notebook | Việc | Đầu ra |
|---|---|---|
| `notebooks/04_generate_data.ipynb` | expert (Alpha-Beta) chơi, gắn nhãn, chia train/val/test theo ván | thư mục `output_dir` trong `configs/train_supervised.yaml` |
| `notebooks/05_train_supervised.ipynb` | train NN bắt chước expert, test đúng 1 lần | `checkpoints/nn_supervised_alphabeta_v2.pt` |
| `notebooks/06_train_rl.ipynb` | RL self-play, learning curve | `checkpoints/rl_selfplay_alphabeta_v2.pt` |
| `notebooks/03_learning_curves.ipynb` | vẽ hình từ log của 05 và 06 | `results/figures/` |

- Mỗi notebook có biến `QUICK_TEST` ở ô đầu: đặt `True` để chạy thử trong vài giây.
- Không muốn mở Jupyter: `bash scripts/run_training.sh` (bản đã chạy lưu ở `results/executed_notebooks/`).
- Mỗi lần train chính thức đổi `RUN_NAME` trong notebook 05/06 để không ghi đè log thô.
- Dữ liệu `data/supervised_*_v1/` trong repo là bản cũ; config hiện tại ghi ra `data/supervised_alphabeta_v2/` nên cần chạy notebook 04 để sinh lại.

### Bảng và hình cho báo cáo

Notebook `01` (giải đấu), `02` (ablation), `03` (learning curve), `07` (phân tích ván), `08` (tune) chỉ đọc log thô trong `results/logs/` rồi sinh bảng và hình (hình lưu ở `results/figures/`).

## 8. Tái lập thí nghiệm

- Mọi tham số nằm trong `configs/`, seed ghi rõ trong config.
- Mỗi ván tạo agent mới với seed xác định nên chạy lại ra đúng nước đi (trừ thời gian).
- Giải đấu chia đều đi trước/sau: mỗi cặp ván dùng cùng khai cuộc ngẫu nhiên (`opening_plies`) rồi đổi màu.
- Tập tune (seed 100-102, xác nhận 200) tách khỏi tập đánh giá cuối (seed 0-2).
- Log thô từng ván không sửa tay; hình và bảng đều sinh từ notebook đọc log.
- Máy chạy giải đấu chính: Intel 16 luồng, Windows 11, 3 worker, khoảng 6.4 giờ cho 8400 ván.

## 9. Lưu ý khi dùng repo

- **Log thô không nằm trong repo** (`results/logs/*` bị `.gitignore`), tải ở link trong `results/logs/Log.md`. Vì vậy các notebook `01`, `02`, `07`, `08` cần có log mới chạy được. `data/*` cũng bị ignore (trừ `.gitkeep`).
- **Ablation:** các biến thể `alphabeta_nopruning`, `alphabeta_discs_only`, `mcts_100`, `mcts_500`, `mcts_5000`, `heuristic_discs_only` đang bị comment trong `configs/agents.yaml`. `eval/ablations.py` cần chúng, nên bỏ comment (hoặc copy từ `configs/agents_alphabeta.yaml`) trước khi chạy.
- Vài chú thích trong `configs/tournament.yaml` còn ghi ablation/profile là "chưa có code"; hiện cả hai đã có (`eval/ablations.py`, `eval/profile_cost.py`).
- `alphabeta_agent1.py` và `models/nets_v1.py` là bản cũ nhưng một số test còn import nên giữ lại. Một vài test import theo đường dẫn `Project_final.…`, nên cần đứng đúng thư mục cha khi chạy (hoặc sửa import).
- `eval.stability` của Alpha-Beta chưa cài; bật lên sẽ báo `NotImplementedError`.
- `configs/game.yaml` chỉ để tài liệu hóa luật, engine cài cứng; `tests/test_configs.py` kiểm tra hai bên khớp nhau.
- `scripts/run_exp.py` ghi kết quả vào `exp_out/` (thư mục này tạo khi chạy, không có sẵn trong repo).

## 10. Báo cáo, slide, log

- Báo cáo: `docs/report/BaoCao.md` (link Google Docs)
- Slide: `docs/slides/Slide.md` (link Canva)
- Poster: `docs/poster/Othello Game AI – Poster.pdf`
- Log huấn luyện và thực nghiệm: `results/logs/Log.md` (link Google Drive)
- Đề bài: `TTNTNC_De_tai_cuoi_ky_Game_AI.pdf`