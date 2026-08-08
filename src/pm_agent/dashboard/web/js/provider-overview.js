var OverviewPageProvider = {
  _freshnessSubtitle: function (state, prefix) {
    var normalized = state || "unknown";
    return prefix + " " + humanizeKey(normalized).toLowerCase();
  },

  _isHirefAlert: function (row) {
    return !!row.current_hiref_missing || (
      !row.next_hiref &&
      ["expired", "critical", "high", "medium"].indexOf(row.urgency) >= 0
    );
  },

  load: function () {
    return Promise.allSettled([
      DataService.summary(),
      DataService.projects(),
      DataService.employees(),
      DataService.hiref(),
    ])
      .then(function (results) {
        var summary = LegacyPageProviderSupport.valueOf(results[0]);
        var projects = LegacyPageProviderSupport.valueOf(results[1]);
        var employees = LegacyPageProviderSupport.valueOf(results[2]);
        var hiref = LegacyPageProviderSupport.valueOf(results[3]);
        var issues = [];

        if (!LegacyPageProviderSupport.isFulfilled(results[0])) {
          issues.push(
            LegacyPageProviderSupport.issueFromRejection("summary", results[0].reason),
          );
        }
        if (!LegacyPageProviderSupport.isFulfilled(results[1])) {
          issues.push(
            LegacyPageProviderSupport.issueFromRejection("projects", results[1].reason),
          );
        }
        if (!LegacyPageProviderSupport.isFulfilled(results[2])) {
          issues.push(
            LegacyPageProviderSupport.issueFromRejection("employees", results[2].reason),
          );
        }
        if (!LegacyPageProviderSupport.isFulfilled(results[3])) {
          issues.push(
            LegacyPageProviderSupport.issueFromRejection("hiref", results[3].reason),
          );
        }

        if (!summary && !projects && !employees && !hiref) {
          throw LegacyPageProviderSupport.error(
            "Error loading overview: no data sources available",
            "overview",
            true,
          );
        }

        var expiringStaff = (hiref && hiref.expiring_staff) || [];
        var derivedHirefAlertCount = expiringStaff.filter(function (item) {
          return (
            OverviewPageProvider._isHirefAlert(item) &&
            (
              item.current_hiref_missing ||
              (
                typeof item.days_until_expiry === "number" &&
                item.days_until_expiry <= 60
              )
            )
          );
        }).length;
        var focusProjects = ((projects || []).filter(function (project) {
          return !!project.is_focus;
        }));
        var loadKnown = function (employee) {
          return employee.current_state_staffing_state === "known" && employee.load_pct != null;
        };
        var allKnownLoad =
          !!employees &&
          employees.length > 0 &&
          employees.every(loadKnown);
        var staffingFreshnessState =
          summary && summary.current_state_staffing_freshness_state
            ? summary.current_state_staffing_freshness_state
            : "unknown";
        var hasKnownLoad = !!employees && employees.some(loadKnown);
        var derivedStaffingState =
          !employees || employees.length === 0
            ? "unknown"
            : allKnownLoad
              ? "known"
              : hasKnownLoad
                ? "partial"
                : "unknown";
        var staffingCoverageState =
          summary && summary.current_state_staffing_state
            ? summary.current_state_staffing_state
            : derivedStaffingState;
        var staffingStateSubtitle =
          staffingCoverageState !== "known"
            ? "Current-state staffing " + staffingCoverageState
            : OverviewPageProvider._freshnessSubtitle(
                staffingFreshnessState,
                "Current-state staffing",
              );
        var renderableLoadState =
          staffingCoverageState === "known" &&
          (staffingFreshnessState === "fresh" || staffingFreshnessState === "stale");
        var derivedOverloadCount = employees
          ? employees.filter(function (employee) {
              return loadKnown(employee) && employee.load_pct > 100;
            }).length
          : 0;
        var derivedFullCount = employees
          ? employees.filter(function (employee) {
              return loadKnown(employee) && employee.load_pct === 100;
            }).length
          : 0;
        var derivedAvailableCount = employees
          ? employees.filter(function (employee) {
              return loadKnown(employee) && employee.load_pct < 100;
            }).length
          : 0;
        var loadDistribution =
          employees && (
            (summary && renderableLoadState) ||
            (!summary && allKnownLoad)
          )
          ? {
              state: "ready",
              total: employees.length,
              overloaded: derivedOverloadCount,
              full: derivedFullCount,
              available: derivedAvailableCount,
            }
          : {
              state: "unavailable",
              message: employees
                ? staffingStateSubtitle
                : LegacyPageProviderSupport.unavailableMessage("employees"),
              total: 0,
              overloaded: 0,
              full: 0,
              available: 0,
            };
        var employeeTotals = employees
          ? {
              ltfte: employees.filter(function (employee) {
                return !employee.is_contractor;
              }).length,
              stfte: employees.filter(function (employee) {
                return !!employee.is_contractor;
              }).length,
            }
          : null;
        var derivedAvgLoad =
          allKnownLoad
            ? Math.round(
                employees.reduce(function (total, employee) {
                  return total + employee.load_pct;
                }, 0) / employees.length,
              )
            : null;
        var summaryHirefAlerts =
          summary && summary.hiref_alerts_60d != null ? summary.hiref_alerts_60d : null;
        var summaryFreeHiref =
          summary && summary.free_hiref_slots != null ? summary.free_hiref_slots : null;
        var hirefReviewCountsAvailable =
            !!hiref && hiref.review_counts_available === true;
        var hirefCoverageSubtitle = hiref
            ? OverviewPageProvider._freshnessSubtitle(
                hiref.contract_coverage_freshness_state,
                "Contract coverage",
              )
            : LegacyPageProviderSupport.unavailableMessage("hiref");
        var badgeHirefCount = summary
            ? summaryHirefAlerts
            : hirefReviewCountsAvailable
              ? derivedHirefAlertCount
              : null;
        var badgeFreeHiref =
            summaryFreeHiref != null
            ? summaryFreeHiref
            : !summary && hiref && hiref.free_count != null
              ? hiref.free_count
              : null;
        var overloadAlertCount =
          loadDistribution.state === "ready" ? loadDistribution.overloaded : null;

        return {
          meta: LegacyPageProviderSupport.meta("overview", issues),
          badges: {
            projects: projects ? String(projects.length) : "—",
            projectsTone: projects ? "green" : "muted",
            team: employees ? String(employees.length) : "—",
            teamTone: employees ? "green" : "muted",
            hiref:
              badgeHirefCount == null
                ? "—"
                : badgeHirefCount > 0
                  ? String(badgeHirefCount)
                  : "OK",
            hirefTone:
              badgeHirefCount == null
                ? "muted"
                : badgeHirefCount > 0
                  ? "default"
                  : "green",
          },
          updatedAtText:
            summary && summary.updated_at
              ? "Updated " + summary.updated_at.substring(11, 16)
              : "",
          cards: {
            totalStaff: {
              value:
                summary && summary.total_staff != null
                  ? summary.total_staff
                  : employees
                    ? employees.length
                    : "Unknown",
              subtitle:
                summary
                  ? displayValue(summary.ltfte, "—") +
                    " LTFTE / " +
                    displayValue(summary.stfte, "—") +
                    " STFTE"
                  : employeeTotals
                    ? employeeTotals.ltfte + " LTFTE / " + employeeTotals.stfte + " STFTE"
                    : LegacyPageProviderSupport.unavailableMessage("summary"),
            },
            activeProjects: {
              value:
                summary && summary.active_projects != null
                  ? summary.active_projects
                  : projects
                    ? projects.length
                    : "Unknown",
              subtitle:
                summary && summary.focus_projects != null
                  ? summary.focus_projects + " focus project(s)"
                  : projects
                    ? focusProjects.length + " focus project(s)"
                    : LegacyPageProviderSupport.unavailableMessage("summary"),
              variant: "blue",
            },
            avgLoad: {
              value:
                summary && summary.avg_load != null
                  ? summary.avg_load + "%"
                  : derivedAvgLoad != null
                    ? derivedAvgLoad + "%"
                    : "Unknown",
              subtitle:
                summary && summary.overloaded != null
                  ? summary.overloaded + " staff overloaded"
                  : derivedAvgLoad != null
                    ? derivedOverloadCount + " staff overloaded"
                    : employees
                      ? staffingStateSubtitle
                      : LegacyPageProviderSupport.unavailableMessage("summary"),
              variant:
                (
                  (summary && summary.overloaded > 0) ||
                  (!summary && overloadAlertCount > 0)
                )
                  ? "coral"
                  : "",
            },
            hirefAlerts: {
              value:
                summary && summary.hiref_alerts_60d != null
                  ? summary.hiref_alerts_60d
                  : !summary && hirefReviewCountsAvailable
                    ? derivedHirefAlertCount
                    : "Unknown",
              subtitle:
                summary && summary.hiref_alerts_60d != null
                  ? "expiring within 60 days"
                  : !summary && hirefReviewCountsAvailable
                    ? "expiring within 60 days"
                  : !summary && hiref
                    ? hirefCoverageSubtitle
                  : summary
                    ? OverviewPageProvider._freshnessSubtitle(
                        summary.contract_coverage_freshness_state,
                        "Contract coverage",
                      )
                    : LegacyPageProviderSupport.unavailableMessage("summary"),
              variant:
                badgeHirefCount != null && badgeHirefCount > 0
                  ? "amber"
                  : "",
            },
            freeHiref: {
              value:
                summary && summary.free_hiref_slots != null
                  ? summary.free_hiref_slots
                  : !summary && hiref && hiref.free_count != null
                    ? hiref.free_count
                  : "Unknown",
              subtitle:
                summary && summary.free_hiref_slots != null
                  ? "slots available"
                  : !summary && hiref && hiref.free_count != null
                    ? "slots available"
                  : !summary && hiref
                    ? hirefCoverageSubtitle
                  : summary
                    ? OverviewPageProvider._freshnessSubtitle(
                        summary.contract_coverage_freshness_state,
                        "Contract coverage",
                      )
                    : LegacyPageProviderSupport.unavailableMessage("summary"),
              variant: badgeFreeHiref != null ? "info" : "",
            },
          },
          alerts: [
            badgeHirefCount != null && badgeHirefCount > 0
              ? {
                  icon: "!",
                  message:
                    "<strong>" +
                    badgeHirefCount +
                    " contractor(s)</strong> have HIREF expiring within 60 days",
                  tone: "red",
                }
              : null,
            overloadAlertCount != null && overloadAlertCount > 0
              ? {
                  icon: "!",
                  message:
                    "<strong>" +
                    overloadAlertCount +
                    " staff</strong> exceeding 100% -- review",
                  tone: "amber",
                }
              : null,
            badgeFreeHiref != null && badgeFreeHiref > 0
              ? {
                  icon: "i",
                  message:
                    "<strong>" + badgeFreeHiref + " free HIREF slots</strong> available",
                  tone: "blue",
                }
              : null,
          ].filter(function (alert) {
            return !!alert;
          }),
          focusProjects: {
            state: projects ? "ready" : "unavailable",
            items: focusProjects,
          },
          loadDistribution: loadDistribution,
        };
      })
      .catch(function (err) {
        throw LegacyPageProviderSupport.error(
          err.message || "Error loading overview",
          err.source || "overview",
          err.retryable,
        );
      });
  },
};
