"""Test phân tích ván: chạy trên log nhỏ sinh bằng chính engine/giải đấu (heuristic vs random, tất định theo seed)."""

import json

from agents.heuristic_agent import HeuristicAgent
from agents.random_agent import RandomAgent
from eval import game_analysis as ga
from eval.tournament import play_game


def _tiny_run(tmp_path, pairs=3):
    lines = []
    opening = [(2, 3), (2, 2), (3, 2), (2, 4)]
    for pair in range(pairs):
        for a_black in (True, False):
            a, b = HeuristicAgent(seed=pair, config_file=None), RandomAgent(seed=pair)
            black, white = (a, b) if a_black else (b, a)
            rec = play_game(black, white, None, None, opening=opening)
            rec.update(game_id=f"m|heuristic|random|s100|p{pair}|{'AB' if a_black else 'BA'}", mode="m", a="heuristic",
                       b="random", a_is_black=a_black, black="heuristic" if a_black else "random",
                       white="random" if a_black else "heuristic", seed=100, pair=pair)
            lines.append(json.dumps(rec))
    (tmp_path / "games.jsonl").write_text("\n".join(lines), encoding="utf-8")


def test_replay_matches_logged_final_score(tmp_path):
    _tiny_run(tmp_path, pairs=1)
    rec = ga.load_games(tmp_path)[0]
    moves = ga.replay(rec)
    assert len(moves) == len(rec["move_log"])
    assert moves[-1]["disc_diff_black"] == rec["black_discs"] - rec["white_discs"]


def test_analyze_writes_all_outputs_and_counts_every_game(tmp_path):
    _tiny_run(tmp_path, pairs=3)
    r = ga.analyze(tmp_path, tmp_path / "out", focus=["heuristic", "random"])
    assert r["n_games"] == 6
    row = r["summary"].iloc[0]
    assert row["games"] == 6 and row["a_wins"] + row["draws"] + row["a_losses"] == 6
    assert row["pairs"] == 3 and row["pairs_a_sweep"] + row["pairs_b_sweep"] + row["pairs_split"] == 3
    for name in ("matchup_summary.csv", "move_stats.csv", "corner_vs_result.csv", "selected_games.md",
                 "fig_matchup_scores.png", "fig_cost_by_phase.png", "fig_corner_behaviour.png"):
        assert (tmp_path / "out" / name).exists(), name


def test_selection_rule_is_deterministic(tmp_path):
    _tiny_run(tmp_path, pairs=3)
    games = ga.build_tables(ga.load_games(tmp_path))["games"]
    a = ga.select_games(games, None)
    b = ga.select_games(games, None)
    assert a.equals(b)
    assert {"closest", "longest", "random1", "random2"} <= set(a["rule"])
