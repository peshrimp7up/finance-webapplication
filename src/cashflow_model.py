"""자금흐름 재계산 엔진.

각 시트의 입력 셀들로부터 소계(B, C, F), 과부족(D), 이월(A, G) 을 연쇄적으로 계산한다.
"""

from __future__ import annotations

from .data_store import (
    CATEGORIES,
    YEAR_LABELS,
    CashflowData,
)


# 시트별 계산에 쓰이는 카테고리 id 묶음
_SHEET1_INCOME_GROUPS = ["s1.inc_tuition", "s1.inc_other", "s1.inc_gov"]
_SHEET1_EXPENSE_GROUPS = ["s1.exp_salary", "s1.exp_admin", "s1.exp_research", "s1.exp_capex"]
_SHEET1_NONOP_ITEMS = [
    "s1.nonop.science", "s1.nonop.land", "s1.nonop.future",
    "s1.nonop.medical", "s1.nonop.loan_interest",
]

_SHEET2_INCOME_GROUPS = ["s2.inc_gov", "s2.inc_clinic", "s2.inc_legal", "s2.inc_special"]
_SHEET2_EXPENSE_GROUPS = ["s2.exp_scholar", "s2.exp_clinic", "s2.exp_legal", "s2.exp_special"]


def _sum_children(data: CashflowData, sheet: str, parent_id: str, year: str) -> float:
    """소계 행: parent_id 하위 세부항목 값의 합."""
    cats = CATEGORIES[sheet]
    total = 0.0
    for child_id in cats[parent_id].children_ids:
        v = data.get(sheet, child_id, year)["value"]
        if v is not None:
            total += v
    return total


def _sum_ids(data: CashflowData, sheet: str, ids: list[str], year: str) -> float:
    total = 0.0
    for cid in ids:
        v = data.get(sheet, cid, year)["value"]
        if v is not None:
            total += v
    return total


def recalculate_sheet1(data: CashflowData) -> None:
    """시트1 전체 재계산. 모든 연도를 순서대로 순회하면서
    A[y] = G[y-1], 그리고 B/C/D/F/G를 결정한다.
    A[21회계]는 사용자가 입력한 시드값을 그대로 둔다 (없으면 0).
    """
    sheet = "sheet1"
    prev_G: float = 0.0
    for idx, year in enumerate(YEAR_LABELS):
        # 1) 입력 항목 소계들 (자식이 있는 is_subtotal 행)
        for parent_id in _SHEET1_INCOME_GROUPS + _SHEET1_EXPENSE_GROUPS:
            v = _sum_children(data, sheet, parent_id, year)
            data.set(sheet, parent_id, year, "", v)

        # 2) B = 경상수입 합 (3개 그룹 소계의 합)
        B = _sum_ids(data, sheet, _SHEET1_INCOME_GROUPS, year)
        data.set(sheet, "s1.subtotal_B", year, "", B)

        # 3) C = 경상지출 합
        C = _sum_ids(data, sheet, _SHEET1_EXPENSE_GROUPS, year)
        data.set(sheet, "s1.subtotal_C", year, "", C)

        # 4) D = B - C
        D = B - C
        data.set(sheet, "s1.delta_D", year, "", D)

        # 5) F = 비경상지출 합
        F = _sum_ids(data, sheet, _SHEET1_NONOP_ITEMS, year)
        data.set(sheet, "s1.nonop_F", year, "", F)

        # 6) E = 부족액충당 (입력)
        E_entry = data.get(sheet, "s1.makeup_E", year)
        E = E_entry["value"] if E_entry["value"] is not None else 0.0

        # 7) A = G[y-1]; 첫 해는 시드 입력 사용 (없으면 0)
        if idx == 0:
            seed = data.get(sheet, "s1.carryover_A", year)
            A = seed["value"] if seed["value"] is not None else 0.0
        else:
            A = prev_G
            data.set(sheet, "s1.carryover_A", year, "", A)

        # 8) G = A + D + E - F
        G = A + D + E - F
        data.set(sheet, "s1.carryover_G", year, "", G)
        prev_G = G


def recalculate_sheet2(data: CashflowData) -> None:
    """시트2 재계산.
    G = A + D (E, F 없음). A[21회계] = 0 (원본 양식 시드).
    """
    sheet = "sheet2"
    prev_G: float = 0.0
    for idx, year in enumerate(YEAR_LABELS):
        for parent_id in _SHEET2_INCOME_GROUPS + _SHEET2_EXPENSE_GROUPS:
            v = _sum_children(data, sheet, parent_id, year)
            data.set(sheet, parent_id, year, "", v)

        B = _sum_ids(data, sheet, _SHEET2_INCOME_GROUPS, year)
        data.set(sheet, "s2.subtotal_B", year, "", B)

        C = _sum_ids(data, sheet, _SHEET2_EXPENSE_GROUPS, year)
        data.set(sheet, "s2.subtotal_C", year, "", C)

        D = B - C
        data.set(sheet, "s2.delta_D", year, "", D)

        if idx == 0:
            seed = data.get(sheet, "s2.carryover_A", year)
            A = seed["value"] if seed["value"] is not None else 0.0
            data.set(sheet, "s2.carryover_A", year, seed["raw"] or "0", A)
        else:
            A = prev_G
            data.set(sheet, "s2.carryover_A", year, "", A)

        G = A + D
        data.set(sheet, "s2.carryover_G", year, "", G)
        prev_G = G


def recalculate(data: CashflowData) -> None:
    recalculate_sheet1(data)
    recalculate_sheet2(data)
