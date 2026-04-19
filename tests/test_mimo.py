import sympy as sp
from mason.solver import MIMOMasonSolver


def assert_expr_equal(a, b):
    assert sp.simplify(a - b) == 0

def test_mimo_basic():
    solver = MIMOMasonSolver()

    data = {
        "edges": [
            ("R1", "C1", "G1"),
            ("R2", "C2", "G2"),
        ],
        "sources": ["R1", "R2"],
        "sinks": ["C1", "C2"],
    }

    solver.load_from_dict(data)

    G = solver.transfer_matrix(
        sources=data["sources"],
        sinks=data["sinks"]
    )

    assert_expr_equal(G[0, 0], sp.sympify("G1"))
    assert_expr_equal(G[0, 1], sp.Integer(0))
    assert_expr_equal(G[1, 0], sp.Integer(0))
    assert_expr_equal(G[1, 1], sp.sympify("G2"))

def test_mimo_coupling():
    solver = MIMOMasonSolver()

    data = {
        "edges": [
            ("R1", "C1", "G11"),
            ("R1", "C2", "G12"),
            ("R2", "C1", "G21"),
            ("R2", "C2", "G22"),
        ],
        "sources": ["R1", "R2"],
        "sinks": ["C1", "C2"],
    }

    solver.load_from_dict(data)

    G = solver.transfer_matrix(
        sources=data["sources"],
        sinks=data["sinks"]
    )

    assert_expr_equal(G[0, 0], sp.sympify("G11"))
    assert_expr_equal(G[0, 1], sp.sympify("G21"))
    assert_expr_equal(G[1, 0], sp.sympify("G12"))
    assert_expr_equal(G[1, 1], sp.sympify("G22"))
