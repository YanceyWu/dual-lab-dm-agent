var LegacyPageProviderSupport = {
  meta: function (pageKey, issues) {
    var normalized = (issues || []).filter(function (issue) {
      return !!issue;
    });
    return {
      pageKey: pageKey,
      state: normalized.length ? "degraded" : "ready",
      issues: normalized,
    };
  },

  issue: function (source, state, message) {
    return {
      source: source,
      state: state || "unavailable",
      message: message || LegacyPageProviderSupport.unavailableMessage(source),
    };
  },

  issueFromRejection: function (source, reason) {
    return LegacyPageProviderSupport.issue(
      source,
      "unavailable",
      reason && reason.message
        ? reason.message
        : LegacyPageProviderSupport.unavailableMessage(source),
    );
  },

  error: function (message, source, retryable) {
    var err = new Error(message);
    if (source) err.source = source;
    if (retryable != null) err.retryable = !!retryable;
    return err;
  },

  isFulfilled: function (result) {
    return result && result.status === "fulfilled";
  },

  valueOf: function (result) {
    return LegacyPageProviderSupport.isFulfilled(result) ? result.value : null;
  },

  unavailableMessage: function (source) {
    return humanizeKey(source || "data") + " unavailable";
  },
};
