"""Hàm vẽ và âm thanh dùng chung: font, quân cờ (tĩnh, đặt quân, lật quân) và tiếng đặt cờ."""

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
        names = "segoeui,arial,helvetica,dejavusans,freesans"
        mk = lambda size, bold=False: pygame.font.SysFont(names, size, bold=bold)
        self.title, self.big = mk(48, True), mk(38, True)
        self.h, self.body, self.bold, self.small = mk(22, True), mk(19), mk(19, True), mk(15)


def disc(surf, color, center, r):
    """Vẽ hình tròn khử răng cưa (quân cờ, chấm nước hợp lệ, chấm nước vừa đi)."""
    x, y = center
    r = max(1, int(round(r)))
    gfx.filled_circle(surf, x, y, r, color)
    gfx.aacircle(surf, x, y, r, color)


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
    # Vòng sóng lan tỏa quanh ô vừa đặt
    ring_r = int(round(r * (0.75 + 0.55 * p)))
    alpha = int(190 * (1.0 - p) ** 1.5)
    if alpha > 5 and ring_r >= 1:
        gfx.aacircle(surf, cx, cy, ring_r, (*ring_color[:3], alpha))
        if ring_r > 1:
            gfx.aacircle(surf, cx, cy, ring_r - 1, (*ring_color[:3], alpha // 2))
    # Quân cờ rơi nhẹ từ trên xuống kèm hiệu ứng thu phóng nảy (overshoot nhẹ)
    lift = int(round(10 * (1.0 - p) ** 2))
    scale = 1.0 + 0.28 * (1.0 - p) * math.cos(p * math.pi * 1.4)
    cur_r = max(1, int(round(r * scale)))
    shadow_offset = 3 + lift // 2
    disc(surf, (0, 0, 0, int(65 + 25 * p)), (cx + 2 + lift // 3, cy + shadow_offset), cur_r)
    disc(surf, color, (cx, cy - lift), cur_r)


def draw_flipping_disc(surf, old_color, new_color, center, r, progress):
    """Hiệu ứng lật quân cờ 3D: nhấc nhẹ khỏi bàn, xoay trục ngang, hiện cạnh dày 2 màu."""
    cx, cy = center
    p = max(0.0, min(1.0, progress))
    angle = p * math.pi
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    # Nửa đầu (p < 0.5) nhìn thấy mặt màu cũ, nửa sau (p >= 0.5) nhìn thấy mặt màu mới
    face_color = old_color if p < 0.5 else new_color
    edge_color = new_color if p < 0.5 else old_color

    rx = max(1, int(round(r * abs(cos_a))))
    ry = max(1, int(round(r * (1.0 + 0.10 * sin_a))))
    lift = int(round(6 * sin_a))

    # Bóng đổ dưới mặt bàn (co giãn theo góc nghiêng của quân cờ)
    shadow_alpha = int(80 - 25 * sin_a)
    ellipse_disc(surf, (0, 0, 0, shadow_alpha), (cx + 2 + lift // 2, cy + 3 + lift // 2), max(2, rx), ry)

    # Cạnh dày 3D của quân cờ khi đang nghiêng
    thickness = max(1, int(round(3 * sin_a)))
    side_dir = 1 if p < 0.5 else -1
    ellipse_disc(surf, edge_color, (cx + side_dir * thickness, cy - lift), rx, ry)

    # Mặt chính của quân cờ
    ellipse_disc(surf, face_color, (cx, cy - lift), rx, ry)
