from mason import MIMOMasonSolver
from mason.visualize import *
import pandas as pd
import sympy as sp
df = pd.read_csv("../mason/tikz/data.csv")
solver = MIMOMasonSolver()

data = {
    "edges": [
        (row.start, row.end, sp.sympify(row.gain))
        for _, row in df.iterrows()
    ],
    "sources": ["R1", "R2"],
    "sinks": ["C1", "C2"],
}

solver.load_from_dict(data)

Td1, info_d1 = solver.transfer_function("D", "C1")
Td2, info_d2 = solver.transfer_function("D", "C2")
R1C1, info_11 = solver.transfer_function("R1", "C1")
G, info = solver.transfer_matrix(
    sources=data["sources"],
    sinks=data["sinks"],
    return_info=True
)

print(Td1)
print(Td2)
print(R1C1)
print(G)