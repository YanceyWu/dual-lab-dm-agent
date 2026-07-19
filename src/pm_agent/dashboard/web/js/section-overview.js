var SectionOverview = {
  load: function() {
    var el = document.getElementById('overview-content');
    el.innerHTML = C.skeleton();
    Promise.all([
      DataService.summary(), DataService.projects(),
      DataService.employees(), DataService.hiref()
    ]).then(function(res) {
      var s = res[0], projs = res[1], emps = res[2], h = res[3];
      document.getElementById('badge-projects').textContent = projs.length;
      document.getElementById('badge-team').textContent     = emps.length;
      var crit = h.expiring_staff.filter(function(x){ return x.urgency==='critical'; }).length;
      var hirefBadge = document.getElementById('badge-hiref');
      hirefBadge.textContent = crit > 0 ? crit : 'OK';
      hirefBadge.className   = 'nav-badge' + (crit > 0 ? '' : ' green');
      var tsEl = document.getElementById('sidebar-ts');
      if (tsEl && s.updated_at) tsEl.textContent = 'Updated ' + s.updated_at.substring(11,16);
      var alerts = '';
      if (crit > 0)
        alerts += C.alertStrip('!', '<strong>' + crit + ' contractor(s)</strong> have HIREF expiring within 60 days', 'red');
      var overloaded = emps.filter(function(e){ return e.load_pct > 100; });
      if (overloaded.length > 0)
        alerts += C.alertStrip('!', '<strong>' + overloaded.length + ' staff</strong> exceeding 100% -- review', 'amber');
      if (h.free_count > 0)
        alerts += C.alertStrip('i', '<strong>' + h.free_count + ' free HIREF slots</strong> available', 'blue');
      var focusProjs = projs.filter(function(p){ return p.is_focus; });
      var focusHtml = focusProjs.length
        ? focusProjs.map(function(p) {
            return '<div style="padding:8px 0;border-bottom:1px solid var(--border-light);display:flex;align-items:center;gap:10px">'
              + '<div style="width:4px;height:28px;border-radius:2px;background:var(--green);flex-shrink:0"></div>'
              + '<div><div class="td-name">' + p.name + '</div>'
              + '<div style="margin-top:2px">' + C.phaseBadge(p.phase) + ' ' + C.priorityBadge(p.priority_tier) + '</div></div>'
            + '</div>';
          }).join('')
        : '<div class="text-muted" style="font-size:13px">No focus projects set</div>';
      var overLoad  = emps.filter(function(e){ return e.load_pct > 100; }).length;
      var fullLoad  = emps.filter(function(e){ return e.load_pct === 100; }).length;
      var availLoad = emps.filter(function(e){ return e.load_pct < 100; }).length;
      var total = emps.length;
      function distBar(count, color, label) {
        var w = total > 0 ? Math.round(count / total * 160) : 0;
        return '<div class="load-dist-row">'
          + '<div class="load-dist-label">' + label + '</div>'
          + '<div class="load-dist-bar"><div style="height:8px;background:var(--border);border-radius:9999px;overflow:hidden">'
            + '<div style="height:100%;width:' + w + 'px;max-width:160px;background:' + color + ';border-radius:9999px"></div>'
          + '</div></div>'
          + '<div class="load-dist-count">' + count + '</div>'
        + '</div>';
      }
      el.innerHTML =
        '<div class="kpi-grid">'
          + C.kpiCard('Total Staff',     s.total_staff,        s.ltfte + ' LTFTE / ' + s.stfte + ' STFTE')
          + C.kpiCard('Active Projects', s.active_projects,    s.focus_projects + ' focus project(s)', 'blue')
          + C.kpiCard('Avg Team Load',   s.avg_load + '%',     s.overloaded + ' staff overloaded', s.overloaded > 0 ? 'coral' : '')
          + C.kpiCard('HIREF Alerts',    s.hiref_alerts_60d,   'expiring within 60 days', s.hiref_alerts_60d > 0 ? 'amber' : '')
          + C.kpiCard('Free HIREF',      s.free_hiref_slots,   'slots available', 'info')
        + '</div>'
        + (alerts ? '<div class="card mb-4">' + alerts + '</div>' : '')
        + '<div class="two-col">'
          + '<div class="card"><div class="card-title">Focus Projects</div>' + focusHtml + '</div>'
          + '<div class="card"><div class="card-title">Load Distribution</div>'
            + distBar(overLoad,  'var(--error)', 'Overloaded &gt;100%')
            + distBar(fullLoad,  'var(--amber)', 'At Capacity =100%')
            + distBar(availLoad, 'var(--green)', 'Available &lt;100%')
          + '</div>'
        + '</div>';
    }).catch(function(err) {
      document.getElementById('overview-content').innerHTML =
        C.alertStrip('X', 'Error loading overview: ' + err.message, 'red');
    });
  }
};
