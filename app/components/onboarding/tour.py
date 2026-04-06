"""Guided tour overlay — 5-step spotlight tour after first document processing.

Phase 12, Plan 02 (original 3 steps).
Phase 19, Plan 01 (expanded to 5 steps, visual polish).
Per ONBR-01: triggered after first pipeline completion, shown once.
Per ONBR-02: «? Гид» button in header resets flag and reruns tour.
Steps: upload → navigation tabs → search/filters → calendar toggle → client dropdown.

Implementation: ui.html + JS (per RESEARCH Pattern 5).
Pitfall 2 guard: setTimeout(startTour, 500) — lets AG Grid finish rendering.
"""
import json
from typing import Callable

from nicegui import ui

from app.styles import HEX


def _build_tour_js(steps: list[dict], tw: int = 300, auto_start: bool = True) -> str:
    """Build pure JS string that creates overlay + tooltip in DOM and runs the tour.

    This can be executed via ui.run_javascript() from ANY context (header, timer, etc.)
    without polluting the NiceGUI slot tree.
    """
    steps_js = json.dumps(steps, ensure_ascii=False)
    return f"""
(function() {{
    // Clean up previous tour if any
    var oldOverlay = document.getElementById('tour-overlay');
    var oldTooltip = document.getElementById('tour-tooltip');
    if (oldOverlay) oldOverlay.remove();
    if (oldTooltip) oldTooltip.remove();

    // Create overlay with clip-path cutout for spotlight
    var overlay = document.createElement('div');
    overlay.id = 'tour-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(15,23,42,0.5);z-index:9000;pointer-events:all;display:none;transition:clip-path 0.3s ease;';
    document.body.appendChild(overlay);

    // Highlight ring — sits exactly around the target element
    var ring = document.createElement('div');
    ring.id = 'tour-ring';
    ring.style.cssText = 'position:fixed;z-index:9001;border:3px solid {HEX["indigo_600"]};border-radius:10px;pointer-events:none;display:none;transition:all 0.3s ease;';
    document.body.appendChild(ring);

    // Create tooltip
    var tooltip = document.createElement('div');
    tooltip.id = 'tour-tooltip';
    tooltip.style.cssText = 'position:fixed;z-index:9002;background:white;border:1px solid #e2e8f0;border-radius:12px;padding:20px 20px 16px;max-width:{tw}px;box-shadow:0 20px 60px rgba(0,0,0,0.15),0 4px 16px rgba(0,0,0,0.1);display:none;';
    document.body.appendChild(tooltip);

    var STEPS = {steps_js};
    var currentStep = 0;
    var highlightedEl = null;

    function clearSpotlight() {{
        highlightedEl = null;
        ring.style.display = 'none';
        overlay.style.clipPath = 'none';
    }}

    function applySpotlight(el) {{
        var pad = 6;
        var rect = el.getBoundingClientRect();
        var t = rect.top - pad, l = rect.left - pad;
        var b = rect.bottom + pad, r = rect.right + pad;

        // Clip-path: polygon covering entire screen with a rectangular hole
        overlay.style.clipPath = 'polygon('
            + '0% 0%, 0% 100%, '
            + l + 'px 100%, ' + l + 'px ' + t + 'px, '
            + r + 'px ' + t + 'px, ' + r + 'px ' + b + 'px, '
            + l + 'px ' + b + 'px, ' + l + 'px 100%, '
            + '100% 100%, 100% 0%)';

        // Position highlight ring
        ring.style.top = t + 'px';
        ring.style.left = l + 'px';
        ring.style.width = (r - l) + 'px';
        ring.style.height = (b - t) + 'px';
        ring.style.display = 'block';

        highlightedEl = el;
    }}

    function positionTooltip(el, position) {{
        var rect = el.getBoundingClientRect();
        var tw = {tw};
        var margin = 14;
        var vw = window.innerWidth;
        tooltip.style.transform = 'none';
        if (position === 'center-top') {{
            tooltip.style.top = (rect.bottom + margin) + 'px';
            var leftPos = Math.max(8, Math.min(vw - tw - 8, (vw - tw) / 2));
            tooltip.style.left = leftPos + 'px';
        }} else if (position === 'below-left') {{
            tooltip.style.top = (rect.bottom + margin) + 'px';
            tooltip.style.left = Math.max(8, rect.left) + 'px';
        }} else if (position === 'below-right') {{
            tooltip.style.top = (rect.bottom + margin) + 'px';
            tooltip.style.left = Math.max(8, rect.right - tw) + 'px';
        }} else {{
            tooltip.style.top = (rect.bottom + margin) + 'px';
            tooltip.style.left = Math.max(8, rect.left) + 'px';
        }}
    }}

    function buildDots(total, active) {{
        var dots = '<div style="display:flex;gap:5px;justify-content:center;margin-top:14px;">';
        for (var i = 0; i < total; i++) {{
            var color = i === active ? '{HEX["indigo_600"]}' : '#e2e8f0';
            dots += '<div style="width:6px;height:6px;border-radius:50%;background:' + color + ';transition:background 0.2s;"></div>';
        }}
        dots += '</div>';
        return dots;
    }}

    function buildProgressBar(index, total) {{
        var pct = Math.round(((index + 1) / total) * 100);
        return '<div style="width:100%;height:3px;background:#f1f5f9;border-radius:99px;margin-top:6px;overflow:hidden;">'
             + '<div style="height:3px;background:{HEX["indigo_600"]};width:' + pct + '%;border-radius:99px;transition:width 0.3s;"></div>'
             + '</div>';
    }}

    function showStep(index) {{
        var step = STEPS[index];
        var el = document.querySelector(step.target);
        clearSpotlight();
        if (el) {{
            applySpotlight(el);
            positionTooltip(el, step.position);
        }}
        var isLast = index === STEPS.length - 1;
        var nextLabel = isLast ? 'Завершить тур' : 'Далее \\u2192';
        tooltip.innerHTML =
            '<div style="font-size:12px;font-weight:500;color:{HEX["slate_400"]};letter-spacing:0.04em;text-transform:uppercase;margin-bottom:6px;">'
            + 'Шаг ' + (index + 1) + ' / ' + STEPS.length
            + buildProgressBar(index, STEPS.length)
            + '</div>'
            + '<div style="font-size:17px;font-weight:700;color:{HEX["slate_900"]};margin-bottom:6px;line-height:1.3;">'
            + step.title
            + '</div>'
            + '<div style="font-size:13.5px;color:{HEX["slate_500"]};line-height:1.65;margin-bottom:18px;">'
            + step.body
            + '</div>'
            + '<div style="display:flex;justify-content:space-between;align-items:center;">'
            + '<button onclick="endTour()" style="font-size:13px;color:{HEX["slate_400"]};cursor:pointer;background:none;border:none;padding:0;">Пропустить</button>'
            + '<button onclick="' + (isLast ? 'endTour' : 'nextStep') + '()" style="padding:10px 28px;background:{HEX["indigo_600"]};color:white;font-size:13.5px;font-weight:600;border-radius:8px;border:none;cursor:pointer;">' + nextLabel + '</button>'
            + '</div>'
            + buildDots(STEPS.length, index);
        tooltip.style.display = 'block';
    }}

    window.nextStep = function() {{
        if (currentStep < STEPS.length - 1) {{
            currentStep++;
            showStep(currentStep);
        }}
    }};

    window.endTour = function() {{
        clearSpotlight();
        // Remove all tour elements from DOM completely
        overlay.remove();
        ring.remove();
        tooltip.remove();
        var doneBtn = document.getElementById('tour-done-btn');
        if (doneBtn) doneBtn.click();
    }};

    function startTour() {{
        overlay.style.display = 'block';
        currentStep = 0;
        showStep(currentStep);
    }}

    {"setTimeout(startTour, 500);" if auto_start else ""}
}})();
"""


