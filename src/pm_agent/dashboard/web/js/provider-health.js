var ProjectHealthPageProvider = {
  _normalizeTargets: function (targets) {
    return (targets || []).map(function (target) {
      return {
        boardId: target.board_id || "",
        boardName: target.board_name || target.board_id || "Unknown board",
      };
    });
  },

  _confirmationMessage: function (targets, prefix) {
    var names = (targets || []).map(function (target) {
      return target.boardName;
    });
    return (
      prefix + " " + names.length + " JIRA board(s): " + names.join(", ") +
      "\n\nThis accesses the external network and updates local snapshots. " +
      "It does not modify remote JIRA data."
    );
  },

  _normalizePreview: function (preview, noActionMessage, confirmationPrefix) {
    var normalizedTargets = ProjectHealthPageProvider._normalizeTargets(
      preview.targets,
    );
    if (!preview.requires_confirmation) {
      return {
        requiresConfirmation: false,
        autoResult: {
          message: preview.message || noActionMessage,
          refreshed: false,
        },
        targets: normalizedTargets,
      };
    }
    return {
      requiresConfirmation: true,
      preview: preview,
      targets: normalizedTargets,
      confirmationMessage: ProjectHealthPageProvider._confirmationMessage(
        normalizedTargets,
        confirmationPrefix,
      ),
    };
  },

  load: function () {
    return DataService.projectHealth()
      .then(function (projects) {
        var analyzed = (projects || []).map(ProjectHealthPageProvider._analyzeProject);
        return {
          meta: LegacyPageProviderSupport.meta("health", []),
          projects: analyzed,
          summary: ProjectHealthPageProvider._pageSummary(analyzed),
        };
      })
      .catch(function (err) {
        throw LegacyPageProviderSupport.error(
          "Error loading project health: " + err.message,
          "health",
          true,
        );
      });
  },

  previewBoardSync: function (boardId) {
    return DataService.previewProjectHealthSync(boardId)
      .then(function (preview) {
        return ProjectHealthPageProvider._normalizePreview(
          preview,
          "No sync required for " + boardId + ".",
          "Sync",
        );
      })
      .catch(function (err) {
        throw LegacyPageProviderSupport.error(err.message, "health-sync", true);
      });
  },

  previewStaleSync: function () {
    return DataService.previewStaleProjectHealthSync()
      .then(function (preview) {
        return ProjectHealthPageProvider._normalizePreview(
          preview,
          "No stale JIRA boards require sync.",
          "Sync stale",
        );
      })
      .catch(function (err) {
        throw LegacyPageProviderSupport.error(err.message, "health-sync", true);
      });
  },

  confirmSync: function (previewAction, defaultMessage) {
    return DataService.confirmProjectHealthSync(previewAction.preview)
      .then(function (result) {
        return {
          message: result.message || defaultMessage || "JIRA sync completed.",
          refreshed: true,
        };
      })
      .catch(function (err) {
        throw LegacyPageProviderSupport.error(err.message, "health-sync", true);
      });
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

  _pageSummary: function (projects) {
    var analyzed = projects || [];
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
    return {
      kpis: {
        projectsListed: {
          value: analyzed.length,
          subtitle: "active projects or standalone boards",
          variant: "",
        },
        needsAttention: {
          value: attentionCount,
          subtitle: "red / yellow health signals",
          variant: attentionCount > 0 ? "coral" : "",
        },
        needSync: {
          value: syncCount,
          subtitle: "missing or stale JIRA health",
          variant: syncCount > 0 ? "amber" : "",
        },
        signalGaps: {
          value: disagreementCount,
          subtitle: "Confluence / JIRA disagreement",
          variant: disagreementCount > 0 ? "info" : "",
        },
        noBoardLink: {
          value: noBoardCount,
          subtitle: "no mapped JIRA health source",
          variant: noBoardCount > 0 ? "amber" : "",
        },
      },
      alerts: [
        attentionCount > 0
          ? {
              icon: "!",
              message:
                "<strong>" + attentionCount +
                " project(s)</strong> need PM attention based on current health signals.",
              tone: "red",
            }
          : null,
        syncCount > 0
          ? {
              icon: "i",
              message:
                "<strong>" + syncCount +
                " project(s)</strong> have stale or missing JIRA health and should be synced before using the score.",
              tone: "amber",
            }
          : null,
        disagreementCount > 0
          ? {
              icon: "↔",
              message:
                "<strong>" + disagreementCount +
                " project(s)</strong> show a gap between Confluence and JIRA signals; review before status reporting.",
              tone: "blue",
            }
          : null,
      ].filter(function (alert) {
        return !!alert;
      }),
    };
  },

  _displayPercent: function (value) {
    return value == null ? "Unknown" : Math.round(value) + "%";
  },

  _displayCount: function (value) {
    return value == null ? "Unknown" : String(value);
  },

  _analyzeProject: function (project) {
    var p = project || {};
    var health = p.health || null;
    var jira = (health || {}).jira || {};
    var confluence = (health || {}).confluence || {};
    var freshness = (health || {}).freshness || {};
    var jiraFresh = freshness.jira_health || null;
    var confFresh = freshness.confluence_status || null;
    var jiraAgeDays = ProjectHealthPageProvider._ageDays(jira.snapshot_date);
    var confAgeDays = ProjectHealthPageProvider._ageDays(confluence.snapshot_date);
    var jiraRiskItems = ProjectHealthPageProvider._safeJson(jira.risks_json, []);
    var jiraRiskMessages = jiraRiskItems.map(function (risk) {
      return "[" + (risk.type || "signal") + "] " + (risk.msg || "");
    });
    var jiraGrade = jira.overall_grade || "";
    var confRag = confluence.rag_status || "";
    var hasJiraSnapshot = !!jira.snapshot_date;
    var hasConfluenceSnapshot = !!confluence.snapshot_date;
    var hasBoard = !!health;
    var jiraFreshState = jiraFresh
      ? jiraFresh.freshness_state
      : hasJiraSnapshot
        ? "snapshot_only"
        : "missing";
    var confFreshState = confFresh
      ? confFresh.freshness_state
      : hasConfluenceSnapshot
        ? "snapshot_only"
        : "missing";
    var jiraNeedsSync =
      jiraFreshState === "failed" ||
      jiraFreshState === "stale" ||
      jiraFreshState === "never_synced" ||
      (!hasJiraSnapshot && hasBoard);
    var noJiraData = !hasJiraSnapshot;
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
      reasons.push(
        "JIRA overall grade is " +
          jiraGrade +
          (
            jira.overall_score != null
              ? " (" + Math.round(jira.overall_score) + ")."
              : "."
          ),
      );
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
    jiraRiskMessages.forEach(function (message) {
      reasons.push(message);
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
      jiraFreshState: jiraFreshState,
      confFreshState: confFreshState,
      jiraAgeDays: jiraAgeDays,
      confAgeDays: confAgeDays,
      jiraRiskMessages: jiraRiskMessages,
      reasons: reasons,
      hasDisagreement: hasDisagreement,
      pmStatusKey: pmStatusKey,
      jiraGrade: jiraGrade,
      jiraOverallScore: jira.overall_score,
      confRag: confRag,
      nextAction: nextAction,
      jiraSummary: {
        hasSnapshot: hasJiraSnapshot,
        versionName: jira.version_name || "",
        releaseDate: jira.release_date || "",
        sprintName: jira.sprint_name || "",
        spProgressText: ProjectHealthPageProvider._displayPercent(
          jira.sp_progress_pct,
        ),
        sprintCompletionText: ProjectHealthPageProvider._displayPercent(
          jira.sprint_completion_pct,
        ),
        newBugsP1P2Text: ProjectHealthPageProvider._displayCount(
          jira.new_bugs_p1p2,
        ),
        totalDefectsText: ProjectHealthPageProvider._displayCount(
          jira.total_defects,
        ),
        unestimatedText:
          jira.unestimated_pct == null
            ? ""
            : Math.round(jira.unestimated_pct) + "%",
      },
      signalSummary: {
        riskMessages: jiraRiskMessages,
        confluenceSummaryAvailable: !!confluence.summary_text,
        confluenceRagWithoutSummary: !confluence.summary_text && !!confRag,
      },
      freshnessSummary: {
        jiraState: jiraFreshState,
        jiraSnapshotDate: jira.snapshot_date || "",
        jiraAgeDays: jiraAgeDays,
        confluenceState: confFreshState,
        confluenceSnapshotDate: confluence.snapshot_date || "",
        confluenceAgeDays: confAgeDays,
      },
      healthSummaryText: jira.summary_text || "",
      confluenceSummary: confluence.summary_text || "",
      confluenceRisks: confluence.risks_text || "",
      hasBoard: hasBoard,
    };
  },
};
