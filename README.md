![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
# Mason Solver

> Symbolic Mason Gain Formula Solver for Control Systems
> 基于符号计算的信号流图传递函数求解工具

---

## 📌 项目简介

本项目实现了 **Mason 增益公式（Mason's Gain Formula）** 的自动化求解，支持：

* 单输入单输出（SISO）系统
* 多输入多输出（MIMO）系统
* 符号表达（基于 `sympy`）
* 信号流图建模
* 自动路径、回路与系统行列式计算
* 传递矩阵生成

适用于：

* 自动控制原理课程
* 控制系统建模与分析
* 教学与验证工具
* 符号推导与科研辅助

---

## ⚙️ 安装方式
```bash
git clone https://github.com/Meeta-factor/mason.git
cd mason
pip install -e .
python examples/siso_sfg.py
```

推荐使用虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
```

开发模式安装：

```bash
pip install -e .
```

---

## 🚀 快速开始

### 1️⃣ 构建系统

```python
from mason.solver import MIMOMasonSolver

solver = MIMOMasonSolver()

data = {
    "edges": [
        ("R1", "C1", "G11"),
        ("R1", "C2", "G12"),
        ("R2", "C1", "G21"),
        ("R2", "C2", "G22"),
    ],
    "sources": ["R1", "R2"],
    "sinks": ["C1", "C2"],
}

solver.load_from_dict(data)
```

---

### 2️⃣ 计算传递矩阵

```python
G = solver.transfer_matrix(
    sources=data["sources"],
    sinks=data["sinks"]
)

print(G)
```

输出：

```
Matrix([
[G11, G21],
[G12, G22]
])
```

---

### 3️⃣ 数学含义

该矩阵满足：

$$
\mathbf{y} = G(s)\mathbf{u}
$$

其中：

* 行 → 输出（sinks）
* 列 → 输入（sources）
* $ G_{ij} $ 表示：第 j 个输入到第 i 个输出的传递函数

---

### 4️⃣ 查看详细推导过程

```python
G, info = solver.transfer_matrix(..., return_info=True)

from mason.visualize import show_result
show_result(info[0][0])  # 查看某个传函
```

展示内容包括：

* Forward Paths（前向通路）
* Loops（回路）
* $\Delta$（系统行列式）
* $\Delta_k$（非接触回路修正项）

---

## 🎉 Examples

- `examples/siso_sfg.py` – basic usage
- `examples/mimo_sfg.py` – multi-input multi-output system
- `examples/feedback_system.py` – classic control example

---

## 📊 功能特性

* ✅ 自动枚举前向路径
* ✅ 自动检测回路与非接触回路
* ✅ 符号计算支持（SymPy）
* ✅ 支持复杂反馈结构
* ✅ MIMO 传递矩阵
* ✅ 无路径自动填 0
* ✅ pytest 自动验证

---

## 🧪 测试

运行测试：

```bash
pytest -v
```

当前测试覆盖：

* 无环系统
* 单反馈环
* 多回路系统
* MIMO 系统
* 耦合与非耦合结构

---

## 📁 项目结构

```
mason/
├── solver.py        # 核心算法（Mason公式）
├── visualize.py     # 可视化与结果展示
├── typing_defs.py   # 类型定义
tests/
├── test_siso.py
├── test_mimo.py
examples/
├── siso_sfg.py
├── mimo_sfg.py
├── feedback_system.py
├── from_csv.py
```

---

## 🧠 理论基础

Mason 增益公式：

$$
T = \frac{\sum_k P_k \Delta_k}{\Delta}
$$

其中：

*  $P_k $：第 k 条前向路径
*  $\Delta$：系统行列式
*  $\Delta_k$ ：与路径不接触的回路组成的行列式

---

## 📌 适用方向

* 自动控制原理
* 信号与系统
* 控制系统建模
* 最优控制（预处理工具）
* 符号推导验证

---

## 🧩 未来计划

* [ ] 状态空间转换
* [ ] 控制系统解耦分析
* [ ] LQR / 最优控制接口
* [ ] GUI 或 Web 可视化
* [ ] 自动生成报告（LaTeX）

---

## 👤 作者

* Meta(Meeta-factor)（Control Engineering Student）

---

## 📜 License

This project is licensed under the MIT License.
