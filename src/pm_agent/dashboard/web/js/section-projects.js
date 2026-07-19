var SectionProjects = {
  load: function () {
    var el = document.getElementById("projects-content");
    el.innerHTML = C.skeleton();
    Promise.all([DataService.projects(), DataService.projectHealth()])
      .then(function (results) {
        var projs = results[0];
        var healthList = results[1];
        // Build health lookup by project id
        var healthMap = {};
        healthList.forEach(function (h) {
          healthMap[h.id] = h.health;
        });
        // Merge health data into projects
        projs = projs.map(function (p) {
          p.health = healthMap[p.id] || null;
          return p;
        });
        var html = projs
          .map(function (p, i) {
            return C.projectCard(p, i);
          })
          .join("");
        el.innerHTML = '<div class="proj-grid">' + html + "</div>";
      })
      .catch(function (err) {
        el.innerHTML = C.alertStrip("X", "Error: " + err.message, "red");
      });
  },
};
