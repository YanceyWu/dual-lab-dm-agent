var SectionIntelligence = {
  _capacityState: {
    options: [],
    selectedKey: "",
    employeesById: {},
  },
  _executionState: {
    projects: [],
    selectedProjectId: "",
    selectedLayer: "all",
  },
  _snapshotState: {
    projects: [],
    selectedProjectId: "",
    selectedHealth: "",
  },

  loadAttention: function () {
    var el = document.getElementById("attention-content");
    el.innerHTML = C.skeleton();
    Promise.all([
      SectionIntelligence._settleQuery("management-attention"),
      SectionIntelligence._settleQuery("delivery-attention-center"),
      SectionIntelligence._settleQuery("action-followup"),
    ]).then(function (outcomes) {
      var management = outcomes[0].ok ? outcomes[0].result : null;
      var center = outcomes[1].ok ? outcomes[1].result : null;
      var followup = outcomes[2].ok ? outcomes[2].result : null;
      var kpis = UC.metricGrid([
        {
          label: "Management Attention",
          value: management ? ((management.data.summary || {}).total_attention_count || 0) : "—",
          sub: management ? (((management.data.summary || {}).critical_count || 0) + " critical ranked items") : "Query failed",
          variant: management && ((management.data.summary || {}).critical_count || 0) ? "coral" : "",
        },
        {
          label: "Attention Center",
          value: center ? ((center.data.summary || {}).returned_count || 0) : "—",
          sub: center ? (((center.data.summary || {}).matched_count || 0) + " matched current items") : "Query failed",
          variant: center && ((center.data.summary || {}).returned_count || 0) ? "amber" : "",
        },
        {
          label: "Open Follow-up",
          value: followup ? ((followup.data.summary || {}).follow_up_count || 0) : "—",
          sub: followup ? (((followup.data.summary || {}).overdue_count || 0) + " overdue actions") : "Query failed",
          variant: followup && ((followup.data.summary || {}).overdue_count || 0) ? "coral" : "",
        },
      ]);
      el.innerHTML = kpis
        + '<div class="intelligence-stack">'
        + SectionIntelligence._renderOutcomePanel(
          outcomes[0],
          {
            title: "Management Attention",
            subtitle: "Legacy promoted attention ranking served through the shared read-only contract.",
          },
          function (result) {
            return SectionIntelligence._renderManagementAttention(result);
          }
        )
        + SectionIntelligence._renderOutcomePanel(
          outcomes[1],
          {
            title: "Delivery Attention Center",
            subtitle: "Current Delivery Attention items, coverage, and rule states without changing them.",
          },
          function (result) {
            return SectionIntelligence._renderAttentionCenter(result);
          }
        )
        + SectionIntelligence._renderOutcomePanel(
          outcomes[2],
          {
            title: "Action Follow-up",
            subtitle: "Open follow-up actions from the promoted shared query route.",
          },
          function (result) {
            return SectionIntelligence._renderActionFollowup(result);
          }
        )
        + "</div>";
    });
  },

  loadWeeklyBrief: function () {
    var el = document.getElementById("weekly-brief-content");
    el.innerHTML = C.skeleton();
    DataService.queryUseCase("weekly-dm-brief-v2", {}, { contractVersion: "2.0" })
      .then(function (result) {
        var summary = result.data.summary || {};
        var nextActions = (((result.data.sections || {}).next_actions || {}).items || []).length;
        var topSignals = (((result.data.sections || {}).highest_attention_signals || {}).items || []).length;
        var summaryHtml = UC.metricGrid([
          {
            label: "Projects",
            value: summary.project_count || 0,
            sub: "Included in this brief",
            variant: "blue",
          },
          {
            label: "Overall State",
            value: (summary.overall_state || "unknown").toUpperCase(),
            sub: "Weekly synthesis outcome",
            variant: UC._toneForState(summary.overall_state) === "error" ? "coral" : "amber",
          },
          {
            label: "Attention Signals",
            value: topSignals,
            sub: "Highest-attention entries",
            variant: topSignals ? "amber" : "",
          },
          {
            label: "Next Actions",
            value: nextActions,
            sub: "Returned action recommendations",
            variant: nextActions ? "info" : "",
          },
        ]);
        el.innerHTML = UC.useCasePanel({
          title: "Weekly Brief v2",
          subtitle: "Opt-in promoted weekly synthesis built on the shared use-case contract.",
          result: result,
          summaryHtml: summaryHtml,
          bodyHtml: SectionIntelligence._renderWeeklyBrief(result),
        });
      })
      .catch(function (err) {
        el.innerHTML = UC.failedPanel(
          "Weekly Brief v2",
          "Opt-in promoted weekly synthesis built on the shared use-case contract.",
          err.message
        );
      });
  },

  loadCapacity: function () {
    var el = document.getElementById("capacity-content");
    el.innerHTML = C.skeleton();
    Promise.all([DataService.allocations(), DataService.employees()])
      .then(function (results) {
        var allocations = results[0];
        var employees = results[1];
        var options = SectionIntelligence._buildCapacityOptions(allocations);
        SectionIntelligence._capacityState.options = options;
        SectionIntelligence._capacityState.employeesById = SectionIntelligence._indexBy(
          employees,
          "id"
        );
        if (!SectionIntelligence._capacityState.selectedKey && options.length) {
          SectionIntelligence._capacityState.selectedKey = options[0].key;
        }
        var selected = SectionIntelligence._capacityState.options.filter(function (item) {
          return item.key === SectionIntelligence._capacityState.selectedKey;
        })[0];
        if (!selected) {
          el.innerHTML = SectionIntelligence._renderCapacityFrame(
            UC.emptyState(
              "Capacity defaults unavailable",
              "No plan-version-backed monthly allocation rows were found for the promoted capacity heatmap."
            )
          );
          return;
        }
        return DataService.queryUseCase("resource-capacity-heatmap", {
          year: selected.year,
          month: selected.month,
          plan_version_id: selected.planVersionId,
        }).then(function (result) {
          var rows = result.data.rows || [];
          var overloaded = rows.filter(function (row) {
            return row.overload_state === "red";
          }).length;
          var summaryHtml = UC.metricGrid([
            {
              label: "Members",
              value: rows.length,
              sub: "Returned heatmap rows",
              variant: "blue",
            },
            {
              label: "Overloaded",
              value: overloaded,
              sub: "Capacity state red",
              variant: overloaded ? "coral" : "",
            },
            {
              label: "Available Capacity",
              value: rows.filter(function (row) {
                return Number(row.available_capacity || 0) > 0;
              }).length,
              sub: "Rows with capacity remaining",
              variant: "green",
            },
          ]);
          el.innerHTML = SectionIntelligence._renderCapacityFrame(
            UC.useCasePanel({
              title: "Resource Capacity Heatmap",
              subtitle: "Read-only effective capacity and overload facts for the selected published plan window.",
              result: result,
              summaryHtml: summaryHtml,
              bodyHtml: SectionIntelligence._renderCapacityTable(result),
            })
          );
        });
      })
      .catch(function (err) {
        el.innerHTML = SectionIntelligence._renderCapacityFrame(
          UC.failedPanel(
            "Resource Capacity Heatmap",
            "Read-only effective capacity and overload facts for the selected published plan window.",
            err.message
          )
        );
      });
  },

  setCapacityKey: function (value) {
    SectionIntelligence._capacityState.selectedKey = value;
    SectionIntelligence.loadCapacity();
  },

  loadExecution: function () {
    var el = document.getElementById("execution-content");
    el.innerHTML = C.skeleton();
    DataService.projects()
      .then(function (projects) {
        SectionIntelligence._executionState.projects = projects;
        if (!SectionIntelligence._executionState.selectedProjectId && projects.length) {
          SectionIntelligence._executionState.selectedProjectId = projects[0].id;
        }
        if (!SectionIntelligence._executionState.selectedProjectId) {
          el.innerHTML = SectionIntelligence._renderExecutionFrame(
            UC.emptyState(
              "No projects available",
              "The execution review needs at least one active project in the current dashboard database."
            )
          );
          return;
        }
        var parameters = {
          project_id: SectionIntelligence._executionState.selectedProjectId,
        };
        if (SectionIntelligence._executionState.selectedLayer !== "all") {
          parameters.layer = SectionIntelligence._executionState.selectedLayer;
        }
        return DataService.queryUseCase("delivery-execution-review", parameters).then(function (result) {
          var sprintCount = (result.data.sprint_execution || []).length;
          var releaseCount = (result.data.release_milestone || []).length;
          var summaryHtml = UC.metricGrid([
            {
              label: "Sprint Facts",
              value: sprintCount,
              sub: "Sprint execution observations",
              variant: "blue",
            },
            {
              label: "Release & Milestone Facts",
              value: releaseCount,
              sub: "Release and milestone observations",
              variant: "amber",
            },
            {
              label: "Signals",
              value: (result.signals || []).length,
              sub: "Returned execution signals",
              variant: (result.signals || []).length ? "info" : "",
            },
          ]);
          el.innerHTML = SectionIntelligence._renderExecutionFrame(
            UC.useCasePanel({
              title: "Delivery Execution Review",
              subtitle: "Promoted Sprint Execution and Release or Milestone facts for the selected project.",
              result: result,
              summaryHtml: summaryHtml,
              bodyHtml: SectionIntelligence._renderExecutionTables(result),
            })
          );
        });
      })
      .catch(function (err) {
        el.innerHTML = SectionIntelligence._renderExecutionFrame(
          UC.failedPanel(
            "Delivery Execution Review",
            "Promoted Sprint Execution and Release or Milestone facts for the selected project.",
            err.message
          )
        );
      });
  },

  setExecutionProject: function (projectId) {
    SectionIntelligence._executionState.selectedProjectId = projectId;
    SectionIntelligence.loadExecution();
  },

  setExecutionLayer: function (layer) {
    SectionIntelligence._executionState.selectedLayer = layer;
    SectionIntelligence.loadExecution();
  },

  loadLayeredHealth: function () {
    var el = document.getElementById("layered-health-content");
    el.innerHTML = C.skeleton();
    Promise.all([
      DataService.projects(),
      DataService.queryUseCase("layered-project-health-review"),
    ])
      .then(function (results) {
        var projects = results[0];
        var result = results[1];
        var projectById = SectionIntelligence._indexBy(projects, "id");
        var assessments = result.data.assessments || [];
        var summaryHtml = UC.metricGrid([
          {
            label: "Projects",
            value: assessments.length,
            sub: "Returned layered assessments",
            variant: "blue",
          },
          {
            label: "Red",
            value: assessments.filter(function (item) { return item.state === "red"; }).length,
            sub: "Overall red projects",
            variant: "coral",
          },
          {
            label: "Unknown or N/A",
            value: assessments.filter(function (item) {
              return item.state === "unknown" || item.state === "not_available";
            }).length,
            sub: "Projects with incomplete signals",
            variant: "amber",
          },
        ]);
        el.innerHTML = UC.useCasePanel({
          title: "Layered Project Health Review",
          subtitle: "Promoted seven-dimension assessments alongside the legacy Project Health screen.",
          result: result,
          summaryHtml: summaryHtml,
          bodyHtml: SectionIntelligence._renderLayeredHealth(result, projectById),
        });
      })
      .catch(function (err) {
        el.innerHTML = UC.failedPanel(
          "Layered Project Health Review",
          "Promoted seven-dimension assessments alongside the legacy Project Health screen.",
          err.message
        );
      });
  },

  loadConnectors: function () {
    var el = document.getElementById("connectors-content");
    el.innerHTML = C.skeleton();
    Promise.all([
      SectionIntelligence._settleQuery("connector-status-review"),
      SectionIntelligence._settleQuery("connector-sync-results"),
    ]).then(function (outcomes) {
      var status = outcomes[0].ok ? outcomes[0].result : null;
      var sync = outcomes[1].ok ? outcomes[1].result : null;
      var summary = sync ? (sync.data.summary || {}) : {};
      var kpis = UC.metricGrid([
        {
          label: "Connectors",
          value: status ? ((status.data.connectors || []).length || 0) : "—",
          sub: "Configured connector projections",
          variant: "blue",
        },
        {
          label: "Never Synced",
          value: summary.never_synced_count != null ? summary.never_synced_count : "—",
          sub: "Source sync results",
          variant: summary.never_synced_count ? "amber" : "",
        },
        {
          label: "Successful Sources",
          value: summary.success_count != null ? summary.success_count : "—",
          sub: "Latest recorded sync outcomes",
          variant: summary.success_count ? "green" : "",
        },
      ]);
      el.innerHTML = kpis
        + '<div class="intelligence-stack">'
        + SectionIntelligence._renderOutcomePanel(
          outcomes[0],
          {
            title: "Connector Status Review",
            subtitle: "Offline connector readiness, source counts, and freshness without runtime probing.",
          },
          function (result) {
            return SectionIntelligence._renderConnectorStatus(result);
          }
        )
        + SectionIntelligence._renderOutcomePanel(
          outcomes[1],
          {
            title: "Connector Sync Results",
            subtitle: "Latest normalized sync outcomes with no connector probe or write flow.",
          },
          function (result) {
            return SectionIntelligence._renderConnectorSyncResults(result);
          }
        )
        + "</div>";
    });
  },

  loadSnapshots: function () {
    var el = document.getElementById("snapshots-content");
    el.innerHTML = C.skeleton();
    DataService.projects()
      .then(function (projects) {
        SectionIntelligence._snapshotState.projects = projects;
        var parameters = {};
        if (SectionIntelligence._snapshotState.selectedProjectId) {
          parameters.project_id = SectionIntelligence._snapshotState.selectedProjectId;
        }
        if (SectionIntelligence._snapshotState.selectedHealth) {
          parameters.health = SectionIntelligence._snapshotState.selectedHealth;
        }
        return DataService.queryUseCase("project-snapshot-list", parameters).then(function (result) {
          var snapshots = result.data.snapshots || [];
          var summaryHtml = UC.metricGrid([
            {
              label: "Snapshots",
              value: snapshots.length,
              sub: "Rows matching current filters",
              variant: "blue",
            },
            {
              label: "Projects in Scope",
              value: SectionIntelligence._snapshotState.selectedProjectId ? 1 : projects.length,
              sub: SectionIntelligence._snapshotState.selectedProjectId ? "Filtered project" : "All known dashboard projects",
              variant: "info",
            },
          ]);
          el.innerHTML = SectionIntelligence._renderSnapshotFrame(
            UC.useCasePanel({
              title: "Project Snapshot List",
              subtitle: "Stored snapshots from the promoted read-only contract, filtered without adding new write paths.",
              result: result,
              summaryHtml: summaryHtml,
              bodyHtml: SectionIntelligence._renderSnapshots(result),
            })
          );
        });
      })
      .catch(function (err) {
        el.innerHTML = SectionIntelligence._renderSnapshotFrame(
          UC.failedPanel(
            "Project Snapshot List",
            "Stored snapshots from the promoted read-only contract, filtered without adding new write paths.",
            err.message
          )
        );
      });
  },

  setSnapshotProject: function (projectId) {
    SectionIntelligence._snapshotState.selectedProjectId = projectId;
    SectionIntelligence.loadSnapshots();
  },

  setSnapshotHealth: function (health) {
    SectionIntelligence._snapshotState.selectedHealth = health;
    SectionIntelligence.loadSnapshots();
  },

  _renderOutcomePanel: function (outcome, descriptor, renderBody) {
    if (!outcome.ok) {
      return UC.failedPanel(descriptor.title, descriptor.subtitle, outcome.error.message);
    }
    return UC.useCasePanel({
      title: descriptor.title,
      subtitle: descriptor.subtitle,
      result: outcome.result,
      bodyHtml: renderBody(outcome.result),
    });
  },

  _renderManagementAttention: function (result) {
    return UC.table(
      [
        {
          label: "Severity",
          render: function (item) {
            return UC.stateBadge(item.severity);
          },
        },
        {
          label: "Subject",
          render: function (item) {
            return '<div class="td-name">' + esc(item.subject || item.subject_id || "—") + "</div>"
              + (item.subject_id ? '<div class="td-mono">' + esc(item.subject_id) + "</div>" : "");
          },
        },
        {
          label: "Type",
          render: function (item) {
            return UC.badge(humanizeKey(item.attention_type || "attention"), "navy");
          },
        },
        {
          label: "Reason",
          render: function (item) {
            return '<div class="intelligence-mono-wrap">' + esc(item.reason_code || "—") + "</div>";
          },
        },
      ],
      (result.data.items || []),
      "No management-attention items were returned."
    );
  },

  _renderAttentionCenter: function (result) {
    return UC.table(
      [
        {
          label: "Severity",
          render: function (item) {
            return UC.stateBadge(item.severity);
          },
        },
        {
          label: "Rule",
          render: function (item) {
            return '<div class="td-name">' + esc(item.rule_key || "—") + "</div>"
              + '<div class="td-mono">' + esc(item.rule_version || "—") + "</div>";
          },
        },
        {
          label: "Subject",
          render: function (item) {
            return '<div class="td-name">' + esc(UC.subjectLabel(item.subject)) + "</div>";
          },
        },
        {
          label: "Workflow",
          render: function (item) {
            return '<div class="badge-row">'
              + UC.stateBadge(item.attention_state || "unknown")
              + UC.stateBadge(item.rule_state || "unknown")
              + "</div>";
          },
        },
        {
          label: "Seen",
          render: function (item) {
            return '<div>' + esc(fmtDateTime(item.last_seen_at)) + "</div>"
              + '<div class="td-muted">first ' + esc(fmtDateTime(item.first_seen_at)) + "</div>";
          },
        },
      ],
      (result.data.items || []),
      "No attention-center items were returned."
    );
  },

  _renderActionFollowup: function (result) {
    return UC.table(
      [
        {
          label: "Priority",
          render: function (item) {
            return UC.stateBadge(item.priority || "unknown");
          },
        },
        {
          label: "Action",
          render: function (item) {
            return '<div class="td-name">' + esc(item.title || "—") + "</div>"
              + (item.notes ? '<div class="td-muted">' + esc(item.notes) + "</div>" : "");
          },
        },
        {
          label: "Owner",
          render: function (item) {
            return '<div>' + esc(item.owner_name || item.owner_id || "—") + "</div>"
              + (item.owner_id ? '<div class="td-mono">' + esc(item.owner_id) + "</div>" : "");
          },
        },
        {
          label: "Due",
          render: function (item) {
            return '<div>' + esc(item.due_date || "—") + "</div>"
              + '<div class="td-muted">' + esc((item.follow_up_reasons || []).join(", ") || "no reason code") + "</div>";
          },
        },
      ],
      (result.data.items || []),
      "No follow-up actions were returned."
    );
  },

  _renderWeeklyBrief: function (result) {
    var sections = result.data.sections || {};
    var preferredKeys = {
      overall_health: ["project_id", "state", "assessment_id"],
      changes_since_previous_snapshot: ["identity_key", "change_state"],
      highest_attention_signals: ["severity", "rule_key", "subject"],
      achievements: ["statement", "project_id", "subject"],
      risks_and_dependencies: ["statement", "project_id", "subject"],
      decisions_required: ["statement", "subject", "rationale_codes"],
      resource_concerns: ["statement", "subject", "reason_codes"],
      next_actions: ["statement", "subject", "write_mode"],
      freshness_and_limitations: ["statement", "reason_codes"],
    };
    var cards = Object.keys(sections).map(function (key) {
      var section = sections[key] || {};
      var badges = '<div class="badge-row">'
        + UC.stateBadge(section.availability || "unknown")
        + (section.overall ? UC.stateBadge(section.overall) : "")
        + (section.counts && section.counts.after_limit != null
          ? UC.badge(section.counts.after_limit + " items", "info")
          : "")
        + "</div>";
      var limitationHtml = (section.limitations || []).length
        ? '<div class="intelligence-section-note">' + esc((section.limitations || []).join(" · ")) + "</div>"
        : "";
      var itemHtml = (section.items || []).length
        ? UC.summaryList(
            section.items.slice(0, 4).map(function (item) {
              return '<div class="intelligence-summary-item">' + UC.recordSummary(item, preferredKeys[key]) + "</div>";
            }),
            "No section items were returned."
          )
        : UC.emptyState("No section items", "This section returned no visible rows for the current brief.");
      return UC.sectionCard(humanizeKey(key), badges + limitationHtml + itemHtml);
    }).join("");
    return '<div class="intelligence-section-grid">' + cards + "</div>";
  },

  _renderCapacityFrame: function (panelHtml) {
    var options = SectionIntelligence._capacityState.options || [];
    var selectedKey = SectionIntelligence._capacityState.selectedKey;
    var filter = '<div class="filter-bar">'
      + '<span class="filter-label">Plan window</span>'
      + '<select class="filter-select" onchange="SectionIntelligence.setCapacityKey(this.value)">'
      + options.map(function (option) {
        return '<option value="' + escAttr(option.key) + '"'
          + (option.key === selectedKey ? " selected" : "")
          + ">" + esc(option.label) + "</option>";
      }).join("")
      + "</select>"
      + '<div class="filter-count">Heatmap requires year, month, and plan version.</div>'
      + "</div>";
    return filter + panelHtml;
  },

  _renderCapacityTable: function (result) {
    var employeesById = SectionIntelligence._capacityState.employeesById || {};
    return UC.table(
      [
        {
          label: "Member",
          render: function (row) {
            var employee = employeesById[row.member_id] || {};
            return '<div class="td-name">' + esc(employee.name || row.member_id || "—") + "</div>"
              + '<div class="td-mono">' + esc(row.member_id || "—") + "</div>";
          },
        },
        {
          label: "State",
          render: function (row) {
            return '<div class="badge-row">'
              + UC.stateBadge(row.state || "unknown")
              + UC.stateBadge(row.overload_state || "unknown")
              + "</div>";
          },
        },
        {
          label: "Effective",
          render: function (row) {
            return fmtNumber(row.effective_capacity, 2);
          },
        },
        {
          label: "Planned",
          render: function (row) {
            return fmtNumber(row.planned_project_allocation, 2);
          },
        },
        {
          label: "Committed",
          render: function (row) {
            return fmtNumber(row.total_commitment, 2);
          },
        },
        {
          label: "Available",
          render: function (row) {
            return fmtNumber(row.available_capacity, 2);
          },
        },
      ],
      (result.data.rows || []),
      "No published capacity rows matched the current plan window."
    );
  },

  _renderExecutionFrame: function (panelHtml) {
    var projects = SectionIntelligence._executionState.projects || [];
    var projectOptions = projects.map(function (project) {
      return '<option value="' + escAttr(project.id) + '"'
        + (project.id === SectionIntelligence._executionState.selectedProjectId ? " selected" : "")
        + ">" + esc(project.name || project.id) + "</option>";
    }).join("");
    var layers = [
      { value: "all", label: "All layers" },
      { value: "sprint", label: "Sprint only" },
      { value: "release_milestone", label: "Release or milestone only" },
    ];
    var layerOptions = layers.map(function (layer) {
      return '<option value="' + escAttr(layer.value) + '"'
        + (layer.value === SectionIntelligence._executionState.selectedLayer ? " selected" : "")
        + ">" + esc(layer.label) + "</option>";
    }).join("");
    var filter = '<div class="filter-bar">'
      + '<span class="filter-label">Project</span>'
      + '<select class="filter-select" onchange="SectionIntelligence.setExecutionProject(this.value)">'
      + projectOptions
      + "</select>"
      + '<span class="filter-label">Layer</span>'
      + '<select class="filter-select" onchange="SectionIntelligence.setExecutionLayer(this.value)">'
      + layerOptions
      + "</select>"
      + '<div class="filter-count">Legacy Project Health remains available on its original page.</div>'
      + "</div>";
    return filter + panelHtml;
  },

  _renderExecutionTables: function (result) {
    var limitations = result.data.limitations || [];
    var sprintTable = UC.table(
      [
        {
          label: "Subject",
          render: function (item) {
            return esc(UC.subjectLabel(item.subject));
          },
        },
        {
          label: "Fact",
          render: function (item) {
            return '<div class="intelligence-mono-wrap">' + esc(item.fact_key || "—") + "</div>";
          },
        },
        {
          label: "Value",
          render: function (item) {
            return '<div>' + UC.inlineValue(item.value) + "</div>"
              + '<div class="badge-row">' + UC.stateBadge(item.value_state || "unknown") + UC.stateBadge(item.freshness_state || "unknown") + "</div>";
          },
        },
      ],
      result.data.sprint_execution || [],
      "No sprint execution facts matched the current project and layer."
    );
    var releaseTable = UC.table(
      [
        {
          label: "Subject",
          render: function (item) {
            return esc(UC.subjectLabel(item.subject));
          },
        },
        {
          label: "Fact",
          render: function (item) {
            return '<div class="intelligence-mono-wrap">' + esc(item.fact_key || "—") + "</div>";
          },
        },
        {
          label: "Value",
          render: function (item) {
            return '<div>' + UC.inlineValue(item.value) + "</div>"
              + '<div class="badge-row">' + UC.stateBadge(item.value_state || "unknown") + UC.stateBadge(item.freshness_state || "unknown") + "</div>";
          },
        },
      ],
      result.data.release_milestone || [],
      "No release or milestone facts matched the current project and layer."
    );
    var limitationHtml = limitations.length
      ? '<div class="intelligence-section-note">' + esc(limitations.join(" · ")) + "</div>"
      : "";
    return '<div class="intelligence-stack">'
      + limitationHtml
      + UC.sectionCard("Sprint Execution", sprintTable)
      + UC.sectionCard("Release & Milestone", releaseTable)
      + "</div>";
  },

  _renderLayeredHealth: function (result, projectById) {
    return UC.table(
      [
        {
          label: "Project",
          render: function (item) {
            var project = projectById[item.project_id] || {};
            return '<div class="td-name">' + esc(project.name || item.project_id || "—") + "</div>"
              + '<div class="td-mono">' + esc(item.project_id || "—") + "</div>";
          },
        },
        {
          label: "Overall",
          render: function (item) {
            return UC.stateBadge(item.state || "unknown");
          },
        },
        {
          label: "Dimensions",
          render: function (item) {
            return '<div class="badge-row">' + Object.keys(item.dimensions || {}).map(function (key) {
              return UC.badge(humanizeKey(key) + ": " + (item.dimensions[key] || "unknown"), UC._toneForState(item.dimensions[key]));
            }).join("") + "</div>";
          },
        },
        {
          label: "Guard Outcomes",
          render: function (item) {
            if (!item.guard_outcomes || !item.guard_outcomes.length) {
              return '<span class="text-muted">No guard outcomes</span>';
            }
            return item.guard_outcomes.map(function (guard) {
              return '<div class="intelligence-summary-item-line"><strong>' + esc(humanizeKey(guard.dimension || "dimension")) + ":</strong> "
                + esc(guard.reason_code || guard.guard_id || "—") + "</div>";
            }).join("");
          },
        },
      ],
      (result.data.assessments || []),
      "No layered project-health assessments were returned."
    );
  },

  _renderConnectorStatus: function (result) {
    return UC.table(
      [
        {
          label: "Connector",
          render: function (item) {
            return '<div class="td-name">' + esc(item.display_name || item.connector || "—") + "</div>"
              + '<div class="td-mono">' + esc(item.connector || "—") + "</div>";
          },
        },
        {
          label: "State",
          render: function (item) {
            return '<div class="badge-row">'
              + UC.stateBadge(item.enabled ? "enabled" : "disabled", { label: item.enabled ? "Enabled" : "Disabled", tone: item.enabled ? "green" : "muted" })
              + UC.stateBadge(item.freshness_state || "unknown")
              + "</div>";
          },
        },
        {
          label: "Sources",
          render: function (item) {
            return '<div>' + esc(String(item.active_sources || 0)) + " active</div>"
              + '<div class="td-muted">' + esc(String(item.stale_sources || 0)) + " stale</div>";
          },
        },
        {
          label: "Runtime Probe",
          render: function (item) {
            return '<div>' + esc(item.runtime_probe_state || "not_performed") + "</div>"
              + '<div class="td-muted">' + esc(item.latest_run_at || "—") + "</div>";
          },
        },
      ],
      (result.data.connectors || []),
      "No connector-status rows were returned."
    );
  },

  _renderConnectorSyncResults: function (result) {
    return UC.table(
      [
        {
          label: "Source",
          render: function (item) {
            return '<div class="td-name">' + esc(item.source_id || "—") + "</div>"
              + '<div class="td-mono">' + esc(item.connector || "—") + "</div>";
          },
        },
        {
          label: "Outcome",
          render: function (item) {
            return '<div class="badge-row">'
              + UC.stateBadge(item.outcome || "unknown")
              + UC.stateBadge(item.freshness_state || "unknown")
              + "</div>";
          },
        },
        {
          label: "Rows",
          render: function (item) {
            return '<div>' + esc(String(item.rows_changed || 0)) + " changed</div>"
              + '<div class="td-muted">' + esc(String(item.rows_observed || 0)) + " observed</div>";
          },
        },
        {
          label: "Retry",
          render: function (item) {
            return item.retry_recommended
              ? UC.badge("Retry recommended", "amber")
              : UC.badge("No retry", "green");
          },
        },
      ],
      (result.data.sync_results || []),
      "No connector sync-result rows were returned."
    );
  },

  _renderSnapshotFrame: function (panelHtml) {
    var projects = SectionIntelligence._snapshotState.projects || [];
    var projectOptions = ['<option value="">All projects</option>'].concat(
      projects.map(function (project) {
        return '<option value="' + escAttr(project.id) + '"'
          + (project.id === SectionIntelligence._snapshotState.selectedProjectId ? " selected" : "")
          + ">" + esc(project.name || project.id) + "</option>";
      })
    ).join("");
    var healthOptions = [
      { value: "", label: "All health states" },
      { value: "green", label: "Green" },
      { value: "amber", label: "Amber" },
      { value: "red", label: "Red" },
      { value: "unknown", label: "Unknown" },
    ].map(function (option) {
      return '<option value="' + escAttr(option.value) + '"'
        + (option.value === SectionIntelligence._snapshotState.selectedHealth ? " selected" : "")
        + ">" + esc(option.label) + "</option>";
    }).join("");
    var filter = '<div class="filter-bar">'
      + '<span class="filter-label">Project</span>'
      + '<select class="filter-select" onchange="SectionIntelligence.setSnapshotProject(this.value)">'
      + projectOptions
      + "</select>"
      + '<span class="filter-label">Health</span>'
      + '<select class="filter-select" onchange="SectionIntelligence.setSnapshotHealth(this.value)">'
      + healthOptions
      + "</select>"
      + '<div class="filter-count">This page stays read-only; use existing snapshot capture routes when a write is required.</div>'
      + "</div>";
    return filter + panelHtml;
  },

  _renderSnapshots: function (result) {
    var snapshots = result.data.snapshots || [];
    if (!snapshots.length) {
      return UC.emptyState(
        "No stored snapshots matched",
        "The shared snapshot query returned no rows for the current filters. Existing snapshot capture flows remain unchanged."
      );
    }
    var projectById = SectionIntelligence._indexBy(
      SectionIntelligence._snapshotState.projects || [],
      "id"
    );
    return UC.table(
      [
        {
          label: "Snapshot",
          render: function (item) {
            var project = projectById[item.project_id] || {};
            return '<div class="td-name">' + esc(item.title || item.id || "—") + "</div>"
              + '<div class="td-muted">' + esc(project.name || item.project_id || "—") + "</div>";
          },
        },
        {
          label: "Date",
          render: function (item) {
            return esc(item.snapshot_date || "—");
          },
        },
        {
          label: "Kind",
          render: function (item) {
            return '<div class="badge-row">'
              + UC.badge(humanizeKey(item.artifact_kind || "unknown"), "navy")
              + UC.stateBadge(item.artifact_state || "unknown")
              + "</div>";
          },
        },
        {
          label: "Health",
          render: function (item) {
            return UC.stateBadge(item.health || "unknown");
          },
        },
      ],
      snapshots,
      "No snapshot rows matched the current filters."
    );
  },

  _buildCapacityOptions: function (allocations) {
    var seen = {};
    var options = [];
    (allocations || []).forEach(function (row) {
      if (!row.plan_version_id) return;
      var key = [row.year, row.month, row.plan_version_id].join(":");
      if (seen[key]) return;
      seen[key] = true;
      options.push({
        key: key,
        year: row.year,
        month: row.month,
        planVersionId: row.plan_version_id,
        label: fmtMonth(row.year + "-" + String(row.month).padStart(2, "0")) + " · " + row.plan_version_id,
      });
    });
    return options.sort(function (a, b) {
      if (a.year !== b.year) return b.year - a.year;
      if (a.month !== b.month) return b.month - a.month;
      return a.planVersionId < b.planVersionId ? 1 : -1;
    });
  },

  _indexBy: function (items, key) {
    var index = {};
    (items || []).forEach(function (item) {
      if (item && item[key]) index[item[key]] = item;
    });
    return index;
  },

  _settleQuery: function (useCaseId, parameters, options) {
    return DataService.queryUseCase(useCaseId, parameters || {}, options || {})
      .then(function (result) {
        return { ok: true, result: result };
      })
      .catch(function (error) {
        return { ok: false, error: error };
      });
  },
};
