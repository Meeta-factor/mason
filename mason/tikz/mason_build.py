import csv
import os
import re
from collections import defaultdict


def fmt_node_label(name: str) -> str:
    """
    把节点名转成更适合 LaTeX 显示的形式。
    例如:
        R1 -> R_1
        n2 -> n_2
        C1 -> C_1
        D  -> D
    """
    m = re.fullmatch(r"([A-Za-z]+)(\d+)", name)
    if m:
        head, num = m.groups()
        return rf"${head}_{num}$"
    return rf"${name}$"


def fmt_gain(gain: str) -> str:
    """
    把 gain 字符串转成数学模式标签。
    例如:
        G1     -> $G_1$
        -a11   -> $-a_{11}$
        sigma  -> $\\sigma$
        1      -> $1$
    """
    gain = gain.strip()

    special = {
        "1": r"$1$",
        "sigma": r"$\sigma$",
        "Sigma": r"$\Sigma$",
    }
    if gain in special:
        return special[gain]

    # G1 -> G_1, a11 -> a_{11}, -a12 -> -a_{12}
    m = re.fullmatch(r"(-?)([A-Za-z]+)(\d+)", gain)
    if m:
        sign, head, num = m.groups()
        if len(num) == 1:
            return rf"${sign}{head}_{num}$"
        return rf"${sign}{head}_{{{num}}}$"

    return rf"${gain}$"


def node_group(name: str) -> str:
    """
    简单分组：
    n* -> 上支路
    m* -> 下支路
    其他 -> 特殊点
    """
    if name.startswith("n"):
        return "n"
    if name.startswith("m"):
        return "m"
    return "other"


def node_index(name: str) -> int | None:
    m = re.fullmatch(r"[A-Za-z]+(\d+)", name)
    return int(m.group(1)) if m else None


def is_disturbance_edge(s: str, t: str) -> bool:
    return s == "D"


def is_same_branch_feedback(s: str, t: str) -> bool:
    """
    同一支路、且编号从大到小，视作反馈。
    n3 -> n1, m3 -> m1 这种。
    """
    gs, gt = node_group(s), node_group(t)
    if gs != gt or gs not in {"n", "m"}:
        return False
    i, j = node_index(s), node_index(t)
    return i is not None and j is not None and i > j


def is_cross_coupling(s: str, t: str) -> bool:
    gs, gt = node_group(s), node_group(t)
    return (gs == "n" and gt == "m") or (gs == "m" and gt == "n")


def is_forward_edge(s: str, t: str) -> bool:
    """
    同支路、编号递增，视作主通道边。
    """
    gs, gt = node_group(s), node_group(t)
    if gs != gt or gs not in {"n", "m"}:
        return False
    i, j = node_index(s), node_index(t)
    return i is not None and j is not None and i < j


def parse_node(name: str):
    """
    返回 (prefix, index)
    例如:
        n3 -> ("n", 3)
        R1 -> ("R", 1)
        D  -> ("D", None)
    """
    m = re.fullmatch(r"([A-Za-z]+)(\d+)", name)
    if m:
        return m.group(1), int(m.group(2))
    return name, None


def collect_nodes(edges):
    nodes = set()
    for s, t, _ in edges:
        nodes.add(s)
        nodes.add(t)
    return nodes


def auto_positions(edges, x_gap=2.0, y_gap=3.0):
    nodes = collect_nodes(edges)

    groups = defaultdict(list)
    others = []

    for node in nodes:
        prefix, idx = parse_node(node)

        if prefix in {"R", "n", "C", "m", "D"}:
            groups[prefix].append((node, idx))
        else:
            others.append(node)

    # 每组内部按编号排序，没有编号的放最后
    for k in groups:
        groups[k].sort(key=lambda x: (x[1] is None, x[1]))

    positions = {}

    # 先处理 n 支路：R -> n -> C
    n_y = y_gap
    m_y = 0.0
    d_y = -2.0

    # ---- 上支路 ----
    n_chain = [node for node, _ in groups["n"]]
    r_nodes = [node for node, _ in groups["R"]]
    c_nodes = [node for node, _ in groups["C"]]

    # 简单策略：
    # R1 放在 n1 左边
    # C1 放在 n链右边
    n_x_start = 2.0

    for i, node in enumerate(n_chain):
        positions[node] = (n_x_start + i * x_gap, n_y)

    # 先假定 R1 对应上支路，R2 对应下支路；C1 对应上支路，C2 对应下支路
    # 这是你当前命名体系下最自然的默认规则
    r_sorted = [node for node, _ in groups["R"]]
    c_sorted = [node for node, _ in groups["C"]]
    m_chain = [node for node, _ in groups["m"]]

    if len(r_sorted) >= 1:
        positions[r_sorted[0]] = (0.0, n_y)
    if len(c_sorted) >= 1:
        positions[c_sorted[0]] = (n_x_start + len(n_chain) * x_gap, n_y)

    # ---- 下支路 ----
    m_x_start = 2.0
    for i, node in enumerate(m_chain):
        positions[node] = (m_x_start + i * x_gap, m_y)

    if len(r_sorted) >= 2:
        positions[r_sorted[1]] = (0.0, m_y)
    if len(c_sorted) >= 2:
        positions[c_sorted[1]] = (m_x_start + len(m_chain) * x_gap, m_y)

    # ---- 扰动 ----
    d_nodes = [node for node, _ in groups["D"]]
    for i, node in enumerate(d_nodes):
        positions[node] = (0.0, d_y - i * 1.5)

    # ---- 其他未知节点 ----
    # 先放在中间层，避免炸掉
    for i, node in enumerate(sorted(others)):
        positions[node] = (2.0 + i * x_gap, -y_gap)

    return positions

