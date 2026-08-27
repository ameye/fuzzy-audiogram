# OAUTHC FAI External Validation — Microsoft Access Schema & Forms Specification

**Version 1.0 | 16 August 2026**
Companion to `data_dictionary.md` and `oatuhc_fai_validation_protocol.qmd`.
Use this document to assemble the data-entry database in **Microsoft Access**
(2016 or later) on a Windows PC.

---

## 0. Overview

The database has a **two-table relational design**:

- `tbl_Patient` — one record per patient (demographics only, no identifiers)
- `tbl_EarRecord` — one record per ear (left/right), linked to patient via `patient_id`

This mirrors the analysis file convention (one row per ear; two rows share a
`patient_id`). Lookup tables provide dropdown values for constrained fields.

```
tbl_Patient 1 ──── ∞ tbl_EarRecord
```

---

## 1. Tables

### 1.1 tbl_Patient

| Field | Data type | Size/Format | Required | Notes |
|---|---|---|---|---|
| patient_id | AutoNumber | Long Integer | — | Primary key (assigned by Access) |
| age_years | Number | Integer (Byte) | Yes | Validation rule 18–110 |
| sex | Number | Integer (Byte) | No | 1 = male, 2 = female; blank = not documented |
| created_at | Date/Time | General Date | Yes | Default `=Now()` (audit) |
| created_by | Text | 50 | No | Data-entry operator (audit) |

**Table validation rule (sex):** `[sex] Is Null Or [sex] In (1,2)`

### 1.2 tbl_EarRecord

| Field | Data type | Size/Format | Required | Notes |
|---|---|---|---|---|
| study_id | Number | Long Integer | Yes | Sequential per ear record, unique |
| patient_id | Number | Long Integer | Yes | FK → tbl_Patient.patient_id |
| ear | Text | 5 | Yes | `left` / `right` (lookup) |
| test_month_year | Text | 12 | Yes | e.g. `Mar 2023` — month-year only, never day |
| th_250 | Number | Single | No | dB HL, −10..120 |
| th_500 | Number | Single | No | dB HL |
| th_1k | Number | Single | No | dB HL |
| th_2k | Number | Single | No | dB HL |
| th_3k | Number | Single | No | dB HL |
| th_4k | Number | Single | No | dB HL |
| th_6k | Number | Single | No | dB HL |
| th_8k | Number | Single | No | dB HL |
| bc_500 | Number | Single | No | Bone conduction, dB HL (optional) |
| bc_1k | Number | Single | No | |
| bc_2k | Number | Single | No | |
| bc_4k | Number | Single | No | |
| diagnosis_category | Text | 20 | No | Lookup `tbl_Lookup_Diagnosis` |
| consultant_grade | Text | 20 | No | Lookup `tbl_Lookup_Grade`; only where documented |
| documented_shape | Text | 12 | No | Lookup `tbl_Lookup_Shape`; only where documented |
| ear_included | Number | Integer (Byte) | No | 1 = eligible, 0 = excluded |
| exclusion_reason | Text | 100 | No | Blank if included |
| created_at | Date/Time | General Date | Yes | Default `=Now()` |

**Indexes:** unique index on `study_id`; index on `patient_id`;
unique composite index on `(patient_id, ear)` to prevent duplicate rows.

**Field validation rules (thresholds):**
```
>= -10 And <= 120
```
applied to every `th_*` and `bc_*` field.

**Table validation rule (ear_included):**
```
[ear_included] Is Null Or [ear_included] In (0,1)
```

**Table validation rule (diagnosis):**
```
[diagnosis_category] Is Null Or [diagnosis_category] In
('csoM','otosclerosis','nihl','presbyacusis','ssnhl','ototoxicity','meniere','other','not_documented')
```

### 1.3 Lookup tables

