/* app.js - navigation controller */
var App = {
  _current: "overview",
  _loaded: {},
  _visibleTabs: new Set(["overview"]),
  _tabRegistry: {},

  _surfaceConfig: function () {
    return CONFIG.PRODUCT_SURFACE || {
      defaultTab: "overview",
      visibleTabs: ["overview"],
      tabGroups: {},
    };
  },

  _surfaceAssemblies: function () {
    var assemblies = [];
    if (typeof LegacyDashboardSurface !== "undefined") {
      assemblies.push(LegacyDashboardSurface);
    }
    if (typeof ExperimentalDashboardSurface !== "undefined") {
      assemblies.push(ExperimentalDashboardSurface);
    }
    return assemblies.filter(function (surface) {
      return surface && Array.isArray(surface.tabs);
    });
  },

  _buildTabRegistry: function () {
    var registry = {};
    App._surfaceAssemblies().forEach(function (surface) {
      surface.tabs.forEach(function (entry) {
        registry[entry.id] = entry;
      });
    });
    App._tabRegistry = registry;
  },

  _resolveDefaultTab: function (preferred) {
    if (preferred && App._visibleTabs.has(preferred)) return preferred;
    var first = App._visibleTabs.values().next();
    return first.done ? "overview" : first.value;
  },

  _applySurface: function () {
    var surface = App._surfaceConfig();
    var configuredTabs = Array.isArray(surface.visibleTabs) && surface.visibleTabs.length
      ? surface.visibleTabs.slice()
      : ["overview"];
    App._visibleTabs = new Set(configuredTabs);
    App._current = App._resolveDefaultTab(surface.defaultTab);

    document.querySelectorAll(".nav-item").forEach(function (el) {
      var visible = App._visibleTabs.has(el.dataset.tab);
      el.hidden = !visible;
      if (!visible) el.classList.remove("active");
    });

    document.querySelectorAll(".nav-group-label").forEach(function (el) {
      var group = el.dataset.surfaceGroup;
      var groupTabs = (surface.tabGroups && surface.tabGroups[group]) || [];
      var visible = !group || groupTabs.some(function (tab) {
        return App._visibleTabs.has(tab);
      });
      el.hidden = !visible;
    });

    document.querySelectorAll(".section").forEach(function (el) {
      var tab = el.dataset.tab || el.id.replace("section-", "");
      var visible = App._visibleTabs.has(tab);
      el.hidden = !visible;
      if (!visible) el.classList.remove("active");
    });
  },

  visibleTabs: function () {
    return Array.from(App._visibleTabs);
  },

  navigate: function (tab) {
    if (!App._visibleTabs.has(tab)) return false;
    /* update nav items */
    document.querySelectorAll(".nav-item").forEach(function (el) {
      el.classList.toggle("active", el.dataset.tab === tab);
    });
    /* show/hide sections */
    document.querySelectorAll(".section").forEach(function (el) {
      el.classList.toggle("active", el.id === "section-" + tab);
    });
    App._current = tab;
    if (!App._loaded[tab]) App._load(tab);
    return true;
  },

  _load: function (tab) {
    if (!App._visibleTabs.has(tab)) return;
    var entry = App._tabRegistry[tab];
    if (!entry || typeof entry.load !== "function") return;
    App._loaded[tab] = true;
    entry.load();
  },

  reload: function () {
    App._loaded = {};
    App._load(App._current);
  },
};

document.addEventListener("DOMContentLoaded", function () {
  App._buildTabRegistry();
  App._applySurface();
  App.navigate(App._current);
});
