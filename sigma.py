import sympy as sp

class SigmaOperator:
    def __init__(self, var):
        self.var = sp.sympify(var)

    def apply(self, f):
        f = sp.sympify(f)
        k = sp.Dummy('k')
        return sp.summation(f.subs(self.var, k), (k, 1, self.var))

    def power(self, f, m):
        expr = sp.sympify(f)
        for _ in range(m):
            expr = self.apply(expr)
        return sp.simplify(expr)


if __name__ == "__main__":
    n = sp.symbols('n', integer=True, positive=True)
    Sigma_op = SigmaOperator(n)

    print("Sigma^1(1) =", Sigma_op.power(1, 1))
    print("Sigma^2(1) =", Sigma_op.power(1, 2))
    print("Sigma^3(1) =", Sigma_op.power(1, 3))
    print("Sigma^4(1) =", Sigma_op.power(1, 4))