"""Tab Dashboard."""

from ui.tabs.dashboard import render_dashboard as _render_dashboard


def render_dashboard_tab():
    return _render_dashboard()


__all__ = ["render_dashboard_tab"]
