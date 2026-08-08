var SectionHealth = {
  _data: null,
  _meta: null,
  _summary: null,
  _syncState: {
    busy: false,
    message: "",
    tone: "blue",
  },

  load: function () {
    var el = document.getElementById("health-content");
    el.innerHTML = C.skeleton();
    ProjectHealthPageProvider.load()
      .then(function (model) {
        SectionHealth._data = model.projects;
        SectionHealth._meta = model.meta;
        SectionHealth._summary = model.summary;
        SectionHealth._render(el);
      })
      .catch(function (err) {
        el.innerHTML = C.alertStrip(
          "X",
          err.message || "Error loading project health",
          "red",
        );
      });
  },

  _render: function (el) {
    el = el || document.getElementById("health-content");
    var analyzed = SectionHealth._data || [];
    var summary = SectionHealth._summary || { kpis: {}, alerts: [] };

    var kpis =
      '<div class="kpi-row">' +
      C.kpiCard("Projects Listed", summary.kpis.projectsListed.value, summary.kpis.projectsListed.subtitle, summary.kpis.projectsListed.variant) +
      C.kpiCard("Needs Attention", summary.kpis.needsAttention.value, summary.kpis.needsAttention.subtitle, summary.kpis.needsAttention.variant) +
      C.kpiCard("Need Sync", summary.kpis.needSync.value, summary.kpis.needSync.subtitle, summary.kpis.needSync.variant) +
      C.kpiCard("Signal Gaps", summary.kpis.signalGaps.value, summary.kpis.signalGaps.subtitle, summary.kpis.signalGaps.variant) +
      C.kpiCard("No Board Link", summary.kpis.noBoardLink.value, summary.kpis.noBoardLink.subtitle, summary.kpis.noBoardLink.variant) +
      "</div>";

    var actionBar =
      '<div class="health-toolbar">' +
      '<div class="health-toolbar-actions">' +
      '<button class="health-sync-btn" ' +
      (SectionHealth._syncState.busy ? "disabled" : "") +
      ' onclick="SectionHealth.syncStale()">' +
      (SectionHealth._syncState.busy ? "Syncing..." : "Sync stale JIRA health") +
      "</button>" +
      '<div class="health-toolbar-note">Runs release sync + health sync for all stale JIRA boards in the current DB.</div>' +
      "</div>" +
      "</div>";

    var alerts = "";
    alerts += (summary.alerts || [])
      .map(function (alert) {
        return C.alertStrip(alert.icon, alert.message, alert.tone);
      })
      .join("");
    if (SectionHealth._syncState.message) {
      var icon = SectionHealth._syncState.tone === "red" ? "X" : SectionHealth._syncState.tone === "green" ? "OK" : "i";
      alerts += C.alertStrip(icon, SectionHealth._syncState.message, SectionHealth._syncState.tone);
    }
    if (SectionHealth._meta && SectionHealth._meta.issues && SectionHealth._meta.issues.length) {
      alerts += SectionHealth._meta.issues
        .map(function (issue) {
          return C.alertStrip("i", esc(issue.message), "blue");
        })
        .join("");
    }

    var sorted = analyzed.slice().sort(function (a, b) {
      return SectionHealth._sortWeight(a) - SectionHealth._sortWeight(b);
    });

    var colSpan = 6;
    var tbody = sorted
      .map(function (item) {
        var key = "health-" + (item.id || "").replace(/[^a-z0-9]/gi, "_");
        var hasDetail =
          item.confluenceSummary ||
          item.confluenceRisks ||
          item.jiraRiskMessages.length ||
          item.healthSummaryText;

        var mainRow =
          '<tr class="health-row' +
          (hasDetail ? " health-expandable" : "") +
          '"' +
          (hasDetail
            ? " onclick=\"SectionHealth._toggle('" +
              key +
              '\')" title="Click to see detail"'
            : "") +
          ' data-key="' +
          key +
          '">' +
          '<td class="health-name-col">' +
          (hasDetail
            ? '<button class="health-toggle-btn" id="htbtn-' +
              key +
              '"><svg width="8" height="8" viewBox="0 0 8 8"><path d="M2 1l4 3-4 3" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></button>'
            : '<span class="health-toggle-spacer"></span>') +
          '<div class="health-name-info">' +
          '<div class="health-proj-name">' +
          esc(item.name || "") +
          "</div>" +
          '<div class="health-proj-phase">' +
          esc(item.boardName || "No linked board") +
          (item.phase ? " · " + esc(item.phase) : "") +
          "</div>" +
          "</div>" +
          "</td>" +
          '<td class="health-pm-col">' +
          SectionHealth._pmStatusBadge(item.pmStatusKey) +
          '<div class="health-sub-badges">' +
          (item.confRag ? C.ragBadge(item.confRag) : "") +
          (item.jiraGrade ? C.jiraGrade(item.jiraGrade, item.jiraOverallScore) : "") +
          "</div>" +
          "</td>" +
          '<td class="health-jira-col">' +
          SectionHealth._renderJiraSummary(item) +
          "</td>" +
          '<td class="health-signals-col">' +
          SectionHealth._renderSignals(item) +
          "</td>" +
          '<td class="health-freshness-col">' +
          SectionHealth._renderFreshness(item) +
          "</td>" +
          '<td class="health-action-col">' +
          '<div class="health-action-text">' + esc(item.nextAction) + "</div>" +
          (item.hasBoard
            ? '<div class="health-action-link"><button class="health-inline-btn" onclick="event.stopPropagation(); SectionHealth.syncBoard(\'' +
              esc(item.boardId) +
              "')\">" +
              "Sync this board" +
              "</button></div>"
            : "") +
          (item.boardUrl
            ? '<div class="health-action-link"><a class="health-board-link" href="' +
              item.boardUrl +
              '" target="_blank">Open JIRA ↗</a></div>'
            : "") +
          "</td>" +
          "</tr>";

        var detailRow = "";
        if (hasDetail) {
          detailRow =
            '<tr class="health-detail-row" data-key="' +
            key +
            '" data-open="0" style="display:none">' +
            '<td colspan="' +
            colSpan +
            '" class="health-detail-cell">' +
            '<div class="health-detail-inner">' +
            '<div class="health-section">' +
            '<div class="health-section-title">PM Interpretation</div>' +
            '<div class="health-section-body">' +
            '<ul class="health-bullets">' +
            item.reasons
              .map(function (reason) {
                return "<li>" + esc(reason) + "</li>";
              })
              .join("") +
            "</ul>" +
            "</div>" +
            "</div>" +
            (item.confluenceSummary
              ? '<div class="health-section">' +
                '<div class="health-section-title">Confluence Summary</div>' +
                '<div class="health-section-body">' +
                SectionHealth._formatText(item.confluenceSummary) +
                "</div>" +
                "</div>"
              : "") +
            (item.confluenceRisks
              ? '<div class="health-section health-section-risk">' +
                '<div class="health-section-title">Confluence Risks</div>' +
                '<div class="health-section-body">' +
                SectionHealth._formatText(item.confluenceRisks) +
                "</div>" +
                "</div>"
              : "") +
            (item.jiraRiskMessages.length
              ? '<div class="health-section health-section-risk">' +
                '<div class="health-section-title">JIRA Risk Signals</div>' +
                '<div class="health-section-body">' +
                SectionHealth._formatText(item.jiraRiskMessages.map(function (msg) { return "- " + msg; }).join("\\n")) +
                "</div>" +
                "</div>"
              : "") +
            (item.healthSummaryText
              ? '<div class="health-section">' +
                '<div class="health-section-title">Snapshot Summary</div>' +
                '<div class="health-section-body">' +
                SectionHealth._formatText(item.healthSummaryText) +
                "</div>" +
                "</div>"
              : "") +
            "</div>" +
            "</td>" +
            "</tr>";
        }

        return mainRow + detailRow;
      })
      .join("");

    var thead =
      "<thead><tr>" +
      '<th class="health-name-col">Project</th>' +
      '<th class="health-pm-col">PM View</th>' +
      '<th class="health-jira-col">JIRA / Release</th>' +
      '<th class="health-signals-col">Signals</th>' +
      '<th class="health-freshness-col">Data Confidence</th>' +
      '<th class="health-action-col">Next Action</th>' +
      "</tr></thead>";

    var table =
      '<div class="table-wrap health-table-wrap">' +
      "<table>" +
      thead +
      "<tbody>" +
      tbody +
      "</tbody></table>" +
      "</div>";

    el.innerHTML = actionBar + kpis + alerts + table;
  },

  _toggle: function (key) {
    var row = document.querySelector(
      '.health-detail-row[data-key="' + key + '"]',
    );
    var btn = document.getElementById("htbtn-" + key);
    if (!row) return;
    var isOpen = row.dataset.open === "1";
    row.dataset.open = isOpen ? "0" : "1";
    row.style.display = isOpen ? "none" : "";
    if (btn) btn.classList.toggle("expanded", !isOpen);
  },

  syncBoard: function (boardId) {
    if (!boardId || SectionHealth._syncState.busy) return;
    SectionHealth._syncState = {
      busy: true,
      message: "Syncing JIRA release + health for " + boardId + "...",
      tone: "blue",
    };
    SectionHealth._render();
    ProjectHealthPageProvider.previewBoardSync(boardId)
      .then(function (previewAction) {
        if (!previewAction.requiresConfirmation) {
          return previewAction.autoResult;
        }
        var confirmed = window.confirm(previewAction.confirmationMessage);
        if (!confirmed) throw new Error("Sync cancelled before confirmation.");
        return ProjectHealthPageProvider.confirmSync(
          previewAction,
          "JIRA sync completed for " + boardId + ".",
        );
      })
      .then(function (result) {
        if (!result.refreshed) {
          SectionHealth._syncState = {
            busy: false,
            message: result.message,
            tone: "green",
          };
          SectionHealth._render();
          return;
        }
        SectionHealth._syncState = {
          busy: false,
          message: result.message,
          tone: "green",
        };
        SectionHealth.load();
      })
      .catch(function (err) {
        SectionHealth._syncState = {
          busy: false,
          message: err.message,
          tone: "red",
        };
        SectionHealth._render();
      });
  },

  syncStale: function () {
    if (SectionHealth._syncState.busy) return;
    SectionHealth._syncState = {
      busy: true,
      message: "Syncing stale JIRA boards...",
      tone: "blue",
    };
    SectionHealth._render();
    ProjectHealthPageProvider.previewStaleSync()
      .then(function (previewAction) {
        if (!previewAction.requiresConfirmation) {
          return previewAction.autoResult;
        }
        var confirmed = window.confirm(previewAction.confirmationMessage);
        if (!confirmed) throw new Error("Sync cancelled before confirmation.");
        return ProjectHealthPageProvider.confirmSync(
          previewAction,
          "Stale JIRA sync completed.",
        );
      })
      .then(function (result) {
        if (!result.refreshed) {
          SectionHealth._syncState = {
            busy: false,
            message: result.message,
            tone: "green",
          };
          SectionHealth._render();
          return;
        }
        SectionHealth._syncState = {
          busy: false,
          message: result.message,
          tone: "green",
        };
        SectionHealth.load();
      })
      .catch(function (err) {
        SectionHealth._syncState = {
          busy: false,
          message: err.message,
          tone: "red",
        };
        SectionHealth._render();
      });
  },

  _sortWeight: function (item) {
    var order = {
      escalate: 0,
      investigate: 1,
      recover: 2,
      sync: 3,
      no_board: 4,
      monitor: 5,
    };
    return (order[item.pmStatusKey] || 9) * 100 + (item.jiraAgeDays || 0);
  },

  _pmStatusBadge: function (key) {
    var map = {
      escalate: ["Escalate", "badge-error"],
      investigate: ["Investigate", "badge-info"],
      recover: ["At Risk", "badge-amber"],
      sync: ["Sync Needed", "badge-muted"],
      no_board: ["No Board", "badge-muted"],
      monitor: ["Monitor", "badge-green"],
    };
    var entry = map[key] || ["Unknown", "badge-muted"];
    return C.badge(entry[0], entry[1]);
  },

  _renderJiraSummary: function (item) {
    var summary = item.jiraSummary || {};
    if (!summary.hasSnapshot) {
      return '<span class="health-na">No JIRA health snapshot</span>';
    }

    var lines = [];
    if (summary.versionName || summary.releaseDate) {
      lines.push(
        '<div class="health-metric-main">' +
          esc(summary.versionName || "Unlabeled release") +
          (summary.releaseDate ? '<span class="health-metric-sub"> · ' + esc(summary.releaseDate) + "</span>" : "") +
        "</div>",
      );
    }
    if (summary.sprintName) {
      lines.push('<div class="health-metric-sub">Sprint: ' + esc(summary.sprintName) + "</div>");
    }
    lines.push(
      '<div class="health-metric-sub">SP progress: ' +
        esc(summary.spProgressText || "Unknown") +
        ' · Sprint completion: ' +
        esc(summary.sprintCompletionText || "Unknown") +
        "</div>",
    );
    lines.push(
      '<div class="health-metric-sub">P1/P2 bugs: ' +
        esc(summary.newBugsP1P2Text || "Unknown") +
        " · Total defects: " +
        esc(summary.totalDefectsText || "Unknown") +
        "</div>",
    );
    if (summary.unestimatedText) {
      lines.push(
        '<div class="health-metric-sub">Unestimated: ' +
          esc(summary.unestimatedText) +
          "</div>",
      );
    }
    return lines.join("");
  },

  _renderSignals: function (item) {
    var signalSummary = item.signalSummary || {};
    var parts = [];
    if ((signalSummary.riskMessages || []).length) {
      parts.push(
        signalSummary.riskMessages
          .slice(0, 2)
          .map(function (msg) {
            return '<div class="health-signal-line">' + esc(msg) + "</div>";
          })
          .join(""),
      );
    }
    if (signalSummary.confluenceSummaryAvailable) {
      parts.push(
        '<div class="health-signal-line health-signal-muted">Confluence summary available</div>',
      );
    } else if (signalSummary.confluenceRagWithoutSummary) {
      parts.push(
        '<div class="health-signal-line health-signal-muted">Confluence RAG captured without summary block</div>',
      );
    }
    if (!parts.length) {
      return '<span class="health-na">No explicit signal captured</span>';
    }
    return parts.join("");
  },

  _renderFreshness: function (item) {
    var freshness = item.freshnessSummary || {};
    var lines = [];
    lines.push(
      '<div class="health-fresh-row">JIRA ' +
        SectionHealth._freshnessBadge(freshness.jiraState) +
        "</div>",
    );
    if (freshness.jiraSnapshotDate) {
      lines.push(
        '<div class="health-metric-sub">Snapshot: ' +
          esc(freshness.jiraSnapshotDate) +
          (freshness.jiraAgeDays != null ? " (" + freshness.jiraAgeDays + "d old)" : "") +
          "</div>",
      );
    }
    lines.push(
      '<div class="health-fresh-row">Confluence ' +
        SectionHealth._freshnessBadge(freshness.confluenceState) +
        "</div>",
    );
    if (freshness.confluenceSnapshotDate) {
      lines.push(
        '<div class="health-metric-sub">Snapshot: ' +
          esc(freshness.confluenceSnapshotDate) +
          (freshness.confluenceAgeDays != null ? " (" + freshness.confluenceAgeDays + "d old)" : "") +
          "</div>",
      );
    }
    return lines.join("");
  },

  _freshnessBadge: function (state) {
    var map = {
      fresh: ["Fresh", "badge-green"],
      running: ["Running", "badge-info"],
      partial: ["Partial", "badge-amber"],
      stale: ["Stale", "badge-amber"],
      failed: ["Failed", "badge-error"],
      never_synced: ["Never Synced", "badge-error"],
      snapshot_only: ["Snapshot Only", "badge-info"],
      missing: ["Missing", "badge-muted"],
      inactive: ["Inactive", "badge-muted"],
    };
    var entry = map[state] || ["Unknown", "badge-muted"];
    return C.badge(entry[0], entry[1]);
  },

  _formatText: function (text) {
    if (!text) return "";
    return (
      '<ul class="health-bullets">' +
      text
        .split("\n")
        .filter(function (line) {
          return line.trim();
        })
        .map(function (line) {
          var clean = line
            .replace(/^[-*]\s*/, "")
            .replace(/~~(.+?)~~/g, "<del>$1</del>");
          return (
            "<li>" +
            esc(clean)
              .replace(/&lt;del&gt;/g, "<del>")
              .replace(/&lt;\/del&gt;/g, "</del>") +
            "</li>"
          );
        })
        .join("") +
      "</ul>"
    );
  },
};
