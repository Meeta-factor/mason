from __future__ import annotations
from abc import ABC
import itertools
import networkx as nx
import sympy as sp
from .typing_defs import *
from .visualize import  *

class BaseSFGSolver(ABC):
    """
    Base Signal Flow Graph Solver

    This base class provides the common graph operations and Mason gain
    formula machinery shared by concrete solvers such as SISO and MIMO
    variants.

    The graph is internally represented as a directed graph (DiGraph),
    where:
        - Nodes represent system variables
        - Edges represent signal flow with associated gains

    Key Capabilities
    ----------------
    - Compute forward path gains
    - Detect all simple loops
    - Identify non-touching loop combinations
    - Construct system determinant (Δ)
    - Compute cofactor determinants (Δ_k)
    - Derive overall transfer function symbolically

    Notes
    -----
    - Gains are internally converted to SymPy expressions
    - Loop enumeration is combinatorial (may not scale for large graphs)
    - Designed for symbolic analysis rather than real-time computation
    """
    def __init__(self):
        self.G = nx.DiGraph()
        self.source = None
        self.sink = None

    def add_edge(self, u, v, gain):
        """
        gain 可以是:
        - SymPy 符号/表达式
        - 字符串，如 'G1', '-H1', 'G2*H3'
        """
        self.G.add_edge(u, v, gain=sp.sympify(gain))

    def add_edges_from(self, edge_list):
        """
        批量添加边。

        edge_list: [(u, v, gain), ...]
        """
        for u, v, gain in edge_list:
            self.add_edge(u, v, gain)

    def path_gain(self, path):
        """
        path: [n0, n1, n2, ...]

        前向通路增益等于路径上所有边增益的连乘。
        """
        gain = sp.Integer(1)
        for i in range(len(path) - 1):
            gain *= self.G[path[i]][path[i + 1]]["gain"]
        return sp.simplify(gain)

    def loop_gain(self, cycle):
        """
        networkx.simple_cycles 返回的 cycle 形如 [a, b, c]
        实际闭环边为 a->b, b->c, c->a

        因此这里要手动把最后一个节点重新连回第一个节点。
        """
        gain = sp.Integer(1)
        n = len(cycle)
        for i in range(n):
            u = cycle[i]
            v = cycle[(i + 1) % n]
            gain *= self.G[u][v]["gain"]
        return sp.simplify(gain)

    def forward_paths(self, source, sink):
        """
        所有从 source 到 sink 的简单前向通路。

        simple path 不允许重复经过同一节点，这和 Mason 公式中
        “前向通路”的定义一致。
        """
        return list(nx.all_simple_paths(self.G, source=source, target=sink))

    def loops(self):
        """
        所有简单回路。
        """
        return list(nx.simple_cycles(self.G))

    @staticmethod
    def non_touching(loop_group):
        """
        判断一组回路是否两两互不接触
        """
        node_sets = [set(loop) for loop in loop_group]
        for i in range(len(node_sets)):
            for j in range(i + 1, len(node_sets)):
                if node_sets[i] & node_sets[j]:
                    return False
        return True

    def non_touching_loop_groups(self, loops):
        """
        枚举所有“两两互不接触”的回路组合。

        返回:
        {
            2: [(loop1, loop2), ...],
            3: [(loop1, loop2, loop3), ...],
            ...
        }
        """
        result = {}
        n = len(loops)
        for r in range(2, n + 1):
            groups = []
            for comb in itertools.combinations(loops, r):
                if self.non_touching(comb):
                    groups.append(comb)
            if groups:
                result[r] = groups
        return result

    def delta_from_loops(self, loops):
        """
        根据给定 loops 计算 Δ
        Δ = 1 - ΣLi + ΣLiLj - ΣLiLjLk + ...

        这里的高阶项只统计“互不接触回路”的乘积，这是 Mason 公式里
        最容易漏掉的一点。
        """
        delta = sp.Integer(1)
        single_sum = sum((self.loop_gain(loop) for loop in loops), sp.Integer(0))
        delta -= single_sum

        nt_groups = self.non_touching_loop_groups(loops)
        for r, groups in nt_groups.items():
            term_sum = sp.Integer(0)
            for group in groups:
                prod = sp.Integer(1)
                # 一个 group 代表一组互不接触回路，对应 Mason 公式里的乘积项。
                for loop in group:
                    prod *= self.loop_gain(loop)
                term_sum += prod
            delta = delta + term_sum if r % 2 == 0 else delta - term_sum

        return sp.simplify(delta)

    def touching_path(self, loop: Loop, path: Path) -> bool:
        """
        回路是否接触某条前向通路。

        只要共享任一节点，就视为接触。
        """
        return bool(set(loop) & set(path))

    def delta_k(self, path: Path, all_loops: List[Loop]) -> Gain:
        """
        Δ_k: 去掉所有接触 path 的回路后计算 Δ。

        这是 Mason 公式中与第 k 条前向通路对应的修正因子。
        """
        untouched_loops = [loop for loop in all_loops if not self.touching_path(loop, path)]
        return self.delta_from_loops(untouched_loops)

    def delta_k_info(self, path: Path, all_loops: List[Loop]) -> Dict[str, Any]:
        """
        返回与某条前向通路 path 对应的 Δ_k 构造信息。

        说明：
        - loops_used: 保留下来的、不接触该 path 的回路在 all_loops 中的索引
        - non_touching_groups: 这些保留回路之间的高阶非接触组合，索引形式返回
        """
        untouched_indices = []
        untouched_loops = []

        for idx, loop in enumerate(all_loops):
            if not self.touching_path(loop, path):
                untouched_indices.append(idx)
                untouched_loops.append(loop)

        nt_groups_raw = self.non_touching_loop_groups(untouched_loops)

        # 把局部组合重新映射回 all_loops 的全局索引
        local_to_global = {
            local_idx: global_idx
            for local_idx, global_idx in enumerate(untouched_indices)
        }

        nt_groups_idx: Dict[int, List[List[int]]] = {}
        for r, groups in nt_groups_raw.items():
            mapped_groups = []
            for group in groups:
                mapped = []
                for loop in group:
                    local_idx = untouched_loops.index(loop)
                    mapped.append(local_to_global[local_idx])
                mapped_groups.append(mapped)
            nt_groups_idx[r] = mapped_groups

        return {
            "loops_used": untouched_indices,
            "non_touching_groups": nt_groups_idx,
        }

    def load_from_dict(self, data):
        self.G.clear()
        for u, v, gain in data["edges"]:
            self.add_edge(u, v, gain)
        self.source = data.get("source")
        self.sink = data.get("sink")

    def transfer_function(
        self,
        source: Node,
        sink: Node,
        expand_result: bool = False,
    ) -> Tuple[Gain, Dict[str, Any]]:
        """
        返回总传递函数 T = Σ(Pk * Δk) / Δ。

        同时返回一份 debug_info，便于把每条前向通路、每个回路以及
        最终 Δ 的组成展示出来。
        """
        paths = self.forward_paths(source, sink)
        loops = self.loops()

        if not paths:
            raise ValueError(f"从 {source} 到 {sink} 没有前向通路")

        delta = self.delta_from_loops(loops)
        nt_groups = self.non_touching_loop_groups(loops)

        delta_info = {
            "single_loops": [
                {
                    "loop": loop,
                    "gain": self.loop_gain(loop),
                }
                for loop in loops
            ],
            "non_touching_groups": {
                r: [
                    {
                        "loops": list(group),
                        "gain_product": sp.simplify(
                            sp.prod(self.loop_gain(loop) for loop in group)
                        ),
                    }
                    for group in groups
                ]
                for r, groups in nt_groups.items()
            },
        }

        numerator = sp.Integer(0)
        path_data = []
        for path in paths:
            pk = self.path_gain(path)
            dk = self.delta_k(path, loops)
            dk_info = self.delta_k_info(path, loops)

            numerator += pk * dk  # type: ignore[operator]
            path_data.append(
                {
                    "path": path,
                    "P": sp.simplify(pk),
                    "Delta_k": sp.simplify(dk),
                    "Delta_k_info": dk_info,
                }
            )

        T = sp.simplify(sp.together(numerator / delta))  # type: ignore[operator]
        if expand_result:
            T = sp.expand(T)

        debug_info = {
            "forward_paths": path_data,
            "loops": [{"loop": loop, "gain": self.loop_gain(loop)} for loop in loops],
            "Delta": sp.simplify(delta),
            "Delta_info": delta_info,
            "TransferFunction": T,
        }
        return T, debug_info

    def solve(self, expand_result: bool = False) -> Tuple[Gain, Dict[str, Any]]:
        if self.source is None or self.sink is None:
            raise ValueError("请先调用 load_from_dict 设置 source 和 sink")
        return self.transfer_function(self.source, self.sink, expand_result=expand_result)

