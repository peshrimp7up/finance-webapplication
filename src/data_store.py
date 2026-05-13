"""엑셀 파일(`data/cashflow.xlsx`)을 메모리 모델로 로드하고 다시 저장한다.

원본 양식의 셀 좌표와 스타일은 그대로 유지한다.
카테고리 트리는 코드에 상수로 박혀 있고, 엑셀에서는 값만 읽어/써넣는다.
"""

from __future__ import annotations

import shutil
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import openpyxl

from .formula_parser import eval_cell

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
XLSX_PATH = DATA_DIR / "cashflow.xlsx"

# 연도 → 엑셀 열 매핑 (E=5, F=6, ..., L=12)
YEARS = [
    ("21회계", "actual", "E"),
    ("22회계", "actual", "F"),
    ("23회계", "actual", "G"),
    ("24회계", "actual", "H"),
    ("25예산", "budget", "I"),
    ("26예산", "budget", "J"),
    ("27예산", "budget", "K"),
    ("28예산", "budget", "L"),
]
YEAR_LABELS = [y[0] for y in YEARS]
YEAR_COLUMNS = {y[0]: y[2] for y in YEARS}
BUDGET_YEARS = [y[0] for y in YEARS if y[1] == "budget"]


@dataclass
class Category:
    id: str
    name: str
    sheet: str            # "sheet1" | "sheet2"
    kind: str             # "income" | "expense" | "calc" | "input" | "nonop"
    row: int              # 엑셀 행 번호
    is_subtotal: bool = False   # 자동 계산되는 합계 행
    is_calc: bool = False       # 자금흐름 계산 결과 (A/D/G 등)
    parent_id: Optional[str] = None
    children_ids: list[str] = field(default_factory=list)


