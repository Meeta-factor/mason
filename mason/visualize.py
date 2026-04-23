import sympy as sp
from typing import Dict, Any, Tuple, overload
from IPython.display import display, Math

EntryByIndex = tuple[int, int]
EntryByName = tuple[str, str]
Entry = EntryByIndex | EntryByName

@overload
def normalize_entry(
    info: Dict[str, Any],
    entry: EntryByIndex,
) -> tuple[int, int, str, str]:
    ...


@overload
def normalize_entry(
    info: Dict[str, Any],
    entry: EntryByName,
) -> tuple[int, int, str, str]:
    ...


def normalize_entry(
    info: Dict[str, Any],
    entry: Entry,
) -> tuple[int, int, str, str]:
    sources = info["sources"]
    sinks = info["sinks"]

    a, b = entry

    if isinstance(a, int) and isinstance(b, int):
        i, j = a, b
        sink = sinks[i]
        source = sources[j]
        return i, j, sink, source

    if isinstance(a, str) and isinstance(b, str):
        sink, source = a, b
        i = sinks.index(sink)
        j = sources.index(source)
        return i, j, sink, source

    raise TypeError("entry 必须是 (int, int) 或 (str, str)")

def show_result_mason(info: Dict[str, Any]) -> None:
    """
    显示 Mason 求解结果
    """
    display(Math(r"\textbf{Loops}"))
    for i, l in enumerate(info["loops"], 1):
        loop_nodes = list(map(str, l["loop"]))
        loop_str = r" \rightarrow ".join(loop_nodes) + r" \rightarrow " + loop_nodes[0]
        display(Math(r"\text{Loop } %d:\ %s" % (i, loop_str)))
        display(Math(r"L_%d = %s" % (i, sp.latex(l["gain"]))))

    display(Math(r"\textbf{Forward Paths}"))
    for i, p in enumerate(info["forward_paths"], 1):
        path_str = r" \rightarrow ".join(map(str, p["path"]))
        display(Math(r"\text{Path } %d:\ %s" % (i, path_str)))
        display(Math(r"P_%d = %s" % (i, sp.latex(p["P"]))))

        if "Delta_k" in p:
            display(Math(r"\Delta_%d = %s" % (i, sp.latex(p["Delta_k"]))))

    display(Math(r"\textbf{System Determinant}"))

    loop_labels = {}
    for i, l in enumerate(info["loops"], 1):
        key = tuple(l["loop"])
        loop_labels[key] = f"L_{i}"

    delta_info = info.get("Delta_info", {})
    single_loops = delta_info.get("single_loops", [])
    nt_groups = delta_info.get("non_touching_groups", {})

    lines = []

    # Step 1: symbolic form
    if single_loops:
        symbolic_1 = " + ".join(
            loop_labels[tuple(item["loop"])]
            for item in single_loops
        )
        line = r"1 - \left(%s\right)" % symbolic_1
    else:
        line = r"1"

    for r in sorted(nt_groups):
        groups = nt_groups[r]
        symbolic_r = " + ".join(
            r" \cdot ".join(loop_labels[tuple(loop)] for loop in g["loops"])
            for g in groups
        )
        sign = "+" if r % 2 == 0 else "-"
        line += r" %s \left(%s\right)" % (sign, symbolic_r)

    lines.append(r"\Delta &= %s" % line)

    # Step 2: substitute gains
    if single_loops:
        expanded_1 = " + ".join(sp.latex(item["gain"]) for item in single_loops)
        line = r"1 - \left(%s\right)" % expanded_1
    else:
        line = r"1"

    for r in sorted(nt_groups):
        groups = nt_groups[r]
        expanded_r = " + ".join(
            sp.latex(g["gain_product"])
            for g in groups
        )
        sign = "+" if r % 2 == 0 else "-"
        line += r" %s \left(%s\right)" % (sign, expanded_r)

    lines.append(r"&= %s" % line)

    # Step 3: final simplified form
    lines.append(r"&= %s" % sp.latex(info["Delta"]))

    latex_block = r"\begin{aligned}" + r" \\\\ ".join(lines) + r"\end{aligned}"
    display(Math(latex_block))

    display(Math(r"\textbf{Transfer Function}"))
    display(
        Math(
            r"T = \frac{\sum P_i \Delta_i}{\Delta} = %s"
            % sp.latex(info["TransferFunction"])
        )
    )