#### tbl_Lookup_Diagnosis
| Value | Display |
|---|---|
| csoM | Chronic suppurative otitis media |
| otosclerosis | Otosclerosis |
| nihl | Noise-induced hearing loss |
| presbyacusis | Presbyacusis |
| ssnhl | Sudden sensorineural hearing loss |
| ototoxicity | Ototoxicity |
| meniere | Meniere's disease |
| other | Other |
| not_documented | Not documented |

#### tbl_Lookup_Grade
| Value | Display |
|---|---|
| normal | Normal |
| mild | Mild |
| moderate | Moderate |
| moderately_severe | Moderately severe |
| severe | Severe |
| profound | Profound |

#### tbl_Lookup_Shape
| Value | Display |
|---|---|
| flat | Flat |
| sloping | Sloping |
| notched | Notched |
| rising | Rising |

---

## 2. Relationships

Access → **Database Tools → Relationships**:

- `tbl_Patient.patient_id` (1) ⟷ `tbl_EarRecord.patient_id` (∞)
  - **Enforce Referential Integrity: YES**
  - **Cascade Update: YES** (patient_id never changes in practice, but harmless)
  - **Cascade Delete: YES** (removing a patient removes both ear rows — desirable at data-entry stage)

---

## 3. Forms

### 3.1 `frm_PatientEntry` (main form — single patient)

**Purpose:** capture demographics, then open the ear-record subform.

Controls:

| Control | Bound to | Type | Notes |
|---|---|---|---|
| txtAge | tbl_Patient.age_years | Text box | Input mask `00`; BeforeUpdate validation |
| cboSex | tbl_Patient.sex | Combo box | RowSource `1;2` or lookup; blank allowed |
| txtCreatedBy | tbl_Patient.created_by | Text box | Optional operator initials |

**Form events:**

- `Form_BeforeUpdate` — validate `age_years` 18–110:
```vba
Private Sub Form_BeforeUpdate(Cancel As Integer)
    If Not IsNull(Me.txtAge) Then
        If Me.txtAge < 18 Or Me.txtAge > 110 Then
            MsgBox "Age must be 18-110.", vbExclamation, "Validation"
            Cancel = True
            Me.txtAge.SetFocus
        End If
    End If
End Sub
```

- `Form_AfterUpdate` — auto-open the ear-record form for this patient:
```vba
Private Sub Form_AfterUpdate()
    DoCmd.OpenForm "frm_EarRecord", , , "patient_id=" & Me.patient_id
End Sub
```

### 3.2 `frm_EarRecord` (data-entry form — one ear per record)

**Purpose:** capture all audiogram fields for one ear of the current patient.

Controls (bound to tbl_EarRecord):

| Section | Control | Bound to | Type/Notes |
|---|---|---|---|
| Header | txtStudyID | study_id | Read-only or auto-assigned (see 3.3) |
| | txtPatientID | patient_id | Read-only (set from main form) |
| | cboEar | ear | Combo `left;right` |
| | txtMonthYear | test_month_year | Text, input mask `LLL\ 0000` (e.g. Mar 2023) |
| Air thresholds | txtTh250 .. txtTh8k | th_250 .. th_8k | 8 text boxes, tab order left→right |
| Bone conduction | txtBc500 .. txtBc4k | bc_500 .. bc_4k | 4 text boxes |
| Clinical | cboDiag | diagnosis_category | Combo from tbl_Lookup_Diagnosis |
| | cboGrade | consultant_grade | Combo from tbl_Lookup_Grade |
| | cboShape | documented_shape | Combo from tbl_Lookup_Shape |
| QA | cboIncluded | ear_included | Combo `1;0` |
| | txtExclusion | exclusion_reason | Text box; enabled only if ear_included=0 |
| Footer | lblPTA | (unbound) | Live PTA-4 display (see 3.4) |
| | lblMono | (unbound) | Live monotonicity warning (see 3.4) |

**Key events:**

