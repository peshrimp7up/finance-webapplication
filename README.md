# 대학 자금수지 관리 웹앱

대학 이사회 양식의 **등록금등자금 / 목적자금** 수지표를 웹으로 옮긴 Streamlit 앱입니다. 재무팀·예산팀·법인 3개 부서가 같은 데이터를 보고, 권한에 따라 셀을 인라인 편집할 수 있으며, 매년 자동으로 **차기 이월금**이 계산되어 다음 해 전기 이월금으로 연결됩니다.

## 자금흐름 식

```
당기 과부족 D = 경상수입 B − 경상지출 C
차기 이월 G   = 전기 이월 A + D + 부족액충당 E − 비경상지출 F
                (목적자금은 G = A + D)
```

이 G가 다음 해의 A로 들어가면서 8개 회계연도(21회계~28예산) 누적 흐름이 자동 계산됩니다.

## 빠른 시작 (로컬)

```bash
# 1) 가상환경 (선택)
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate # Mac/Linux

# 2) 의존성 설치
pip install -r requirements.txt

# 3) 앱 실행
streamlit run app.py
```

브라우저에서 자동으로 `http://localhost:8501` 가 열립니다.

## GitHub + Streamlit Cloud 배포

1. 이 리포지토리를 GitHub에 push (private도 가능)
2. https://share.streamlit.io 에서 GitHub 연결 → 이 리포 선택
3. 메인 파일: `app.py`
4. Python 버전: 3.11+
5. 배포 후 공유 URL을 부서에 안내

> ⚠️ Streamlit Cloud의 컨테이너 파일시스템은 휘발성이므로, 운영 단계에서는
> GitHub commit-back (PyGithub) 또는 Google Sheets / Supabase 같은 외부 저장소
> 연동이 필요합니다. MVP는 데모용 단일 인스턴스 기준입니다.

## 부서별 권한

| 부서 | 등록금등자금 | 목적자금 | 엑셀 다운로드 | 변경 이력 |
|---|---|---|---|---|
| 재무팀 (admin) | 전체 편집 + 저장 | 전체 편집 + 저장 | O | O |
| 예산팀 (editor) | 25~28예산 열만 | 25~28예산 열만 | O | X |
| 법인 (viewer) | 조회 전용 | 조회 전용 | O | X |

## 셀 편집

엑셀처럼 셀에 산식을 입력할 수 있습니다.
- 숫자: `150`
- 산식: `=2+148` → 150으로 평가, 원본 `=2+148` 보존
- 빈 칸: 입력 지우면 NULL

허용 연산자: `+ − × ÷ ( ) **`. 함수 호출/속성 접근은 차단됩니다.

## 디렉터리 구조

```
finance_webapp/
├── app.py                          # 진입 페이지
├── pages/
│   ├── 1_📊_대시보드.py
│   ├── 2_📋_등록금등자금.py
│   ├── 3_📋_목적자금.py
│   └── 4_📜_변경이력.py
├── src/
│   ├── data_store.py               # 엑셀 I/O + 카테고리 트리
│   ├── cashflow_model.py           # 소계/이월 재계산 엔진
│   ├── formula_parser.py           # 안전한 산식 평가
│   ├── auth.py                     # 부서 권한
│   ├── audit.py                    # 변경 이력 CSV
│   └── ui_common.py                # 사이드바 + 세션 초기화
├── data/
│   ├── cashflow.xlsx               # 작업본 (원본 이사회 양식 복사)
│   └── audit_log.csv               # 변경 이력 (자동 생성)
├── .streamlit/config.toml          # 테마
└── requirements.txt
```

## 향후 작업 (Phase 2)

- [ ] 셀 단위 코멘트(질의응답) 기능
- [ ] 엑셀 업로드 기능 (재무팀이 새 양식으로 갱신)
- [ ] Streamlit Cloud 영속화 (GitHub commit-back 또는 외부 DB)
- [ ] 실제 인증 (Streamlit Authenticator / SSO)
- [ ] 동시 편집 충돌 감지
