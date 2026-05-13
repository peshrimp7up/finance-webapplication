"""대학 자금수지 관리 웹앱 — 메인 진입 페이지.

`pages/` 폴더의 다른 페이지로 자동 라우팅된다 (Streamlit multipage).
"""

from __future__ import annotations

import streamlit as st

from src.auth import role
from src.data_store import XLSX_PATH
from src.ui_common import setup_page


def main() -> None:
    setup_page("대학 자금수지 관리", "💰")

    st.title("💰 대학 자금수지 관리 웹앱")
    st.markdown(
        """
        이 앱은 **등록금등자금**과 **목적자금** 두 가지 자금 흐름을 관리합니다.

        매년 다음 식으로 차기 이월금이 계산되고 다음 해의 전기 이월금으로 넘어갑니다.
        ```
        차기 이월 G = 전기 이월 A + 당기 과부족 D + 부족액충당 E − 비경상지출 F
                     (단, 목적자금은 G = A + D)
        ```
        """
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("부서", st.session_state["dept"])
    with col2:
        st.metric("권한", role(st.session_state["dept"]))
    with col3:
        st.metric("작업 파일", XLSX_PATH.name)

    st.divider()

    st.markdown(
        """
        ### 사용 방법
        1. 좌측 사이드바에서 **부서**를 선택하세요. 부서별로 편집 가능한 연도가 다릅니다.
           - **재무팀**(관리자): 모든 연도 편집 + 저장 + 변경이력 조회
           - **예산팀**(편집자): 25~28예산 열만 편집 가능
           - **법인**(조회자): 조회 전용
        2. **📋 등록금등자금** 또는 **📋 목적자금** 페이지에서 셀을 클릭해 값을 수정합니다.
           - `=2+148` 같이 엑셀 산식 입력이 가능합니다 (안전한 산술 연산만 허용).
           - 계산 행(소계, 과부족, 이월)은 자동으로 갱신됩니다.
        3. 수정이 끝나면 사이드바의 **💾 엑셀 파일에 저장** 버튼으로 디스크에 반영합니다.
           다른 부서가 디스크에서 새로고침해야 변경분을 볼 수 있습니다.
        4. **📊 대시보드**에서 연도별 수입·지출·이월 추이를 확인할 수 있습니다.
        5. **📜 변경 이력**(관리자만)에서 누가 언제 무엇을 수정했는지 추적할 수 있습니다.
        """
    )


main()
