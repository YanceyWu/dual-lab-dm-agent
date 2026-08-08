var TeamPageProvider = {
  _loadBucket: function (employee) {
    if (!(employee.current_state_staffing_state === "known" && employee.load_pct != null)) {
      return "unknown";
    }
    if (employee.load_pct > 100) return "over";
    if (employee.load_pct === 100) return "full";
    return "avail";
  },

  _hirefDisplay: function (employee) {
    var contractState = employee.contract_coverage_freshness_state || "unknown";
    var reviewCountsAvailable = employee.contract_review_counts_available === true;
    if (!employee.is_contractor) {
      return {
        state: "na",
      };
    }
    if (!reviewCountsAvailable) {
      return {
        state: "degraded",
        message: "Contract coverage " + humanizeKey(contractState).toLowerCase(),
        hirefId: employee.current_hiref || "",
        hirefEndDate: employee.hiref_end_date || "",
      };
    }
    if (employee.current_hiref) {
      return {
        state: "linked",
        urgency: employee.hiref_urgency || "unknown",
        hirefId: employee.current_hiref || "",
        hirefEndDate: employee.hiref_end_date || "",
      };
    }
    return {
      state: "missing",
    };
  },

  _loadDisplay: function (employee) {
    if (!(employee.current_state_staffing_state === "known" && employee.load_pct != null)) {
      return {
        state: "unknown",
      };
    }
    return {
      state: "known",
      pct: employee.load_pct,
    };
  },

  _typeDisplay: function (employee) {
    return employee.is_contractor
      ? { label: "STFTE", badgeClass: "badge-coral" }
      : { label: "LTFTE", badgeClass: "badge-blue" };
  },

  _projectAssignments: function (employee) {
    return (employee.projects || []).map(function (project) {
      return {
        name: project.name || "",
        allocationPct: fmtPct(project.allocation),
      };
    });
  },

  _nextAssignmentDisplay: function (employee) {
    if (!employee.next_assignment) return null;
    var nextAssignment = employee.next_assignment;
    return {
      name: nextAssignment.name || "",
      allocationPct: nextAssignment.allocation,
      startMonth: nextAssignment.start_date
        ? fmtMonth(nextAssignment.start_date.substring(0, 7))
        : "",
    };
  },

  load: function () {
    return DataService.employees()
      .then(function (employees) {
        return {
          meta: LegacyPageProviderSupport.meta("team", []),
          rows: (employees || []).map(function (employee) {
            var hirefDisplay = TeamPageProvider._hirefDisplay(employee);
            var loadDisplay = TeamPageProvider._loadDisplay(employee);
            var typeDisplay = TeamPageProvider._typeDisplay(employee);
            return Object.assign({}, employee, {
              searchText: [
                employee.name || "",
                employee.wd_id || "",
                (employee.projects || [])
                  .map(function (project) {
                    return project.name || "";
                  })
                  .join(" "),
              ]
                .join(" ")
                .toLowerCase(),
              loadKnown:
                employee.current_state_staffing_state === "known" &&
                employee.load_pct != null,
              loadBucket: TeamPageProvider._loadBucket(employee),
              loadDisplayState: loadDisplay.state,
              loadDisplayPct: loadDisplay.pct,
              typeLabel: typeDisplay.label,
              typeBadgeClass: typeDisplay.badgeClass,
              projectAssignments: TeamPageProvider._projectAssignments(employee),
              nextAssignmentDisplay: TeamPageProvider._nextAssignmentDisplay(employee),
              hirefDisplayState: hirefDisplay.state,
              hirefDisplayMessage: hirefDisplay.message || "",
              hirefDisplayUrgency: hirefDisplay.urgency || "",
              hirefDisplayId: hirefDisplay.hirefId || "",
              hirefDisplayEndDate: hirefDisplay.hirefEndDate || "",
            });
          }),
        };
      })
      .catch(function (err) {
        throw LegacyPageProviderSupport.error(
          "Error loading team: " + err.message,
          "team",
          true,
        );
      });
  },
};
