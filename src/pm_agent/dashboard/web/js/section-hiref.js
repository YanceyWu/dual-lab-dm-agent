var SectionHiref = {
  _coverageSubtitle: function(data, fallback) {
    if (fallback != null) return fallback;
    return 'Contract coverage ' + humanizeKey(data.contract_coverage_freshness_state || 'unknown').toLowerCase();
  },
  load: function() {
    var el = document.getElementById('hiref-content');
    el.innerHTML = C.skeleton();
    DataService.hiref().then(function(data) {
      var uc = function(u) {
        return data.expiring_staff.filter(function(x){ return x.urgency===u; }).length;
      };
      var assignedFreeSubtitle = (data.assigned_count != null && data.free_count != null)
        ? data.assigned_count + ' assigned / ' + data.free_count + ' free'
        : SectionHiref._coverageSubtitle(data, null);
      var nextHirefValue = data.next_covered_count != null ? data.next_covered_count : 'Unknown';
      var nextHirefSubtitle = data.next_covered_count != null
        ? 'Already covered by next HIREF'
        : SectionHiref._coverageSubtitle(data, null);
      var mismatchValue = data.mismatch_count != null ? data.mismatch_count : 'Unknown';
      var mismatchSubtitle = data.mismatch_count != null
        ? 'HIREF project != actual project'
        : SectionHiref._coverageSubtitle(data, null);
      var freeSlotsValue = data.free_count != null ? data.free_count : 'Unknown';
      var freeSlotsSubtitle = data.free_count != null
        ? 'Available for assignment'
        : SectionHiref._coverageSubtitle(data, null);
      var allRows   = data.all_hiref.map(function(h) { return C.hirefRow(h); }).join('');
      var staffRows = data.expiring_staff.map(function(e) { return C.staffHirefRow(e); }).join('');
      el.innerHTML =
        '<div class="kpi-grid mb-5">'
        + C.kpiCard('Total HIREF',   data.total,          assignedFreeSubtitle)
        + C.kpiCard('Critical <60d', uc('critical'),      'Immediate action required', uc('critical') > 0 ? 'coral' : '')
        + C.kpiCard('High <90d',     uc('high'),          'Plan renewal soon', uc('high') > 0 ? 'amber' : '')
        + C.kpiCard('Next HIREF',    nextHirefValue,      nextHirefSubtitle, data.next_covered_count > 0 ? 'info' : '')
        + C.kpiCard('Mismatch',      mismatchValue,       mismatchSubtitle, data.mismatch_count > 0 ? 'coral' : '')
        + C.kpiCard('Free Slots',    freeSlotsValue,      freeSlotsSubtitle, 'info')
      + '</div>'
        + '<div class="subtab-bar">'
          + '<button class="subtab-btn active" onclick="SectionHiref._tab(\'staff\',this)">Staff Expiry View</button>'
          + '<button class="subtab-btn"        onclick="SectionHiref._tab(\'all\',this)">All HIREF Slots</button>'
        + '</div>'
        + '<div class="subtab-panel active" id="hs-staff">'
          + (data.expiring_staff.length
            ? '<div class="table-wrap"><table><thead><tr>'
              + '<th>WD ID</th><th>Name</th><th>HIREF ID</th><th>HIREF Project</th>'
              + '<th>Status / Signals</th><th>End Date</th><th>Actual Project / Coverage</th>'
              + '</tr></thead><tbody>' + staffRows + '</tbody></table></div>'
            : C.alertStrip('OK', 'No staff with HIREF expiring within 180 days', 'green'))
        + '</div>'
        + '<div class="subtab-panel" id="hs-all">'
          + '<div class="table-wrap"><table><thead><tr>'
            + '<th>HIREF ID</th><th>Project</th><th>Status / Signals</th><th>End Date</th><th>Assigned To / Coverage</th>'
          + '</tr></thead><tbody>' + allRows + '</tbody></table></div>'
        + '</div>';
    }).catch(function(err) {
      el.innerHTML = C.alertStrip('X', 'Error: ' + err.message, 'red');
    });
  },
  _tab: function(which, btn) {
    document.querySelectorAll('#hiref-content .subtab-btn').forEach(function(b){ b.classList.remove('active'); });
    btn.classList.add('active');
    document.getElementById('hs-staff').classList.toggle('active', which==='staff');
    document.getElementById('hs-all').classList.toggle('active',   which==='all');
  }
};
