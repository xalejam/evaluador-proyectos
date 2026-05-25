# Heredar % de avance y sincronizar entre note_types Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify progress percent inheritance works correctly, and update historical data to ensure all note_types for the same date share the same progress percent.

**Architecture:** 
- Progress inheritance: Already implemented ✅ (lines 1235-1240, 1370 in seguimiento_operativo.py)
- Progress sync for new notes: Already implemented ✅ (all note_types get same value at line 1466)
- Data cleanup: Execute ONE SQL UPDATE to replicate progress_percent from 'general' to other note_types in historical data
- note_title: **Removed from scope** (no user value, not editable in UI)

**Tech Stack:** Streamlit, PostgreSQL/Supabase via adapter

---

## Task 1: Verify progress inheritance in current code (Code Review)

**Files:**
- Review: `ui/tabs/seguimiento_operativo.py:1235-1240, 1370, 1466`

**Description:** Verify that progress_percent inheritance is working correctly in the code.

- [ ] **Step 1: Check progress loading (lines 1235-1240)**

Expected code:
```python
latest_progress_df = get_project_progress_trend(conn, selected_project.project_id, limit=1)
last_progress_value = None
last_progress_date = None
if not latest_progress_df.empty:
    last_progress_value = latest_progress_df.iloc[0]["progress_percent"]
    last_progress_date = latest_progress_df.iloc[0]["created_at"]
```

This loads the last progress_percent from the project.

- [ ] **Step 2: Check default value in form (line 1370)**

Expected code:
```python
default_progress = (
    int(last_progress_value) if last_progress_value is not None and not pd.isna(last_progress_value) else 0
)
progress_percent_input = st.number_input(
    t("ops_progress_percent_label"),
    min_value=0,
    max_value=100,
    value=default_progress,  # ← Uses last value as default
    step=1,
    disabled=not enable_progress_capture,
    key=f"ops_progress_percent_{selected_project.project_id}",
)
```

This pre-fills the form with the last known progress_percent.

- [ ] **Step 3: Check progress sync across note_types (line 1466)**

Expected code:
```python
notes_to_insert.append(
    {
        "project_id": selected_project.project_id,
        "note_type": ntype,
        "note_text": str(ntext).strip(),
        "author": author.strip(),
        "tags": "",
        "is_private": False,
        "entry_group_id": entry_group_id,
        "note_title": "",  # ← Can stay empty or be removed
        "progress_percent": progress_percent_value,  # ← SAME for all note_types
        "estimated_end_date": estimated_end_date_value,
        "effort_hours": effort_hours_input if ntype == "general" else None,
    }
)
```

Same `progress_percent_value` is used for ALL note_types (general, proximo_paso, bloqueador, riesgo).

- [ ] **Step 4: Conclusion**

✅ **Code review complete:** Progress inheritance and sync are correctly implemented. No code changes needed.

---

## Task 2: Update historical data - Replicate progress_percent to all note_types

**Files:**
- Execute: SQL UPDATE via Supabase dashboard or Python connection

**Description:** For entries where progress_percent is only set on note_type='general', replicate that value to bloqueador, proximo_paso, and riesgo for the same date and project.

**Affected entries (example):**
- MX-DDD-0004 2026-05-18: bloqueador, proximo_paso, riesgo → all get 99
- MX-DDD-0005 2026-05-18: bloqueador, proximo_paso, riesgo → all get 70
- MX-DDD-0006 2026-05-18: bloqueador, proximo_paso, riesgo → all get 30
- MX-DDD-0006 2026-05-05: bloqueador, proximo_paso, riesgo → all get 20
- MX-DDD-0006 2026-05-01: bloqueador, proximo_paso, riesgo → all get 10

- [ ] **Step 1: Write the UPDATE query**

For PostgreSQL/Supabase:

```sql
UPDATE project_notes pn
SET progress_percent = (
    SELECT progress_percent
    FROM project_notes pn2
    WHERE pn2.project_id = pn.project_id
    AND pn2.note_type = 'general'
    AND pn2.created_at::date = pn.created_at::date
    AND pn2.progress_percent IS NOT NULL
    LIMIT 1
)
WHERE pn.note_type IN ('bloqueador', 'proximo_paso', 'riesgo')
AND (pn.progress_percent IS NULL OR pn.progress_percent = 0)
AND EXISTS (
    SELECT 1
    FROM project_notes pn3
    WHERE pn3.project_id = pn.project_id
    AND pn3.note_type = 'general'
    AND pn3.created_at::date = pn.created_at::date
    AND pn3.progress_percent IS NOT NULL
);
```