- `cboEar_AfterUpdate` — prevent duplicate (patient_id, ear):
```vba
Private Sub cboEar_AfterUpdate()
    If Not IsNull(Me.patient_id) And Not IsNull(Me.cboEar) Then
        If DCount("*", "tbl_EarRecord",
                 "patient_id=" & Me.patient_id & " And ear='" & Me.cboEar & "'") > 0 Then
            MsgBox "This ear already has a record for this patient.", vbExclamation
            Me.cboEar.Undo
        End If
    End If
End Sub
```

- Threshold `BeforeUpdate` (all 12 threshold boxes) — range check:
```vba
Private Sub txtTh250_BeforeUpdate(Cancel As Integer)
    If Not IsNull(Me.txtTh250) Then
        If Me.txtTh250 < -10 Or Me.txtTh250 > 120 Then
            MsgBox "Threshold must be -10 to 120 dB HL.", vbExclamation
            Cancel = True
        End If
    End If
End Sub
```
(Repeat for txtTh500 … txtBc4k; or use the field-level Validation Rule instead — simpler.)

- `txtExclusion_GotFocus` — require ear_included=0:
```vba
Private Sub txtExclusion_GotFocus()
    If IsNull(Me.cboIncluded) Or Me.cboIncluded <> 0 Then
        MsgBox "Set 'ear_included' to 0 before entering an exclusion reason.", _
               vbInformation
        Me.cboIncluded.SetFocus
    End If
End Sub
```

### 3.3 Auto-assigning study_id

Use a `BeforeInsert` event on `frm_EarRecord`:

```vba
Private Sub Form_BeforeInsert(Cancel As Integer)
    Me.txtStudyID = Nz(DMax("study_id", "tbl_EarRecord"), 0) + 1
End Sub
```

This guarantees sequential, unique study_id per ear record.

### 3.4 Live QA displays (footer labels)

Update on every threshold change (`AfterUpdate` of each threshold box or via
`Form_AfterUpdate`):

```vba
Private Sub UpdateQA()
    Dim pta As Variant, v As Variant, maxJump As Double, i As Integer
    Dim arr(1 To 8) As Variant, freqs(1 To 8) As String
    freqs(1) = "txtTh250": freqs(2) = "txtTh500": freqs(3) = "txtTh1k"
    freqs(4) = "txtTh2k":  freqs(5) = "txtTh3k":  freqs(6) = "txtTh4k"
    freqs(7) = "txtTh6k":  freqs(8) = "txtTh8k"

    ' PTA-4 = mean(500, 1k, 2k, 4k)
    pta = Nz(Me.txtTh500, 0) + Nz(Me.txtTh1k, 0) + Nz(Me.txtTh2k, 0) + Nz(Me.txtTh4k, 0)
    If Not IsNull(Me.txtTh500) And Not IsNull(Me.txtTh1k) And _
       Not IsNull(Me.txtTh2k) And Not IsNull(Me.txtTh4k) Then
        pta = pta / 4
        Me.lblPTA.Caption = "PTA-4 = " & Format(pta, "0.0") & " dB"
    Else
        Me.lblPTA.Caption = "PTA-4 = — (need 500,1k,2k,4k)"
    End If

    ' Monotonicity: any adjacent jump > 40 dB
    For i = 1 To 8
        arr(i) = Nz(Controls(freqs(i)), Null)
    Next i
    maxJump = 0
    For i = 1 To 7
        If Not IsNull(arr(i)) And Not IsNull(arr(i + 1)) Then
            If Abs(arr(i) - arr(i + 1)) > maxJump Then maxJump = Abs(arr(i) - arr(i + 1))
        End If
    Next i
    If maxJump > 40 Then
        Me.lblMono.Caption = "⚠ Adjacent jump " & Format(maxJump, "0") & " dB > 40 — REVIEW"
        Me.lblMono.ForeColor = RGB(192, 0, 0)
    Else
        Me.lblMono.Caption = "Monotonicity OK"
        Me.lblMono.ForeColor = RGB(0, 128, 0)
    End If
End Sub
```

