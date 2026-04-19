from mason.solver import SISOMasonSolver
from mason.visualize import *
import sympy as sp
solver = SISOMasonSolver()

data = {
    "edges": [
        ("R", "n1", 1),
        ("n1", "n2", "G1"),
        ("n2", "C", "G2"),
        ("n2", "n1", "-H1"),
    ],
    "source": "R",
    "sink": "C",
}



solver.load_from_dict(data)

result,info = solver.transfer_function(source="R", sink="C")

print("Transfer function:")
print(result)
print(info)