# 시트1 카테고리 정의 (엑셀의 행 번호 그대로)
_SHEET1_DEFS: list[Category] = [
    Category("s1.carryover_A", "전기 이월 A",                  "sheet1", "calc",    4,  is_calc=True),
    # 경상수입 > 등록금 수입
    Category("s1.inc_tuition",          "등록금 수입",          "sheet1", "income",  7,  is_subtotal=True),
    Category("s1.inc_tuition.ug",       "학부 수업료",          "sheet1", "income",  8,  parent_id="s1.inc_tuition"),
    Category("s1.inc_tuition.grad",     "대학원(입학금+수업료)", "sheet1", "income",  9,  parent_id="s1.inc_tuition"),
    Category("s1.inc_tuition.short",    "단기수강료",           "sheet1", "income", 10,  parent_id="s1.inc_tuition"),
    # 경상수입 > 기타 수입
    Category("s1.inc_other",            "기타 수입",            "sheet1", "income", 11, is_subtotal=True),
    Category("s1.inc_other.sandan",     "산단전입금",           "sheet1", "income", 12, parent_id="s1.inc_other"),
    Category("s1.inc_other.dorm",       "기숙사수입",           "sheet1", "income", 13, parent_id="s1.inc_other"),
    Category("s1.inc_other.rent",       "대여료및사용료기타",   "sheet1", "income", 14, parent_id="s1.inc_other"),
    Category("s1.inc_other.misc",       "잡수입",               "sheet1", "income", 15, parent_id="s1.inc_other"),
    Category("s1.inc_other.app_fee",    "입시수수료",           "sheet1", "income", 16, parent_id="s1.inc_other"),
    Category("s1.inc_other.hospital",   "부속병원전입금",       "sheet1", "income", 17, parent_id="s1.inc_other"),
    Category("s1.inc_other.interest",   "이자수입",             "sheet1", "income", 18, parent_id="s1.inc_other"),
    Category("s1.inc_other.donation",   "기부금(순수)",         "sheet1", "income", 19, parent_id="s1.inc_other"),
    # 경상수입 > 국고보조금
    Category("s1.inc_gov",              "국고보조금 수입_운영비", "sheet1", "income", 21, is_subtotal=True),
    Category("s1.inc_gov.innov",        "교육부 혁신지원(운영비사용)", "sheet1", "income", 22, parent_id="s1.inc_gov"),
    Category("s1.inc_gov.highschool",   "교육부 고교기여(운영비사용)", "sheet1", "income", 23, parent_id="s1.inc_gov"),
    Category("s1.inc_gov.local",        "기타지방자치단체등(운영비사용)", "sheet1", "income", 24, parent_id="s1.inc_gov"),
    # 경상수입 계 B
    Category("s1.subtotal_B",           "경상수입 계 B",        "sheet1", "calc",   25, is_calc=True, is_subtotal=True),
    # 경상지출 > 보수
    Category("s1.exp_salary",           "보수(비임상 교원, 직원)", "sheet1", "expense", 27, is_subtotal=True),
    Category("s1.exp_salary.faculty",   "비임상교원",           "sheet1", "expense", 28, parent_id="s1.exp_salary"),
    Category("s1.exp_salary.staff",     "직원",                 "sheet1", "expense", 29, parent_id="s1.exp_salary"),
    Category("s1.exp_salary.ta",        "조교",                 "sheet1", "expense", 30, parent_id="s1.exp_salary"),
    Category("s1.exp_salary.severance", "퇴직금",               "sheet1", "expense", 31, parent_id="s1.exp_salary"),
    Category("s1.exp_salary.lecturer",  "강사료",               "sheet1", "expense", 32, parent_id="s1.exp_salary"),
    # 경상지출 > 관리운영비
    Category("s1.exp_admin",            "관리운영비",           "sheet1", "expense", 33, is_subtotal=True),
    Category("s1.exp_admin.facility",   "시설관리비",           "sheet1", "expense", 34, parent_id="s1.exp_admin"),
    Category("s1.exp_admin.general",    "일반관리비",           "sheet1", "expense", 35, parent_id="s1.exp_admin"),
    Category("s1.exp_admin.ops",        "운영비",               "sheet1", "expense", 36, parent_id="s1.exp_admin"),
    # 경상지출 > 연구 학생경비
    Category("s1.exp_research",         "연구 학생경비",        "sheet1", "expense", 37, is_subtotal=True),
    Category("s1.exp_research.research","연구비",               "sheet1", "expense", 38, parent_id="s1.exp_research"),
    Category("s1.exp_research.sch_ug",  "교내장학금 학부",      "sheet1", "expense", 39, parent_id="s1.exp_research"),
    Category("s1.exp_research.sch_grad","교내장학금 대학원",    "sheet1", "expense", 40, parent_id="s1.exp_research"),
    Category("s1.exp_research.lab",     "실험실습비및논문심사료", "sheet1", "expense", 41, parent_id="s1.exp_research"),
    Category("s1.exp_research.support", "학생지원비및기타학생경비", "sheet1", "expense", 42, parent_id="s1.exp_research"),
    Category("s1.exp_research.entrance","입시관리비",           "sheet1", "expense", 43, parent_id="s1.exp_research"),
    # 경상지출 > 고정자산매입
    Category("s1.exp_capex",            "고정자산매입",         "sheet1", "expense", 44, is_subtotal=True),
    Category("s1.exp_capex.machine",    "기계기구매입",         "sheet1", "expense", 45, parent_id="s1.exp_capex"),
    Category("s1.exp_capex.equipment",  "집기비품및도서매입",   "sheet1", "expense", 46, parent_id="s1.exp_capex"),
    # 경상지출 계 C
    Category("s1.subtotal_C",           "경상지출 계 C",        "sheet1", "calc",   48, is_calc=True, is_subtotal=True),
    # 당기 과부족액 D
    Category("s1.delta_D",              "당기 과부족액 D=B-C",  "sheet1", "calc",   49, is_calc=True, is_subtotal=True),
    # 부족액충당 E (입력)
    Category("s1.makeup_E",             "부족액충당(기부수입 등) E", "sheet1", "input", 51),
    # 비경상지출
    Category("s1.nonop.science",        "과학관증축 등",        "sheet1", "nonop", 53),
    Category("s1.nonop.land",           "토지매입(이새공장)",   "sheet1", "nonop", 54),
    Category("s1.nonop.future",         "미래관증축",           "sheet1", "nonop", 55),
    Category("s1.nonop.medical",        "의학관건축",           "sheet1", "nonop", 56),
    Category("s1.nonop.loan_interest",  "차입금이자(의학관융자300억)", "sheet1", "nonop", 57),
    Category("s1.nonop_F",              "비경상지출 계 F",      "sheet1", "calc",  59, is_calc=True, is_subtotal=True),
    # 차기 이월 G
    Category("s1.carryover_G",          "차기 이월 G=A+D+E-F",  "sheet1", "calc",  61, is_calc=True, is_subtotal=True),
]