Call `UpdateQA` from the `AfterUpdate` event of every threshold control.

---

## 4. Queries (analysis prep)

### 4.1 `qry_DataEntryQA` — batch validation check

```sql
SELECT e.study_id, e.patient_id, e.ear, p.age_years, p.sex,
       e.th_500, e.th_1k, e.th_2k, e.th_4k,
       e.ear_included, e.exclusion_reason,
       (e.th_500 + e.th_1k + e.th_2k + e.th_4k) / 4 AS pta4,
       IIf(IsNull(e.th_250) Or IsNull(e.th_500), 0, Abs(e.th_250 - e.th_500)) AS j_250_500,
       IIf(IsNull(e.th_500) Or IsNull(e.th_1k), 0, Abs(e.th_500 - e.th_1k)) AS j_500_1k,
       IIf(IsNull(e.th_1k) Or IsNull(e.th_2k), 0, Abs(e.th_1k - e.th_2k)) AS j_1k_2k,
       IIf(IsNull(e.th_2k) Or IsNull(e.th_3k), 0, Abs(e.th_2k - e.th_3k)) AS j_2k_3k,
       IIf(IsNull(e.th_3k) Or IsNull(e.th_4k), 0, Abs(e.th_3k - e.th_4k)) AS j_3k_4k,
       IIf(IsNull(e.th_4k) Or IsNull(e.th_6k), 0, Abs(e.th_4k - e.th_6k)) AS j_4k_6k,
       IIf(IsNull(e.th_6k) Or IsNull(e.th_8k), 0, Abs(e.th_6k - e.th_8k)) AS j_6k_8k,
       (IIf(IsNull(e.th_250) Or IsNull(e.th_500), 0, Abs(e.th_250 - e.th_500)) +
        IIf(IsNull(e.th_500) Or IsNull(e.th_1k), 0, Abs(e.th_500 - e.th_1k)) +
        IIf(IsNull(e.th_1k) Or IsNull(e.th_2k), 0, Abs(e.th_1k - e.th_2k)) +
        IIf(IsNull(e.th_2k) Or IsNull(e.th_3k), 0, Abs(e.th_2k - e.th_3k)) +
        IIf(IsNull(e.th_3k) Or IsNull(e.th_4k), 0, Abs(e.th_3k - e.th_4k)) +
        IIf(IsNull(e.th_4k) Or IsNull(e.th_6k), 0, Abs(e.th_4k - e.th_6k)) +
        IIf(IsNull(e.th_6k) Or IsNull(e.th_8k), 0, Abs(e.th_6k - e.th_8k))) AS max_jump
FROM tbl_EarRecord AS e
INNER JOIN tbl_Patient AS p ON e.patient_id = p.patient_id
WHERE e.ear_included = 1;
```

Any row where `max_jump > 40` is a **monotonicity flag** — review, do not
auto-correct.

### 4.2 `qry_ExportFAI` — clean export for the FAI pipeline

```sql
SELECT e.study_id, e.patient_id, e.ear, e.test_month_year,
       p.age_years, p.sex,
       e.th_250, e.th_500, e.th_1k, e.th_2k, e.th_3k, e.th_4k, e.th_6k, e.th_8k,
       e.bc_500, e.bc_1k, e.bc_2k, e.bc_4k,
       e.diagnosis_category, e.consultant_grade, e.documented_shape,
       e.ear_included, e.exclusion_reason
FROM tbl_EarRecord AS e
INNER JOIN tbl_Patient AS p ON e.patient_id = p.patient_id
WHERE e.ear_included = 1
ORDER BY e.study_id;
```

---

## 5. Macros / VBA — batch operations

### 5.1 Export to CSV (one click)

Module `mod_Export`:

