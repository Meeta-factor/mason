import sympy as sp


# =========================================================
# 你原来的算子类：保持不变
# =========================================================

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


# =========================================================
# 1. 伯努利数：用旧约定，匹配 t/(e^t-1)
# =========================================================

def bernoulli_em(n):
    """
    Euler–Maclaurin 常用约定：
    B1 = -1/2
    """
    return sp.simplify((-1)**n * sp.bernoulli(n))


# =========================================================
# 2. 所有 m 组非负整数分拆：k1+...+km = n
# =========================================================

def compositions(n, m):
    if m == 1:
        yield (n,)
        return
    for k in range(n + 1):
        for rest in compositions(n - k, m - 1):
            yield (k,) + rest


# =========================================================
# 3. 用普通伯努利数卷积出广义伯努利系数 B_n^(m)
# =========================================================

def generalized_bernoulli_em(n, m):
    """
    B_n^(m) defined by:
        (t/(e^t - 1))^m = sum_{n>=0} B_n^(m) t^n / n!
    using the EM sign convention.
    """
    total = sp.Integer(0)
    for ks in compositions(n, m):
        term = sp.Integer(1)
        for k in ks:
            term *= bernoulli_em(k) / sp.factorial(k)
        total += term
    return sp.simplify(sp.factorial(n) * total) # type: ignore


# =========================================================
# 4. D 的正负幂作用
#    p >= 0: p 次微分
#    p < 0 : -p 次不定积分
# =========================================================

def apply_D_power(f, var, p):
    f = sp.sympify(f)
    var = sp.sympify(var)

    if p >= 0:
        return sp.diff(f, var, p)

    result = f
    for _ in range(-p):
        result = sp.integrate(result, var)
    return result


# =========================================================
# 5. Sigma^m 的截断展开项
#    Sigma^m ~ sum_{n=0}^N B_n^(m)/n! * D^(n-m)
# =========================================================

def sigma_power_terms(m, order):
    """
    返回列表 [(coeff, power), ...]
    表示 coeff * D^power
    """
    if not isinstance(m, int) or m < 1:
        raise ValueError("m must be a positive integer")
    if not isinstance(order, int) or order < 0:
        raise ValueError("order must be a nonnegative integer")

    terms = []
    for n in range(order + 1):
        coeff = sp.simplify(generalized_bernoulli_em(n, m) / sp.factorial(n))
        power = n - m
        terms.append((coeff, power))
    return terms


# =========================================================
# 6. 把展开打印成算子形式
# =========================================================

def sigma_power_operator_str(m, order, symbol='D'):
    pieces = []
    for coeff, power in sigma_power_terms(m, order):
        coeff_s = sp.sstr(sp.simplify(coeff))

        if power == 0:
            pieces.append(f"{coeff_s}")
        elif power == 1:
            pieces.append(f"{coeff_s}*{symbol}")
        else:
            pieces.append(f"{coeff_s}*{symbol}**({power})")

    s = " + ".join(pieces)
    return s.replace("+ -", "- ")


# =========================================================
# 7. 让截断展开作用到 f(x)
# =========================================================

def sigma_power_expand_apply(f, var, m, order):
    """
    返回截断展开后的近似：
        Sigma^m f ~ sum_{n=0}^N B_n^(m)/n! * D^(n-m) f
    """
    result = sp.Integer(0)
    for coeff, power in sigma_power_terms(m, order):
        result += coeff * apply_D_power(f, var, power)
    return sp.simplify(sp.expand(result))


# =========================================================
# 8. 真正的 Sigma^m 直接作用：用于对照验证
# =========================================================

def sigma_power_exact_apply(f, var, m, lower=0):
    Sigma = SigmaOperator(var, lower=lower)
    return (Sigma**m)(f)


# =========================================================
# 9. 生成函数验证：
#    (t/(e^t-1))^m 与卷积结果是否一致
# =========================================================

def verify_generalized_bernoulli(m, order):
    t = sp.symbols('t')
    left = sp.series((t / (sp.exp(t) - 1))**m, t, 0, order + 1).removeO().expand() # type: ignore

    right = sp.Integer(0)
    for n in range(order + 1):
        right += generalized_bernoulli_em(n, m) * t**n / sp.factorial(n)
    right = sp.expand(right)

    return sp.simplify(left - right)


# =========================================================
# 10. 使用示例
# =========================================================

if __name__ == "__main__":
    x = sp.symbols('x')
    f = x**3


    print("=== verify generating function ===")
    print(verify_generalized_bernoulli(m=3, order=6))   # 应该输出 0

    print("\n=== Sigma^2 operator expansion ===")
    print(sigma_power_operator_str(m=2, order=6))

    print("\n=== Sigma^3 operator expansion ===")
    print(sigma_power_operator_str(m=3, order=6))

    print("\n=== apply expansion to f(x)=x^3 ===")
    approx = sigma_power_expand_apply(f, x, m=2, order=6)
    print(approx)

    print("\n=== exact Sigma^2 applied to x^3 ===")
    exact = sigma_power_exact_apply(f, x, m=2, lower=0)
    print(sp.expand(exact))