# 시트2 카테고리 정의
_SHEET2_DEFS: list[Category] = [
    Category("s2.carryover_A",          "전기 이월 A",          "sheet2", "calc",   4, is_calc=True),
    # 목적수입 > 국고보조금
    Category("s2.inc_gov",              "국고보조금",           "sheet2", "income", 7, is_subtotal=True),
    Category("s2.inc_gov.nat_scholar",  "교육부 국가장학금",    "sheet2", "income", 8, parent_id="s2.inc_gov"),
    Category("s2.inc_gov.innov_sch",    "교육부 혁신지원(장학금)", "sheet2", "income", 9, parent_id="s2.inc_gov"),
    # 목적수입 > 협력병원근무자
    Category("s2.inc_clinic",           "협력병원근무자",       "sheet2", "income", 11, is_subtotal=True),
    Category("s2.inc_clinic.salary",    "임상교원보수(계산서)", "sheet2", "income", 12, parent_id="s2.inc_clinic"),
    Category("s2.inc_clinic.welfare",   "기타보수및복리후생(기부금)", "sheet2", "income", 13, parent_id="s2.inc_clinic"),
    # 목적수입 > 법정부담전입금
    Category("s2.inc_legal",            "법정부담전입금",       "sheet2", "income", 15, is_subtotal=True),
    Category("s2.inc_legal.transfer",   "법정부담전입금",       "sheet2", "income", 16, parent_id="s2.inc_legal"),
    # 목적수입 > 특별목적기부
    Category("s2.inc_special",          "특별목적기부",         "sheet2", "income", 18, is_subtotal=True),
    Category("s2.inc_special.stock",    "주식취득",             "sheet2", "income", 19, parent_id="s2.inc_special"),
    # 목적수입 계 B
    Category("s2.subtotal_B",           "목적수입 계 B",        "sheet2", "calc",  21, is_calc=True, is_subtotal=True),
    # 목적지출 > 교외장학금
    Category("s2.exp_scholar",          "교외장학금",           "sheet2", "expense", 23, is_subtotal=True),
    Category("s2.exp_scholar.ext",      "교외장학금",           "sheet2", "expense", 24, parent_id="s2.exp_scholar"),
    # 목적지출 > 협력병원근무자보수및경비
    Category("s2.exp_clinic",           "협력병원근무자보수및경비", "sheet2", "expense", 26, is_subtotal=True),
    Category("s2.exp_clinic.salary",    "임상교원보수(계산서)", "sheet2", "expense", 27, parent_id="s2.exp_clinic"),
    Category("s2.exp_clinic.welfare",   "기타보수및복리후생비(기부재원)", "sheet2", "expense", 28, parent_id="s2.exp_clinic"),
    # 목적지출 > 법정부담금
    Category("s2.exp_legal",            "법정부담금",           "sheet2", "expense", 30, is_subtotal=True),
    Category("s2.exp_legal.all",        "법정부담금(교직원전체)", "sheet2", "expense", 31, parent_id="s2.exp_legal"),
    # 목적지출 > 특별목적기부금 사용
    Category("s2.exp_special",          "특별목적기부금 사용",  "sheet2", "expense", 32, is_subtotal=True),
    Category("s2.exp_special.stock",    "주식취득",             "sheet2", "expense", 33, parent_id="s2.exp_special"),
    # 목적지출 계 C
    Category("s2.subtotal_C",           "목적지출 계 C",        "sheet2", "calc",  35, is_calc=True, is_subtotal=True),
    # 당기 과부족액 D
    Category("s2.delta_D",              "당기 과부족액 D=B-C",  "sheet2", "calc",  36, is_calc=True, is_subtotal=True),
    # 차기 이월 E (시트2는 G가 아닌 E라고 라벨됨)
    Category("s2.carryover_G",          "차기 이월 E=A+D",      "sheet2", "calc",  38, is_calc=True, is_subtotal=True),
]


