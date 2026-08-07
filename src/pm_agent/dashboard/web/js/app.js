/* app.js - navigation controller */
var App = {
  _current: "overview",
  _loaded: {},
  _visibleTabs: new Set(["overview"]),

  _surfaceConfig: function () {
    return CONFIG.PRODUCT_SURFACE || {
      defaultTab: "overview",
      visibleTabs: ["overview"],
      tabGroups: {},
    };
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
    App._loaded[tab] = true;
    if (tab === "overview") SectionOverview.load();
    if (tab === "projects") SectionProjects.load();
    if (tab === "team") SectionTeam.load();
    if (tab === "hiref") SectionHiref.load();
    if (tab === "allocation") SectionAllocation.load();
    if (tab === "health") SectionHealth.load();
    if (tab === "attention") SectionIntelligence.loadAttention();
    if (tab === "weekly-brief") SectionIntelligence.loadWeeklyBrief();
    if (tab === "capacity") SectionIntelligence.loadCapacity();
    if (tab === "execution") SectionIntelligence.loadExecution();
    if (tab === "layered-health") SectionIntelligence.loadLayeredHealth();
    if (tab === "connectors") SectionIntelligence.loadConnectors();
    if (tab === "snapshots") SectionIntelligence.loadSnapshots();
  },

  reload: function () {
    App._loaded = {};
    App._load(App._current);
  },
};

document.addEventListener("DOMContentLoaded", function () {
  App._applySurface();
  App.navigate(App._current);
});
