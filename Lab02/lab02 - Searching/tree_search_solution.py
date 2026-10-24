"""
tree_search_solution.py  --  cài đặt tìm kiếm trên mê cung cho Lab 02 (viết lại, tự chứa).

API tương thích với các notebook 02_Maze_Example / 05_Maze_..._Cycle_checking:
    ts.set_order("NESW") | ts.set_order(random=True)
    ts.best_first_search(maze, strategy="BFS"|"GBFS"|"A*", W=1, debug=False, vis=False)
    ts.DFS(maze, limit=None, frontier_option=1|2|3, check_cycle=True, max_tries=..., vis=False, animation=False, debug_reached=False)
    ts.IDS(maze, max_limit=..., frontier_option=1, max_tries=..., vis=False)
    ts.heuristic = ts.manhattan | ts.euclidean
    ts.show_path(maze, result), ts.show_maze(maze), ts.animate_maze(result), ts.min_index(list)

Mê cung: mảng/list 2 chiều ký tự ('X' tường, 'S' đầu, 'G' đích, ' ' ô trống), vị trí là (hàng, cột).

Ý nghĩa frontier_option của DFS (theo notebook 05):
    3 = cycle checking 1: chỉ kiểm tra trạng thái có nằm trên đường đi hiện tại không (khi lấy khỏi stack)
    2 = cycle checking 2: như 3 + không thêm lại trạng thái đã có trong frontier
    1 = cycle checking 3: như 3 + nếu trạng thái đã có trong frontier thì xóa bản cũ và đưa lên đỉnh stack
"""
import math, random as _random, time, heapq
from collections import deque

# ----------------------------------------------------------------- cấu hình hướng đi
DIRS = {"N": (-1, 0), "E": (0, 1), "S": (1, 0), "W": (0, -1)}
_order = ["N", "E", "S", "W"]
_random_order = False


def set_order(order="NESW", random=False):
    """Thứ tự các hướng khi sinh nút con. random=True: xáo trộn ngẫu nhiên ở mỗi lần mở rộng."""
    global _order, _random_order
    _random_order = bool(random)
    if not random:
        _order = list(order)
        print("Directions are checked in the order", _order)
    else:
        print("Directions are checked in random order")


def _directions():
    if _random_order:
        o = list(DIRS)
        _random.shuffle(o)
        return o
    return _order


