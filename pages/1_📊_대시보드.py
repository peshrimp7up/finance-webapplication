"""대시보드 — 연도별 수입/지출/과부족/이월 차트와 요약 카드."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.data_store import YEAR_LABELS
from src.ui_common import setup_page


def _series(sheet: str, cat_id: str) -> list[float]:
    return [
        st.session_state["data"].get(sheet, cat_id, y)["value"] or 0.0
        for y in YEAR_LABELS
    ]


def _format(v: float) -> str:
    sign = "▲" if v > 0 else ("▼" if v < 0 else "•")
    return f"{sign} {abs(int(round(v)))}억"


def render() -> None:
    setup_page("대시보드", "📊")
    st.title("📊 자금수지 대시보드")
    st.caption("단위: 억원")

    # 선택 연도
    selected_year = st.selectbox("연도", YEAR_LABELS, index=4)  # 25예산 기본
    idx = YEAR_LABELS.index(selected_year)

    s1_B = _series("sheet1", "s1.subtotal_B")
    s1_C = _series("sheet1", "s1.subtotal_C")
    s1_D = _series("sheet1", "s1.delta_D")
    s1_F = _series("sheet1", "s1.nonop_F")
    s1_A = _series("sheet1", "s1.carryover_A")
    s1_G = _series("sheet1", "s1.carryover_G")
    s2_B = _series("sheet2", "s2.subtotal_B")
    s2_C = _series("sheet2", "s2.subtotal_C")
    s2_G = _series("sheet2", "s2.carryover_G")

    # 요약 카드 4개 (시트1 기준 선택 연도)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"{selected_year} 경상수입 B", f"{int(s1_B[idx])}억", help="등록금+기타+국고보조")
    c2.metric(f"{selected_year} 경상지출 C", f"{int(s1_C[idx])}억", help="보수+관리+연구학생+고정자산")
    delta = s1_D[idx]
    c3.metric(f"{selected_year} 당기 과부족 D", _format(delta))
    c4.metric(f"{selected_year} 차기 이월 G", _format(s1_G[idx]))

    st.divider()

    # 차트 1: 시트1 — 수입/지출 막대 + 과부족 라인
    st.subheader("등록금등자금: 수입·지출 추이")
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(
        go.Bar(x=YEAR_LABELS, y=s1_B, name="경상수입 B", marker_color="#1D9E75"),
        secondary_y=False,
    )
    fig1.add_trace(
        go.Bar(x=YEAR_LABELS, y=s1_C, name="경상지출 C", marker_color="#E24B4A"),
        secondary_y=False,
    )
    fig1.add_trace(
        go.Scatter(x=YEAR_LABELS, y=s1_D, name="당기 과부족 D",
                   mode="lines+markers", line=dict(color="#185FA5", width=3)),
        secondary_y=True,
    )
    fig1.update_layout(
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=420,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    fig1.update_yaxes(title_text="금액(억)", secondary_y=False)
    fig1.update_yaxes(title_text="과부족(억)", secondary_y=True)
    st.plotly_chart(fig1, use_container_width=True)

    # 차트 2: 시트1 — 누적 이월
    st.subheader("등록금등자금: 차기 이월 누적 추이")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=YEAR_LABELS, y=s1_A, name="전기 이월 A",
        mode="lines+markers", line=dict(color="#9CA3AF", dash="dot"),
    ))
    fig2.add_trace(go.Scatter(
        x=YEAR_LABELS, y=s1_G, name="차기 이월 G",
        mode="lines+markers", line=dict(color="#185FA5", width=3),
        fill="tozeroy", fillcolor="rgba(24,95,165,0.1)",
    ))
    fig2.add_hline(y=0, line_dash="dash", line_color="#888")
    fig2.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # 차트 3: 시트2 — 목적자금
    st.subheader("목적자금: 수입·지출")
    col_l, col_r = st.columns([3, 2])
    with col_l:
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=YEAR_LABELS, y=s2_B, name="목적수입 B", marker_color="#1D9E75"))
        fig3.add_trace(go.Bar(x=YEAR_LABELS, y=s2_C, name="목적지출 C", marker_color="#E24B4A"))
        fig3.update_layout(
            barmode="group",
            height=340,
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig3, use_container_width=True)
    with col_r:
        # 요약 표
        df_summary = pd.DataFrame({
            "연도": YEAR_LABELS,
            "수입 B": [int(v) for v in s2_B],
            "지출 C": [int(v) for v in s2_C],
            "차기이월 G": [int(v) for v in s2_G],
        })
        st.dataframe(df_summary, hide_index=True, use_container_width=True)

    st.divider()

    # 종합 표
    st.subheader("종합 요약 (단위: 억)")
    summary = pd.DataFrame({
        "연도": YEAR_LABELS,
        "[등록금] 수입 B": [int(v) for v in s1_B],
        "[등록금] 지출 C": [int(v) for v in s1_C],
        "[등록금] 과부족 D": [int(v) for v in s1_D],
        "[등록금] 비경상 F": [int(v) for v in s1_F],
        "[등록금] 차기이월 G": [int(v) for v in s1_G],
        "[목적] 수입 B": [int(v) for v in s2_B],
        "[목적] 지출 C": [int(v) for v in s2_C],
        "[목적] 차기이월 G": [int(v) for v in s2_G],
    })
    st.dataframe(summary, hide_index=True, use_container_width=True)


render()
