"""Chạy các thí nghiệm bổ sung cho mục 4.7. Xem README_chay_thi_nghiem.md.

  python run_exp.py e1 --n 20 --workers 4
  python run_exp.py e2 --workers 4
  python run_exp.py e3 --n 25 --workers 4
  python run_exp.py e4 --n 25 --workers 4
Kết quả ghi vào exp_out/<exp>.jsonl (mỗi dòng = 1 ván). Chạy lại cùng lệnh sẽ bỏ qua ván đã xong.
"""
import argparse, json, os, sys
from eval.tournament import play_game, random_opening  
from agents.registry import build_agent, load_agent_specs
from multiprocessing import Pool

OUT = 'exp_out'
E2_LOG = 'results/logs/round_robin_v2/games.jsonl'
SPECS = load_agent_specs('configs/agents.yaml')

def mk(name, seed, **over):
    """Dựng tác tử `name` theo configs/agents.yaml, ghi đè một số tham số bằng **over."""
    spec = json.loads(json.dumps(SPECS[name]))
    spec['params'].update(over)
    return build_agent(spec, seed, name)


def tasks_e1(n):
    cfgs = [('rollout=heuristic,ABd1', {}, 1), ('rollout=heuristic,ABd2', {}, 2),
            ('rollout=heuristic,ABd4', {}, 4), ('rollout=random,ABd4', {'rollout_policy': 'random'}, 4)]
    for i in range(n):
        for tag, mo, d in cfgs:
            for mb in (True, False):
                yield dict(exp='e1', key=f'{tag}|{i}|{mb}', tag=tag, i=i, mcts_black=mb, mcts_over=mo, ab_depth=d,
                           opening_seed=5000 + i)

def tasks_e2(n):
    seen = {}
    for l in open(E2_LOG, encoding='utf8'):
        if not l.strip(): continue
        r = json.loads(l)
        if r['game_id'].startswith('default_config|heuristic|mcts|'):
            seen[r['game_id']] = r
    for gid, r in sorted(seen.items()):
        yield dict(exp='e2', key=gid, tag='heur_noswitch', gid=gid, opening=r['opening'],
                   heur_black=(r['black'] == 'heuristic'), base_result_black=r['result_black'],
                   base_b=r['black_discs'], base_w=r['white_discs'])

def tasks_e3(n):   # Alpha-Beta độ sâu cố định 2/4/6 đấu MCTS mặc định
    for i in range(n):
        for d in (2, 4, 6):
            for ab_black in (True, False):
                yield dict(exp='e3', key=f'ABd{d}|{i}|{ab_black}', tag=f'ABd{d}', i=i, ab_black=ab_black,
                           ab_depth=d, opening_seed=9000 + i)

def tasks_e4(n):   # MCTS 250/500/1000/2000 mô phỏng đấu Alpha-Beta độ sâu 4
    for i in range(n):
        for s in (250, 500, 1000, 2000):
            for mb in (True, False):
                yield dict(exp='e4', key=f'sims{s}|{i}|{mb}', tag=f'sims{s}', i=i, mcts_black=mb, sims=s,
                           opening_seed=9500 + i)

def run_one(t):
    e = t['exp']
    if e == 'e1':
        m = mk('mcts', t['i'] * 7 + 1, **t['mcts_over']); a = mk('alphabeta', t['i'] * 7 + 2, depth=t['ab_depth'])
        op = random_opening(t['opening_seed'], 4); black, white = (m, a) if t['mcts_black'] else (a, m)
    elif e == 'e2':
        h = mk('heuristic', 3, endgame_empties=0); m = mk('mcts', 4)
        op = [tuple(x) for x in t['opening']]; black, white = (h, m) if t['heur_black'] else (m, h)
    elif e == 'e3':
        a = mk('alphabeta', t['i'] * 7 + 2, depth=t['ab_depth']); m = mk('mcts', t['i'] * 7 + 1)
        op = random_opening(t['opening_seed'], 4); black, white = (a, m) if t['ab_black'] else (m, a)
    else:
        m = mk('mcts', t['i'] * 7 + 1, simulations=t['sims']); a = mk('alphabeta', t['i'] * 7 + 2, depth=4)
        op = random_opening(t['opening_seed'], 4); black, white = (m, a) if t['mcts_black'] else (a, m)
    r = play_game(black, white, opening=op)
    out = dict(t)
    out.update(result_black=r['result_black'], b=r['black_discs'], w=r['white_discs'], opening=r['opening'],
               moves=[dict(p=x['p'], a=x['a'], stats=x.get('stats')) for x in r['move_log']])
    return out

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('exp', choices=['e1', 'e2', 'e3', 'e4'])
    ap.add_argument('--n', type=int, default=20, help='số khai cuộc (mỗi khai cuộc đấu cả hai màu)')
    ap.add_argument('--workers', type=int, default=1)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    path = f'{OUT}/{a.exp}.jsonl'
    done = set()
    if os.path.exists(path):
        done = {json.loads(l)['key'] for l in open(path, encoding='utf8') if l.strip()}
    todo = [t for t in {'e1': tasks_e1, 'e2': tasks_e2, 'e3': tasks_e3, 'e4': tasks_e4}[a.exp](a.n) if t['key'] not in done]
    print(f'{a.exp}: còn {len(todo)} ván cần chạy (đã xong {len(done)})', flush=True)
    with open(path, 'a', encoding='utf8') as f, Pool(a.workers) as pool:
        for k, r in enumerate(pool.imap_unordered(run_one, todo), 1):
            f.write(json.dumps(r) + '\n'); f.flush()
            if k % 10 == 0 or k == len(todo): print(f'  {k}/{len(todo)}', flush=True)
    print('XONG', path)
