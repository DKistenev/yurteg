/* ЮрТэг Calendar — FullCalendar init + tooltip */

window.initCalendar = function(events) {
  var el = document.getElementById('yurteg-calendar');
  if (!el) return;
  if (window._cal) { window._cal.destroy(); }
  window._cal = new FullCalendar.Calendar(el, {
    initialView: 'dayGridMonth',
    locale: 'ru',
    headerToolbar: { left: 'prev,next today', center: 'title', right: '' },
    height: 'auto',
    events: events,
    eventClick: function(info) { showCalTooltip(info); },
    buttonText: { today: 'Сегодня' },
    dayMaxEvents: 3,
  });
  window._cal.render();
};

function showCalTooltip(info) {
  var ev = info.event;
  var props = ev.extendedProps || {};
  var tooltip = document.getElementById('cal-tooltip');
  if (!tooltip) return;
  var typeLabel = props.type === 'end_date' ? 'Дата окончания' : 'Платёж';
  var detail = props.type === 'payment'
    ? (props.amount ? props.amount.toLocaleString('ru') + ' ₽' : '')
    : (ev.startStr || '');
  tooltip.innerHTML =
    '<div style="font-size:11px;color:#94a3b8;">' + typeLabel + '</div>' +
    '<div style="font-size:14px;font-weight:600;color:#0f172a;margin-top:2px;">' + (props.counterparty || ev.title) + '</div>' +
    '<div style="font-size:13px;color:#475569;margin-top:2px;">' + detail + '</div>' +
    '<div style="font-size:13px;color:#4f46e5;font-weight:600;cursor:pointer;margin-top:8px;" onclick="history.pushState(null,\'\',\'/document/' + props.contract_id + '\');window.dispatchEvent(new PopStateEvent(\'popstate\'));document.getElementById(\'cal-tooltip\').style.display=\'none\'">Открыть →</div>';
  var rect = info.el.getBoundingClientRect();
  tooltip.style.display = 'block';
  tooltip.style.top = (rect.bottom + 8) + 'px';
  tooltip.style.left = Math.min(rect.left, window.innerWidth - 280) + 'px';
}

document.addEventListener('click', function(e) {
  var tooltip = document.getElementById('cal-tooltip');
  if (tooltip && !tooltip.contains(e.target) && !e.target.closest('.fc-event')) {
    tooltip.style.display = 'none';
  }
});
