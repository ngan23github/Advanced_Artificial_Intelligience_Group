"""Luật của HeuristicAgent: mô tả một nước đi bằng các con số, đổi sang giá trị từng luật, ghép thành khóa so sánh.

heuristic_agent.py chỉ lo chọn nước; file này lo "luật là gì". Thêm luật mới: khai báo tên trong
configs/constants.RULE_NAMES, thêm 1 dòng vào rule_values() ở đây.
"""

from agents import board_features as bf
from configs.constants import CORNERS, DANGER_C, DANGER_X, DEFAULT_PRIORITIES, RULE_NAMES
from othello.rules import apply_move


def normalize_priorities(priorities=None) -> list:
    """List tên luật (từ yaml) -> list hợp lệ. Tên sai hoặc trùng -> ValueError; None -> thứ tự mặc định."""
    pr = list(DEFAULT_PRIORITIES if priorities is None else priorities)
    unknown = [r for r in pr if r not in RULE_NAMES]
    if unknown:
        raise ValueError(f"Luật không biết: {unknown}. Hợp lệ: {list(RULE_NAMES)}")
    if len(set(pr)) != len(pr):
        raise ValueError(f"priorities có luật bị trùng: {pr}")
    return pr


def describe_move(board, me: int, action) -> dict:
    """Các con số của nước `action` của `me` (trên board TRƯỚC khi đi): góc, ô nguy hiểm, mobility, số quân, kết cục."""
    after = apply_move(board, me, action[0], action[1])
    mine_moves, opp_moves = bf.mobility_counts(after, me)
    mine_discs, opp_discs = bf.disc_counts(after, me)
    outcome = 0  # +1 thắng ngay, -1 thua ngay (nước này kết thúc ván), 0 chưa kết thúc / hòa
    if mine_moves == 0 and opp_moves == 0:
        outcome = (mine_discs > opp_discs) - (mine_discs < opp_discs)
    return {"corner": int(action in CORNERS), "danger": bf.square_danger(board, action),
            "mobility": mine_moves - opp_moves, "discs": mine_discs, "outcome": outcome}


def rule_values(info: dict) -> dict:
    """Giá trị của từng luật cho 1 nước đi (càng lớn càng tốt)."""
    return {
        "win_now": info["outcome"],
        "take_corner": info["corner"],
        "avoid_x_square": -int(info["danger"] == DANGER_X),
        "avoid_c_square": -int(info["danger"] == DANGER_C),
        "maximize_mobility": info["mobility"],
        "maximize_discs": info["discs"],
    }


def rule_key(info: dict, order) -> tuple:
    """Khóa so sánh theo thứ tự ưu tiên `order` (so từ trái sang phải; luật trước thắng tuyệt đối luật sau)."""
    vals = rule_values(info)
    return tuple(vals[r] for r in order)
