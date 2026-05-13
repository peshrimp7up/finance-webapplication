"""변경 이력 페이지 (관리자 전용)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.audit import read_log
from src.auth import can_view_audit, role
from src.ui_common import setup_page


def render() -> None:
    setup_page("변경 이력", "📜")
    st.title("📜 변경 이력")

    dept = st.session_state["dept"]
    if not can_view_audit(dept):
        st.error(f"🔒 변경 이력은 **재무팀(관리자)** 만 조회할 수 있습니다. (현재: {dept})")
        return

    rows = read_log()
    if not rows:
        st.info("아직 변경 이력이 없습니다. 셀을 수정해 보세요.")
        return

    df = pd.DataFrame(rows)
    df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)

    # 필터
    col1, col2, col3 = st.columns(3)
    with col1:
        sheet_filter = st.selectbox(
            "시트", ["전체", "sheet1", "sheet2"], index=0
        )
    with col2:
        dept_filter = st.selectbox(
            "부서", ["전체"] + sorted(df["dept"].unique().tolist()), index=0
        )
    with col3:
        year_filter = st.selectbox(
            "연도", ["전체"] + sorted(df["year"].unique().tolist()), index=0
        )

    filtered = df.copy()
    if sheet_filter != "전체":
        filtered = filtered[filtered["sheet"] == sheet_filter]
    if dept_filter != "전체":
        filtered = filtered[filtered["dept"] == dept_filter]
    if year_filter != "전체":
        filtered = filtered[filtered["year"] == year_filter]

    st.caption(f"총 {len(filtered)}건")
    st.dataframe(
        filtered.rename(columns={
            "timestamp": "시각",
            "dept": "부서",
            "sheet": "시트",
            "category_name": "항목",
            "year": "연도",
            "before": "이전값",
            "after": "변경값",
        })[["시각", "부서", "시트", "항목", "연도", "이전값", "변경값"]],
        hide_index=True,
        use_container_width=True,
    )

    csv_bytes = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ CSV 다운로드",
        data=csv_bytes,
        file_name="audit_log.csv",
        mime="text/csv",
    )


render()
