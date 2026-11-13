"""Hàm vẽ và âm thanh dùng chung: font, quân cờ 3D bóng bẩy (tĩnh, đặt quân, lật quân) và tiếng đặt cờ."""

import math
from pathlib import Path
import numpy as np
import pygame
import pygame.gfxdraw as gfx

SOUND_PATH = Path(__file__).resolve().parent / "assets" / "chess_sound.mp3"


def load_move_sound():
    """Tải âm thanh đặt cờ (chess_sound.mp3) và cắt khoảng lặng đầu file để tiếng phát ngay lập tức."""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        snd = pygame.mixer.Sound(str(SOUND_PATH))
        arr = pygame.sndarray.array(snd)
        env = np.abs(arr).max(axis=1) if arr.ndim > 1 else np.abs(arr)
        idx = np.where(env > env.max() * 0.01)[0]
        if len(idx):
            lo = max(0, int(idx[0]) - 200)
            hi = min(len(arr), int(idx[-1]) + 2000)
            snd = pygame.sndarray.make_sound(np.ascontiguousarray(arr[lo:hi]))
        return snd
    except Exception:  # noqa: BLE001 - môi trường không có audio device vẫn chạy bình thường
        return None


class Fonts:
    """Tạo font một lần sau pygame.init() (SysFont cần pygame đã khởi tạo)."""

    def __init__(self):
        names = "segoeui,inter,arial,helvetica,dejavusans,freesans"
        mk = lambda size, bold=False: pygame.font.SysFont(names, size, bold=bold)
        self.title, self.big = mk(42, True), mk(34, True)
        self.h, self.body, self.bold, self.small = mk(20, True), mk(17), mk(17, True), mk(14)


def disc(surf, color, center, r):
    """Vẽ hình tròn khử răng cưa; nếu là quân cờ nguyên màu RGB (r >= 10) thì vẽ hiệu ứng 3D bóng khối."""
    x, y = int(round(center[0])), int(round(center[1]))
    r = max(1, int(round(r)))
    if len(color) == 4 or r < 10:
        gfx.filled_circle(surf, x, y, r, color)
        gfx.aacircle(surf, x, y, r, color)
        return

    is_dark = (color[0] + color[1] + color[2]) < 380
    if is_dark:
        # Quân Đen: vành ngoài đen sâu, mặt trong ánh than chì + điểm phản quang góc trên trái
        outer = (14, 16, 22)
        inner = (34, 39, 48)
        rim = (68, 76, 92)
        shine = (95, 106, 125)
    else:
        # Quân Trắng: vành ngà ấm, mặt trong trắng sứ + điểm phản quang sáng
        outer = (205, 212, 222)
        inner = (246, 248, 252)
        rim = (255, 255, 255)
        shine = (255, 255, 255)

    gfx.filled_circle(surf, x, y, r, outer)
    gfx.aacircle(surf, x, y, r, outer)

    ir = max(1, r - max(2, r // 8))
    gfx.filled_circle(surf, x, y, ir, inner)
    gfx.aacircle(surf, x, y, ir, rim)

    # Ánh sáng phản chiếu (specular highlight) tạo độ nổi 3D
    if r >= 14:
        hx, hy = x - r // 4, y - r // 4
        hr = max(2, r // 3)
        gfx.filled_circle(surf, hx, hy, hr, shine if is_dark else (255, 255, 255))
        gfx.aacircle(surf, hx, hy, hr, shine if is_dark else (255, 255, 255))
        if is_dark:
            gfx.filled_circle(surf, hx + 2, hy + 2, max(1, hr - 2), inner)


def ellipse_disc(surf, color, center, rx, ry):
    """Vẽ hình elip khử răng cưa (dùng cho quân cờ đang nghiêng khi lật)."""
    x, y = int(round(center[0])), int(round(center[1]))
    rx, ry = max(1, int(round(rx))), max(1, int(round(ry)))
    gfx.filled_ellipse(surf, x, y, rx, ry, color)
    gfx.aaellipse(surf, x, y, rx, ry, color)


def draw_placed_disc(surf, color, ring_color, center, r, progress):
    """Hiệu ứng đặt quân cờ: rơi từ trên xuống + nảy nhẹ + vòng sóng lan tỏa."""
    cx, cy = center
    p = max(0.0, min(1.0, progress))
    ring_r = int(round(r * (0.78 + 0.58 * p)))
    alpha = int(200 * (1.0 - p) ** 1.5)
    if alpha > 5 and ring_r >= 1:
        gfx.aacircle(surf, cx, cy, ring_r, (*ring_color[:3], alpha))
        if ring_r > 1:
            gfx.aacircle(surf, cx, cy, ring_r - 1, (*ring_color[:3], alpha // 2))
    lift = int(round(10 * (1.0 - p) ** 2))
    scale = 1.0 + 0.25 * (1.0 - p) * math.cos(p * math.pi * 1.4)
    cur_r = max(1, int(round(r * scale)))
    shadow_offset = 3 + lift // 2
    disc(surf, (0, 0, 0, int(75 + 25 * p)), (cx + 2 + lift // 3, cy + shadow_offset), cur_r)
    disc(surf, color, (cx, cy - lift), cur_r)


def draw_flipping_disc(surf, old_color, new_color, center, r, progress):
    """Hiệu ứng lật quân cờ 3D: nhấc nhẹ khỏi bàn, xoay trục ngang, hiện cạnh dày 2 màu."""
    cx, cy = center
    p = max(0.0, min(1.0, progress))
    angle = p * math.pi
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    face_color = old_color if p < 0.5 else new_color
    edge_color = new_color if p < 0.5 else old_color

    rx = max(1, int(round(r * abs(cos_a))))
    ry = max(1, int(round(r * (1.0 + 0.10 * sin_a))))
    lift = int(round(6 * sin_a))

    shadow_alpha = int(85 - 25 * sin_a)
    ellipse_disc(surf, (0, 0, 0, shadow_alpha), (cx + 2 + lift // 2, cy + 3 + lift // 2), max(2, rx), ry)

    thickness = max(1, int(round(3 * sin_a)))
    side_dir = 1 if p < 0.5 else -1
    ellipse_disc(surf, edge_color, (cx + side_dir * thickness, cy - lift), rx, ry)
    ellipse_disc(surf, face_color, (cx, cy - lift), rx, ry)
