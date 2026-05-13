"""엑셀처럼 셀에 입력된 산식("=2+148")을 안전하게 평가한다.

이름/속성/함수 호출은 모두 거부 — 산술 연산자와 숫자만 허용한다.
"""

from __future__ import annotations

import ast
import operator as op

_BIN_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}

_UNARY_OPS = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}


class FormulaError(ValueError):
    pass


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise FormulaError(f"숫자가 아닙니다: {node.value!r}")
    if isinstance(node, ast.BinOp):
        fn = _BIN_OPS.get(type(node.op))
        if fn is None:
            raise FormulaError(f"허용되지 않은 연산자: {type(node.op).__name__}")
        return fn(_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        fn = _UNARY_OPS.get(type(node.op))
        if fn is None:
            raise FormulaError(f"허용되지 않은 단항 연산자: {type(node.op).__name__}")
        return fn(_eval_node(node.operand))
    raise FormulaError(f"허용되지 않은 표현: {type(node).__name__}")


def eval_cell(raw):
    """셀 입력값을 받아 (computed_value, normalized_raw) 튜플 반환.

    - None / 빈 문자열 → (None, "")
    - "150" / 150 → (150.0, "150")
    - "=2+148" → (150.0, "=2+148")
    - "2+148" (= 없이) → (150.0, "=2+148") — 자동으로 = 붙여 저장
    """
    if raw is None:
        return None, ""
    if isinstance(raw, (int, float)):
        return float(raw), str(raw)
    s = str(raw).strip()
    if s == "":
        return None, ""
    body = s[1:] if s.startswith("=") else s
    try:
        v = float(body)
        return v, body
    except ValueError:
        pass
    try:
        tree = ast.parse(body, mode="eval")
    except SyntaxError as e:
        raise FormulaError(f"수식 구문 오류: {body!r}") from e
    value = _eval_node(tree.body)
    return value, "=" + body


def display_value(computed):
    """대시보드/표 표시용 — None은 빈칸, 정수는 정수형으로."""
    if computed is None:
        return ""
    if float(computed).is_integer():
        return int(computed)
    return round(float(computed), 2)
