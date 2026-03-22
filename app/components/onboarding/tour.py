"""Guided tour overlay — 3-step spotlight tour after first document processing.

Phase 12, Plan 02.
Per D-14: triggered after first pipeline completion, shown once.
Per D-15: 3 steps — registry table, search/filters row, upload button.
Per D-16: full-screen overlay + spotlight on target element via JS.
Per D-18: tour_completed flag saved via config.save_setting.

Implementation: ui.html + JS (per RESEARCH Pattern 5).
Pitfall 2 guard: setTimeout(startTour, 500) — lets AG Grid finish rendering.
"""
from typing import Callable

from nicegui import ui

from app.styles import HEX

TOUR_STEPS = [
    {
        "target": ".ag-root-wrapper",
        "title": "Реестр документов",
        "body": "Это ваш реестр. Кликните на строку для просмотра подробностей.",
        "position": "center-top",  # tooltip below center of screen, above table
    },
    {
        "target": ".search-row",
        "title": "Фильтры и поиск",
        "body": "Переключайте вкладки, чтобы видеть только истекающие или требующие внимания договоры. Поиск ищет по всем полям.",
        "position": "below-left",
    },
    {
        "target": "#upload-btn",
        "title": "Загрузка документов",
        "body": "Нажмите, чтобы выбрать папку с новыми документами для обработки.",
        "position": "below-right",
    },
]


def render_tour(on_complete: Callable) -> None:
    """Рендерит guided tour overlay с 3 шагами spotlight.

    Args:
        on_complete: async callback, вызывается когда юрист завершил или пропустил тур.
                     Должен сохранить tour_completed = True через save_setting.
    """
    # Hidden NiceGUI button — JS вызывает его click() когда тур завершён/пропущен
    done_btn = (
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

    tour_html = f"""
<div id="tour-overlay" style="
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.5);
    z-index: 40;
    pointer-events: all;
"></div>

<div id="tour-tooltip" style="
    position: fixed;
    z-index: 50;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px;
    max-width: 256px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    display: none;
"></div>

<script>
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
            highlightedEl.style.outline = '';
            highlightedEl.style.outlineOffset = '';
            highlightedEl = null;
        }}
    }}

    function applySpotlight(el) {{
        savedStyle = el.style.boxShadow;
        savedPosition = el.style.position;
        savedZIndex = el.style.zIndex;
        el.style.position = 'relative';
        el.style.zIndex = '50';
        el.style.outline = '2px solid {HEX["indigo_600"]}';
        el.style.outlineOffset = '2px';
        highlightedEl = el;
    }}

    function positionTooltip(el, position) {{
        const tooltip = document.getElementById('tour-tooltip');
        const rect = el.getBoundingClientRect();
        const tw = 256;
        const margin = 12;

        if (position === 'center-top') {{
            // Centered horizontally, positioned below top of page (above table content)
            tooltip.style.top = (rect.top + margin) + 'px';
            tooltip.style.left = '50%';
            tooltip.style.transform = 'translateX(-50%)';
        }} else if (position === 'below-left') {{
            // Below the element, left-aligned
            tooltip.style.top = (rect.bottom + margin) + 'px';
            tooltip.style.left = Math.max(8, rect.left) + 'px';
            tooltip.style.transform = 'none';
        }} else if (position === 'below-right') {{
            // Below the element, right-aligned
            tooltip.style.top = (rect.bottom + margin) + 'px';
            tooltip.style.left = Math.max(8, rect.right - tw) + 'px';
            tooltip.style.transform = 'none';
        }} else {{
            tooltip.style.top = (rect.bottom + margin) + 'px';
            tooltip.style.left = Math.max(8, rect.left) + 'px';
            tooltip.style.transform = 'none';
        }}
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
        const nextLabel = isLast ? 'Завершить тур' : 'Далее \u2192';

        tooltip.innerHTML = `
            <div style="font-size: 14px; color: {HEX["slate_400"]}; margin-bottom: 8px;">
                \u0428\u0430\u0433 ${{index + 1}} / ${{STEPS.length}}
            </div>
            <div style="font-size: 20px; font-weight: 600; color: {HEX["slate_900"]}; margin-bottom: 4px;">
                ${{step.title}}
            </div>
            <div style="font-size: 14px; color: {HEX["slate_500"]}; line-height: 1.625; margin-bottom: 16px;">
                ${{step.body}}
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <button onclick="endTour()" style="
                    font-size: 14px;
                    color: {HEX["slate_400"]};
                    cursor: pointer;
                    background: none;
                    border: none;
                    padding: 0;
                ">Пропустить тур</button>
                <button onclick="${{isLast ? 'endTour' : 'nextStep'}}()" style="
                    padding: 8px 24px;
                    background: {HEX["indigo_600"]};
                    color: white;
                    font-size: 14px;
                    font-weight: 600;
                    border-radius: 8px;
                    border: none;
                    cursor: pointer;
                ">${{nextLabel}}</button>
            </div>
        `;
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

    ui.html(tour_html)
