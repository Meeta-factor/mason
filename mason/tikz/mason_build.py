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
        H_1b   -> $H_{1b}$
        H_1^b  -> $H_{1}^{b}$
        G^*    -> $G^{*}$
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

    # H_1^b -> H_{1}^{b}, -a_12^* -> -a_{12}^{*}
    m = re.fullmatch(r"(-?)([A-Za-z]+)_([A-Za-z0-9]+)\^([A-Za-z0-9*+\-]+)", gain)
    if m:
        sign, head, sub, sup = m.groups()
        return rf"${sign}{head}_{{{sub}}}^{{{sup}}}$"

    # G^* -> G^{*}, H^b -> H^{b}
    m = re.fullmatch(r"(-?)([A-Za-z]+)\^([A-Za-z0-9*+\-]+)", gain)
    if m:
        sign, head, sup = m.groups()
        return rf"${sign}{head}^{{{sup}}}$"

    # H_1b -> H_{1b}, -a_12 -> -a_{12}
    m = re.fullmatch(r"(-?)([A-Za-z]+)_([A-Za-z0-9]+)", gain)
    if m:
        sign, head, sub = m.groups()
        return rf"${sign}{head}_{{{sub}}}$"

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


def has_dual_branch_layout(edges) -> bool:
    nodes = collect_nodes(edges)
    return any(name.startswith("n") for name in nodes) or any(name.startswith("m") for name in nodes)


def build_edge_sets(edges):
    edge_pairs = {(s, t) for s, t, _ in edges}
    reverse_pairs = {pair for pair in edge_pairs if (pair[1], pair[0]) in edge_pairs}
    return edge_pairs, reverse_pairs


def generic_main_path(edges):
    edge_pairs, reverse_pairs = build_edge_sets(edges)
    main_edges = [(s, t) for s, t, _ in edges if (s, t) not in reverse_pairs]

    if not main_edges:
        return []

    adjacency = defaultdict(list)
    indegree = defaultdict(int)
    nodes = collect_nodes(edges)

    for s, t in main_edges:
        adjacency[s].append(t)
        indegree[t] += 1
        indegree.setdefault(s, 0)

    preferred_sources = [n for n in ("R", "R1", "X") if n in nodes]
    sources = preferred_sources or [n for n in nodes if indegree.get(n, 0) == 0]
    if not sources:
        sources = [main_edges[0][0]]

    preferred_sinks = {"Y", "C", "C1", "Z"}

    best_path = []

    def score(path):
        sink_bonus = 1 if path and path[-1] in preferred_sinks else 0
        return (len(path), sink_bonus)

    def dfs(node, path, seen):
        nonlocal best_path
        if score(path) > score(best_path):
            best_path = path[:]

        for nxt in adjacency.get(node, []):
            if nxt in seen:
                continue
            seen.add(nxt)
            path.append(nxt)
            dfs(nxt, path, seen)
            path.pop()
            seen.remove(nxt)

    for source in sources:
        dfs(source, [source], {source})

    return best_path


