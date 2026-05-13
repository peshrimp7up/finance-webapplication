"""모든 Streamlit 페이지가 공유하는 사이드바 + 세션 초기화 로직."""

from __future__ import annotations

import io

import streamlit as st

from .auth import DEPARTMENTS, role
from .cashflow_model import recalculate
from .data_store import XLSX_PATH, load_from_xlsx, save_to_xlsx


def init_session() -> None:
    if "data" not in st.session_state:
        data = load_from_xlsx()
        recalculate(data)
        st.session_state["data"] = data
    if "dept" not in st.session_state:
        st.session_state["dept"] = DEPARTMENTS[0]
    if "dirty" not in st.session_state:
        st.session_state["dirty"] = False


def reload_from_disk() -> None:
    data = load_from_xlsx()
    recalculate(data)
    st.session_state["data"] = data
    st.session_state["dirty"] = False


def render_sidebar() -> None:
    with st.sidebar:
        st.title("💰 자금수지 관리")
        st.session_state["dept"] = st.selectbox(
            "부서 선택",
            DEPARTMENTS,
            index=DEPARTMENTS.index(st.session_state["dept"]),
            key="dept_select",
        )
        r = role(st.session_state["dept"])
        badge = {"admin": "🟢 관리자", "editor": "🟡 편집자", "viewer": "⚪ 조회자"}[r]
        st.caption(f"권한: {badge}")
        if st.session_state.get("dirty"):
            st.warning("⚠️ 저장되지 않은 변경분이 있습니다")
        st.divider()

        if st.button("🔄 디스크에서 새로고침", use_container_width=True):
            reload_from_disk()
            st.rerun()

        if r == "admin":
            if st.button("💾 엑셀 파일에 저장", use_container_width=True, type="primary"):
                save_to_xlsx(st.session_state["data"])
                st.session_state["dirty"] = False
                st.success("저장 완료")

        # 엑셀 다운로드 (현재 메모리 상태 기준)
        if XLSX_PATH.exists():
            save_to_xlsx(st.session_state["data"])  # 메모리→디스크 동기화 후 읽기
            with open(XLSX_PATH, "rb") as f:
                buf = io.BytesIO(f.read())
            st.download_button(
                "⬇️ 엑셀 다운로드",
                data=buf,
                file_name="대학자금수지.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        st.divider()
        st.caption("📄 페이지")
        st.caption("• 📊 대시보드")
        st.caption("• 📋 등록금등자금")
        st.caption("• 📋 목적자금")
        st.caption("• 📜 변경 이력")


def setup_page(title: str, icon: str = "💰") -> None:
    """모든 페이지가 호출하는 진입 헬퍼."""
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_session()
    render_sidebar()
