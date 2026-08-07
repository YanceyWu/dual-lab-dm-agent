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
        }}

        main().catch((err) => {{
          console.error(err);
          process.exit(1);
        }});
        """
    )
    subprocess.run([_node_executable_or_skip(), "-e", script], check=True, cwd=ROOT)