def show_result_shannon(info: Dict[str, Any]) -> None:
    """
    显示 Shannon-Happ 求解结果
    """
    display(Math(r"\textbf{Closed Graph Loops}"))
    for i, l in enumerate(info["closed_loops"], 1):
        loop_nodes = list(map(str, l["loop"]))
        loop_str = r" \rightarrow ".join(loop_nodes) + r" \rightarrow " + loop_nodes[0]
        display(Math(r"\text{Loop } %d:\ %s" % (i, loop_str)))
        display(Math(r"L_%d = %s" % (i, sp.latex(l["gain"]))))

    if "forward_paths" in info:
        display(Math(r"\textbf{Original Forward Paths}"))
        for i, p in enumerate(info["forward_paths"], 1):
            path_str = r" \rightarrow ".join(map(str, p["path"]))
            display(Math(r"\text{Path } %d:\ %s" % (i, path_str)))
            display(Math(r"P_%d = %s" % (i, sp.latex(p["gain"]))))

    display(Math(r"\textbf{Characteristic Equation}"))

    # 建立闭图 loop -> L_i 编号映射
    loop_labels = {}
    for i, l in enumerate(info["closed_loops"], 1):
        key = tuple(l["loop"])
        loop_labels[key] = f"L_{i}"

    nt_groups = info.get("non_touching_groups", {})
    closed_loops = info.get("closed_loops", [])

    lines = []

    # Step 1: symbolic form
    if closed_loops:
        symbolic_1 = " + ".join(
            loop_labels[tuple(item["loop"])]
            for item in closed_loops
        )
        line = r"1 - \left(%s\right)" % symbolic_1
    else:
        line = r"1"

    for r in sorted(nt_groups):
        groups = nt_groups[r]
        symbolic_r = " + ".join(
            r" \cdot ".join(loop_labels[tuple(loop)] for loop in g["loops"])
            for g in groups
        )
        sign = "+" if r % 2 == 0 else "-"
        line += r" %s \left(%s\right)" % (sign, symbolic_r)

    lines.append(r"0 &= %s" % line)

    # Step 2: substitute gains
    if closed_loops:
        expanded_1 = " + ".join(sp.latex(item["gain"]) for item in closed_loops)
        line = r"1 - \left(%s\right)" % expanded_1
    else:
        line = r"1"

    for r in sorted(nt_groups):
        groups = nt_groups[r]
        expanded_r = " + ".join(
            sp.latex(g["gain_product"])
            for g in groups
        )
        sign = "+" if r % 2 == 0 else "-"
        line += r" %s \left(%s\right)" % (sign, expanded_r)

    lines.append(r"&= %s" % line)

    if "characteristic_expression" in info:
        lines.append(r"&= %s" % sp.latex(info["characteristic_expression"]))

    latex_block = r"\begin{aligned}" + r" \\\\ ".join(lines) + r"\end{aligned}"
    display(Math(latex_block))


    display(Math(r"\textbf{Transfer Function}"))
    display(Math(r"T = %s" % sp.latex(info["TransferFunction"])))


def get_entry_info(info: Dict[str, Any], i: int, j: int) -> Dict[str, Any]:
    sink = info["sinks"][i]
    source = info["sources"][j]
    return info["entry_info"][(sink, source)]


def get_entry_value(info: Dict[str, Any], i: int, j: int):
    return info["transfer_matrix"][i, j]


def get_entry(info: Dict[str, Any], i: int, j: int):
    sink = info["sinks"][i]
    source = info["sources"][j]
    value = info["transfer_matrix"][i, j]
    detail = info["entry_info"][(sink, source)]
    return value, detail


def show_result_mimo(
    info: Dict[str, Any],
    entry: Entry | None = None,
) -> None:
    G = info["transfer_matrix"]

    display(Math(r"\textbf{MIMO Transfer Matrix}"))
    display(Math(r"G(s) = %s" % sp.latex(G)))

    if entry is None:
        return

    i, j, sink, source = normalize_entry(info, entry)

    sub_info = info["entry_info"][(sink, source)]
    value = G[i, j]

    display(Math(
        r"\textbf{Selected Entry}: \ G_{%d%d}(s) = %s \leftarrow %s"
        % (i + 1, j + 1, str(sink), str(source))
    ))
    display(Math(r"G_{%d%d}(s) = %s" % (i + 1, j + 1, sp.latex(value))))

    show_result(sub_info)


def show_result(
    info: Dict[str, Any],
    entry: Entry | None = None,
) -> None:
    if "transfer_matrix" in info and "entry_info" in info:
        show_result_mimo(info, entry=entry)
    elif "Delta" in info and "loops" in info:
        if entry is not None:
            raise ValueError("entry 参数只对 MIMO 结果有效")
        show_result_mason(info)
    elif "characteristic_expression" in info and "closed_loops" in info:
        if entry is not None:
            raise ValueError("entry 参数只对 MIMO 结果有效")
        show_result_shannon(info)
    else:
        raise ValueError("无法识别 info 的类型：既不像 Mason，也不像 Shannon-Happ，也不像 MIMO")
    
def solve_and_show(solver: Any, expand_result: bool = False):
    """
    对已经 load_from_dict 的 solver 进行求解并显示结果。
    """
    T, info = solver.solve(expand_result=expand_result)
    show_result(info)
    return T, info