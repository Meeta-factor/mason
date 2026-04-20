import sympy as sp
from typing import Dict, Any

from IPython.display import display, Math


def show_result(info: Dict[str, Any]) -> None:
    """
    将 solver.transfer_function 返回的 info 用 LaTeX 数学公式显示。

    适用于 Jupyter Notebook / VS Code Notebook。
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
        display(Math(r"\Delta_%d = %s" % (i, sp.latex(p["Delta_k"]))))


    display(Math(r"\textbf{System Determinant}"))
    # 建立 loop -> L_i 的编号映射
    loop_labels = {}
    loop_gain_map = {}
    for i, l in enumerate(info["loops"], 1):
        key = tuple(l["loop"])
        loop_labels[key] = f"L_{i}"
        loop_gain_map[key] = l["gain"]

    delta_info = info.get("Delta_info", {})
    single_loops = delta_info.get("single_loops", [])
    nt_groups = delta_info.get("non_touching_groups", {})

    lines = []

    # Step 1: 直接从结构式开始
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

    # Step 2: 代入 L_i
    if single_loops:
        expanded_1 = " + ".join(
            sp.latex(item["gain"])
            for item in single_loops
        )
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
        line += r"%s \left(%s\right)" % (sign, expanded_r)

    lines.append(r"&= %s" % line)

    # Step 3: 最终展开
    lines.append(r"&= %s" % sp.latex(info["Delta"]))

    latex_block = r"\begin{aligned}" + " \\\\ ".join(lines) + r"\end{aligned}"
    display(Math(latex_block))

    display(Math(r"\textbf{Transfer Function}"))
    display(Math(r"T = \frac{\sum P_{i} \Delta_{i}}{\Delta} = %s" % sp.latex(info["TransferFunction"])))


def solve_and_show(solver: Any, expand_result: bool = False):
    """
    对已经 load_from_dict 的 solver 进行求解并显示结果。
    """
    T, info = solver.solve(expand_result=expand_result)
    show_result(info)
    return T, info