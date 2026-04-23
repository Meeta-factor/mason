import sympy as sp
from typing import List, Tuple, Dict, Union, Optional, Any, TypeAlias
Node = str
Gain = sp.Expr
RawGain = Union[str, sp.Expr]
Path = List[Node]
Loop = List[Node]
Edge = Tuple[Node, Node, RawGain]
TransferResult: TypeAlias = tuple[Gain, dict[str, Any]]