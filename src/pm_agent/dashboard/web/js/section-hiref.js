var SectionHiref = {
  load: function() {
    var el = document.getElementById('hiref-content');
    el.innerHTML = C.skeleton();
    HirefPageProvider.load().then(function(model) {
      var allRows = model.allHiref.map(function(item) { return C.hirefRow(item); }).join('');
      var staffRows = model.expiringStaff.map(function(item) { return C.staffHirefRow(item); }).join('');
      el.innerHTML =
        '<div class="kpi-grid mb-5">'
        + C.kpiCard('Total HIREF', model.kpis.total.value, model.kpis.total.subtitle)
        + C.kpiCard('Critical <60d', model.kpis.critical.value, model.kpis.critical.subtitle, model.kpis.critical.variant)
        + C.kpiCard('High <90d', model.kpis.high.value, model.kpis.high.subtitle, model.kpis.high.variant)
        + C.kpiCard('Next HIREF', model.kpis.nextHiref.value, model.kpis.nextHiref.subtitle, model.kpis.nextHiref.variant)
        + C.kpiCard('Mismatch', model.kpis.mismatch.value, model.kpis.mismatch.subtitle, model.kpis.mismatch.variant)
        + C.kpiCard('Free Slots', model.kpis.freeSlots.value, model.kpis.freeSlots.subtitle, model.kpis.freeSlots.variant)
      + '</div>'
        + '<div class="subtab-bar">'
          + '<button class="subtab-btn active" onclick="SectionHiref._tab(\'staff\',this)">Staff Expiry View</button>'
          + '<button class="subtab-btn" onclick="SectionHiref._tab(\'all\',this)">All HIREF Slots</button>'
        + '</div>'
        + '<div class="subtab-panel active" id="hs-staff">'
          + (model.expiringStaffState === 'ready'
            ? '<div class="table-wrap"><table><thead><tr>'
              + '<th>WD ID</th><th>Name</th><th>HIREF ID</th><th>HIREF Project</th>'
              + '<th>Status / Signals</th><th>End Date</th><th>Actual Project / Coverage</th>'
              + '</tr></thead><tbody>' + staffRows + '</tbody></table></div>'
            : C.alertStrip('i', model.expiringStaffMessage, model.expiringStaffTone))
        + '</div>'
        + '<div class="subtab-panel" id="hs-all">'
          + '<div class="table-wrap"><table><thead><tr>'
            + '<th>HIREF ID</th><th>Project</th><th>Status / Signals</th><th>End Date</th><th>Assigned To / Coverage</th>'
          + '</tr></thead><tbody>' + allRows + '</tbody></table></div>'
        + '</div>';
    }).catch(function(err) {
      el.innerHTML = C.alertStrip('X', err.message || 'Error loading HIREF', 'red');
    });
  },
  _tab: function(which, btn) {
    document.querySelectorAll('#hiref-content .subtab-btn').forEach(function(b){ b.classList.remove('active'); });
    btn.classList.add('active');
    document.getElementById('hs-staff').classList.toggle('active', which==='staff');
    document.getElementById('hs-all').classList.toggle('active',   which==='all');
  }
};
