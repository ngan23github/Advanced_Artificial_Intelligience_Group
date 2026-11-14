"""Hằng số của giao diện: kích thước, màu, danh sách chế độ/thời gian. Không import pygame ở đây."""

from othello.encoding import BLACK, WHITE

# ---------- bố cục ----------
CELL, N, MARGIN = 72, 8, 34              # ô cờ (px), số ô mỗi cạnh, lề quanh bàn cờ
BOARD_PX = CELL * N
BOARD_W = BOARD_PX + 2 * MARGIN
PANEL_W = 340                            # bảng thông tin bên phải rộng rãi hơn
WIN_W, WIN_H = BOARD_W + PANEL_W, BOARD_W
AGENT_DELAY = 1.0                        # giây; thời gian tối thiểu hiển thị mỗi nước của agent (để người xem kịp nhìn)
PLACE_TIME = 0.22                        # giây; thời lượng hiệu ứng đặt quân cờ
FLIP_TIME = 0.30                         # giây; thời lượng hiệu ứng lật mỗi quân cờ
FLIP_WAVE = 0.06                         # giây; độ trễ lan truyền lật quân theo từng ô cách quân vừa đặt

# ---------- bảng màu hiện đại (Rich Slate & Emerald Felt) ----------
C_BG = (15, 19, 26)                      # nền chính tối sâu sang trọng
C_BG_TOP = (24, 31, 44)                  # ánh sáng đỉnh nền gradient
C_PANEL = (20, 25, 35)                   # nền panel bên phải
C_CARD = (30, 38, 52)                    # nền thẻ (card)
C_CARD_HI = (38, 48, 66)                 # nền thẻ nổi bật
C_BORDER = (52, 65, 86)                  # viền mảnh quanh card/button
C_ACCENT = (16, 185, 129)                # xanh ngọc lục bảo (Emerald accent)
C_ACCENT_GLOW = (52, 211, 153)           # viền sáng khi chọn / tới lượt
C_GOLD = (245, 184, 65)                  # vàng kim cho tiêu đề / chiến thắng
C_BTN = (36, 45, 62)                     # nút thường
C_BTN_HOVER = (51, 64, 88)               # nút khi rê chuột
C_BTN_OFF = (25, 31, 42)                 # nút bị khóa
C_TEXT = (241, 245, 249)                 # chữ chính trắng sáng
C_DIM = (148, 163, 184)                  # chữ phụ xám bạc
C_WARN = (251, 191, 36)                  # vàng cảnh báo / thông báo
C_ERR = (248, 113, 113)                  # đỏ báo lỗi
C_WOOD = (28, 22, 18)                    # khung gỗ viền bàn cờ
C_WOOD_BORDER = (78, 60, 42)             # chỉ viền khung bàn cờ
C_BOARD = (22, 122, 74)                  # ô bàn cờ nỉ xanh
C_BOARD_ALT = (18, 108, 65)              # ô bàn cờ xen kẽ
C_GRID = (11, 68, 40)                    # đường kẻ lưới bàn cờ
C_DISC_B = (24, 26, 32)                  # quân Đen
C_DISC_W = (245, 247, 250)               # quân Trắng
C_LAST = (244, 63, 94)                   # chấm đánh dấu nước vừa đi

# ---------- văn bản (toàn bộ chữ trên UI là tiếng Anh) ----------
NAME = {BLACK: "Black", WHITE: "White"}
MODES = [("Human vs Agent", "hva"), ("Agent vs Agent", "ava")]
TIMES = [("Default", None), ("0.5 s", 0.5), ("1 s", 1.0), ("2 s", 2.0), ("5 s", 5.0)]
