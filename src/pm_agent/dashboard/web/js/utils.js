/* utils.js - pure helper functions, no side effects */
function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function escAttr(s) {
  return esc(s).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function fmtPct(val) { return Math.round((val || 0) * 100); }
function fmtMonth(ym) {
  if (!ym) return '';
  var parts = ym.split('-');
  var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return months[parseInt(parts[1], 10) - 1] + " '" + parts[0].substring(2);
}
function fmtDateTime(value) {
  if (!value) return '—';
  var text = String(value);
  var normalized = text.replace(' ', 'T');
  var parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return esc(text);
  var pad = function(num) { return String(num).padStart(2, '0'); };
  return parsed.getFullYear()
    + '-' + pad(parsed.getMonth() + 1)
    + '-' + pad(parsed.getDate())
    + ' ' + pad(parsed.getHours())
    + ':' + pad(parsed.getMinutes());
}
function fmtNumber(value, digits) {
  if (value == null || value === '') return '—';
  var num = Number(value);
  if (Number.isNaN(num)) return esc(String(value));
  var places = digits == null ? 0 : digits;
  return num.toFixed(places).replace(/\.0+$|(\.\d*[1-9])0+$/, '$1');
}
function humanizeKey(key) {
  if (!key) return '';
  return String(key)
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, function(ch) { return ch.toUpperCase(); });
}
function pluralize(count, singular, plural) {
  return count === 1 ? singular : (plural || singular + 's');
}