def default_positions() -> dict[str, tuple[float, float]]:
    """
    先给你一套适配当前数据的固定布局。
    以后你可以再抽成 layout preset。
    """
    return {
        "R1": (0, 3), "n1": (2, 3), "n2": (4, 3), "n3": (6, 3), "C1": (8, 3),
        "R2": (0, 0), "m1": (2, 0), "m2": (4, 0), "m3": (6, 0), "C2": (8, 0),
        "D":  (0, -2),
    }


def build_node_lines(positions: dict[str, tuple[float, float]]) -> list[str]:
    lines = []
    for name, (x, y) in positions.items():
        label = fmt_node_label(name)
        lines.append(rf"\node ({name}) at ({x},{y}) {{{label}}};")
    return lines


def edge_to_tikz(
    s: str,
    t: str,
    g: str,
    positions: dict[str, tuple[float, float]],
    style_overrides: dict[tuple[str, str], dict] | None = None,
) -> str:
    """
    核心：按边类型自动生成更接近人工排版的 \\draw 语句。

    style_overrides 用来覆盖默认规则，例如：
        {
            ("n3", "m2"): {"mode": "straight", "node_opt": "pos=0.38,right"},
        }
    """
    style_overrides = style_overrides or {}
    override = style_overrides.get((s, t), {})

    label = fmt_gain(g)

    # 允许手工覆盖模式
    mode = override.get("mode")

    if mode == "straight":
        node_opt = override.get("node_opt", "")
        node_part = rf" node[{node_opt}] {{{label}}}" if node_opt else rf" node {{{label}}}"
        return rf"\draw ({s}) --{node_part} ({t});"

    if mode == "curve":
        out_angle = override.get("out", 120)
        in_angle = override.get("in", 60)
        node_opt = override.get("node_opt", "pos=0.5,above")
        return rf"\draw ({s}) to[out={out_angle},in={in_angle}] node[{node_opt}] {{{label}}} ({t});"

    # 1) 扰动输入
    if is_disturbance_edge(s, t):
        return rf"\draw ({s}) -- node[left] {{{label}}} ({t});"

    # 2) 同支路反馈
    if is_same_branch_feedback(s, t):
        if node_group(s) == "n":
            # 上支路反馈，从上方绕
            return rf"\draw ({s}) to[out=120,in=60] node[pos=0.5,above] {{{label}}} ({t});"
        else:
            # 下支路反馈，从下方绕
            return rf"\draw ({s}) to[out=-120,in=-60] node[pos=0.5,below] {{{label}}} ({t});"

    # 3) 交叉耦合
    if is_cross_coupling(s, t):
        if node_group(s) == "n" and node_group(t) == "m":
            # 上 -> 下
            return rf"\draw ({s}) -- node[pos=0.40,right] {{{label}}} ({t});"
        else:
            # 下 -> 上
            return rf"\draw ({s}) -- node[pos=0.60,left] {{{label}}} ({t});"

    # 4) 主通道
    if is_forward_edge(s, t):
        return rf"\draw ({s}) -- node {{{label}}} ({t});"

    # 5) 其他默认
    return rf"\draw ({s}) -- node {{{label}}} ({t});"


def csv_to_tikz(csv_path: str) -> str:
    edges = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            s = row["start"].strip()
            t = row["end"].strip()
            g = row["gain"].strip()
            edges.append((s, t, g))

    positions = auto_positions(edges)

    lines = [r"\begin{tikzpicture}[>=stealth,->,auto]"]
    lines.extend(build_node_lines(positions))

    for s, t, g in edges:
        lines.append(edge_to_tikz(s, t, g, positions))

    lines.append(r"\end{tikzpicture}")
    return "\n".join(lines)


def build_tex(csv_path: str, output: str | None = None) -> str:
    tikz = csv_to_tikz(csv_path)

    tex = rf"""\documentclass{{standalone}}
\pagestyle{{empty}}
\usepackage{{tikz}}
\usetikzlibrary{{arrows.meta,bending}}

\begin{{document}}
\noindent
{tikz}
\end{{document}}
"""

    if output is None:
        output = os.path.splitext(csv_path)[0] + ".tex"

    with open(output, "w", encoding="utf-8") as f:
        f.write(tex)

    return output

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python mason_build.py <input.csv> [output.tex]")
        sys.exit(1)

    csv_path = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) >= 3 else None
    out_file = build_tex(csv_path, output)
    print(f"[OK] Generated {out_file}")


if __name__ == "__main__":
    main()