def _build_index(defs: list[Category]) -> dict[str, Category]:
    by_id = {c.id: c for c in defs}
    for c in defs:
        if c.parent_id:
            by_id[c.parent_id].children_ids.append(c.id)
    return by_id


SHEET1: dict[str, Category] = _build_index(_SHEET1_DEFS)
SHEET2: dict[str, Category] = _build_index(_SHEET2_DEFS)
CATEGORIES: dict[str, dict[str, Category]] = {"sheet1": SHEET1, "sheet2": SHEET2}
SHEET_NAMES = {"sheet1": "1.등록금등자금", "sheet2": "2.목적자금"}
SHEET_TITLES = {"sheet1": "등록금등자금", "sheet2": "목적자금"}


@dataclass
class CashflowData:
    """전체 메모리 모델. UI 세션 상태에 보관된다."""
    # values[(sheet, cat_id, year_label)] = {"raw": str, "value": float|None}
    values: dict[tuple[str, str, str], dict] = field(default_factory=dict)
    # comments[(sheet, cat_id, year_label)] = "..."
    comments: dict[tuple[str, str, str], str] = field(default_factory=dict)

    def get(self, sheet: str, cat_id: str, year: str) -> dict:
        return self.values.get((sheet, cat_id, year), {"raw": "", "value": None})

    def set(self, sheet: str, cat_id: str, year: str, raw, value):
        self.values[(sheet, cat_id, year)] = {"raw": raw, "value": value}

    def copy(self) -> "CashflowData":
        return CashflowData(values=deepcopy(self.values), comments=deepcopy(self.comments))


def load_from_xlsx(path: Path = XLSX_PATH) -> CashflowData:
    """엑셀에서 입력 셀들의 값을 읽어 메모리 모델에 채운다.

    파싱 대상은 `is_calc=False`인 카테고리(사용자 입력 행)만.
    수식 셀(소계 등)은 코드에서 자동 계산하므로 읽지 않는다.
    """
    wb = openpyxl.load_workbook(path, data_only=False)
    data = CashflowData()
    for sheet_key, ws_name in SHEET_NAMES.items():
        ws = wb[ws_name]
        for cat in CATEGORIES[sheet_key].values():
            if cat.is_calc:
                continue
            for year, _type, col in YEARS:
                cell_ref = f"{col}{cat.row}"
                raw = ws[cell_ref].value
                if raw is None or raw == "":
                    continue
                try:
                    value, normalized = eval_cell(raw)
                except Exception:
                    value, normalized = None, str(raw)
                data.set(sheet_key, cat.id, year, normalized, value)
    return data


def save_to_xlsx(data: CashflowData, path: Path = XLSX_PATH) -> None:
    """메모리 모델을 엑셀 파일에 다시 써넣는다.

    - 입력 셀: raw 문자열을 그대로 (산식 유지)
    - 계산 셀: 계산된 수치를 (엑셀 수식 없이) 숫자로 기록
    """
    wb = openpyxl.load_workbook(path, data_only=False)
    for sheet_key, ws_name in SHEET_NAMES.items():
        ws = wb[ws_name]
        for cat in CATEGORIES[sheet_key].values():
            for year, _type, col in YEARS:
                cell_ref = f"{col}{cat.row}"
                entry = data.get(sheet_key, cat.id, year)
                if cat.is_calc:
                    ws[cell_ref] = entry["value"] if entry["value"] is not None else None
                else:
                    raw = entry["raw"]
                    if raw == "" or raw is None:
                        ws[cell_ref] = None
                    else:
                        ws[cell_ref] = raw
    wb.save(path)


def reset_from_template(template_path: Path, target_path: Path = XLSX_PATH) -> None:
    """원본 양식을 작업본으로 덮어쓴다 (초기화)."""
    shutil.copyfile(template_path, target_path)
