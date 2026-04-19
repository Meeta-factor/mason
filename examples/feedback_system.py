from mason.solver import SISOMasonSolver
import sympy as sp
solver = SISOMasonSolver()
G, H = sp.symbols('G H')

data = {
    "edges": [
        ("R", "C", G),
        ("C", "R", -H),
    ],
    "source": "R",
    "sink": "C",
}

solver = SISOMasonSolver()
solver.load_from_dict(data)

T = solver.transfer_function("R","C")

print("Expected: G / (1 + G*H)")
print("Result:", T)