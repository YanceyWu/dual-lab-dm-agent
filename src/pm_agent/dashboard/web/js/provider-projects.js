var ProjectsPageProvider = {
  _healthDisplayContract: function (health) {
    var normalized = health || {};
    var confluence = normalized.confluence || {};
    var jira = normalized.jira || {};
    return {
      confluenceRag: confluence.rag_status || "",
      jiraGrade: jira.overall_grade || "",
      jiraScore: jira.overall_score,
      sprintProgressPct: jira.sp_progress_pct,
      snapshotDate: confluence.snapshot_date || "",
    };
  },

  _teamDisplayContract: function (project) {
    var staffingState = project.current_state_staffing_state || "unknown";
    var freshnessState = project.current_state_staffing_freshness_state || "unknown";
    var teamReady = project.team_size != null;
    var members = teamReady
      ? (project.members || []).map(function (member) {
          return {
            name: member.name || "",
            wdId: member.wd_id || "",
            allocation: member.allocation,
            isPlanned: member.assign_status === "planned",
          };
        })
      : [];
    var staffingSummaryText = teamReady
      ? project.team_size + " staff assigned"
      : staffingState !== "known"
        ? "Current-state staffing " + staffingState
        : "Current-state staffing " + humanizeKey(freshnessState).toLowerCase();
    return {
      memberRows: members,
      memberTableMessage: teamReady ? "No staff assigned" : staffingSummaryText,
      staffingSummaryText: staffingSummaryText,
    };
  },

  load: function () {
    return Promise.allSettled([DataService.projects(), DataService.projectHealth()])
      .then(function (results) {
        if (!LegacyPageProviderSupport.isFulfilled(results[0])) {
          throw LegacyPageProviderSupport.error(
            "Error loading projects: " + (results[0].reason && results[0].reason.message
              ? results[0].reason.message
              : "project list unavailable"),
            "projects",
            true,
          );
        }

        var issues = [];
        var healthMap = {};
        var projects = results[0].value || [];
        var healthList = LegacyPageProviderSupport.valueOf(results[1]) || [];

        if (!LegacyPageProviderSupport.isFulfilled(results[1])) {
          issues.push(
            LegacyPageProviderSupport.issueFromRejection(
              "project health",
              results[1].reason,
            ),
          );
        } else {
          healthList.forEach(function (item) {
            healthMap[item.id] = item.health;
          });
        }

        return {
          meta: LegacyPageProviderSupport.meta("projects", issues),
          projects: projects.map(function (project) {
            var normalized = Object.assign(
              {},
              project,
              ProjectsPageProvider._teamDisplayContract(project),
            );
            normalized.healthDisplay = ProjectsPageProvider._healthDisplayContract(
              healthMap[project.id] || null,
            );
            return normalized;
          }),
        };
      })
      .catch(function (err) {
        throw LegacyPageProviderSupport.error(
          err.message || "Error loading projects",
          err.source || "projects",
          err.retryable,
        );
      });
  },
};
