# Nguồn tham khảo và phân biệt phần tự làm / phần kế thừa

Đề yêu cầu nêu rõ phần nào nhóm tự cài đặt, phần nào kế thừa. File này cập nhật dần trong lúc làm.

## Phần nhóm tự cài đặt

| Thành phần | Ghi chú |
|---|---|
| Engine Othello (`othello/`) | TODO |
| Random / Heuristic / Alpha-Beta / MCTS | TODO |
| Pipeline sinh dữ liệu, train (notebook 04-06, `models/nets.py`, `agents/nn_agent.py`, `agents/rl_agent.py`) | Người 3. Tự cài đặt: mạng CNN policy-value, sinh dữ liệu/chia theo ván/dedupe, đối xứng bàn cờ, train supervised, REINFORCE có baseline + self-play, đánh giá learning curve.|
| Giải đấu, độ đo, ablation | TODO |
| Giao diện demo | TODO |

## Phần kế thừa / dùng thư viện

| Thành phần | Nguồn | Dùng vào việc gì |
|---|---|---|
| NumPy, PyTorch, pandas, scipy, statsmodels, matplotlib, pygame | thư viện chuẩn | tính toán, train, thống kê, hình, UI |
| TODO | | |

## Tài liệu tham khảo

- Mark Liu, *AlphaGo Simplified: Rule-Based AI and Deep Learning in Everyday Games*, CRC Press.
- Russell & Norvig, *Artificial Intelligence: A Modern Approach* (2021).
- Sutton & Barto, *Reinforcement Learning: An Introduction* (2018).
- TODO: bổ sung bài báo, repo mở, tài liệu khác đã đọc.

## Công cụ AI đã dùng

Ghi rõ đã dùng công cụ AI (Claude) vào việc gì, ví dụ: gợi ý cấu trúc repo, hỗ trợ viết khung code. Phần nào do AI viết mà nhóm sửa lại thì ghi chú ở đây.

- Phần học máy (Người 3): khung code ban đầu (`models/nets.py`, notebook 04-06, `agents/nn_agent.py`, `agents/rl_agent.py`,
  `agents/registry.py` bản hợp nhất, tách `ui/`, `tests/`, notebook 03) do Claude (Anthropic) viết theo `PHAN_CONG.md`; thành viên cần đọc, chạy,
  chỉnh sửa và tự hiểu từng phần trước khi nộp. Nhóm ghi lại chỗ nào đã sửa tay.
