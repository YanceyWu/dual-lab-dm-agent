#!/usr/bin/env python3
"""
Interactive Project Profile Filler
Usage:
  python3 scripts/fill_project_profiles.py
  python3 scripts/fill_project_profiles.py --project atlas
  python3 scripts/fill_project_profiles.py --skip-done
"""
import sqlite3, json, argparse
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "pm.db"

PHASES = ["Planning", "Development", "UAT", "Go-Live", "Support", "On-Hold"]
TIER_LABELS = {1: "Tier 1 - Highest priority (attack)", 2: "Tier 2 - Normal progress", 3: "Tier 3 - Low priority"}

def ask(prompt, default=""):
    hint = f" [{default}]" if default else " (Enter to skip)"
    val = input(f"  {prompt}{hint}: ").strip()
    return val if val else default

def choose(prompt, options, default=None):
    print(f"\n  {prompt}")
    for i, o in enumerate(options, 1):
        marker = " <--" if o == default else ""
        print(f"    {i}) {o}{marker}")
    while True:
        val = input(f"  Select [1-{len(options)}]: ").strip()
        if not val and default:
            return default
        if val.isdigit() and 1 <= int(val) <= len(options):
            return options[int(val) - 1]

def ask_milestones():
    print("\n  Milestones - enter date + name pairs (blank date to finish)")
    milestones = []
    while True:
        date = input("    Date YYYY-MM (blank to finish): ").strip()
        if not date:
            break
        name = input("    Milestone name: ").strip()
        if name:
            milestones.append({"date": date, "name": name})
    return milestones

def ask_risks():
    print("\n  Key Risks (blank to finish)")
    risks = []
    while True:
        risk = input("    Risk description (blank to finish): ").strip()
        if not risk:
            break
        level = input("    Level [high/medium/low, default=medium]: ").strip() or "medium"
        risks.append({"risk": risk, "level": level})
    return risks

def ask_list(prompt, example=""):
    print(f"\n  {prompt}" + (f"  e.g. {example}" if example else ""))
    print("  (one per line, blank to finish)")
    items = []
    while True:
        val = input("  + ").strip()
        if not val:
            break
        items.append(val)
    return items

def get_team_size(conn, project_id):
    row = conn.execute(
        "SELECT COUNT(*) FROM assignments WHERE project_id=? AND status='active'",
        [project_id]
    ).fetchone()
    return row[0] if row else 0

def fill_project(conn, project_id, project_name):
    team_size = get_team_size(conn, project_id)
    print(f"\n{'='*58}")
    print(f"  Project: {project_name}")
    print(f"  ID: {project_id}  |  Team size: {team_size}")
    print(f"{'='*58}")

    row = conn.execute(
        "SELECT phase, objective FROM project_profiles WHERE project_id=?",
        [project_id]
    ).fetchone()
    if row and row[0] not in ("TBC", "", None):
        print(f"  Already filled: phase={row[0]}")
        ow = input("  Overwrite? [y/N]: ").strip().lower()
        if ow != "y":
            print("  Skipped.\n")
            return False

    phase = choose("Project phase?", PHASES)
    phase_detail = ask("Phase detail", default="")

    print("\n  Priority tier:")
    for k, v in TIER_LABELS.items():
        print(f"    {k}) {v}")
    t = input("  Select [1/2/3, default=2]: ").strip()
    priority_tier = int(t) if t in ("1","2","3") else 2

    is_focus = 1 if input("\n  Current focus/attack project? [y/N]: ").strip().lower() == "y" else 0

    objective = ask("One-line objective")

    do_ms = input("\n  Add milestones? [Y/n]: ").strip().lower()
    milestones = ask_milestones() if do_ms != "n" else []

    do_risk = input("\n  Add key risks? [Y/n]: ").strip().lower()
    key_risks = ask_risks() if do_risk != "n" else []

    do_stake = input("\n  Add stakeholders? [Y/n]: ").strip().lower()
    stakeholders = ask_list("Stakeholders", "CTO, Business Owner") if do_stake != "n" else []

    do_tech = input("\n  Add tech stack? [y/N]: ").strip().lower()
    tech_stack = ask_list("Technologies", "Java, Spring Boot") if do_tech == "y" else []

    special_rules = ask("Special rules / compliance notes")

    print(f"\n  Summary:")
    print(f"    Phase:       {phase}  {phase_detail}")
    print(f"    Priority:    Tier {priority_tier} {'(FOCUS)' if is_focus else ''}")
    print(f"    Objective:   {objective or '--'}")
    print(f"    Milestones:  {len(milestones)}")
    print(f"    Risks:       {len(key_risks)}")
    print(f"    Stakeholders:{', '.join(stakeholders) or '--'}")

    if input("\n  Save? [Y/n]: ").strip().lower() == "n":
        print("  Discarded.\n")
        return False

    conn.execute("""
        INSERT INTO project_profiles
            (project_id, phase, phase_detail, priority_tier, is_focus,
             objective, milestones, key_risks, stakeholders, tech_stack,
             special_rules, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
        ON CONFLICT(project_id) DO UPDATE SET
            phase=excluded.phase, phase_detail=excluded.phase_detail,
            priority_tier=excluded.priority_tier, is_focus=excluded.is_focus,
            objective=excluded.objective, milestones=excluded.milestones,
            key_risks=excluded.key_risks, stakeholders=excluded.stakeholders,
            tech_stack=excluded.tech_stack, special_rules=excluded.special_rules,
            updated_at=excluded.updated_at
    """, [
        project_id, phase, phase_detail, priority_tier, is_focus,
        objective, json.dumps(milestones), json.dumps(key_risks),
        json.dumps(stakeholders), json.dumps(tech_stack), special_rules
    ])
    conn.commit()
    print("  Saved!\n")
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", help="Filter by name (partial match)")
    parser.add_argument("--skip-done", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    sql = "SELECT id, name FROM projects WHERE status='active'"
    params = []
    if args.project:
        sql += " AND name LIKE ?"
        params.append(f"%{args.project}%")
    sql += " ORDER BY name"

    projects = conn.execute(sql, params).fetchall()
    if not projects:
        print("No matching projects.")
        return

    print(f"\nProject Profile Filler  ({len(projects)} projects)")
    print("Press Enter to skip optional fields, Ctrl+C to quit\n")

    filled = skipped = 0
    for p in projects:
        if args.skip_done:
            r = conn.execute("SELECT phase FROM project_profiles WHERE project_id=?", [p["id"]]).fetchone()
            if r and r[0] not in ("TBC","",None):
                print(f"  -- {p['name']} already filled, skipping")
                skipped += 1
                continue
        if fill_project(conn, p["id"], p["name"]):
            filled += 1
        else:
            skipped += 1

    print(f"\nDone.  Filled: {filled}  Skipped: {skipped}")
    print("Run: python3 -m pm_agent.cli.app report  to see updated status")
    conn.close()

if __name__ == "__main__":
    main()
