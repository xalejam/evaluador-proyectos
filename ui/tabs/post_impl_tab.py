"""Tab Post-Implementacion."""

from ui.tabs.tracking import render_tracking_tab as _render_tracking_tab


def render_post_impl_tab():
    return _render_tracking_tab()


__all__ = ["render_post_impl_tab"]