# ----------------------------------------------------------------- heuristic
def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def euclidean(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


heuristic = manhattan


def min_index(lst):
    return min(range(len(lst)), key=lambda i: lst[i])


# ----------------------------------------------------------------- tiện ích mê cung
def _cell(maze, p):
    return maze[p[0]][p[1]]


def find_pos(maze, what):
    for r in range(len(maze)):
        for c in range(len(maze[r])):
            if maze[r][c] == what:
                return (r, c)
    return None


def _free(maze, p):
    r, c = p
    return 0 <= r < len(maze) and 0 <= c < len(maze[r]) and maze[r][c] != "X"


class Node:
    def __init__(self, pos, parent, action, cost):
        self.pos, self.parent, self.action, self.cost = pos, parent, action, cost
        self.depth = 0 if parent is None else parent.depth + 1

    def get_path_from_root(self):
        n, out = self, []
        while n is not None:
            out.append(n)
            n = n.parent
        return out[::-1]

    def in_path(self, pos):
        """pos có xuất hiện trên đường đi từ gốc tới nút này không?"""
        n = self
        while n is not None:
            if n.pos == pos:
                return True
            n = n.parent
        return False


def _children(maze, node):
    out = []
    for d in _directions():
        dr, dc = DIRS[d]
        q = (node.pos[0] + dr, node.pos[1] + dc)
        if _free(maze, q):
            out.append(Node(q, node, d, node.cost + 1))
    return out


def _result(node, stats, reached, t0, solved, maze=None):
    nodes = node.get_path_from_root() if (solved and node is not None) else None
    res = dict(
        path=[n.pos for n in nodes] if nodes else None,
        actions=[n.action for n in nodes[1:]] if nodes else None,
        cost=node.cost if nodes else None,
        reached=reached,
        time=time.perf_counter() - t0,
    )
    res.update(stats)
    res["maze"] = maze
    return res


def _new_stats():
    return dict(num_expanded=0, tries=0, max_depth=0, max_frontier=0, frontier_sizes=[],
                expanded_log=[], repeated_expansions=0, frames=[])


# ----------------------------------------------------------------- BFS / GBFS / A*
def best_first_search(maze, strategy="BFS", W=1, debug=False, vis=False, animation=False):
    t0 = time.perf_counter()
    start, goal = find_pos(maze, "S"), find_pos(maze, "G")
    stats = _new_stats()
    root = Node(start, None, None, 0)
    cnt = 0

    def f(n):
        if strategy == "GBFS":
            return heuristic(n.pos, goal)
        if strategy == "A*":
            return n.cost + W * heuristic(n.pos, goal)
        return n.depth  # BFS

    if strategy == "BFS":
        frontier = deque([root])
        push, pop, size = frontier.append, frontier.popleft, lambda: len(frontier)
    else:
        frontier = [(f(root), cnt, root)]
        push = lambda n: heapq.heappush(frontier, (f(n), next_id(), n))
        pop = lambda: heapq.heappop(frontier)[2]
        size = lambda: len(frontier)
    ids = iter(range(1, 10 ** 9))
    next_id = lambda: next(ids)

    reached = {start: root}
    if start == goal:
        return _result(root, stats, reached, t0, True, maze)
    while size():
        stats["max_frontier"] = max(stats["max_frontier"], size())
        stats["frontier_sizes"].append(size())
        node = pop()
        # A*: nút cũ có chi phí tệ hơn nút đã ghi nhận -> bỏ
        if strategy == "A*" and reached.get(node.pos) is not node and reached[node.pos].cost < node.cost:
            continue
        stats["num_expanded"] += 1
        stats["tries"] += 1
        stats["max_depth"] = max(stats["max_depth"], node.depth)
        stats["expanded_log"].append(node.pos)
        for ch in _children(maze, node):
            if ch.pos == goal and strategy in ("BFS",):
                reached[ch.pos] = ch
                return _result(ch, stats, reached, t0, True, maze)
            if ch.pos not in reached or ch.cost < reached[ch.pos].cost:
                reached[ch.pos] = ch
                if ch.pos == goal and strategy != "BFS":
                    pass
                push(ch)
        # với GBFS/A* kiểm tra đích khi lấy ra khỏi hàng đợi
        if strategy != "BFS" and node.pos == goal:
            return _result(node, stats, reached, t0, True, maze)
    return _result(None, stats, reached, t0, False, maze)


# ----------------------------------------------------------------- DFS (có giới hạn độ sâu + 3 kiểu cycle checking)
def DFS(maze, limit=None, max_tries=100000, frontier_option=1, check_cycle=True,
        vis=False, animation=False, debug_reached=False, debug=False):
    """DFS dùng stack (LIFO). Không dùng bảng reached (bộ nhớ ~ O(b*d)).
    limit: giới hạn độ sâu (Depth-Limited DFS). Nút ở độ sâu = limit không được mở rộng.
    max_tries: số lần lấy nút khỏi stack tối đa; vượt quá thì dừng và trả path=None."""
    t0 = time.perf_counter()
    start, goal = find_pos(maze, "S"), find_pos(maze, "G")
    stats = _new_stats()
    stats["cutoff"] = False
    root = Node(start, None, None, 0)
    stack = [root]
    in_frontier = {start: 1}          # đếm số bản ghi của mỗi trạng thái trong stack
    expanded_states = set()
    solved_node = None

    while stack:
        stats["max_frontier"] = max(stats["max_frontier"], len(stack))
        if stats["tries"] >= max_tries:
            break
        node = stack.pop()
        in_frontier[node.pos] -= 1
        if in_frontier[node.pos] == 0:
            del in_frontier[node.pos]
        stats["tries"] += 1
        stats["frontier_sizes"].append(len(stack))
        # --- cycle checking (khi lấy khỏi frontier)
        if check_cycle and node.parent is not None and node.parent.in_path(node.pos):
            continue
        stats["num_expanded"] += 1
        stats["max_depth"] = max(stats["max_depth"], node.depth)
        stats["expanded_log"].append(node.pos)
        if node.pos in expanded_states:
            stats["repeated_expansions"] += 1
        expanded_states.add(node.pos)
        if animation:
            stats["frames"].append((node.pos, [n.pos for n in node.get_path_from_root()],
                                    list(in_frontier)))
        if node.pos == goal:
            solved_node = node
            break
        if limit is not None and node.depth >= limit:
            stats["cutoff"] = True
            continue
        for ch in _children(maze, node):
            if check_cycle and node.in_path(ch.pos):
                if frontier_option != 3:        # option 3 chỉ kiểm tra khi lấy ra
                    continue
            if check_cycle and frontier_option == 2 and ch.pos in in_frontier:
                continue                         # option 2: không thêm lại trạng thái đang có trong frontier
            if check_cycle and frontier_option == 1 and ch.pos in in_frontier:
                # option 3 (của đề): xóa bản cũ, đưa lên đỉnh stack
                stack = [x for x in stack if x.pos != ch.pos]
                in_frontier.pop(ch.pos, None)
            stack.append(ch)
            in_frontier[ch.pos] = in_frontier.get(ch.pos, 0) + 1

    res = _result(solved_node, stats, {} if not debug_reached else {s: None for s in expanded_states},
                  t0, solved_node is not None, maze)
    res["frontier_left"] = len(stack)
    res["distinct_states"] = len(expanded_states)
    res["limit"] = limit
    res["hit_max_tries"] = solved_node is None and stats["tries"] >= max_tries
    res["start"], res["goal"] = start, goal
    res["maze"] = maze
    return res


def IDS(maze, max_limit=10 ** 4, frontier_option=1, check_cycle=True, max_tries=100000, vis=False, debug=False):
    """Iterative Deepening Search: chạy DLS với limit = 0, 1, 2, ... đến khi tìm được lời giải."""
    t0 = time.perf_counter()
    total_expanded, per_iter = 0, []
    for L in range(max_limit + 1):
        r = DFS(maze, limit=L, frontier_option=frontier_option, check_cycle=check_cycle, max_tries=max_tries)
        total_expanded += r["num_expanded"]
        per_iter.append((L, r["num_expanded"], r["max_frontier"], r["path"] is not None))
        if r["path"] is not None or (not r["cutoff"] and not r["hit_max_tries"]):
            r["limit_increases"] = L          # số lần tăng giới hạn (từ 0 lên L)
            r["total_expanded"] = total_expanded
            r["per_iteration"] = per_iter
            r["time"] = time.perf_counter() - t0
            return r
    r["limit_increases"] = max_limit
    r["total_expanded"] = total_expanded
    r["per_iteration"] = per_iter
    return r


# ----------------------------------------------------------------- hiển thị
def _grid(maze, result=None, show_reached=True):
    import numpy as np
    R, C = len(maze), len(maze[0])
    g = np.zeros((R, C))                       # 0 trống
    for r in range(R):
        for c in range(C):
            if maze[r][c] == "X":
                g[r, c] = 1                    # tường
    if result is not None and show_reached:
        for p in result.get("expanded_log", []):
            g[p] = 2                           # đã mở rộng
    if result is not None and result.get("path"):
        for p in result["path"]:
            g[p] = 3                           # đường đi
    return g


def show_maze(maze, result=None, title=None, ax=None):
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    g = _grid(maze, result)
    cmap = ListedColormap(["white", "black", "#cfe8ff", "#ff7f0e"])
    own = ax is None
    if own:
        fig, ax = plt.subplots(figsize=(8, 4))
    ax.imshow(g, cmap=cmap, vmin=0, vmax=3)
    for ch, col in (("S", "blue"), ("G", "green")):
        p = find_pos(maze, ch)
        if p:
            ax.text(p[1], p[0], ch, ha="center", va="center", color=col, fontweight="bold")
    ax.set_xticks([]); ax.set_yticks([])
    if title:
        ax.set_title(title, fontsize=9)
    if own:
        plt.show()


def show_path(maze, result):
    if result["path"] is None:
        print("No solution found.")
    else:
        print("Path length:", len(result["path"]) - 1)
        print("Reached squares:", len(result["reached"]))
        print("Action sequence:", result["actions"])
    show_maze(maze, result)


def animate_maze(result, maze=None):
    """Animation các bước DFS (cần animation=True khi gọi DFS và truyền maze)."""
    import matplotlib.pyplot as plt, matplotlib.animation as animation
    plt.rcParams["animation.html"] = "jshtml"
    maze = maze if maze is not None else result.get("maze")
    frames = result["frames"]
    if maze is None or not frames:
        raise ValueError("Cần gọi ts.DFS(maze, ..., animation=True) trước khi animate_maze(result)")
    fig, ax = plt.subplots(figsize=(8, 4))

    def draw(i):
        ax.clear()
        pos, path, fr = frames[i]
        g = _grid(maze)
        for p in fr: g[p] = 2
        for p in path: g[p] = 3
        from matplotlib.colors import ListedColormap
        ax.imshow(g, cmap=ListedColormap(["white", "black", "#ffb347", "#d62728"]), vmin=0, vmax=3)
        ax.set_title(f"bước {i+1}/{len(frames)} | frontier={len(fr)}", fontsize=9)
        ax.set_xticks([]); ax.set_yticks([])

    anim = animation.FuncAnimation(fig, draw, frames=len(frames), interval=60)
    plt.close(fig)
    return anim