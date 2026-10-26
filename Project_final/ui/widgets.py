"""Thành phần giao diện tái sử dụng: Button và Selector (chọn một mục trong danh sách bằng mũi tên)."""

import pygame

from ui.config import (C_ACCENT, C_BTN, C_BTN_HOVER, C_BTN_OFF, C_CARD, C_DIM, C_ERR, C_TEXT)


class Button:
    def __init__(self, rect, label, action, selected=False, enabled=True, sub=""):
        self.rect = pygame.Rect(rect)
        self.label, self.action, self.selected, self.enabled, self.sub = label, action, selected, enabled, sub

    def draw(self, screen, fonts, mouse):
        if not self.enabled:
            bg, fg = C_BTN_OFF, C_DIM
        elif self.selected:
            bg, fg = C_ACCENT, (255, 255, 255)
        elif self.rect.collidepoint(mouse):
            bg, fg = C_BTN_HOVER, C_TEXT
        else:
            bg, fg = C_BTN, C_TEXT
        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        font = fonts.bold if self.selected else fonts.body
        dy = -9 if self.sub else 0
        t = font.render(self.label, True, fg)
        screen.blit(t, t.get_rect(center=(self.rect.centerx, self.rect.centery + dy)))
        if self.sub:
            s = fonts.small.render(self.sub, True, C_DIM)
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
        return [Button((x, y, 44, h), "<", lambda: self.step(-1)),
                Button((x + w - 44, y, 44, h), ">", lambda: self.step(+1))]

    def draw(self, screen, fonts, rect):
        x, y, w, h = rect
        box = pygame.Rect(x + 52, y, w - 104, h)
        pygame.draw.rect(screen, C_CARD, box, border_radius=8)
        p = self.current
        name = fonts.bold.render(p.label, True, C_TEXT if p.available else C_DIM)
        screen.blit(name, name.get_rect(center=(box.centerx, box.y + h // 2 - 12)))
        if p.available:
            text, color = p.summary or "default parameters", C_DIM
        else:
            text, color = f"not available: {p.reason}", C_ERR
        sub = fonts.small.render(text[:70], True, color)
        screen.blit(sub, sub.get_rect(center=(box.centerx, box.y + h // 2 + 14)))
        count = fonts.small.render(f"{self.index + 1}/{len(self.items)}", True, C_DIM)
        screen.blit(count, (box.right - count.get_width() - 8, box.y + 6))
