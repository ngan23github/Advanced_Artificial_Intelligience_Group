"""Hằng số của giao diện: kích thước, màu, danh sách chế độ/thời gian. Không import pygame ở đây."""

from othello.encoding import BLACK, WHITE

# ---------- bố cục ----------
CELL, N, MARGIN = 72, 8, 28              # ô cờ (px), số ô mỗi cạnh, lề quanh bàn cờ
BOARD_PX = CELL * N
BOARD_W = BOARD_PX + 2 * MARGIN
PANEL_W = 300                            # bảng thông tin bên phải
WIN_W, WIN_H = BOARD_W + PANEL_W, BOARD_W
AGENT_DELAY = 1.0                        # giây; thời gian tối thiểu hiển thị mỗi nước của agent (để người xem kịp nhìn)

# ---------- màu ----------
C_BG = (24, 26, 31)
C_PANEL = (32, 35, 42)
C_CARD = (42, 46, 55)
C_ACCENT = (46, 125, 90)
C_BTN = (58, 63, 74)
C_BTN_HOVER = (74, 80, 93)
C_BTN_OFF = (36, 39, 46)
C_TEXT = (236, 238, 242)
C_DIM = (135, 142, 155)
C_WARN = (255, 196, 80)
C_ERR = (240, 100, 90)
C_BOARD = (38, 128, 78)
C_BOARD_ALT = (34, 120, 72)
C_GRID = (22, 80, 48)
C_DISC_B = (22, 22, 24)
C_DISC_W = (246, 246, 244)
C_LAST = (235, 80, 70)

# ---------- văn bản (toàn bộ chữ trên UI là tiếng Anh) ----------
NAME = {BLACK: "Black", WHITE: "White"}
MODES = [("Human vs Agent", "hva"), ("Agent vs Agent", "ava")]
TIMES = [("Default", None), ("0.5 s", 0.5), ("1 s", 1.0), ("2 s", 2.0), ("5 s", 5.0)]
