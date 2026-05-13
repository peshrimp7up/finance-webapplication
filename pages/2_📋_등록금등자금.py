"""시트1 — 등록금등자금 인라인 편집 페이지."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.audit import log_change
from src.auth import can_edit_cell, disabled_years, role
from src.cashflow_model import recalculate
from src.data_store import CATEGORIES, YEAR_LABELS
from src.formula_parser import FormulaError, display_value, eval_cell
from src.ui_common import setup_page


SHEET = "sheet1"
SHEET_TITLE = "1. 등록금등자금"


def _build_df() -> pd.DataFrame:
    cats_sorted = sorted(CATEGORIES[SHEET].values(), key=lambda c: c.row)
    rows = []
    for c in cats_sorted:
        prefix = "▶ " if c.is_calc else ("• " if c.parent_id else "■ ")
        row = {"항목": prefix + c.name}
        for y in YEAR_LABELS:
            entry = st.session_state["data"].get(SHEET, c.id, y)
            if c.is_calc:
                row[y] = display_value(entry["value"])
            else:
                row[y] = entry["raw"] if entry["raw"] else ""
        rows.append(row)
    return pd.DataFrame(rows)


def _apply_diff(edited: pd.DataFrame) -> None:
    """편집된 데이터프레임의 셀들을 검사해 변경분을 적용."""
    dept = st.session_state["dept"]
    data = st.session_state["data"]
    cats_sorted = sorted(CATEGORIES[SHEET].values(), key=lambda c: c.row)
    changes = 0
    errors: list[str] = []

    for i, c in enumerate(cats_sorted):
        if c.is_calc:
            continue
        for y in YEAR_LABELS:
            new_raw = edited.iloc[i][y]
            new_raw_str = "" if pd.isna(new_raw) else str(new_raw).strip()
            old_entry = data.get(SHEET, c.id, y)
            old_raw_str = old_entry["raw"] if old_entry["raw"] else ""
            if new_raw_str == old_raw_str:
                continue
            if not can_edit_cell(dept, y, c.is_calc):
                errors.append(f"권한 없음: {c.name} / {y}")
                continue
            try:
                value, normalized = eval_cell(new_raw_str)
            except FormulaError as e:
                errors.append(f"{c.name} / {y}: {e}")
                continue
            data.set(SHEET, c.id, y, normalized, value)
            log_change(dept, SHEET, c.id, c.name, y, old_entry.get("value"), value)
            changes += 1

    if changes > 0:
        recalculate(data)
        st.session_state["dirty"] = True
        st.success(f"{changes}개 셀 수정 적용됨")
    for msg in errors:
        st.error(msg)


def render() -> None:
    setup_page(SHEET_TITLE, "📋")
    st.title(f"📋 {SHEET_TITLE}")

    dept = st.session_state["dept"]
    r = role(dept)
    if r == "viewer":
        st.info("🔒 조회 전용입니다. 셀 편집은 재무팀/예산팀만 가능합니다.")
    elif r == "editor":
        st.info("ℹ️ 예산팀은 **25~28예산** 열만 편집할 수 있습니다.")
    st.caption(
        "▶ = 자동 계산 행 (편집 불가) │ ■ = 항목 소계 (자동) │ • = 입력 셀  "
        "│ `=2+148` 같은 산식 입력 가능"
    )

    df = _build_df()
    if r == "viewer":
        st.dataframe(df, use_container_width=True, hide_index=True)
        return

    disabled_cols = ["항목"] + disabled_years(dept)
    edited = st.data_editor(
        df,
        key=f"editor_{SHEET}",
        use_container_width=True,
        hide_index=True,
        disabled=disabled_cols,
        num_rows="fixed",
        column_config={
            "항목": st.column_config.TextColumn("항목", width="medium"),
            **{y: st.column_config.TextColumn(y, help="숫자 또는 =2+148 형태의 산식")
               for y in YEAR_LABELS},
        },
    )

    if not edited.equals(df):
        _apply_diff(edited)
        st.rerun()


render()