class MasonSolver(BaseSFGSolver):
    """
    SISO Mason Gain Formula Solver

    This class implements a symbolic solver for signal flow graphs based
    on Mason’s Gain Formula for single-input single-output (SISO) systems.

    The graph is internally represented as a directed graph (DiGraph),
    where:
        - Nodes represent system variables
        - Edges represent signal flow with associated gains

    Key Capabilities
    ----------------
    - Compute forward path gains
    - Detect all simple loops
    - Identify non-touching loop combinations
    - Construct system determinant (Δ)
    - Compute cofactor determinants (Δ_k)
    - Derive overall transfer function symbolically

    Input Format
    ------------
    The system can be defined using a dictionary:

        data = {
            "edges": [(u, v, gain), ...],
            "source": "input_node",
            "sink": "output_node"
        }

    where:
        u, v   : node names (str)
        gain   : str or sympy.Expr

    Example
    -------
        solver = SISOMasonSolver()
        solver.load_from_dict(data)
        T, info = solver.solve()

    Notes
    -----
    - Gains are internally converted to SymPy expressions
    - Loop enumeration is combinatorial (may not scale for large graphs)
    - Designed for symbolic analysis rather than real-time computation

    """
    def __init__(self):
        super().__init__()

    def transfer_function(
        self,
        source: Node,
        sink: Node,
        expand_result: bool = False
    ) -> Tuple[Gain, Dict]:
        """
        返回总传递函数 T = Σ(Pk * Δk) / Δ。

        同时返回一份 debug_info，便于把每条前向通路、每个回路以及
        最终 Δ 的组成展示出来。
        """
        return super().transfer_function(source, sink, expand_result=expand_result)
    
    def load_from_dict(self, data: dict) -> None:
        """
        从字典格式载入 SISO 图结构及默认输入输出节点。

        约定:
            data["edges"] = [(u, v, gain), ...]
            data["source"] = 输入节点
            data["sink"]   = 输出节点
        """
        super().load_from_dict(data)

    def disturbance_transfer_function(
        self,
        disturbance: Node,
        output: Node,
        expand_result: bool = False
    ) -> Tuple[Gain, Dict]:
        # 扰动到输出的传函，本质上仍然是两节点之间的 Mason 求解。
        return self.transfer_function(disturbance, output, expand_result=expand_result)
    
    def solve(self, expand_result: bool = False) -> Tuple[Gain, Dict]:
        """
        使用 load_from_dict 中记录的默认 source/sink 求解。
        """
        return super().solve(expand_result=expand_result)
        
