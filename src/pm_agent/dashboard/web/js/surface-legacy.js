var LegacyDashboardSurface = {
  name: "legacy",
  tabs: [
    {
      id: "overview",
      load: function () {
        SectionOverview.load();
      },
    },
    {
      id: "projects",
      load: function () {
        SectionProjects.load();
      },
    },
    {
      id: "team",
      load: function () {
        SectionTeam.load();
      },
    },
    {
      id: "hiref",
      load: function () {
        SectionHiref.load();
      },
    },
    {
      id: "allocation",
      load: function () {
        SectionAllocation.load();
      },
    },
    {
      id: "health",
      load: function () {
        SectionHealth.load();
      },
    },
  ],
};
