var UC = {
  _toneForState: function (value) {
    var normalized = String(value || "").toLowerCase();
    if (
      [
        "critical",
        "failed",
        "invalid",
        "red",
        "error",
        "expired",
        "overdue",
        "high",
      ].indexOf(normalized) >= 0
    ) {
      return "error";
    }
    if (
      [
        "amber",
        "yellow",
        "warning",
        "partial",
        "stale",
        "never_synced",
        "blocked",
      ].indexOf(normalized) >= 0
    ) {
      return "amber";
    }
    if (["active", "open", "pending", "not_performed", "info"].indexOf(normalized) >= 0) {
      return "blue";
    }
    if (
      [
        "success",
        "available",
        "clear",
        "fresh",
        "green",
        "complete",
        "completed",
        "known",
        "ready",
      ].indexOf(normalized) >= 0
    ) {
      return "green";
    }
    if (
      [
        "unknown",
        "unavailable",
        "not_available",
        "limited",
        "n/a",
      ].indexOf(normalized) >= 0
    ) {
      return "muted";
    }
    return "navy";
  },

  badge: function (label, tone) {
    return '<span class="badge badge-' + (tone || "muted") + '">' + esc(label) + "</span>";
  },

  stateBadge: function (value, options) {
    options = options || {};
    var label = options.label || humanizeKey(value || "unknown");
    var prefix = options.prefix ? options.prefix + ": " : "";
    return UC.badge(prefix + label, options.tone || UC._toneForState(value));
  },

  metricGrid: function (metrics) {
    return '<div class="kpi-grid">' + metrics.map(function (metric) {
      return C.kpiCard(
        metric.label,
        metric.value,
        metric.sub || "",
        metric.variant || ""
      );
    }).join("") + "</div>";
  },

  emptyState: function (title, message) {
    return '<div class="intelligence-empty">'
      + '<div class="intelligence-empty-title">' + esc(title) + "</div>"
      + '<div class="intelligence-empty-text">' + esc(message) + "</div>"
      + "</div>";
  },

  errorState: function (title, message) {
    return '<div class="intelligence-empty intelligence-empty-error">'
      + '<div class="intelligence-empty-title">' + esc(title) + "</div>"
      + '<div class="intelligence-empty-text">' + esc(message) + "</div>"
      + "</div>";
  },

  _formatWarning: function (warning) {
    if (warning == null) return "Unknown warning";
    if (typeof warning === "string") return warning;
    if (typeof warning !== "object") return String(warning);
    var pieces = [];
    Object.keys(warning).forEach(function (key) {
      if (key === "code") return;
      var value = warning[key];
      if (value == null || value === "") return;
      pieces.push(humanizeKey(key) + ": " + value);
    });
    return warning.code ? warning.code + (pieces.length ? " · " + pieces.join(" · ") : "") : JSON.stringify(warning);
  },

  renderWarnings: function (warnings) {
    if (!warnings || !warnings.length) return "";
    return '<div class="intelligence-subsection">'
      + '<div class="intelligence-subtitle">Warnings</div>'
      + '<div class="intelligence-warning-list">'
      + warnings.map(function (warning) {
        return '<div class="intelligence-warning-item">' + esc(UC._formatWarning(warning)) + "</div>";
      }).join("")
      + "</div></div>";
  },

  renderFreshness: function (freshness) {
    if (!freshness || !freshness.length) return "";
    return '<div class="intelligence-subsection">'
      + '<div class="intelligence-subtitle">Freshness</div>'
      + '<div class="intelligence-freshness-grid">'
      + freshness.map(function (item) {
        var observed = item && item.observed_at ? fmtDateTime(item.observed_at) : "Not recorded";
        var meta = [];
        if (item && item.refresh_sla_hours != null) meta.push("SLA " + item.refresh_sla_hours + "h");
        if (item && item.rule_version) meta.push(item.rule_version);
        return '<div class="intelligence-freshness-item">'
          + '<div class="intelligence-freshness-head">'
          + '<div class="intelligence-freshness-source">' + esc(item && item.source_id ? item.source_id : "source") + "</div>"
          + UC.stateBadge(item && item.state ? item.state : "unknown")
          + "</div>"
          + '<div class="intelligence-freshness-time">' + esc(observed) + "</div>"
          + (meta.length ? '<div class="intelligence-freshness-meta">' + esc(meta.join(" · ")) + "</div>" : "")
          + "</div>";
      }).join("")
      + "</div></div>";
  },

  table: function (columns, rows, emptyText) {
    if (!rows || !rows.length) return UC.emptyState("No rows returned", emptyText);
    return '<div class="table-wrap"><table><thead><tr>'
      + columns.map(function (column) {
        return "<th" + (column.className ? ' class="' + column.className + '"' : "") + ">" + esc(column.label) + "</th>";
      }).join("")
      + "</tr></thead><tbody>"
      + rows.map(function (row) {
        return "<tr>" + columns.map(function (column) {
          var cell = column.render ? column.render(row) : UC.inlineValue(row[column.key]);
          return "<td" + (column.cellClassName ? ' class="' + column.cellClassName + '"' : "") + ">" + cell + "</td>";
        }).join("") + "</tr>";
      }).join("")
      + "</tbody></table></div>";
  },

  summaryList: function (items, emptyText) {
    if (!items || !items.length) return UC.emptyState("Nothing to show", emptyText);
    return '<div class="intelligence-summary-list">' + items.join("") + "</div>";
  },

  sectionCard: function (title, bodyHtml, subtitle) {
    return '<div class="intelligence-section-card">'
      + '<div class="intelligence-section-card-head">'
      + '<div class="intelligence-section-card-title">' + esc(title) + "</div>"
      + (subtitle ? '<div class="intelligence-section-card-sub">' + esc(subtitle) + "</div>" : "")
      + "</div>"
      + bodyHtml
      + "</div>";
  },

  inlineValue: function (value) {
    if (value == null || value === "") return '<span class="text-muted">—</span>';
    if (Array.isArray(value)) {
      if (!value.length) return '<span class="text-muted">—</span>';
      return esc(value.map(function (item) {
        if (item && typeof item === "object" && item.kind && item.id) {
          return item.kind + ":" + item.id;
        }
        return String(item);
      }).join(", "));
    }
    if (typeof value === "object") {
      if (value.kind && value.id) return esc(value.kind + " · " + value.id);
      return esc(JSON.stringify(value));
    }
    return esc(String(value));
  },

  subjectLabel: function (subject) {
    if (!subject) return "—";
    if (typeof subject === "string") return subject;
    if (subject.kind && subject.id) return subject.kind + " · " + subject.id;
    return JSON.stringify(subject);
  },

  recordSummary: function (record, preferredKeys) {
    preferredKeys = preferredKeys || [];
    var keys = preferredKeys.length ? preferredKeys.slice() : Object.keys(record || {});
    var pieces = [];
    keys.some(function (key) {
      if (!record || !(key in record)) return false;
      var value = record[key];
      if (value == null || value === "" || (Array.isArray(value) && !value.length)) return false;
      if (key === "subject") value = UC.subjectLabel(value);
      else if (Array.isArray(value)) value = value.join(", ");
      else if (typeof value === "object") value = JSON.stringify(value);
      pieces.push('<div class="intelligence-summary-item-line"><strong>' + esc(humanizeKey(key)) + ":</strong> " + esc(String(value)) + "</div>");
      return pieces.length >= 4;
    });
    return pieces.join("");
  },

  useCasePanel: function (options) {
    var result = options.result;
    var badges = [
      UC.stateBadge(result.status || "unknown", { prefix: "Status" }),
      UC.badge("Contract " + (result.contract_version || "—"), "navy"),
      UC.badge(
        (result.warnings || []).length + " " + pluralize((result.warnings || []).length, "warning"),
        (result.warnings || []).length ? "amber" : "green"
      ),
      UC.badge(
        (result.freshness || []).length + " freshness record" + (((result.freshness || []).length === 1) ? "" : "s"),
        (result.freshness || []).length ? "blue" : "muted"
      ),
    ];
    if (result.signals && result.signals.length) {
      badges.push(UC.badge(result.signals.length + " signals", "blue"));
    }
    if (result.recommendations && result.recommendations.length) {
      badges.push(UC.badge(result.recommendations.length + " recommendations", "info"));
    }
    return '<div class="card intelligence-panel">'
      + '<div class="intelligence-panel-head">'
      + '<div class="intelligence-panel-copy">'
      + '<div class="card-title-lg">' + esc(options.title) + "</div>"
      + (options.subtitle ? '<div class="intelligence-panel-sub">' + esc(options.subtitle) + "</div>" : "")
      + "</div>"
      + '<div class="intelligence-panel-meta">' + badges.join("") + "</div>"
      + "</div>"
      + (options.summaryHtml || "")
      + UC.renderWarnings(result.warnings || [])
      + (options.bodyHtml || UC.emptyState("No data returned", "The use case completed without a visible result payload."))
      + UC.renderFreshness(result.freshness || [])
      + "</div>";
  },

  failedPanel: function (title, subtitle, message) {
    return '<div class="card intelligence-panel">'
      + '<div class="intelligence-panel-head">'
      + '<div class="intelligence-panel-copy">'
      + '<div class="card-title-lg">' + esc(title) + "</div>"
      + (subtitle ? '<div class="intelligence-panel-sub">' + esc(subtitle) + "</div>" : "")
      + "</div>"
      + '<div class="intelligence-panel-meta">' + UC.stateBadge("failed", { prefix: "Status" }) + "</div>"
      + "</div>"
      + UC.errorState("Unable to load this view", message)
      + "</div>";
  },
};
