/* utils.js - pure helper functions, no side effects */
function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function fmtPct(val) { return Math.round((val || 0) * 100); }
function fmtMonth(ym) {
  if (!ym) return '';
  var parts = ym.split('-');
  var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return months[parseInt(parts[1], 10) - 1] + " '" + parts[0].substring(2);
}
