var C = {
  badge: function(text, cls) {
    return '<span class="badge ' + cls + '">' + text + '</span>';
  },
  phaseBadge: function(phase) {
    var p = (phase || 'TBC').toLowerCase().replace(/[\s\/]+/g, '-');
    var labels = {
      planning:'Planning', development:'Development', uat:'UAT',
      'go-live':'Go-Live', support:'Support', 'on-hold':'On Hold', tbc:'TBC'
    };
    return '<span class="badge phase-' + p + '">' + (labels[p] || p) + '</span>';
  },
  priorityBadge: function(tier) {
    var map = { 1: ['P1 Focus','pri-1'], 2: ['P2 Normal','pri-2'], 3: ['P3 Low','pri-3'] };
    var e = map[tier] || ['P2','pri-2'];
    return '<span class="badge ' + e[1] + '">' + e[0] + '</span>';
  },
  urgencyBadge: function(urgency) {
    var map = {
      expired:  ['Expired',   'urgency-expired'],
      critical: ['Critical',  'urgency-critical'],
      high:     ['High',      'urgency-high'],
      medium:   ['Medium',    'urgency-medium'],
      ok:       ['OK',        'urgency-ok']
    };
    var e = map[urgency] || ['Unknown','badge-muted'];
    return '<span class="badge ' + e[1] + '">' + e[0] + '</span>';
  },
  hirefSignalBadges: function(item) {
    var badges = [];
    if (item.next_hiref || item.assigned_next_hiref) {
      badges.push(C.badge('Next HIREF Ready', 'badge-info'));
    } else if (item.reserved_for_next) {
      badges.push(C.badge('Reserved Next Holder', 'badge-blue'));
    } else if (item.placeholder_name) {
      badges.push(C.badge('Placeholder Reserved', 'badge-amber'));
    }

    if (item.project_alignment_status === 'mismatch') {
      badges.push(C.badge('Project Mismatch', 'badge-error'));
    } else if (item.project_alignment_status === 'no_active_assignment') {
      badges.push(C.badge('No Active Project', 'badge-muted'));
    }

    return badges.length ? '<div class="badge-row">' + badges.join(' ') + '</div>' : '';
  },
  hirefNextDetail: function(item) {
    var nextHirefId = item.next_hiref || item.assigned_next_hiref || '';
    var nextHirefEndDate = item.next_hiref_end_date || item.assigned_next_hiref_end_date || '';
    if (!nextHirefId) return '';
    return '<div class="td-muted">Next: ' + nextHirefId
      + (nextHirefEndDate ? ' → ' + nextHirefEndDate : '')
      + '</div>';
  },
  loadBar: function(pct) {
    var cls, label;
    if (pct > 100)        { cls = 'overload'; label = 'Overloaded'; }
    else if (pct === 100) { cls = 'full';     label = 'At Capacity'; }
    else if (pct >= 80)   { cls = 'full';     label = 'High - ' + (100-pct) + '% free'; }
    else                  { cls = 'ok';       label = 'Available - ' + (100-pct) + '% free'; }
    var w = Math.min(pct, 100);
    return '<div class="load-cell">'
      + '<div class="load-bar-row">'
        + '<div class="load-bar-track"><div class="load-bar-fill ' + cls + '" style="width:' + w + '%"></div></div>'
        + '<span class="load-pct ' + cls + '">' + pct + '%</span>'
      + '</div>'
      + '<div class="load-label ' + cls + '">' + label + '</div>'
    + '</div>';
  },
  kpiCard: function(label, value, sub, variant) {
    var renderedValue = displayValue(value, '—');
    var renderedSub = displayValue(sub, '—');
    return '<div class="kpi-card ' + (variant||'') + '">'
      + '<div class="kpi-label">' + esc(displayValue(label, '')) + '</div>'
      + '<div class="kpi-val">' + esc(renderedValue) + '</div>'
      + '<div class="kpi-sub">' + esc(renderedSub) + '</div>'
    + '</div>';
  },
  alertStrip: function(icon, msg, type) {
    return '<div class="alert-strip ' + type + '"><span>' + icon + '</span><span>' + msg + '</span></div>';
  },
  skeleton: function() {
    return '<div class="skeleton-wrap">'
      + '<div class="skeleton-kpi-row">'
        + '<div class="skeleton skeleton-kpi"></div>'
        + '<div class="skeleton skeleton-kpi"></div>'
        + '<div class="skeleton skeleton-kpi"></div>'
        + '<div class="skeleton skeleton-kpi"></div>'
      + '</div>'
      + '<div class="skeleton skeleton-h"></div>'
      + '<div class="skeleton skeleton-h"></div>'
      + '<div class="skeleton skeleton-table" style="height:200px;margin-top:16px"></div>'
    + '</div>';
  },
  ragBadge: function(rag) {
    if (!rag) return '';
    var map = { RED: 'rag-red', YELLOW: 'rag-yellow', AMBER: 'rag-yellow', GREEN: 'rag-green' };
    var cls = map[(rag||'').toUpperCase()] || 'rag-unknown';
    return '<span class="rag-badge ' + cls + '">' + (rag||'').toUpperCase() + '</span>';
  },
  jiraGrade: function(grade, score) {
    if (!grade) return '';
    var cls = grade === 'GREEN' ? 'jira-green' : grade === 'RED' ? 'jira-red' : 'jira-yellow';
    var label = score != null ? grade + ' ' + Math.round(score) : grade;
    return '<span class="jira-grade ' + cls + '">'
      + '<svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><circle cx="5" cy="5" r="4.5"/></svg>'
      + label + '</span>';
  },
  projectCard: function(p, idx) {
    var color = CONFIG.COLORS[idx % CONFIG.COLORS.length];
    var members = (p.members || []).map(function(m) {
      var pct = fmtPct(m.allocation);
      var isPlanned = m.assign_status === 'planned';
      var nameHtml = m.name + (isPlanned ? '<span class="planned-tag">Planned</span>' : '');
      var rowStyle = isPlanned ? 'opacity:0.65;' : '';
      return '<tr class="member-row" style="' + rowStyle + '">'
        + '<td class="proj-member-name">' + nameHtml + '</td>'
        + '<td class="proj-member-wd">' + (m.wd_id||'') + '</td>'
        + '<td class="proj-member-pct" style="color:' + color + '">' + pct + '%</td>'
      + '</tr>';
    }).join('');
    var memberTable = p.members && p.members.length
      ? '<table class="proj-member-table">'
          + '<tr class="thead-row"><td>Name</td><td>WD ID</td><td style="text-align:right">Alloc</td></tr>'
          + members
        + '</table>'
      : '<div style="padding:12px 16px;font-size:12px;color:var(--text-muted)">No staff assigned</div>';
    var milestones = (p.milestones||[]).map(function(m) {
      var n = typeof m === 'string' ? m : (m.name||String(m));
      return C.badge(n, 'badge-navy');
    }).join(' ');

    // Health badges from JIRA / Confluence
    var health = p.health || {};
    var conf = health.confluence || {};
    var jira = health.jira || {};
    var healthHtml = '';
    if (conf.rag_status || jira.overall_grade) {
      healthHtml = '<div class="proj-health-bar">';
      if (conf.rag_status) healthHtml += C.ragBadge(conf.rag_status);
      if (jira.overall_grade) healthHtml += C.jiraGrade(jira.overall_grade, jira.overall_score);
      if (jira.sp_progress_pct != null) {
        var sp = Math.round(jira.sp_progress_pct);
        healthHtml += '<span class="proj-sprint-pct">'
          + '<span class="proj-sprint-bar"><span style="width:' + Math.min(sp,100) + '%"></span></span>'
          + sp + '% SP</span>';
      }
      if (conf.snapshot_date) healthHtml += '<span class="proj-health-date">' + conf.snapshot_date + '</span>';
      healthHtml += '</div>';
    }

    var metaBadges = C.phaseBadge(p.phase) + ' ' + C.priorityBadge(p.priority_tier)
      + (p.is_focus ? ' ' + C.badge('Focus','badge-green') : '')
      + (p.hiref_risk > 0 ? ' ' + C.badge(p.hiref_risk + ' HIREF expiring','badge-error') : '');
    return '<div class="proj-card">'
      + '<div class="proj-card-header">'
        + '<div class="proj-card-accent">'
          + '<div class="proj-card-dot" style="background:' + color + '"></div>'
          + '<div>'
            + '<div class="proj-card-name">' + (p.name||'') + '</div>'
            + (p.objective ? '<div class="proj-card-objective">' + p.objective + '</div>' : '')
          + '</div>'
        + '</div>'
      + '</div>'
      + '<div class="proj-card-meta">' + metaBadges + '</div>'
      + healthHtml
      + (milestones ? '<div class="proj-card-milestones">' + milestones + '</div>' : '')
      + memberTable
      + '<div class="proj-card-footer">' + (p.members||[]).length + ' staff assigned</div>'
    + '</div>';
  },
  staffRow: function(e) {
    var projs = (e.projects||[]).map(function(p) {
      var pct = fmtPct(p.allocation);
      return '<span class="badge badge-navy" style="margin:1px 2px;white-space:normal">'
        + p.name + ' <strong>' + pct + '%</strong></span>';
    }).join(' ');
    var nextHtml = '';
    if (e.next_assignment) {
      var na = e.next_assignment;
      var mo = na.start_date ? na.start_date.substring(0,7) : '';
      nextHtml = '<div class="next-assign">&#8594; ' + na.name + ' ' + na.allocation + '%'
        + (mo ? ' from ' + fmtMonth(mo) : '') + '</div>';
    }
    var hirefCell;
    if (e.current_hiref) {
      hirefCell = C.urgencyBadge(e.hiref_urgency||'ok')
        + '<div class="td-mono" style="margin-top:2px">' + (e.current_hiref||'') + '</div>'
        + (e.hiref_end_date ? '<div class="td-muted">' + e.hiref_end_date + '</div>' : '');
    } else if (e.is_contractor) {
      hirefCell = C.badge('No HIREF','badge-error');
    } else {
      hirefCell = C.badge('N/A','badge-muted');
    }
    var typeTag = e.is_contractor ? C.badge('STFTE','badge-coral') : C.badge('LTFTE','badge-blue');
    var loadHtml = (e.current_state_staffing_state === 'known' && e.load_pct != null)
      ? C.loadBar(e.load_pct)
      : C.badge('Unknown','badge-muted');
    return '<tr>'
      + '<td class="td-mono">' + (e.wd_id||e.id||'') + '</td>'
      + '<td class="td-name">' + (e.name||'') + '</td>'
      + '<td>' + typeTag + '</td>'
      + '<td class="text-sec">' + (e.level||'--') + '</td>'
      + '<td>' + loadHtml + '</td>'
      + '<td>' + projs + nextHtml + '</td>'
      + '<td>' + hirefCell + '</td>'
    + '</tr>';
  },
  hirefRow: function(h) {
    var who = h.assigned_to
      ? '<span class="td-name">' + h.assigned_to + '</span><div class="td-mono">' + (h.wd_id||'') + '</div>'
          + (h.actual_project_display && h.actual_project_display !== '-' ? '<div class="td-muted">Actual: ' + h.actual_project_display + '</div>' : '')
          + C.hirefNextDetail(h)
      : C.badge('FREE','badge-green')
          + (h.reserved_for_next ? '<div class="td-muted">Reserved: ' + h.reserved_for_next + '</div>' : '')
          + (h.placeholder_name ? '<div class="td-muted">Placeholder: ' + h.placeholder_name + '</div>' : '');
    return '<tr>'
      + '<td class="td-mono">' + (h.id||'') + '</td>'
      + '<td class="text-sm">' + (h.project||'') + '</td>'
      + '<td>' + C.urgencyBadge(h.urgency) + C.hirefSignalBadges(h) + '</td>'
      + '<td class="td-mono">' + (h.end_date||'') + '</td>'
      + '<td>' + who + '</td>'
    + '</tr>';
  },
  staffHirefRow: function(e) {
    return '<tr>'
      + '<td class="td-mono">' + (e.wd_id||'') + '</td>'
      + '<td class="td-name">' + (e.name||'') + '</td>'
      + '<td class="td-mono">' + (e.current_hiref||'') + '</td>'
      + '<td class="text-sm">' + (e.hiref_project||'') + '</td>'
      + '<td>' + C.urgencyBadge(e.urgency) + C.hirefSignalBadges(e) + '</td>'
      + '<td class="td-mono">' + (e.end_date||'') + '</td>'
      + '<td class="text-sm">' + (e.actual_project||'')
          + C.hirefNextDetail(e)
          + ((e.next_hiref_project && e.next_hiref_project !== (e.hiref_project || ''))
              ? '<div class="td-muted">Next project: ' + e.next_hiref_project + '</div>'
              : '')
        + '</td>'
    + '</tr>';
  }
};
