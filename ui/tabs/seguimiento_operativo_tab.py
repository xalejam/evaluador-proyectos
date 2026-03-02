"""Tab Seguimiento Operativo (wrapper incremental)."""

from ui.tabs.seguimiento_operativo import render_seguimiento_operativo as _render_seguimiento_operativo


def render_seguimiento_operativo_tab():
    return _render_seguimiento_operativo()


__all__ = ["render_seguimiento_operativo_tab"]