```vba
Public Sub ExportFAI_CSV()
    Dim qd As QueryDef, rst As DAO.Recordset, fso As Object, ts As Object
    Dim path As String, i As Integer, line As String

    path = CurrentProject.Path & "\fai_export_" & Format(Now, "yyyymmdd_hhnn") & ".csv"
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set ts = fso.CreateTextFile(path, True, True)

    Set qd = CurrentDb.QueryDefs("qry_ExportFAI")
    Set rst = qd.OpenRecordset()

    ' Header
    line = ""
    For i = 0 To rst.Fields.Count - 1
        line = line & IIf(i > 0, ",", "") & rst.Fields(i).Name
    Next i
    ts.WriteLine line

    ' Rows — blank as empty (no NA/./0)
    Do While Not rst.EOF
        line = ""
        For i = 0 To rst.Fields.Count - 1
            If IsNull(rst.Fields(i).Value) Then
                line = line & IIf(i > 0, ",", "") & ""
            Else
                line = line & IIf(i > 0, ",", "") & CStr(rst.Fields(i).Value)
            End If
        Next i
        ts.WriteLine line
        rst.MoveNext
    Loop

    ts.Close
    rst.Close
    MsgBox "Exported: " & path, vbInformation
End Sub
```

### 5.2 Auto-increment check (QA)

```vba
Public Function MissingStudyIDs() As Long
    ' Returns count of duplicate/missing study_ids for QA log
    Dim cnt As Long
    cnt = DCount("*", "qry_DuplicateStudyID")
    Debug.Print "Duplicate study_ids: " & cnt
    MissingStudyIDs = cnt
End Function
```

(SQL for `qry_DuplicateStudyID`:

```sql
SELECT study_id, COUNT(*) AS n
FROM tbl_EarRecord
GROUP BY study_id
HAVING COUNT(*) > 1;
```
)

---

## 6. Access → FAI pipeline handoff

1. Run `qry_DataEntryQA` after every batch of 20 — resolve flags.
2. Run `ExportFAI_CSV` → `fai_export_YYYYMMDD_HHNN.csv`.
3. Feed CSV to the Python validation script (repo-side):

```bash
python scripts/validate_oatuhc.py --input fai_export_YYYYMMDD_HHNN.csv
```

4. The script computes frozen-FAI `fai_score`, `fai_label`, `fai_config`,
   membership degrees, WHO grade, and the borderline flag — same contract as
   `data_dictionary.md` derived variables.

---

## 7. Security & hygiene

- **No PHI.** The schema collects no names, hospital numbers, addresses,
  phones or emails. `patient_id` is an arbitrary sequential number.
- Password-protect the database if multiple operators share a machine
  (File → Encrypt with Password).
- Keep a dated backup of the .accdb before each export batch.
- Store the .accdb on a network drive with per-user NTFS permissions if
  multi-user concurrent entry is needed; otherwise single-user on the
  entry machine and nightly backup.
- **Do not** store `created_by` as free text if operator names are sensitive —
  use a user code (initials).

---

## 8. Build checklist (Access steps in order)

- [ ] 1. Create tables: `tbl_Patient`, `tbl_EarRecord`, 3 lookup tables
- [ ] 2. Set field data types, validation rules, indexes per §1
- [ ] 3. Define relationships with referential integrity (§2)
- [ ] 4. Build `frm_PatientEntry` with BeforeUpdate/AfterUpdate VBA (§3.1)
- [ ] 5. Build `frm_EarRecord` with all controls + events (§3.2–3.4)
- [ ] 6. Create queries `qry_DataEntryQA`, `qry_ExportFAI`, `qry_DuplicateStudyID` (§4)
- [ ] 7. Add module `mod_Export` + ExportFAI_CSV (§5.1)
- [ ] 8. Test: enter 2 rows for one patient (L/R), export CSV, verify blank handling
- [ ] 9. Back up .accdb; hand to data-entry operators with the Instructions sheet
