"""Tab Viabilidad (wrapper incremental)."""

from ui.tabs.planning import render_planning_tab as _render_planning_tab


def render_viabilidad_tab():
    return _render_planning_tab()


__all__ = ["render_viabilidad_tab"]
