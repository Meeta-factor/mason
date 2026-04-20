import sympy as sp

class Operator:
    def apply(self, f):
        raise NotImplementedError

    def __call__(self, f):
        return self.apply(sp.sympify(f))

    def __matmul__(self, other):
        return CompositeOperator(self, other)

    def __pow__(self, m):
        if not isinstance(m, int) or m < 1:
            raise ValueError("m must be a positive integer")
        op = self
        for _ in range(m - 1):
            op = op @ self
        return op


class CompositeOperator(Operator):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def apply(self, f):
        return self.left(self.right(f))


class ShiftOperator(Operator):
    def __init__(self, var, step=1):
        self.var = sp.sympify(var)
        self.step = step

    def apply(self, f):
        # return f.subs(self.var, self.var + self.step)
        return sp.expand(f.xreplace({self.var: self.var + self.step}))


class DeltaOperator(Operator):
    def __init__(self, var):
        self.var = sp.sympify(var)
        self.E = ShiftOperator(var)

    def apply(self, f):
        return sp.simplify(self.E(f) - f)


class SigmaOperator(Operator):
    def __init__(self, var, lower=0):
        self.var = sp.sympify(var)
        self.lower = lower

    def apply(self, f):
        k = sp.Dummy('k')
        return sp.summation(f.subs(self.var, k), (k, self.lower, self.var - 1))


class DOperator(Operator):
    def __init__(self, var):
        self.var = sp.sympify(var)

    def apply(self, f):
        return sp.diff(f, self.var)


class IntegralOperator(Operator):
    def __init__(self, var):
        self.var = sp.sympify(var)

    def apply(self, f):
        return sp.integrate(f, self.var)