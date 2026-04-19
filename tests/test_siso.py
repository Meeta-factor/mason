import sympy as sp
from mason.solver import SISOMasonSolver


def assert_expr_equal(a, b):
    assert sp.simplify(a - b) == 0


def test_simple_chain():
    solver = SISOMasonSolver()

    data = {
        "edges": [
            ("A", "B", "G1"),
            ("B", "C", "G2"),
        ],
        "source": "A",
        "sink": "C",
    }

    solver.load_from_dict(data)
    T, _ = solver.solve()

    expected = sp.sympify("G1*G2")
    assert_expr_equal(T, expected)

def test_single_loop():
    solver = SISOMasonSolver()

    data = {
        "edges": [
            ("A", "B", "G1"),
            ("B", "C", "G2"),
            ("C", "B", "G3"),
        ],
        "source": "A",
        "sink": "C",
    }

    solver.load_from_dict(data)
    T, _ = solver.solve()

    expected = sp.sympify("G1*G2 / (1 - G2*G3)")
    assert_expr_equal(T, expected)

def test_two_non_touching_loops():
    solver = SISOMasonSolver()

    data = {
        "edges": [
            ("A", "B", "G1"),
            ("B", "C", "G2"),

            # loop1
            ("B", "B", "H1"),

            # loop2
            ("C", "C", "H2"),
        ],
        "source": "A",
        "sink": "C",
    }

    solver.load_from_dict(data)
    T, _ = solver.solve()

    expected = sp.sympify("G1*G2 / (1 - H1 - H2 + H1*H2)")
    assert_expr_equal(T, expected)

def test_disturbance_like_structure():
    solver = SISOMasonSolver()

    data = {
        "edges": [
            ("R", "n1", "1"),
            ("n1", "n2", "1"),
            ("n2", "zd", "1"),
            ("zd", "n3", "G1"),
            ("n3", "C1", "1"),
        ],
        "source": "R",
        "sink": "C1",
    }

    solver.load_from_dict(data)
    T, _ = solver.solve()

    expected = sp.sympify("G1")
    assert_expr_equal(T, expected)

