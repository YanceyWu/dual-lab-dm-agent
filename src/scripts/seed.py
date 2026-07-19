"""Seed a small, fully synthetic local demonstration dataset.

For a richer example, prefer ``scripts/load_sample_data.py``. Real team data
must be imported from local ignored files and must never be added here.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pm_agent.database.bootstrap import main as init_db
from pm_agent.database.repository import create_assignment, upsert_member, upsert_project


DATASET_MARKER = "SYNTHETIC_DATASET_V1"

MEMBERS = [
    {
        "id": "990001",
        "name": "Alex Example",
        "email": "alex.example@example.invalid",
        "role": "pm",
        "level": "senior",
        "team": "Example Delivery Team",
        "lead_id": None,
        "max_parallel": 3,
        "skills": {"delivery_management": 0.9, "stakeholder_management": 0.8},
        "notes": DATASET_MARKER,
    },
    {
        "id": "990002",
        "name": "Blair Example",
        "email": "blair.example@example.invalid",
        "role": "backend",
        "level": "mid",
        "team": "Example Delivery Team",
        "lead_id": "990001",
        "max_parallel": 2,
        "skills": {"python": 0.7, "cloud_platforms": 0.5},
        "notes": DATASET_MARKER,
    },
    {
        "id": "990003",
        "name": "Casey Example",
        "email": "casey.example@example.invalid",
        "role": "fullstack",
        "level": "senior",
        "team": "Example Delivery Team",
        "lead_id": "990001",
        "max_parallel": 2,
        "skills": {"react": 0.7, "data_analysis": 0.5},
        "notes": DATASET_MARKER,
    },
    {
        "id": "990004",
        "name": "Drew Example",
        "email": "drew.example@example.invalid",
        "role": "pm-senior",
        "level": "lead",
        "team": "Example Delivery Team",
        "lead_id": None,
        "max_parallel": 3,
        "skills": {"portfolio_governance": 0.9},
        "notes": DATASET_MARKER,
    },
]

PROJECTS = [
    {
        "id": "project-atlas-990001",
        "name": "Project Atlas",
        "jira_key": "ATL",
        "status": "active",
        "priority": 1,
        "lead_id": "990001",
        "tech_stack": ["Python", "Cloud"],
        "start_date": "2026-01-01",
        "target_end": "2026-12-31",
        "notes": DATASET_MARKER,
    },
    {
        "id": "project-beacon-990002",
        "name": "Project Beacon",
        "jira_key": "BCN",
        "status": "active",
        "priority": 2,
        "lead_id": "990004",
        "tech_stack": ["React", "Data"],
        "start_date": "2026-02-01",
        "target_end": "2026-11-30",
        "notes": DATASET_MARKER,
    },
    {
        "id": "project-cedar-990003",
        "name": "Project Cedar",
        "jira_key": "CDR",
        "status": "planned",
        "priority": 3,
        "lead_id": "990001",
        "tech_stack": ["Python", "React"],
        "start_date": "2026-08-01",
        "target_end": "2027-02-28",
        "notes": DATASET_MARKER,
    },
]

ASSIGNMENTS = [
    ("990001", "project-atlas-990001", "delivery_manager", 0.5),
    ("990002", "project-atlas-990001", "backend_engineer", 0.8),
    ("990003", "project-beacon-990002", "fullstack_engineer", 0.7),
    ("990004", "project-beacon-990002", "delivery_manager", 0.4),
]


def main() -> None:
    init_db()

    for member in MEMBERS:
        upsert_member({**member, "status": "active", "metadata": {"dataset": DATASET_MARKER}})
    for project in PROJECTS:
        upsert_project({**project, "actual_end": None})
    for employee_id, project_id, role, allocation in ASSIGNMENTS:
        create_assignment(employee_id, project_id, role, allocation)

    print(
        f"Seeded {len(MEMBERS)} synthetic people, {len(PROJECTS)} synthetic projects, "
        f"and {len(ASSIGNMENTS)} assignments."
    )


if __name__ == "__main__":
    main()
