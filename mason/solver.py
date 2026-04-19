import itertools
import networkx as nx
import sympy as sp
from .typing_defs import *
from .visualize import  *

class SISOMasonSolver:
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
        self.G = nx.DiGraph()

    def add_edge(self, u: str, v: str, gain: Union[str, sp.Expr]) -> None:
        """
        gain 可以是:
        - SymPy 符号/表达式
        - 字符串，如 'G1', '-H1', 'G2*H3'
        """
        self.G.add_edge(u, v, gain=sp.sympify(gain))

    def add_edges_from(self, edge_list: List[Edge]) -> None:
        """
        批量添加边。

        edge_list: [(u, v, gain), ...]
        """
        for u, v, gain in edge_list:
            self.add_edge(u, v, gain)

    def path_gain(self, path: Path) -> Gain:
        """
        path: [n0, n1, n2, ...]

        前向通路增益等于路径上所有边增益的连乘。
        """
        gain = sp.Integer(1)
        for i in range(len(path) - 1):
            gain *= self.G[path[i]][path[i + 1]]["gain"]
        return sp.simplify(gain)

    def loop_gain(self, cycle: Loop) -> Gain:
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

    def forward_paths(self, source: Node, sink: Node) -> List[Path]:
        """
        所有从 source 到 sink 的简单前向通路。

        simple path 不允许重复经过同一节点，这和 Mason 公式中
        “前向通路”的定义一致。
        """
        return list(nx.all_simple_paths(self.G, source=source, target=sink))

    def loops(self) -> List[Loop]:
        """
        所有简单回路。
        """
        return list(nx.simple_cycles(self.G))

    @staticmethod
    @staticmethod
    def non_touching(loop_group: Tuple[Loop, ...]) -> bool:
        """
        判断一组回路是否两两互不接触
        """
        node_sets = [set(loop) for loop in loop_group]
        for i in range(len(node_sets)):
            for j in range(i + 1, len(node_sets)):
                if node_sets[i] & node_sets[j]:
                    return False
        return True

    def non_touching_loop_groups(
        self, loops: List[Loop]
    ) -> Dict[int, List[Tuple[Loop, ...]]]:
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

    def delta_from_loops(self, loops: List[Loop]) -> Gain:
        """
        根据给定 loops 计算 Δ
        Δ = 1 - ΣLi + ΣLiLj - ΣLiLjLk + ...

        这里的高阶项只统计“互不接触回路”的乘积，这是 Mason 公式里
        最容易漏掉的一点。
        """
        delta = sp.Integer(1)

        # 一阶项：单个回路
        single_sum = sum((self.loop_gain(loop) for loop in loops), sp.Integer(0)) # type: ignore
        delta -= single_sum

        # 高阶非接触项
        nt_groups = self.non_touching_loop_groups(loops)
        for r, groups in nt_groups.items():
            term_sum = sp.Integer(0)
            for group in groups:
                prod = sp.Integer(1)
                # 一个 group 代表一组互不接触回路，对应 Mason 公式里的乘积项。
                for loop in group:
                    prod *= self.loop_gain(loop) # type: ignore
                term_sum += prod # type: ignore

            if r % 2 == 0:
                delta += term_sum # pyright: ignore[reportOperatorIssue]
            else:
                delta -= term_sum # pyright: ignore[reportOperatorIssue]

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
        paths = self.forward_paths(source, sink)
        loops = self.loops()

        if not paths:
            raise ValueError(f"从 {source} 到 {sink} 没有前向通路")

        delta = self.delta_from_loops(loops)

        numerator = sp.Integer(0)
        path_data = []
        for path in paths:
            pk = self.path_gain(path)
            dk = self.delta_k(path, loops)
            # Mason 分子项是每条前向通路增益与其对应 Δ_k 的乘积之和。
            numerator += pk * dk # type: ignore
            path_data.append({
                "path": path,
                "P": sp.simplify(pk),
                "Delta_k": sp.simplify(dk)
            })

        T = sp.simplify(sp.together(numerator / delta)) # type: ignore
        if expand_result:
            T = sp.expand(T)

        debug_info = {
            "forward_paths": path_data,
            "loops": [{"loop": loop, "gain": self.loop_gain(loop)} for loop in loops],
            "Delta": sp.simplify(delta),
            "TransferFunction": T
        }
        return T, debug_info
    
    def load_from_dict(self, data: dict) -> None:
        """
        从字典格式载入 SISO 图结构及默认输入输出节点。

        约定:
            data["edges"] = [(u, v, gain), ...]
            data["source"] = 输入节点
            data["sink"]   = 输出节点
        """
        self.G.clear()
        for u, v, gain in data["edges"]:
            self.add_edge(u, v, gain)

        self.source = data["source"]
        self.sink = data["sink"]

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
        if not hasattr(self, "source") or not hasattr(self, "sink"):
            raise ValueError("请先调用 load_from_dict 设置 source 和 sink")
        return self.transfer_function(self.source, self.sink, expand_result=expand_result)
        
    

