# Ván được chọn theo quy tắc cố định

Với mỗi (chế độ, cặp agent) được chọn (--focus): (1) `worst_loss:<agent>` = ván agent đó thua chênh lệch quân lớn nhất; (2) `closest` = ván có |chênh lệch quân| nhỏ nhất; (3) `longest` = ván có nhiều nước nhất; (4) `random1`, `random2` = 2 ván bốc ngẫu nhiên bằng random.Random(SEED_CHON_VAN) trên danh sách game_id đã sắp xếp. Hòa điểm thì lấy game_id nhỏ hơn theo thứ tự chữ cái. Quy tắc cố định TRƯỚC khi xem ván, áp dụng như nhau cho mọi cặp.


## [worst_loss:alphabeta] default_config|alphabeta|mcts|s1|p17|AB

Đen = alphabeta, Trắng thắng, chênh lệch quân (Đen - Trắng) = -16, 60 nước.


sau nước 20 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . . . . . . .
1 . . . O O X . .
2 . . O O O . . O
3 . O O O X O O .
4 . . O X X O X X
5 . . . . O O X O
6 . . . . O . . .
7 . . . . . . . .
Đen X: 7  Trắng O: 17  Lượt: Đen (X)
```


sau nước 40 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . O O O O O . .
1 . . . X O O . .
2 . . O X X O O O
3 . O O X O X O X
4 O . O X X O X X
5 X O X X O X O O
6 . . O X X O . .
7 . . O X X O . .
Đen X: 18  Trắng O: 26  Lượt: Đen (X)
```


