"""Hàm vẽ dùng chung: font và quân cờ."""

import pygame
import pygame.gfxdraw as gfx


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
    gfx.filled_circle(surf, x, y, r, color)
    gfx.aacircle(surf, x, y, r, color)
