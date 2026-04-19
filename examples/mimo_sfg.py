from mason import MIMOMasonSolver
from mason.visualize import *
import sympy as sp
solver = MIMOMasonSolver()

G1, G2, a11, a12, a21, a22, sigma = sp.symbols('G1 G2 a11 a12 a21 a22 sigma')

data = {'edges': [
    ('R1', 'n1', 1),
    ('n1', 'n2', 1),
    ('n2', 'n3', G1),
    ('n3', 'C1', 1),
    ('R2', 'm1', 1),
    ('m1', 'm2', 1),
    ('m2', 'm3', G2),
    ('m3', 'C2', 1),
    ('n3', 'n1', -a11),
    ('m3', 'm1', -a22),
    ('n3', 'm2', -a12),
    ('m3', 'n2', -a21),
    ('D', 'm1', sigma)],
    'sources': ['R1', 'R2'],
    'sinks': ['C1', 'C2']}

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