/* app.js - navigation controller */
var App = {
  _current: "overview",
  _loaded: {},

  navigate: function (tab) {
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
  },

  _load: function (tab) {
    App._loaded[tab] = true;
    if (tab === "overview") SectionOverview.load();
    if (tab === "projects") SectionProjects.load();
    if (tab === "team") SectionTeam.load();
    if (tab === "hiref") SectionHiref.load();
    if (tab === "allocation") SectionAllocation.load();
    if (tab === "health") SectionHealth.load();
  },

  reload: function () {
    App._loaded = {};
    App._load(App._current);
  },
};

document.addEventListener("DOMContentLoaded", function () {
  App._load("overview");
});
