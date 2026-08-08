var SectionProjects = {
  load: function () {
    var el = document.getElementById("projects-content");
    el.innerHTML = C.skeleton();
    ProjectsPageProvider.load()
      .then(function (model) {
        var html = model.projects
          .map(function (p, i) {
            return C.projectCard(p, i);
          })
          .join("");
        var alerts = model.meta.issues
          .map(function (issue) {
            return C.alertStrip("i", esc(issue.message), "blue");
          })
          .join("");
        el.innerHTML = (alerts ? '<div class="card mb-4">' + alerts + "</div>" : "")
          + '<div class="proj-grid">' + html + "</div>";
      })
      .catch(function (err) {
        el.innerHTML = C.alertStrip(
          "X",
          err.message || "Error loading projects",
          "red",
        );
      });
  },
};
