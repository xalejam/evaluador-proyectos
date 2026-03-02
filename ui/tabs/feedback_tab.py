"""Tab Feedback."""

from ui.tabs.feedback_processor import render_feedback_processor as _render_feedback_processor


def render_feedback_tab():
    return _render_feedback_processor()


__all__ = ["render_feedback_tab"]