class MIMOMasonSolver(SISOMasonSolver):
    """
    MIMO Mason Solver (Extension of SISO)

    This class extends the SISO Mason solver to support multi-input
    multi-output (MIMO) systems by computing transfer functions for
    multiple input-output pairs.

    The resulting system is represented as a transfer matrix:

        G(s) = [T_ij]

    where:
        T_ij = transfer function from input j to output i

    Approach
    --------
    Each element of the transfer matrix is computed independently
    using the standard SISO Mason Gain Formula.

    Features
    --------
    - Transfer matrix construction
    - Per-path symbolic analysis
    - Optional debug information for each entry

    Example
    -------
        solver = MIMOMasonSolver()
        solver.load_from_dict(data)

        G = solver.transfer_matrix(
            sources=["u1", "u2"],
            sinks=["y1", "y2"]
        )

    Notes
    -----
    - Internally reuses SISO computation
    - Suitable for symbolic system modeling and analysis
    - Not optimized for large-scale networks

    """
    def load_from_dict(self, data: dict) -> None:
        """
        从字典格式载入 MIMO 图结构。

        支持字段:
            data["edges"]   = [(u, v, gain), ...]
            data["source"]  = 默认输入节点（可选）
            data["sink"]    = 默认输出节点（可选）
            data["sources"] = 输入节点列表（可选）
            data["sinks"]   = 输出节点列表（可选）
        """
        self.G.clear()
        for u, v, gain in data["edges"]:
            self.add_edge(u, v, gain)

        self.source = data.get("source")
        self.sink = data.get("sink")
        self.sources = data.get("sources", [])
        self.sinks = data.get("sinks", [])

    def transfer_matrix(
        self,
        sources: List[Node],
        sinks: List[Node],
        return_info: bool = False
    ) -> Union[sp.Matrix, Tuple[sp.Matrix, List[List[Dict]]]]:
        """
        计算从 sources 到 sinks 的传递矩阵。

        返回矩阵的第 i 行第 j 列元素，表示第 j 个输入到第 i 个输出的传函。
        """
        tf_matrix = []
        info_matrix = []

        for sink in sinks:
            row_tf = []
            row_info = []
            for source in sources:
                try:
                    T, info = self.transfer_function(source, sink)
                except ValueError:
                    T = sp.Integer(0)
                    info = None
                row_tf.append(T)
                row_info.append(info)
            tf_matrix.append(row_tf)
            info_matrix.append(row_info)

        G = sp.Matrix(tf_matrix)

        if return_info:
            return G, info_matrix
        return G
    
    def solve_path(
        self,
        source: Optional[Node] = None,
        sink: Optional[Node] = None,
        expand_result: bool = False
    ) -> Tuple[Gain, Dict]:
        """
        求某一对指定输入输出之间的传函。

        如果未显式传参，则回退到 load_from_dict 中记录的默认 source/sink。
        """
        source = source if source is not None else self.source
        sink = sink if sink is not None else self.sink

        if source is None or sink is None:
            raise ValueError("请指定 source 和 sink")

        return self.transfer_function(source, sink, expand_result=expand_result)
    
    
