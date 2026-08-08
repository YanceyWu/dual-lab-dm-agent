var SectionOverview = {
  _distBar: function (count, color, label, total) {
    var width = total > 0 ? Math.round((count / total) * 160) : 0;
    return '<div class="load-dist-row">'
      + '<div class="load-dist-label">' + label + '</div>'
      + '<div class="load-dist-bar"><div style="height:8px;background:var(--border);border-radius:9999px;overflow:hidden">'
        + '<div style="height:100%;width:' + width + 'px;max-width:160px;background:' + color + ';border-radius:9999px"></div>'
      + '</div></div>'
      + '<div class="load-dist-count">' + count + '</div>'
    + '</div>';
  },

  _badgeClass: function (tone) {
    return "nav-badge"
      + (tone === "green"
        ? " green"
        : tone === "amber"
          ? " amber"
          : tone === "muted"
            ? " muted"
            : "");
  },

  _renderFocusProjects: function (focusProjects) {
    if (focusProjects.state !== "ready") {
      return '<div class="text-muted" style="font-size:13px">Project list unavailable</div>';
    }
    if (!focusProjects.items.length) {
      return '<div class="text-muted" style="font-size:13px">No focus projects set</div>';
    }
    return focusProjects.items
      .map(function (project) {
        return '<div style="padding:8px 0;border-bottom:1px solid var(--border-light);display:flex;align-items:center;gap:10px">'
          + '<div style="width:4px;height:28px;border-radius:2px;background:var(--green);flex-shrink:0"></div>'
          + '<div><div class="td-name">' + project.name + '</div>'
          + '<div style="margin-top:2px">' + C.phaseBadge(project.phase) + ' ' + C.priorityBadge(project.priority_tier) + '</div></div>'
        + '</div>';
      })
      .join("");
  },

  _render: function (model) {
    var projectsBadge = document.getElementById("badge-projects");
    var teamBadge = document.getElementById("badge-team");
    var hirefBadge = document.getElementById("badge-hiref");
    var sidebarTimestamp = document.getElementById("sidebar-ts");
    var loadDistribution = model.loadDistribution;
    var alerts = model.meta.issues
      .map(function (issue) {
        return C.alertStrip("i", esc(issue.message), "blue");
      })
      .join("");

    if (projectsBadge) {
      projectsBadge.textContent = model.badges.projects;
      projectsBadge.className = SectionOverview._badgeClass(model.badges.projectsTone);
    }
    if (teamBadge) {
      teamBadge.textContent = model.badges.team;
      teamBadge.className = SectionOverview._badgeClass(model.badges.teamTone);
    }
    if (hirefBadge) {
      hirefBadge.textContent = model.badges.hiref;
      hirefBadge.className = SectionOverview._badgeClass(model.badges.hirefTone);
    }
    if (sidebarTimestamp) sidebarTimestamp.textContent = model.updatedAtText || "";

    alerts += model.alerts
      .map(function (alert) {
        return C.alertStrip(alert.icon, alert.message, alert.tone);
      })
      .join("");

    document.getElementById("overview-content").innerHTML =
      '<div class="kpi-grid">'
        + C.kpiCard("Total Staff", model.cards.totalStaff.value, model.cards.totalStaff.subtitle)
        + C.kpiCard("Active Projects", model.cards.activeProjects.value, model.cards.activeProjects.subtitle, model.cards.activeProjects.variant)
        + C.kpiCard("Avg Team Load", model.cards.avgLoad.value, model.cards.avgLoad.subtitle, model.cards.avgLoad.variant)
        + C.kpiCard("HIREF Alerts", model.cards.hirefAlerts.value, model.cards.hirefAlerts.subtitle, model.cards.hirefAlerts.variant)
        + C.kpiCard("Free HIREF", model.cards.freeHiref.value, model.cards.freeHiref.subtitle, model.cards.freeHiref.variant)
      + "</div>"
      + (alerts ? '<div class="card mb-4">' + alerts + "</div>" : "")
      + '<div class="two-col">'
        + '<div class="card"><div class="card-title">Focus Projects</div>' + SectionOverview._renderFocusProjects(model.focusProjects) + "</div>"
        + '<div class="card"><div class="card-title">Load Distribution</div>'
          + (loadDistribution.state === "ready"
            ? SectionOverview._distBar(loadDistribution.overloaded, "var(--error)", "Overloaded &gt;100%", loadDistribution.total)
              + SectionOverview._distBar(loadDistribution.full, "var(--amber)", "At Capacity =100%", loadDistribution.total)
              + SectionOverview._distBar(loadDistribution.available, "var(--green)", "Available &lt;100%", loadDistribution.total)
            : '<div class="text-muted" style="font-size:13px">' + esc(loadDistribution.message || "Load distribution unavailable") + "</div>")
        + "</div>"
      + "</div>";
  },

  load: function () {
    var el = document.getElementById("overview-content");
    el.innerHTML = C.skeleton();
    OverviewPageProvider.load()
      .then(function (model) {
        SectionOverview._render(model);
      })
      .catch(function (err) {
        el.innerHTML = C.alertStrip(
          "X",
          err.message || "Error loading overview",
          "red",
        );
      });
  },
};