def start_tour_via_js(on_complete: Callable) -> None:
    """Start tour from any UI context (header, timer, etc.) via pure JS injection.

    Safe to call from header callbacks — doesn't create NiceGUI elements in the slot tree.
    """
    (
        ui.button("", on_click=on_complete)
        .props("id=tour-done-btn")
        .classes("hidden")
        .style("display: none !important; position: absolute; pointer-events: none;")
    )
    steps = [
        {
            "target": s["target"],
            "title": s["title"],
            "body": s["body"],
            "position": s["position"],
        }
        for s in TOUR_STEPS
    ]
    js_code = _build_tour_js(steps, auto_start=True)
    ui.run_javascript(js_code)

TOUR_STEPS = [
    {
        "target": "[data-tour='upload']",
        "title": "Загрузка документов",
        "body": "Нажмите, чтобы выбрать папку с новыми документами. ЮрТэг обработает их автоматически.",
        "position": "below-right",
    },
    {
        "target": "[data-tour='nav']",
        "title": "Навигация",
        "body": "Реестр, Шаблоны и Настройки — три раздела приложения. Реестр — главное рабочее пространство.",
        "position": "center-top",
    },
    {
        "target": "[data-tour='filters']",
        "title": "Фильтры и поиск",
        "body": "Переключайте вкладки, чтобы видеть только истекающие или требующие внимания договоры. Поиск ищет по всем полям.",
        "position": "below-left",
    },
    {
        "target": "[data-tour='calendar']",
        "title": "Вид календаря",
        "body": "Переключите на вид календаря для просмотра дат платежей и окончания договоров.",
        "position": "below-right",
    },
    {
        "target": "[data-tour='workspace']",
        "title": "Рабочие пространства",
        "body": "Создавайте отдельные пространства для разных клиентов — каждое со своим реестром и настройками.",
        "position": "below-right",
    },
]