For SQLite (if needed):

```sql
UPDATE project_notes
SET progress_percent = (
    SELECT progress_percent
    FROM project_notes pn2
    WHERE pn2.project_id = project_notes.project_id
    AND pn2.note_type = 'general'
    AND DATE(pn2.created_at) = DATE(project_notes.created_at)
    AND pn2.progress_percent IS NOT NULL
    LIMIT 1
)
WHERE note_type IN ('bloqueador', 'proximo_paso', 'riesgo')
AND (progress_percent IS NULL OR progress_percent = 0)
AND EXISTS (
    SELECT 1
    FROM project_notes pn3
    WHERE pn3.project_id = project_notes.project_id
    AND pn3.note_type = 'general'
    AND DATE(pn3.created_at) = DATE(project_notes.created_at)
    AND pn3.progress_percent IS NOT NULL
);
```

- [ ] **Step 2: Execute the UPDATE query**

Run via Supabase SQL editor or Python connection:

```python
from infra.db.connection import get_sqlite_conn

with get_sqlite_conn() as conn:
    conn.execute("""
        UPDATE project_notes
        SET progress_percent = (
            SELECT progress_percent
            FROM project_notes pn2
            WHERE pn2.project_id = project_notes.project_id
            AND pn2.note_type = 'general'
            AND DATE(pn2.created_at) = DATE(project_notes.created_at)
            AND pn2.progress_percent IS NOT NULL
            LIMIT 1
        )
        WHERE note_type IN ('bloqueador', 'proximo_paso', 'riesgo')
        AND (progress_percent IS NULL OR progress_percent = 0)
        AND EXISTS (
            SELECT 1
            FROM project_notes pn3
            WHERE pn3.project_id = project_notes.project_id
            AND pn3.note_type = 'general'
            AND DATE(pn3.created_at) = DATE(project_notes.created_at)
            AND pn3.progress_percent IS NOT NULL
        )
    """)
    conn.commit()
```

Expected result: All bloqueador, proximo_paso, riesgo entries for the affected dates should now have progress_percent matching their 'general' counterparts.

- [ ] **Step 3: Verify the update**

Run this query to confirm:

```sql
SELECT project_id, created_at, note_type, progress_percent
FROM project_notes
WHERE created_at >= '2026-05-01' AND created_at < '2026-05-20'
ORDER BY project_id, created_at, note_type;
```

Expected output (example):
```
project_id      | created_at              | note_type     | progress_percent
MX-DDD-0004     | 2026-05-18 16:05:00     | bloqueador    | 99
MX-DDD-0004     | 2026-05-18 16:05:00     | general       | 99
MX-DDD-0004     | 2026-05-18 16:05:00     | proximo_paso  | 99
MX-DDD-0004     | 2026-05-18 16:05:00     | riesgo        | 99
MX-DDD-0005     | 2026-05-18 16:05:00     | bloqueador    | 70
MX-DDD-0005     | 2026-05-18 16:05:00     | general       | 70
MX-DDD-0005     | 2026-05-18 16:05:00     | proximo_paso  | 70
MX-DDD-0005     | 2026-05-18 16:05:00     | riesgo        | 70
```

All note_types for the same (project_id, date) should have matching progress_percent.

- [ ] **Step 4: Commit (document in memory)**

Update memory with what was done:

```bash
git add memory/MEMORY.md
git commit -m "data: replicate progress_percent from 'general' to all note_types for historical entries"
```

Add to `memory/MEMORY.md`:
```markdown
- Progress inheritance: User inherits last % when creating new note (auto-filled in form)
- Progress sync: All note_types get same % value when saving
- Historical data: Updated to replicate % from 'general' to bloqueador/proximo_paso/riesgo
- note_title: Removed from scope (no user value, not editable)
```

---

## Summary

**What's already working ✅:**
1. Progress inheritance: Loaded from last note and pre-filled in form
2. Progress sync: All note_types get the same value when creating a note
3. Code is correct and needs no changes

**What gets updated 🔧:**
1. Historical data: Replicate progress_percent to ensure all note_types have matching values for the same date

**Testing checklist:**
- [ ] Create a new note and verify default progress_percent is from last value
- [ ] Verify all 4 note_types (general, proximo_paso, bloqueador, riesgo) get the same progress_percent
- [ ] Verify historical update query runs without errors
- [ ] Query the updated rows to confirm all note_types now have progress_percent
- [ ] Run dashboard and timeline to verify visualizations work with synchronized data
