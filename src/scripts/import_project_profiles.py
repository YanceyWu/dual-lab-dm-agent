#!/usr/bin/env python3
# ruff: noqa: E402
"""
Import project profiles from filled Excel template back to DB.
Usage: python3 scripts/import_project_profiles.py
       python3 scripts/import_project_profiles.py --file path/to/file.xlsx
       python3 scripts/import_project_profiles.py --dry-run
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pm_agent.config import get_database_path

DEFAULT_FILE = ROOT / "data-feed" / "Project_Profiles_Template.xlsx"

def parse_milestones(text):
    if not text or not str(text).strip():
        return []
    result = []
    for line in str(text).strip().split("\n"):
        line = line.strip()
        if "|" in line:
            parts = line.split("|", 1)
            result.append({"date": parts[0].strip(), "name": parts[1].strip()})
    return result

def parse_risks(text):
    if not text or not str(text).strip():
        return []
    result = []
    for line in str(text).strip().split("\n"):
        line = line.strip()
        if "|" in line:
            parts = line.split("|", 1)
            level = parts[1].strip().lower()
            if level not in ("high", "medium", "low"):
                level = "medium"
            result.append({"risk": parts[0].strip(), "level": level})
        elif line:
            result.append({"risk": line, "level": "medium"})
    return result

def parse_stakeholders(text):
    if not text or not str(text).strip():
        return []
    return [s.strip() for s in str(text).split(",") if s.strip()]

def safe(val, default=""):
    if val is None:
        return default
    s = str(val).strip()
    return s if s and s.lower() != "none" else default

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=str(DEFAULT_FILE))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    wb = openpyxl.load_workbook(args.file)
    ws = wb["Project Profiles"]
    conn = sqlite3.connect(get_database_path())

    updated = skipped = errors = 0

    for row in ws.iter_rows(min_row=4, values_only=True):
        project_name, team_size, phase, phase_detail, priority, focus, objective, \
            milestones_raw, risks_raw, stakeholders_raw, special_rules, project_id = row

        if not project_id:
            continue

        project_id = str(project_id).strip()
        if project_id.lower() == "project id":
            continue
        phase = safe(phase)
        if not phase or phase == "TBC":
            print(f"  SKIP  {safe(project_name, project_id)} — phase not filled")
            skipped += 1
            continue

        # Validate project exists
        exists = conn.execute("SELECT id FROM projects WHERE id=?", [project_id]).fetchone()
        if not exists:
            print(f"  ERROR {project_id} — not found in DB")
            errors += 1
            continue

        priority_int = 2
        try:
            priority_int = int(priority)
            if priority_int not in (1, 2, 3):
                priority_int = 2
        except Exception:
            pass

        is_focus = 1 if safe(focus).upper() == "Y" else 0
        milestones = json.dumps(parse_milestones(milestones_raw))
        key_risks = json.dumps(parse_risks(risks_raw))
        stakeholders = json.dumps(parse_stakeholders(stakeholders_raw))

        print(f"  {'DRY ' if args.dry_run else ''}UPDATE  {safe(project_name, project_id)}")
        print(f"         phase={phase} | priority={priority_int} | focus={is_focus}")
        print(f"         objective={safe(objective)[:60]}")

        if not args.dry_run:
            conn.execute("""
                INSERT INTO project_profiles
                    (project_id, phase, phase_detail, priority_tier, is_focus,
                     objective, milestones, key_risks, stakeholders, special_rules, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now'))
                ON CONFLICT(project_id) DO UPDATE SET
                    phase=excluded.phase, phase_detail=excluded.phase_detail,
                    priority_tier=excluded.priority_tier, is_focus=excluded.is_focus,
                    objective=excluded.objective, milestones=excluded.milestones,
                    key_risks=excluded.key_risks, stakeholders=excluded.stakeholders,
                    special_rules=excluded.special_rules, updated_at=excluded.updated_at
            """, [
                project_id, phase, safe(phase_detail), priority_int, is_focus,
                safe(objective), milestones, key_risks, stakeholders, safe(special_rules)
            ])
        updated += 1

    if not args.dry_run:
        conn.commit()

    conn.close()
    print(f"\nDone.  Updated: {updated}  Skipped: {skipped}  Errors: {errors}")
    if not args.dry_run:
        print("Run: python3 -m pm_agent.cli.app report  to verify")

if __name__ == "__main__":
    main()
