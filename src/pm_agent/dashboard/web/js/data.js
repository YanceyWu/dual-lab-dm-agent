/* data.js - all API calls, returns Promises */
var DataService = {
  _get: function (path) {
    return fetch(CONFIG.API + path).then(function (r) {
      if (!r.ok) throw new Error("API " + r.status + ": " + path);
      return r.json();
    });
  },
  _post: function (path, payload) {
    return fetch(CONFIG.API + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    }).then(function (r) {
      return r
        .json()
        .catch(function () {
          return {};
        })
        .then(function (data) {
          if (!r.ok) {
            throw new Error(data.message || ("API " + r.status + ": " + path));
          }
          return data;
        });
    });
  },
  summary: function () {
    return DataService._get("/api/summary");
  },
  projects: function () {
    return DataService._get("/api/projects");
  },
  employees: function () {
    return DataService._get("/api/employees");
  },
  hiref: function () {
    return DataService._get("/api/hiref");
  },
  allocations: function () {
    return DataService._get("/api/allocations");
  },
  projectHealth: function () {
    return DataService._get("/api/project-health");
  },
  queryUseCase: function (useCaseId, parameters, options) {
    var payload = {
      parameters: parameters || {},
    };
    if (typeof options === "string") {
      payload.correlation_id = options;
    } else if (options) {
      if (options.correlationId) payload.correlation_id = options.correlationId;
      if (options.contractVersion) payload.contract_version = options.contractVersion;
    }
    return DataService._post("/api/tool/query/" + encodeURIComponent(useCaseId), payload);
  },
  previewProjectHealthSync: function (boardId) {
    return DataService._post("/api/project-health/sync", {
      operation: "preview",
      board_id: boardId,
    });
  },
  previewStaleProjectHealthSync: function () {
    return DataService._post("/api/project-health/sync", {
      operation: "preview",
      stale_only: true,
    });
  },
  confirmProjectHealthSync: function (preview) {
    return DataService._post("/api/project-health/sync", {
      operation: "confirm",
      operation_id: preview.execution_id,
      confirmation_token: preview.confirmation_token,
    });
  },
};