def render_tour(on_complete: Callable) -> None:
    """Рендерит guided tour overlay с 5 шагами spotlight.

    Args:
        on_complete: async callback, вызывается когда юрист завершил или пропустил тур.
                     Должен сохранить tour_completed = True через save_setting.
    """
    # Hidden NiceGUI button — JS вызывает его click() когда тур завершён/пропущен
    (
        ui.button("", on_click=on_complete)
        .props("id=tour-done-btn")
        .classes("hidden")
        .style("display: none !important")
    )

    steps_json = [
        {
            "target": s["target"],
            "title": s["title"],
            "body": s["body"],
            "position": s["position"],
        }
        for s in TOUR_STEPS
    ]

    # Build steps JSON for inline JS
    import json
    steps_js = json.dumps(steps_json, ensure_ascii=False)

    # Tooltip max-width in px (matches positionTooltip calc)
    TW = 300

    tour_overlay_html = f"""
<div id="tour-overlay" style="
    position: fixed;
    inset: 0;
    background: rgba(15,23,42,0.6);
    z-index: 9000;
    pointer-events: all;
    display: none;
"></div>

<div id="tour-tooltip" style="
    position: fixed;
    z-index: 9001;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px 20px 16px;
    max-width: {TW}px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.15), 0 4px 16px rgba(0,0,0,0.1);
    display: none;
"></div>
"""

    tour_script = f"""<script>
(function() {{
    const STEPS = {steps_js};
    let currentStep = 0;
    let highlightedEl = null;
    let savedStyle = null;
    let savedPosition = null;
    let savedZIndex = null;

    function clearSpotlight() {{
        if (highlightedEl) {{
            highlightedEl.style.boxShadow = savedStyle || '';
            highlightedEl.style.position = savedPosition || '';
            highlightedEl.style.zIndex = savedZIndex || '';
            highlightedEl.style.borderRadius = '';
            highlightedEl = null;
        }}
    }}

    function applySpotlight(el) {{
        savedStyle = el.style.boxShadow;
        savedPosition = el.style.position;
        savedZIndex = el.style.zIndex;
        el.style.position = 'relative';
        el.style.zIndex = '9002';
        el.style.boxShadow = '0 0 0 4px {HEX["indigo_600"]}, 0 0 0 9999px rgba(15,23,42,0.45)';
        el.style.borderRadius = '8px';
        highlightedEl = el;
    }}

    function positionTooltip(el, position) {{
        const tooltip = document.getElementById('tour-tooltip');
        const rect = el.getBoundingClientRect();
        const tw = {TW};
        const margin = 14;
        const vw = window.innerWidth;

        tooltip.style.transform = 'none';

        if (position === 'center-top') {{
            // Centered horizontally, below the element top edge
            tooltip.style.top = (rect.bottom + margin) + 'px';
            const leftPos = Math.max(8, Math.min(vw - tw - 8, (vw - tw) / 2));
            tooltip.style.left = leftPos + 'px';
        }} else if (position === 'below-left') {{
            tooltip.style.top = (rect.bottom + margin) + 'px';
            tooltip.style.left = Math.max(8, rect.left) + 'px';
        }} else if (position === 'below-right') {{
            tooltip.style.top = (rect.bottom + margin) + 'px';
            tooltip.style.left = Math.max(8, rect.right - tw) + 'px';
        }} else {{
            tooltip.style.top = (rect.bottom + margin) + 'px';
            tooltip.style.left = Math.max(8, rect.left) + 'px';
        }}
    }}

    function buildDots(total, active) {{
        let dots = '<div style="display:flex;gap:5px;justify-content:center;margin-top:14px;">';
        for (let i = 0; i < total; i++) {{
            const color = i === active ? '{HEX["indigo_600"]}' : '#e2e8f0';
            dots += '<div style="width:6px;height:6px;border-radius:50%;background:' + color + ';transition:background 0.2s;"></div>';
        }}
        dots += '</div>';
        return dots;
    }}

    function buildProgressBar(index, total) {{
        const pct = Math.round(((index + 1) / total) * 100);
        return '<div style="width:100%;height:3px;background:#f1f5f9;border-radius:99px;margin-top:6px;overflow:hidden;">'
             + '<div style="height:3px;background:{HEX["indigo_600"]};width:' + pct + '%;border-radius:99px;transition:width 0.3s;"></div>'
             + '</div>';
    }}

    function showStep(index) {{
        const step = STEPS[index];
        const el = document.querySelector(step.target);
        const tooltip = document.getElementById('tour-tooltip');

        clearSpotlight();

        if (el) {{
            applySpotlight(el);
            positionTooltip(el, step.position);
        }}

        const isLast = index === STEPS.length - 1;
        const nextLabel = isLast ? 'Завершить тур' : '\u0414\u0430\u043b\u0435\u0435 \u2192';

        tooltip.innerHTML =
            '<div style="font-size:12px;font-weight:500;color:{HEX["slate_400"]};letter-spacing:0.04em;text-transform:uppercase;margin-bottom:6px;">'
            + '\u0428\u0430\u0433 ' + (index + 1) + ' / ' + STEPS.length
            + buildProgressBar(index, STEPS.length)
            + '</div>'
            + '<div style="font-size:17px;font-weight:700;color:{HEX["slate_900"]};margin-bottom:6px;line-height:1.3;">'
            + step.title
            + '</div>'
            + '<div style="font-size:13.5px;color:{HEX["slate_500"]};line-height:1.65;margin-bottom:18px;">'
            + step.body
            + '</div>'
            + '<div style="display:flex;justify-content:space-between;align-items:center;">'
            + '<button onclick="endTour()" style="font-size:13px;color:{HEX["slate_400"]};cursor:pointer;background:none;border:none;padding:0;transition:color 0.15s;" onmouseover="this.style.color=\'{HEX["slate_500"]}\'" onmouseout="this.style.color=\'{HEX["slate_400"]}\'">Пропустить</button>'
            + '<button onclick="' + (isLast ? 'endTour' : 'nextStep') + '()" style="padding:10px 28px;background:{HEX["indigo_600"]};color:white;font-size:13.5px;font-weight:600;border-radius:8px;border:none;cursor:pointer;transition:background 0.15s;" onmouseover="this.style.background=\'#4338ca\'" onmouseout="this.style.background=\'{HEX["indigo_600"]}\'">' + nextLabel + '</button>'
            + '</div>'
            + buildDots(STEPS.length, index);

        tooltip.style.display = 'block';
    }}

    window.nextStep = function() {{
        if (currentStep < STEPS.length - 1) {{
            currentStep++;
            showStep(currentStep);
        }}
    }};

    window.endTour = function() {{
        clearSpotlight();
        const overlay = document.getElementById('tour-overlay');
        const tooltip = document.getElementById('tour-tooltip');
        if (overlay) overlay.style.display = 'none';
        if (tooltip) tooltip.style.display = 'none';
        // Signal NiceGUI Python side to save tour_completed flag
        const doneBtn = document.getElementById('tour-done-btn');
        if (doneBtn) doneBtn.click();
    }};

    function startTour() {{
        const overlay = document.getElementById('tour-overlay');
        if (overlay) overlay.style.display = 'block';
        currentStep = 0;
        showStep(currentStep);
    }}

    // Pitfall 2 guard: give AG Grid time to render
    setTimeout(startTour, 500);
}})();
</script>
"""

    ui.html(tour_overlay_html)
    ui.add_body_html(tour_script)
