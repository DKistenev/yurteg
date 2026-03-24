"""Reusable skeleton loading placeholders.

Replaces empty space during data loading with pulsing shimmer bars.
Uses CSS animation from design-system.css (.yt-skeleton-pulse).
"""
from nicegui import ui


def skeleton_rows(count: int = 5, columns: int = 5) -> ui.column:
    """Render skeleton table rows — shimmer bars that match table layout."""
    container = ui.column().classes("w-full gap-0")
    with container:
        for _ in range(count):
            with ui.row().classes("w-full items-center gap-4 px-4 py-3 border-b border-slate-100"):
                for j in range(columns):
                    width = "60%" if j == 0 else "40%" if j < 3 else "30%"
                    ui.element("div").classes("yt-skeleton-pulse rounded").style(
                        f"height: 12px; width: {width};"
                    )
    return container


def skeleton_card() -> ui.card:
    """Render a skeleton card placeholder."""
    card = ui.card().classes("w-full shadow-none border rounded-lg p-5")
    with card:
        ui.element("div").classes("yt-skeleton-pulse rounded").style(
            "height: 16px; width: 50%; margin-bottom: 12px;"
        )
        ui.element("div").classes("yt-skeleton-pulse rounded").style(
            "height: 12px; width: 80%; margin-bottom: 8px;"
        )
        ui.element("div").classes("yt-skeleton-pulse rounded").style(
            "height: 12px; width: 65%;"
        )
    return card
