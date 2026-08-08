var HirefPageProvider = {
  _coverageSubtitle: function (data, fallback) {
    if (fallback != null) return fallback;
    return (
      "Contract coverage " +
      humanizeKey(data.contract_coverage_freshness_state || "unknown").toLowerCase()
    );
  },

  _signalBadges: function (item) {
    var badges = [];
    if (item.next_hiref || item.assigned_next_hiref) {
      badges.push({ text: "Next HIREF Ready", className: "badge-info" });
    } else if (item.reserved_for_next) {
      badges.push({ text: "Reserved Next Holder", className: "badge-blue" });
    } else if (item.placeholder_name) {
      badges.push({ text: "Placeholder Reserved", className: "badge-amber" });
    }
    if (item.project_alignment_status === "mismatch") {
      badges.push({ text: "Project Mismatch", className: "badge-error" });
    } else if (item.project_alignment_status === "no_active_assignment") {
      badges.push({ text: "No Active Project", className: "badge-muted" });
    }
    return badges;
  },

  _nextHirefDetail: function (item) {
    var nextHirefId = item.next_hiref || item.assigned_next_hiref || "";
    var nextHirefEndDate = item.next_hiref_end_date || item.assigned_next_hiref_end_date || "";
    if (!nextHirefId) return "";
    return "Next: " + nextHirefId + (nextHirefEndDate ? " → " + nextHirefEndDate : "");
  },

  _normalizeAllHirefRow: function (item) {
    return {
      id: item.id || "",
      project: item.project || "",
      urgency: item.urgency || "",
      signalBadges: HirefPageProvider._signalBadges(item),
      endDate: item.end_date || "",
      primaryText: item.assigned_to || "FREE",
      primaryTone: item.assigned_to ? "" : "badge-green",
      wdId: item.wd_id || "",
      actualProjectText:
        item.actual_project_display && item.actual_project_display !== "-"
          ? "Actual: " + item.actual_project_display
          : "",
      nextHirefDetail: HirefPageProvider._nextHirefDetail(item),
      reservedText: item.reserved_for_next ? "Reserved: " + item.reserved_for_next : "",
      placeholderText: item.placeholder_name ? "Placeholder: " + item.placeholder_name : "",
    };
  },

  _normalizeExpiringStaffRow: function (item) {
    return {
      wdId: item.wd_id || "",
      name: item.name || "",
      currentHirefId: item.current_hiref || "",
      hirefProject: item.hiref_project || "",
      urgency: item.urgency || "",
      signalBadges: HirefPageProvider._signalBadges(item),
      endDate: item.end_date || "",
      actualProjectText: item.actual_project || "",
      nextHirefDetail: HirefPageProvider._nextHirefDetail(item),
      nextProjectText:
        item.next_hiref_project && item.next_hiref_project !== (item.hiref_project || "")
          ? "Next project: " + item.next_hiref_project
          : "",
    };
  },

  load: function () {
    return DataService.hiref()
      .then(function (data) {
        var reviewCountsAvailable = data.review_counts_available === true;
        var urgencyCount = function (urgency) {
          return (data.expiring_staff || []).filter(function (item) {
            return item.urgency === urgency;
          }).length;
        };
        var assignedFreeSubtitle =
          data.assigned_count != null && data.free_count != null
            ? data.assigned_count + " assigned / " + data.free_count + " free"
            : HirefPageProvider._coverageSubtitle(data, null);
        var nextHirefValue =
          data.next_covered_count != null ? data.next_covered_count : "Unknown";
        var nextHirefSubtitle =
          data.next_covered_count != null
            ? "Already covered by next HIREF"
            : HirefPageProvider._coverageSubtitle(data, null);
        var mismatchValue = data.mismatch_count != null ? data.mismatch_count : "Unknown";
        var mismatchSubtitle =
          data.mismatch_count != null
            ? "HIREF project != actual project"
            : HirefPageProvider._coverageSubtitle(data, null);
        var freeSlotsValue = data.free_count != null ? data.free_count : "Unknown";
        var freeSlotsSubtitle =
          data.free_count != null
            ? "Available for assignment"
            : HirefPageProvider._coverageSubtitle(data, null);

        return {
          meta: LegacyPageProviderSupport.meta("hiref", []),
          kpis: {
            total: {
              value: data.total,
              subtitle: assignedFreeSubtitle,
            },
            critical: {
              value: reviewCountsAvailable ? urgencyCount("critical") : "Unknown",
              subtitle: reviewCountsAvailable
                ? "Immediate action required"
                : HirefPageProvider._coverageSubtitle(data, null),
              variant:
                reviewCountsAvailable && urgencyCount("critical") > 0 ? "coral" : "",
            },
            high: {
              value: reviewCountsAvailable ? urgencyCount("high") : "Unknown",
              subtitle: reviewCountsAvailable
                ? "Plan renewal soon"
                : HirefPageProvider._coverageSubtitle(data, null),
              variant: reviewCountsAvailable && urgencyCount("high") > 0 ? "amber" : "",
            },
            nextHiref: {
              value: nextHirefValue,
              subtitle: nextHirefSubtitle,
              variant: data.next_covered_count > 0 ? "info" : "",
            },
            mismatch: {
              value: mismatchValue,
              subtitle: mismatchSubtitle,
              variant: data.mismatch_count > 0 ? "coral" : "",
            },
            freeSlots: {
              value: freeSlotsValue,
              subtitle: freeSlotsSubtitle,
              variant: data.free_count != null ? "info" : "",
            },
          },
          expiringStaffState: reviewCountsAvailable
            ? (data.expiring_staff || []).length
              ? "ready"
              : "empty"
            : "unavailable",
          expiringStaffMessage: reviewCountsAvailable
            ? "No staff with HIREF expiring within 180 days"
            : HirefPageProvider._coverageSubtitle(data, null),
          expiringStaffTone: reviewCountsAvailable ? "green" : "blue",
          expiringStaff: (data.expiring_staff || []).map(
            HirefPageProvider._normalizeExpiringStaffRow,
          ),
          allHiref: (data.all_hiref || []).map(HirefPageProvider._normalizeAllHirefRow),
        };
      })
      .catch(function (err) {
        throw LegacyPageProviderSupport.error(
          "Error loading HIREF: " + err.message,
          "hiref",
          true,
        );
      });
  },
};
