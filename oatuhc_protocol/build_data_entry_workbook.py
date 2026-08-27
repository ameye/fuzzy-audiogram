#!/usr/bin/env python3
"""
Build the OAUTHC FAI validation data-entry workbook (Excel).

Aligns exactly with oatuhc_protocol/data_dictionary.md v1.0 (16 Aug 2026):
  - One row per EAR (left/right share a patient_id)
  - No direct identifiers
  - Thresholds in dB HL (−10..120)
  - Dropdowns for diagnosis, grade, shape, ear, sex
  - Per-row rules: monotonicity flag, PTA-4 auto-calc, WHO grade, borderline flag
  - Instructions + data dictionary sheets baked in
"""

import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("pip install openpyxl")

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

OUT = Path("/workspace/fuzzy-audiogram/oatuhc_protocol/OAUTHC_FAI_validation_data_entry.xlsx")

NAVY = "1a3a5c"
TEAL = "2a7a6f"
LIGHT = "eef2f7"
AMBER = "fff3cd"
RED = "f8d7da"

thin = Side(style="thin", color="bbbbbb")
border_all = Border(left=thin, right=thin, top=thin, bottom=thin)

wb = Workbook()

# ─────────────────────────────────────────────────────────────
# SHEET 1: DATA ENTRY
# ─────────────────────────────────────────────────────────────
ws = wb.active
ws.title = "Data Entry"

# Column layout
COLS = [
    ("study_id", "int", "Study ID (auto, sequential)"),
    ("patient_id", "int", "Patient ID (2 rows share: L/R)"),
    ("ear", "ear", "Ear"),
    ("test_month_year", "text", "e.g. Mar 2023 (month-year only)"),
    ("age_years", "int", "Age (18–110)"),
    ("sex", "sex", "1=M, 2=F"),
    ("th_250", "db", "dB HL"),
    ("th_500", "db", "dB HL"),
    ("th_1k", "db", "dB HL"),
    ("th_2k", "db", "dB HL"),
    ("th_3k", "db", "dB HL"),
    ("th_4k", "db", "dB HL"),
    ("th_6k", "db", "dB HL"),
    ("th_8k", "db", "dB HL"),
    ("bc_500", "db", "dB HL (optional)"),
    ("bc_1k", "db", "dB HL (optional)"),
    ("bc_2k", "db", "dB HL (optional)"),
    ("bc_4k", "db", "dB HL (optional)"),
    ("diagnosis_category", "diag", "Clinical diagnosis"),
    ("consultant_grade", "grade", "Documented grade"),
    ("documented_shape", "shape", "Documented shape"),
    ("ear_included", "flag", "1=eligible 0=excluded"),
    ("exclusion_reason", "text", "Blank if included"),
    # Derived / QA (auto-formula)
    ("pta4", "calc", "Auto: mean of 500,1k,2k,4k"),
    ("who_grade", "calc", "Auto WHO PTA-4"),
    ("borderline", "calc", "Auto: within ±5 dB of boundary"),
    ("monotonicity_flag", "calc", "Auto: >40 dB jump between adjacent freqs"),
]

n_cols = len(COLS)
for j, (name, kind, note) in enumerate(COLS, start=1):
    c = ws.cell(row=1, column=j, value=name)
    c.font = Font(bold=True, color="FFFFFF", size=10)
    c.fill = PatternFill("solid", fgColor=NAVY)
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    c.border = border_all

# Row 2 = note row (grey)
for j, (name, kind, note) in enumerate(COLS, start=1):
    c = ws.cell(row=2, column=j, value=note)
    c.font = Font(italic=True, size=8, color="777777")
    c.fill = PatternFill("solid", fgColor=LIGHT)
    c.alignment = Alignment(wrap_text=True, vertical="center")

# Row 3 = example row
example = {
    "study_id": 1, "patient_id": 1, "ear": "left", "test_month_year": "Mar 2023",
    "age_years": 45, "sex": 1, "th_250": 20, "th_500": 25, "th_1k": 30,
    "th_2k": 35, "th_3k": 38, "th_4k": 42, "th_6k": 40, "th_8k": 45,
    "bc_500": "", "bc_1k": "", "bc_2k": "", "bc_4k": "",
    "diagnosis_category": "presbyacusis", "consultant_grade": "mild",
    "documented_shape": "sloping", "ear_included": 1, "exclusion_reason": "",
}
for j, (name, kind, note) in enumerate(COLS, start=1):
    c = ws.cell(row=3, column=j, value=example.get(name, ""))
    c.font = Font(size=9, color="999999", italic=True)
    c.fill = PatternFill("solid", fgColor="f5f5f5")

