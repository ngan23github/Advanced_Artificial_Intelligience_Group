"""Thành phần giao diện tái sử dụng: Button và Selector (chọn một mục trong danh sách bằng mũi tên)."""

import pygame
import pygame.gfxdraw as gfx

from ui.config import (C_ACCENT, C_ACCENT_GLOW, C_BORDER, C_BTN, C_BTN_HOVER, C_BTN_OFF,
                       C_CARD, C_CARD_HI, C_DIM, C_ERR, C_TEXT)


def _draw_arrow_icon(screen, center, direction, color):
    """Vẽ mũi tên tam giác khử răng cưa sắc nét (tránh lỗi font thiếu ký tự Unicode)."""
    cx, cy = center
    size = 7
    if direction < 0:
        pts = [(cx - size, cy), (cx + size - 2, cy - size), (cx + size - 2, cy + size)]
    else:
        pts = [(cx + size, cy), (cx - size + 2, cy - size), (cx - size + 2, cy + size)]
    gfx.filled_trigon(screen, pts[0][0], pts[0][1], pts[1][0], pts[1][1], pts[2][0], pts[2][1], color)
    gfx.aatrigon(screen, pts[0][0], pts[0][1], pts[1][0], pts[1][1], pts[2][0], pts[2][1], color)


class Button:
    def __init__(self, rect, label, action, selected=False, enabled=True, sub="", primary=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.selected = selected
        self.enabled = enabled
        self.sub = sub
        self.primary = primary

    def draw(self, screen, fonts, mouse):
        hovered = self.enabled and self.rect.collidepoint(mouse)
        if not self.enabled:
            bg, fg, border = C_BTN_OFF, C_DIM, (38, 46, 60)
        elif self.selected:
            bg = (20, 155, 108) if not hovered else C_ACCENT
            fg = (255, 255, 255)
            border = C_ACCENT_GLOW
        elif self.primary:
            bg = C_ACCENT if not hovered else (24, 202, 142)
            fg = (255, 255, 255)
            border = C_ACCENT_GLOW
        elif hovered:
            bg, fg, border = C_BTN_HOVER, C_TEXT, (82, 100, 130)
        else:
            bg, fg, border = C_BTN, C_TEXT, C_BORDER

        # Bóng đổ nhẹ phía dưới nút
        shadow_rect = self.rect.move(0, 2)
        pygame.draw.rect(screen, (8, 11, 16), shadow_rect, border_radius=10)
        pygame.draw.rect(screen, bg, self.rect, border_radius=10)
        pygame.draw.rect(screen, border, self.rect, width=2 if (self.selected or self.primary) else 1, border_radius=10)

        if self.label in ("<", ">"):
            _draw_arrow_icon(screen, self.rect.center, -1 if self.label == "<" else 1, fg)
            return

        font = fonts.bold if (self.selected or self.primary) else fonts.body
        dy = -9 if self.sub else 0
        t = font.render(self.label, True, fg)
        screen.blit(t, t.get_rect(center=(self.rect.centerx, self.rect.centery + dy)))
        if self.sub:
            s = fonts.small.render(self.sub, True, (220, 245, 235) if self.selected else C_DIM)
            screen.blit(s, s.get_rect(center=(self.rect.centerx, self.rect.centery + 12)))


class Selector:
    """Hộp chọn có mũi tên trái/phải để duyệt danh sách agent (không giới hạn số lượng, không tràn màn hình).

    `items` là danh sách `agents.registry.Preset`. Dưới tên agent hiện tóm tắt tham số, hoặc lý do không dùng được.
    """

    def __init__(self, items, index=0):
        self.items = items
        self.index = index if 0 <= index < len(items) else 0

    @property
    def current(self):
        return self.items[self.index]

    def step(self, delta):
        self.index = (self.index + delta) % len(self.items)

    def buttons(self, rect):
        x, y, w, h = rect
        return [Button((x, y, 48, h), "<", lambda: self.step(-1)),
                Button((x + w - 48, y, 48, h), ">", lambda: self.step(+1))]

    def draw(self, screen, fonts, rect):
        x, y, w, h = rect
        box = pygame.Rect(x + 56, y, w - 112, h)
        pygame.draw.rect(screen, (8, 11, 16), box.move(0, 2), border_radius=10)
        pygame.draw.rect(screen, C_CARD_HI, box, border_radius=10)
        p = self.current
        border_col = C_BORDER if p.available else C_ERR
        pygame.draw.rect(screen, border_col, box, width=1, border_radius=10)

        name = fonts.bold.render(p.label, True, C_TEXT if p.available else C_DIM)
        screen.blit(name, name.get_rect(center=(box.centerx, box.y + h // 2 - 11)))
        if p.available:
            text, color = p.summary or "default configuration", C_DIM
        else:
            text, color = f"unavailable: {p.reason}", C_ERR
        sub = fonts.small.render(text[:68], True, color)
        screen.blit(sub, sub.get_rect(center=(box.centerx, box.y + h // 2 + 13)))

        # Huy hiệu số thứ tự góc phải
        badge_txt = fonts.small.render(f"{self.index + 1} / {len(self.items)}", True, C_DIM)
        badge_rect = badge_txt.get_rect(topright=(box.right - 12, box.y + 7))
        pygame.draw.rect(screen, C_CARD, badge_rect.inflate(10, 4), border_radius=6)
        screen.blit(badge_txt, badge_rect)
