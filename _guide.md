**대학 자금수지 관리 웹앱**

Claude Code 개발 가이드 --- DB 스키마 · 파일 구조 · 프롬프트 전문

재무팀 · 예산팀 · 법인 협업 플랫폼 \| 2026년 3월

**1. 시스템 개요**

이 문서는 대학 자금수지(등록금등자금/목적자금) 이사회 양식을 웹
플랫폼으로 전환하기 위한 완전한 개발 가이드입니다. 재무팀, 예산팀,
법인이 동일한 데이터를 실시간으로 조회·편집·공유할 수 있는 시스템을
구축합니다.

+-------------------------------------------------------------------+
| **분석된 엑셀 구조**                                              |
|                                                                   |
| 시트1: 등록금등자금 (경상수입/경상지출/비경상지출,                |
| 21\~28회계연도, 70행 x 22열) 시트2: 목적자금 (목적수입/목적지출,  |
| 21\~28회계연도, 42행 x 13열)                                      |
+-------------------------------------------------------------------+

**1-1. 핵심 기능 목록**

- 엑셀 파일 업로드 → DB 자동 파싱 및 저장

- 연도별·항목별 데이터 인라인 편집 (부서 권한 기반)

- 수입/지출 추이 차트 자동 시각화 (Chart.js)

- 부서별 코멘트 및 질의응답 기능

- 엑셀 다운로드 (현재 이사회 양식 그대로 재출력)

- 감사 로그 --- 누가 언제 무엇을 수정했는지 추적

**2. 프로젝트 파일 구조**

모노레포 구조로 백엔드(Node.js/Express)와 프론트엔드(React/Vite)를
분리합니다.

> cashflow-platform/
>
> ├── backend/
>
> │ ├── src/
>
> │ │ ├── app.js \# Express 앱 진입점
>
> │ │ ├── config/
>
> │ │ │ └── db.js \# PostgreSQL 연결 설정
>
> │ │ ├── middleware/
>
> │ │ │ ├── auth.js \# JWT 인증 미들웨어
>
> │ │ │ └── rbac.js \# 역할 기반 권한 제어
>
> │ │ ├── routes/
>
> │ │ │ ├── auth.js \# POST /api/auth/login
>
> │ │ │ ├── cashflow.js \# CRUD /api/cashflow
>
> │ │ │ ├── upload.js \# POST /api/upload/excel
>
> │ │ │ ├── comments.js \# /api/comments
>
> │ │ │ └── export.js \# GET /api/export/excel
>
> │ │ ├── services/
>
> │ │ │ ├── excelParser.js \# xlsx → DB 파싱 로직
>
> │ │ │ ├── excelExporter.js \# DB → xlsx 재출력
>
> │ │ │ └── auditLog.js \# 변경 이력 기록
>
> │ │ └── models/
>
> │ │ └── index.js \# DB 쿼리 함수
>
> │ ├── migrations/
>
> │ │ ├── 001_create_tables.sql
>
> │ │ └── 002_seed_data.sql
>
> │ ├── Dockerfile
>
> │ └── package.json
>
> ├── frontend/
>
> │ ├── src/
>
> │ │ ├── main.jsx \# React 진입점
>
> │ │ ├── App.jsx \# 라우터 설정
>
> │ │ ├── pages/
>
> │ │ │ ├── Dashboard.jsx \# 메인 대시보드
>
> │ │ │ ├── Sheet1.jsx \# 등록금등자금 편집
>
> │ │ │ ├── Sheet2.jsx \# 목적자금 편집
>
> │ │ │ ├── Upload.jsx \# 엑셀 업로드
>
> │ │ │ └── AuditLog.jsx \# 변경 이력
>
> │ │ ├── components/
>
> │ │ │ ├── CashflowTable.jsx \# 인라인 편집 테이블
>
> │ │ │ ├── ChartPanel.jsx \# Chart.js 래퍼
>
> │ │ │ ├── CommentBox.jsx \# 코멘트 UI
>
> │ │ │ └── YearSelector.jsx \# 연도 필터
>
> │ │ ├── hooks/
>
> │ │ │ ├── useCashflow.js \# API 연동 훅
>
> │ │ │ └── useAuth.js \# 인증 훅
>
> │ │ └── api/
>
> │ │ └── client.js \# Axios 인스턴스
>
> │ ├── Dockerfile
>
> │ └── package.json
>
> ├── nginx/
>
> │ └── nginx.conf \# 리버스 프록시
>
> └── docker-compose.yml