# Data validation dropdowns
def add_dv(formula, cells):
    dv = DataValidation(type="list", formula1=formula, allow_blank=True,
                        showDropDown=False, showErrorMessage=True,
                        errorTitle="Invalid entry", error="Choose from the list")
    ws.add_data_validation(dv)
    dv.add(cells)

col_letter = {name: get_column_letter(j + 1) for j, (name, _, _) in enumerate(COLS)}
idx_of = {name: j + 1 for j, (name, _, _) in enumerate(COLS)}
def col_letter_idx(name):
    return idx_of[name]
add_dv('"left,right"', f"{col_letter['ear']}3:{col_letter['ear']}2000")
add_dv('"1,2"', f"{col_letter['sex']}3:{col_letter['sex']}2000")
add_dv('"csoM,otosclerosis,nihl,presbyacusis,ssnhl,ototoxicity,meniere,other,not_documented"',
       f"{col_letter['diagnosis_category']}3:{col_letter['diagnosis_category']}2000")
add_dv('"normal,mild,moderate,moderately_severe,severe,profound"',
       f"{col_letter['consultant_grade']}3:{col_letter['consultant_grade']}2000")
add_dv('"flat,sloping,notched,rising"',
       f"{col_letter['documented_shape']}3:{col_letter['documented_shape']}2000")
add_dv('"1,0"', f"{col_letter['ear_included']}3:{col_letter['ear_included']}2000")

# Numeric validation: thresholds -10..120
for name in ["th_250", "th_500", "th_1k", "th_2k", "th_3k", "th_4k", "th_6k", "th_8k",
             "bc_500", "bc_1k", "bc_2k", "bc_4k"]:
    L = col_letter[name]
    dv = DataValidation(type="decimal", operator="between", formula1="-10",
                        formula2="120", allow_blank=True, showErrorMessage=True,
                        errorTitle="Out of range", error="dB HL must be −10..120")
    ws.add_data_validation(dv)
    dv.add(f"{L}3:{L}2000")

# Age validation
dv = DataValidation(type="whole", operator="between", formula1="18", formula2="110",
                    allow_blank=True, showErrorMessage=True,
                    errorTitle="Out of range", error="Age must be 18–110")
ws.add_data_validation(dv)
dv.add(f"{col_letter['age_years']}3:{col_letter['age_years']}2000")

# Derived formula columns (start at row 3)
P = {f: col_letter[f] for f in ["th_500", "th_1k", "th_2k", "th_4k",
                                "th_3k", "th_250", "th_6k", "th_8k"]}
n_data = 500  # formulas pre-filled for 500 rows

for row in range(3, 3 + n_data):
    # PTA-4 (average of 500, 1k, 2k, 4k)
    ws.cell(row=row, column=col_letter_idx("pta4"),
            value=(f"=IF(COUNT({P['th_500']}{row},{P['th_1k']}{row},{P['th_2k']}{row},{P['th_4k']}{row})<4,\"\","
                   f"ROUND(AVERAGE({P['th_500']}{row},{P['th_1k']}{row},{P['th_2k']}{row},{P['th_4k']}{row}),1))"))
    # WHO grade
    ws.cell(row=row, column=col_letter_idx("who_grade"),
            value=(f"=IF({col_letter['pta4']}{row}=\"\",\"\","
                   f"IF({col_letter['pta4']}{row}<26,\"normal\","
                   f"IF({col_letter['pta4']}{row}<41,\"mild\","
                   f"IF({col_letter['pta4']}{row}<61,\"moderate\","
                   f"IF({col_letter['pta4']}{row}<81,\"severe\",\"profound\")))))"))
    # Borderline (within ±5 dB of WHO boundaries: 25, 40, 60, 80)
    ws.cell(row=row, column=col_letter_idx("borderline"),
            value=(f"=IF({col_letter['pta4']}{row}=\"\",\"\","
                   f"IF(OR(ABS({col_letter['pta4']}{row}-25)<=5,ABS({col_letter['pta4']}{row}-40)<=5,"
                   f"ABS({col_letter['pta4']}{row}-60)<=5,ABS({col_letter['pta4']}{row}-80)<=5),1,0))"))
    # Monotonicity flag: max adjacent jump > 40 dB across the 8 air thresholds
    freqs = ["th_250", "th_500", "th_1k", "th_2k", "th_3k", "th_4k", "th_6k", "th_8k"]
    pairs = []
    for a, b in zip(freqs[:-1], freqs[1:]):
        pairs.append(f"ABS({col_letter[a]}{row}-{col_letter[b]}{row})")
    ws.cell(row=row, column=col_letter_idx("monotonicity_flag"),
            value=f"=IF(MAX({','.join(pairs)})>40,1,0)")

