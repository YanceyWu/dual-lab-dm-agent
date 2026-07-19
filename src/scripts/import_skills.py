# ruff: noqa: E402
"""
Import employee roles, grades, and skills from:
  - data-feed/team_data.json   → role, level, email
  - data-feed/skillset.json    → skills dict {skill_name: score}

Skill proficiency → score mapping:
  1 - Entry          → 0.2
  2 - Intermediate   → 0.4
  3 - Foundation     → 0.5
  4 - Experienced    → 0.7
  5 - Expert         → 0.9
  6 - Thought Leader → 1.0

Grade → level mapping:
  Level 5 → mid
  Level 6 → senior
  Level 7 → lead
  (other)  → mid (fallback)

Job profile → role mapping:
  *Senior*Project Manager → pm-senior
  *Project Manager        → pm
  *Back-end*              → backend
  *Front-end*             → frontend
  *Full-stack*            → fullstack
  Contingent Worker       → contractor
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pm_agent.database.bootstrap import main as init_db
from pm_agent.config import get_database_path
from pm_agent.database import repository

DEFAULT_TEAM_DATA = ROOT / "data-feed" / "team_data.json"
DEFAULT_SKILL_DATA = ROOT / "data-feed" / "skillset.json"

# ── Field IDs in skillset.json ───────────────────────────────────────────────
SKILL_NAME_FIELD   = "4e1c5171c0ff4c4f9bd582d7983ad9e8"
PROF_LEVEL_FIELD   = "7fea42e3132e42459a59f7408e9822c8"
EMP_ID_FIELD       = "employee_id"

PROF_SCORE = {
    "1 - entry":          0.2,
    "2 - intermediate":   0.4,
    "3 - foundation":     0.5,
    "4 - experienced":    0.7,
    "5 - expert":         0.9,
    "6 - thought leader": 1.0,
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def map_grade(grade: str) -> str:
    g = grade.strip().lower()
    if "level 5" in g:
        return "mid"
    if "level 6" in g:
        return "senior"
    if "level 7" in g:
        return "lead"
    return "mid"


def map_job_profile(profile: str) -> str:
    p = profile.lower()
    if "senior" in p and "project manager" in p:
        return "pm-senior"
    if "project manager" in p:
        return "pm"
    if "back-end" in p or "backend" in p:
        return "backend"
    if "front-end" in p or "frontend" in p:
        return "frontend"
    if "full-stack" in p or "fullstack" in p:
        return "fullstack"
    if "contingent" in p:
        return "contractor"
    return "engineer"


def normalise_emp_id(raw_id: str) -> str:
    """Strip 'C' suffix added by some HR systems."""
    return raw_id.rstrip("C").rstrip("c")


def db_slug_to_numeric(slug: str) -> str:
    """Return the comparable numeric Workday ID for matching.
    'worker990101' → '990101', '990102' → '990102'
    """
    match = re.search(r"(\d+)$", slug)
    return match.group(1) if match else slug


# ── Load source files ────────────────────────────────────────────────────────

def load_team_data(team_data_path: Path) -> dict:
    """Returns {numeric_id: record} for all team members."""
    with open(team_data_path, encoding="utf-8") as f:
        records = json.load(f)
    lookup = {}
    for r in records:
        raw = r["id"]
        lookup[raw] = r
        numeric = re.sub(r"[^0-9]", "", raw)
        if numeric != raw:
            lookup[numeric] = r
    return lookup


def load_skill_data(skill_data_path: Path) -> dict:
    """Returns {numeric_emp_id: {skill_name: score}} for all skill records."""
    with open(skill_data_path, encoding="utf-8") as f:
        payload = json.load(f)
    records = payload["data"]

    emp_skills: dict[str, dict[str, float]] = {}

    for r in records:
        vd = r["version_display"]["data"]

        # Employee ID
        emp_raw = vd.get(EMP_ID_FIELD, {}).get("value", "")
        if isinstance(emp_raw, dict):
            emp_id = normalise_emp_id(emp_raw.get("record_id", ""))
        else:
            emp_id = normalise_emp_id(str(emp_raw))
        if not emp_id:
            continue

        # Skill name
        skill_raw = vd.get(SKILL_NAME_FIELD, {}).get("value", "")
        skill = skill_raw.get("value", "") if isinstance(skill_raw, dict) else str(skill_raw)
        skill = skill.strip()
        if not skill:
            continue

        # Proficiency → score
        prof_raw = vd.get(PROF_LEVEL_FIELD, {}).get("value", "")
        prof_key = str(prof_raw).strip().lower()
        score = PROF_SCORE.get(prof_key, 0.5)

        if emp_id not in emp_skills:
            emp_skills[emp_id] = {}
        # Keep highest score if skill appears twice
        if skill not in emp_skills[emp_id] or emp_skills[emp_id][skill] < score:
            emp_skills[emp_id][skill] = score

    return emp_skills


# ── Main import ──────────────────────────────────────────────────────────────

def import_skills(
    team_data_path: Path = DEFAULT_TEAM_DATA,
    skill_data_path: Path = DEFAULT_SKILL_DATA,
) -> None:
    init_db()
    run_id = repository.start_sync_run(
        "import-skills-matrix",
        run_type="file-import",
        target_tables=["employees"],
        artifact_path=f"{team_data_path.resolve()} | {skill_data_path.resolve()}",
        triggered_by="cli",
        notes="Role/level/skills enrichment import",
    )
    print("Loading source files…")
    con = None
    try:
        team_lookup = load_team_data(team_data_path)
        skill_lookup = load_skill_data(skill_data_path)

        print(f"  team_data: {len(team_lookup)} ID entries")
        print(f"  skillset:  {len(skill_lookup)} employees with skills")

        con = sqlite3.connect(get_database_path())
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        employees = cur.execute("SELECT id, name FROM employees").fetchall()
        print(f"  DB employees: {len(employees)}")

        updated_role = 0
        updated_skills = 0
        skipped = []

        for emp in employees:
            db_id = emp["id"]
            numeric_id = db_slug_to_numeric(db_id)

            updates: dict[str, str] = {}

            # ── Role / level from team_data ──────────────────────────────────
            td = team_lookup.get(db_id) or team_lookup.get(numeric_id)
            if td:
                grade   = td.get("grade", "")
                profile = td.get("jobProfile", "")
                email   = td.get("email", "")
                updates["role"]  = map_job_profile(profile)
                updates["level"] = map_grade(grade)
                if email:
                    updates["email"] = email
                updated_role += 1

            # ── Skills from skillset ─────────────────────────────────────────
            skill_map = skill_lookup.get(db_id) or skill_lookup.get(numeric_id)
            if skill_map:
                updates["skills"] = json.dumps(skill_map, ensure_ascii=False)
                updated_skills += 1

            if updates:
                set_clause = ", ".join(f"{k} = ?" for k in updates)
                values     = list(updates.values()) + [db_id]
                cur.execute(f"UPDATE employees SET {set_clause} WHERE id = ?", values)
            else:
                skipped.append(db_id)

        con.commit()
        con.close()
        con = None
        repository.finish_sync_run(
            run_id,
            rows_in=len(team_lookup) + len(skill_lookup),
            rows_changed=updated_role + updated_skills,
            notes="Role/level/skills enrichment import completed successfully.",
        )

        print("\n✅ Done:")
        print(f"   Role/level updated: {updated_role}")
        print(f"   Skills updated:     {updated_skills}")
        print(f"   Skipped (no data):  {len(skipped)} — {skipped[:8]}")
    except Exception as exc:
        if con is not None:
            con.close()
        repository.fail_sync_run(run_id, str(exc))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import skills/team JSON into pm.db")
    parser.add_argument(
        "--team-data",
        default=str(DEFAULT_TEAM_DATA),
        help="Path to team_data.json",
    )
    parser.add_argument(
        "--skill-data",
        default=str(DEFAULT_SKILL_DATA),
        help="Path to skillset.json",
    )
    args = parser.parse_args()
    import_skills(Path(args.team_data), Path(args.skill_data))
