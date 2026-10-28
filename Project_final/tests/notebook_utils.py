"""Chạy code trong notebook từ test (không cần Jupyter kernel).

Quy ước của các notebook 04-06: ô gắn tag `setup` (import, đường dẫn) và `defs` (chỉ định nghĩa hàm, không có tác dụng phụ)
được test đơn vị trực tiếp; ô còn lại chạy được ở chế độ QUICK_TEST (dữ liệu/số vòng rất nhỏ, ghi ra thư mục tạm).
"""

import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # không mở cửa sổ khi plt.show()

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS = ROOT / "notebooks"


def code_cells(name):
    nb = json.load(open(NOTEBOOKS / name, encoding="utf-8"))
    return [(c.get("metadata", {}).get("tags", []), "".join(c["source"])) for c in nb["cells"] if c["cell_type"] == "code"]


def run_notebook(name, quick=False, only_tags=None, namespace=None):
    """Chạy tuần tự các ô code trong một namespace chung. only_tags=None: chạy mọi ô; ngược lại chỉ ô có tag thuộc tập này."""
    ns = namespace if namespace is not None else {"__name__": "__notebook__"}
    old = Path.cwd()
    os.chdir(ROOT)
    try:
        for i, (tags, src) in enumerate(code_cells(name)):
            if only_tags is not None and not (set(tags) & set(only_tags)):
                continue
            src = src.replace("QUICK_TEST = False", f"QUICK_TEST = {quick}")
            exec(compile(src, f"{name}[cell {i}]", "exec"), ns)
    finally:
        os.chdir(old)
    return ns


def load_defs(name):
    """Namespace chỉ gồm import + hàm của notebook (không chạy phần huấn luyện)."""
    return run_notebook(name, only_tags={"setup", "defs"})
