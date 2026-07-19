var SectionHealth = {
  _data: null,
  _syncState: {
    busy: false,
    message: "",
    tone: "blue",
  },

  load: function () {
    var el = document.getElementById("health-content");
    el.innerHTML = C.skeleton();
    DataService.projectHealth()
      .then(function (data) {
        SectionHealth._data = data;
        SectionHealth._render(el);
      })
      .catch(function (err) {
        el.innerHTML = C.alertStrip("X", "Error: " + err.message, "red");
      });
  },

  _render: function (el) {
    el = el || document.getElementById("health-content");
    var analyzed = (SectionHealth._data || []).map(SectionHealth._analyzeProject);

    var attentionCount = analyzed.filter(function (item) {
      return item.pmStatusKey === "escalate" || item.pmStatusKey === "recover";
    }).length;
    var syncCount = analyzed.filter(function (item) {
      return item.pmStatusKey === "sync";
    }).length;
    var disagreementCount = analyzed.filter(function (item) {
      return item.hasDisagreement;
    }).length;
    var noBoardCount = analyzed.filter(function (item) {
      return item.pmStatusKey === "no_board";
    }).length;

    var kpis =
      '<div class="kpi-row">' +
      C.kpiCard("Projects Listed", analyzed.length, "active projects or standalone boards", "") +
      C.kpiCard("Needs Attention", attentionCount, "red / yellow health signals", attentionCount > 0 ? "coral" : "") +
      C.kpiCard("Need Sync", syncCount, "missing or stale JIRA health", syncCount > 0 ? "amber" : "") +
      C.kpiCard("Signal Gaps", disagreementCount, "Confluence / JIRA disagreement", disagreementCount > 0 ? "info" : "") +
      C.kpiCard("No Board Link", noBoardCount, "no mapped JIRA health source", noBoardCount > 0 ? "amber" : "") +
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
    if (attentionCount > 0) {
      alerts += C.alertStrip(
        "!",
        "<strong>" + attentionCount + " project(s)</strong> need PM attention based on current health signals.",
        "red",
      );
    }
    if (syncCount > 0) {
      alerts += C.alertStrip(
        "i",
        "<strong>" + syncCount + " project(s)</strong> have stale or missing JIRA health and should be synced before using the score.",
        "amber",
      );
    }
    if (disagreementCount > 0) {
      alerts += C.alertStrip(
        "↔",
        "<strong>" + disagreementCount + " project(s)</strong> show a gap between Confluence and JIRA signals; review before status reporting.",
        "blue",
      );
    }
    if (SectionHealth._syncState.message) {
      var icon = SectionHealth._syncState.tone === "red" ? "X" : SectionHealth._syncState.tone === "green" ? "OK" : "i";
      alerts += C.alertStrip(icon, SectionHealth._syncState.message, SectionHealth._syncState.tone);
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
          item.pmStatusBadge +
          '<div class="health-sub-badges">' +
          (item.confluenceRagBadge || "") +
          (item.jiraGradeBadge || "") +
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

  _analyzeProject: function (project) {
    var p = project || {};
    var health = p.health || null;
    var jira = (health || {}).jira || {};
    var confluence = (health || {}).confluence || {};
    var freshness = (health || {}).freshness || {};
    var jiraFresh = freshness.jira_health || null;
    var confFresh = freshness.confluence_status || null;
    var jiraAgeDays = SectionHealth._ageDays(jira.snapshot_date);
    var confAgeDays = SectionHealth._ageDays(confluence.snapshot_date);
    var jiraRiskItems = SectionHealth._safeJson(jira.risks_json, []);
    var jiraRiskMessages = jiraRiskItems.map(function (risk) {
      return "[" + (risk.type || "signal") + "] " + (risk.msg || "");
    });
    var jiraGrade = jira.overall_grade || "";
    var confRag = confluence.rag_status || "";

    var hasJiraSnapshot = !!jira.snapshot_date;
    var hasConfluenceSnapshot = !!confluence.snapshot_date;
    var hasBoard = !!health;
    var jiraFreshState = jiraFresh ? jiraFresh.freshness_state : hasJiraSnapshot ? "snapshot_only" : "missing";
    var confFreshState = confFresh ? confFresh.freshness_state : hasConfluenceSnapshot ? "snapshot_only" : "missing";
    var jiraNeedsSync =
      jiraFreshState === "failed" ||
      jiraFreshState === "stale" ||
      jiraFreshState === "never_synced" ||
      (!hasJiraSnapshot && hasBoard);
    var noJiraData = !hasJiraSnapshot;
    var noConfluenceData = !hasConfluenceSnapshot;

    var hasDisagreement =
      (confRag === "RED" && jiraGrade === "GREEN") ||
      ((confRag === "GREEN" || confRag === "") && jiraGrade === "RED") ||
      ((confRag === "GREEN" || confRag === "") && jiraGrade === "YELLOW") ||
      ((confRag === "AMBER" || confRag === "YELLOW") && jiraGrade === "GREEN");

    var reasons = [];
    if (!hasBoard) {
      reasons.push("No active JIRA board is linked to this project.");
    }
    if (noJiraData && hasBoard) {
      reasons.push("No JIRA health snapshot is available yet.");
    }
    if (jiraNeedsSync && hasJiraSnapshot) {
      reasons.push(
        "JIRA health snapshot exists but freshness is `" + jiraFreshState + "`.",
      );
    }
    if (jiraAgeDays != null) {
      reasons.push("Latest JIRA snapshot is " + jiraAgeDays + " day(s) old.");
    }
    if (jiraGrade) {
      reasons.push("JIRA overall grade is " + jiraGrade + " (" + Math.round(jira.overall_score || 0) + ").");
    }
    if (confRag) {
      reasons.push("Confluence RAG is " + confRag + ".");
    }
    if (hasDisagreement) {
      reasons.push("Confluence and JIRA signals do not align.");
    }
    if ((jira.new_bugs_p1p2 || 0) > 0) {
      reasons.push("There are " + jira.new_bugs_p1p2 + " new P1/P2 bug(s).");
    }
    if (jira.unestimated_pct != null && jira.unestimated_pct >= 40) {
      reasons.push(Math.round(jira.unestimated_pct) + "% of open issues are unestimated.");
    }
    jiraRiskMessages.forEach(function (msg) {
      reasons.push(msg);
    });
    if (!reasons.length) {
      reasons.push("No major risk signal is currently exposed on this project.");
    }

    var pmStatusKey = "monitor";
    if (!hasBoard) {
      pmStatusKey = "no_board";
    } else if (jiraNeedsSync && noJiraData) {
      pmStatusKey = "sync";
    } else if (jiraGrade === "RED" || confRag === "RED") {
      pmStatusKey = "escalate";
    } else if (hasDisagreement) {
      pmStatusKey = "investigate";
    } else if (
      jiraGrade === "YELLOW" ||
      confRag === "YELLOW" ||
      confRag === "AMBER" ||
      (jira.new_bugs_p1p2 || 0) > 0 ||
      ((jira.sprint_completion_pct || 0) > 0 && jira.sprint_completion_pct < 50) ||
      (jira.unestimated_pct || 0) >= 40
    ) {
      pmStatusKey = "recover";
    } else if (jiraNeedsSync) {
      pmStatusKey = "sync";
    }

    var nextAction = "Monitor in weekly governance.";
    if (pmStatusKey === "no_board") {
      nextAction = "Link a JIRA board to this project before relying on the health view.";
    } else if (pmStatusKey === "sync") {
      nextAction =
        "Refresh JIRA health before making a PM judgment; current health data is missing or stale.";
    } else if (pmStatusKey === "escalate") {
      nextAction =
        "Escalate with the squad lead this week and confirm blockers, defect impact, and recovery actions.";
    } else if (pmStatusKey === "investigate") {
      nextAction =
        "Review why Confluence and JIRA disagree before the next project status update.";
    } else if (pmStatusKey === "recover") {
      nextAction =
        "Review burndown, estimation coverage, and bug trend with the team and confirm a recovery plan.";
    }

    return {
      id: p.id,
      name: p.name,
      phase: p.phase,
      boardId: (health || {}).board_id || "",
      boardName: (health || {}).board_name || "",
      boardUrl: (health || {}).board_url || "",
      jira: jira,
      confluence: confluence,
      jiraFreshState: jiraFreshState,
      confFreshState: confFreshState,
      jiraAgeDays: jiraAgeDays,
      confAgeDays: confAgeDays,
      jiraRiskMessages: jiraRiskMessages,
      reasons: reasons,
      hasDisagreement: hasDisagreement,
      pmStatusKey: pmStatusKey,
      pmStatusBadge: SectionHealth._pmStatusBadge(pmStatusKey),
      jiraGradeBadge: jiraGrade ? C.jiraGrade(jiraGrade, jira.overall_score) : "",
      confluenceRagBadge: confRag ? C.ragBadge(confRag) : "",
      nextAction: nextAction,
      healthSummaryText: jira.summary_text || "",
      confluenceSummary: confluence.summary_text || "",
      confluenceRisks: confluence.risks_text || "",
      hasBoard: hasBoard,
    };
  },

  syncBoard: function (boardId) {
    if (!boardId || SectionHealth._syncState.busy) return;
    SectionHealth._syncState = {
      busy: true,
      message: "Syncing JIRA release + health for " + boardId + "...",
      tone: "blue",
    };
    SectionHealth._render();
    DataService.syncProjectHealth(boardId)
      .then(function (result) {
        SectionHealth._syncState = {
          busy: false,
          message: result.message || ("JIRA sync completed for " + boardId + "."),
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
    DataService.syncStaleProjectHealth()
      .then(function (result) {
        SectionHealth._syncState = {
          busy: false,
          message: result.message || "Stale JIRA sync completed.",
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
    var jira = item.jira || {};
    if (!jira.snapshot_date) {
      return '<span class="health-na">No JIRA health snapshot</span>';
    }

    var lines = [];
    if (jira.version_name || jira.release_date) {
      lines.push(
        '<div class="health-metric-main">' +
          esc(jira.version_name || "Unlabeled release") +
          (jira.release_date ? '<span class="health-metric-sub"> · ' + esc(jira.release_date) + "</span>" : "") +
        "</div>",
      );
    }
    if (jira.sprint_name) {
      lines.push('<div class="health-metric-sub">Sprint: ' + esc(jira.sprint_name) + "</div>");
    }
    lines.push(
      '<div class="health-metric-sub">SP progress: ' +
        Math.round(jira.sp_progress_pct || 0) +
        '% · Sprint completion: ' +
        Math.round(jira.sprint_completion_pct || 0) +
        "%</div>",
    );
    lines.push(
      '<div class="health-metric-sub">P1/P2 bugs: ' +
        (jira.new_bugs_p1p2 || 0) +
        " · Total defects: " +
        (jira.total_defects || 0) +
        "</div>",
    );
    if (jira.unestimated_pct != null) {
      lines.push(
        '<div class="health-metric-sub">Unestimated: ' +
          Math.round(jira.unestimated_pct) +
          "%</div>",
      );
    }
    return lines.join("");
  },

  _renderSignals: function (item) {
    var parts = [];
    if (item.jiraRiskMessages.length) {
      parts.push(
        item.jiraRiskMessages
          .slice(0, 2)
          .map(function (msg) {
            return '<div class="health-signal-line">' + esc(msg) + "</div>";
          })
          .join(""),
      );
    }
    if (item.confluenceSummary) {
      parts.push(
        '<div class="health-signal-line health-signal-muted">Confluence summary available</div>',
      );
    } else if (item.confluence.rag_status) {
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
    var lines = [];
    lines.push(
      '<div class="health-fresh-row">JIRA ' +
        SectionHealth._freshnessBadge(item.jiraFreshState) +
        "</div>",
    );
    if (item.jira.snapshot_date) {
      lines.push(
        '<div class="health-metric-sub">Snapshot: ' +
          esc(item.jira.snapshot_date) +
          (item.jiraAgeDays != null ? " (" + item.jiraAgeDays + "d old)" : "") +
          "</div>",
      );
    }
    lines.push(
      '<div class="health-fresh-row">Confluence ' +
        SectionHealth._freshnessBadge(item.confFreshState) +
        "</div>",
    );
    if (item.confluence.snapshot_date) {
      lines.push(
        '<div class="health-metric-sub">Snapshot: ' +
          esc(item.confluence.snapshot_date) +
          (item.confAgeDays != null ? " (" + item.confAgeDays + "d old)" : "") +
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

  _safeJson: function (value, fallback) {
    try {
      return JSON.parse(value || JSON.stringify(fallback));
    } catch (err) {
      return fallback;
    }
  },

  _ageDays: function (value) {
    if (!value) return null;
    var dateText = value.substring(0, 10);
    var parsed = new Date(dateText + "T00:00:00");
    if (isNaN(parsed.getTime())) return null;
    var now = new Date();
    return Math.floor((now - parsed) / (1000 * 60 * 60 * 24));
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
