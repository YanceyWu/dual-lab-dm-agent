var SectionAllocation = {
  _data: null,
  _view: "employee",

  load: function () {
    var el = document.getElementById("allocation-content");
    el.innerHTML = C.skeleton();
    DataService.allocations()
      .then(function (raw) {
        SectionAllocation._data = SectionAllocation._pivot(raw);
        SectionAllocation._render(el);
      })
      .catch(function (err) {
        el.innerHTML = C.alertStrip("X", "Error: " + err.message, "red");
      });
  },

  _pivot: function (raw) {
    var monthSet = {};
    var empMap = {},
      projMap = {};
    raw.forEach(function (r) {
      var mkey = r.year + "-" + ("0" + r.month).slice(-2);
      monthSet[mkey] = 1;

      // Employee map — accumulate totals + per-project breakdown
      if (!empMap[r.employee_id]) {
        empMap[r.employee_id] = {
          id: r.employee_id,
          name: r.name,
          wd_id: r.wd_id,
          is_contractor: r.wd_id && r.wd_id.toString().slice(-1) === "C",
          months: {},
          projects: {},
        };
      }
      empMap[r.employee_id].months[mkey] =
        (empMap[r.employee_id].months[mkey] || 0) + r.allocation;
      if (!empMap[r.employee_id].projects[r.project_id]) {
        empMap[r.employee_id].projects[r.project_id] = {
          name: r.project_name,
          months: {},
        };
      }
      empMap[r.employee_id].projects[r.project_id].months[mkey] =
        (empMap[r.employee_id].projects[r.project_id].months[mkey] || 0) +
        r.allocation;

      // Project map — accumulate totals + per-employee breakdown
      if (!projMap[r.project_id]) {
        projMap[r.project_id] = {
          id: r.project_id,
          name: r.project_name,
          months: {},
          employees: {},
        };
      }
      projMap[r.project_id].months[mkey] =
        (projMap[r.project_id].months[mkey] || 0) + r.allocation;
      if (!projMap[r.project_id].employees[r.employee_id]) {
        projMap[r.project_id].employees[r.employee_id] = {
          name: r.name,
          is_contractor: r.wd_id && r.wd_id.toString().slice(-1) === "C",
          months: {},
        };
      }
      projMap[r.project_id].employees[r.employee_id].months[mkey] =
        (projMap[r.project_id].employees[r.employee_id].months[mkey] || 0) +
        r.allocation;
    });

    var months = Object.keys(monthSet).sort();
    var by_employee = Object.values(empMap).sort(function (a, b) {
      return a.name.localeCompare(b.name);
    });
    var by_project = Object.values(projMap)
      .map(function (p) {
        return {
          id: p.id,
          name: p.name,
          member_count: Object.keys(p.employees).length,
          months: p.months,
          employees: p.employees,
        };
      })
      .sort(function (a, b) {
        return a.name.localeCompare(b.name);
      });
    return { months: months, by_employee: by_employee, by_project: by_project };
  },

  _render: function (el) {
    var d = SectionAllocation._data;
    if (!d) return;
    el = el || document.getElementById("allocation-content");
    var v = SectionAllocation._view;

    // Segmented control with icons
    var filterBar =
      '<div class="filter-bar alloc-filter-bar">' +
      '<div class="alloc-view-group">' +
      '<button class="alloc-view-btn' +
      (v === "employee" ? " active" : "") +
      '" onclick="SectionAllocation._switch(\'employee\')">' +
      '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' +
      '<circle cx="6" cy="5" r="2.5"/><path d="M1 14v-1a5 5 0 0110 0v1"/>' +
      '<circle cx="13" cy="5" r="2"/><path d="M15 14v-.5a3.5 3.5 0 00-3.5-3.5"/>' +
      "</svg>" +
      "By Employee" +
      "</button>" +
      '<button class="alloc-view-btn' +
      (v === "project" ? " active" : "") +
      '" onclick="SectionAllocation._switch(\'project\')">' +
      '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M2 4a2 2 0 012-2h3l1.5 1.5H12a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V4z"/>' +
      "</svg>" +
      "By Project" +
      "</button>" +
      "</div>" +
      '<input class="search-input" id="alloc-q" placeholder="Filter by name..." oninput="SectionAllocation._filter()">' +
      '<span class="filter-hint">Click row to expand ↕</span>' +
      '<span class="filter-count" id="alloc-count"></span>' +
      "</div>";

    var content =
      v === "employee"
        ? SectionAllocation._empTable(d.by_employee, d.months)
        : SectionAllocation._projTable(d.by_project, d.months);
    el.innerHTML = filterBar + content;
    SectionAllocation._filter();
  },

  _switch: function (view) {
    SectionAllocation._view = view;
    SectionAllocation._render();
  },

  _filter: function () {
    var qEl = document.getElementById("alloc-q");
    var q = qEl ? qEl.value.toLowerCase() : "";
    var rows = document.querySelectorAll("#allocation-content .alloc-row");
    var shown = 0;
    rows.forEach(function (r) {
      var vis = !q || (r.dataset.name || "").toLowerCase().indexOf(q) >= 0;
      r.style.display = vis ? "" : "none";
      // Keep detail row in sync: only show if parent visible AND currently open
      var next = r.nextElementSibling;
      if (next && next.classList.contains("alloc-detail-row")) {
        next.style.display = vis && next.dataset.open === "1" ? "" : "none";
      }
      if (vis) shown++;
    });
    var cnt = document.getElementById("alloc-count");
    if (cnt) cnt.textContent = shown + " rows";
  },

  _toggle: function (key) {
    var detailRow = document.querySelector(
      '.alloc-detail-row[data-key="' + key + '"]',
    );
    var toggleBtn = document.querySelector(
      '.alloc-row[data-key="' + key + '"] .alloc-toggle-btn',
    );
    if (!detailRow) return;
    var isOpen = detailRow.dataset.open === "1";
    detailRow.dataset.open = isOpen ? "0" : "1";
    detailRow.style.display = isOpen ? "none" : "";
    if (toggleBtn) toggleBtn.classList.toggle("expanded", !isOpen);
  },

  _monthHeader: function (months) {
    return (
      '<tr><th class="alloc-name-col">Name</th>' +
      months
        .map(function (m) {
          return '<th class="alloc-month-col">' + fmtMonth(m) + "</th>";
        })
        .join("") +
      '<th class="alloc-month-col">Avg</th></tr>'
    );
  },

  // Employee cell: 100% = good (green), <100% = warning (amber), >100% = error (red)
  _empCell: function (val, sub) {
    var tdCls = sub ? " alloc-sub-cell" : "";
    if (!val) return '<td class="alloc-cell' + tdCls + ' empty">—</td>';
    var v = Math.round(val * 100);
    var cls =
      v > 100 ? "e-over" : v === 100 ? "e-ok" : v >= 80 ? "e-warn" : "e-low";
    return (
      '<td class="alloc-cell' +
      tdCls +
      " " +
      cls +
      '"><span class="alloc-pill">' +
      v +
      "%</span></td>"
    );
  },

  // Project cell: show FTE sum, no red for >1 FTE (multiple people is normal)
  _projCell: function (val, sub) {
    var tdCls = sub ? " alloc-sub-cell" : "";
    if (!val) return '<td class="alloc-cell' + tdCls + ' empty">—</td>';
    var fte = val.toFixed(1);
    var cls = val === 0 ? "empty" : "p-ok";
    return (
      '<td class="alloc-cell' +
      tdCls +
      " " +
      cls +
      '"><span class="alloc-pill">' +
      fte +
      "</span></td>"
    );
  },

  // Build a collapsible detail row containing a mini-table of breakdowns
  // mode: 'employee' (sub rows are projects) | 'project' (sub rows are people)
  _detailRow: function (key, colSpan, headerLabel, subRows, months, mode) {
    var subHtml = subRows
      .map(function (sr) {
        var cells =
          mode === "project"
            ? months
                .map(function (m) {
                  return SectionAllocation._empCell(sr.months[m], true);
                })
                .join("")
            : months
                .map(function (m) {
                  return SectionAllocation._projCell(sr.months[m], true);
                })
                .join("");
        return (
          '<tr class="alloc-sub-row">' +
          '<td class="alloc-sub-name-col">' +
          '<div class="alloc-sub-item-name">' +
          esc(sr.name) +
          "</div>" +
          (sr.type
            ? '<div class="alloc-sub-item-type">' + sr.type + "</div>"
            : "") +
          "</td>" +
          cells +
          '<td class="alloc-cell alloc-sub-cell empty"></td>' +
          "</tr>"
        );
      })
      .join("");

    return (
      '<tr class="alloc-detail-row" data-key="' +
      key +
      '" data-open="0" style="display:none">' +
      '<td colspan="' +
      colSpan +
      '" class="alloc-detail-cell">' +
      '<div class="alloc-detail-inner">' +
      '<table class="alloc-sub-table">' +
      '<thead><tr class="alloc-sub-header">' +
      '<th class="alloc-sub-name-col">' +
      headerLabel +
      "</th>" +
      months
        .map(function (m) {
          return '<th class="alloc-month-col">' + fmtMonth(m) + "</th>";
        })
        .join("") +
      '<th class="alloc-month-col"></th>' +
      "</tr></thead>" +
      "<tbody>" +
      subHtml +
      "</tbody>" +
      "</table>" +
      "</div>" +
      "</td>" +
      "</tr>"
    );
  },

  _empTable: function (rows, months) {
    var thead = "<thead>" + SectionAllocation._monthHeader(months) + "</thead>";
    var unassigned = 0;
    var colSpan = months.length + 2;
    var legend =
      '<div class="alloc-legend-bar">' +
      '<span class="alloc-legend-item e-ok">100% — On target</span>' +
      '<span class="alloc-legend-item e-warn">&lt;100% or 0% — Under-allocated / Gap</span>' +
      '<span class="alloc-legend-item e-over">&gt;100% — Overloaded</span>' +
      "</div>";

    // Build issue summary: employees with ANY month != 100%
    var issues = { over: [], under: [] };
    rows.forEach(function (r) {
      var hasAny = months.some(function (m) {
        return (r.months[m] || 0) > 0;
      });
      if (!hasAny) return;
      months.forEach(function (m) {
        var v = Math.round((r.months[m] || 0) * 100);
        if (v > 100 && issues.over.indexOf(r.name) < 0)
          issues.over.push(r.name);
        if (v < 100 && issues.under.indexOf(r.name) < 0)
          issues.under.push(r.name);
      });
    });

    var issueBanner = "";
    if (issues.over.length || issues.under.length) {
      var parts = [];
      if (issues.over.length)
        parts.push(
          '<span class="issue-group e-over"><strong>' +
            issues.over.length +
            " overloaded</strong>: " +
            issues.over.join(", ") +
            "</span>",
        );
      if (issues.under.length)
        parts.push(
          '<span class="issue-group e-warn"><strong>' +
            issues.under.length +
            " under-allocated / gap</strong>: " +
            issues.under.join(", ") +
            "</span>",
        );
      issueBanner =
        '<div class="alloc-issue-banner">' +
        '<div class="alloc-issue-title">' +
        '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 1L1 14h14L8 1z"/><line x1="8" y1="7" x2="8" y2="10"/><circle cx="8" cy="12.5" r="0.5" fill="currentColor"/></svg>' +
        "Allocation Issues — " +
        (issues.over.length + issues.under.length) +
        " staff need attention" +
        "</div>" +
        '<div class="alloc-issue-groups">' +
        parts.join("") +
        "</div>" +
        "</div>";
    }

    var tbody = rows
      .map(function (r) {
        var key = "emp-" + r.id;
        var cells = months
          .map(function (m) {
            return SectionAllocation._empCell(r.months[m]);
          })
          .join("");
        var vals = months.map(function (m) {
          return r.months[m] || 0;
        });
        var avg = vals.length
          ? Math.round(
              (vals.reduce(function (a, v) {
                return a + v;
              }, 0) /
                vals.length) *
                100,
            )
          : 0;
        var hasAny = vals.some(function (v) {
          return v > 0;
        });
        if (!hasAny) unassigned++;
        var avgCls =
          avg > 100
            ? "e-over"
            : avg === 100
              ? "e-ok"
              : avg > 0
                ? "e-warn"
                : "e-low";

        // Flag row if any month is not exactly 100% (including 0% gaps)
        var hasIssue = hasAny && months.some(function (m) {
          var v = Math.round((r.months[m] || 0) * 100);
          return v !== 100;
        });

        var projects = Object.values(r.projects).sort(function (a, b) {
          return a.name.localeCompare(b.name);
        });
        var hasProjects = projects.length > 0;

        var mainRow =
          '<tr class="alloc-row alloc-parent-row' +
          (hasIssue ? " has-issue" : "") +
          '" data-name="' +
          esc(r.name) +
          '" data-key="' +
          key +
          '" onclick="SectionAllocation._toggle(\'' +
          key +
          "')\">" +
          '<td class="alloc-name-col">' +
          '<button class="alloc-toggle-btn' +
          (hasProjects ? "" : " disabled") +
          '" title="' +
          (hasProjects ? "Show project breakdown" : "No project data") +
          '"' +
          (hasProjects ? "" : " disabled") +
          '><svg width="8" height="8" viewBox="0 0 8 8"><path d="M2 1l4 3-4 3" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></button>' +
          '<div class="alloc-name-info">' +
          '<div class="alloc-name">' +
          esc(r.name) +
          "</div>" +
          '<div class="alloc-type-badge ' +
          (r.is_contractor ? "stfte" : "ltfte") +
          '">' +
          (r.is_contractor ? "STFTE" : "LTFTE") +
          "</div>" +
          "</div>" +
          "</td>" +
          cells +
          '<td class="alloc-cell alloc-total ' +
          avgCls +
          '"><span class="alloc-pill">' +
          avg +
          "%</span></td>" +
          "</tr>";

        var detailRow = hasProjects
          ? SectionAllocation._detailRow(
              key,
              colSpan,
              "Project",
              projects,
              months,
              "employee",
            )
          : "";

        return mainRow + detailRow;
      })
      .join("");

    var summary =
      unassigned > 0
        ? C.alertStrip(
            "!",
            unassigned + " employee(s) have no allocations recorded",
            "amber",
          )
        : "";
    return (
      legend +
      issueBanner +
      summary +
      '<div class="table-wrap alloc-table-wrap"><table>' +
      thead +
      "<tbody>" +
      tbody +
      "</tbody></table></div>"
    );
  },

  _projTable: function (rows, months) {
    var thead = "<thead>" + SectionAllocation._monthHeader(months) + "</thead>";
    var empty = 0;
    var colSpan = months.length + 2;
    var legend =
      '<div class="alloc-legend-bar">' +
      '<span class="alloc-legend-item p-ok">FTE count per month (multiple staff per project is normal)</span>' +
      "</div>";
    var tbody = rows
      .map(function (r) {
        var key = "proj-" + r.id;
        var cells = months
          .map(function (m) {
            return SectionAllocation._projCell(r.months[m]);
          })
          .join("");
        var vals = months.map(function (m) {
          return r.months[m] || 0;
        });
        var avg = vals.length
          ? (
              vals.reduce(function (a, v) {
                return a + v;
              }, 0) / vals.length
            ).toFixed(1)
          : "0.0";
        var hasAny = vals.some(function (v) {
          return v > 0;
        });
        if (!hasAny) empty++;

        var employees = Object.values(r.employees)
          .map(function (e) {
            return {
              name: e.name,
              type: e.is_contractor ? "STFTE" : "LTFTE",
              months: e.months,
            };
          })
          .sort(function (a, b) {
            return a.name.localeCompare(b.name);
          });
        var hasMembers = employees.length > 0;

        var mainRow =
          '<tr class="alloc-row alloc-parent-row" data-name="' +
          esc(r.name) +
          '" data-key="' +
          key +
          '" onclick="SectionAllocation._toggle(\'' +
          key +
          "')\">" +
          '<td class="alloc-name-col">' +
          '<button class="alloc-toggle-btn' +
          (hasMembers ? "" : " disabled") +
          '" title="' +
          (hasMembers ? "Show team members" : "No member data") +
          '"' +
          (hasMembers ? "" : " disabled") +
          '><svg width="8" height="8" viewBox="0 0 8 8"><path d="M2 1l4 3-4 3" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></button>' +
          '<div class="alloc-name-info">' +
          '<div class="alloc-name">' +
          esc(r.name) +
          "</div>" +
          '<div class="alloc-sub">' +
          r.member_count +
          " staff</div>" +
          "</div>" +
          "</td>" +
          cells +
          '<td class="alloc-cell alloc-total p-total"><span class="alloc-pill">' +
          avg +
          " FTE</span></td>" +
          "</tr>";

        var detailRow = hasMembers
          ? SectionAllocation._detailRow(
              key,
              colSpan,
              "Team Member",
              employees,
              months,
              "project",
            )
          : "";

        return mainRow + detailRow;
      })
      .join("");

    var summary =
      empty > 0
        ? C.alertStrip(
            "!",
            empty + " project(s) have no monthly allocations recorded",
            "amber",
          )
        : "";
    return (
      summary +
      '<div class="table-wrap alloc-table-wrap"><table>' +
      thead +
      "<tbody>" +
      tbody +
      "</tbody></table></div>"
    );
  },
};