kết thúc (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 X O O O O O O O
1 O X O O O X O X
2 O O X O X O X X
3 O X O X O X X X
4 O X O O X O X X
5 O X O X O X O X
6 O O X O O O O X
7 O O O O O O O X
Đen X: 24  Trắng O: 40  Lượt: Hết ván
```


## [worst_loss:mcts] default_config|alphabeta|mcts|s0|p30|BA

Đen = mcts, Trắng thắng, chênh lệch quân (Đen - Trắng) = -63, 59 nước.


sau nước 20 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . X X X X . .
1 . . X X X X . .
2 . . X O X X . .
3 . . X O O X . .
4 . . . O O O O O
5 . . . O . X X .
6 . . . . . . . .
7 . . . . . . . .
Đen X: 15  Trắng O: 9  Lượt: Đen (X)
```


sau nước 40 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 O O O O O O O O
1 O O O X X O O O
2 . O X X X X O O
3 . X X O X O O O
4 . X X O O O O O
5 . . X X . X O O
6 . . . X . . . O
7 . . . . . . . .
Đen X: 15  Trắng O: 29  Lượt: Đen (X)
```


kết thúc (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 O O O O O O O O
1 O O O O O O O O
2 O O O O O O O O
3 O O O O O O O O
4 O O O O O O O O
5 O O O O O O O O
6 O O O O O O O O
7 . O O O O O O O
Đen X: 0  Trắng O: 63  Lượt: Hết ván
```


## [closest] default_config|alphabeta|mcts|s0|p27|AB

Đen = alphabeta, Hòa, chênh lệch quân (Đen - Trắng) = 0, 60 nước.


sau nước 20 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . . . . . . .
1 . . . . . . . .
2 X O O O X O . .
3 X X O X O . . .
4 X X X O O . . .
5 X X O O O X . .
6 X . O . . . . .
7 . . . . . . . .
Đen X: 12  Trắng O: 12  Lượt: Đen (X)
```


sau nước 40 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 X . O . . . . .
1 X X O O . O . .
2 X X O O O O . .
3 X X X O O O . .
4 X O X X O O . .
5 X X X X O O O .
6 X O O O O O . .
7 X O X X X X . .
Đen X: 21  Trắng O: 23  Lượt: Đen (X)
```


kết thúc (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 X X X X X X X X
1 X O O X O O O O
2 X O O O X X O O
3 X O O X X X O X
4 X O O O O X O O
5 X X X X X O O O
6 X O O O O O O O
7 X O X X X X X O
Đen X: 32  Trắng O: 32  Lượt: Hết ván
```


## [longest] default_config|alphabeta|mcts|s0|p0|AB

Đen = alphabeta, Đen thắng, chênh lệch quân (Đen - Trắng) = 18, 60 nước.


sau nước 20 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . . . . . . .
1 . . . . . O . .
2 . . O X O O O .
3 . O O O X O O .
4 . . O X O O X .
5 O O O O O O . .
6 . . . . . O . .
7 . . . . . . . .
Đen X: 4  Trắng O: 20  Lượt: Đen (X)
```


sau nước 40 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . . . . . . .
1 . . . . O O . .
2 . . O O O O O O
3 . O O O X X O X
4 . O O X X O X X
5 O O O X O X O O
6 . X O O O O O O
7 X X X X X X . X
Đen X: 17  Trắng O: 27  Lượt: Đen (X)
```


kết thúc (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 X X X X X X X O
1 X X X X X X O O
2 X O X O X O X O
3 X X O O X X O O
4 X O O O X O X O
5 X X O O X X X O
6 X O X O O X X O
7 X X X X X X X X
Đen X: 41  Trắng O: 23  Lượt: Hết ván
```


## [random1] default_config|alphabeta|mcts|s0|p23|AB

Đen = alphabeta, Đen thắng, chênh lệch quân (Đen - Trắng) = 16, 60 nước.


sau nước 20 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . . . . . . .
1 . . . . . . . .
2 . . . X O O O O
3 . O O O O X O .
4 . . O X X X X X
5 . O O X X X O .
6 . . O . . . . .
7 . . . . . . . .
Đen X: 10  Trắng O: 14  Lượt: Đen (X)
```


sau nước 40 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . . . . . . .
1 . . . . O . . .
2 . O O O O O O O
3 . O O O X X O X
4 . O O X X O O X
5 . O O X X X O O
6 . X O O O O O O
7 X X X X X X X X
Đen X: 18  Trắng O: 26  Lượt: Đen (X)
```


kết thúc (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 X X X X X X X X
1 X X X X O O O O
2 X O O O X X O O
3 X O O X X X X X
4 X O O X X O O X
5 X O X X X X O O
6 X O X O O O O O
7 X X X X X X X X
Đen X: 40  Trắng O: 24  Lượt: Hết ván
```


## [random2] default_config|alphabeta|mcts|s1|p15|BA

Đen = mcts, Trắng thắng, chênh lệch quân (Đen - Trắng) = -52, 60 nước.


sau nước 20 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . . . . . . .
1 . . . . . . . .
2 . . . X X X X .
3 . O O X O X . .
4 . . O O O X . .
5 . X X O O X . .
6 . . X X O X . .
7 . . X . O . . .
Đen X: 14  Trắng O: 10  Lượt: Đen (X)
```


sau nước 40 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . . . . . . .
1 . . . . . . . .
2 O X . X X X X .
3 O X X X O X . .
4 O X O X X X X X
5 O X X O O O X X
6 O O O X O X X X
7 O O O O O O O O
Đen X: 23  Trắng O: 21  Lượt: Trắng (O)
```


kết thúc (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 O O O O O O X O
1 O O O O O O O O
2 O O O O O O O O
3 O O O O O O O O
4 O O O O X X O O
5 O O O O X O O O
6 O O O X O X O O
7 O O O O O O O O
Đen X: 6  Trắng O: 58  Lượt: Hết ván
```


## [worst_loss:alphabeta] time_per_move|alphabeta|mcts|s2|p11|AB

Đen = alphabeta, Trắng thắng, chênh lệch quân (Đen - Trắng) = -18, 60 nước.


sau nước 20 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . . . X O . .
1 . . O . O O . .
2 X X X O X O . .
3 X X X X O . O .
4 . X . X O . . .
5 X . O O . . . .
6 . . O . . . . .
7 . . . . . . . .
Đen X: 12  Trắng O: 12  Lượt: Đen (X)
```


sau nước 40 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 X O O X X O . .
1 O O O X X O . .
2 X O O O O X O O
3 X X O O X O O .
4 . X X X O O . X
5 X X X X X O X .
6 . X O X . . . .
7 X . . . . . . .
Đen X: 23  Trắng O: 21  Lượt: Đen (X)
```


kết thúc (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 X O O X X X X X
1 O X O O O O X X
2 O O X O X X O X
3 O O O X O O O X
4 O O O O O O O X
5 O O X O X X O X
6 O O O O O O O X
7 X O O O O O O X
Đen X: 23  Trắng O: 41  Lượt: Hết ván
```


## [worst_loss:mcts] time_per_move|alphabeta|mcts|s0|p11|AB

Đen = alphabeta, Đen thắng, chênh lệch quân (Đen - Trắng) = 64, 60 nước.


sau nước 20 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . . . . . . .
1 . . . . . . . .
2 . . O O O . . .
3 . . O O O . . .
4 . O O O O . . .
5 O O O O O . . .
6 . X X O O O . .
7 X . X X O . . .
Đen X: 5  Trắng O: 19  Lượt: Đen (X)
```


sau nước 40 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 X X . . . . . .
1 X X X . . . . .
2 X X O O O . . .
3 X X X O O . . .
4 X X X X O . X .
5 X X X X X X X X
6 X X X X X X X .
7 X X X X X X X X
Đen X: 38  Trắng O: 6  Lượt: Trắng (O)
```


kết thúc (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 X X X X X X X X
1 X X X X X X X X
2 X X X X X X X X
3 X X X X X X X X
4 X X X X X X X X
5 X X X X X X X X
6 X X X X X X X X
7 X X X X X X X X
Đen X: 64  Trắng O: 0  Lượt: Hết ván
```


## [closest] time_per_move|alphabeta|mcts|s0|p26|BA

Đen = mcts, Hòa, chênh lệch quân (Đen - Trắng) = 0, 60 nước.


sau nước 20 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . . . . . . .
1 . . . . . . . .
2 . . . X . . . .
3 O O X X X X . .
4 O O X X X X X .
5 X O O O O X . .
6 . . O O X . . .
7 . . . O . . . .
Đen X: 13  Trắng O: 11  Lượt: Đen (X)
```


sau nước 40 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . . . . . . .
1 O X . . . . . .
2 O X X X . . . .
3 O X O X X X . X
4 O O O O O X X O
5 O X O O O X O O
6 O X X X X X O .
7 O O O O O O O O
Đen X: 18  Trắng O: 26  Lượt: Trắng (O)
```


kết thúc (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 O X X X X X O X
1 O X X O O O O X
2 O X X X X X O X
3 O X O O X O O X
4 O X X X O O O X
5 O X X O O X O X
6 O X O X X X X X
7 O O O O O O O O
Đen X: 32  Trắng O: 32  Lượt: Hết ván
```


## [longest] time_per_move|alphabeta|mcts|s0|p0|AB

Đen = alphabeta, Đen thắng, chênh lệch quân (Đen - Trắng) = 42, 60 nước.


sau nước 20 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . . . . . . .
1 . . . . . O . .
2 O O O O O O . .
3 . . O O X O . .
4 . . O O X O O .
5 . . O X O O . .
6 . . X X X . . .
7 . . . . X . . .
Đen X: 7  Trắng O: 17  Lượt: Đen (X)
```


sau nước 40 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . . . . . . .
1 . . . . . O . X
2 O O O O O O O X
3 O O O O O X O X
4 . O O X X X O X
5 O . O O X X O X
6 . . O X O O O X
7 . . O O O O O X
Đen X: 14  Trắng O: 30  Lượt: Đen (X)
```


kết thúc (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 X X X X X X X X
1 X O O X X X X X
2 X O X O X X O X
3 X X O X X X X X
4 X X X X X X O X
5 O X X X X X O X
6 O X X X X X X X
7 O X X X X X X X
Đen X: 53  Trắng O: 11  Lượt: Hết ván
```


## [random1] time_per_move|alphabeta|mcts|s1|p7|AB

Đen = alphabeta, Đen thắng, chênh lệch quân (Đen - Trắng) = 60, 58 nước.


sau nước 20 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . . . . . . .
1 . . . . . . . .
2 X . O . O . . .
3 X X O O O . . .
4 X X O O O . . .
5 X X X O X X . .
6 X O O O . . . .
7 . . . O . . . .
Đen X: 11  Trắng O: 13  Lượt: Đen (X)
```


sau nước 40 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 X . . . . . . .
1 X X O . . . . .
2 X X O O O . O .
3 X X O X X O . .
4 X X X X X O O .
5 X X X X X O . .
6 X X O O O O X .
7 X X X X X X X X
Đen X: 30  Trắng O: 14  Lượt: Đen (X)
```


kết thúc (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 X X X X X X X X
1 X X X X X . X X
2 X X X X X X X X
3 X X X X X X X X
4 X X X X X X X .
5 X X X X X X X X
6 X X O X X X X X
7 X X X X X X X X
Đen X: 61  Trắng O: 1  Lượt: Hết ván
```


## [random2] time_per_move|alphabeta|mcts|s1|p8|BA

Đen = mcts, Trắng thắng, chênh lệch quân (Đen - Trắng) = -58, 60 nước.


sau nước 20 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . X . . . . .
1 . . X . . X . .
2 . X X O O O . .
3 . . X X X X . .
4 . . O X O . . .
5 . O X O X X X .
6 . X O . . . . .
7 . . O . . . . .
Đen X: 15  Trắng O: 9  Lượt: Đen (X)
```


sau nước 40 (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 . . X . . . . .
1 . . X . . X X X
2 . X X X X O X .
3 O O O O O X . .
4 O O O O X X . .
5 O O O O O X X .
6 O O X X O O X .
7 O O O O O O O .
Đen X: 18  Trắng O: 26  Lượt: Trắng (O)
```


kết thúc (Đen X / Trắng O):
```
  0 1 2 3 4 5 6 7
0 O O O O O O O O
1 O O O O O O O O
2 O O O O O O O O
3 O O O O O O O O
4 O O X O O O O O
5 O O O O O O O O
6 O O X O X O O O
7 O O O O O O O O
Đen X: 3  Trắng O: 61  Lượt: Hết ván
```
