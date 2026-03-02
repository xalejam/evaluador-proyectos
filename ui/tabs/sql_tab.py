"""Tab SQL."""

from ui.tabs.sql_queries import render_sql_queries_tab as _render_sql_queries_tab


def render_sql_tab():
    return _render_sql_queries_tab()


__all__ = ["render_sql_tab"]
