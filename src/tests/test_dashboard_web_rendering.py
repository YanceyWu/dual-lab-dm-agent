from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
WEB_JS = ROOT / "pm_agent" / "dashboard" / "web" / "js"


def _node_executable_or_skip() -> str:
    executable = shutil.which("node") or shutil.which("nodejs")
    if executable is None:
        pytest.skip("node runtime is required for dashboard web rendering checks")
    return executable


def test_legacy_dashboard_rendering_replaces_null_with_placeholders() -> None:
    script = textwrap.dedent(
        f"""
        const fs = require("fs");
        const vm = require("vm");

        global.CONFIG = {{ COLORS: ["#00838f"] }};
        const elements = {{}};
        global.document = {{
          getElementById(id) {{
            if (!elements[id]) {{
              elements[id] = {{
                id,
                innerHTML: "",
                textContent: "",
                className: "",
                value: "",
              }};
            }}
            return elements[id];
          }}
        }};

        function load(name) {{
          const source = fs.readFileSync("{WEB_JS.as_posix()}/" + name, "utf8");
          vm.runInThisContext(source, {{ filename: name }});
        }}

        load("utils.js");
        load("components.js");
        load("provider-common.js");
        load("provider-overview.js");
        load("provider-hiref.js");
        load("section-overview.js");
        load("section-hiref.js");

        if (!C.kpiCard("Test KPI", null, null, "").includes(">—<")) {{
          throw new Error("kpiCard should render placeholders for null values");
        }}
        if (!C.kpiCard("Zero KPI", 0, 0, "").includes(">0<")) {{
          throw new Error("kpiCard should preserve zero values");
        }}

        global.DataService = {{
          summary: () => Promise.resolve({{
            total_staff: 3,
            ltfte: 0,
            stfte: 3,
            active_projects: 2,
            focus_projects: 0,
            avg_load: null,
            overloaded: null,
            hiref_alerts_60d: null,
            free_hiref_slots: null,
            current_state_staffing_freshness_state: "unknown",
            contract_coverage_freshness_state: "partial",
            updated_at: "2026-08-06 12:21:47",
          }}),
          projects: () => Promise.resolve([]),
          employees: () => Promise.resolve([]),
          hiref: () => Promise.resolve({{
            total: 4,
            assigned_count: null,
            free_count: null,
            next_covered_count: null,
            mismatch_count: null,
            review_counts_available: false,
            contract_coverage_freshness_state: "partial",
            expiring_staff: [],
            all_hiref: [],
          }}),
        }};

        async function flush() {{
          await Promise.resolve();
          await new Promise((resolve) => setTimeout(resolve, 0));
        }}

        async function main() {{
          SectionOverview.load();
          await flush();
          const overviewHtml = elements["overview-content"].innerHTML;
          if (overviewHtml.includes("null")) {{
            throw new Error("overview rendered literal null");
          }}
          if (!overviewHtml.includes("Unknown")) {{
            throw new Error("overview should show Unknown placeholders");
          }}
          if (!overviewHtml.includes("Contract coverage partial")) {{
            throw new Error("overview should explain suppressed contract metrics");
          }}

          SectionHiref.load();
          await flush();
          const hirefHtml = elements["hiref-content"].innerHTML;
          if (hirefHtml.includes("null")) {{
            throw new Error("hiref rendered literal null");
          }}
          if (!hirefHtml.includes("Unknown")) {{
            throw new Error("hiref should show Unknown placeholders");
          }}
          if (!hirefHtml.includes("Contract coverage partial")) {{
            throw new Error("hiref should explain suppressed contract metrics");
          }}
          if (hirefHtml.includes("No staff with HIREF expiring within 180 days")) {{
            throw new Error("hiref should not render a healthy empty-state message when review counts are unavailable");
          }}
          const hirefModel = await HirefPageProvider.load();
          if (hirefModel.kpis.critical.value !== "Unknown") {{
            throw new Error("hiref critical KPI should stay unknown when review counts are unavailable");
          }}
          if (hirefModel.kpis.high.value !== "Unknown") {{
            throw new Error("hiref high KPI should stay unknown when review counts are unavailable");
          }}
          if (hirefModel.kpis.freeSlots.variant !== "") {{
            throw new Error("hiref should not highlight free-slot KPI when slot counts are unavailable");
          }}
          global.DataService = {{
            hiref: () => Promise.resolve({{
              total: 1,
              assigned_count: null,
              free_count: null,
              next_covered_count: null,
              mismatch_count: null,
              review_counts_available: false,
              contract_coverage_freshness_state: "partial",
              expiring_staff: [
                {{
                  current_hiref_missing: true,
                  urgency: "critical",
                }},
              ],
              all_hiref: [],
            }}),
          }};
          const degradedHirefModel = await HirefPageProvider.load();
          if (degradedHirefModel.expiringStaffState !== "unavailable") {{
            throw new Error("hiref expiry table should stay unavailable when review counts are suppressed");
          }}
        }}

        main().catch((err) => {{
          console.error(err);
          process.exit(1);
        }});
        """
    )
    subprocess.run([_node_executable_or_skip(), "-e", script], check=True, cwd=ROOT)


