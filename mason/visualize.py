import sympy as sp
from typing import Dict, Any

from IPython.display import display, Math


def show_result(info: Dict[str, Any]) -> None:
    """
    将 solver.transfer_function 返回的 info 用 LaTeX 数学公式显示。

    适用于 Jupyter Notebook / VS Code Notebook。
    """
    display(Math(r"\textbf{Forward Paths}"))
    for i, p in enumerate(info["forward_paths"], 1):
        path_str = r" \rightarrow ".join(map(str, p["path"]))
        display(Math(r"\text{Path } %d:\ %s" % (i, path_str)))
        display(Math(r"P_%d = %s" % (i, sp.latex(p["P"]))))
        display(Math(r"\Delta_%d = %s" % (i, sp.latex(p["Delta_k"]))))

    display(Math(r"\textbf{Loops}"))
    for i, l in enumerate(info["loops"], 1):
        loop_nodes = list(map(str, l["loop"]))
        loop_str = r" \rightarrow ".join(loop_nodes) + r" \rightarrow " + loop_nodes[0]
        display(Math(r"\text{Loop } %d:\ %s" % (i, loop_str)))
        display(Math(r"L_%d = %s" % (i, sp.latex(l["gain"]))))

    display(Math(r"\textbf{System Determinant}"))
    display(Math(r"\Delta = %s" % sp.latex(info["Delta"])))

    display(Math(r"\textbf{Transfer Function}"))
    display(Math(r"T = %s" % sp.latex(info["TransferFunction"])))


def solve_and_show(solver: Any, expand_result: bool = False):
    """
    对已经 load_from_dict 的 solver 进行求解并显示结果。
    """
    T, info = solver.solve(expand_result=expand_result)
    show_result(info)
    return T, info