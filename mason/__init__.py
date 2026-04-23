"""
Mason Signal Flow Graph Solver
==============================

This module provides a symbolic solver for signal flow graphs based on
Mason's Gain Formula. It supports both SISO (Single-Input Single-Output)
and MIMO (Multi-Input Multi-Output) systems.

Core Features
-------------
- Symbolic computation using SymPy
- Directed graph modeling via NetworkX
- Automatic enumeration of:
    * Forward paths
    * Loops
    * Non-touching loop combinations
- Exact transfer function derivation
- Support for disturbance-to-output transfer analysis
- Visualization via Graphviz and Matplotlib

Mathematical Background
----------------------
For a signal flow graph, the transfer function is computed as:

    T = Σ (P_k * Δ_k) / Δ

where:
    P_k   : gain of the k-th forward path
    Δ     : system determinant
    Δ_k   : cofactor (excluding loops touching path k)

The determinant is defined as:

    Δ = 1 - ΣL_i + ΣL_i L_j - ΣL_i L_j L_k + ...

where only non-touching loop products are included.

Typical Usage
-------------
    solver = SISOMasonSolver()
    solver.load_from_dict(data)
    T, info = solver.solve()

    solver.show_result(info)

Applications
------------
- Control system analysis
- Block diagram simplification
- Symbolic transfer function derivation
- Educational tools for Mason’s formula
- Research prototyping for control theory

Author Notes
------------
This implementation focuses on correctness and symbolic clarity rather
than computational optimality. Loop enumeration may become expensive
for large graphs.

"""
from .solver import MasonSolver,MIMOSFGSolver,ShannonHappSolver
from .visualize import  show_result, solve_and_show

__all__ = [
    "MasonSolver",
    "show_result",
    "solve_and_show",
]