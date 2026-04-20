import sympy as sp

n, m = 2, 1

t = sp.symbols('t', real=True)

# state and control dimensions
A = sp.MatrixSymbol('A', n, n)
B = sp.MatrixSymbol('B', n, m)
Q = sp.MatrixSymbol('Q', n, n)
R = sp.MatrixSymbol('R', m, m)
P = sp.MatrixSymbol('P', n, n)

x = sp.MatrixSymbol('x', n, 1)
xdot = sp.MatrixSymbol('xdot', n, 1)
Pdot = sp.MatrixSymbol('Pdot', n, n)

Rinv = sp.MatrixSymbol('Rinv', m, m)   # later substitute R.inv() formally if needed

# optimal feedback u = -R^{-1} B^T P x
u = -Rinv * B.T * P * x

# running cost
f = (x.T * Q * x)[0, 0] + (u.T * R * u)[0, 0]

print("f =")
print(f)

# closed-loop xdot
Acl = A - B * Rinv * B.T * P
xdot_expr = Acl * x

# manual derivative of x^T M x style terms:
# d/dt (x^T Q x) = xdot^T Q x + x^T Q xdot
f1 = (xdot_expr.T * Q * x)[0, 0] + (x.T * Q * xdot_expr)[0, 0]

# second term: x^T P B R^{-1} B^T P x
S = P * B * Rinv * B.T * P
Sdot = Pdot * B * Rinv * B.T * P + P * B * Rinv * B.T * Pdot

f2 = (xdot_expr.T * S * x)[0, 0] + (x.T * Sdot * x)[0, 0] + (x.T * S * xdot_expr)[0, 0]

fp = sp.expand(f1 + f2)

print("\nf'(t) =")
print(fp)