"""부서별 권한 매트릭스. MVP는 사이드바 dropdown 기반.

부서 코드: '재무팀' (admin) / '예산팀' (editor) / '법인' (viewer)
"""

from __future__ import annotations

DEPARTMENTS = ["재무팀", "예산팀", "법인"]
ROLE = {"재무팀": "admin", "예산팀": "editor", "법인": "viewer"}

# 예산팀이 편집할 수 있는 연도 (budget 연도만)
BUDGET_YEARS = ["25예산", "26예산", "27예산", "28예산"]


def role(dept: str) -> str:
    return ROLE.get(dept, "viewer")


def can_edit_cell(dept: str, year_label: str, is_calc: bool) -> bool:
    """주어진 (부서, 연도, 셀종류) 조합에서 편집 가능 여부."""
    if is_calc:
        return False
    r = role(dept)
    if r == "admin":
        return True
    if r == "editor":
        return year_label in BUDGET_YEARS
    return False


def can_upload(dept: str) -> bool:
    return role(dept) == "admin"


def can_view_audit(dept: str) -> bool:
    return role(dept) == "admin"


def can_comment(dept: str) -> bool:
    return role(dept) in ("admin", "editor", "viewer")


def disabled_years(dept: str) -> list[str]:
    """st.data_editor `disabled` 인자에 쓸 — 편집 불가 열 리스트."""
    r = role(dept)
    if r == "admin":
        return []
    if r == "editor":
        return [y for y in ["21회계", "22회계", "23회계", "24회계"]]
    # viewer
    return ["21회계", "22회계", "23회계", "24회계",
            "25예산", "26예산", "27예산", "28예산"]
