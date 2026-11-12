"""Cac tac tu Tic-Tac-Toe dung cho bang tong hop (lay nguyen code tu cac notebook cua lab)."""
import math, time
import numpy as np
from tictactoe import empty_board, actions, result, utility, other, check_board, random_player

# ---------- AND-OR ----------
def _results(state, action, player):
    opponent = other(player); state = state.copy(); state[action] = player
    o_actions = actions(state)
    if len(o_actions) < 1: return [state]
    out = []
    for o_a in o_actions:
        s = state.copy(); s[o_a] = opponent; out.append(s)
    return out

def _or_search(state, player, draw_is_win):
    u = utility(state, player)
    if u == -1 or (not draw_is_win and u == 0): return None
    for action in actions(state):
        plan = _and_search(_results(state, action, player), player, draw_is_win)
        if plan is not None: return [action, plan]
    return None

def _and_search(states, player, draw_is_win):
    plans = []
    for s in states:
        u = utility(s, player)
        if u == 1: return "win"
        if draw_is_win and u == 0: return "draw"
        plan = _or_search(s, player, draw_is_win)
        if plan is None: return None
        plans.append(['if', s, 'then', plan])
    return plans

def and_or_player(board, player='x'):
    plan = _or_search(board, player, True)
    return np.random.choice(actions(board)) if plan is None else plan[0]

# ---------- Alpha-Beta (co move ordering o nuoc dau) ----------
PRIORITY = [1,0,1, 0,2,0, 1,0,1]
def ordered_actions(board):
    acts = actions(board)
    return sorted(acts, key=lambda a: -PRIORITY[a])

def _max_ab(state, player, alpha, beta, depth, cutoff, evalf):
    v0, term = evalf(state, player)
    if term or (cutoff is not None and depth >= cutoff): return v0, None
    v, move = -math.inf, None
    for a in ordered_actions(state):
        v2, _ = _min_ab(result(state, player, a), player, alpha, beta, depth+1, cutoff, evalf)
        if v2 > v: v, move = v2, a; alpha = max(alpha, v)
        if v >= beta: return v, move
    return v, move

def _min_ab(state, player, alpha, beta, depth, cutoff, evalf):
    v0, term = evalf(state, player)
    if term or (cutoff is not None and depth >= cutoff): return v0, None
    v, move = math.inf, None
    for a in ordered_actions(state):
        v2, _ = _max_ab(result(state, other(player), a), player, alpha, beta, depth+1, cutoff, evalf)
        if v2 < v: v, move = v2, a; beta = min(beta, v)
        if v <= alpha: return v, move
    return v, move

def eval_exact(state, player):
    u = utility(state, player)
    return (u, True) if u is not None else (0, False)

def eval_fun(state, player='x'):
    u = utility(state, player)
    if u is not None: return u, True
    score = 0
    board = np.array(state).reshape((3,3))
    diagonals = np.array([[board[i][i] for i in range(3)], [board[i][2-i] for i in range(3)]])
    for a_board in [board, np.transpose(board), diagonals]:
        for row in a_board:
            if sum(row == player) == 2 and any(row == ' '): score += .4
            if sum(row == other(player)) == 2 and any(row == ' '): score -= .4
    return score, False

_cache = {}
def alpha_beta_player(board, player='x'):
    key = tuple(board) + (player,)
    if key in _cache: return _cache[key]   # tran bo nho dem de khong lap lai nuoc dau o ban rong (xac dinh)
    v, m = _max_ab(board, player, -math.inf, math.inf, 0, None, eval_exact)
    _cache[key] = m
    return m

def alpha_beta_player_nocache(board, player='x'):
    return _max_ab(board, player, -math.inf, math.inf, 0, None, eval_exact)[1]

def heuristic2_player(board, player='x'):
    return _max_ab(board, player, -math.inf, math.inf, 0, 2, eval_fun)[1]
def heuristic4_player(board, player='x'):
    return _max_ab(board, player, -math.inf, math.inf, 0, 4, eval_fun)[1]

# ---------- Pure Monte Carlo ----------
def playout(state, action, player='x'):
    state = result(state, player, action); cur = other(player)
    while True:
        u = utility(state, player)
        if u is not None: return u
        state = result(state, cur, np.random.choice(actions(state))); cur = other(cur)

def pmcs(board, N=100, player='x'):
    acts = actions(board); n = max(1, math.floor(N/len(acts)))
    ps = {i: np.mean([playout(board, i, player) for _ in range(n)]) for i in acts}
    return max(ps, key=ps.get)

def make_pmcs(N): return lambda board, player='x': pmcs(board, N, player)

# ---------- UCB1 (UCT do sau 1) ----------
def uct_depth1(board, N=100, player='x', return_stats=False):
    C = math.sqrt(2)
    acts = actions(board)
    u = [0]*len(acts); n = [0]*len(acts); n_parent = 0
    ucb = [math.inf]*len(acts)
    for _ in range(N):
        i = ucb.index(max(ucb))
        p = playout(board, acts[i], player)
        u[i] += p; n[i] += 1; n_parent += 1
        for j in range(len(acts)):
            if n[j] > 0: ucb[j] = u[j]/n[j] + C*math.sqrt(math.log(n_parent)/n[j])
    action = acts[n.index(max(n))]
    if return_stats: return action, acts, u, n, ucb
    return action

def make_ucb1(N): return lambda board, player='x': uct_depth1(board, N, player)

# ---------- do thoi gian + choi ----------
class Timed:
    def __init__(self, f): self.f, self.t, self.k = f, 0.0, 0
    def __call__(self, board, player='x'):
        t0 = time.perf_counter(); a = self.f(board, player)
        self.t += time.perf_counter()-t0; self.k += 1
        return a
    @property
    def avg_ms(self): return 1000*self.t/max(1, self.k)

def play_one(x, o):
    board = empty_board()
    while True:
        board = result(board, 'x', x(board, 'x'))
        w = check_board(board)
        if w != 'n': return w
        board = result(board, 'o', o(board, 'o'))
        w = check_board(board)
        if w != 'n': return w

def play_timed(agent, opponent, N, agent_side='x'):
    """agent choi N van voi opponent. Tra ve (thang, hoa, thua, ms/nuoc di cua agent)."""
    ta = Timed(agent); res = {'x':0,'o':0,'d':0}
    for _ in range(N):
        w = play_one(ta, opponent) if agent_side=='x' else play_one(opponent, ta)
        res[w] += 1
    win = res[agent_side]; loss = res[other(agent_side)]; draw = res['d']
    return win, draw, loss, ta.avg_ms