class ShannonHappSolver(BaseSFGSolver):
    """
    SISO Shannon-Happ Formula Solver

    核心流程：
    1. 将原始开型信号流图闭合：sink -> source 增加一条增益 1/T 的支路
    2. 在闭图中枚举全部简单回路
    3. 构造 Shannon-Happ 特征方程：
           1 - ΣLi + ΣLiLj - ΣLiLjLk + ... = 0
       其中高阶项只保留互不接触回路组合
    4. 对 T 求解，得到总传递函数
    """

    def closed_loop_expression(
        self,
        source: str,
        sink: str,
        T_symbol: str = "T",
    ) -> tuple[sp.Expr, sp.Symbol, list[list[str]], dict[str, Any]]:
        """
        构造闭图后的 Shannon-Happ 特征表达式 expr，
        满足 expr = 0。

        返回：
            expr        : 闭图特征表达式
            T           : 传函符号
            closed_loops: 闭图中所有回路
            debug_info  : 调试信息
        """
        T = sp.Symbol(T_symbol)

        # ---- 备份原图状态，临时闭图，算完后恢复 ----
        if self.G.has_edge(sink, source):
            raise ValueError(
                f"原图中已存在边 {sink} -> {source}，"
                f"直接添加 1/{T_symbol} 会覆盖旧边。"
                "如果你后面要支持并行边，建议把 DiGraph 改成 MultiDiGraph。"
            )

        self.add_edge(sink, source, 1 / T)

        try:
            closed_loops = self.loops()
            expr = self.delta_from_loops(closed_loops)

            nt_groups = self.non_touching_loop_groups(closed_loops)

            debug_info = {
                "T_symbol": T,
                "closed_edge": {
                    "from": sink,
                    "to": source,
                    "gain": sp.simplify(1 / T),
                },
                "closed_loops": [
                    {
                        "loop": loop,
                        "gain": self.loop_gain(loop),
                    }
                    for loop in closed_loops
                ],
                "non_touching_groups": {
                    r: [
                        {
                            "loops": list(group),
                            "gain_product": sp.simplify(
                                sp.prod(self.loop_gain(loop) for loop in group)
                            ),
                        }
                        for group in groups
                    ]
                    for r, groups in nt_groups.items()
                },
                "characteristic_expression": sp.simplify(expr),
            }

        finally:
            # 恢复原图
            self.G.remove_edge(sink, source)

        return sp.simplify(expr), T, closed_loops, debug_info

    def transfer_function(
        self,
        source: str,
        sink: str,
        expand_result: bool = False,
        T_symbol: str = "T",
        pick_physical: bool = True,
    ) -> tuple[sp.Expr, dict[str, Any]]:
        """
        计算总传递函数 T = sink / source

        参数：
            source       : 输入节点
            sink         : 输出节点
            expand_result: 是否展开结果
            T_symbol     : Shannon-Happ 中使用的未知传函符号
            pick_physical: 若解出多个分支，是否自动选取更“物理”的那个

        返回：
            (T_expr, debug_info)
        """
        # 可选：先检查原图确实存在 source -> sink 的前向通路
        paths = self.forward_paths(source, sink)
        if not paths:
            raise ValueError(f"从 {source} 到 {sink} 没有前向通路")

        expr, T, closed_loops, debug_info = self.closed_loop_expression(
            source=source,
            sink=sink,
            T_symbol=T_symbol,
        )

        eq = sp.Eq(expr, 0)
        sols = sp.solve(eq, T)

        if not sols:
            raise ValueError("Shannon-Happ 方程未能解出传递函数")

        # 一般情况下应该只有一个合理分支
        T_expr: Optional[sp.Expr] = None

        if len(sols) == 1:
            T_expr = sp.simplify(sols[0])
        else:
            # 有时 solve 可能返回多个形式分支，尽量挑一个不含 1/T 循环残留、
            # 且形式更像标准传函的表达式
            simplified_sols = [sp.simplify(sol) for sol in sols]

            if pick_physical:
                candidates = []
                for sol in simplified_sols:
                    # 倾向选取不再含 T 的、自由符号中不含 T 的解
                    if T not in sol.free_symbols:
                        candidates.append(sol)

                if candidates:
                    # 取复杂度较低的那个
                    T_expr = min(candidates, key=sp.count_ops)
                else:
                    T_expr = min(simplified_sols, key=sp.count_ops)
            else:
                T_expr = simplified_sols[0]

        if T_expr is None:
            raise ValueError("未找到有效的传递函数表达式")

        T_expr = sp.simplify(sp.together(T_expr))
        if expand_result:
            T_expr = sp.expand(T_expr)

        debug_info.update(
            {
                "forward_paths": [
                    {
                        "path": path,
                        "gain": self.path_gain(path),
                    }
                    for path in paths
                ],
                "characteristic_equation": eq,
                "solutions": sols,
                "TransferFunction": T_expr,
            }
        )

        return T_expr, debug_info # type: ignore

    def solve(
        self,
        expand_result: bool = False,
        T_symbol: str = "T",
        pick_physical: bool = True,
    ) -> tuple[sp.Expr, dict[str, Any]]:
        """
        使用 load_from_dict 中记录的默认 source/sink 求解。
        """
        if self.source is None or self.sink is None:
            raise ValueError("请先调用 load_from_dict 设置 source 和 sink")

        return self.transfer_function(
            self.source,
            self.sink,
            expand_result=expand_result,
            T_symbol=T_symbol,
            pick_physical=pick_physical,
        )

