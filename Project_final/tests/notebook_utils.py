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


def run_notebook(name, quick=False, only_tags=None, namespace=None, replace=None):
    """Chạy tuần tự các ô code trong một namespace chung. only_tags=None: chạy mọi ô; ngược lại chỉ ô có tag thuộc tập này.

    replace: dict {đoạn mã cũ: đoạn mã mới} áp lên mã nguồn các ô trước khi chạy (vd đổi thư mục dữ liệu sang thư mục tạm).
    Nếu một đoạn cũ không xuất hiện ở ô nào thì báo lỗi, để notebook đổi code mà test không âm thầm bỏ qua việc thay.
    """
    ns = namespace if namespace is not None else {"__name__": "__notebook__"}
    pending = set(replace or {})
    old = Path.cwd()
    os.chdir(ROOT)
    try:
        for i, (tags, src) in enumerate(code_cells(name)):
            if only_tags is not None and not (set(tags) & set(only_tags)):
                continue
            src = src.replace("QUICK_TEST = False", f"QUICK_TEST = {quick}")
            for old_src, new_src in (replace or {}).items():
                if old_src in src:
                    src = src.replace(old_src, new_src)
                    pending.discard(old_src)
            exec(compile(src, f"{name}[cell {i}]", "exec"), ns)
    finally:
        os.chdir(old)
    if pending:
        raise AssertionError(f"{name}: không tìm thấy đoạn mã cần thay: {sorted(pending)}")
    return ns


def load_defs(name):
    """Namespace chỉ gồm import + hàm của notebook (không chạy phần huấn luyện)."""
    return run_notebook(name, only_tags={"setup", "defs"})