def test_project_health_provider_owns_page_summary_and_confirmation_contract() -> None:
    script = textwrap.dedent(
        f"""
        const fs = require("fs");
        const vm = require("vm");

        function load(name) {{
          const source = fs.readFileSync("{WEB_JS.as_posix()}/" + name, "utf8");
          vm.runInThisContext(source, {{ filename: name }});
        }}

        load("provider-common.js");
        load("provider-health.js");

        global.DataService = {{
          projectHealth: () => Promise.resolve([
            {{
              id: "proj-red",
              name: "Project Red",
              phase: "Build",
              health: {{
                board_id: "BOARD-RED",
                board_name: "Board Red",
                board_url: "https://example.test/red",
                jira: {{
                  snapshot_date: "2026-08-01",
                  overall_grade: "RED",
                  overall_score: 42,
                  risks_json: "[]",
                  new_bugs_p1p2: 0,
                  sprint_completion_pct: 80,
                  unestimated_pct: 0,
                }},
                confluence: {{}},
                freshness: {{
                  jira_health: {{ freshness_state: "fresh" }},
                }},
              }},
            }},
            {{
              id: "proj-sparse",
              name: "Project Sparse",
              phase: "Build",
              health: {{
                board_id: "BOARD-SPARSE",
                board_name: "Board Sparse",
                jira: {{
                  snapshot_date: "2026-08-01",
                  overall_grade: "GREEN",
                  risks_json: "[]",
                }},
                confluence: {{}},
                freshness: {{
                  jira_health: {{ freshness_state: "fresh" }},
                }},
              }},
            }},
            {{
              id: "proj-sync",
              name: "Project Sync",
              phase: "Build",
              health: {{
                board_id: "BOARD-SYNC",
                board_name: "Board Sync",
                jira: {{}},
                confluence: {{}},
                freshness: {{}},
              }},
            }},
            {{
              id: "proj-none",
              name: "Project None",
              phase: "Start",
              health: null,
            }},
          ]),
          previewProjectHealthSync: () => Promise.resolve({{
            requires_confirmation: true,
            targets: [{{ board_id: "BOARD-RED", board_name: "Board Red" }}],
          }}),
          previewStaleProjectHealthSync: () => Promise.resolve({{
            requires_confirmation: true,
            targets: [
              {{ board_id: "BOARD-SYNC", board_name: "Board Sync" }},
              {{ board_id: "BOARD-OLD", board_name: "Board Old" }},
            ],
          }}),
          confirmProjectHealthSync: () => Promise.resolve({{
            message: "ok",
          }}),
        }};

        async function main() {{
          const model = await ProjectHealthPageProvider.load();
          if (model.summary.kpis.needsAttention.value !== 1) {{
            throw new Error("health provider should own attention KPI derivation");
          }}
          if (model.summary.kpis.needSync.value !== 1) {{
            throw new Error("health provider should own sync KPI derivation");
          }}
          if (model.summary.kpis.noBoardLink.value !== 1) {{
            throw new Error("health provider should own no-board KPI derivation");
          }}
          if (!model.summary.alerts.some((alert) => alert.message.includes("need PM attention"))) {{
            throw new Error("health provider should own page alert derivation");
          }}
          const sparse = model.projects.find((project) => project.id === "proj-sparse");
          if (sparse.jiraSummary.spProgressText !== "Unknown") {{
            throw new Error("health provider should keep missing SP progress explicit");
          }}
          if (sparse.jiraSummary.totalDefectsText !== "Unknown") {{
            throw new Error("health provider should keep missing defect counts explicit");
          }}

          const boardPreview = await ProjectHealthPageProvider.previewBoardSync("BOARD-RED");
          if (!boardPreview.confirmationMessage.includes("Sync 1 JIRA board(s): Board Red")) {{
            throw new Error("health provider should own board-sync confirmation text");
          }}

          const stalePreview = await ProjectHealthPageProvider.previewStaleSync();
          if (!stalePreview.confirmationMessage.includes("Sync stale 2 JIRA board(s): Board Sync, Board Old")) {{
            throw new Error("health provider should own stale-sync confirmation text");
          }}
        }}

        main().catch((err) => {{
          console.error(err);
          process.exit(1);
        }});
        """
    )
    subprocess.run([_node_executable_or_skip(), "-e", script], check=True, cwd=ROOT)


