#!/usr/bin/env python3
"""Script to update specific note entries in the database."""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "project_viability.db"

def update_notes():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Update 1: Change date for c21160da07c64607a8befcd524b185b4 to March 4, 2026
    cursor.execute("""
        UPDATE project_notes
        SET created_at = '2026-03-04 22:05:46'
        WHERE entry_group_id = 'c21160da07c64607a8befcd524b185b4'
    """)

    # Update 2: Change date to March 16, 2026 and progress to 50% for c5b46f25dbf24ef1a1e0ed378e88e3df
    cursor.execute("""
        UPDATE project_notes
        SET created_at = '2026-03-16 22:07:02', progress_percent = 50
        WHERE entry_group_id = 'c5b46f25dbf24ef1a1e0ed378e88e3df'
    """)

    # Update 3: Change progress to 70% for 60683608b04e41a89a597cb1aef502d3
    cursor.execute("""
        UPDATE project_notes
        SET progress_percent = 70
        WHERE entry_group_id = '60683608b04e41a89a597cb1aef502d3'
    """)

    conn.commit()
    conn.close()
    print("Updates completed successfully.")

if __name__ == "__main__":
    update_notes()