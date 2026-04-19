import sympy as sp
import control as ct


class ControlAdapter:
    def __init__(self, s, subs_dict=None):
        self.s = s
        self.subs_dict = subs_dict or {}

    def _prepare_expr(self, expr):
        expr = sp.simplify(expr)
        if self.subs_dict:
            expr = expr.subs(self.subs_dict)
        expr = sp.cancel(sp.together(expr))

        extra = expr.free_symbols - {self.s}
        if extra:
            raise ValueError(f"表达式仍含未替换符号: {extra}")

        return expr

    def expr_to_tf(self, expr):
        expr = self._prepare_expr(expr)
        num_expr, den_expr = expr.as_numer_denom()

        num_poly = sp.Poly(num_expr, self.s)
        den_poly = sp.Poly(den_expr, self.s)

        num = [float(c.evalf()) for c in num_poly.all_coeffs()]
        den = [float(c.evalf()) for c in den_poly.all_coeffs()]

        return ct.tf(num, den)

    def matrix_to_tf(self, Gsym):
        nrows, ncols = Gsym.shape
        tf_array = []

        for i in range(nrows):
            row = []
            for j in range(ncols):
                row.append(self.expr_to_tf(Gsym[i, j]))
            tf_array.append(row)

        return ct.combine_tf(tf_array)

    def matrix_to_ss(self, Gsym):
        Gtf = self.matrix_to_tf(Gsym)
        return ct.ss(Gtf)