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
