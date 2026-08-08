var MonthlyPlanPageProvider = {
  _employeeIssueSummary: function (rows, months) {
    var over = [];
    var under = [];
    (rows || []).forEach(function (row) {
      var hasAny = months.some(function (month) {
        return (row.months[month] || 0) > 0;
      });
      if (!hasAny) return;
      months.forEach(function (month) {
        var value = Math.round((row.months[month] || 0) * 100);
        if (value > 100 && over.indexOf(row.name) < 0) over.push(row.name);
        if (value < 100 && under.indexOf(row.name) < 0) under.push(row.name);
      });
    });
    return {
      over: over,
      under: under,
    };
  },

  _zeroAllocationEmployeeCount: function (rows, months) {
    return (rows || []).filter(function (row) {
      return !months.some(function (month) {
        return (row.months[month] || 0) > 0;
      });
    }).length;
  },

  _zeroAllocationProjectCount: function (rows, months) {
    return (rows || []).filter(function (row) {
      return !months.some(function (month) {
        return (row.months[month] || 0) > 0;
      });
    }).length;
  },

  _empCellContract: function (val, sub) {
    if (!val) return { text: "—", className: "empty", isSub: !!sub };
    var v = Math.round(val * 100);
    var cls =
      v > 100 ? "e-over" : v === 100 ? "e-ok" : v >= 80 ? "e-warn" : "e-low";
    return {
      text: String(v) + "%",
      className: cls,
      isSub: !!sub,
    };
  },

  _projCellContract: function (val, sub) {
    if (!val) return { text: "—", className: "empty", isSub: !!sub };
    return {
      text: val.toFixed(1),
      className: val === 0 ? "empty" : "p-ok",
      isSub: !!sub,
    };
  },

  _buildEmployeeView: function (rows, months) {
    var issues = MonthlyPlanPageProvider._employeeIssueSummary(rows, months);
    return {
      legend: [
        { className: "e-ok", text: "100% — On target" },
        { className: "e-warn", text: "<100% or 0% — Under-allocated / Gap" },
        { className: "e-over", text: ">100% — Overloaded" },
      ],
      issueSummary: issues,
      zeroAllocationCount: MonthlyPlanPageProvider._zeroAllocationEmployeeCount(
        rows,
        months,
      ),
      rows: (rows || []).map(function (row) {
        var key = "emp-" + row.id;
        var cells = months.map(function (month) {
          return MonthlyPlanPageProvider._empCellContract(row.months[month], false);
        });
        var vals = months.map(function (month) {
          return row.months[month] || 0;
        });
        var avg = vals.length
          ? Math.round(
              (vals.reduce(function (total, value) {
                return total + value;
              }, 0) /
                vals.length) *
                100,
            )
          : 0;
        var avgClass =
          avg > 100
            ? "e-over"
            : avg === 100
              ? "e-ok"
              : avg > 0
                ? "e-warn"
                : "e-low";
        var detailRows = Object.values(row.projects)
          .sort(function (left, right) {
            return left.name.localeCompare(right.name);
          })
          .map(function (project) {
            return {
              name: project.name,
              type: "",
              cells: months.map(function (month) {
                return MonthlyPlanPageProvider._projCellContract(
                  project.months[month],
                  true,
                );
              }),
            };
          });
        var hasAny = vals.some(function (value) {
          return value > 0;
        });
        return {
          key: key,
          name: row.name,
          typeLabel: row.is_contractor ? "STFTE" : "LTFTE",
          typeClass: row.is_contractor ? "stfte" : "ltfte",
          cells: cells,
          totalCell: {
            text: String(avg) + "%",
            className: avgClass,
          },
          hasIssue:
            hasAny &&
            months.some(function (month) {
              return Math.round((row.months[month] || 0) * 100) !== 100;
            }),
          detailHeader: "Project",
          detailRows: detailRows,
          detailToggleTitle: detailRows.length
            ? "Show project breakdown"
            : "No project data",
        };
      }),
    };
  },

  _buildProjectView: function (rows, months) {
    return {
      legend: [
        {
          className: "p-ok",
          text: "FTE count per month (multiple staff per project is normal)",
        },
      ],
      zeroAllocationCount: MonthlyPlanPageProvider._zeroAllocationProjectCount(
        rows,
        months,
      ),
      rows: (rows || []).map(function (row) {
        var key = "proj-" + row.id;
        var vals = months.map(function (month) {
          return row.months[month] || 0;
        });
        var avg = vals.length
          ? (
              vals.reduce(function (total, value) {
                return total + value;
              }, 0) / vals.length
            ).toFixed(1)
          : "0.0";
        var detailRows = Object.values(row.employees)
          .map(function (employee) {
            return {
              name: employee.name,
              type: employee.is_contractor ? "STFTE" : "LTFTE",
              cells: months.map(function (month) {
                return MonthlyPlanPageProvider._empCellContract(
                  employee.months[month],
                  true,
                );
              }),
            };
          })
          .sort(function (left, right) {
            return left.name.localeCompare(right.name);
          });
        return {
          key: key,
          name: row.name,
          subLabel: row.member_count + " staff",
          cells: months.map(function (month) {
            return MonthlyPlanPageProvider._projCellContract(row.months[month], false);
          }),
          totalCell: {
            text: avg + " FTE",
            className: "p-total",
          },
          detailHeader: "Team Member",
          detailRows: detailRows,
          detailToggleTitle: detailRows.length
            ? "Show team members"
            : "No member data",
        };
      }),
    };
  },

  _pivot: function (raw) {
    var monthSet = {};
    var employeeMap = {};
    var projectMap = {};

    (raw || []).forEach(function (row) {
      var monthKey = row.year + "-" + ("0" + row.month).slice(-2);
      monthSet[monthKey] = 1;

      if (!employeeMap[row.employee_id]) {
        employeeMap[row.employee_id] = {
          id: row.employee_id,
          name: row.name,
          wd_id: row.wd_id,
          is_contractor: row.wd_id && row.wd_id.toString().slice(-1) === "C",
          months: {},
          projects: {},
        };
      }
      employeeMap[row.employee_id].months[monthKey] =
        (employeeMap[row.employee_id].months[monthKey] || 0) + row.allocation;
      if (!employeeMap[row.employee_id].projects[row.project_id]) {
        employeeMap[row.employee_id].projects[row.project_id] = {
          name: row.project_name,
          months: {},
        };
      }
      employeeMap[row.employee_id].projects[row.project_id].months[monthKey] =
        (employeeMap[row.employee_id].projects[row.project_id].months[monthKey] || 0) +
        row.allocation;

      if (!projectMap[row.project_id]) {
        projectMap[row.project_id] = {
          id: row.project_id,
          name: row.project_name,
          months: {},
          employees: {},
        };
      }
      projectMap[row.project_id].months[monthKey] =
        (projectMap[row.project_id].months[monthKey] || 0) + row.allocation;
      if (!projectMap[row.project_id].employees[row.employee_id]) {
        projectMap[row.project_id].employees[row.employee_id] = {
          name: row.name,
          is_contractor: row.wd_id && row.wd_id.toString().slice(-1) === "C",
          months: {},
        };
      }
      projectMap[row.project_id].employees[row.employee_id].months[monthKey] =
        (projectMap[row.project_id].employees[row.employee_id].months[monthKey] || 0) +
        row.allocation;
    });

    var months = Object.keys(monthSet).sort();
    var byEmployee = Object.values(employeeMap).sort(function (left, right) {
      return left.name.localeCompare(right.name);
    });
    var byProject = Object.values(projectMap)
      .map(function (project) {
        return {
          id: project.id,
          name: project.name,
          member_count: Object.keys(project.employees).length,
          months: project.months,
          employees: project.employees,
        };
      })
      .sort(function (left, right) {
        return left.name.localeCompare(right.name);
      });

    return {
      months: months,
      byEmployee: byEmployee,
      byProject: byProject,
    };
  },

  load: function () {
    return DataService.allocations()
      .then(function (raw) {
        var pivoted = MonthlyPlanPageProvider._pivot(raw);
        var employeeIssueSummary = MonthlyPlanPageProvider._employeeIssueSummary(
          pivoted.byEmployee,
          pivoted.months,
        );
        return {
          meta: LegacyPageProviderSupport.meta("allocation", []),
          months: pivoted.months,
          byEmployee: pivoted.byEmployee,
          byProject: pivoted.byProject,
          employeeIssueSummary: employeeIssueSummary,
          zeroAllocationEmployees: MonthlyPlanPageProvider._zeroAllocationEmployeeCount(
            pivoted.byEmployee,
            pivoted.months,
          ),
          zeroAllocationProjects: MonthlyPlanPageProvider._zeroAllocationProjectCount(
            pivoted.byProject,
            pivoted.months,
          ),
          employeeView: MonthlyPlanPageProvider._buildEmployeeView(
            pivoted.byEmployee,
            pivoted.months,
          ),
          projectView: MonthlyPlanPageProvider._buildProjectView(
            pivoted.byProject,
            pivoted.months,
          ),
        };
      })
      .catch(function (err) {
        throw LegacyPageProviderSupport.error(
          "Error loading monthly plan: " + err.message,
          "allocation",
          true,
        );
      });
  },
};
