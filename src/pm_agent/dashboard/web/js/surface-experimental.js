var ExperimentalDashboardSurface = {
  name: "experimental",
  tabs: [
    {
      id: "attention",
      load: function () {
        SectionIntelligence.loadAttention();
      },
    },
    {
      id: "weekly-brief",
      load: function () {
        SectionIntelligence.loadWeeklyBrief();
      },
    },
    {
      id: "capacity",
      load: function () {
        SectionIntelligence.loadCapacity();
      },
    },
    {
      id: "execution",
      load: function () {
        SectionIntelligence.loadExecution();
      },
    },
    {
      id: "layered-health",
      load: function () {
        SectionIntelligence.loadLayeredHealth();
      },
    },
    {
      id: "connectors",
      load: function () {
        SectionIntelligence.loadConnectors();
      },
    },
    {
      id: "snapshots",
      load: function () {
        SectionIntelligence.loadSnapshots();
      },
    },
  ],
};
