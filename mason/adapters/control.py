import sympy as sp
import control as ct


def ensure_only_s(expr, s):
    extra = expr.free_symbols - {s}
    if extra:
        raise ValueError(f"表达式仍含未替换符号: {extra}")


def expr_to_tf(expr, s):
    expr = sp.cancel(sp.together(expr))
    ensure_only_s(expr, s)

    num_expr, den_expr = expr.as_numer_denom()
    num_poly = sp.Poly(num_expr, s)
    den_poly = sp.Poly(den_expr, s)

    num = [float(c) for c in num_poly.all_coeffs()]
    den = [float(c) for c in den_poly.all_coeffs()]

    return ct.tf(num, den)


def matrix_to_control_tf(Gsym, s, subs_dict=None):
    if subs_dict is not None:
        Gsym = Gsym.subs(subs_dict)

    nrows, ncols = Gsym.shape
    tf_array = []

    for i in range(nrows):
        row = []
        for j in range(ncols):
            expr = sp.simplify(Gsym[i, j])
            row.append(expr_to_tf(expr, s))
        tf_array.append(row)

    return ct.combine_tf(tf_array)

def matrix_to_control_ss(Gsym, s, subs_dict=None, minimal=False):
    """
    将 SymPy 传函矩阵 Gsym 转成 python-control 的 StateSpace 对象

    参数
    ----
    Gsym : sympy.Matrix
        元素为关于 s 的有理表达式
    s : sympy.Symbol
        拉普拉斯变量
    subs_dict : dict, optional
        参数代入字典
    minimal : bool, default=False
        是否做最小实现

    返回
    ----
    ss_sys : control.StateSpace
    """
    tf_sys = matrix_to_control_tf(Gsym, s, subs_dict=subs_dict)
    ss_sys = ct.tf2ss(tf_sys)

    if minimal:
        ss_sys = ct.minreal(ss_sys)

    return ss_sys

def matrix_to_ss_matrices(Gsym, s, subs_dict=None, minimal=False):
    ss_sys = matrix_to_control_ss(Gsym, s, subs_dict=subs_dict, minimal=minimal)
    return ss_sys.A, ss_sys.B, ss_sys.C, ss_sys.D # type: ignore