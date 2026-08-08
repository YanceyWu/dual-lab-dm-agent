var SectionTeam = {
  _data: [],
  load: function() {
    var el = document.getElementById('team-content');
    el.innerHTML = C.skeleton();
    TeamPageProvider.load().then(function(model) {
      SectionTeam._data = model.rows;
      el.innerHTML =
        '<div class="filter-bar">'
          + '<span class="filter-label">Filter</span>'
          + '<input class="search-input" id="t-search" placeholder="Name, WD ID, project..." oninput="SectionTeam._render()">'
          + '<select class="filter-select" id="t-type" onchange="SectionTeam._render()">'
            + '<option value="">All Types</option>'
            + '<option value="stfte">STFTE (Contractors)</option>'
            + '<option value="ltfte">LTFTE (Permanent)</option>'
          + '</select>'
          + '<select class="filter-select" id="t-load" onchange="SectionTeam._render()">'
            + '<option value="">All Loads</option>'
            + '<option value="over">Overloaded (&gt;100%)</option>'
            + '<option value="full">At Capacity (=100%)</option>'
            + '<option value="avail">Available (&lt;100%)</option>'
          + '</select>'
          + '<span class="filter-count" id="t-count"></span>'
        + '</div>'
        + '<div class="table-wrap"><table>'
          + '<thead><tr><th>WD ID</th><th>Name</th><th>Type</th><th>Level</th>'
          + '<th>Load</th><th>Projects / Next</th><th>HIREF</th></tr></thead>'
          + '<tbody id="t-body"></tbody>'
        + '</table></div>';
      SectionTeam._render();
    }).catch(function(err) {
      el.innerHTML = C.alertStrip('X', err.message || 'Error loading team', 'red');
    });
  },
  _render: function() {
    var q   = (document.getElementById('t-search').value || '').toLowerCase();
    var typ = document.getElementById('t-type').value;
    var lod = document.getElementById('t-load').value;
    var data = SectionTeam._data.filter(function(e) {
      var matchQ = !q || (e.searchText || "").indexOf(q) >= 0;
      var matchT = !typ || (typ==='stfte' && e.is_contractor) || (typ==='ltfte' && !e.is_contractor);
      var matchL = !lod
        || e.loadBucket === lod;
      return matchQ && matchT && matchL;
    });
    var rows = data.map(function(e){ return C.staffRow(e); }).join('');
    var tbody = document.getElementById('t-body');
    if (tbody) tbody.innerHTML = rows || '<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--text-muted)">No results</td></tr>';
    var cnt = document.getElementById('t-count');
    if (cnt) cnt.textContent = data.length + ' of ' + SectionTeam._data.length + ' staff';
  }
};