def test_monthly_plan_provider_owns_table_display_contracts() -> None:
    script = textwrap.dedent(
        f"""
        const fs = require("fs");
        const vm = require("vm");

        function load(name) {{
          const source = fs.readFileSync("{WEB_JS.as_posix()}/" + name, "utf8");
          vm.runInThisContext(source, {{ filename: name }});
        }}

        load("utils.js");
        load("provider-common.js");
        load("provider-allocation.js");

        global.DataService = {{
          allocations: () => Promise.resolve([
            {{
              employee_id: "emp-1",
              name: "Alex Example",
              wd_id: "990101C",
              project_id: "project-1",
              project_name: "Project One",
              year: 2026,
              month: 8,
              allocation: 1.2,
            }},
            {{
              employee_id: "emp-1",
              name: "Alex Example",
              wd_id: "990101C",
              project_id: "project-1",
              project_name: "Project One",
              year: 2026,
              month: 9,
              allocation: 0.8,
            }},
          ]),
        }};

        async function main() {{
          const model = await MonthlyPlanPageProvider.load();
          if (!model.employeeView || !model.projectView) {{
            throw new Error("allocation provider should own employee/project view contracts");
          }}
          if (model.employeeView.rows[0].cells[0].className !== "e-over") {{
            throw new Error("allocation provider should own employee severity classes");
          }}
          if (model.employeeView.rows[0].detailRows[0].cells[0].className !== "p-ok") {{
            throw new Error("allocation provider should own employee detail project cells");
          }}
          if (model.projectView.rows[0].detailRows[0].cells[0].className !== "e-over") {{
            throw new Error("allocation provider should own project detail member cells");
          }}
        }}

        main().catch((err) => {{
          console.error(err);
          process.exit(1);
        }});
        """
    )
    subprocess.run([_node_executable_or_skip(), "-e", script], check=True, cwd=ROOT)