# =========================
# MIMO wrapper
# =========================
class MIMOSFGSolver:
    """
    MIMO wrapper based on entry-wise SISO solving.

    For each (sink_i, source_j), solve:
        G_ij = Y_i / U_j
    then assemble the transfer matrix.

    Default backend is SISOMasonSolver.
    You can also pass SISOShannonHappSolver.
    """

    def __init__(
        self,
        entry_solver_cls: type[BaseSFGSolver] = MasonSolver,
    ) -> None:
        self.entry_solver_cls = entry_solver_cls
        self.data: Optional[dict] = None
        self.sources: List[Node] = []
        self.sinks: List[Node] = []

    def load_from_dict(self, data: dict) -> None:
        """
        Expected format:
            {
                "edges": [(u, v, gain), ...],
                "sources": ["R1", "R2", ...],
                "sinks": ["C1", "C2", ...]
            }

        Compatible with SISO style too:
            {
                "edges": [...],
                "source": "R",
                "sink": "C"
            }
        """
        if "edges" not in data:
            raise ValueError("data 必须包含 'edges'")

        self.data = {
            "edges": list(data["edges"]),
        }

        self.sources = list(data.get("sources", []))
        self.sinks = list(data.get("sinks", []))

        if not self.sources and "source" in data:
            self.sources = [data["source"]]

        if not self.sinks and "sink" in data:
            self.sinks = [data["sink"]]

    def transfer_function(
        self,
        source: Node,
        sink: Node,
        expand_result: bool = False,
        **kwargs: Any,
    ) -> TransferResult:
        if self.data is None:
            raise ValueError("请先调用 load_from_dict")

        solver = self.entry_solver_cls()
        solver.load_from_dict(
            {
                "edges": list(self.data["edges"]),
                "source": source,
                "sink": sink,
            }
        )
        return solver.transfer_function(
            source,
            sink,
            expand_result=expand_result,
            **kwargs,
        )

    def transfer_matrix(
        self,
        sources: Optional[List[Node]] = None,
        sinks: Optional[List[Node]] = None,
        expand_result: bool = False,
        **kwargs: Any,
    ) -> tuple[sp.Matrix, Dict[str, Any]]:
        if self.data is None:
            raise ValueError("请先调用 load_from_dict")

        srcs = list(sources) if sources is not None else list(self.sources)
        snks = list(sinks) if sinks is not None else list(self.sinks)

        if not srcs or not snks:
            raise ValueError(
                "请在 data 中提供 sources / sinks，或在 transfer_matrix 中显式传入"
            )

        M = sp.MutableDenseMatrix.zeros(len(snks), len(srcs))
        entry_info: Dict[Tuple[Node, Node], Dict[str, Any]] = {}

        for i, sink in enumerate(snks):
            for j, source in enumerate(srcs):
                Tij, info = self.transfer_function(
                    source=source,
                    sink=sink,
                    expand_result=expand_result,
                    **kwargs,
                )
                M[i, j] = Tij
                entry_info[(sink, source)] = info

        G = sp.Matrix(M)
        matrix_info = {
            "method": self.entry_solver_cls.__name__,
            "sources": srcs,
            "sinks": snks,
            "transfer_matrix": G,
            "entry_info": entry_info,
        }
        return G, matrix_info

    def solve(
        self,
        expand_result: bool = False,
        **kwargs: Any,
    ) -> tuple[sp.Matrix, Dict[str, Any]]:
        return self.transfer_matrix(
            expand_result=expand_result,
            **kwargs,
        )