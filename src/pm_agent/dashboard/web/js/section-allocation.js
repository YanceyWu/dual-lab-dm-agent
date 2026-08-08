var SectionAllocation = {
  _data: null,
  _view: "employee",

  load: function () {
    var el = document.getElementById("allocation-content");
    el.innerHTML = C.skeleton();
    MonthlyPlanPageProvider.load()
      .then(function (model) {
        SectionAllocation._data = model;
        SectionAllocation._render(el);
      })
      .catch(function (err) {
        el.innerHTML = C.alertStrip(
          "X",
          err.message || "Error loading monthly plan",
          "red",
        );
      });
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
        ? SectionAllocation._empTable(d.employeeView, d.months)
        : SectionAllocation._projTable(d.projectView, d.months);
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

  _cell: function (cell) {
    var tdCls = cell.isSub ? " alloc-sub-cell" : "";
    return (
      '<td class="alloc-cell' +
      tdCls +
      " " +
      (cell.className || "empty") +
      '"><span class="alloc-pill">' +
      esc(cell.text || "—") +
      "</span></td>"
    );
  },

  _legend: function (items) {
    return (
      '<div class="alloc-legend-bar">' +
      (items || [])
        .map(function (item) {
          return '<span class="alloc-legend-item ' + item.className + '">' + item.text + "</span>";
        })
        .join("") +
      "</div>"
    );
  },

  _detailRow: function (key, colSpan, headerLabel, subRows, months) {
    var subHtml = subRows
      .map(function (sr) {
        var cells = (sr.cells || [])
          .map(function (cell) {
            return SectionAllocation._cell(cell);
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

  _empTable: function (view, months) {
    var thead = "<thead>" + SectionAllocation._monthHeader(months) + "</thead>";
    var colSpan = months.length + 2;
    var legend = SectionAllocation._legend(view.legend);
    var issues = view.issueSummary || { over: [], under: [] };
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

    var tbody = (view.rows || [])
      .map(function (r) {
        var cells = (r.cells || [])
          .map(function (cell) {
            return SectionAllocation._cell(cell);
          })
          .join("");
        var hasProjects = (r.detailRows || []).length > 0;

        var mainRow =
          '<tr class="alloc-row alloc-parent-row' +
          (r.hasIssue ? " has-issue" : "") +
          '" data-name="' +
          esc(r.name) +
          '" data-key="' +
          r.key +
          '" onclick="SectionAllocation._toggle(\'' +
          r.key +
          "')\">" +
          '<td class="alloc-name-col">' +
          '<button class="alloc-toggle-btn' +
          (hasProjects ? "" : " disabled") +
          '" title="' +
          esc(r.detailToggleTitle || (hasProjects ? "Show project breakdown" : "No project data")) +
          '"' +
          (hasProjects ? "" : " disabled") +
          '><svg width="8" height="8" viewBox="0 0 8 8"><path d="M2 1l4 3-4 3" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></button>' +
          '<div class="alloc-name-info">' +
          '<div class="alloc-name">' +
          esc(r.name) +
          "</div>" +
          '<div class="alloc-type-badge ' +
          r.typeClass +
          '">' +
          r.typeLabel +
          "</div>" +
          "</div>" +
          "</td>" +
          cells +
          '<td class="alloc-cell alloc-total ' +
          r.totalCell.className +
          '"><span class="alloc-pill">' +
          r.totalCell.text +
          "</span></td>" +
          "</tr>";

        var detailRow = hasProjects
          ? SectionAllocation._detailRow(
              r.key,
              colSpan,
              r.detailHeader,
              r.detailRows,
              months,
            )
          : "";

        return mainRow + detailRow;
      })
      .join("");

    var summary =
      view.zeroAllocationCount > 0
        ? C.alertStrip(
            "!",
            view.zeroAllocationCount + " employee(s) only have 0% allocation rows in this view",
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

  _projTable: function (view, months) {
    var thead = "<thead>" + SectionAllocation._monthHeader(months) + "</thead>";
    var colSpan = months.length + 2;
    var legend = SectionAllocation._legend(view.legend);
    var tbody = (view.rows || [])
      .map(function (r) {
        var cells = (r.cells || [])
          .map(function (cell) {
            return SectionAllocation._cell(cell);
          })
          .join("");
        var hasMembers = (r.detailRows || []).length > 0;

        var mainRow =
          '<tr class="alloc-row alloc-parent-row" data-name="' +
          esc(r.name) +
          '" data-key="' +
          r.key +
          '" onclick="SectionAllocation._toggle(\'' +
          r.key +
          "')\">" +
          '<td class="alloc-name-col">' +
          '<button class="alloc-toggle-btn' +
          (hasMembers ? "" : " disabled") +
          '" title="' +
          esc(r.detailToggleTitle || (hasMembers ? "Show team members" : "No member data")) +
          '"' +
          (hasMembers ? "" : " disabled") +
          '><svg width="8" height="8" viewBox="0 0 8 8"><path d="M2 1l4 3-4 3" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></button>' +
          '<div class="alloc-name-info">' +
          '<div class="alloc-name">' +
          esc(r.name) +
          "</div>" +
          '<div class="alloc-sub">' +
          r.subLabel +
          "</div>" +
          "</div>" +
          "</td>" +
          cells +
          '<td class="alloc-cell alloc-total ' + r.totalCell.className + '"><span class="alloc-pill">' +
          r.totalCell.text +
          "</span></td>" +
          "</tr>";

        var detailRow = hasMembers
          ? SectionAllocation._detailRow(
              r.key,
              colSpan,
              r.detailHeader,
              r.detailRows,
              months,
            )
          : "";

        return mainRow + detailRow;
      })
      .join("");

    var summary =
      view.zeroAllocationCount > 0
        ? C.alertStrip(
            "!",
            view.zeroAllocationCount + " project(s) only have 0 FTE rows in this view",
            "amber",
          )
        : "";
    return (
      legend +
      summary +
      '<div class="table-wrap alloc-table-wrap"><table>' +
      thead +
      "<tbody>" +
      tbody +
      "</tbody></table></div>"
    );
  },
};