def auto_positions_generic(edges, x_gap=2.2, y_gap=2.2):
    nodes = collect_nodes(edges)
    positions = {}
    edge_pairs, reverse_pairs = build_edge_sets(edges)
    main_path = generic_main_path(edges)

    if not main_path:
        for i, node in enumerate(sorted(nodes)):
            positions[node] = (i * x_gap, 0.0)
        return positions

    for i, node in enumerate(main_path):
        positions[node] = (i * x_gap, 0.0)

    levels_used = defaultdict(int)
    attached = set(main_path)

    for anchor in main_path:
        partners = []
        for s, t, _ in edges:
            if s == anchor and (t, s) in reverse_pairs and t not in attached:
                partners.append(t)
            elif t == anchor and (t, s) in reverse_pairs and s not in attached:
                partners.append(s)

        unique_partners = []
        seen = set()
        for node in partners:
            if node not in seen:
                unique_partners.append(node)
                seen.add(node)

        slot_order = [0, -1, 1, -2, 2, -3, 3]
        for idx, node in enumerate(unique_partners):
            level = levels_used[anchor]
            levels_used[anchor] += 1
            x, y = positions[anchor]
            slot = slot_order[idx] if idx < len(slot_order) else ((idx // 2 + 1) * (-1 if idx % 2 else 1))
            x_offset = 0.9 * slot
            y_offset = y_gap + level * 1.5 + abs(slot) * 0.4
            positions[node] = (x + x_offset, y + y_offset)
            attached.add(node)

    remaining = [node for node in sorted(nodes) if node not in positions]
    base_x = len(main_path) * x_gap
    for i, node in enumerate(remaining):
        positions[node] = (base_x + i * x_gap, -y_gap)

    return positions


def auto_positions(edges, x_gap=2.0, y_gap=3.0):
    if not has_dual_branch_layout(edges):
        return auto_positions_generic(edges, x_gap=x_gap, y_gap=2.6)

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
        prefix, _ = parse_node(name)
        style = "io node" if prefix in {"R", "C", "D"} else "signal node"
        lines.append(rf"\node[{style}] ({name}) at ({x},{y}) {{{label}}};")
    return lines


def edge_direction(
    s: str,
    t: str,
    positions: dict[str, tuple[float, float]],
) -> tuple[float, float]:
    x1, y1 = positions[s]
    x2, y2 = positions[t]
    return x2 - x1, y2 - y1


def straight_label_opt(
    s: str,
    t: str,
    positions: dict[str, tuple[float, float]],
) -> str:
    dx, dy = edge_direction(s, t, positions)

    if abs(dy) < 0.2:
        return "midway,above"
    if abs(dx) < 0.2:
        return "midway,right"
    if dx * dy > 0:
        return "midway,above left"
    return "midway,above right"


def with_edge_label_style(node_opt: str) -> str:
    return f"edge label,{node_opt}" if node_opt else "edge label"


def is_reverse_pair(s: str, t: str, edge_pairs: set[tuple[str, str]]) -> bool:
    return (t, s) in edge_pairs


def paired_loop_edge_style(
    s: str,
    t: str,
    positions: dict[str, tuple[float, float]],
) -> tuple[int, int, str, float]:
    dx, dy = edge_direction(s, t, positions)
    abs_dx = abs(dx)

    if dy > 0:
        if dx < -0.2:
            return 120, 250, "pos=0.35,left,xshift=-2pt,yshift=2pt", 0.9 + 0.08 * abs_dx
        if dx > 0.2:
            return 60, 290, "pos=0.35,right,xshift=2pt,yshift=2pt", 0.9 + 0.08 * abs_dx
        return 100, 260, "pos=0.35,left,xshift=-2pt,yshift=2pt", 0.85

    if dx < -0.2:
        return 240, 110, "pos=0.65,left,xshift=-2pt,yshift=-2pt", 0.9 + 0.08 * abs_dx
    if dx > 0.2:
        return 300, 70, "pos=0.65,right,xshift=2pt,yshift=-2pt", 0.9 + 0.08 * abs_dx
    return 280, 80, "pos=0.65,right,xshift=2pt,yshift=-2pt", 0.85


def feedback_angles(
    s: str,
    t: str,
    positions: dict[str, tuple[float, float]],
) -> tuple[int, int, str, float]:
    dx, _ = edge_direction(s, t, positions)
    span = max(abs(dx), 1.0)
    looseness = 0.9 + 0.12 * span

    if node_group(s) == "n":
        return 125, 55, "midway,above", looseness
    return -125, -55, "midway,below", looseness


def cross_coupling_style(
    s: str,
    t: str,
    positions: dict[str, tuple[float, float]],
) -> tuple[int, int, str, float]:
    dx, _ = edge_direction(s, t, positions)
    span = max(abs(dx), 1.0)
    looseness = 0.55 + 0.04 * span

    # 就近原则：目标在右边就从右侧出入，目标在左边就从左侧出入
    # 同时保留一点上下倾角，避免贴着节点边缘滑出去
    if dx >= 0:
        if node_group(s) == "n" and node_group(t) == "m":
            return -18, 18, "midway,right", looseness
        return 18, -18, "midway,left", looseness

    if node_group(s) == "n" and node_group(t) == "m":
        return -162, 162, "midway,left", looseness
    return 162, -162, "midway,right", looseness


def edge_to_tikz(
    s: str,
    t: str,
    g: str,
    positions: dict[str, tuple[float, float]],
    edge_pairs: set[tuple[str, str]],
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
        node_opt = with_edge_label_style(
            override.get("node_opt", straight_label_opt(s, t, positions))
        )
        node_part = rf" node[{node_opt}] {{{label}}}" if node_opt else rf" node {{{label}}}"
        return rf"\draw ({s}) --{node_part} ({t});"

    if mode == "curve":
        out_angle = override.get("out", 120)
        in_angle = override.get("in", 60)
        looseness = override.get("looseness")
        node_opt = with_edge_label_style(override.get("node_opt", "midway,above"))
        looseness_opt = rf",looseness={looseness}" if looseness is not None else ""
        return rf"\draw ({s}) to[out={out_angle},in={in_angle}{looseness_opt}] node[{node_opt}] {{{label}}} ({t});"

    # 0) 成对双向边：给单回路侧支路留出左右两条通道，避免完全重合
    dx, dy = edge_direction(s, t, positions)
    if is_reverse_pair(s, t, edge_pairs) and abs(dy) > 0.5 and abs(dx) <= 1.8:
        out_angle, in_angle, node_opt, looseness = paired_loop_edge_style(s, t, positions)
        return (
            rf"\draw ({s}) to[out={out_angle},in={in_angle},looseness={looseness:.2f}] "
            rf"node[{with_edge_label_style(node_opt)}] {{{label}}} ({t});"
        )

    # 1) 扰动输入
    if is_disturbance_edge(s, t):
        return rf"\draw ({s}) -- node[{with_edge_label_style('midway,left')}] {{{label}}} ({t});"

    # 2) 同支路反馈
    if is_same_branch_feedback(s, t):
        out_angle, in_angle, node_opt, looseness = feedback_angles(s, t, positions)
        return (
            rf"\draw ({s}) to[out={out_angle},in={in_angle},looseness={looseness:.2f}] "
            rf"node[{with_edge_label_style(node_opt)}] {{{label}}} ({t});"
        )

    # 3) 交叉耦合
    if is_cross_coupling(s, t):
        out_angle, in_angle, node_opt, looseness = cross_coupling_style(s, t, positions)
        return (
            rf"\draw ({s}) to[out={out_angle},in={in_angle},looseness={looseness:.2f}] "
            rf"node[{with_edge_label_style(node_opt)}] {{{label}}} ({t});"
        )

    # 4) 主通道
    if is_forward_edge(s, t):
        return rf"\draw ({s}) -- node[{with_edge_label_style('midway,above')}] {{{label}}} ({t});"

    # 5) 其他默认
    return rf"\draw ({s}) -- node[{with_edge_label_style(straight_label_opt(s, t, positions))}] {{{label}}} ({t});"


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
    edge_pairs, _ = build_edge_sets(edges)

    lines = [r"\begin{tikzpicture}["]
    lines.append(r"  >=Latex,")
    lines.append(r"  ->,")
    lines.append(r"  semithick,")
    lines.append(r"  every node/.style={font=\small},")
    lines.append(r"  signal node/.style={circle,draw,minimum size=8mm,inner sep=1pt,fill=white},")
    lines.append(r"  io node/.style={rectangle,rounded corners=2pt,draw,minimum width=8mm,minimum height=6mm,inner sep=2pt,fill=gray!8},")
    lines.append(r"  every path/.style={draw=black!85},")
    lines.append(r"  edge label/.style={fill=white,inner sep=1pt,text=black},")
    lines.append(r"]")
    lines.extend(build_node_lines(positions))

    for s, t, g in edges:
        lines.append(edge_to_tikz(s, t, g, positions, edge_pairs))

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