def test_legacy_dashboard_overview_fallback_and_load_errors_remain_honest() -> None:
    script = textwrap.dedent(
        f"""
        const fs = require("fs");
        const vm = require("vm");

        global.CONFIG = {{ COLORS: ["#00838f"] }};
        const elements = {{}};
        global.document = {{
          getElementById(id) {{
            if (!elements[id]) {{
              elements[id] = {{
                id,
                innerHTML: "",
                textContent: "",
                className: "",
                value: "",
              }};
            }}
            return elements[id];
          }}
        }};

        function load(name) {{
          const source = fs.readFileSync("{WEB_JS.as_posix()}/" + name, "utf8");
          vm.runInThisContext(source, {{ filename: name }});
        }}

        load("utils.js");
        load("components.js");
        load("provider-common.js");
        load("provider-overview.js");
        load("provider-projects.js");
        load("provider-team.js");
        load("section-projects.js");
        load("section-overview.js");
        load("section-team.js");

        async function flush() {{
          await Promise.resolve();
          await new Promise((resolve) => setTimeout(resolve, 0));
        }}

        async function main() {{
          global.DataService = {{
            summary: () => Promise.reject(new Error("summary unavailable")),
            projects: () => Promise.resolve([]),
            employees: () => Promise.resolve([]),
            hiref: () => Promise.resolve({{
              expiring_staff: [
                {{
                  current_hiref_missing: true,
                  next_hiref: "",
                  urgency: "critical",
                  days_until_expiry: null,
                }},
                {{
                  current_hiref_missing: false,
                  next_hiref: "",
                  urgency: "critical",
                  days_until_expiry: 30,
                }},
                {{
                  current_hiref_missing: false,
                  next_hiref: "",
                  urgency: "medium",
                  days_until_expiry: 120,
                }},
                {{
                  current_hiref_missing: false,
                  next_hiref: "HIREF-NEXT-001",
                  urgency: "critical",
                  days_until_expiry: 15,
                }},
              ],
              free_count: 0,
              review_counts_available: true,
            }}),
          }};

          SectionOverview.load();
          await flush();
          const overviewHtml = elements["overview-content"].innerHTML;
          if (!overviewHtml.includes("2 contractor(s)</strong> have HIREF expiring within 60 days")) {{
            throw new Error("overview should keep the 60-day HIREF alert count when summary is unavailable");
          }}
          if (overviewHtml.includes("3 contractor(s)</strong> have HIREF expiring within 60 days")) {{
            throw new Error("overview should not overcount medium-risk 180-day HIREF rows");
          }}

          global.DataService = {{
            summary: () => Promise.reject(new Error("summary unavailable")),
            projects: () => Promise.resolve([]),
            employees: () => Promise.resolve([]),
            hiref: () => Promise.resolve({{
              expiring_staff: [],
              free_count: null,
              next_covered_count: null,
              mismatch_count: null,
              review_counts_available: false,
              contract_coverage_freshness_state: "unknown",
            }}),
          }};
          SectionOverview.load();
          await flush();
          const overviewUnknownHirefHtml = elements["overview-content"].innerHTML;
          if (!overviewUnknownHirefHtml.includes("Contract coverage unknown")) {{
            throw new Error("overview should preserve contract-coverage degraded semantics when HIREF counts are unavailable");
          }}
          if (overviewUnknownHirefHtml.includes(">OK<")) {{
            throw new Error("overview should not render HIREF as OK when contract coverage is unavailable");
          }}
          if (!elements["badge-hiref"].className.includes("muted")) {{
            throw new Error("overview HIREF badge should render degraded counts with muted tone");
          }}

          global.DataService = {{
            summary: () => Promise.reject(new Error("summary unavailable")),
            projects: () => Promise.resolve([]),
            employees: () => Promise.resolve([
              {{
                current_state_staffing_state: "known",
                load_pct: 80,
              }},
              {{
                current_state_staffing_state: "unknown",
                load_pct: null,
              }},
            ]),
            hiref: () => Promise.resolve({{
              expiring_staff: [],
              free_count: 0,
              review_counts_available: true,
            }}),
          }};
          const partialOverviewModel = await OverviewPageProvider.load();
          if (partialOverviewModel.loadDistribution.state !== "unavailable") {{
            throw new Error("overview should not render a complete load distribution from mixed known/unknown staffing rows");
          }}
          if (partialOverviewModel.loadDistribution.message !== "Current-state staffing partial") {{
            throw new Error("overview should keep partial staffing coverage explicit when summary is unavailable");
          }}
          if (partialOverviewModel.cards.avgLoad.variant !== "") {{
            throw new Error("overview avg-load KPI should not signal overload when staffing coverage is partial");
          }}
          if (partialOverviewModel.alerts.some((alert) => alert.message.includes("exceeding 100%"))) {{
            throw new Error("overview should not render overload alerts from partial staffing coverage");
          }}

          global.DataService = {{
            summary: () => Promise.resolve({{
              current_state_staffing_state: "partial",
              current_state_staffing_freshness_state: "fresh",
              contract_coverage_freshness_state: "fresh",
              hiref_alerts_60d: 0,
              free_hiref_slots: 0,
              updated_at: "2026-08-06 12:21:47",
            }}),
            projects: () => Promise.resolve([]),
            employees: () => Promise.resolve([
              {{
                current_state_staffing_state: "known",
                load_pct: 80,
              }},
              {{
                current_state_staffing_state: "unknown",
                load_pct: null,
              }},
            ]),
            hiref: () => Promise.resolve({{
              expiring_staff: [],
              free_count: 0,
              review_counts_available: true,
            }}),
          }};
          const summaryCoverageModel = await OverviewPageProvider.load();
          if (summaryCoverageModel.loadDistribution.state !== "unavailable") {{
            throw new Error("overview should respect summary staffing coverage before rendering load distribution");
          }}
          if (summaryCoverageModel.loadDistribution.message !== "Current-state staffing partial") {{
            throw new Error("overview should keep summary staffing coverage explicit when freshness alone looks healthy");
          }}
          if (summaryCoverageModel.cards.avgLoad.subtitle !== "Current-state staffing partial") {{
            throw new Error("overview avg-load card should preserve partial staffing coverage when overload rollups are unavailable");
          }}

          global.DataService = {{
            summary: () => Promise.reject(new Error("summary unavailable")),
            projects: () => Promise.resolve([]),
            employees: () => Promise.resolve([
              {{
                current_state_staffing_state: "known",
                load_pct: 120,
              }},
              {{
                current_state_staffing_state: "known",
                load_pct: 80,
              }},
            ]),
            hiref: () => Promise.resolve({{
              expiring_staff: [
                {{
                  current_hiref_missing: true,
                  next_hiref: "",
                  urgency: "critical",
                  days_until_expiry: null,
                }},
              ],
              free_count: 0,
              review_counts_available: true,
            }}),
          }};
          const derivedOverviewModel = await OverviewPageProvider.load();
          if (derivedOverviewModel.cards.avgLoad.variant !== "coral") {{
            throw new Error("overview should keep derived overload KPI tone when summary is unavailable but staffing coverage is complete");
          }}
          if (derivedOverviewModel.cards.hirefAlerts.variant !== "amber") {{
            throw new Error("overview should keep derived HIREF KPI tone when summary is unavailable");
          }}
          if (derivedOverviewModel.cards.freeHiref.variant !== "info") {{
            throw new Error("overview should keep free-slot KPI emphasis only when the slot count is known");
          }}
          if (!derivedOverviewModel.alerts.some((alert) => alert.message.includes("1 staff</strong> exceeding 100%"))) {{
            throw new Error("overview should keep overload alerts when staffing coverage is complete");
          }}

          global.DataService = {{
            summary: () => Promise.resolve({{
              total_staff: 3,
              ltfte: 1,
              stfte: 2,
              active_projects: 2,
              focus_projects: 1,
              avg_load: 90,
              overloaded: 0,
              hiref_alerts_60d: null,
              free_hiref_slots: null,
              current_state_staffing_freshness_state: "fresh",
              contract_coverage_freshness_state: "unknown",
              updated_at: "2026-08-06 12:21:47",
            }}),
            projects: () => Promise.reject(new Error("projects unavailable")),
            employees: () => Promise.reject(new Error("employees unavailable")),
            hiref: () => Promise.resolve({{
              expiring_staff: [],
              free_count: null,
              review_counts_available: false,
              contract_coverage_freshness_state: "unknown",
            }}),
          }};
          SectionOverview.load();
          await flush();
          if (!elements["badge-projects"].className.includes("muted")) {{
            throw new Error("overview projects badge should render unavailable counts with muted tone");
          }}
          if (!elements["badge-team"].className.includes("muted")) {{
            throw new Error("overview team badge should render unavailable counts with muted tone");
          }}
          if (!elements["badge-hiref"].className.includes("muted")) {{
            throw new Error("overview hiref badge should keep suppressed counts muted");
          }}

          const suppressedOverviewModel = await OverviewPageProvider.load();
          if (suppressedOverviewModel.cards.freeHiref.variant !== "") {{
            throw new Error("overview should not highlight free-slot KPI when slot counts are unavailable");
          }}

          global.DataService = {{
            projects: () => Promise.resolve([
              {{
                id: "project-1",
                name: "Project One",
                phase: "Build",
                priority_tier: 1,
                members: [
                  {{
                    wd_id: "990001",
                    id: "emp-1",
                    name: "Planned Member",
                    allocation: 0.5,
                    assign_status: "planned",
                  }},
                ],
                team_size: null,
                current_state_staffing_state: "partial",
                current_state_staffing_freshness_state: "fresh",
                milestones: [],
              }},
            ]),
            projectHealth: () => Promise.resolve([]),
          }};
          SectionProjects.load();
          await flush();
          const projectsHtml = elements["projects-content"].innerHTML;
          if (projectsHtml.includes("1 staff assigned")) {{
            throw new Error("projects should not render planned members as authoritative assigned staff when staffing coverage is partial");
          }}
          if (!projectsHtml.includes("Current-state staffing partial")) {{
            throw new Error("projects should keep staffing degradation explicit when authoritative team size is unavailable");
          }}

          global.DataService = {{
            employees: () => Promise.resolve([
              {{
                id: "emp-2",
                wd_id: "990002",
                name: "Contractor Example",
                is_contractor: true,
                current_hiref: "HIREF-001",
                hiref_end_date: "2026-12-31",
                contract_coverage_freshness_state: "unknown",
                current_state_staffing_state: "known",
                load_pct: 75,
                projects: [],
              }},
            ]),
          }};
          const degradedTeamModel = await TeamPageProvider.load();
          const degradedTeamRow = C.staffRow(degradedTeamModel.rows[0]);
          if (!degradedTeamRow.includes("Contract coverage unknown")) {{
            throw new Error("team should show degraded HIREF state when contract coverage is unavailable");
          }}
          if (degradedTeamRow.includes(">OK<")) {{
            throw new Error("team should not fall back to healthy HIREF status when urgency is unavailable");
          }}

          global.DataService = {{
            employees: () => Promise.reject(new Error("backend down")),
          }};
          SectionTeam.load();
          await flush();
          const teamHtml = elements["team-content"].innerHTML;
          if (!teamHtml.includes("Error loading team: backend down")) {{
            throw new Error("team section should surface the provider load error");
          }}
          if (teamHtml.includes("Error: Error loading team")) {{
            throw new Error("team section should not duplicate the provider error prefix");
          }}

          global.DataService = {{
            summary: () => Promise.reject(new Error("summary unavailable")),
            projects: () => Promise.reject(new Error("projects unavailable")),
            employees: () => Promise.reject(new Error("employees unavailable")),
            hiref: () => Promise.reject(new Error("hiref unavailable")),
          }};
          SectionOverview.load();
          await flush();
          const overviewErrorHtml = elements["overview-content"].innerHTML;
          if (!overviewErrorHtml.includes("Error loading overview: no data sources available")) {{
            throw new Error("overview section should show the provider load failure once");
          }}
          if (overviewErrorHtml.includes("Error loading overview: Error loading overview")) {{
            throw new Error("overview section should not duplicate the provider error prefix");
          }}
        }}

        main().catch((err) => {{
          console.error(err);
          process.exit(1);
        }});
        """
    )
    subprocess.run([_node_executable_or_skip(), "-e", script], check=True, cwd=ROOT)