**3. DB 스키마 (PostgreSQL)**

총 6개 테이블로 구성됩니다. 엑셀의 계층적 구조(구분→항목→세부항목)를
parent_id로 표현합니다.

**3-1. 테이블 목록**

  -------------------------------------------------------------------------
  **테이블명**          **역할**               **핵심 컬럼**
  --------------------- ---------------------- ----------------------------
  users                 사용자 및 부서/권한    id, name, email, department,
                        관리                   role

  fiscal_years          회계연도 메타 정보     id, label, year_code,
                                               type(actual/budget)

  cashflow_categories   구분·항목·세부항목     id, sheet, parent_id, name,
                        트리                   sort_order

  cashflow_values       연도별 금액 데이터     id, category_id,
                                               fiscal_year_id, amount_100m

  comments              항목별 코멘트/질의     id, category_id,
                                               fiscal_year_id, user_id,
                                               body

  audit_logs            수정 이력 추적         id, user_id, category_id,
                                               old_val, new_val, changed_at
  -------------------------------------------------------------------------

**3-2. DDL 전문**

> \-- 1. 사용자
>
> CREATE TABLE users (
>
> id SERIAL PRIMARY KEY,
>
> name VARCHAR(50) NOT NULL,
>
> email VARCHAR(100) UNIQUE NOT NULL,
>
> password_hash TEXT NOT NULL,
>
> department VARCHAR(30) CHECK (department IN
> (\'재무팀\',\'예산팀\',\'법인\',\'이사회\')),
>
> role VARCHAR(20) CHECK (role IN (\'admin\',\'editor\',\'viewer\'))
> DEFAULT \'viewer\',
>
> created_at TIMESTAMPTZ DEFAULT now()
>
> );
>
> \-- 2. 회계연도
>
> CREATE TABLE fiscal_years (
>
> id SERIAL PRIMARY KEY,
>
> label VARCHAR(10) NOT NULL, \-- 예: \"25예산\", \"24회계\"
>
> year_code SMALLINT NOT NULL, \-- 예: 25
>
> type VARCHAR(10) CHECK (type IN (\'actual\',\'budget\')) NOT NULL,
>
> UNIQUE(year_code, type)
>
> );
>
> \-- 시드: INSERT INTO fiscal_years(label,year_code,type) VALUES
>
> \--
> (\'21회계\',21,\'actual\'),(\'22회계\',22,\'actual\'),(\'23회계\',23,\'actual\'),
>
> \--
> (\'24회계\',24,\'actual\'),(\'25예산\',25,\'budget\'),(\'26예산\',26,\'budget\'),
>
> \-- (\'27예산\',27,\'budget\'),(\'28예산\',28,\'budget\');
>
> \-- 3. 항목 트리 (시트1/시트2 공통)
>
> CREATE TABLE cashflow_categories (
>
> id SERIAL PRIMARY KEY,
>
> sheet VARCHAR(10) CHECK (sheet IN (\'sheet1\',\'sheet2\')) NOT NULL,
>
> type VARCHAR(10) CHECK (type IN (\'income\',\'expense\',\'extra\'))
> NOT NULL,
>
> parent_id INT REFERENCES cashflow_categories(id),
>
> name VARCHAR(100) NOT NULL,
>
> is_subtotal BOOLEAN DEFAULT false, \-- 소계 행 여부
>
> sort_order SMALLINT NOT NULL
>
> );
>
> \-- 4. 금액 (단위: 억원)
>
> CREATE TABLE cashflow_values (
>
> id SERIAL PRIMARY KEY,
>
> category_id INT NOT NULL REFERENCES cashflow_categories(id),
>
> fiscal_year_id INT NOT NULL REFERENCES fiscal_years(id),
>
> amount_100m NUMERIC(10,2), \-- NULL = 해당없음, 0 = 예산 미정
>
> UNIQUE(category_id, fiscal_year_id)
>
> );
>
> \-- 5. 코멘트
>
> CREATE TABLE comments (
>
> id SERIAL PRIMARY KEY,
>
> category_id INT NOT NULL REFERENCES cashflow_categories(id),
>
> fiscal_year_id INT REFERENCES fiscal_years(id),
>
> user_id INT NOT NULL REFERENCES users(id),
>
> body TEXT NOT NULL,
>
> created_at TIMESTAMPTZ DEFAULT now()
>
> );
>
> \-- 6. 감사 로그
>
> CREATE TABLE audit_logs (
>
> id SERIAL PRIMARY KEY,
>
> user_id INT NOT NULL REFERENCES users(id),
>
> category_id INT NOT NULL REFERENCES cashflow_categories(id),
>
> fiscal_year_id INT NOT NULL REFERENCES fiscal_years(id),
>
> old_value NUMERIC(10,2),
>
> new_value NUMERIC(10,2),
>
> changed_at TIMESTAMPTZ DEFAULT now()
>
> );

**4. 권한 (RBAC) 설계**

  ----------------------------------------------------------------------------
  **부서/역할**   **대시보드   **데이터    **코멘트    **파일     **감사
                  조회**       편집**      작성**      업로드**   로그**
  --------------- ------------ ----------- ----------- ---------- ------------
  재무팀 (admin)  O            O 전체      O           O          O

  예산팀 (editor) O            O 예산 열만 O           X          X

  법인 (viewer)   O            X           O           X          X

  이사회 (viewer) O            X           X           X          X
  ----------------------------------------------------------------------------

예산팀은 fiscal_years.type = \"budget\" 행(25예산, 26예산, 27예산,
28예산)만 수정 가능. 실적(actual) 행은 재무팀 admin만 수정합니다.

**5. API 엔드포인트 설계**

  ---------------------------------------------------------------------------------
  **메서드**   **경로**                            **설명**            **권한**
  ------------ ----------------------------------- ------------------- ------------
  POST         /api/auth/login                     로그인 → JWT 반환   전체

  GET          /api/cashflow?sheet=1               전체 항목+금액 조회 전체

  PUT          /api/cashflow/:categoryId/:yearId   금액 1건 수정       editor↑

  POST         /api/upload/excel                   엑셀 업로드 → 파싱  admin

  GET          /api/export/excel                   현재 DB → 엑셀 출력 전체

  GET          /api/comments?categoryId=5          코멘트 목록         전체

  POST         /api/comments                       코멘트 등록         viewer↑

  GET          /api/audit?categoryId=5             수정 이력 조회      admin
  ---------------------------------------------------------------------------------

**6. Claude Code 프롬프트 전문**

아래 프롬프트를 Claude Code 세션에 순서대로 입력합니다. 각 단계는
독립적으로 실행 가능합니다.

**STEP 1 --- 프로젝트 초기화 및 DB 구성**

+-------------------------------------------------------------------+
| **Claude Code에 붙여넣기**                                        |
|                                                                   |
| 대학 자금수지 관리 웹앱 프로젝트를 초기화해줘. \## 요구사항 -     |
| 모노레포: cashflow-platform/backend +                             |
| cashflow-platform/frontend - 백엔드: Node.js 20, Express, pg      |
| (PostgreSQL 클라이언트), xlsx, jsonwebtoken, multer, bcrypt -     |
| 프론트엔드: React 18, Vite, axios, chart.js, react-chartjs-2 -    |
| Docker Compose로 postgres:15 + backend + frontend + nginx 구성    |
| \## 해야 할 일 1. 위 디렉터리 구조대로 폴더/파일 생성             |
| (package.json, Dockerfile 포함) 2.                                |
| migrations/001_create_tables.sql 작성 (아래 스키마 기준) 3.       |
| migrations/002_seed_data.sql 작성 --- fiscal_years 8개 연도 시드  |
| 4. docker-compose.yml 작성 --- DB 마이그레이션 자동 실행 포함 \## |
| DB 스키마 (PostgreSQL) users, fiscal_years, cashflow_categories,  |
| cashflow_values, comments, audit_logs (스키마 DDL은 첨부 문서의   |
| 섹션 3-2 참고)                                                    |
+-------------------------------------------------------------------+

**STEP 2 --- 엑셀 파서 서비스**

+-------------------------------------------------------------------+
| **Claude Code에 붙여넣기**                                        |
|                                                                   |
| backend/src/services/excelParser.js를 작성해줘. \## 파싱할 엑셀   |
| 구조 - 시트1 \"1.등록금등자금\": 4행 헤더,                        |
| 구분(A열)/항목(B열)/세부항목(D열)/금액(E\~L열, 21\~28회계) -      |
| 시트2 \"2.목적자금\": 동일 구조, 항목 트리 깊이 2단계 - 금액      |
| 단위: 억원 (정수 또는 소수) - 소계 행 감지: \"경상수입 계 B\",    |
| \"경상지출 계 C\", \"목적수입 계 B\", \"목적지출 계 C\" 등 \##    |
| 파서 동작 1. xlsx 라이브러리로 파일 읽기 2. 항목 트리를           |
| cashflow_categories에 upsert (name+sheet 기준) 3. 금액을          |
| cashflow_values에 upsert (category_id + fiscal_year_id 기준) 4.   |
| 파싱 결과 요약 반환: { inserted, updated, skipped } \##           |
| 주의사항 - 병합된 셀은 첫 번째 값만 사용 - None/null 값은 DB에    |
| NULL로 저장 (0과 구별) - 트랜잭션으로 전체 처리 (실패 시 롤백)    |
+-------------------------------------------------------------------+

**STEP 3 --- REST API 라우트**

+-------------------------------------------------------------------+
| **Claude Code에 붙여넣기**                                        |
|                                                                   |
| backend/src/routes/ 아래 라우트 파일들을 작성해줘. \## auth.js -  |
| POST /api/auth/login: email+password → bcrypt 검증 → JWT(24h)     |
| 반환 - JWT payload: { userId, department, role } \##              |
| cashflow.js - GET /api/cashflow?sheet=1: 해당 시트 전체           |
| 카테고리+8개 연도 금액 조인 반환 응답 형태: \[{id, name,          |
| parent_id, type, sort_order, values: {25: 402, 26: 436, \...}},   |
| \...\] - PUT /api/cashflow/:categoryId/:yearId: 금액 수정 +       |
| audit_log 기록 - 권한 체크: role=editor면 budget 연도만 허용,     |
| role=admin은 전체 \## upload.js - POST /api/upload/excel:         |
| multipart 파일 수신 → excelParser 호출 → 결과 반환 - admin만 접근 |
| 가능 \## comments.js - GET /api/comments?categoryId=&yearId=:     |
| 해당 셀의 코멘트 목록+작성자 정보 - POST /api/comments: 코멘트    |
| 작성 (viewer 이상) \## 공통 - 모든 라우트에 auth 미들웨어 적용 -  |
| 에러는 { error: \"message\" } 형태로 반환 - 응답 상태코드 준수    |
| (401, 403, 404, 500)                                              |
+-------------------------------------------------------------------+

**STEP 4 --- React 프론트엔드**

+-------------------------------------------------------------------+
| **Claude Code에 붙여넣기**                                        |
|                                                                   |
| frontend/src/ 아래 React 컴포넌트들을 작성해줘. \## App.jsx -     |
| react-router-dom으로 라우팅: /, /sheet1, /sheet2, /upload,        |
| /audit - useAuth 훅으로 JWT 관리, 미인증 시 /login 리다이렉트 \## |
| Dashboard.jsx (메인 화면) - 상단: 연도 선택 탭 (21회계\~28예산) - |
| 좌측: 경상수입/경상지출/당기 과부족 요약 카드 3개 - 우측:         |
| Chart.js 막대+라인 혼합 차트 (수입 막대, 지출 막대, 과부족        |
| 라인) - 하단: 목적자금 수입/지출 막대 차트 \## CashflowTable.jsx  |
| (공통 인라인 편집 테이블) - props: { data, sheetType, onSave } -  |
| 계층 표현: 구분(배경 파란색) \> 항목(배경 회색) \>                |
| 세부항목(일반) - 편집 가능 셀: 클릭 시 input으로 전환, Enter/blur |
| 시 PUT API 호출 - 권한에 따라 편집 가능 셀 구분 (editor는 budget  |
| 열만 편집 가능) - 소계 행은 항상 읽기 전용, 굵은 글씨 - 셀에      |
| 코멘트 있으면 우상단 점 표시, 클릭 시 CommentBox 표시 \##         |
| Upload.jsx - 드래그앤드롭 파일 업로드 UI - 업로드 후 파싱         |
| 결과(inserted/updated/skipped) 표시 \## 스타일 - CSS Modules      |
| 사용, 별도 UI 라이브러리 없이 순수 CSS - 폰트: Noto Sans KR       |
| (Google Fonts) - 테마 색상: 파란색 #185FA5 (헤더/포인트), 초록    |
| #1D9E75 (수입), 빨간 #E24B4A (지출)                               |
+-------------------------------------------------------------------+

**STEP 5 --- Docker 배포**

+-------------------------------------------------------------------+
| **Claude Code에 붙여넣기**                                        |
|                                                                   |
| 사내 서버 배포를 위한 Docker 구성을 완성해줘. \##                 |
| docker-compose.yml - services: postgres, backend, frontend,       |
| nginx - postgres: 볼륨 마운트 ./data/postgres, 헬스체크 포함 -    |
| backend: postgres 헬스체크 통과 후 기동, 마이그레이션 자동 실행 - |
| frontend: Vite build 결과물을 nginx로 서빙 - nginx: 80포트,       |
| /api/\* → backend:3000, /\* → frontend 정적 파일 \##              |
| nginx/nginx.conf - gzip 압축 활성화 - React SPA를 위한 try_files  |
| \$uri /index.html - 업로드 크기 제한: client_max_body_size 50M    |
| \## 환경변수 (.env 예시 포함) DATABASE_URL, JWT_SECRET, PORT,     |
| VITE_API_BASE_URL \## 실행 방법 README.md 작성 - git clone → .env |
| 설정 → docker compose up -d - 초기 관리자 계정 생성 명령어 - 기존 |
| 엑셀 임포트 명령어: docker compose exec backend node              |
| scripts/import.js \<파일명\>                                      |
+-------------------------------------------------------------------+

**7. 빠른 시작 체크리스트**

Claude Code 세션을 열고 아래 순서대로 진행합니다.

1.  cashflow-platform 폴더 열기: claude code ./cashflow-platform

2.  STEP 1 프롬프트 입력 → 파일 구조 생성 확인

3.  docker compose up -d postgres → DB 기동

4.  STEP 2 프롬프트 입력 → excelParser.js 생성

5.  기존 엑셀 파일로 임포트 테스트: node scripts/import.js 파일명.xlsx

6.  STEP 3 프롬프트 입력 → API 라우트 생성

7.  curl로 API 동작 확인: curl localhost:3000/api/cashflow?sheet=1

8.  STEP 4 프롬프트 입력 → React 컴포넌트 생성

9.  STEP 5 프롬프트 입력 → Docker 배포 구성

10. docker compose up -d → http://사내서버IP 접속 확인

+-------------------------------------------------------------------+
| **예상 개발 기간**                                                |
|                                                                   |
| 경험 있는 개발자 + Claude Code 활용 기준: - STEP 1\~2 (DB +       |
| 파서): 반나절 - STEP 3 (API): 반나절 - STEP 4 (프론트엔드): 1일 - |
| STEP 5 (배포): 반나절 → 총 2\~3일 예상 (기능 테스트 및 데이터     |
| 검증 포함)                                                        |
+-------------------------------------------------------------------+