# Column widths
widths = {
    "study_id": 9, "patient_id": 10, "ear": 8, "test_month_year": 14, "age_years": 9,
    "sex": 6, "th_250": 8, "th_500": 8, "th_1k": 8, "th_2k": 8, "th_3k": 8,
    "th_4k": 8, "th_6k": 8, "th_8k": 8, "bc_500": 8, "bc_1k": 8, "bc_2k": 8,
    "bc_4k": 8, "diagnosis_category": 18, "consultant_grade": 16, "documented_shape": 14,
    "ear_included": 11, "exclusion_reason": 22, "pta4": 9, "who_grade": 10,
    "borderline": 11, "monotonicity_flag": 15,
}
for name, w in widths.items():
    ws.column_dimensions[col_letter[name]].width = w

# Freeze panes (keep header + note visible)
ws.freeze_panes = "A3"

# Highlight derived columns lightly
for j, (name, kind, _) in enumerate(COLS, start=1):
    if kind == "calc":
        ws.cell(row=1, column=j).fill = PatternFill("solid", fgColor=TEAL)

# Conditional formatting: monotonicity_flag == 1 → amber
from openpyxl.formatting.rule import FormulaRule
ws.conditional_formatting.add(
    f"{col_letter['monotonicity_flag']}3:{col_letter['monotonicity_flag']}2000",
    FormulaRule(formula=["AND($H3<>\"\",$H3=1)"], fill=PatternFill("solid", fgColor=AMBER))
)

# ─────────────────────────────────────────────────────────────
# SHEET 2: INSTRUCTIONS
# ─────────────────────────────────────────────────────────────
ws2 = wb.create_sheet("Instructions")
ws2.column_dimensions["A"].width = 3
ws2.column_dimensions["B"].width = 100
rows = [
    ("OAUTHC FAI External Validation — Data Entry", "h1"),
    ("", "n"),
    ("1. One row per EAR. A patient with both ears tested contributes two rows sharing the same patient_id.", "n"),
    ("2. No direct identifiers. No names, hospital numbers, addresses, phones or emails. study_id is sequential and NOT linked to the hospital record.", "n"),
    ("3. Missing values: leave BLANK. Do not write NA, N/A, -, ., or 0.", "n"),
    ("4. Thresholds are dB HL, range −10 to +120 (enforced).", "n"),
    ("5. test_month_year: month-year only (e.g. Mar 2023). Never the day.", "n"),
    ("6. sex: 1 = male, 2 = female, blank = not documented.", "n"),
    ("7. diagnosis_category, consultant_grade, documented_shape: dropdowns; only fill grade/shape where explicitly documented.", "n"),
    ("8. ear_included: 1 = eligible, 0 = excluded (give exclusion_reason).", "n"),
    ("9. Derived columns (pta4, who_grade, borderline, monotonicity_flag) are auto-computed — do not type into them.", "n"),
    ("10. After every 20 rows, run the batch validation script (see README) and resolve any flags.", "n"),
    ("", "n"),
    ("Study design note: the frozen FAI pipeline computes fai_score/fai_label/fai_config + membership degrees from these thresholds; those columns are added by the processing script, not the entry form.", "note"),
]
for i, (txt, kind) in enumerate(rows, start=1):
    c = ws2.cell(row=i, column=2, value=txt)
    if kind == "h1":
        c.font = Font(bold=True, size=14, color=NAVY)
    elif kind == "note":
        c.font = Font(italic=True, size=10, color=TEAL)
    else:
        c.font = Font(size=11)
    c.alignment = Alignment(wrap_text=True, vertical="top")

# ─────────────────────────────────────────────────────────────
# SHEET 3: DATA DICTIONARY
# ─────────────────────────────────────────────────────────────
ws3 = wb.create_sheet("Data Dictionary")
ws3.column_dimensions["A"].width = 22
ws3.column_dimensions["B"].width = 14
ws3.column_dimensions["C"].width = 70
ws3.column_dimensions["D"].width = 24
headers = ["Column", "Type", "Allowed values / notes", "Source"]
for j, h in enumerate(headers, start=1):
    c = ws3.cell(row=1, column=j, value=h)
    c.font = Font(bold=True, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor=NAVY)
    c.border = border_all

DICT = [
    ("study_id", "Integer", "Sequential 1..N, unique per record (one row per ear)", "Assigned"),
    ("patient_id", "Integer", "Sequential per patient; two ear rows share it", "Assigned"),
    ("ear", "Text", "left / right", "Audiogram"),
    ("test_month_year", "Text", "e.g. Mar 2023; month-year only, never day", "Audiogram header"),
    ("age_years", "Integer", "18–110", "Record"),
    ("sex", "Integer", "1 = male, 2 = female, blank = not documented", "Record"),
    ("th_250..th_8k", "Decimal", "dB HL, −10..120", "Audiogram chart"),
    ("bc_500..bc_4k", "Decimal", "dB HL bone conduction where recorded", "Audiogram chart"),
    ("diagnosis_category", "Text", "csoM | otosclerosis | nihl | presbyacusis | ssnhl | ototoxicity | meniere | other | not_documented", "Record"),
    ("consultant_grade", "Text", "normal | mild | moderate | moderately_severe | severe | profound — only where explicitly documented", "Record"),
    ("documented_shape", "Text", "flat | sloping | notched | rising — only where explicitly documented", "Record"),
    ("ear_included", "Integer", "1 = eligible, 0 = excluded (reason below)", "Extraction review"),
    ("exclusion_reason", "Text", "blank if included; e.g. <4 PTA freqs, out-of-range thresholds, duplicate episode", "Extraction review"),
    ("pta4 (auto)", "Decimal", "mean(th_500, th_1k, th_2k, th_4k)", "Derived"),
    ("who_grade (auto)", "Text", "WHO PTA-4 classification of pta4", "Derived"),
    ("borderline (auto)", "Integer", "pta4 within ±5 dB of any WHO boundary (25/40/60/80)", "Derived"),
    ("monotonicity_flag (auto)", "Integer", "1 if any adjacent-frequency jump > 40 dB (review, do not auto-correct)", "Derived"),
]
for i, row in enumerate(DICT, start=2):
    for j, val in enumerate(row, start=1):
        c = ws3.cell(row=i, column=j, value=val)
        c.font = Font(size=10)
        c.border = border_all
        c.alignment = Alignment(wrap_text=True, vertical="top")

# ─────────────────────────────────────────────────────────────
# SHEET 4: README / next steps
# ─────────────────────────────────────────────────────────────
ws4 = wb.create_sheet("README")
ws4.column_dimensions["A"].width = 3
ws4.column_dimensions["B"].width = 100
readme = [
    ("How this workbook works", "h1"),
    ("", "n"),
    ("- Enter data in the 'Data Entry' sheet, one row per ear.", "n"),
    ("- Use the dropdowns; thresholds auto-validate (−10..120 dB HL).", "n"),
    ("- pta4, who_grade, borderline and monotonicity_flag compute automatically.", "n"),
    ("- The monotonicity flag turns amber when an adjacent-frequency jump exceeds 40 dB — review that row (do not auto-correct).", "n"),
    ("", "n"),
    ("Processing the data", "h1"),
    ("", "n"),
    ("1. Save this file, then run the batch processor (to be added):", "n"),
    ("   python scripts/validate_oatuhc.py --input OAUTHC_FAI_validation_data_entry.xlsx", "n"),
    ("2. The processor validates rules (unique study_id, duplicate (patient_id,ear), age range, binary flags).", "n"),
    ("3. It then runs the frozen FAI pipeline on every eligible ear and appends:", "n"),
    ("   fai_score, fai_label, fai_config, membership_normal..profound", "n"),
    ("4. Outputs an analysis-ready CSV (ear-level) plus a per-batch QA report.", "n"),
    ("", "n"),
    ("Cheat-sheet of dropdown values", "h1"),
    ("", "n"),
    ("diagnosis_category: csoM | otosclerosis | nihl | presbyacusis | ssnhl | ototoxicity | meniere | other | not_documented", "n"),
    ("consultant_grade: normal | mild | moderate | moderately_severe | severe | profound", "n"),
    ("documented_shape: flat | sloping | notched | rising", "n"),
    ("ear: left | right      sex: 1 | 2      ear_included: 1 | 0", "n"),
]
for i, (txt, kind) in enumerate(readme, start=1):
    c = ws4.cell(row=i, column=2, value=txt)
    if kind == "h1":
        c.font = Font(bold=True, size=13, color=NAVY)
    else:
        c.font = Font(size=11)
    c.alignment = Alignment(wrap_text=True, vertical="top")

wb.save(str(OUT))
print(f"✅ Workbook saved: {OUT}")
print(f"   Size: {OUT.stat().st_size:,} bytes")
print("   Sheets: Data Entry, Instructions, Data Dictionary, README")
print("   500 pre-filled formula rows; dropdowns + validations active")
